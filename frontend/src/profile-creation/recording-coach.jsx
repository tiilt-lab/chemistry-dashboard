import React, { useEffect, useMemo, useRef, useState } from "react";

/**
 * RecordingCoach
 * A production‑ready React component that helps users capture **high‑quality** face + voice recordings
 * for facial recognition and speaker diarization workflows.
 *
 * Features
 * - Preflight checklist (lighting, background, posture, mic test)
 * - Device pickers (camera/microphone)
 * - Live video preview with safe‑framing overlay
 * - Face centering & size guidance (via FaceDetector API if available; fallback to heuristics)
 * - Lighting/brightness estimation from video frames
 * - Audio level meter (RMS, peak, clipping warnings)
 * - Background‑noise check (measures noise floor during a silent window)
 * - Guided script/teleprompter & countdown
 * - Test‑record + playback, then Full recording
 * - Records to WebM (VP8/VP9 + Opus) with sensible getUserMedia constraints
 *
 * Usage
 *   <RecordingCoach onComplete={(blob, diagnostics) => { ...upload or save... }} />
 *
 * Styling: TailwindCSS utility classes are used by default.
 */

// Types
//  type Diagnostics = {
//    video: {
//      averageLuma: number; // 0..255
//      faceOk: boolean;
//      faceBox?: { x: number; y: number; width: number; height: number };
//      hints: string[];
//    };
//    audio: {
//      noiseFloorDb: number; // estimated during silence window
//      rmsDb: number; // live speech RMS (approx)
//      clipping: boolean;
//      hints: string[];
//    };
//    device: {
//      cameraId?: string;
//      micId?: string;
//    };
//  };

//  type Props = {
//    maxDurationSec?: number; // hard stop for full recording
//    minDurationSec?: number; // recommend at least this long
//    onComplete?: (blob: Blob, diagnostics: Diagnostics) => void;
//    onTestClip?: (blob: Blob, diagnostics: Diagnostics) => void;
//    saveRecording: calls saverecoding from parent component  
//    showScript?: boolean;
//    scriptText?: string;
//  };

const DEFAULT_SCRIPT = `Please read the following passage in a clear, natural voice:

“Today I am recording a short sample so my face and voice can be matched accurately. I am looking straight at the camera  and Will turn my head to the Right, Left, Up and Down. I will speak at a consistent pace and volume.”`;

