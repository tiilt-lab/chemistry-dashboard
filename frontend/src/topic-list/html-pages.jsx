import React from 'react';
import { EmptyState } from "../components/empty-state";
import { dlgWindow, dlgHeading, dlgInput, dlgPrimary, dlgCancel } from '../components/dialog-styles'
import { pageShell, formCard } from '../components/layout-styles'
import { Appheader } from '../header/header-component'
import { AppContextMenu } from '../components/context-menu/context-menu-component';
import { GenericDialogBox } from '../dialog/dialog-component';

const DIALOG_HEADINGS = {
  rename: "Rename topic",
  submit: "Submit topics",
  tips: "Tips",
  close: "Discard topics?",
};

function TopicListPage(props) {
  const hasRenameTarget =
    props.showedInd >= 0 && props.topicListStruct[props.showedInd];

  return (
    <>
      <div role="main" className="main-container">
        <Appheader
          title={props.editMode ? "Topic List" : props.viewTitle}
          leftText={false}
          rightText={props.editMode ? "Tips" : ""}
          rightTextClick={
            props.editMode ? () => props.toggleDisplay(true, "tips", -1) : null
          }
          editMode={props.editMode}
          changeInputVal={(val) => props.setNameInput(val)}
          nav={() => {
            props.editMode
              ? props.toggleDisplay(true, "close", -1)
              : props.navTopicModels();
          }}
        />

        <div className={pageShell}>
        <div className={formCard}>
        <div className="mx-auto flex w-full max-w-lg grow flex-col gap-2 overflow-y-auto px-4 py-6">
          {props.topicListStruct.length === 0 ? (
            <EmptyState
              title="No topics"
              subtitle="There are no topics to show for this model."
            />
          ) : (
            <></>
          )}
          {props.topicListStruct.map((testArr, count) => (
            <div
              key={"model" + count}
              onClick={() => (props.editMode ? props.toggleClicked(count) : null)}
              className={`rounded-lg border p-4 transition ${testArr.clicked ? "border-tiilt bg-tiilt-soft" : "border-tiilt-line bg-white"} ${props.editMode ? "cursor-pointer hover:border-tiilt" : ""}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 grow font-semibold text-tiilt-ink">
                  {testArr.tname}
                </div>
                {props.editMode ? (
                  <AppContextMenu label={`Options for ${testArr.tname}`} reverseToggle={() => props.toggleClicked(count)}>
                    <button
                      role="menuitem"
                      className="block w-full cursor-pointer px-4 py-2 text-left text-sm text-tiilt-ink transition hover:bg-tiilt-soft"
                      onClick={() => props.toggleDisplay(true, "rename", count)}
                    >
                      Rename
                    </button>
                  </AppContextMenu>
                ) : (
                  <></>
                )}
              </div>
              <div className="mt-1 text-sm font-medium text-tiilt-ink">
                {props.stringFormat(testArr.kwds, testArr.kwdprobs, false)}
              </div>
              <div className="mt-0.5 text-xs text-tiilt-muted">
                {props.stringFormat(testArr.kwds, testArr.kwdprobs, true)}
              </div>
            </div>
          ))}
        </div>

        {props.editMode ? (
          <div className="w-full flex-none border-t border-tiilt-line bg-white">
            <div className="mx-auto w-full max-w-lg px-4 py-4">
              <button
                className={dlgPrimary + " w-full"}
                onClick={() => props.toggleDisplay(true, "submit", -1)}
              >
                Submit
              </button>
            </div>
          </div>
        ) : (
          <></>
        )}
        </div>
        </div>
      </div>

      <GenericDialogBox onClose={() => props.toggleDisplay(false, "", -1)} show={props.showDialog}>
        <div className={dlgWindow} style={{ minWidth: "min(20rem, 76vw)" }}>
          <div className={dlgHeading}>
            {DIALOG_HEADINGS[props.currentDialog] || ""}
          </div>

          {props.currentDialog === "rename" ? (
            <React.Fragment>
              <input
                id="txtName"
                className={dlgInput}
                defaultValue={
                  hasRenameTarget
                    ? props.topicListStruct[props.showedInd].tname
                    : ""
                }
                onKeyUp={(event) => props.setCurrInput(event.target.value)}
                maxLength="64"
              />
              <button className={dlgPrimary} onClick={() => props.setTopicName()}>
                Confirm
              </button>
              {props.wrongInput ? (
                <div className="text-sm text-tiilt-danger">
                  There can only be letters or numbers in your topic name.
                </div>
              ) : (
                <></>
              )}
              {props.changedName && hasRenameTarget ? (
                <div className="text-sm text-tiilt-muted">
                  Name changed to {props.topicListStruct[props.showedInd].tname}
                </div>
              ) : (
                <></>
              )}
            </React.Fragment>
          ) : (
            <></>
          )}

          {props.currentDialog === "submit" ? (
            <React.Fragment>
              <div className="text-sm text-tiilt-ink">
                Are you sure you want to go forward with the following topics:{" "}
                {props.getSelectNameList(true)}
              </div>
              {props.noName ? (
                <div className="flex flex-col gap-1.5">
                  <div className="text-sm text-tiilt-ink">
                    If yes, select a name for your topics.
                  </div>
                  <input
                    id="txtName"
                    className={dlgInput}
                    defaultValue=""
                    onKeyUp={(event) => props.setNameInput(event.target.value)}
                    maxLength="64"
                  />
                </div>
              ) : (
                <></>
              )}
              <button className={dlgPrimary} onClick={() => props.saveNewModel()}>
                Submit topics
              </button>
              {props.noTopics ? (
                <div className="text-sm text-tiilt-danger">
                  You must select topics before submitting.
                </div>
              ) : (
                <></>
              )}
              {props.wrongInput ? (
                <div className="text-sm text-tiilt-danger">
                  Your topic list name can't be empty.
                </div>
              ) : (
                <></>
              )}
            </React.Fragment>
          ) : (
            <></>
          )}

          {props.currentDialog === "tips" ? (
            <div className="flex flex-col gap-2 text-left text-sm text-tiilt-ink">
              <div>Click on “Topic List” to change the name of your topic model.</div>
              <div>
                Then, select (and/or rename) which topics you’d like to include in
                your model.
              </div>
            </div>
          ) : (
            <></>
          )}

          {props.currentDialog === "close" ? (
            <React.Fragment>
              <div className="text-sm text-tiilt-ink">
                Are you sure you want to go back? All topics will be lost.
              </div>
              <button
                className={dlgPrimary}
                onClick={() => props.navigateToFileUpload()}
              >
                Yes, discard
              </button>
            </React.Fragment>
          ) : (
            <></>
          )}

          <button
            className={dlgCancel}
            onClick={() => props.toggleDisplay(false, "", -1)}
          >
            Close
          </button>
        </div>
      </GenericDialogBox>
    </>
  );
}

export { TopicListPage };
