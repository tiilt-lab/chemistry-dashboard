import { describe, it, expect } from "vitest"
import { TIMELINE_FIELDS } from "./negotiation-coding-helpers"

// The server's timeline() keys (src/server/negotiation_coding.py, pinned by
// tests/test_negotiation_coding.py::test_timeline_landmarks_on_the_fixture).
// The panel reads timeline[f.key]; a key the server never sends leaves the
// card on "—" forever, which is what a "_s" suffix did until 2026-10-19.
const SERVER_TIMELINE_KEYS = [
    "first_escalating",
    "peak_escalation_window_start",
    "first_sustained_deescalation",
    "first_future_move",
]

describe("TIMELINE_FIELDS", () => {
    it("reads exactly the keys the server sends, in display order", () => {
        expect(TIMELINE_FIELDS.map((f) => f.key)).toEqual(SERVER_TIMELINE_KEYS)
    })

    it("resolves a value for every card on a server-shaped timeline", () => {
        const timeline = {
            first_escalating: 15,
            peak_escalation_window_start: 30,
            peak_escalation_count: 4,
            first_sustained_deescalation: 95,
            first_future_move: 120,
        }
        for (const f of TIMELINE_FIELDS) {
            expect(timeline[f.key], f.key).not.toBeUndefined()
        }
    })
})
