import { describe, expect, it } from "vitest"
import { joinWithDefault } from "./join-mode"

describe("joinWithDefault", () => {
    it("opens on Video only when the session says video", () => {
        expect(joinWithDefault({ join_mode: "video" })).toBe("Video")
    })
    it("is Audio for audio, missing, unknown and no session", () => {
        expect(joinWithDefault({ join_mode: "audio" })).toBe("Audio")
        expect(joinWithDefault({})).toBe("Audio")
        expect(joinWithDefault({ join_mode: "Videocartoonify" })).toBe("Audio")
        expect(joinWithDefault(null)).toBe("Audio")
        expect(joinWithDefault(undefined)).toBe("Audio")
    })
})
