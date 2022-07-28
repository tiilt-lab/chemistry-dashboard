import {useNavigate} from 'react-router-dom'
import './landing-page-css.css';
import {Instruction} from '../utilities/utility-components'
import { updateTime } from '../utilities/helper-functions';


const timeOfDay = updateTime();
  
function Greeting(){
  return <div className="greeting">Good {timeOfDay}!</div>
}


function IntroBox(){
 return( <div className="intro-box">
      <Greeting/>
      <Instruction instructions="Welcome to the BLINC platform. Please sign in to manage recordings or join a session."/>
  </div>
 )
}

function LandingPageComponent() {

const navigate = useNavigate();


  return (
  <div className="container">
  <IntroBox/>
  <button className="basic-button medium-button"
   onClick={()=> navigate('/login')}
  >
  Sign In
  </button>

  <button 
  className="basic-button medium-button" 
    onClick = {()=> navigate('/join')} 
  > 
  Join Discussion
  </button >
  </div >
  )
}
export default LandingPageComponent;