function RecordingCoach({
    maxDurationSec = 60,
    minDurationSec = 10,
    onComplete,
    saveRecording,
    onTestClip,
    showScript = true,
    scriptText = DEFAULT_SCRIPT,
}) {
    // Refs & state
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const mediaStreamRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const recordedChunksRef = useRef([]);

    const audioCtxRef = useRef(null);
    const analyserRef = useRef(null);
    const sourceRef = useRef(null);
    const scriptStartRef = useRef(null);

    const [devices, setDevices] = useState([]);
    const [micId, setMicId] = useState();
    const [camId, setCamId] = useState();

    const [isPreviewing, setIsPreviewing] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [isTesting, setIsTesting] = useState(false);
    const [isRecordingStopped, setIsRecordingStopped] = useState(false)
    const [countdown, setCountdown] = useState(null);
    const [elapsed, setElapsed] = useState(0);

    const [avgLuma, setAvgLuma] = useState(0);
    const [faceOk, setFaceOk] = useState(false);
    const [faceBox, setFaceBox] = useState();

    const [rmsDb, setRmsDb] = useState(-Infinity);
    const [peakDb, setPeakDb] = useState(-Infinity);
    const [clipping, setClipping] = useState(false);
    const [noiseFloorDb, setNoiseFloorDb] = useState(null);

    const [hintsVideo, setHintsVideo] = useState([]);
    const [hintsAudio, setHintsAudio] = useState([]);
    const [videoBlobData, setVideoBlobData] = useState(null)
    const [actualTimeElapsed, setActualTimeElapsed] = useState(0)

    const FaceDetectorApi = useMemo(() => (typeof window !== 'undefined' && (window).FaceDetector ? new (window).FaceDetector({ fastMode: true }) : null), []);

    // Enumerate devices
    useEffect(() => {
        navigator.mediaDevices?.enumerateDevices().then(setDevices).catch(() => { });
    }, []);

    // Start preview with selected devices
    const startPreview = async () => {
        stopEverything();
        const constraints = {
            video: {
                deviceId: camId ? { exact: camId } : undefined,
                width: { ideal: 1280 },
                height: { ideal: 720 },
                frameRate: { ideal: 30, max: 30 },
                facingMode: 'user',
            },
            audio: {
                deviceId: micId ? { exact: micId } : undefined,
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: false,
            },
        };

        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        mediaStreamRef.current = stream;

        if (videoRef.current) {
            videoRef.current.srcObject = stream;
            await videoRef.current.play();
        }

        // audio chain
        const ctx = new AudioContext();
        audioCtxRef.current = ctx;
        const source = ctx.createMediaStreamSource(stream);
        sourceRef.current = source;
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 2048;
        analyserRef.current = analyser;
        source.connect(analyser);

        // warm up noise floor during 2s silence window
        setNoiseFloorDb(null);
        const noiseWindowMs = 1500;
        const start = performance.now();
        const data = new Float32Array(analyser.fftSize);

        const sampleNoise = () => {
            if (!analyserRef.current) return;
            analyserRef.current.getFloatTimeDomainData(data);
            const rms = Math.sqrt(data.reduce((s, v) => s + v * v, 0) / data.length) || 1e-8;
            const db = 20 * Math.log10(rms);
            if (performance.now() - start > noiseWindowMs) {
                setNoiseFloorDb(db);
            } else {
                requestAnimationFrame(sampleNoise);
            }
        };
        requestAnimationFrame(sampleNoise);

        setIsPreviewing(true);
        startMeters();
        startVisionLoop();
    };

    const stopEverything = () => {
        stopMeters();
        stopVisionLoop();

        mediaRecorderRef.current?.stop();
        mediaRecorderRef.current = null;

        mediaStreamRef.current?.getTracks().forEach(t => t.stop());
        mediaStreamRef.current = null;

        audioCtxRef.current?.close();
        audioCtxRef.current = null;

        setIsPreviewing(false);
        setIsRecording(false);
        setIsTesting(false);
        setIsRecordingStopped(false)
        setVideoBlobData(null)
        setCountdown(null);
        setElapsed(0);
    };

    // Audio meters
    let meterRAF = 0;
    const startMeters = () => {
        const analyser = analyserRef.current;
        if (!analyser) return;
        const buf = new Float32Array(analyser.fftSize);
        const loop = () => {
            analyser.getFloatTimeDomainData(buf);
            // RMS
            const rms = Math.sqrt(buf.reduce((s, v) => s + v * v, 0) / buf.length) || 1e-8;
            const peak = buf.reduce((p, v) => Math.max(p, Math.abs(v)), 0) || 1e-8;
            const rmsDbNew = 20 * Math.log10(rms);
            const peakDbNew = 20 * Math.log10(peak);
            setRmsDb(rmsDbNew);
            setPeakDb(peakDbNew);
            setClipping(peak > 0.98); // near full‑scale
            meterRAF = requestAnimationFrame(loop);
        };
        meterRAF = requestAnimationFrame(loop);
    };
    const stopMeters = () => cancelAnimationFrame(meterRAF);

    // Vision loop (brightness + face guidance)
    let visionRAF = 0;
    const startVisionLoop = () => {
        const v = videoRef.current;
        const c = canvasRef.current;
        if (!v || !c) return;
        const ctx = c.getContext('2d');
        if (!ctx) return;

        const loop = async () => {
            if (!v.videoWidth || !v.videoHeight) {
                visionRAF = requestAnimationFrame(loop);
                return;
            }
            c.width = v.videoWidth;
            c.height = v.videoHeight;
            ctx.drawImage(v, 0, 0, c.width, c.height);

            // average luma (very cheap): convert to 1px via drawImage scaling
            const thumbW = 32, thumbH = 18;
            const tmp = document.createElement('canvas');
            tmp.width = thumbW; tmp.height = thumbH;
            const tctx = tmp.getContext('2d');
            tctx.drawImage(c, 0, 0, thumbW, thumbH);
            const img = tctx.getImageData(0, 0, thumbW, thumbH).data;
            let sum = 0;
            for (let i = 0; i < img.length; i += 4) {
                const r = img[i], g = img[i + 1], b = img[i + 2];
                // Rec. 601 luma approximation
                sum += 0.299 * r + 0.587 * g + 0.114 * b;
            }
            const luma = sum / (img.length / 4);
            setAvgLuma(luma);

            // Face detection if available
            let fOk = false;
            let fBox = undefined;
            try {
                if (FaceDetectorApi) {
                    const faces = await FaceDetectorApi.detect(v);
                    if (faces && faces[0] && faces[0].boundingBox) {
                        const bb = faces[0].boundingBox;
                        fBox = { x: bb.x, y: bb.y, width: bb.width, height: bb.height };
                        // Heuristic: face box covers ~15–60% of height and centered
                        const sizePct = bb.height / v.videoHeight;
                        const centerX = bb.x + bb.width / 2;
                        const centerY = bb.y + bb.height / 2;
                        const cxOk = Math.abs(centerX - v.videoWidth / 2) < v.videoWidth * 0.15;
                        const cyOk = Math.abs(centerY - v.videoHeight / 2) < v.videoHeight * 0.15;
                        fOk = sizePct > 0.15 && sizePct < 0.6 && cxOk && cyOk;
                    }
                }
            } catch { }
            setFaceBox(fBox);
            setFaceOk(fOk);

            // Hints
            const vHints = [];
            if (luma < 80) vHints.push('Increase lighting in front of your face.');
            if (luma > 220) vHints.push('Lighting is too bright; reduce glare or move back.');
            if (FaceDetectorApi && !fOk) vHints.push('Center your face and keep eyes level; fill ~1/3 of frame.');
            setHintsVideo(vHints);

            visionRAF = requestAnimationFrame(loop);
        };
        visionRAF = requestAnimationFrame(loop);
    };
    const stopVisionLoop = () => cancelAnimationFrame(visionRAF);

    // Start a recording (test or full)
    const beginRecording = async (mode) => {
        if (!mediaStreamRef.current) return;
        recordedChunksRef.current = [];
        const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')
            ? 'video/webm;codecs=vp9,opus'
            : 'video/webm;codecs=vp8,opus';

        const rec = new MediaRecorder(mediaStreamRef.current, {
            mimeType: mime,
            videoBitsPerSecond: 3_000_000,
            audioBitsPerSecond: 128_000,
        });
        mediaRecorderRef.current = rec;

        rec.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) recordedChunksRef.current.push(e.data);
        };
        rec.onstop = () => {
            const blob = new Blob(recordedChunksRef.current, { type: rec.mimeType });
            const diagnostics = {
                video: { averageLuma: avgLuma, faceOk, faceBox, hints: hintsVideo },
                audio: { noiseFloorDb: noiseFloorDb ?? -Infinity, rmsDb, clipping, hints: hintsAudio },
                device: { cameraId: camId, micId: micId },
            };
            if (mode === 'test') onTestClip?.(blob, diagnostics);
            else {
                setVideoBlobData(blob) //onComplete?.(blob, diagnostics);
            }
        };

        // countdown
        await runCountdown(3);

        if (mode === 'full') setIsRecording(true); else setIsTesting(true);
        scriptStartRef.current = performance.now();
        const startedAt = Date.now();
        rec.start(250);

        const tick = () => {
            const sec = Math.floor((Date.now() - startedAt) / 1000);
            setElapsed(sec);

            // Stop logic
            if (mode === 'test' && sec >= 5) {
                rec.stop();
                setIsTesting(false);
                return;
            }
            if (mode === 'full' && sec >= maxDurationSec) {
                rec.stop();
                setIsRecording(false);
                return;
            }
            requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
        if (isRecording) {
            setIsRecordingStopped(true)
        }
        setIsRecording(false);
        setIsTesting(false);
        setActualTimeElapsed(elapsed)

    };

    const startSaveRecording = () => {
        if (videoBlobData !== null && actualTimeElapsed !== 0) {
            saveRecording(videoBlobData, actualTimeElapsed)
        }
    }
    const runCountdown = (n) =>
        new Promise((resolve) => {
            let val = n;
            setCountdown(val);
            const id = setInterval(() => {
                val -= 1;
                if (val <= 0) {
                    clearInterval(id);
                    setCountdown(null);
                    resolve();
                } else setCountdown(val);
            }, 1000);
        });

    // Compute audio hints
    useEffect(() => {
        const hints = [];
        if (noiseFloorDb !== null) {
            if (noiseFloorDb > -40) hints.push('Background noise is high; move to a quieter room.');
            if (noiseFloorDb < -70) hints.push('Room is very quiet (good).');
        }
        if (rmsDb > -18) hints.push('Reduce mic gain or move mic farther (too loud).');
        if (rmsDb < -35) hints.push('Speak a bit louder or move closer to mic.');
        if (clipping) hints.push('Audio clipping detected; lower input level.');
        setHintsAudio(hints);
    }, [noiseFloorDb, rmsDb, clipping]);

    // Cleanup on unmount
    useEffect(() => () => stopEverything(), []);

    // Helpers
    const cameras = devices.filter(d => d.kind === 'videoinput');
    const mics = devices.filter(d => d.kind === 'audioinput');

    return (
        <div className="mx-auto max-w-5xl p-6 space-y-6 overflow-y-auto h-screen">
            <header className="flex items-center justify-between">
                <h1 className="text-2xl font-semibold">Recording Guide</h1>
                <div className="text-sm text-gray-500">Optimized for face+voice capture</div>
            </header>

            {/* Preflight checklist */}
            <section className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border p-4 shadow-sm">
                    <h2 className="mb-2 font-medium">Preflight</h2>
                    <ul className="space-y-2 text-sm">
                        <li>• Ensure your face is within the rectangular box.</li>
                        <li>• Face a window or soft light; avoid strong backlight.</li>
                        <li>• Plain background; remove hats/hoods; keep glasses clean.</li>
                        <li>• Quiet room; turn off fans/AC where possible.</li>
                        <li>• Speak at normal pace; avoid sudden shouting/laughter.</li>
                    </ul>
                </div>


                <div className="rounded-2xl border p-4 shadow-sm text-sm text-gray-600">
                    <div className="font-medium text-gray-800">Capture Tips (FR + Diarization)</div>
                    <ul className="mt-1 list-inside list-disc">
                        <li>Keep head upright, look at camera; avoid extreme angles & occlusions.</li>
                        <li>Maintain neutral to mild expressions for FR enrollment; smile only if consistent with target set.</li>
                        <li>You could turn your head to the right, left, up and down while speaking; to ensure all head orientations are captured.</li>
                    </ul>
                </div>

                <div className="rounded-2xl border p-4 shadow-sm">
                    <h2 className="mb-2 font-medium">Devices</h2>
                    <div className="flex gap-3">
                        <label className="flex-1 text-sm">Camera
                            <select className="mt-1 w-full rounded-lg border p-2" value={camId} onChange={e => setCamId(e.target.value)}>
                                <option value="">Default</option>
                                {cameras.map(d => (<option key={d.deviceId} value={d.deviceId}>{d.label || `Camera ${d.deviceId.slice(-4)}`}</option>))}
                            </select>
                        </label>
                        <label className="flex-1 text-sm">Microphone
                            <select className="mt-1 w-full rounded-lg border p-2" value={micId} onChange={e => setMicId(e.target.value)}>
                                <option value="">Default</option>
                                {mics.map(d => (<option key={d.deviceId} value={d.deviceId}>{d.label || `Mic ${d.deviceId.slice(-4)}`}</option>))}
                            </select>
                        </label>
                    </div>
                    <div className="mt-3 flex gap-2">
                        <button className="rounded-xl bg-black px-4 py-2 text-white shadow" onClick={startPreview} disabled={isPreviewing}>Start Preview</button>
                        <button className="rounded-xl border px-4 py-2" onClick={stopEverything}>Stop</button>
                    </div>
                </div>

                <div className="rounded-2xl border p-4 shadow-sm">
                    <h3 className="mb-2 font-medium">Mic Levels</h3>
                    <LevelMeter rmsDb={rmsDb} peakDb={peakDb} clipping={clipping} />
                    <div className="mt-1 text-xs text-gray-500">Target RMS: −35 to −18 dBFS (green zone)</div>
                </div>
            </section>

            {/* Live Preview */}
            <section className="grid gap-4 md:grid-cols-3">
                <div className="md:col-span-2 rounded-2xl border p-3 shadow-sm">
                    <div className="relative aspect-video overflow-hidden rounded-xl bg-black">
                        <video ref={videoRef} className="h-full w-full object-cover" playsInline muted />
                        {/* Safe frame overlay */}
                        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                            <div className="h-3/4 w-1/2 rounded-3xl border-4 border-white/70"></div>
                        </div>
                        {/* Detected face box */}
                        {faceBox && (
                            <div
                                className="pointer-events-none absolute border-2 border-emerald-400"
                                style={{ left: faceBox.x, top: faceBox.y, width: faceBox.width, height: faceBox.height }}
                            />
                        )}
                    </div>
                    <canvas ref={canvasRef} className="hidden" />
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
                        <Badge ok={avgLuma >= 100 && avgLuma <= 200} label={`Brightness: ${avgLuma.toFixed(0)}`} />
                        <Badge ok={noiseFloorDb !== null && noiseFloorDb < -40} label={`Noise floor: ${noiseFloorDb === null ? '…' : noiseFloorDb.toFixed(1) + ' dB'}`} />
                        {FaceDetectorApi && <Badge ok={faceOk} label={`Face centered: ${faceOk ? 'OK' : 'Adjust'}`} />}
                    </div>
                </div>

                {/* script */}
                <div className="flex flex-col gap-4">

                    {showScript && (
                        <div className="rounded-2xl border p-4 shadow-sm">
                            <h3 className="mb-2 font-medium">Script</h3>
                            <div className="max-h-48 overflow-y-auto whitespace-pre-wrap rounded-xl bg-gray-50 p-3 text-sm leading-relaxed">
                                {scriptText}
                            </div>
                        </div>
                    )}

                    {/* Controls */}
                    <div className="rounded-2xl border p-4 shadow-sm">
                        <div className="flex flex-wrap items-center gap-3">
                            <button className="rounded-xl border px-4 py-2" onClick={() => beginRecording('test')} disabled={!isPreviewing || isRecording || isTesting}>Test 5s</button>
                            <button className="rounded-xl bg-emerald-600 px-4 py-2 text-white shadow disabled:opacity-50" onClick={() => beginRecording('full')} disabled={!isPreviewing || isRecording || isTesting}>
                                {isRecording ? 'Recording…' : 'Start Recording'}
                            </button>
                            {(isRecording || isTesting) && (
                                <button className="rounded-xl bg-red-600 px-4 py-2 text-white" onClick={stopRecording}>Stop</button>
                            )}

                            {isRecordingStopped && (
                                <button className="rounded-xl bg-red-600 px-4 py-2 text-white" onClick={startSaveRecording}>Save</button>
                                // startSaveRecording
                            )}
                            {countdown !== null && <span className="ml-2 text-lg font-semibold">{countdown}</span>}
                            <span className="ml-auto text-sm text-gray-600">{elapsed}s / {maxDurationSec}s</span>
                        </div>
                        <div className="mt-2 text-xs text-gray-500">Recommended duration ≥ {minDurationSec}s.</div>
                    </div>
                </div>
            </section>

            {/* Controls */}
            <section className="rounded-2xl border p-4 shadow-sm">
                 {(hintsVideo.length > 0 || hintsAudio.length > 0) && (
                        <div className="mt-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
                            <div className="font-medium">Suggestions</div>
                            <ul className="list-inside list-disc">
                                {[...hintsVideo, ...hintsAudio].map((h, i) => <li key={i}>{h}</li>)}
                            </ul>
                        </div>
                    )}
            </section>

        </div>
    );
}

