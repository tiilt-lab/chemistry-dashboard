import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { SkeletonRows } from "../components/skeleton"
import { EmptyState } from "../components/empty-state"
import { btnPrimary } from "../components/dialog-styles"
import { pageShell, formCard } from "../components/layout-styles"
import { DialogBoxTwoOption } from "../dialog/dialog-component"
import { Appheader } from "../header/header-component"
import { LibraryTabs } from "../components/library-tabs"
import style from "./manage-topic-models.module.css"
import style2 from "../components/context-menu/context-menu.module.css"

function ManageTopicsPage(props) {
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
                <div className="relative min-h-0 w-full grow overflow-y-auto">
                    <div className="mx-auto w-full max-w-2xl px-4 py-6">
                        {!props.topicModels ? (
                            <SkeletonRows rows={5} />
                        ) : (
                            <></>
                        )}
                        {props.topicModels && props.topicModels.length === 0 ? (
                            <EmptyState
                                title="No topic models"
                                subtitle="Tap the button below to make your first topic model."
                            />
                        ) : (
                            <></>
                        )}
                        <ul className="flex flex-col gap-2">
                            {(props.topicModels || []).map(
                                (topicModel, count) => (
                                    <li
                                        key={"topic" + count}
                                        className="flex items-center gap-3 rounded-xl border border-tiilt-line bg-white px-4 py-3 transition hover:border-tiilt hover:shadow-card-hover"
                                    >
                                        <button
                                            onClick={() =>
                                                props.navTopicList(
                                                    topicModel.data,
                                                    topicModel.summary,
                                                    topicModel.name,
                                                )
                                            }
                                            className="min-w-0 grow cursor-pointer text-left"
                                        >
                                            <span className="flex items-baseline justify-between gap-3">
                                                <span className="truncate text-base font-semibold text-tiilt-ink">
                                                    {topicModel.name}
                                                </span>
                                                <span className="flex-none text-xs text-tiilt-muted">
                                                    {props.formatdate(
                                                        topicModel.creation_date,
                                                    )}
                                                </span>
                                            </span>
                                            <span className="mt-0.5 block truncate text-sm text-tiilt-muted">
                                                {topicModel.summary}
                                            </span>
                                        </button>
                                        <div className="flex-none">
                                            <AppContextMenu label={`Options for ${topicModel.name}`}>
                                                <button
                                                    role="menuitem"
                                                    className={`${style2["menu-item"]} ${style2["red"]}`}
                                                    onClick={() => {
                                                        props.deleteTopicModel(
                                                            topicModel,
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
                <div className="flex w-full flex-none items-center justify-center border-t border-tiilt-line bg-white px-4 py-3">
                    <button
                        className={btnPrimary + " h-11 w-full max-w-55 cursor-pointer"}
                        onClick={props.navFileUpload}
                    >
                        Create Topic Model
                    </button>
                </div>
                </div>
                </div>
            </div>

            <DialogBoxTwoOption
                show={props.deleteDialogIsOpen}
                itsclass={style["dialog-window"]}
                heading={"Delete Topic Model"}
                body={
                    "Are you sure you want to permanently delete this topic model?"
                }
                deletebuttonaction={props.confirmDeleteTopicModel}
                cancelbuttonaction={props.closeDeleteDialog}
            />
        </>
    )
}

export { ManageTopicsPage }
