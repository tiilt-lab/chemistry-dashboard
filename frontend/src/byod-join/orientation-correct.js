// Upright recording for rotation-locked phones.
//
// The camera pipeline orients its buffer to the SCREEN, not to gravity. A
// phone mounted sideways with rotation lock on (the normal state for a phone
// used as a recording rig) reports portrait everywhere — matchMedia, screen
// .orientation, the captured track — while the scene inside the buffer lies
// on its side. No screen-based API can see through that; the accelerometer
// can. When physical orientation (gravity) disagrees with the buffer shape,
// we re-rasterize the camera track through a rotated canvas so the ENCODED
// video is upright — playback, live analytics, and posthoc all get correct
// frames with no server-side work.
//
// iOS is deliberately skipped: DeviceMotion needs a permission prompt there,
// and iOS Safari already rotates capture buffers to match the physical
// device, so there is nothing to fix.

// User-selectable orientation modes for the device-check preview. Android
// camera pipelines disagree about who compensates rotation — some orient
// the buffer to the screen (sideways content under rotation lock), some to
// gravity (upright content in whatever frame satisfied the constraints),
// and no API distinguishes them. "auto" applies the gravity heuristic;
// the rest force a specific handling, chosen by eye against the preview
// and remembered per camera.
export const ORIENTATION_MODES = [
    { id: "auto", label: "Auto" },
    { id: "ccw", label: "Rotate left" },
    { id: "cw", label: "Rotate right" },
    { id: "wide", label: "Wide (ask camera for landscape)" },
    { id: "flip", label: "Upside-down" },
]

export const rotationForMode = (id) =>
    ({ cw: 90, ccw: -90, flip: 180 })[id] || 0

// One gravity sample from devicemotion, or null when unavailable (iOS
// permission-gated, no sensor, or no event within the timeout).
const readGravity = (timeoutMs = 700) =>
    new Promise((resolve) => {
        if (
            typeof DeviceMotionEvent === "undefined" ||
            typeof DeviceMotionEvent.requestPermission === "function"
        ) {
            resolve(null)
            return
        }
        let done = false
        const finish = (v) => {
            if (!done) {
                done = true
                window.removeEventListener("devicemotion", onMotion)
                resolve(v)
            }
        }
        const onMotion = (e) => {
            const g = e.accelerationIncludingGravity
            if (g && (g.x != null || g.y != null)) {
                finish({ ax: g.x || 0, ay: g.y || 0 })
            }
        }
        window.addEventListener("devicemotion", onMotion)
        setTimeout(() => finish(null), timeoutMs)
    })

// Degrees the captured frame must be rotated to stand upright, or 0.
//
// The camera orients its buffer to the SCREEN, so the correction is the
// mismatch between screen orientation and gravity — the buffer's own shape
// says nothing reliable (a sideways phone can hand back either shape,
// depending on how the browser satisfied the size constraints). Engage only
// on a portrait-vs-landscape shape mismatch: within-landscape 90-vs-270
// never triggers, so phones with auto-rotate working are never touched.
//
// Device coords: x across the screen (portrait right), y along it (portrait
// up); accelerationIncludingGravity points opposite gravity, so upright
// portrait reads ay≈+9.8 and a sideways mount puts the weight on ax. A
// near-flat phone (both small) gives no orientation signal — leave as-is.
//
// Sign, validated against real sideways captures (pods 1212/1219,
// 2026-08-08): a mount with the phone-top to the LEFT (ax>0) leaves the
// scene rotated clockwise in a portrait-oriented capture — world-up points
// at the frame's right edge — so the correction is counter-clockwise (-90).
export async function neededRotation() {
    const g = await readGravity()
    if (!g) return 0
    const MIN_G = 4 // m/s² — below this on both axes the phone is lying flat
    const physPortrait =
        Math.abs(g.ay) >= Math.abs(g.ax) && Math.abs(g.ay) > MIN_G
    const physLandscape =
        Math.abs(g.ax) > Math.abs(g.ay) && Math.abs(g.ax) > MIN_G

    const angle =
        (window.screen &&
            window.screen.orientation &&
            window.screen.orientation.angle) ||
        0
    const screenLandscape = angle === 90 || angle === 270

    if (physLandscape && !screenLandscape) {
        return g.ax > 0 ? -90 : 90
    }
    if (physPortrait && screenLandscape) {
        // Landscape-locked screen, phone held upright: undo the screen's
        // rotation (angle 90 and 270 are opposite landscapes).
        return angle === 90 ? 90 : -90
    }
    if (physPortrait && !screenLandscape && g.ay < -MIN_G) {
        return 180 // mounted upside-down
    }
    return 0
}

