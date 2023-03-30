import React from 'react';
import style from './topic-list.module.css'
import { Appheader } from '../header/header-component'
import { isLargeScreen, adjDim } from '../myhooks/custom-hooks';
import { AppContextMenu } from '../components/context-menu/context-menu-component';
import style2 from '../components/context-menu/context-menu.module.css';
import {DialogBox} from '../dialog/dialog-component';

function TopicListPage(props) {
	return (
	  <>
	    <div className={style.container}>
	      <Appheader
		title={"Topic List"}
		leftText={false}
		rightText={""}
		rightEnabled={false}
		//needs to be something to navigate, an issue
		nav={() => {props.toggleDisplay(true, "close", -1)}}
	      />
	      <div className={style["list-container"]}>
	      {props.topicListStruct.map((testArr, count) => (
		<div key={"model" + count} className={testArr.clicked ? `${style["model-selected"]} ${style["model-list-button"]}` : style["model-list-button"]} onClick={() => props.toggleClicked(count)}>
		  <div className={style["model-list-header"]}>
		    <div className={style.title}>{testArr.tname}</div>
		    <div className={style.date}>{testArr.prob}</div>
		  </div>
		  <div className={style["model-list-elements-one"]}>{props.stringFormat(testArr.kwds, testArr.kwdprobs, false)}</div>
		  <div className={style["model-list-elements-two"]}>{props.stringFormat(testArr.kwds, testArr.kwdprobs, true)}</div>
		  <AppContextMenu className={style["model-list-options"]}>
		    <div className={`${style2["menu-item"]} ${style2["menu-item"]}`} onClick={() => {props.toggleDisplay(true, "rename", count)}}>Rename</div>
		  </AppContextMenu >
		</div>
		))}
	      </div>
	      <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} onClick={() => {props.toggleDisplay(true, "submit", -1)}}>
		  Submit
	    </button>
	    </div>
	    
	    <DialogBox 
		show = {props.showDialog}
		heading = {props.currentDialog == 'rename' ? 'Rename' : (props.currentDialog == 'submit' ? 'Submit' : 'Close')}
		message = {props.currentDialog == 'rename' ?
		<React.Fragment>
		<div className={style.container}>
		<input id="txtName" className={style["text-input"]} style = {{width: adjDim(279) + 'px',}} defaultValue={props.topicListStruct[props.showedInd].tname} onKeyUp={(event) => props.setCurrInput(event.target.value)} maxLength='64' />
		<div>
		<button className={style["basic-button"]} style = {{width: adjDim(343) + 'px',}} onClick={() => {props.setTopicName()}} >Confirm</button >
		</div>
		{(props.changedName) ? "Name changed to " + props.topicListStruct[props.showedInd].tname : ""}
		</div>
		</React.Fragment>
		: (props.currentDialog == 'submit' ? 
		<React.Fragment>
		<div className={style.container}>
		  {"Are you sure you want to go forward with the following topics: " + props.getSelectNameList()}
		  <div>
		    {"If yes, select a name for your topics."}
		    <input id="txtName" className={style["text-input"]} style = {{width: adjDim(279) + 'px',}} defaultValue={""} onKeyUp={(event) => props.setNameInput(event.target.value)} maxLength='64' />
		  </div>
		  <div>
		    <button className={style["basic-button"]} style = {{width: adjDim(343) + 'px',}} onClick={() => {props.saveNewModel()}} >Submit Topics</button >
		  </div>
		</div>
		</React.Fragment> : 
		<React.Fragment>
		<div className={style.container}>
		  {"Are you sure you want to go back? All topics will be lost."}
		  <div>
		    <button className={style["basic-button"]} style = {{width: adjDim(343) + 'px',}} onClick={() => {props.navigateToFileUpload()}} >Yes</button >
		  </div>
		</div>
		</React.Fragment>)}
		closedialog = {()=> props.toggleDisplay(false, "", -1)}
	     /> 
	   </>
	  )
}

export { TopicListPage }
