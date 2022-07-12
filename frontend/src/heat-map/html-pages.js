import {AppContextMenu} from '../components/context-menu/context-menu-component'
import {DialogBox} from '../dialog/dialog-component'
import style from './heat-map.module.css'
import questIcon from "../assets/img/question.svg"
import React from 'react'

function HeatMapPage(props){
  return(
      <>
      <div className={style["heatmap-container"]} style={props.showTools ? {height:"190px"} : {height:"160px"}}>
      <svg className={style.graph} height="112" width="112">
        <radialGradient id="heatGradient" cx="56" cy="56" gradientUnits="userSpaceOnUse">
          <stop offset="17%" stopColor="#9ddaf4"/>
          <stop offset="17%" stopColor="#c1c7f0"/>
          <stop offset="29%" stopColor="#c1c7f0"/>
          <stop offset="29%" stopColor="#e1b4df"/>
          <stop offset="40%" stopColor="#e1b4df"/>
          <stop offset="40%" stopColor="#f6a3c1"/>
          <stop offset="47%" stopColor="#f6a3c1"/>
          <stop offset="67%" stopColor="#fc979f"/>
          <stop offset="83.33%" stopColor="#fc979f"/>
          <stop offset="84%" stopColor="#f47c69"/>
          <stop offset="100%" stopColor="#f47c69"/>
        </radialGradient>
        <g transform="rotate(-90, 56, 56)">
          <path d={props.clipPath} fill="url(#heatGradient)"/>
          <path d={props.segmentPath} fill="none" strokeWidth="1" stroke="rgb(222,222,222)"/>
        </g>
        <circle cx="56" cy="56" r="56" stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
        <circle cx="56" cy="56" r="52" stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
        <circle cx="56" cy="56" r="47" stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
        <circle cx="56" cy="56" r="40" stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
        <circle cx="56" cy="56" r="29" stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
        <circle cx="56" cy="56" r="16" stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
      </svg>

      <div className={style["angle-text"]} style={{right:"156px", top:"0px"}}>front</div>
      <div className={style["angle-text"]} style={{left:"234px", top:"70px"}}>right</div>
      <div className={style["angle-text"]} style={{right:"157px", top:"136px"}}>back</div>
      <div className={style["angle-text"]} style={{right:"237px", top:"71px"}}>left</div>
      {props.showTools ?
             <React.Fragment>
             <hr className={style["tool-hr"]}></hr>
             <div className={style["angle-text"]} style={{left:'0px', top:'160px'}}> Zones: {props.segments}</div>
             <input className={`${style["segment-input"]} ${style["dc-slider"]}`} type="range" defaultValue='8' min='2' max='24' onKeyUp={(event)=> props.segmentChange(event)}  />
             <div className={style["angle-text"]} style={{right:'0px', top:'160px'}}>Offset</div>
             <input className={`${style["offset-input"]} ${style["dc-slider"]}`} type="range"  min='0' max='1' step='0.01' onKeyUp={(event)=> props.offsetChange(event)} />
           </React.Fragment>
        :
          <></>
      }
     

      <img onClick={()=> props.toggleDisplay(true)} className={style["info-button"]} alt='question' src={questIcon}/>
      <div className={style["graph-menu"]}>
      <AppContextMenu  setcallback = {props.setCallbackFunc}>
          <div className={style["menu-item"]} onClick={()=>{props.setShowTools(!props.showTools); props.callbackfunc(false)}}>{(props.showTools)? 'Hide Tools': 'Show Tools'}</div>
          <div className={style["menu-item"]} onClick={()=>{props.resetDiagram(); props.callbackfunc(false)}}>Reset</div>
        </AppContextMenu>
      </div>
    </div>

     <DialogBox 
        show = {props.showDialog}
        heading = {'Direction of Arrival'}
        message = {'This graph displays the distribution of the conversation based on the direction of arrival of each transcript. The front of the room corresponds to the 0° mark on the pod.'}
        closedialog = {()=> props.toggleDisplay(false)}
     /> 
      </>

  )}

export {HeatMapPage}