import { formatSeconds, stringToDate } from "../../globals"

// Pure helpers for the negotiation-coding panel (no React) so the roll-up,
// filters, clock formatting and polling can be unit-tested in node.

export const TEAMS = ["Pat", "Sandy"]   // the Viking default; a session's pod setup may name others
export const UNASSIGNED = "unassigned"

// The team names in play: the run's (server-stamped), else the session's
// pod setup when it has two or more teams, else the Viking default.
export function teamNamesOf(data, session) {
    const fromRun = data && Array.isArray(data.team_names) ? data.team_names.filter(Boolean) : []
    if (fromRun.length >= 2) return fromRun
    const teams = session && session.pod_config && Array.isArray(session.pod_config.teams) ? session.pod_config.teams : []
    const fromSetup = teams.map((t) => t && t.name).filter(Boolean)
    return fromSetup.length >= 2 ? fromSetup : TEAMS
}

// The codebook, in display order. `rollup: false` marks the "nothing coded"
// values that the server's summary does not count (they still get a filter
// chip). Listening is multi-label.
export const DIMENSIONS = [
    {
        key: "emotion",
        label: "Emotion",
        codes: [
            { code: "escalating", label: "Escalating" },
            { code: "defusing", label: "Defusing" },
            { code: "neutral", label: "Neutral" },
        ],
    },
    {
        key: "rip",
        label: "Interests · rights · power",
        codes: [
            { code: "interest", label: "Interest" },
            { code: "right", label: "Right" },
            { code: "power", label: "Power" },
            { code: "none", label: "None", rollup: false },
        ],
    },
    {
        key: "frame",
        label: "Frame",
        codes: [
            { code: "past_blame", label: "Past / blame" },
            { code: "future_problem_solving", label: "Future / problem-solving" },
            { code: "none", label: "None", rollup: false },
        ],
    },
    {
        key: "listening",
        label: "Listening",
        multi: true,
        codes: [
            { code: "open_question", label: "Open question" },
            { code: "closed_question", label: "Closed question" },
            { code: "paraphrase", label: "Paraphrase" },
            { code: "summarize", label: "Summarize" },
            { code: "acknowledge", label: "Acknowledge" },
            { code: "check_understanding", label: "Check understanding" },
            { code: "ask_why", label: "Ask why" },
            { code: "ask_priority", label: "Ask priority" },
            { code: "ask_constraint", label: "Ask constraint" },
            { code: "interrupt", label: "Interrupt" },
        ],
    },
]

const LABELS = {}
for (const d of DIMENSIONS) {
    LABELS[d.key] = {}
    for (const c of d.codes) LABELS[d.key][c.code] = c.label
}

export function codeLabel(dim, code) {
    return (LABELS[dim] && LABELS[dim][code]) || code
}

// The de-escalation timeline, in display order, with what each time means.
export const TIMELINE_FIELDS = [
    {
        key: "first_escalating_s",
        label: "First escalation",
        desc: "The first utterance coded as escalating.",
    },
    {
        key: "peak_escalation_window_start_s",
        label: "Peak escalation",
        desc: "Start of the window with the densest run of escalating utterances.",
    },
    {
        key: "first_sustained_deescalation_s",
        label: "Sustained de-escalation",
        desc: "First point after the peak where the talk stays defusing or neutral.",
    },
    {
        key: "first_future_move_s",
        label: "First future move",
        desc: "The first utterance framed as future problem-solving rather than past blame.",
    },
]

// Seconds -> "mm:ss" ("h:mm:ss" past an hour); "—" when missing.
export function fmtClock(seconds) {
    return formatSeconds(seconds, { invalid: "—" })
}

// Whole seconds -> "1m 05s" style for elapsed time.
export function fmtElapsed(seconds) {
    const s = Math.max(0, Math.floor(seconds || 0))
    const m = Math.floor(s / 60)
    return m > 0 ? `${m}m ${String(s % 60).padStart(2, "0")}s` : `${s}s`
}

// Elapsed since a server timestamp, or null when it cannot be parsed.
export function elapsedSince(iso, now = Date.now()) {
    if (!iso) return null
    const t = stringToDate(String(iso)).getTime()
    if (Number.isNaN(t)) return null
    return fmtElapsed((now - t) / 1000)
}

export function isActiveStatus(status) {
    return status === "queued" || status === "running"
}

// One-line status for the header pill: { tone, text }.
export function describeRun(run, now = Date.now()) {
    if (!run || !run.status) return { tone: "neutral", text: "Never run" }
    switch (run.status) {
        case "queued":
            return { tone: "orange", text: "Queued" }
        case "running": {
            const e = elapsedSince(run.started_at, now)
            return { tone: "orange", text: e ? `Running · ${e}` : "Running" }
        }
        case "done": {
            const when = run.finished_at ? stringToDate(String(run.finished_at)) : null
            const ok = when && !Number.isNaN(when.getTime())
            return {
                tone: "teal",
                text: ok ? `Done · ${when.toLocaleString()}` : "Done",
            }
        }
        case "error":
            return { tone: "danger", text: `Error: ${run.error || "unknown error"}` }
        default:
            return { tone: "neutral", text: String(run.status) }
    }
}