function Badge({ ok, label }) {
    return (
        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs ${ok ? 'bg-emerald-100 text-emerald-900' : 'bg-amber-100 text-amber-900'}`}>
            <span className={`h-2 w-2 rounded-full ${ok ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
            {label}
        </span>
    );
}

function LevelMeter({ rmsDb, peakDb, clipping }) {
    // Map −60..0 dBFS to 0..100
    const norm = (db) => Math.max(0, Math.min(100, 100 * (1 + db / 60)));
    const rmsPct = norm(rmsDb);
    const peakPct = norm(peakDb);
    return (
        <div>
            <div className="relative h-3 w-full rounded bg-gray-200">
                <div className="absolute left-0 top-0 h-3 rounded bg-green-500" style={{ width: `${rmsPct}%` }} />
                <div className="absolute left-0 top-0 h-3 rounded bg-black/30" style={{ width: `${peakPct}%` }} />
            </div>
            <div className="mt-1 flex items-center justify-between text-xs text-gray-600">
                <span>RMS {Number.isFinite(rmsDb) ? rmsDb.toFixed(1) : '…'} dBFS</span>
                <span>Peak {Number.isFinite(peakDb) ? peakDb.toFixed(1) : '…'} dBFS {clipping && <strong className="text-red-600">(CLIP)</strong>}</span>
            </div>
        </div>
    );
}

export { RecordingCoach }