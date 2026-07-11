import React, { useEffect, useRef, useState } from "react"
import { dlgSelect, dlgPrimary, dlgError } from "../components/dialog-styles"

// Pre-join device check: after the join form and before connecting, show
// what the chosen camera and microphone actually capture — live camera
// preview, a level meter per audio channel, and (for multi-channel rigs
// like 2-transmitter lav receivers) a picker for which channel to record.
// The selections feed the real capture: deviceIds go into getUserMedia and
// the channel choice is applied by a ChannelSplitter before the audio
// worklet.
//
// Echo cancellation / noise suppression are disabled here and during the
// session whenever a specific channel is chosen — several platforms force
// a mono downmix when they are on, which destroys channel separation.
const MAX_CHANNELS = 8

const fieldLabel = "mb-1.5 block text-left text-sm font-semibold text-tiilt-ink"

function DeviceCheckPage({ joinwith, onConfirm, onBack }) {
    const wantsVideo = joinwith === "Video" || joinwith === "Videocartoonify"
    const [error, setError] = useState("")
    const [mics, setMics] = useState([])
    const [cams, setCams] = useState([])
    const [micId, setMicId] = useState("")
    const [camId, setCamId] = useState("")
    const [channels, setChannels] = useState(1)
    const [levels, setLevels] = useState([])
    const [channelChoice, setChannelChoice] = useState("mix") // "mix" | index
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

    const openPreview = async (audioDeviceId, videoDeviceId) => {
        stopPreview()
        setError("")
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
                          facingMode: "user",
                          width: 640,
                          height: 480,
                          ...(videoDeviceId ? { deviceId: { exact: videoDeviceId } } : {}),
                      }
                    : false,
            }
            const stream = await navigator.mediaDevices.getUserMedia(constraints)
            streamRef.current = stream

            if (wantsVideo && videoRef.current) {
                videoRef.current.srcObject = stream
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
    }, [micId, camId])

    const speaking = levels.some((l) => l > 0.02)

    return (
        <div className="mx-auto flex w-full max-w-md grow flex-col gap-4 overflow-y-auto px-4 py-6">
            <div>
                <div className="text-lg font-semibold text-tiilt-ink">
                    Check your devices
                </div>
                <div className="mt-1 text-sm text-tiilt-muted">
                    Make sure the recording will look and sound right before
                    joining.
                </div>
            </div>

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

            <div className="mt-2 flex flex-col gap-2">
                <button
                    className={dlgPrimary + " w-full"}
                    onClick={() => {
                        stopPreview()
                        onConfirm({
                            audioDeviceId: micId || null,
                            videoDeviceId: camId || null,
                            channelIndex:
                                channelChoice === "mix" ? null : channelChoice,
                        })
                    }}
                >
                    Looks good — join session
                </button>
                <button
                    className="w-full cursor-pointer rounded-lg border border-tiilt-line bg-white px-3 py-2.5 text-sm font-semibold text-tiilt-ink transition hover:border-tiilt"
                    onClick={() => {
                        stopPreview()
                        onBack()
                    }}
                >
                    Back
                </button>
            </div>
        </div>
    )
}

export { DeviceCheckPage }
