// File for generic functions.

// Date format expected 'YYYY-MM-DD HH:MM:SS.mmmmmm UTC'
export function stringToDate(dateString) {
  let date = new Date(dateString); // Chrome
  if (isNaN(date.getTime())) { // Firefox
    date = new Date(dateString.replace(' UTC', 'Z'));
  }
  if (isNaN(date.getTime())) { // Safari
    date = new Date(dateString.replace(' ', 'T').replace(' UTC', 'Z'));
  }
  return date;
}

// One date format app-wide ("Jul 5, 2026") — there used to be three.
export function formatDate(date) {
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function degrees_to_radians(degrees) {
  return degrees * (Math.PI / 180);
}

export function sin(degrees) {
  let result = Math.round(Math.sin(degrees_to_radians(degrees)) * 1000) / 1000;
  if (result === 0) {
      result = Math.abs(result);
  }
  return result;
}

export function cos(degrees) {
  let result = Math.round(Math.cos(degrees_to_radians(degrees)) * 1000) / 1000;
  if (result === 0) {
      result = Math.abs(result);
  }
  return result;
}

// Canonical seconds -> clock formatter. Options let it express the variants
// that used to be reimplemented across components/models:
//   padLeading  (default true)  pad the largest shown unit to 2 digits
//   alwaysHours (default false)  show hours even when 0 (HH:MM:SS)
//   invalid     (default none)   value to return for null/NaN input
export function formatSeconds(seconds, opts = {}) {
  const { padLeading = true, alwaysHours = false, invalid } = opts || {};
  if (invalid !== undefined && (seconds == null || Number.isNaN(Number(seconds)))) {
    return invalid;
  }
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = Math.floor(total % 60);
  const ss = s.toString().padStart(2, '0');
  if (alwaysHours || h > 0) {
    const hh = padLeading ? h.toString().padStart(2, '0') : h.toString();
    const mm = m.toString().padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
  }
  const mm = padLeading ? m.toString().padStart(2, '0') : m.toString();
  return `${mm}:${ss}`;
}

// Keep only the rows for one pod (session device) and sort them ascending by
// a time key. This filter+sort was copy-pasted into every live-stream
// subscriber (transcripts by start_time, video metrics by time_stamp); the
// subscriber-leak bug that pattern carried was fixed independently three
// times, so it belongs in one place.
export function filterSortByDevice(items, sessionDeviceId, sortKey) {
  const id = parseInt(sessionDeviceId, 10);
  return items
    .filter((x) => x.session_device_id === id)
    .sort((a, b) => (a[sortKey] > b[sortKey] ? 1 : -1));
}

export function similarityToRGB(similarity) {
  const color = Math.floor(230 - (230 * similarity / 100));
  return 'rgb(' + color + ',' + color + ', 255)';
}

// Canonical per-speaker colors: alphabetical name order -> palette index, so
// every panel (transcript, video analytics, dynamics) gives the same person
// the same color regardless of each panel's data ordering. Presentation only.
// Brand hexes for canvas/chart configs (CSS vars don't resolve in canvas).
export const BRAND = {
  purple: "#3a2163",
  pink: "#ec008c",
  danger: "#b3261e",
  muted: "#675e7d",
}
// Dark-surface equivalents; canvas charts can't read CSS vars, so chart
// configs should resolve through brandColor() at render time.
export const BRAND_DARK = {
  purple: "#a58cd6",
  pink: "#f24aa8",
  danger: "#e5766f",
  muted: "#a89fc0",
}
export function brandColor(key) {
  return (isDarkTheme() ? BRAND_DARK : BRAND)[key]
}

export const SPEAKER_PALETTE = [
    "#3a2163",
    "#00a79d",
    "#c0007a",
    "#b26a00",
    "#4d7c1f",
    "#2e3192",
    "#b3261e",
    "#6d28d9",
]
// Same hues lightened for dark surfaces — the light palette is deep
// ink-on-white colors that all but vanish on a dark background.
export const SPEAKER_PALETTE_DARK = [
    "#b39ddb",
    "#2dbdb3",
    "#f06eb5",
    "#e8a13c",
    "#9ccc65",
    "#8f96e8",
    "#e5766f",
    "#b794f6",
]
export function isDarkTheme() {
    return (
        typeof document !== "undefined" &&
        document.documentElement.classList.contains("dark")
    )
}
// A negotiation's two teams: cool shades for the first team, warm for the
// second, so a glance tells the side and the shade tells the person. A
// speaker's shade is their place on the team (the server's speaker_labels
// order: Pat 1 is the first cool shade, Sandy 2 the second warm one).
export const TEAM_PALETTES = [
    ["#312e81", "#6d28d9", "#2563eb", "#0e7490", "#4338ca"],
    ["#9a3412", "#b91c1c", "#b45309", "#be185d", "#c2410c"],
]
export const TEAM_PALETTES_DARK = [
    ["#a5b4fc", "#c4b5fd", "#93c5fd", "#67e8f9", "#818cf8"],
    ["#fdba74", "#fca5a5", "#fcd34d", "#f9a8d4", "#fb923c"],
]
// The group payload's speakers (speaker_labels: [{alias, label, team,
// team_index, index}]) as a lookup by alias: {label, team, teamIndex, slot,
// order}, slot being the speaker's place on their team.
export function indexSpeakerInfo(speakers) {
    const info = {}
    const perTeam = {}
    ;(speakers || []).forEach((s, order) => {
        if (!s || !s.alias) return
        const t = s.team_index == null ? null : s.team_index
        const slot = t == null ? null : (perTeam[t] = (perTeam[t] || 0) + 1) - 1
        info[s.alias] = { label: s.label || s.alias, team: s.team || null, teamIndex: t, slot, order }
    })
    return info
}
// What the page calls a speaker: their team label ("Sandy 2") when the
// group knows one, else the tag as stored.
export function speakerLabel(name, info) {
    const e = info && name != null ? info[name] : null
    return e && e.label ? e.label : name
}
export function teamColorFor(teamIndex) {
    const palettes = isDarkTheme() ? TEAM_PALETTES_DARK : TEAM_PALETTES
    return palettes[Math.max(0, teamIndex || 0) % palettes.length][0]
}
export function speakerColorFor(name, allNames, info) {
    const e = info && name != null ? info[name] : null
    if (e && e.teamIndex != null) {
        const palettes = isDarkTheme() ? TEAM_PALETTES_DARK : TEAM_PALETTES
        const pal = palettes[e.teamIndex % palettes.length]
        return pal[(e.slot || 0) % pal.length]
    }
    const palette = isDarkTheme() ? SPEAKER_PALETTE_DARK : SPEAKER_PALETTE
    const sorted = [...new Set(allNames || [])].sort()
    const i = Math.max(0, sorted.indexOf(name))
    return palette[i % palette.length]
}
// The time of day a second on the session clock fell on, in the viewer's
// zone ("2:11:53 PM"); base is the session clock's zero (creation_date).
// timeZone pins the zone (tests); the page leaves it to the browser.
export function wallClockLabel(base, seconds, timeZone) {
    if (!(base instanceof Date) || isNaN(base.getTime()) || seconds == null || isNaN(seconds)) return ""
    const d = new Date(base.getTime() + Math.floor(seconds) * 1000)
    const opts = { hour: "numeric", minute: "2-digit", second: "2-digit" }
    if (timeZone) opts.timeZone = timeZone
    return d.toLocaleTimeString("en-US", opts)
}

// One stable color per speaker across a set of transcripts, so a speaker keeps
// the same color in every view. Was built two ways (a reduce in
// transcripts-component, a loop in transcript-panel).
export function buildSpeakerColors(transcripts, info) {
    const tags = [...new Set((transcripts || []).map((t) => t.speaker_tag).filter(Boolean))]
    const map = {}
    for (const tag of tags) map[tag] = speakerColorFor(tag, tags, info)
    return map
}

// Clock-style HH:MM:SS from seconds (shared by transcripts + reflection dashboards).
export function formatHMS(s) {
  const date = new Date(1000 * Math.floor(s));
  return date.toISOString().substr(11, 8);
}

// ---------------------------------------------------------------------------
// Polling / reconnect helpers (infra audit G.1, G.2). Pure and unit-tested.
// ---------------------------------------------------------------------------

// Exponential backoff with full jitter: uniform in [floor, cap] where
// cap = min(max, base * 2^attempt). The floor (half the base) is the one
// departure from pure full jitter — a fast-failing endpoint must never be
// retried in a near-zero-delay loop. `attempt` counts from 0.
export function backoffDelay(attempt, base = 1000, max = 30000, rand = Math.random) {
  const cap = Math.min(max, base * Math.pow(2, Math.max(0, attempt || 0)))
  const floor = Math.min(cap, base / 2)
  return Math.round(floor + rand() * (cap - floor))
}

// Merge rows by id. Known ids keep their position but take the newer copy
// (a transcript whose speaker metrics were attached after it was first
// fetched); unknown ids append in the order received; rows without an id
// always append. Never mutates its inputs.
export function mergeById(current, incoming) {
  const out = [...(current || [])]
  if (!incoming || incoming.length === 0) return out
  const index = new Map()
  out.forEach((r, i) => {
    if (r && r.id != null) index.set(r.id, i)
  })
  for (const r of incoming) {
    if (r && r.id != null && index.has(r.id)) {
      out[index.get(r.id)] = r
    } else {
      if (r && r.id != null) index.set(r.id, out.length)
      out.push(r)
    }
  }
  return out
}

// Highest numeric id in a row list, never below `floor`: the `after_id`
// cursor for the next incremental poll.
export function maxId(rows, floor = 0) {
  let m = floor
  for (const r of rows || []) {
    if (r && typeof r.id === "number" && r.id > m) m = r.id
  }
  return m
}

// Chained polling: `fn(signal)` runs once, and the next run is scheduled
// only after it settles (requests never overlap). A run that resolves
// false or throws counts as a failure and the next delay backs off (full
// jitter, capped at maxBackoffMs); a success returns to intervalMs. Runs
// pause while the tab is hidden and resume on visibilitychange. The
// returned stop() aborts the in-flight request and cancels the chain.
export function startPolling(fn, intervalMs, { maxBackoffMs = 30000, immediate = true } = {}) {
  let stopped = false
  let timer = null
  let inFlight = null
  let failures = 0
  const doc = typeof document !== "undefined" ? document : null
  const hidden = () => !!(doc && doc.hidden)
  const schedule = (ms) => {
    if (stopped) return
    clearTimeout(timer)
    timer = setTimeout(tick, ms)
  }
  const tick = async () => {
    timer = null
    if (stopped || inFlight !== null) return
    if (hidden()) return // resumed by visibilitychange
    inFlight =
      typeof AbortController !== "undefined"
        ? new AbortController()
        : { abort() {}, signal: undefined }
    let ok = false
    try {
      ok = (await fn(inFlight.signal)) !== false
    } catch {
      ok = false
    }
    inFlight = null
    if (stopped) return
    failures = ok ? 0 : failures + 1
    schedule(ok ? intervalMs : backoffDelay(failures, intervalMs, maxBackoffMs))
  }
  const onVisibility = () => {
    if (!hidden() && !stopped && inFlight === null && timer === null) tick()
  }
  if (doc) doc.addEventListener("visibilitychange", onVisibility)
  if (immediate) tick()
  else schedule(intervalMs)
  return () => {
    stopped = true
    clearTimeout(timer)
    timer = null
    if (inFlight !== null) inFlight.abort()
    if (doc) doc.removeEventListener("visibilitychange", onVisibility)
  }
}
