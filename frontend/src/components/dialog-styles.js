// Shared sleek form/dialog styling (the "dlg*" pattern) — one source of truth
// so every page's dialogs and wizard forms look identical and theme correctly.
export const dlgWindow = "flex min-w-[min(22rem,76vw)] flex-col gap-3"
export const dlgHeading = "mb-1 text-lg font-semibold text-tiilt-ink"
export const dlgInput =
    "h-11 w-full rounded-lg border border-tiilt-line bg-white px-3 text-base text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
export const dlgPrimary =
    "mt-2 h-11 rounded-lg bg-tiilt font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
export const dlgCancel =
    "h-11 rounded-lg border border-tiilt-line bg-white font-semibold text-tiilt-ink transition hover:border-tiilt hover:bg-tiilt-soft active:translate-y-px"
export const dlgBody = "flex min-w-[min(22rem,86vw)] flex-col gap-3"
export const dlgLabel = "text-sm font-semibold text-tiilt-ink"
export const dlgSelect =
    "h-11 w-full cursor-pointer rounded-lg border border-tiilt-line bg-white px-3 pr-8 text-base text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
export const dlgError =
    "rounded-md bg-tiilt-danger-soft px-3 py-2 text-sm text-tiilt-danger"
export const dlgDanger =
    "mt-2 h-11 rounded-lg bg-tiilt-danger font-semibold text-white transition hover:brightness-90 active:translate-y-px"

// Page-level buttons (toolbars, headers, cards) — one source instead of the
// ~20 hand-copied bg-tiilt / outline class strings that had drifted.
export const btnPrimary =
    "rounded-lg bg-tiilt px-4 py-2 text-sm font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
export const btnPrimarySm =
    "rounded-lg bg-tiilt px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
export const btnPrimaryTall =
    "flex h-12 items-center justify-center rounded-lg bg-tiilt text-base font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
export const btnSecondary =
    "rounded-lg border border-tiilt-line bg-white px-4 py-2 text-sm font-semibold text-tiilt-ink transition hover:border-tiilt hover:bg-tiilt-soft active:translate-y-px"
export const btnSecondarySm =
    "rounded-lg border border-tiilt-line bg-white px-3 py-1.5 text-xs font-semibold text-tiilt-ink transition hover:border-tiilt hover:bg-tiilt-soft active:translate-y-px"
export const btnSecondaryTall =
    "flex h-12 items-center justify-center rounded-lg border border-tiilt-line bg-white text-base font-semibold text-tiilt transition hover:border-tiilt hover:bg-tiilt-soft active:translate-y-px"
