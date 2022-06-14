import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { Instruction } from '../utilities/utility-components';
import { Appheader } from '../header/header-component';
import { DialogBox } from '../dialog/dialog-component';
//import { useLogin } from '../myhooks/custom-hooks.js';
import { AuthService } from '../services/auth-service';
import './login-component.scss';

function LoginPage() {
  const navigate = useNavigate();
  const [isShow, setShow] = useState(false);
  const [message, setMessage] = useState('');
  //const [loginpara, setLoginPara] = useState(null);

  //const [error, value] = useLogin("api/v1/login", 'POST', loginpara, true);

  const dialogheader = 'Login Failed';

  const backClick = () => {
    return navigate(-1)
  }

  //console.log(value)
  //console.log(error)
  const checkLogin = () => {
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();
    if (username === '') {
      setMessage("Please Enter Your Username");
      setShow(true);
      document.getElementById("username").focus();
    } else if (password === '') {
      setMessage("Please Enter Your Password");
      setShow(true);
      document.getElementById("password").focus();
    } else {

      // setLoginPara({
      //   email: username,
      //   password: password,
      // });

      new AuthService().login(username,password).subscribe(
        (value)=>{ 
          console.log("i am here 1")
          console.log(value)
          return navigate('/home')},
        (error)=>{
          console.log("i am here 2")
          console.log(error.status)
          console.log(error.message)
          return navigate('/login')}
      )
    }

  }

  const closeDialogBox = () => {
    setShow(false);
  }
  return (
    <div className="container">

      <Appheader title="Sign In" nav={backClick} />
      <br></br>
      <Instruction instructions="Please enter your username and password." />

      <input className="text-input" placeholder="username / email" name="username" id='username' />
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