// Trigger a browser download for a Blob and release the object URL —
// previously re-implemented inline in five components, two of which never
// revoked the URL.
export function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
}
