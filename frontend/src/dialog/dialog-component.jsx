
import style from './dialog.module.css';

function DialogBox(props) {
  if (!props.show) {
    return (
      <></>
    )
  }

  return (
    <div className={style["dialog-background"]}>
      <div className={style["dialog-container"]}>
        <div className={style[props.itsclass]}>
          <div className={style["dialog-heading"]}>{props.heading}</div>
          {props.message}
          <button className={style["cancel-button"]} onClick={props.closedialog}>Close</button>
        </div>
      </div>
    </div>
  )
}

function DialogBoxTwoOption(props) {
  if (!props.show) {
    return (<></>)
  }

  return (
    <div className={style["dialog-background"]}>
      <div className={style["dialog-container"]}>
        <div className={props.itsclass}>
          <div className={style["dialog-heading"]}>{props.heading}</div>
          <div className={style["dialog-body"]}>{props.body}</div>
          <button className={style["delete-button"]} onClick={props.deletebuttonaction} > Yes</button >
          <button className={style["cancel-button"]} onClick={props.cancelbuttonaction} > Cancel</button >
        </div>
      </div>
    </div>
  )
}

function WaitingDialog(props) {
  if (!props.show) {
    return (
      <></>
    )
  }
  return (
    <div className={style["dialog-background"]}>
      <div className={style["dialog-container"]}>
        <div className={style[props.itsclass]}>
          <div className={style["dialog-heading"]}>{props.heading}</div>
          {props.message}
        </div >
      </div>
    </div>
  )
}

function GenericDialogBox(props) {
  
  if (!props.show) {
    return (
      <></>
    )
  }
  if (props.checkBox == "checkbox") {
    return (
        <div className={style["dialog-background"]}>
          <div className={style["dialog-container-expanded"]}>
            {props.displayDevices.map((device, index) => (
              <label className={style["dc-checkbox"]}>{device.name}
                  <input type="checkbox" checked={device.checked} value={device.checked} onChange={() => props.changeCheck(index)}  />
                  <span className={style.checkmark}></span>
              </label>))}
            {props.children} 
          </div>
        </div>
    )
  }
  return (
    <div className={style["dialog-background"]}>
      <div className={style["dialog-container"]} style={{'overflow-y': props.optionsCase ? 'visible' : 'auto'}}>
        {props.children}
      </div>
    </div>)
}
export { DialogBox, WaitingDialog, DialogBoxTwoOption,GenericDialogBox }
