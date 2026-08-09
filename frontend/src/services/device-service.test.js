import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { DeviceService } from "./device-service"
import { ApiService } from "./api-service"

// removeDevice/setDevice/blinkPod address a single device by id in the path.
// A single-quoted template literal ('api/v1/devices/${deviceId}') is NOT
// interpolated — it would DELETE the literal ".../${deviceId}" and never hit
// the real device. These tests pin that the id lands in the URL.
describe("DeviceService per-device routes interpolate the id", () => {
    let spy
    beforeEach(() => {
        spy = vi
            .spyOn(ApiService.prototype, "httpRequestCall")
            .mockResolvedValue({ status: 200, json: () => Promise.resolve({}) })
    })
    afterEach(() => vi.restoreAllMocks())

    it("removeDevice targets the id, not a literal template", () => {
        new DeviceService().removeDevice(42)
        expect(spy).toHaveBeenCalledWith("api/v1/devices/42", "DELETE", {})
    })

    it("setDevice targets the id", () => {
        new DeviceService().setDevice(7, { name: "x" })
        expect(spy).toHaveBeenCalledWith("api/v1/devices/7", "PUT", { name: "x" })
    })

    it("blinkPod targets the id's blink subroute", () => {
        new DeviceService().blinkPod(9, "on")
        expect(spy.mock.calls[0][0]).toBe("api/v1/devices/9/blink")
    })
})
