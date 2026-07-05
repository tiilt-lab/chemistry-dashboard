import { Fragment } from "react";

const IconFolder = (p) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}>
    <path d="M3 7a2 2 0 0 1 2-2h3.5l2 2H19a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
  </svg>
);
const IconHome = (p) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}>
    <path d="M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10" />
  </svg>
);
const IconChevronRight = (p) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}>
    <path d="M9 6l6 6-6 6" />
  </svg>
);
const IconChevronLeft = (p) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}>
    <path d="M15 6l-6 6 6 6" />
  </svg>
);
const IconCheck = (p) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" {...p}>
    <path d="M5 13l4 4L19 7" />
  </svg>
);

function rowClass(selected) {
  return (
    "flex items-center gap-2 rounded-lg border px-3 py-2 transition " +
    (selected
      ? "border-tiilt bg-tiilt-soft"
      : "border-tiilt-line bg-white hover:border-tiilt")
  );
}

function AppFolderPage(props) {
  const atRoot = props.breadcrumbs.length === 0;
  const currentName = atRoot
    ? "Home"
    : props.breadcrumbs[props.breadcrumbs.length - 1].name;

  return (
    <div className="flex min-w-[min(20rem,76vw)] flex-col gap-2">
      {/* Current location + back */}
      <div className="flex items-center gap-1.5 text-sm">
        {!atRoot ? (
          <button
            type="button"
            title="Back"
            onClick={() =>
              props.displayFolder(
                props.breadcrumbs.length > 1
                  ? props.breadcrumbs[props.breadcrumbs.length - 2].id
                  : undefined
              )
            }
            className="flex h-7 w-7 flex-none items-center justify-center rounded-md text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
          >
            <IconChevronLeft />
          </button>
        ) : null}
        <div className="min-w-0 truncate font-semibold text-tiilt-ink">
          {atRoot ? (
            "Home"
          ) : (
            <>
              Home
              <span className="text-tiilt-muted"> / … / </span>
              {currentName}
            </>
          )}
        </div>
      </div>

      <ul className="flex max-h-[46vh] flex-col gap-1.5 overflow-y-auto">
        {/* Select the current (root) level as the target */}
        {atRoot ? (
          <li>
            <div
              className={rowClass(props.selectedFolder === -1) + " cursor-pointer"}
              onClick={() => props.setSelectedFolderEvent(-1)}
            >
              <span className="flex-none text-tiilt-muted">
                <IconHome />
              </span>
              <span className="min-w-0 grow truncate font-medium text-tiilt-ink">
                Home
              </span>
              {props.selectedFolder === -1 ? (
                <span className="flex-none text-tiilt">
                  <IconCheck />
                </span>
              ) : null}
            </div>
          </li>
        ) : null}

        {props.visibleFolders.length === 0 ? (
          <li className="rounded-lg border border-dashed border-tiilt-line px-4 py-6 text-center text-sm text-tiilt-muted">
            No subfolders here.
          </li>
        ) : (
          <></>
        )}

        {props.visibleFolders.map((folder, index) => (
          <li key={index}>
            <div className={rowClass(folder.id === props.selectedFolder)}>
              <button
                type="button"
                onClick={() => props.setSelectedFolderEvent(folder.id)}
                className="flex min-w-0 grow cursor-pointer items-center gap-2.5 text-left"
              >
                <span className="flex-none text-tiilt-muted">
                  <IconFolder />
                </span>
                <span className="min-w-0 truncate font-medium text-tiilt-ink">
                  {folder.name}
                </span>
                {folder.id === props.selectedFolder ? (
                  <span className="flex-none text-tiilt">
                    <IconCheck />
                  </span>
                ) : null}
              </button>
              {props.hasChildren(folder) ? (
                <button
                  type="button"
                  title="Open folder"
                  onClick={() => props.displayFolder(folder.id)}
                  className="flex h-8 w-8 flex-none items-center justify-center rounded-md text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
                >
                  <IconChevronRight />
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export { AppFolderPage };
