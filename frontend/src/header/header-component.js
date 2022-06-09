
//import {useNavigate} from 'react-router-dom'
import './header-component.scss';
import backicon from '../assets/img/icon-back.svg'

function CenterText(props){
    return( 
        <div className="center">{props.title}</div>
    )
   }

   
function Appheader(props){
    

    return(
    <div className="header-grid">
        <img  onClick={props.nav} alt="mee" className="left" src={backicon}/>
        <CenterText title={props.title}/>
    </div>
    )
  }

  export {Appheader}