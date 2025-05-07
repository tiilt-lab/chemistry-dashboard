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
		title={props.editMode ? "Topic List" : props.viewTitle}
		leftText={false}
		// just to give the user tips (/instructions) on how to use this
		rightText={props.editMode ? "Tips" : ""}
		rightEnabled={props.editMode}
                rightTextClick={ props.editMode ? (()=>{props.toggleDisplay(true, "tips", -1)}) : null}
		// to make an input for the edit mode
		editMode = {props.editMode}
		changeInputVal = {(val) => props.setNameInput(val)}
		//needs to be something to navigate, an issue
		nav={() => {props.editMode ? props.toggleDisplay(true, "close", -1) : props.navTopicModels()}}
	      />
	      <div className={style["list-container"]}>
	      {props.topicListStruct.map((testArr, count) => (
		<div key={"model" + count} className={testArr.clicked ? `${style["model-selected"]} ${style["model-list-button"]}` : style["model-list-button"]} onClick={() => props.editMode ? props.toggleClicked(count) : null}>
		  <div className={style["model-list-header"]}>
		    <div className={style.title}>{testArr.tname}</div>
		  </div>
		  <div className={style["model-list-elements-one"]}>{props.stringFormat(testArr.kwds, testArr.kwdprobs, false)}</div>
		  <div className={style["model-list-elements-two"]}>{props.stringFormat(testArr.kwds, testArr.kwdprobs, true)}</div>
		  {props.editMode ? 
		  (<AppContextMenu className={style["model-list-options"]} reverseToggle = {() => props.toggleClicked(count)}>
		    <div className={`${style2["menu-item"]} ${style2["menu-item"]}`} onClick={() => {props.toggleDisplay(true, "rename", count)}}>Rename</div>
		  </AppContextMenu >)
		  : null}
		</div>
		))}
	      </div>
	      {props.editMode ? 
	      (<button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} onClick={() => {props.toggleDisplay(true, "submit", -1)}}>
		  Submit
	      </button>)
	      : null}
	    </div>
	    
	    <DialogBox 
		show = {props.showDialog}
		heading = {props.currentDialog == 'rename' ? 'Rename' : (props.currentDialog == 'submit' ? 'Submit' : (props.currentDialog == 'tips' ? 'Tips' : 'Close'))}
		message = {props.currentDialog == 'rename' ?
		<React.Fragment>
		<div className={style.container}>
		<input id="txtName" className={style["text-input"]} style = {{width: adjDim(279) + 'px',}} defaultValue={props.topicListStruct[props.showedInd].tname} onKeyUp={(event) => props.setCurrInput(event.target.value)} maxLength='64' />
		<div>
		<button className={style["basic-button"]} style = {{width: adjDim(343) + 'px', 'margin-bottom': ((props.changedName) ? 10 : 0) + 'px',}} onClick={() => {props.setTopicName()}} >Confirm</button >
		</div>
		  {(props.wrongInput) ? "There can only be letters or numbers in your topic name." : ""}
		  {(props.changedName) ? "Name changed to " + props.topicListStruct[props.showedInd].tname : ""}
		</div>
		</React.Fragment>
		: (props.currentDialog == 'submit' ? 
		<React.Fragment>
		<div className={style.container}>
		  {"Are you sure you want to go forward with the following topics: " + props.getSelectNameList(true)}
		  {props.noName ? 
		  <React.Fragment>
		    <div>
		      {"If yes, select a name for your topics."}
		      <input id="txtName" className={style["text-input"]} style = {{width: adjDim(279) + 'px',}} defaultValue={""} onKeyUp={(event) => props.setNameInput(event.target.value)} maxLength='64' />
		    </div>
		  </React.Fragment> : <></>}
		  <div>
		    <button className={style["basic-button"]} style = {{width: adjDim(343) + 'px', 'margin-top': (props.noName ? 0 : 10) + 'px', 'margin-bottom': ((props.noTopics || props.wrongInput) ? 10 : 0) + 'px',}} onClick={() => {props.saveNewModel()}} >Submit Topics</button >
		  </div>
		  {(props.noTopics) ? "You must select topics before submitting." : ""}
		  {(props.wrongInput) ? "Your topic list name can't be empty." : ""}
		</div>
		</React.Fragment> : 
		(props.currentDialog == 'tips' ?
		<div className={style.container}>
		  <div> {'Click on "Topic List" to change the name of your topic model.'} </div>
		  <div> {'Then, select (and\/or rename) which topics you\'d like to include in your model.'} </div>
		</div>
		:
		<React.Fragment>
		<div className={style.container}>
		  {"Are you sure you want to go back? All topics will be lost."}
		  <div>
		    <button className={style["basic-button"]} style = {{width: adjDim(343) + 'px', 'margin-top': '10px',}} onClick={() => {props.navigateToFileUpload()}} >Yes</button >
		  </div>
		</div>
		</React.Fragment>))}
		closedialog = {()=> props.toggleDisplay(false, "", -1)}
	     /> 
	   </>
	  )
}

export { TopicListPage }
