import React from "react"
import style from "./keywords.module.css"
import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { adjDim } from "../myhooks/custom-hooks"
import { DialogBox } from "../dialog/dialog-component"
import questIcon from "../assets/img/question.svg"

function AppKeywordsPage(props) {
    return (
        <>
            <div
                className="min-h-20 small-section"
            >
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
                <img
                    onClick={() => props.toggleDisplay(true)}
                    className="absolute top-0 left-0 mt-3.5 ml-1 cursor-pointer"
                    alt="question"
                    src={questIcon}
                />
                <div className="absolute top-0 right-0 mt-3.5 mr-1 cursor-pointer">
                    <AppContextMenu setcallback={props.setCallbackFunc}>
                        <div
                            className="mt-2.5"
                            onClick={() => {
                                props.toggleGraph()
                                props.callbackfunc(false)
                            }}
                        >
                            {props.showGraph ? "Show Words" : "Show Timeline"}
                        </div>
                    </AppContextMenu>
                </div>
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
