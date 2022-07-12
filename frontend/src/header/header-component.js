
import style from './header.module.css'
import backicon from '../assets/img/icon-back.svg'
   
function Appheader(props){
  
    return(
    <div className={style["header-grid"]}>
       {props.leftText!== false
                ? <div onClick={props.nav} className={style.left}> {props.leftText}</div>
                : <img  onClick={props.nav} alt="back" className={style.left} src={backicon}/> }
        <div className={style.center}>{props.title}</div>
        <div onClick={props.rightTextClick} className={!props.rightEnabled? `${style.right} ${style.disabled}`: style.right}>{props.rightText}</div>
    </div>
    )
  }

  export {Appheader}