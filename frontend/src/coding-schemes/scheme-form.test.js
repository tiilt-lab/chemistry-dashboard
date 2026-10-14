import { describe, it, expect } from "vitest"
import { slugify, toForm, toApi, formProblem, emptyScheme } from "./scheme-form"

describe("scheme form", () => {
    it("slugs keys and codes from labels", () => {
        expect(slugify(" Past / blame! ")).toBe("past_blame")
        expect(slugify("x".repeat(40))).toBe("x".repeat(24))
    })
    it("round-trips the API shape through the form", () => {
        const api = {
            name: "Liveliness", description: "d", context: ["a", "b"],
            dimensions: [{ key: "move", label: "Move", multi: false, guidance: "g", default: "other", conventions: ["c"],
                           codes: [{ code: "proposes", label: "Proposes", definition: "x", examples: ["e1", "e2"] }] }],
        }
        const form = toForm(api)
        expect(form.context).toBe("a\nb")
        expect(form.dimensions[0].codes[0].examples).toBe("e1\ne2")
        expect(toApi(form)).toEqual({
            name: "Liveliness", description: "d", context: ["a", "b"],
            dimensions: [{ key: "move", label: "Move", multi: false, guidance: "g", default: "other", conventions: ["c"],
                           codes: [{ code: "proposes", label: "Proposes", definition: "x", examples: ["e1", "e2"] }] }],
        })
    })
    it("fills keys and codes from labels and drops blanks", () => {
        const form = emptyScheme()
        form.name = "T"
        form.dimensions[0].label = "Speech act"
        form.dimensions[0].codes[0].label = "Open question"
        const api = toApi(form)
        expect(api.dimensions[0].key).toBe("speech_act")
        expect(api.dimensions[0].codes[0]).toEqual({ code: "open_question", label: "Open question", definition: "", examples: [] })
        expect(api.dimensions[0].default).toBeUndefined()
    })
    it("reports what the form can tell before the server", () => {
        const form = emptyScheme()
        expect(formProblem(form)).toBe("Give the scheme a name.")
        form.name = "T"
        expect(formProblem(form)).toBe("Dimension 1 needs a label.")
        form.dimensions[0].label = "D"
        expect(formProblem(form)).toBe('"D" needs at least one code.')
        form.dimensions[0].codes[0].code = "a"
        expect(formProblem(form)).toBeNull()
        expect(formProblem({ name: "T", dimensions: [] })).toBe("Add at least one dimension.")
    })
})
