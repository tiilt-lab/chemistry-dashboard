
import './header-component.scss';
import backicon from '../assets/img/icon-back.svg'
   
function Appheader(props){
    return(
    <div className="header-grid">
       {props.leftText!== false
                ? <div onClick={props.nav} className="left"> {props.leftText}</div>
                : <img  onClick={props.nav} alt="back" className="left" src={backicon}/> }
        <div className="center">{props.title}</div>
        <div onClick={props.rightTextClick} className="right" style={!props.rightEnabled ? {pointerEvents: "none", opacity:"0.4"} : {}}  >{props.rightText}</div>
    </div>
    )
  }

  export {Appheader}