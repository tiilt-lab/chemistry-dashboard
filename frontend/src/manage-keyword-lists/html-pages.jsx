import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { SkeletonRows } from "../components/skeleton"
import { EmptyState } from "../components/empty-state"
import { btnPrimary } from "../components/dialog-styles"
import { pageShell, formCard } from "../components/layout-styles"
import { DialogBoxTwoOption } from "../dialog/dialog-component"
import { Appheader } from "../header/header-component"
import { LibraryTabs } from "../components/library-tabs"
import style from "./manage-keyword-lists.module.css"
import style2 from "../components/context-menu/context-menu.module.css"

function KeywordListPage(props) {
    return (
        <>
            <div role="main" className="main-container">
                <Appheader
                    title={"Library"}
                    leftText={false}
                    rightText={""}
                    nav={props.navigate}
                />
                <LibraryTabs />
                <div className={pageShell}>
                <div className={formCard}>
                <div className="relative min-h-0 w-full grow">
                    <div className="mx-auto w-full max-w-2xl px-4 py-6">
                        {!props.keywordLists ? (
                            <SkeletonRows rows={5} />
                        ) : (
                            <></>
                        )}
                        {props.keywordLists &&
                        props.keywordLists.length === 0 ? (
                            <EmptyState
                                title="No keyword lists"
                                subtitle="Tap the button below to make your first keyword list."
                            />
                        ) : (
                            <></>
                        )}
                        <ul className="flex flex-col gap-2">
                            {(props.keywordLists || []).map(
                                (keywordList, count) => (
                                    <li
                                        key={"keyword" + count}
                                        className="flex items-center gap-3 rounded-xl border border-tiilt-line bg-white px-4 py-3 transition hover:border-tiilt hover:shadow-card-hover"
                                    >
                                        <button
                                            onClick={() =>
                                                props.keywordListClicked(
                                                    keywordList,
                                                )
                                            }
                                            className="min-w-0 grow cursor-pointer text-left"
                                        >
                                            <span className="flex items-baseline justify-between gap-3">
                                                <span className="truncate text-base font-semibold text-tiilt-ink">
                                                    {keywordList.name}
                                                </span>
                                                <span className="flex-none text-xs text-tiilt-muted">
                                                    {props.formatdate(
                                                        keywordList.creation_date,
                                                    )}
                                                </span>
                                            </span>
                                            <span className="mt-0.5 block truncate text-sm text-tiilt-muted">
                                                {keywordList.keywords.join(
                                                    ", ",
                                                )}
                                            </span>
                                        </button>
                                        <div className="flex-none">
                                            <AppContextMenu label={`Options for ${keywordList.name}`}>
                                                <button
                                                    role="menuitem"
                                                    className={`${style2["menu-item"]} ${style2["red"]}`}
                                                    onClick={() => {
                                                        props.deleteKeywordList(
                                                            keywordList,
                                                        )
                                                    }}
                                                >
                                                    Delete
                                                </button>
                                            </AppContextMenu>
                                        </div>
                                    </li>
                                ),
                            )}
                        </ul>
                    </div>
                </div>
                <div className="flex w-full flex-none flex-wrap items-center justify-center gap-3 border-t border-tiilt-line bg-white px-4 py-3">
                    <button
                        className={btnPrimary + " h-11 w-full max-w-55 cursor-pointer"}
                        onClick={props.openNewKeywordList}
                    >
                        New Keyword List
                    </button>
                </div>
                </div>
                </div>
            </div>

            <DialogBoxTwoOption
                show={props.deleteDialogIsOpen}
                itsclass={style["dialog-window"]}
                heading={"Delete Keyword List"}
                body={
                    "Are you sure you want to permanently delete this keyword list?"
                }
                deletebuttonaction={props.confirmDeleteKeywordList}
                cancelbuttonaction={props.closeDeleteDialog}
            />
        </>
    )
}

export { KeywordListPage }
