
import style from './keyword-list-items.module.css';
import { Appheader } from '../header/header-component';
import removeicon from '../assets/img/remove.svg'
import React from 'react';

function KeywordListPages(props) {

  return (
    <div className={style.container}>
      <Appheader
        title={"Manage Keyword Lists"}
        leftText={"Cancel"}
        rightText={"Save"}
        rightEnabled={props.isValid}
        rightTextClick={props.saveKeywordList}
        nav={props.navigate}
      />
      {
        (props.keywordList && props.keywordListItems) ?
          <React.Fragment>
            {(!props.keywordList) ? <div className={style["load-text onload"]}>Loading...</div> : <></>}
            {(props.keywordListItems && props.keywordListItems.length === 0) ?
              <div className={style["empty-keyword-list"]} >
                <div className={style["load-text"]}>Type a title for your list and click Add Keyword below to add keywords.</div>
              </div>
              : <></>
            }

            <input className={style["keyword-lists-title"]} defaultValue={props.keywordList.name === undefined ? '' : props.keywordList.name} placeholder="Enter new list name" maxLength='64' type="text" onKeyUp={props.checkName} />
            <div className={style["keyword-lists-container"]}>
              {props.keywordListItems.map((keyword,count)=>(
                <div key={"keyword" + count} className={style["change-keywords-container"]}>
                <input touched="true" type="text" defaultValue={keyword.keyword === undefined ? '' : keyword.keyword} autoComplete="off" onKeyUp={(event) => props.checkKeyword(keyword, event)} maxLength='64' />
                <img alt='remove' width='16' height='16' src={removeicon} onClick={() => props.removeKeyword(keyword)} />
                {(keyword.error != null && props.keywordError !== "") ? <div className={style["add-new-keywords-status"]}>{props.keywordError}</div> : <></>}
              </div>
              ))}
            </div>
            <button className={`${style["basic-button"]} ${style["medium-button"]}`} onClick={props.addNewKeyword}>Add Keyword</button>
          </React.Fragment>
          :
          <></>
      }
    </div>
  )
}

export { KeywordListPages }




