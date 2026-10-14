// The coding-scheme editor's form state and its conversion to the API shape
// (pure, so the rules are unit-testable). The server validates again.

export function slugify(text, limit = 24) {
    return String(text || "")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "")
        .slice(0, limit)
        .replace(/_+$/, "")
}

let seq = 0
const uid = () => "k" + ++seq

export function emptyCode() {
    return { id: uid(), code: "", label: "", definition: "", examples: "" }
}

export function emptyDimension() {
    return { id: uid(), key: "", label: "", multi: false, guidance: "", default: "", conventions: "", codes: [emptyCode()] }
}

export function emptyScheme() {
    return { name: "", description: "", context: "", dimensions: [emptyDimension()] }
}

// API shape (lists; examples/context as lists) -> form state (strings).
export function toForm(scheme) {
    if (!scheme) return emptyScheme()
    return {
        name: scheme.name || "",
        description: scheme.description || "",
        context: (scheme.context || []).join("\n"),
        dimensions: (scheme.dimensions || []).map((d) => ({
            id: uid(),
            key: d.key || "",
            label: d.label || "",
            multi: d.multi === true,
            guidance: d.guidance || "",
            default: d.default || "",
            conventions: (d.conventions || []).join("\n"),
            codes: (d.codes || []).map((c) => ({
                id: uid(),
                code: c.code || "",
                label: c.label || "",
                definition: c.definition || "",
                examples: (c.examples || []).join("\n"),
            })),
        })),
    }
}

const lines = (text) =>
    String(text || "")
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean)

// Form state -> API shape. Keys and codes fall back to slugs of their labels.
export function toApi(form) {
    return {
        name: (form.name || "").trim(),
        description: (form.description || "").trim(),
        context: lines(form.context),
        dimensions: (form.dimensions || []).map((d) => ({
            key: slugify(d.key || d.label),
            label: (d.label || "").trim(),
            multi: d.multi === true,
            guidance: (d.guidance || "").trim(),
            default: d.multi ? null : slugify(d.default) || undefined,
            conventions: lines(d.conventions),
            codes: (d.codes || []).map((c) => ({
                code: slugify(c.code || c.label),
                label: (c.label || "").trim() || undefined,
                definition: (c.definition || "").trim(),
                examples: lines(c.examples),
            })),
        })),
    }
}

// What the form can tell before asking the server, or null.
export function formProblem(form) {
    if (!(form.name || "").trim()) return "Give the scheme a name."
    if (!form.dimensions || form.dimensions.length === 0) return "Add at least one dimension."
    for (const [i, d] of form.dimensions.entries()) {
        if (!(d.label || "").trim()) return `Dimension ${i + 1} needs a label.`
        const codes = (d.codes || []).filter((c) => slugify(c.code || c.label))
        if (codes.length === 0) return `"${d.label}" needs at least one code.`
    }
    return null
}
