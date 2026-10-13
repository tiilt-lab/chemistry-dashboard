// Which sessions the open folder view is about: at Home ("" / null) every
// session the account can see, inside a folder the sessions filed directly
// in it (subfolders are their own rows, with their own counts). Shared by
// the stats cards and the table so the two never disagree.
export function scopeSessions(sessions, folderId) {
    const all = sessions || []
    if (folderId === "" || folderId == null) return all
    return all.filter((s) => s.folder === folderId)
}

// Sessions the table shows for the open folder: Home lists the unfiled
// ones (folders are rows above them), a folder lists its own.
export function listedSessions(sessions, folderId) {
    const all = sessions || []
    if (folderId === "" || folderId == null) return all.filter((s) => s.folder == null)
    return all.filter((s) => s.folder === folderId)
}
