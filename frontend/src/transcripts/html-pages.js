
import style from './transcripts.module.css'
import style2 from '../dialog/dialog.module.css'
import { GenericDialogBox } from '../dialog/dialog-component'
import {Appheader} from '../header/header-component'

function TranscriptComponentPage(props) {
  return (
    <>
      <div className={style.container}>
        <Appheader
          title={"Transcripts from" + " " + props.sessionDevice.name}
          leftText={false}
          rightText={"Options"}
          rightEnabled={props.isenabled}
          rightTextClick={props.openOptionsDialog}
          nav={props.navigateToSession}
        />

        <div className={style["transcript-list"]}>
          {props.displayTranscripts.map((transcript, index) => (
            <div key={index}>
              <div id={`${transcript.id}`} className={transcript.id === props.transcriptIndex ? `${style["transcript-container"]} ${style.highlighted}` : style["transcript-container"]} style={{ backgroundColor: `${transcript.doaColor}` }}>
                <div className={style.timestamp}>{props.formatSeconds(transcript.start_time)}</div>
                <div className={style["transcript-text"]}>
                  {transcript.speaker_tag ? <span className={style.bold}>{transcript.speaker_tag}: </span> : <></>}
                  {
                    transcript.words.map((transcriptData, index) => (
                      <span key={index}>
                        {transcriptData.matchingKeywords !== null ?
                          <span style={{ color: `${transcriptData.color}` }} onClick={() => props.openKeywordDialog(transcriptData.matchingKeywords)} className={style["highlight-keyword"]}>
                            {transcriptData.word+" "}
                          </span>
                          :
                          <></>}
                        {transcriptData.matchingKeywords === null ? <span>{transcriptData.word+" "}</span> : <></>}
                      </span>
                    ))
                  }

                </div>
              </div>
              {index !== (Object.keys(props.displayTranscripts).length - 1) ? <hr /> : <></>}
            </div>
          ))

          }
        </div>
      </div>

      <GenericDialogBox show={props.currentForm !== ""} >
        {props.currentForm == "Keyword" ?
          <div className={style2["dialog-box"]}>
            <div className={style2["dialog-heading"]}>Keyword Data</div>
            <div className={style2["dialog-body"]}><span className={style.bold}>Word:</span> {props.dialogKeywords[0].word} </div>
            <div className={style2["dialog-body"]}><span className={style.bold}>Keywords (Similarity):</span></div>
            <div className={style2["dialog-body"]}>
              {
                props.dialogKeywords.map((keyword, index) => (
                  <span key={index}>
                    {keyword.keyword} ({keyword.similarity}%) {index === (Object.keys(props.displayTranscripts).length - 1) ? '' : ','}
                  </span>
                ))
              }

            </div>
            <button className={style["delete-button"]} onClick={props.closeDialog}>Close</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "Options" ?
          <div className={style2["dialog-box"]}>
            <div className={style2["dialog-heading"]}>Transcript Options</div>
            <br />
            <label className={style["dc-checkbox"]}>Show keywords
              <input type="checkbox" checked={props.showKeywords} value={props.showKeywords} onChange={props.createDisplayTranscripts} />
              <span className={style["checkmark"]}></span>
            </label>
            <label className={style["dc-checkbox"]}>Show direction of arrival
              <input type="checkbox" checked={props.showDoA} value={props.showDoA} onChange={props.createDisplayTranscripts} />
              <span className={style["checkmark"]}></span>
            </label>
            <svg
              ref={props.legendRef}
              width = {100}
              height = {100 + (10 * 2)}>
            </svg>
            <br />
            <button className={style["delete-button"]} onClick={props.closeDialog}>Close</button>
          </div>
          :
          <></>
        }
      </GenericDialogBox>
    </>
  )
}
export {TranscriptComponentPage}
