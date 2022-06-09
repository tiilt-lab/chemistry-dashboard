import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { Instruction } from '../utility_components/utilities';
import { Appheader } from '../header/header-component';
import { DialogBox } from '../dialog/dialog-component';
import './login-component.scss';

function LoginPage() {
  const navigate = useNavigate();
  const [ isShow, setShow ] = useState(false);
  const [message, setMessage] = useState('');

  const dialogheader = 'Login Failed';

  const backClick = () => {
    return navigate(-1)
  }

  const checkLogin = ()=>{
    if(document.getElementById("username").value.trim() === ''){
        setMessage("Please Enter Your Username") ;
        setShow(true); 
        document.getElementById("username").focus();
    }else if(document.getElementById("password").value.trim() === ''){
      setMessage("Please Enter Your Password"); 
      setShow(true); 
      document.getElementById("password").focus();
  } 

  }

  const closeDialogBox = ()=>{
    setShow(false);
  }
  return (
    <div className="container">

      <Appheader title="Sign In" nav={backClick} />
      <br></br>
      <Instruction instructions="Please enter your username and password." />

      <input className="text-input" placeholder="username / email" name="username" id='username'/>
      <input className="text-input" placeholder="password" type="password" name="password" id='password' />

      <button className="basic-button medium-button" onClick={checkLogin}>
        Sign In
      </button>

      <DialogBox 
      heading={dialogheader} 
      message={message} 
      show={isShow} 
      closedialog={closeDialogBox} />
    </div >
  )
}

export { LoginPage }