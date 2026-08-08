import { useEffect, useRef, useState } from "react"
import { dlgSelect, dlgError } from "../components/dialog-styles"
import {
    ORIENTATION_MODES,
    rotationForMode,
    neededRotation,
    correctedStream,
} from "./orientation-correct"

// Inline device check, embedded in the join form (it used to be a separate
// "Check your devices" page between the form and joining): live camera
// preview, a level meter per audio channel, and (for multi-channel rigs
// like 2-transmitter lav receivers) a picker for which channel to record.
// The current selection is continuously mirrored into `selectionRef` so the
// form's "Connect to server" click can read it synchronously — deviceIds go
// into getUserMedia and the channel choice is applied by a ChannelSplitter
// before the audio worklet.
//
// Echo cancellation / noise suppression are disabled here and during the
// session whenever a specific channel is chosen — several platforms force
// a mono downmix when they are on, which destroys channel separation.
const MAX_CHANNELS = 8

const fieldLabel = "mb-1.5 block text-left text-sm font-semibold text-tiilt-ink"

// 360° conference cameras (j5create JVCU360 "360 All Around", Jabra
// PanaCast, ...) are plain UVC webcams that compose their dewarped panorama
// inside whatever frame size the host requests. UVC exposes nothing more
// structured than the device label, so panorama handling keys off it.
const isPanoramaCamera = (label) => /360|panacast|panoram/i.test(label || "")

// Full HD is the default: phone cameras deliver it natively, faces stay
// legible across a whole table (the analytics face detector downscales its
// own input, so the extra pixels cost decode time, not accuracy), and 360°
// panorama cameras need it or their whole ring view is squeezed into a
// small frame. The lower options remain for constrained uplinks — the
// bitrate cap scales with the pixels actually captured either way.
const RESOLUTIONS = [
    { value: "1920x1080", label: "1920 × 1080 (Full HD, default)" },
    { value: "1280x720", label: "1280 × 720 (HD)" },
    { value: "640x480", label: "640 × 480 (low bandwidth)" },
]

const parseResolution = (value) => {
    const m = /^(\d+)x(\d+)$/.exec(value || "")
    return m ? { width: Number(m[1]), height: Number(m[2]) } : null
}

// Constraint dims for an orientation mode: "wide" explicitly asks the
// camera for a landscape frame (the right move for pipelines that keep the
// content upright themselves — rotating their portrait crop can never
// recover the wide field of view); every other mode requests the
// screen-oriented shape and fixes rotation after capture if needed.
const dimsForMode = (mode, res) => {
    if (mode === "wide") {
        return {
            width: { ideal: Math.max(res.width, res.height) },
            height: { ideal: Math.min(res.width, res.height) },
        }
    }
    return orientedDims(res.width, res.height)
}

const orientStorageKey = (camId) => "blinc.orient." + (camId || "default")

// Orientation-agnostic "can this camera deliver this resolution" test —
// portrait phone cameras report their maximums swapped (1080×1920).
const resFitsCamera = (res, camMax) => {
    if (!res || !camMax) return true
    return (
        Math.max(res.width, res.height) <= Math.max(camMax.w, camMax.h) &&
        Math.min(res.width, res.height) <= Math.min(camMax.w, camMax.h)
    )
}

// Session capture points AWAY from whoever set the pod up: a phone or
// tablet propped on the table should record the group with its back camera,
// which on every such device has the better sensor and optics. (Enrollment
// stays on "user" — there you are recording your own face.) Plain string =
// "ideal", so laptops and single-camera devices fall back to what they have
// instead of failing; an explicit camera pick overrides it entirely.
export const SESSION_FACING = "environment"

// Width/height constraints oriented to how the device is actually held. A
// phone held upright delivers portrait frames; asking that camera for a
// landscape-shaped box (or a sideways-mounted phone for a portrait one)
// makes the browser crop or squeeze before a byte is encoded. Desktops
// report landscape and keep the classic shapes. `ideal` lets the browser
// fall back to the camera's nearest native mode instead of failing.
const orientedDims = (w, h) => {
    const portrait =
        typeof window.matchMedia === "function" &&
        window.matchMedia("(orientation: portrait)").matches
    return portrait
        ? { width: { ideal: Math.min(w, h) }, height: { ideal: Math.max(w, h) } }
        : { width: { ideal: Math.max(w, h) }, height: { ideal: Math.min(w, h) } }
}

