
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
  <div className="add-dialog">
      <div className="dialog-heading">{props.heading}</div>
      {props.message}
     <button className="cancel-button" onClick={props.closeDialog}>Close</button>
   </div>
  </div>
</div>
  )
}

export {DialogBox}
