import {useNavigate} from 'react-router-dom'
import './landing-page-css.scss';
import {Instruction} from '../utility_components/utilities'
import {updateTime} from './landing-page-logic'


const timeOfDay = updateTime();
  
function Greeting(){
  
  return <div className="greeting">Good {timeOfDay}!</div>
}


function IntroBox(){
 return( <div className="intro-box">
      <Greeting/>
      <Instruction instructions="Welcome to Discussion Capture. Please sign in to manage recordings or join a session."/>
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
  //onClick = {()=> navigate('/join')} 
  > 
  Join Discussion
  </button >
  </div >
  )
}
export default LandingPageComponent;
