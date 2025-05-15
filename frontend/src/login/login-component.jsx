import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Instruction } from '../utilities/utility-components';
import { Appheader } from '../header/header-component';
import { DialogBox } from '../dialog/dialog-component';
import { AuthService } from '../services/auth-service';


function LoginPage() {
  const navigate = useNavigate();
  const [isShow, setShow] = useState(false);
  const [message, setMessage] = useState('');
  const [loginStatus, setLoginStatus] = useState(0)
  const [authObject, setAuthObject] = useState(null)

  useEffect(() => {
    if (loginStatus.status === 200 && authObject !== null) {
      return navigate('/home') //,{state: authObject}
    } else if (loginStatus.status === 400) {
      setMessage(loginStatus.message);
      setShow(true);
    } else if (loginStatus.status === 401) {
      return navigate('/login')
    } else if (loginStatus.status === 600) {
      setMessage("Inavlid Username or Password");
      setShow(true);
    }
  }, [loginStatus,authObject])

  
  const dialogheader = 'Login Failed';

  const backClick = () => {
    return navigate('/')
  }

  const closeDialogBox = () => {
    setShow(false);
  }

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
      new AuthService().login(username, password, setLoginStatus,setAuthObject);
    }

  }

  return (
    <div className="main-container items-center text-center">

      <Appheader
        title="Sign In"
        leftText={false}
        rightText={""}
        rightEnabled={false}
        nav={backClick} />
      <br></br>
      <Instruction instructions="Please enter your username and password." />

      <input className="text-box my-2 small-section" placeholder="username / email" name="username" id='username' />
      <input className="text-box small-section" placeholder="password" type="password" name="password" id='password' />

      <button className="wide-button"  onClick={checkLogin}>
        Sign In
      </button>

      <DialogBox
        itsclass={"add-dialog"}
        heading={dialogheader}
        message={message}
        show={isShow}
        closedialog={closeDialogBox} />
    </div >
  )
}

export { LoginPage }
