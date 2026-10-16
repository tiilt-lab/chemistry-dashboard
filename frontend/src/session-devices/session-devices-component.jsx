import { useEffect, useRef, useState } from "react"
import { useNavigate, useOutletContext } from "react-router-dom"
import { Appheader } from "../header/header-component"
import { SessionTabs } from "../components/session-tabs"
import { StatusPill } from "../components/status-pill"
import { SessionService } from "../services/session-service"
import { startPolling } from "../globals"
import { buildRows, summarize, formatAge, SPEAKING_WINDOW_S, QUIET_WARN_S } from "./live-status"

// The Devices tab: is every group's device connected, is its audio actually
// reaching the server, and when did it last produce speech. Built for the
// instructor walking between breakout rooms: a glance says which room to go
// to. Polls the live endpoint (connection + audio-service presence + last
// transcript) every few seconds while the session runs.
const POLL_MS = 3000
const ENDED_POLL_MS = 30000

function Stat({ label, value, tone }) {
    return (
        <div className="rounded-xl border border-tiilt-line bg-white p-4">
            <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">{label}</div>
            <div className={"mt-1 text-2xl font-semibold " + (tone || "text-tiilt-ink")}>{value}</div>
        </div>
    )
}

function SessionDevicesComponent() {
    const [activeSessionService] = useOutletContext()
    const navigate = useNavigate()
    const [session, setSession] = useState(null)
    const [live, setLive] = useState(null)
    const [problem, setProblem] = useState(null)
    // When this dashboard first saw each device streaming, so a pod that has
    // only just pressed Start is "Listening…" rather than a mic warning.
    const streamingSince = useRef({})
    const [, setTick] = useState(0)

    useEffect(() => {
        if (!activeSessionService) return undefined
        const sub = activeSessionService.sessionSource.subscribe((s) => setSession(s))
        return () => {
            if (sub && sub.unsubscribe) sub.unsubscribe()
        }
    }, [activeSessionService])

    const sessionId = session ? session.id : null
    const recording = session ? !!session.recording : false
    useEffect(() => {
        if (!sessionId) return undefined
        return startPolling(async (signal) => {
            const r = await new SessionService().getSessionLive(sessionId, { signal })
            if (r.status !== 200) {
                setProblem(r.status)
                return false
            }
            const data = await r.json()
            const now = Date.now()
            for (const d of data.devices || []) {
                if (d.streaming && streamingSince.current[d.id] == null) streamingSince.current[d.id] = now
                if (!d.streaming) delete streamingSince.current[d.id]
            }
            setLive(data)
            setProblem(null)
            return true
        }, recording ? POLL_MS : ENDED_POLL_MS)
    }, [sessionId, recording])

    // Ages shown in the table move on between polls.
    useEffect(() => {
        const t = setInterval(() => setTick((x) => x + 1), 5000)
        return () => clearInterval(t)
    }, [])

    const rows = live
        ? buildRows(session && session.pod_config, live.devices, { streamingSince: streamingSince.current, now: Date.now() })
        : []
    const totals = summarize(rows)
    const hasSetup = totals.slots > 0
    const openPod = (d) => navigate(`/sessions/${sessionId}/pods/${d.id}`)

    return (
        <div role="main" className="main-container">
            <Appheader title={"Devices"} leftText={false} rightText={false} nav={() => navigate("/sessions")} escToBack={true} />
            <SessionTabs />
            <div className="toolbar-view-container">
                <div className="min-h-0 grow overflow-y-auto">
                    <div className="mx-auto w-full max-w-6xl px-4 py-8 lg:px-8">
                        <div className="mb-4">
                            <h2 className="text-lg font-semibold text-tiilt-ink">Device monitor</h2>
                            <p className="text-sm text-tiilt-muted">
                                Every group&apos;s device, whether its audio is reaching the server, and when it last produced speech.
                                {recording ? ` Refreshes every ${POLL_MS / 1000} seconds.` : " This session has ended."}
                            </p>
                        </div>

                        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                            <Stat label={hasSetup ? "Slots joined" : "Devices"} value={hasSetup ? `${totals.joined} / ${totals.slots}` : totals.devices} />
                            <Stat label="Streaming audio" value={totals.streaming} />
                            <Stat label="Speaking now" value={totals.speaking} tone="text-tiilt-teal-text" />
                            <Stat label="Need attention" value={totals.attention} tone={totals.attention ? "text-tiilt-orange-text" : undefined} />
                        </div>

                        {problem ? (
                            <div className="mb-4 rounded-lg border border-tiilt-orange/40 bg-tiilt-orange/10 px-3 py-2 text-sm text-tiilt-orange-text">
                                The live status could not be loaded (HTTP {problem}); retrying.
                            </div>
                        ) : null}

                        {live === null ? (
                            <p className="text-sm text-tiilt-muted">Loading…</p>
                        ) : rows.length === 0 ? (
                            <p className="text-sm text-tiilt-muted">No device has joined this session yet.</p>
                        ) : (
                            <div className="overflow-x-auto rounded-xl border border-tiilt-line bg-white">
                                <table className="w-full min-w-[640px] text-sm">
                                    <thead>
                                        <tr className="bg-tiilt-ground/60 text-left text-xs font-semibold tracking-wide text-tiilt-muted uppercase">
                                            <th className="px-3 py-2">{hasSetup ? "Slot" : "Group"}</th>
                                            <th className="px-3 py-2">Device</th>
                                            <th className="px-3 py-2">Status</th>
                                            <th className="px-3 py-2">Last speech</th>
                                            <th className="px-3 py-2 text-right">Utterances</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {rows.map((r, i) => {
                                            const d = r.device
                                            const attention = r.state.attention || (r.clock && r.clock.attention)
                                            return (
                                                <tr
                                                    key={d ? `d${d.id}` : `s${i}`}
                                                    onClick={d ? () => openPod(d) : undefined}
                                                    title={d ? `Open ${d.name}` : undefined}
                                                    className={
                                                        "border-t border-tiilt-line " +
                                                        (d ? "cursor-pointer hover:bg-tiilt-soft/50 " : "") +
                                                        (attention ? "border-l-4 border-l-tiilt-orange bg-tiilt-orange/5" : "border-l-4 border-l-transparent")
                                                    }
                                                >
                                                    <td className="px-3 py-2 font-semibold whitespace-nowrap text-tiilt-ink">
                                                        {r.first ? r.slotLabel : <span className="text-xs font-normal text-tiilt-muted">extra device</span>}
                                                    </td>
                                                    <td className="px-3 py-2 whitespace-nowrap">
                                                        {d ? d.name : <span className="text-tiilt-muted">—</span>}
                                                    </td>
                                                    <td className="px-3 py-2">
                                                        <div className="flex flex-col gap-0.5">
                                                            <span>
                                                                <StatusPill tone={r.state.tone} pulse={!!r.state.pulse} dot={!!r.state.dot} title={r.state.hint} className="text-[11px]">
                                                                    {r.state.label}
                                                                </StatusPill>
                                                            </span>
                                                            {r.state.attention ? <span className="text-xs text-tiilt-muted">{r.state.hint}</span> : null}
                                                            {r.clock ? (
                                                                <span
                                                                    title={r.clock.hint}
                                                                    className={"text-xs " + (r.clock.attention ? "font-semibold text-tiilt-orange" : "text-tiilt-muted")}
                                                                >
                                                                    {r.clock.label}
                                                                </span>
                                                            ) : null}
                                                        </div>
                                                    </td>
                                                    <td className="px-3 py-2 whitespace-nowrap text-tiilt-muted">
                                                        {d && d.last_speech_age != null ? `${formatAge(d.last_speech_age)} ago` : "—"}
                                                    </td>
                                                    <td className="px-3 py-2 text-right whitespace-nowrap text-tiilt-muted">
                                                        {d ? d.utterances : "—"}
                                                    </td>
                                                </tr>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        <p className="mt-4 text-xs text-tiilt-muted">
                            Speaking: speech recognised in the last {SPEAKING_WINDOW_S} s. Receiving audio: streaming, last speech under {QUIET_WARN_S / 60} min ago.
                            No speech: audio is streaming but nothing is recognised, so check the microphone. Joined, not recording: connected but Start recording has not been pressed.
                            Speech shows here 15 to 25 seconds after it is spoken.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}

export { SessionDevicesComponent }
