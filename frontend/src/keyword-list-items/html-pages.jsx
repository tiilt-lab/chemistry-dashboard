import { dlgInput, dlgCancel } from '../components/dialog-styles';
import { pageShell, formCard } from '../components/layout-styles';
import { Appheader } from '../header/header-component';
import removeicon from '../assets/img/remove.svg'
import React from 'react';

function KeywordListPages(props) {
  return (
    <div role="main" className="main-container">
      <Appheader
        title={"Manage Keyword Lists"}
        leftText={"Cancel"}
        rightText={"Save"}
        rightTextClick={props.saveKeywordList}
        nav={props.navigate}
      />
      <div className={pageShell}>
      <div className={formCard}>
      {props.keywordList && props.keywordListItems ? (
        <div className="mx-auto flex w-full max-w-lg grow flex-col gap-3 px-4 py-6">
          <div>
            <label
              htmlFor="kw-list-name"
              className="mb-1.5 block text-sm font-semibold text-tiilt-ink"
            >
              List name
            </label>
            <input
              id="kw-list-name"
              className={dlgInput}
              defaultValue={
                props.keywordList.name === undefined ? "" : props.keywordList.name
              }
              placeholder="Enter new list name"
              maxLength="64"
              type="text"
              onKeyUp={props.checkName}
            />
          </div>

          {props.keywordListItems.length === 0 ? (
            <div className="rounded-lg border border-dashed border-tiilt-line px-4 py-6 text-center text-sm text-tiilt-muted">
              Name your list and add keywords below.
            </div>
          ) : (
            <></>
          )}

          <div className="flex flex-col gap-2">
            {props.keywordListItems.map((keyword, count) => (
              <div key={"keyword" + count}>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    defaultValue={
                      keyword.keyword === undefined ? "" : keyword.keyword
                    }
                    autoComplete="off"
                    onKeyUp={(event) => props.checkKeyword(keyword, event)}
                    maxLength="64"
                    placeholder="Keyword"
                    className={dlgInput + " grow"}
                  />
                  <button
                    type="button"
                    title="Remove keyword"
                    onClick={() => props.removeKeyword(keyword)}
                    className="flex h-11 w-11 flex-none items-center justify-center rounded-lg border border-tiilt-line text-tiilt-muted transition hover:border-tiilt-danger hover:text-tiilt-danger"
                  >
                    <img alt="remove" width="16" height="16" src={removeicon} />
                  </button>
                </div>
                {keyword.error != null && props.keywordError !== "" ? (
                  <div className="mt-1 text-sm text-tiilt-danger">
                    {props.keywordError}
                  </div>
                ) : (
                  <></>
                )}
              </div>
            ))}
          </div>

          <button
            className={dlgCancel + " w-full"}
            onClick={props.addNewKeyword}
          >
            + Add keyword
          </button>
        </div>
      ) : (
        <div className="py-10 text-center text-sm text-tiilt-muted">Loading…</div>
      )}
      </div>
      </div>
    </div>
  )
}

export { KeywordListPages }
