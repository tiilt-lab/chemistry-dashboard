import style from './discussion-graph.module.css'
import style2 from '../dialog/dialog.module.css'
import {GenericDialogBox} from '../dialog/dialog-component'
import { Appheader } from '../header/header-component'
import React from 'react'

function DiscussionPage(props){

  return(
  <>
    <div>
    <Appheader 
        title={"Discussion Graph"}
        leftText={false}
        rightText={"Options"}
        rightEnabled={true}
        rightTextClick={()=>{props.openForms("devices")}}
        nav={props.navigateToSession} 
        headerclass={"discussion-graph-header"}
      />
</div>
<div className={style["page-container"]}>
  <div className={style["header-container"]}>
    <span className={style["header-spacer"]}></span>
    {
      props.displayDevices.map((device, index)=>(
        <div  key={index} className={style["header-text"]} onClick={()=> props.openForms("stats", device)}>{ device.name }</div>
      ))
    } 
  </div>
  <div className={style["graph-container"]}>
    <div className={style["timeline"]}>
      {
          props.timestamps.map((timestamp, index)=>(
            <div  key={index} className={style.timestamp}>{ timestamp }</div>
          ))
        }
    </div>

    {
      props.displayDevices.map((device, index)=>(
        <div  key={index} className={style["transcript-column"]} >
          {
            props.device.transcripts.map((transcript,index)=>(
              <div key={index} className={style.transcript} style={{marginTop: `${transcript.start_time * 20}`+"px" , height: `${transcript.length * 20}`+"px"}} >
                  <div className={style["tr]anscript-text"]}>
                      {transcript.question ? <div className={style["question-mark"]} onClick={()=> props.highlightQuestions(transcript)}>?</div> : <></>}
                      {transcript.speaker_tag ?  <span className={style["speaker-tag"]}>{transcript.speaker_tag}: </span> : <></> }
                        { transcript.transcript.map((transcriptData, index)=>{
                          <React.Fragment key={index}>
                            {(transcriptData.matchingKeywords !== null) ? <span className={transcriptData.highlight ? `${style["keyword-text"]} ${style["question-highlight"]}` : style["keyword-text"]} style={{color: `${transcriptData.color}`}} onClick={()=> props.openForms("keywords", transcriptData.matchingKeywords)}>{transcriptData.word}</span> : <></> }
                            {(transcriptData.matchingKeywords === null) ? <span className={transcriptData.highlight? style["question-highlight"] : ""}> {transcriptData.word} </span> : <></> }
                          </React.Fragment>
                        })
                      
                        }
                    </div>
                </div>
            ))
          }                                         
        </div>
      ))
    }
  </div>
</div>

 <GenericDialogBox show = {props.currentForm !== ""}>
   {/* Keyword dialog */}
   {(props.currentForm === "keywords") ?
     <div>
        <div className={style2["dialog-heading"]}>Keyword Data</div>
        <div className={style2["dialog-body"]}><span className={style.bold}>Word:</span> {props.displayKeywords[0].word} </div>
        <div className={style2["dialog-body"]}><span className={style.bold}>Keywords (Similarity):</span></div>
        <div className={style2["dialog-body"]}>
          {props.displayKeywords.map((keyword, index)=>(
            <span key={index}>
              {keyword.keyword} ({keyword.similarity}%) {index === (Object.keys(props.displayKeywords).length - 1) ? '' : ','}
          </span>
          ))
          }
        </div>
     </div>
     :
     <></>
   }

    {/* Stats dialog */}
    { props.currentForm === "stats" ?
      <div>
          <div className={style2["dialog-heading"]}> Statistics for {props.selectedDevice !== undefined ? props.selectedDevice.name : "" } </div>
          <div className={style["basic-button"]} onClick={()=> props.toggleGraph(!props.showGraph, props.selectedDevice)}> Contributions: {props.contributions}</div>
          <br></br>
          {props.showGraph ?
              <React.Fragment>
                <div className={style["graph-box"]}>
                  <svg viewBox="-1 -1 2 2" style={{transform: "rotate(-90deg)"}} className={style["pie-chart"]}>
                    {props.displayDevices.map((device, index)=>(
                      <path d= {device.path} fill={device.color}  className={style["pie-piece"]} onClick={()=> props.toggleGraph(true, device)} stroke="transparent" ></path>
                    ))
                    } 
                  </svg>
                  <span className={style["pie-piece-text"]}> { props.selectedPercent}% </span>
                </div> 
                <h3>Key</h3>
                <div className={style["graph-legend"]}>
                    { props.displayDevices.map((device, index)=>(
                      <React.Fragment key={index}>
                         <div className={style["color-box"]} style={{backgroundColor: `${device.color}`}}> </div>
                        {device.selected ? <div className={style.name}  style={{fontWeight: "bold"}}> {device.name} </div> : <></> }
                        {!device.selected ? <div className={style.name} > {device.name}</div> : <></> } 
                      </React.Fragment>
                      ))
                    }
                </div>
                <div className={style["individual-stat"]}> { props.selectedDevice.name } spoke for { props.selectedPercent }% of the total conversation of displayed speakers</div>
                <br></br>
              </React.Fragment>
              :
              <></>
            }

          <div className={style["basic-button"]} onClick={props.toggleQuestions}> Questions: { props.displayQuestions.length } </div>
          <br></br>
          {props.showQuestions ?
              <div className={style["question-container"]}>
                  {
                    props.displayQuestions.map((question, index)=>(
                      <div  className={style["question-item"]}>{ question }</div>
                    ))
                  }
                <br></br>
              </div>
              :
              <></> 
          }
     
      </div>
      :
      <></>
    }

    {/* Devices dialog  */}
    {props.currentForm === "devices" ?
        <div>
          <div className={style2["dialog-heading"]}>Display devices</div>
          {props.sessionDevices!== undefined ?
            props.sessionDevices.map((device, index)=>(
              <label key={index} className={style["dc-checkbox"]}> { device.name }
                  <input type="checkbox" defaultValue={device.visible} onChange={props.updateGraph}/>
                  <span className={style["checkmark"]}></span>
             </label>
            ))
            :
            <></>
          }
        </div>
      :
        <></>
    }     
   <div className={style["delete-button"]} onClick={props.closeForm}>Close</div>
 </GenericDialogBox>
  </>
)
}

export {DiscussionPage}

