// Shared sleek form/dialog styling (the "dlg*" pattern) — one source of truth
// so every page's dialogs and wizard forms look identical and theme correctly.
export const dlgWindow = "flex min-w-[min(22rem,86vw)] flex-col gap-3"
export const dlgHeading = "mb-1 text-lg font-semibold text-tiilt-ink"
export const dlgInput =
    "h-11 w-full rounded-lg border border-tiilt-line bg-white px-3 text-base text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
export const dlgPrimary =
    "mt-2 h-11 rounded-lg bg-tiilt font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
export const dlgCancel =
    "h-11 rounded-lg border border-tiilt-line bg-white font-semibold text-tiilt-ink transition hover:bg-tiilt-soft active:translate-y-px"
