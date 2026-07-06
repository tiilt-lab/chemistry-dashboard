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
    // null = not enough signal yet; true = channels carry the same signal
    // (mono duplicated onto both); false = genuinely distinct channels.
    const [duplicated, setDuplicated] = useState(null)
    // Channels that never carried signal while others did (mono link
    // advertised as stereo): [indexes], or null while unknown.
    const [deadChannels, setDeadChannels] = useState(null)
    const statsRef = useRef(null)
    const cleanupRef = useRef(null)

    const stop = () => {
        if (cleanupRef.current) {
            cleanupRef.current()
            cleanupRef.current = null
        }
        setState("idle")
        setLevels([])
        setDuplicated(null)
        setDeadChannels(null)
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
            const bufs = analysers.map(() => new Float32Array(512))
            statsRef.current = { frames: 0, a: 0, b: 0, d: 0, peaks: new Array(n).fill(0) }
            const tick = () => {
                const next = analysers.map((an, i) => {
                    an.getFloatTimeDomainData(bufs[i])
                    let sum = 0
                    for (let k = 0; k < bufs[i].length; k++)
                        sum += bufs[i][k] * bufs[i][k]
                    return Math.sqrt(sum / bufs[i].length)
                })
                setLevels(next)
                // Duplicate-channel detection: accumulate the energy of the
                // (ch1 - ch2) difference while there is actual signal. A
                // receiver in mono mode mirrors one mix onto both channels,
                // which looks like "2 channels" but gives no separation.
                if (n >= 2 && Math.max(...next) > 0.02) {
                    const s = statsRef.current
                    let d = 0
                    for (let k = 0; k < bufs[0].length; k++) {
                        const diff = bufs[0][k] - bufs[1][k]
                        d += diff * diff
                    }
                    s.a += next[0] * next[0] * bufs[0].length
                    s.b += next[1] * next[1] * bufs[1].length
                    s.d += d
                    next.forEach((v, i) => {
                        if (v > s.peaks[i]) s.peaks[i] = v
                    })
                    s.frames += 1
                    if (s.frames >= 40) {
                        const loudest = Math.max(...s.peaks)
                        const dead = s.peaks
                            .map((p, i) => (p < Math.max(0.01, loudest * 0.05) ? i : -1))
                            .filter((i) => i >= 0)
                        setDeadChannels(dead)
                        const ratio = Math.sqrt(
                            s.d / (Math.max(s.a, s.b) + 1e-9),
                        )
                        // A dead channel also makes the channels "different";
                        // only call it duplicated when both actually carry audio.
                        setDuplicated(dead.length === 0 && ratio < 0.2)
                    }
                }
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
                            ? "1 channel (mono) — speakers will be identified by voice"
                            : duplicated === null && !deadChannels
                              ? `${channels} channels reported — testing whether this is true stereo or mono…`
                              : duplicated === false && deadChannels && deadChannels.length === 0
                                ? `${channels} channels — true stereo, one mic per person will work`
                                : `${channels} channels reported — but effectively mono`}
                    </div>
                    {channels > 1 && deadChannels && deadChannels.length > 0 ? (
                        <div className="rounded-md bg-tiilt-orange/15 px-3 py-2 text-xs leading-relaxed text-tiilt-orange-text">
                            Only{" "}
                            {channels - deadChannels.length === 1
                                ? "one channel is"
                                : `${channels - deadChannels.length} channels are`}{" "}
                            carrying audio — the rest stayed silent, so this
                            connection is effectively mono. Both mics are being
                            mixed onto one channel by the receiver; per-mic
                            attribution won't work over this link.
                        </div>
                    ) : null}
                    {channels > 1 && duplicated === true ? (
                        <div className="rounded-md bg-tiilt-orange/15 px-3 py-2 text-xs leading-relaxed text-tiilt-orange-text">
                            Both channels are carrying the same signal, so this
                            behaves like a single mic. If your receiver has a
                            mono/stereo (track) switch, set it to stereo and
                            check again.
                        </div>
                    ) : null}
                    {channels > 1 && duplicated === false && deadChannels && deadChannels.length === 0 ? (
                        <div className="rounded-md bg-tiilt-teal/15 px-3 py-2 text-xs leading-relaxed text-tiilt-teal-text">
                            Channels are carrying distinct signals — per-mic
                            attribution will work on this setup.
                        </div>
                    ) : null}
                    {channels > 1 && duplicated === null && !deadChannels ? (
                        <div className="text-[11px] text-tiilt-muted">
                            Speak or tap a mic for a moment to test whether the
                            channels are really separate…
                        </div>
                    ) : null}
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
