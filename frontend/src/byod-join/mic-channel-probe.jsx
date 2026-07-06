import { useEffect, useRef, useState } from "react"

// Validates multi-channel mic kits (e.g. a 2-transmitter lav receiver on
// USB-C) before we build per-channel speaker attribution on top of them:
// shows how many channels the selected input exposes, with a live level
// meter per channel so each mic can be tapped and identified.
//
// Constraints matter: echo cancellation / noise suppression force a mono
// downmix on several platforms, so they are disabled for the probe.
const MAX_CHANNELS = 8

function MicChannelProbe() {
    const [state, setState] = useState("idle") // idle | running | error
    const [message, setMessage] = useState("")
    const [deviceLabel, setDeviceLabel] = useState("")
    const [channels, setChannels] = useState(0)
    const [levels, setLevels] = useState([])
    const cleanupRef = useRef(null)

    const stop = () => {
        if (cleanupRef.current) {
            cleanupRef.current()
            cleanupRef.current = null
        }
        setState("idle")
        setLevels([])
    }

    useEffect(() => () => cleanupRef.current && cleanupRef.current(), [])

    const start = async () => {
        setMessage("")
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: { ideal: MAX_CHANNELS },
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                },
                video: false,
            })
            const track = stream.getAudioTracks()[0]
            const settings = track.getSettings ? track.getSettings() : {}
            const ctx = new AudioContext()
            const source = ctx.createMediaStreamSource(stream)
            const reported =
                settings.channelCount || source.channelCount || 1
            const n = Math.max(1, Math.min(reported, MAX_CHANNELS))
            const splitter = ctx.createChannelSplitter(n)
            source.connect(splitter)
            const analysers = []
            for (let i = 0; i < n; i++) {
                const an = ctx.createAnalyser()
                an.fftSize = 512
                splitter.connect(an, i)
                analysers.push(an)
            }
            setDeviceLabel(track.label || "Microphone")
            setChannels(n)
            setState("running")

            let raf = null
            const buf = new Float32Array(512)
            const tick = () => {
                const next = analysers.map((an) => {
                    an.getFloatTimeDomainData(buf)
                    let sum = 0
                    for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i]
                    return Math.sqrt(sum / buf.length)
                })
                setLevels(next)
                raf = requestAnimationFrame(tick)
            }
            tick()

            cleanupRef.current = () => {
                if (raf) cancelAnimationFrame(raf)
                stream.getTracks().forEach((t) => t.stop())
                ctx.close().catch(() => {})
            }
        } catch (ex) {
            setState("error")
            setMessage(
                ex && ex.name === "NotAllowedError"
                    ? "Microphone access was blocked — allow it and try again."
                    : "Couldn't open the microphone (" +
                      ((ex && ex.name) || "error") +
                      ").",
            )
        }
    }

    return (
        <div className="rounded-xl border border-tiilt-line bg-tiilt-ground/60 px-4 py-3">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <div className="text-sm font-semibold text-tiilt-ink">
                        Microphone check
                    </div>
                    <div className="mt-0.5 text-xs text-tiilt-muted">
                        See how many channels your mic setup provides — tap
                        each mic to find its channel.
                    </div>
                </div>
                {state === "running" ? (
                    <button
                        type="button"
                        onClick={stop}
                        className="flex-none cursor-pointer rounded-lg border border-tiilt-line bg-white px-3 py-1.5 text-xs font-semibold text-tiilt-ink transition hover:border-tiilt"
                    >
                        Stop
                    </button>
                ) : (
                    <button
                        type="button"
                        onClick={start}
                        className="flex-none cursor-pointer rounded-lg border border-tiilt-line bg-white px-3 py-1.5 text-xs font-semibold text-tiilt transition hover:border-tiilt hover:bg-tiilt-soft"
                    >
                        Check mic
                    </button>
                )}
            </div>

            {state === "error" ? (
                <div className="mt-2 rounded-md bg-tiilt-danger-soft px-3 py-1.5 text-xs text-tiilt-danger">
                    {message}
                </div>
            ) : null}

            {state === "running" ? (
                <div className="mt-3 flex flex-col gap-2">
                    <div className="truncate text-xs text-tiilt-muted" title={deviceLabel}>
                        {deviceLabel}
                    </div>
                    <div className="text-xs font-semibold text-tiilt-ink">
                        {channels === 1
                            ? "1 channel — speakers will be identified by voice"
                            : `${channels} channels detected — one mic per person is possible on this setup`}
                    </div>
                    {levels.map((lvl, i) => (
                        <div key={i} className="flex items-center gap-2">
                            <span className="w-16 flex-none font-ahamono text-[11px] text-tiilt-muted">
                                ch {i + 1}
                            </span>
                            <div className="h-2.5 grow overflow-hidden rounded-full bg-tiilt-line/40">
                                <div
                                    className="h-full rounded-full bg-tiilt-teal transition-[width] duration-75"
                                    style={{
                                        width: `${Math.min(100, Math.round(lvl * 300))}%`,
                                    }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            ) : null}
        </div>
    )
}

export { MicChannelProbe }
