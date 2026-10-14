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

// Library pages (keyword lists, topic models, coding schemes and their
// editors): the same card, but using the content column's width rather
// than a narrow wizard, since they hold lists and tables.
export const wideCard =
  "flex w-full grow flex-col md:my-auto md:grow-0 md:max-w-5xl md:rounded-2xl md:border md:border-tiilt-line md:bg-white md:shadow-modal"

// A card's action bar. Rounded at the bottom on desktop so the white bar
// does not square off the card's lower corners (the card itself cannot
// clip overflow: context menus inside it need to escape it).
export const cardFooter =
  "flex w-full flex-none flex-wrap items-center justify-center gap-3 border-t border-tiilt-line bg-white px-4 py-3 md:rounded-b-2xl"