const withTimeout = (promise, ms, what) =>
    Promise.race([
        promise,
        new Promise((_res, rej) =>
            setTimeout(() => rej(new Error("timeout: " + what)), ms),
        ),
    ])

// Wrap the stream's video track in a rotated-canvas re-rasterization.
// Returns { stream, stop }: `stream` carries the corrected video plus the
// ORIGINAL audio tracks; `stop` ends the draw loop (camera tracks are the
// caller's to stop). Frame pacing uses requestVideoFrameCallback when the
// browser has it (one draw per camera frame), falling back to rAF.
//
// FAIL-OPEN by design: every stage is bounded and the function proves
// frames are actually flowing before returning — on any doubt it throws so
// the caller records the raw stream instead. A sideways recording is
// recoverable; a silently empty one is not (pod 1221 recorded exactly one
// byte of video when an early version hung here).
export async function correctedStream(rawStream, rotationDeg) {
    const track = rawStream.getVideoTracks()[0]
    const vid = document.createElement("video")
    vid.muted = true
    vid.playsInline = true
    vid.setAttribute("playsinline", "")
    vid.srcObject = new MediaStream([track])
    // Mark the decoder so the join page's querySelector("video") calls can
    // exclude it: if the preview stream gets assigned to THIS element, the
    // camera track feeding the canvas stops decoding and the recorder goes
    // silent while the on-screen preview still looks alive.
    vid.setAttribute("data-orient-decoder", "")
    // Detached <video> elements are not guaranteed to decode on Android
    // Chrome — keep it in the DOM, invisible.
    vid.style.cssText =
        "position:fixed;left:0;top:0;width:2px;height:2px;opacity:0;pointer-events:none;"
    document.body.appendChild(vid)
    const dropVid = () => {
        vid.srcObject = null
        vid.remove()
    }

    try {
        await withTimeout(vid.play(), 2000, "camera preview play")
        if (!vid.videoWidth) {
            await withTimeout(
                new Promise((res) =>
                    vid.addEventListener("loadedmetadata", res, { once: true }),
                ),
                2000,
                "camera metadata",
            )
        }
        const w = vid.videoWidth
        const h = vid.videoHeight
        if (!w || !h) throw new Error("camera reported no dimensions")

        const swap = Math.abs(rotationDeg) === 90
        const canvas = document.createElement("canvas")
        canvas.width = swap ? h : w
        canvas.height = swap ? w : h
        const ctx = canvas.getContext("2d")

        let running = true
        let framesDrawn = 0
        const draw = () => {
            ctx.save()
            ctx.translate(canvas.width / 2, canvas.height / 2)
            ctx.rotate((rotationDeg * Math.PI) / 180)
            ctx.drawImage(vid, -w / 2, -h / 2, w, h)
            ctx.restore()
            framesDrawn += 1
        }
        const useVFC = typeof vid.requestVideoFrameCallback === "function"
        const loop = () => {
            if (!running) return
            draw()
            if (useVFC) {
                vid.requestVideoFrameCallback(loop)
            } else {
                requestAnimationFrame(loop)
            }
        }
        loop()

        // Prove the pipeline is live before anyone records from it.
        await new Promise((res) => setTimeout(res, 700))
        if (framesDrawn === 0) {
            running = false
            throw new Error("no frames drawn")
        }

        const out = canvas.captureStream(30)
        rawStream.getAudioTracks().forEach((t) => out.addTrack(t))
        return {
            stream: out,
            stop: () => {
                running = false
                out.getVideoTracks().forEach((t) => t.stop())
                dropVid()
            },
        }
    } catch (e) {
        dropVid()
        throw e
    }
}
