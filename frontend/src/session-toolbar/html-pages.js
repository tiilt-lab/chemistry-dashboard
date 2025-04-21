import style from "./session-toolbar.module.css";
import style2 from "../dialog/dialog.module.css";
import { GenericDialogBox } from "../dialog/dialog-component";
import { AppSpinner } from "../spinner/spinner-component";
import React from "react";
import { adjDim } from "../myhooks/custom-hooks";
import { isLargeScreen } from "../myhooks/custom-hooks";

function AppSessionPage(props) {
  return (
    <>
      <div
        className={
          props.sessionEnding
            ? `${style["session-toolbar"]} ${style["dialog-blur"]}`
            : style["session-toolbar"]
        }
      >
        <span className={style["session-time"]}>
          <div className={style.time}>{props.timeText}</div>
          <div className={style.info}>Total duration</div>
        </span>
        {props.menus.map((menu, index) => (
          <button className={
            isLargeScreen()
              ? `${style["toolbar-button"]} ${style["basic-button"]} ${style["medium-button"]}`
              : `${style["toolbar-button"]} ${style["basic-button"]} ${style["small-button"]}`}
           >{`${index + 1}. ${menu.title}`}</button>
        ))}
        {props.session.recording ? (
          <span className={style["session-end"]} onClick={props.onEndSession}>
            <button className={style["end-button"]}>End</button>
          </span>
        ) : (
          <></>
        )}
      </div>

      <GenericDialogBox show={props.sessionEnding}>
        <div className={style["dialog-content"]}>
          <div className={style2["dialog-heading"]}>Session Ending...</div>
          <div className={style["dialog-spinner"]}>
            <AppSpinner></AppSpinner>
          </div>
        </div>
      </GenericDialogBox>
    </>
  );
}

export { AppSessionPage };
