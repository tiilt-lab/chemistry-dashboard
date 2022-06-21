
import './dialog-component.scss';

function DialogBox(props) {
  if (!props.show) {
    return (
      <></>
    )
  }

  return (
    <div className="dialog-background">
      <div className="dialog-container">
        <div className={props.itsclass}>
          <div className="dialog-heading">{props.heading}</div>
          {props.message}
          <button className="cancel-button" onClick={props.closedialog}>Close</button>
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
    <div className="dialog-background">
      <div className="dialog-container">
      <div className="dialog-window" >
        <div className="dialog-heading">{props.heading}</div>
        <div className="dialog-body">{props.body}</div>
        <button className="delete-button" onClick={props.deletebuttonaction} > Yes</button >
        <button className="cancel-button" onClick={props.cancelbuttonaction} > Cancel</button >
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
    <div className={props.itsclass}>
      <div className="dialog-heading">{props.heading}</div>
      {props.message}
    </div >
  )
}

export { DialogBox, WaitingDialog, DialogBoxTwoOption }
