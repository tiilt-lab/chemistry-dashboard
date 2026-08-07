// Web Bluetooth client for Polar H10 (or any strap exposing the standard
// GATT Heart Rate service). One connection per speaker; each notification
// carries BPM plus zero or more beat-to-beat RR intervals (1/1024 s units),
// which is the raw material for HRV (RMSSD etc.).
//
// Web Bluetooth exists in Chrome/Edge (desktop + Android) over HTTPS only —
// callers should gate UI on isBluetoothSupported().

const HEART_RATE_SERVICE = "heart_rate"
const HEART_RATE_MEASUREMENT = "heart_rate_measurement"
const BATTERY_SERVICE = "battery_service"
const BATTERY_LEVEL = "battery_level"

export const isBluetoothSupported = () =>
    typeof navigator !== "undefined" && !!navigator.bluetooth

// Parse a Heart Rate Measurement characteristic value (GATT 0x2A37).
// Returns { hr: bpm, rr: [ms, ...] }.
export const parseHeartRateMeasurement = (dataView) => {
    const flags = dataView.getUint8(0)
    let offset = 1
    let hr
    if (flags & 0x01) {
        hr = dataView.getUint16(offset, true)
        offset += 2
    } else {
        hr = dataView.getUint8(offset)
        offset += 1
    }
    if (flags & 0x08) offset += 2 // energy expended field, skip
    const rr = []
    if (flags & 0x10) {
        for (; offset + 1 < dataView.byteLength; offset += 2) {
            // RR is in 1/1024ths of a second per the spec.
            rr.push(Math.round((dataView.getUint16(offset, true) * 1000) / 1024))
        }
    }
    return { hr, rr }
}

// One managed strap connection. onSample({hr, rr, t}) fires per notification
// (H10: ~1/s); onStatus("connecting"|"connected"|"disconnected", info) tracks
// the connection lifecycle, including auto-reconnect attempts.
export class PolarConnection {
    constructor({ onSample, onStatus }) {
        this.onSample = onSample || (() => {})
        this.onStatus = onStatus || (() => {})
        this.device = null
        this.characteristic = null
        this.battery = null
        this.closed = false
        this._reconnectTimer = null
        this._notifyHandler = (event) => {
            const { hr, rr } = parseHeartRateMeasurement(event.target.value)
            this.onSample({ hr, rr, t: Date.now() })
        }
        this._disconnectHandler = () => {
            this.characteristic = null
            if (this.closed) return
            this.onStatus("disconnected")
            // Straps drop out when the wearer walks off or the band dries
            // out — retry quietly until close() or the strap comes back.
            this._reconnectTimer = setTimeout(() => this._attach().catch(() => {
                if (!this.closed) this._disconnectHandler()
            }), 3000)
        }
    }

    // Must be called from a user gesture (button click): opens the browser's
    // device chooser listing nearby heart-rate straps. Filters are OR'd:
    // Polar straps don't reliably put the HR service UUID in their
    // advertisement (varies with firmware/bonding state), so filtering on
    // the service alone can miss a worn, advertising strap — match on the
    // "Polar" name too, with the HR service in optionalServices so a
    // name-matched device still exposes it after connecting.
    async choose() {
        this.device = await navigator.bluetooth.requestDevice({
            filters: [
                { services: [HEART_RATE_SERVICE] },
                { namePrefix: "Polar" },
            ],
            optionalServices: [HEART_RATE_SERVICE, BATTERY_SERVICE],
        })
        this.device.addEventListener("gattserverdisconnected", this._disconnectHandler)
        await this._attach()
        return {
            // e.g. "Polar H10 8C0B2A2B" — the ID printed on the strap module.
            name: this.device.name || "Heart-rate sensor",
            battery: this.battery,
        }
    }

    async _attach() {
        if (this.closed || !this.device) return
        this.onStatus("connecting")
        const server = await this.device.gatt.connect()
        const service = await server.getPrimaryService(HEART_RATE_SERVICE)
        this.characteristic = await service.getCharacteristic(HEART_RATE_MEASUREMENT)
        this.characteristic.addEventListener(
            "characteristicvaluechanged",
            this._notifyHandler,
        )
        await this.characteristic.startNotifications()
        try {
            const batt = await server.getPrimaryService(BATTERY_SERVICE)
            const level = await batt.getCharacteristic(BATTERY_LEVEL)
            this.battery = (await level.readValue()).getUint8(0)
        } catch (ex) {
            this.battery = null // battery service is optional
        }
        this.onStatus("connected", { battery: this.battery })
    }

    close() {
        this.closed = true
        if (this._reconnectTimer) clearTimeout(this._reconnectTimer)
        if (this.device) {
            this.device.removeEventListener(
                "gattserverdisconnected",
                this._disconnectHandler,
            )
            if (this.device.gatt && this.device.gatt.connected) {
                this.device.gatt.disconnect()
            }
        }
        this.device = null
        this.characteristic = null
    }
}
