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

import './homescreen.component.css';

function Menus(props) {
  return (
    <div className="home-button" onClick={() => props.route(props.path)}>
      <img alt={props.menuName} src={props.menuIcon} className="icon" />
      <div className="button-text">{props.menuName}</div>
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
    <div className="home-container">
      <div className="intro-box">
      <div className="greeting">Good {timeOfDay}!</div>
        <Instruction instructions="Welcome to the Building Literacy in N-person Collaborations (BLINC) Dashboard. You can start gathering
      analytic data by recording a new discussion." />
      </div>
      <img alt="speaker" className="logo" src={speaker} />
      <Menus menuIcon={recordicon} menuName="Discussions" route={navigate} path='/sessions' />
      <Menus menuIcon={wordlist} menuName="Keyword" route={navigate} path='/keyword-lists' />
      <Menus menuIcon={pod} menuName="Pods" route={navigate} path='/pods' />
      <Menus menuIcon={trending} menuName="Topic Modeling" route={navigate} path='/file_upload' />
      <Menus menuIcon={settings} menuName="Settings" route={navigate} path='/Settings' />

      <div className="home-button" onClick={navigateToHelp}>
        <img alt="help" src={question} className="icon" />
        <div className="button-text">Help</div>
      </div>

      <div className="home-button" onClick={logout}>
        <img alt="sign out" src={logouticon} className="icon" />
        <div className="button-text">Sign Out</div>
      </div>
    </div >
  )
}

export { HomeScreen }