
import './dialog-component.scss';

function DialogBox(props){
  if(!props.show){
    return(
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

function WaitingDialog(props){
  if(!props.show){
    return(
      <></>
    )
  }

  return(
    <div className={props.itsclass}>
        <div className="dialog-heading">{props.heading}</div>
        {props.message}
  </div >
  )
}

export {DialogBox,WaitingDialog}
