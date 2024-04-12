import React from 'react';
import { Appheader } from '../header/header-component';
import { GenericDialogBox } from '../dialog/dialog-component';
import { AppFolderSelectComponent } from '../components/folder-select/folder-select-component'
import style from './create-session.module.css'
import style2 from '../dialog/dialog.module.css'
import openFolderIcon from '../assets/img/open-folder.svg'
import podIcon from "../assets/img/icon-pod.svg"
import lightIcon from "../assets/img/light.svg"
import { adjDim } from '../myhooks/custom-hooks';

function CreateSessionPage(props) {
  return (
    <>
      <div className={style.container}>
        <Appheader
          title={props.pageTitle}
          leftText={false}
          rightText={""}
          rightEnabled={false}
          nav={props.navigateToSessions}
        />
        {(props.currentMenu === "Settings") ?
          <React.Fragment >
            <div className={style["list-container"]}>
              <div>Discussion name:</div>
              <input id="txtName" className={style["text-input"]} style = {{width: adjDim(350) + 'px',}} defaultValue={props.sessionName} onKeyUp={(event) => props.setSessionName(event.target.value)} maxLength='64' />
              <div>Folder: </div>
              <span className={style["path-container"]} style = {{width: adjDim(375) + 'px',}}>
                <input type="text" className={style["folder-input"]} style = {{width: adjDim(318) + 'px',}} name="Location" placeholder={props.folderPath} readOnly />
                <img src={openFolderIcon} id={style["open-folder-icon"]} onClick={() => props.openDialog("Folder", "test")} />
              </span>
              <label className={style["dc-checkbox"]}>Allow participant devices
                <input type="checkbox" checked={props.byod} value={props.byod} onChange={() => props.setByod(!props.byod)} />
                <span className={style.checkmark}></span>
              </label>
              <label className={style["dc-checkbox"]}>Analyze discussion features
                <input type="checkbox" checked={props.features} value={props.features} onChange={() => props.setFeatures(!props.features)} />
                <span className={style.checkmark}></span>
              </label>
            </div>
            <div className={style["button-side-container"]}>
              <button className={style["footer-button"]} style={{width: adjDim(374/2) + 'px', 'margin-right': '5px',}} onClick={props.navigateToSessions} >Back</button>
              <button className={style["footer-button"]} style={{width: adjDim(374/2) + 'px', 'margin-left': '5px',}} onClick={props.goToKeywords}>Next</button>
             </div>
          </React.Fragment>
          :
          <></>
        }
        {(props.currentMenu == "Keywords") ?
          <React.Fragment>
            <div className={style["list-container"]}>
              {(props.keywordLists && props.keywordLists.length == 0) ?
                <div className={style["empty-keyword-list"]} >
                  <div className={style["load-text"]} > No Keyword Lists </div>
                  <div className={style["load-text-description"]} > Tap the button below to make your first keyword list. </div>
                </div>
                :
                <></>
              }
              {
                props.keywordLists.map((keywordList, index) => (
                  <div key={index} className={JSON.stringify(props.selectedKeywordList) === JSON.stringify(keywordList) ? `${style["keywords-selected"]} ${style["keyword-list-button"]}` : style["keyword-list-button"]} onClick={() => props.setSelectedKeywordList(props.selectedKeywordList === keywordList ? null : keywordList)}>
                    <div className={style["keyword-list-header"]} >
                      <span className={style.title}>{keywordList.name}</span>
                      <span className={style.date}> - {props.formatKeywordDate(keywordList.creation_date)}</span>
                    </div>
                    <div className={style["keyword-list-keywords"]} >{keywordList.keywordsText}</div>
                  </div>
                ))
              }
            </div>

            <button className={style["footer-button"]} style={{width: adjDim(374) + 'px',}} onClick={props.navigateToKeywordLists}>Create Keyword List</button>
            <div className={style["button-side-container"]}>
              <button className={style["footer-button"]} style={{width: adjDim(374/2) + 'px', 'margin-right': '5px',}} onClick={props.goToSettings}>Back</button>
              <button className={style["footer-button"]} style={{width: adjDim(374/2) + 'px', 'margin-left': '5px',}} onClick={props.goToTopModels}>Next</button>
            </div>
          </React.Fragment>
          :
          <></>
        }
        
        {(props.currentMenu == "TopModels") ?
          <React.Fragment>
            <div className={style["list-container"]}>
              {(props.topicModels && props.topicModels.length == 0) ?
                <div className={style["empty-keyword-list"]} >
                  <div className={style["load-text"]} > No Topic Models </div>
                  <div className={style["load-text-description"]} > Tap the button below to make your first topic model. </div>
                </div>
                :
                <></>
              }
              {
                props.topicModels.map((topicModel, index) => (
                  <div key={index} className={JSON.stringify(props.selectedTopicModel) === JSON.stringify(topicModel) ? `${style["keywords-selected"]} ${style["keyword-list-button"]}` : style["keyword-list-button"]} onClick={() => props.setSelectedTopicModel(props.selectedTopicModel === topicModel ? null : topicModel)}>
                    <div className={style["keyword-list-header"]} >
                      <span className={style.title}>{topicModel.name}</span>
                      <span className={style.date}> - {props.formatKeywordDate(topicModel.creation_date)}</span>
                    </div>
                    <div className={style["keyword-list-keywords"]} >{topicModel.summary}</div>
                  </div>
                ))
              }
            </div>

            <button className={style["footer-button"]} style={{width: adjDim(374) + 'px',}} onClick={props.navigateToFileUpload}>Create Topic Model</button>
            <div className={style["button-side-container"]}>
              <button className={style["footer-button"]} style={{width: adjDim(374/2) + 'px', 'margin-right': '5px',}} onClick={props.goToKeywords}>Back</button>
              <button className={style["footer-button"]} style={{width: adjDim(374/2) + 'px', 'margin-left': '5px',}} onClick={props.goToDevices}>Next</button>
            </div>
          </React.Fragment>
          :
          <></>
        }

        {(props.currentMenu === "Devices") ?
          <React.Fragment>
            <div className={style["list-container"]}>
              {props.devices.length === 0 ?
                <div className={style["empty-keyword-list"]}>
                  <div className={style["load-text"]}> No Devices </div>
                </div>
                :
                <></>
              }
              {props.devices.length > 0 ?
                <ul className={style.list}>
                  {props.devices.map((device) => {
                    <li className={props.selectedDevices.includes(device) ? style["selected-pod"] : style["pod-item"]} onClick={() => props.deviceSelected(device)} >
                      <img className={style["pod-icon"]} src={podIcon} />
                      <div className={style["pod-text"]}>{device.name}</div>
                      <div className={style["button-container"]}>
                        <button className={device.blinking ? style["selected-button"] : style["pod-button"]} onClick={(event) => props.blinkPod(event, device)}>
                          <svg x="0" y="0" width="20" height="20" viewBox="0 0 512 512" className={style["light-svg"]}>
                            <use xlinkHref={`${lightIcon}#light-icon`}></use>
                          </svg>
                        </button>
                      </div>
                    </li>
                  })
                  }
                </ul>
                :
                <></>}

            </div>
            <button className={style["select-all"]} onClick={props.onClickSelectAll}>Select All</button>
            <button className={style["footer-button"]} style={{width: adjDim(374) + 'px',}} onClick={props.goToTopModels}>Back</button>
            <button className={style["footer-button"]} style={{width: adjDim(374) + 'px',}} onClick={props.createSession}>Start Discussion</button>
          </React.Fragment>
          :
          <></>
        }
      </div>

      <GenericDialogBox show={props.currentForm !== ""} >
        {(props.currentForm === "Error") ?
          <div className={style["add-dialog"]} >
            <div className={style2["dialog-heading"]} >Invalid Sesion</div>
            {props.displayText}
            <button className={style["cancel-button"]} onClick={props.closeDialog}> Close</button >
          </div >
          :
          <></>
        }

        {(props.currentForm === "Folder") ?
          <div className={style["dialog-window"]} >
            <div className={style2["dialog-heading"]}>Select Folder</div>
            <AppFolderSelectComponent
              selectableFolders={props.folders}
              setFolderSelect={props.setFolderSelect}
              setBreadCrumbSelect={props.setBreadCrumbSelect}
            />
            {/* <app-folder-select #folderSelect [folders]="folders" (itemSelected)="receiveEmmitedFolder($event)"></app-folder-select> */}
            {(props.folderSelect) ? <button className={style["dialog-button"]} onClick={() => props.setFolderLocation(props.folderSelect, props.breadCrumbSelect)}>OK</button> : <></>}
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div >
          :
          <></>
        }
      </GenericDialogBox>
    </>
  )
}

export { CreateSessionPage } 

