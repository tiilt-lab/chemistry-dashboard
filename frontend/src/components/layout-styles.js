// Shared layout for "action-bar" form/wizard pages.
//
// Mobile: the flow fills the screen and the action bar sits at the bottom
//   (natural for a phone).
// Desktop (md+): the same flow becomes a centered, bounded card sized to its
//   content — so a short form no longer leaves a large whitespace void above a
//   viewport-pinned footer. Long content scrolls inside the card.
//
// Usage: <div className={pageShell}><div className={formCard}>…content…, …footer…</div></div>
export const pageShell =
  "flex grow flex-col overflow-y-auto md:items-center md:justify-center md:p-6"

export const formCard =
  "flex w-full grow flex-col md:grow-0 md:max-h-[calc(100dvh-6rem)] md:max-w-xl md:overflow-hidden md:rounded-2xl md:border md:border-tiilt-line md:bg-white md:shadow-modal"