// Every speaker tag the editor should offer: those in the transcript
// (tagCounts, {tag: n}), those the codes mention, and those already assigned.
export function speakerTags(tagCounts, codes, teams) {
    const tags = new Set()
    for (const t of Object.keys(tagCounts || {})) if (t) tags.add(t)
    for (const c of codes || []) if (c && c.speaker_tag) tags.add(c.speaker_tag)
    for (const t of Object.keys(teams || {})) if (t) tags.add(t)
    return [...tags].sort((a, b) => a.localeCompare(b))
}

// Keep only real team assignments (drop unassigned / unknown values).
export function assignedTeams(draft, names = TEAMS) {
    const out = {}
    for (const [tag, team] of Object.entries(draft || {})) {
        if (names.includes(team)) out[tag] = team
    }
    return out
}

export function sameTeams(a, b, names = TEAMS) {
    const x = assignedTeams(a, names)
    const y = assignedTeams(b, names)
    const kx = Object.keys(x).sort()
    const ky = Object.keys(y).sort()
    if (kx.length !== ky.length) return false
    return kx.every((k, i) => k === ky[i] && x[k] === y[k])
}

// An utterance's team: the one the server stamped on it (its device's side
// in a paired run), else its speaker tag's assignment, else unassigned.
export function teamOf(row, teams, names = TEAMS) {
    if (row && names.includes(row.team)) return row.team
    const t = row && teams ? teams[row.speaker_tag] : null
    return names.includes(t) ? t : UNASSIGNED
}

// "Table 3 · Pat" for a pod's negotiation role; null when it has none.
export function roleLabel(group, side) {
    const parts = [group, side].map((p) => (p == null ? "" : String(p).trim())).filter(Boolean)
    return parts.length ? parts.join(" · ") : null
}

function count(team, key) {
    const v = team ? team[key] : 0
    return typeof v === "number" ? v : 0
}

// Summary.by_team -> a table: teams as columns (unassigned only when it has
// utterances), one section per dimension, one row per counted code. Each
// cell is { n, pct } with pct relative to the column's utterance count.
export function rollupTable(summary, names = TEAMS) {
    const byTeam = (summary && summary.by_team) || {}
    const columns = names.map((t) => ({
        key: t,
        label: t,
        utterances: count(byTeam[t], "utterances"),
    }))
    const un = byTeam[UNASSIGNED]
    if (un && count(un, "utterances") > 0) {
        columns.push({ key: UNASSIGNED, label: "Unassigned", utterances: count(un, "utterances") })
    }
    const sections = DIMENSIONS.map((d) => ({
        key: d.key,
        label: d.label,
        rows: d.codes
            .filter((c) => c.rollup !== false)
            .map((c) => ({
                code: c.code,
                label: c.label,
                cells: columns.map((col) => {
                    const team = byTeam[col.key]
                    const n =
                        d.key === "listening"
                            ? count(team && team.listening, c.code)
                            : count(team, c.code)
                    const pct = col.utterances > 0 ? Math.round((100 * n) / col.utterances) : null
                    return { n, pct }
                }),
            })),
    }))
    return { columns, sections }
}

// All codes carried by one utterance as [{dim, code, label}] (including the
// quiet neutral/none values, so filters on them work).
export function utteranceCodes(row) {
    if (!row) return []
    const out = []
    for (const d of DIMENSIONS) {
        const v = row[d.key]
        const list = d.multi ? (Array.isArray(v) ? v : []) : v ? [v] : []
        for (const code of list) out.push({ dim: d.key, code, label: codeLabel(d.key, code) })
    }
    return out
}

const QUIET = new Set(["neutral", "none"])

// Codes worth a badge on the utterance line (neutral / none are implied).
export function badgeCodes(row) {
    return utteranceCodes(row).filter((c) => !QUIET.has(c.code))
}

export function filterKey(dim, code) {
    return `${dim}:${code}`
}

// selected is a Set of "dim:code" keys. Chips within one dimension OR
// together; dimensions AND together ("escalating" + "power" = escalating
// power moves). An empty selection matches everything.
export function matchesFilters(row, selected) {
    if (!selected || selected.size === 0) return true
    const byDim = {}
    for (const key of selected) {
        const i = key.indexOf(":")
        const dim = key.slice(0, i)
        const code = key.slice(i + 1)
        if (!byDim[dim]) byDim[dim] = new Set()
        byDim[dim].add(code)
    }
    const have = utteranceCodes(row)
    return Object.entries(byDim).every(([dim, codes]) =>
        have.some((c) => c.dim === dim && codes.has(c.code)),
    )
}

export function filterCodes(rows, selected) {
    return (rows || []).filter((r) => matchesFilters(r, selected))
}

// Poll while a run is queued/running. `poll` returns a promise; `onResult`
// gets what it resolves to and returns false to stop (run settled). A
// rejected poll is retried on the next tick. Returns stop(): after it, no
// further poll is issued and a poll already in flight is ignored — this is
// what the panel's effect cleanup calls on unmount.
export function startRunPolling({ poll, onResult, intervalMs = 5000 }) {
    let stopped = false
    let handle = null
    const schedule = () => {
        if (stopped) return
        handle = setTimeout(tick, intervalMs)
    }
    const tick = () => {
        if (stopped) return
        Promise.resolve()
            .then(poll)
            .then(
                (result) => {
                    if (stopped) return
                    if (onResult(result) !== false) schedule()
                },
                () => schedule(),
            )
    }
    schedule()
    return () => {
        stopped = true
        if (handle != null) clearTimeout(handle)
        handle = null
    }
}
