import { describe, it, expect } from "vitest"
import { speakingOver, decorateTranscripts } from "./transcript-utils"

const line = (id, tag, start, length) => ({ id, speaker_tag: tag, start_time: start, length })

describe("speakingOver", () => {
    it("marks the later line, naming the speaker it talks over", () => {
        // Session 434, Group 7: Pat 1 starts while Sandy 1 is mid-sentence.
        const over = speakingOver([
            line(1, "Sand1", 274, 9),
            line(2, "Pat1", 279, 2),
            line(3, "Jing", 284, 4),
        ])
        expect(over.get(2)).toEqual(["Sand1"])
        expect(over.has(1)).toBe(false)
        expect(over.has(3)).toBe(false) // starts as Sand1 ends (283): a turn change
    })

    it("ignores the same speaker, unnamed lines and touching turns", () => {
        const over = speakingOver([
            line(1, "Pat1", 0, 5),
            line(2, "Pat1", 2, 5), // the recognizer cutting one voice
            line(3, null, 3, 4),
            line(4, "Sand1", 7, 3), // starts as the last Pat1 line ends
            line(5, "Sand2", 9.8, 2), // 0.2 s of overlap: below the floor
        ])
        expect([...over.keys()]).toEqual([])
    })

    it("lists every speaker a line talks over, once each, in any input order", () => {
        const over = speakingOver([line(3, "C", 4, 3), line(1, "A", 0, 10), line(2, "B", 2, 10), line(4, "A", 5, 1)])
        expect(over.get(3)).toEqual(["B", "A"])
        expect(over.get(2)).toEqual(["A"])
        expect(over.get(4)).toEqual(["C", "B"])
    })
})

describe("decorateTranscripts", () => {
    it("carries speakingOver on every line", () => {
        const rows = [
            { ...line(1, "Sand1", 274, 9), transcript: "It was just out of pure good intentions", keywords: [] },
            { ...line(2, "Pat1", 279, 2), transcript: "So maybe you guys can give us some color", keywords: [] },
        ]
        const out = decorateTranscripts(rows, false, false, () => "#000")
        expect(out.map((t) => t.speakingOver)).toEqual([[], ["Sand1"]])
    })
})
