import style from './pods.module.css'
import { AppContextMenu } from '../components/context-menu/context-menu-component'
import { Appheader } from '../header/header-component'
import { GenericDialogBox } from '../dialog/dialog-component'
import IconPod from "../Icons/IconPod"
import LightIcon from "../Icons/Light"
import React from 'react'
import { isLargeScreen } from '../myhooks/custom-hooks';

function PodComponentPage(props) {

  return (
    <>
      <div className={style.container}>
        <Appheader
          title={"Manage Pods"}
          leftText={false}
          rightEnabled={false}
          nav={props.navigateToHomescreen}
        />


        <div className={style["list-container"]}>
          <ul className={style.list}>
            {
              props.devices.map((device, index) => (
                <li key={index} className={style["pod-item"]}>
                  <svg x="0" y="0" width="20" height="18" viewBox="0 0 20 18" className={!device.connected ? `${style["pod-icon pod-connected"]}` `${style["pod-disconnected"]}` : style["pod-icon pod-connected"]}>
                    <IconPod></IconPod>
                  </svg>
                  <div className={style["pod-text"]}>{device.name}</div>
                  <div className={style["button-container"]}>
                    {device.connected ?
                      <button className={device.blinking ? `${style["pod-button"]}` `${style["selected-button"]}` : style["pod-button"]} onClick={() => props.blinkPod(device)} >
                        <svg x="0" y="0" width="20" height="20" viewBox="0 0 512 512" className={style["light-svg"]}>
                          <LightIcon></LightIcon>
                        </svg>
                      </button>
                      : <></>
                    }
                    <AppContextMenu>
                      <div className={style["menu-item"]} onClick={() => props.openDialog("Rename", device)}>Rename</div>
                      {props.user.isAdmin || props.user.isSuper ? <div className={style["menu-item red"]} onClick={() => props.openDialog("Remove", device)}>Remove</div> : <></>}
                    </AppContextMenu>
                  </div>
                </li>
              ))
            }

          </ul>
          {props.devices === undefined ? <div className={props.loading ? style.loading : style["load-text onload"]} >Loading...</div> : <></>}
          {props.devices !== undefined && props.devices.length == 0 ?
            <div className={style["empty-pod-list"]} >
              <div className={style["load-text"]}>There are no pods.</div>
              <div className={style["load-text-description"]}>Add pods by clicking the button below.</div>
            </div>
            :
            <></>
          }
        </div>
        {props.user.isAdmin || props.user.isSuper ? <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} onClick={() => props.openDialog("Add")}>Add via MAC address</button> : <></>}
      </div>

      <GenericDialogBox show={props.currentForm !== ""}>
        <div className={style["dialog-window"]}>
          {props.currentForm === "Remove" ?
            <React.Fragment>
              <div className={style["dialog-heading"]}>Remove Pod</div>
              <div className={style["dialog-body"]}>Are you sure you want to remove this pod?</div>
              <button className={style["delete-button"]} onClick={props.removeDevice}>Remove</button>
              <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
            </React.Fragment>
            :
            <></>
          }
          {props.currentForm === "Add" ?
            <React.Fragment>
              <div className={style["dialog-heading"]}>Pod MAC address:</div>
              <input id='macInput' className={style["text-input"]} type="text"
                onKeyDown={(event) => { if (event.key === 'Enter') { props.addDevice(document.getElementById('macInput').value) } }} />
              <div className={style["input-status-text"]}>{props.statusText}</div>
              <button className={style["basic-button"]} onClick={() => props.addDevice(document.getElementById('macInput').value)}>Add</button>
              <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
            </React.Fragment>
            :
            <></>
          }
          {props.currentForm === "Rename" ?
            <React.Fragment>
              <div className={style["dialog-heading"]}>Pod Name:</div>
              <input id='nameInput' className={style["text-input"]} value={props.selectedDevice.name} type="text"
                onKeyDown={(event) => { if (event.key === 'Enter') { props.renameDevice(document.getElementById('nameInput').value) } }} />
              <div className={style["input-status-text"]}>{props.statusText}</div>
              <button className={style["basic-button"]} onClick={() => props.renameDevice(document.getElementById('nameInput').value)}>Rename</button>
              <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
            </React.Fragment>
            :
            <></>
          }
        </div>
      </GenericDialogBox>
    </>
  )
}

export {PodComponentPage}