function InlineDeviceCheck({ wantsVideo, selectionRef }) {
    const [error, setError] = useState("")
    const [mics, setMics] = useState([])
    const [cams, setCams] = useState([])
    const [micId, setMicId] = useState("")
    const [camId, setCamId] = useState("")
    const [channels, setChannels] = useState(1)
    const [levels, setLevels] = useState([])
    const [channelChoice, setChannelChoice] = useState("mix") // "mix" | index
    // Default Full HD. The low-bandwidth defaults from the 2026-08-08
    // incident treated a server-side ingest stall as a network limit; with
    // the streaming decoder fix the service ingests at line speed, venue
    // uplinks measured 79+ Mbps, and the 2.5 Mbps bitrate cap bounds each
    // pod's bandwidth regardless of the resolution chosen here.
    const [resChoice, setResChoice] = useState("1920x1080")
    const [actualRes, setActualRes] = useState("")
    // What the current camera can deliver at most ({w, h} or null when the
    // browser doesn't expose it) — drives the "up to ..." line and greys
    // out resolution choices the camera can't honor (the browser would
    // otherwise silently downgrade and record less than the label promises).
    const [camMax, setCamMax] = useState(null)
    const [orientMode, setOrientMode] = useState(
        // Default "wide": the camera itself delivers a landscape frame, so
        // no rotation canvas ever sits between the camera and the recorder
        // (the canvas path has stalled into zero-byte recordings on real
        // pods). "auto"/rotate remain as explicit choices for rigs whose
        // preview needs them.
        () => localStorage.getItem(orientStorageKey("")) || "wide",
    )
    const videoRef = useRef(null)
    const cleanupRef = useRef(null)
    const streamRef = useRef(null)

    const stopPreview = () => {
        if (cleanupRef.current) {
            cleanupRef.current()
            cleanupRef.current = null
        }
        streamRef.current = null
    }

    // Mirror the live selection (and a way to release the devices) into the
    // parent's ref on every render, so the join click reads fresh values.
    useEffect(() => {
        const vtrack =
            streamRef.current && streamRef.current.getVideoTracks
                ? streamRef.current.getVideoTracks()[0]
                : null
        selectionRef.current = {
            audioDeviceId: micId || null,
            videoDeviceId: camId || null,
            videoResolution: parseResolution(resChoice),
            videoPanorama: !!(vtrack && isPanoramaCamera(vtrack.label)),
            channelIndex: channelChoice === "mix" ? null : channelChoice,
            orientationMode: orientMode,
            stopPreview,
        }
    })

    // Remember the orientation choice per camera, so a rig only needs
    // dialing in once.
    useEffect(() => {
        const saved = localStorage.getItem(orientStorageKey(camId))
        if (saved) setOrientMode(saved)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [camId])

    // If the camera can't deliver the selected resolution, drop to the
    // best one it can — otherwise the browser silently downgrades and the
    // recording is smaller than the picker claims.
    useEffect(() => {
        if (!camMax) return
        if (!resFitsCamera(parseResolution(resChoice), camMax)) {
            const best = RESOLUTIONS.find((r) =>
                resFitsCamera(parseResolution(r.value), camMax),
            )
            if (best) setResChoice(best.value)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [camMax])

    const openPreview = async (audioDeviceId, videoDeviceId) => {
        stopPreview()
        setError("")
        const chosenRes = parseResolution(resChoice)
        try {
            const constraints = {
                audio: {
                    channelCount: { ideal: MAX_CHANNELS },
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                    ...(audioDeviceId ? { deviceId: { exact: audioDeviceId } } : {}),
                },
                video: wantsVideo
                    ? {
                          // An explicit camera pick replaces the facing hint
                          // rather than competing with it.
                          ...(videoDeviceId
                              ? { deviceId: { exact: videoDeviceId } }
                              : { facingMode: SESSION_FACING }),
                          ...dimsForMode(
                              orientMode,
                              chosenRes || { width: 1920, height: 1080 },
                          ),
                      }
                    : false,
            }
            const stream = await navigator.mediaDevices.getUserMedia(constraints)
            streamRef.current = stream

            const vtrack = stream.getVideoTracks()[0]
            if (wantsVideo && vtrack) {
                const vset = vtrack.getSettings ? vtrack.getSettings() : {}
                setActualRes(
                    vset.width && vset.height
                        ? vset.width + " × " + vset.height
                        : "",
                )
                const caps = vtrack.getCapabilities
                    ? vtrack.getCapabilities()
                    : {}
                setCamMax(
                    caps.width && caps.width.max && caps.height && caps.height.max
                        ? { w: caps.width.max, h: caps.height.max }
                        : null,
                )
            }

            // Preview exactly what will be recorded: rotate modes (and
            // auto, when gravity says the mount is sideways) run through
            // the same corrected-canvas path the recorder uses.
            let previewStream = stream
            let orientFix = null
            if (wantsVideo) {
                try {
                    const rot =
                        orientMode === "auto"
                            ? await neededRotation()
                            : rotationForMode(orientMode)
                    if (rot !== 0) {
                        orientFix = await correctedStream(stream, rot)
                        previewStream = orientFix.stream
                    }
                } catch {
                    previewStream = stream
                }
            }

            if (wantsVideo && videoRef.current) {
                videoRef.current.srcObject = previewStream
                videoRef.current.play().catch(() => {})
            }

            // Device labels only populate after permission is granted.
            const devices = await navigator.mediaDevices.enumerateDevices()
            setMics(devices.filter((d) => d.kind === "audioinput"))
            setCams(devices.filter((d) => d.kind === "videoinput"))

            const track = stream.getAudioTracks()[0]
            const settings = track && track.getSettings ? track.getSettings() : {}
            const ctx = new AudioContext()
            const source = ctx.createMediaStreamSource(stream)
            const n = Math.max(
                1,
                Math.min(settings.channelCount || source.channelCount || 1, MAX_CHANNELS),
            )
            setChannels(n)
            setChannelChoice((prev) =>
                prev !== "mix" && prev >= n ? "mix" : prev,
            )
            const splitter = ctx.createChannelSplitter(n)
            source.connect(splitter)
            const analysers = []
            for (let i = 0; i < n; i++) {
                const an = ctx.createAnalyser()
                an.fftSize = 512
                splitter.connect(an, i)
                analysers.push(an)
            }
            const bufs = analysers.map(() => new Float32Array(512))
            let raf = null
            const tick = () => {
                setLevels(
                    analysers.map((an, i) => {
                        an.getFloatTimeDomainData(bufs[i])
                        let sum = 0
                        for (let k = 0; k < bufs[i].length; k++)
                            sum += bufs[i][k] * bufs[i][k]
                        return Math.sqrt(sum / bufs[i].length)
                    }),
                )
                raf = requestAnimationFrame(tick)
            }
            tick()

            cleanupRef.current = () => {
                if (raf) cancelAnimationFrame(raf)
                if (orientFix) orientFix.stop()
                stream.getTracks().forEach((t) => t.stop())
                ctx.close().catch(() => {})
            }
        } catch (ex) {
            setError(
                ex && ex.name === "NotAllowedError"
                    ? "Camera/microphone access was blocked — allow it in your browser and try again."
                    : "Couldn't open the selected device (" +
                          ((ex && ex.name) || "error") +
                          ").",
            )
        }
    }

    useEffect(() => {
        openPreview(micId || undefined, camId || undefined)
        return stopPreview
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [micId, camId, resChoice, wantsVideo, orientMode])

    const cycleOrientMode = () => {
        const ids = ORIENTATION_MODES.map((m) => m.id)
        const next = ids[(ids.indexOf(orientMode) + 1) % ids.length]
        setOrientMode(next)
        localStorage.setItem(orientStorageKey(camId), next)
    }

    const speaking = levels.some((l) => l > 0.02)

    // "Wide" was asked for but the camera delivered portrait — on iPhones
    // this means the rotation lock is pinning the capture to a portrait
    // window (the wide field of view is cropped away before recording).
    // Warn here, where there's still time to fix it before joining.
    const portraitCapture = (() => {
        if (orientMode !== "wide") return false
        const m = /^(\d+) × (\d+)$/.exec(actualRes)
        return m != null && Number(m[2]) > Number(m[1])
    })()

    return (
        <div className="flex flex-col gap-4">
            {error ? (
                <div className={dlgError}>{error}</div>
            ) : null}

            {wantsVideo && (
                <div>
                    <label className={fieldLabel}>Camera</label>
                    <video
                        ref={videoRef}
                        muted
                        autoPlay
                        playsInline
                        className="w-full rounded-xl bg-black"
                    />
                    {(actualRes || camMax) && (
                        <div className="mt-1 text-right font-ahamono text-[11px] text-tiilt-muted">
                            {actualRes && <>capturing at {actualRes}</>}
                            {actualRes && camMax && " — "}
                            {camMax && (
                                <>
                                    camera supports up to {camMax.w} ×{" "}
                                    {camMax.h}
                                </>
                            )}
                        </div>
                    )}
                    {portraitCapture && (
                        <div className="mt-1 rounded-lg bg-amber-100 px-3 py-2 text-xs font-semibold text-amber-900">
                            The camera is delivering a tall (portrait)
                            picture. To record wide, turn off the phone&apos;s
                            rotation lock and hold it sideways — the recording
                            screen will ask again before it starts.
                        </div>
                    )}
                    <div className="mt-2 flex items-center justify-between gap-3">
                        <span className="text-left text-xs text-tiilt-muted">
                            Orientation:{" "}
                            <span className="font-semibold">
                                {(ORIENTATION_MODES.find((m) => m.id === orientMode) || ORIENTATION_MODES[0]).label}
                            </span>
                            {" — mount the phone as it will record; if this preview is sideways or narrow, change until it looks right."}
                        </span>
                        <button
                            type="button"
                            onClick={cycleOrientMode}
                            className="shrink-0 rounded-lg border border-tiilt-muted/40 px-3 py-1.5 text-xs font-semibold text-tiilt-ink"
                        >
                            Change
                        </button>
                    </div>
                    {cams.length > 1 && (
                        <select
                            aria-label="Camera"
                            className={dlgSelect + " mt-2"}
                            value={camId}
                            onChange={(e) => setCamId(e.target.value)}
                        >
                            <option value="">Default camera</option>
                            {cams.map((c) => (
                                <option key={c.deviceId} value={c.deviceId}>
                                    {c.label || "Camera"}
                                </option>
                            ))}
                        </select>
                    )}
                    <label className={fieldLabel + " mt-3"}>
                        Recording resolution
                    </label>
                    <select
                        aria-label="Recording resolution"
                        className={dlgSelect}
                        value={resChoice}
                        onChange={(e) => setResChoice(e.target.value)}
                    >
                        {RESOLUTIONS.map((r) => {
                            const unsupported = !resFitsCamera(
                                parseResolution(r.value),
                                camMax,
                            )
                            return (
                                <option
                                    key={r.value}
                                    value={r.value}
                                    disabled={unsupported}
                                >
                                    {r.label +
                                        (unsupported
                                            ? " — not supported by this camera"
                                            : "")}
                                </option>
                            )
                        })}
                    </select>
                    <div className="mt-1 text-xs text-tiilt-muted">
                        Higher resolutions make larger recordings. Pick Full
                        HD for 360° panorama cameras, or their ring view gets
                        squeezed into the small frame.
                    </div>
                </div>
            )}

            <div>
                <label className={fieldLabel}>Microphone</label>
                {mics.length > 1 && (
                    <select
                        aria-label="Microphone"
                        className={dlgSelect + " mb-2"}
                        value={micId}
                        onChange={(e) => setMicId(e.target.value)}
                    >
                        <option value="">Default microphone</option>
                        {mics.map((m) => (
                            <option key={m.deviceId} value={m.deviceId}>
                                {m.label || "Microphone"}
                            </option>
                        ))}
                    </select>
                )}
                <div className="rounded-xl border border-tiilt-line bg-tiilt-ground/60 px-4 py-3">
                    <div className="text-xs text-tiilt-muted">
                        {channels === 1
                            ? "1 channel (mono)"
                            : channels +
                              " channels detected — tap each mic to find its channel."}
                        {!speaking && " Speak to see the level move."}
                    </div>
                    <div className="mt-2 flex flex-col gap-2">
                        {(levels.length ? levels : [0]).map((lvl, i) => (
                            <div key={i} className="flex items-center gap-2">
                                {channels > 1 ? (
                                    <label className="flex w-20 flex-none cursor-pointer items-center gap-1.5 font-ahamono text-[11px] text-tiilt-muted">
                                        <input
                                            type="radio"
                                            name="channel"
                                            checked={channelChoice === i}
                                            onChange={() => setChannelChoice(i)}
                                        />
                                        ch {i + 1}
                                    </label>
                                ) : (
                                    <span className="w-20 flex-none font-ahamono text-[11px] text-tiilt-muted">
                                        level
                                    </span>
                                )}
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
                        {channels > 1 && (
                            <label className="flex cursor-pointer items-center gap-1.5 text-xs text-tiilt-muted">
                                <input
                                    type="radio"
                                    name="channel"
                                    checked={channelChoice === "mix"}
                                    onChange={() => setChannelChoice("mix")}
                                />
                                Use all channels mixed (default)
                            </label>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

export { InlineDeviceCheck, orientedDims, dimsForMode }
