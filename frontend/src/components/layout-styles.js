// Shared layout for "action-bar" form/wizard pages.
//
// Mobile: the flow fills the screen and the action bar sits at the bottom
//   (natural for a phone).
// Desktop (md+): the same flow becomes a centered card sized to its content.
//
// Single scroll: pageShell is the page's ONE scroll region (the app shell
// never scrolls — #root is overflow-clip). The card grows with its content
// instead of capping height and scrolling internally, so no page shows a
// scrollbar nested inside another. The card centers via auto margins, not
// justify-center, so a card taller than the viewport scrolls from its top
// instead of clipping it.
//
// Usage: <div className={pageShell}><div className={formCard}>…content…, …footer…</div></div>
export const pageShell =
  "flex min-h-0 grow flex-col overflow-y-auto md:items-center md:p-6"

export const formCard =
  "flex w-full grow flex-col md:my-auto md:grow-0 md:max-w-xl md:rounded-2xl md:border md:border-tiilt-line md:bg-white md:shadow-modal"
