import { useNavigate } from 'react-router-dom';
import { useLocation } from 'react-router-dom';
import { updateTime } from '../utilities/helper-functions';
import { Instruction } from '../utilities/utility-components';
import { AuthService } from '../services/auth-service';

import recordicon from '../assets/img/icon-record.svg'
import speaker from '../assets/img/home_graphic_respeaker.svg'
import wordlist from '../assets/img/icon-wordlist.svg'
import pod from '../assets/img/icon-pod.svg'
import trending from '../assets/img/icon-trending-up.svg'
import settings from '../assets/img/settings.svg'
import question from '../assets/img/question.svg'
import logouticon from '../assets/img/logout.svg'

function Menus(props) {
  return (
    <div className="option-button small-section" onClick={props.onClick? props.onClick : () => props.route(props.path)}>
      <img alt={props.menuName} src={props.menuIcon} className="w-6 h-6" />
      <div>{props.menuName}</div>
    </div>
  )
}

function HomeScreen(props) {
  const timeOfDay = updateTime();
  const navigate = useNavigate();
  const location = useLocation()
  
  const navigateToHelp = () => {
    window.open(
      window.location.protocol +
      "//" +
      window.location.hostname +
      "/help/Default.htm"
    );
  }

  const logout = () => {
    const ret = new AuthService().logout();
    ret.then(
      (response) => { return navigate('/login'); },
      (apiError) => { return navigate('/login'); })
  }

  return (
    <div className="main-container items-center overflow-y-auto">
      <div className="flex flex-col wide-section text-center items-center">
        <div className="font-sans mt-8 text-4xl/relaxed font-bold text-[#6466E3]">Good {timeOfDay}!</div>
        <Instruction instructions="Welcome to the Building Literacy in N-person Collaborations (BLINC) Dashboard. You can start gathering
        analytic data by recording a new discussion." />
      </div>
      <img alt="speaker" className="flex w-36.5 h-36.5 mt-13 mb-12.5" src={speaker} />
      <Menus menuIcon={recordicon} menuName="Discussions" route={navigate} path='/sessions' />
      <Menus menuIcon={wordlist} menuName="Keyword" route={navigate} path='/keyword-lists' />
      <Menus menuIcon={pod} menuName="Pods" route={navigate} path='/pods' />
      <Menus menuIcon={trending} menuName="Topic Modeling" route={navigate} path='/topic-models' />
      <Menus menuIcon={settings} menuName="Settings" route={navigate} path='/Settings' />
      <Menus menuIcon={question} menuName="Help" onClick={navigateToHelp} />
      <Menus menuIcon={logouticon} menuName="Sign Out"  onClick={logout} />
    </div >
  )
}

export { HomeScreen }
