import React from "react"
import style from "./keywords.module.css"
import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { DialogBox } from "../dialog/dialog-component"
import questIcon from "../assets/img/question.svg"

function AppKeywordsPage(props) {
    return (
        <>
            <div className="min-h-20 w-full">
                <div className="mb-2 flex items-center justify-between">
                    <button
                        onClick={() => props.toggleDisplay(true)}
                        className="cursor-pointer border-0 bg-transparent p-0"
                        aria-label="About keyword detection"
                    >
                        <img
                            className="h-4 w-4 opacity-70"
                            alt=""
                            src={questIcon}
                        />
                    </button>
                    <AppContextMenu label="Keyword display options" setcallback={props.setCallbackFunc}>
                        <button
                            role="menuitem"
                            className="mt-2.5 block w-full cursor-pointer px-2.5 text-left"
                            onClick={() => {
                                props.toggleGraph()
                                props.callbackfunc(false)
                            }}
                        >
                            {props.showGraph ? "Show Words" : "Show Timeline"}
                        </button>
                    </AppContextMenu>
                </div>
                {!props.showGraph ? (
                    <React.Fragment>
                        {props.displayKeywords
                            .slice(
                                0,
                                props.displayKeywords.length < 25
                                    ? props.displayKeywords.length
                                    : 25,
                            )
                            .map((displayKeyword, index) => (
                                <span
                                    key={index}
                                    className={style["keyword"]}
                                    style={{ color: `${displayKeyword.color}` }}
                                    onClick={() =>
                                        props.showKeywordContext(
                                            displayKeyword.transcript_id,
                                        )
                                    }
                                >
                                    {displayKeyword.word}
                                    {index !==
                                    (props.displayKeywords.length < 25
                                        ? props.displayKeywords.length
                                        : 25) -
                                        1 ? (
                                        <span className={style["base"]}>
                                            ,{" "}
                                        </span>
                                    ) : (
                                        <></>
                                    )}
                                </span>
                            ))}

                        {props.displayKeywords.length == 0 ? (
                            <div className={style["no-keywords"]}>
                                No keywords detected
                            </div>
                        ) : (
                            <></>
                        )}
                    </React.Fragment>
                ) : (
                    <></>
                )}

                {props.showGraph ? (
                    <React.Fragment>
                        <div className={style["timeline-container"]}>
                            {props.session.keywords.map((keyword, index) => (
                                <div
                                    key={index}
                                    className={style["keyword-timeline"]}
                                >
                                    <div className={style["keyword-text"]}>
                                        {keyword}
                                    </div>
                                    <div className={style["keyword-graph"]}>
                                        <hr />
                                        {props.keywordPoints[keyword].map(
                                            (point, index) => (
                                                <div
                                                    key={index}
                                                    className={
                                                        style["keyword-point"]
                                                    }
                                                    style={{
                                                        left:
                                                            `${point.x}` + "px",
                                                        backgroundColor: `${point.color}`,
                                                    }}
                                                    onClick={() =>
                                                        props.showKeywordContext(
                                                            point.transcript_id,
                                                        )
                                                    }
                                                ></div>
                                            ),
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                        {props.session.keywords.length == 0 ? (
                            <div className={style["no-keywords"]}>
                                No keywords detected
                            </div>
                        ) : (
                            <></>
                        )}
                    </React.Fragment>
                ) : (
                    <></>
                )}
            </div>

            <DialogBox
                show={props.showDialog}
                heading={"Keywords"}
                message={props.displayKeywords.map((displayKeyword, index) => (
                    <span
                        key={index}
                        className={style["keyword"]}
                        style={{ color: `${displayKeyword.color}` }}
                        onClick={() =>
                            props.showKeywordContext(
                                displayKeyword.transcript_id,
                            )
                        }
                    >
                        {displayKeyword.word}
                        {index !==
                        Object.keys(props.displayKeywords).length - 1 ? (
                            <span className={style["base"]}>, </span>
                        ) : (
                            <></>
                        )}
                    </span>
                ))}
                closedialog={() => props.toggleDisplay(false)}
            />
        </>
    )
}

export { AppKeywordsPage }
