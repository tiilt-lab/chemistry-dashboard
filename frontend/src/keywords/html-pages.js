import React from 'react'
import style from './keywords.module.css'
import {AppContextMenu} from '../components/context-menu/context-menu-component'

function AppKeywordsPage(props) {
  
  return (
    <div className={style["keyword-container"]}>
      {!props.showGraph ?
        <React.Fragment>
          {
            props.displayKeywords.map((displayKeyword, index) => (
              <span key={index} className={style["keyword"]} style={{ color: `${displayKeyword.color}` }} onClick={() => props.showKeywordContext(displayKeyword.transcript_id)}>
                {displayKeyword.word}
                {index !== (Object.keys(props.displayKeywords).length - 1) ? <span className={style["base"]}>, </span> : <></>}
              </span>
            ))
          }

          {props.displayKeywords.length == 0 ? <div className={style["no-keywords"]}>No keywords detected</div> : <></>}
        </React.Fragment>
        :
        <></>
      }

      {props.showGraph ?
        <React.Fragment>
          <div className={style["timeline-container"]}>
            {props.session.keywords.map((keyword, index) => (
              <div key={index} className={style["keyword-timeline"]}>
                <div className={style["keyword-text"]}>{keyword}</div>
                <div className={style["keyword-graph"]}>
                  <hr />
                  {props.keywordPoints[keyword].map((point, index) => (
                    <div key={index}
                      className={style["keyword-point"]}
                      style={{ left: `${point.x}` + 'px', backgroundColor: `${point.color}` }}
                      onClick={() => props.showKeywordContext(point.transcript_id)}>
                    </div>
                  ))}
                </div>
              </div>
            ))}


          </div>
          {props.session.keywords.length == 0 ? <div className={style["no-keywords"]}>No keywords detected</div> : <></>}
        </React.Fragment>
        :
        <></>
      }
      <div className={style["graph-menu"]}>
        <AppContextMenu setcallback={props.setCallbackFunc}>
          <div className={style["menu-item"]} onClick={() => { props.toggleGraph(); props.callbackfunc(false); }}>{(props.showGraph) ? 'Show Words' : 'Show Timeline'}</div>
        </AppContextMenu>
      </div>
    </div>
  )
}

export { AppKeywordsPage }