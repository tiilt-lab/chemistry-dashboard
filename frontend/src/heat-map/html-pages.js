import {AppContextMenu} from '../components/context-menu/context-menu-component'
import {DialogBox} from '../dialog/dialog-component'
import style from './heat-map.module.css'
import questIcon from "../assets/img/question.svg"
import React from 'react'
import { adjDim } from '../myhooks/custom-hooks';

function HeatMapPage(props){
  return(
      <>
      <div className={style["heatmap-container"]} style={{height: (props.showTools ? "190px" : "160px"), width: adjDim(340) + 'px',}}>
      <svg className={style.graph} 
      style={{ width: adjDim(112) + 'px', height: adjDim(112) + 'px', left: adjDim(114) + 'px',}}>
        <radialGradient id="heatGradient" cx={adjDim(56) + ""} cy={adjDim(56) + ""} gradientUnits="userSpaceOnUse">
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
        <g transform={"rotate(-90, " + adjDim(56) + ", " + adjDim(56) + ")"}>
          <path d={props.clipPath} fill="url(#heatGradient)"/>
          <path d={props.segmentPath} fill="none" strokeWidth="1" stroke="rgb(222,222,222)"/>
        </g>
        <circle cx={adjDim(56) + ""} cy={adjDim(56) + ""} r= {adjDim(56) + ""} stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
        <circle cx={adjDim(56) + ""} cy={adjDim(56) + ""} r= {adjDim(52) + ""} stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
        <circle cx={adjDim(56) + ""} cy={adjDim(56) + ""} r= {adjDim(47) + ""} stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
        <circle cx={adjDim(56) + ""} cy={adjDim(56) + ""} r= {adjDim(40) + ""} stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
        <circle cx={adjDim(56) + ""} cy={adjDim(56) + ""} r= {adjDim(29) + ""} stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
        <circle cx={adjDim(56) + ""} cy={adjDim(56) + ""} r= {adjDim(16) + ""} stroke="#E8E9EB" strokeWidth="1" fillOpacity="0"/>
      </svg>

      <div className={style["angle-text"]} style={{right: adjDim(156) + "px", top:"0px"}}>front</div>
      <div className={style["angle-text"]} style={{left: adjDim(234) + "px", top:"70px"}}>right</div>
      <div className={style["angle-text"]} style={{right: adjDim(157) + "px", top:"136px"}}>back</div>
      <div className={style["angle-text"]} style={{right: adjDim(237) + "px", top:"71px"}}>left</div>
      {props.showTools ?
             <React.Fragment>
             <hr className={style["tool-hr"]}></hr>
             <div className={style["angle-text"]} style={{left:'0px', top:'160px'}}> Zones: {props.segments}</div>
             <input className={`${style["segment-input"]} ${style["dc-slider"]}`} style = {{width: adjDim(100) + 'px',}} type="range" defaultValue={props.segments} min='2' max='24' onChange={(event)=> props.segmentChange(event)}  />
             <div className={style["angle-text"]} style={{right:'0px', top:'160px'}} style = {{width: adjDim(100) + 'px',}} >Offset</div>
             <input className={`${style["offset-input"]} ${style["dc-slider"]}`} type="range"  min='0' max='1' step='0.01' defaultValue={props.angleOffset} onChange={(event)=> props.offsetChange(event)} />
           </React.Fragment>
        :
          <></>
      }
     

      <img onClick={()=> props.toggleDisplay(true)} className={style["info-button"]} alt='question' src={questIcon}/>
      <div className={style["graph-menu"]}>
      <AppContextMenu  setcallback = {props.setCallbackFunc}>
          <div className={style["menu-item"]} onClick={()=>{props.setShowTools(!props.showTools); if(props.callbackfunc){props.callbackfunc(false)}}}>{(props.showTools)? 'Hide Tools': 'Show Tools'}</div>
          <div className={style["menu-item"]} onClick={()=>{props.resetDiagram(); if(props.callbackfunc){props.callbackfunc(false)}}}>Reset</div>
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
