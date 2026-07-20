import { AuthService } from '../services/auth-service';
import { DeviceService } from '../services/device-service';
import { clearAuthCache } from '../routes/protected-route';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DeviceModel } from '../models/device'
import { SettingComponentPage } from './html-pages'

function SettingsComponent(props) {

  const user = props.userdata // The currently logged in user.
  const [devices, setDevices] = useState();
  const [currentForm, setCurrentForm] = useState("");
  const [statusTitle, setStatusTitle] = useState('');
  const [status, setStatus] = useState('');
  const navigate = useNavigate()



  const navigateToHomescreen = () => {
    navigate('/home');
  }

  const signOut = () => {
    clearAuthCache()
    new AuthService().logout().then(
      () => navigate('/login'),
      () => navigate('/login'),
    )
  }

  // Student and rater management moved to /students and /raters — this page
  // is account settings + the super-only server/device log tools.
  const openDialog = (newForm, _loadUsers = false, loadDevices = false) => {
    if (loadDevices) {
      setCurrentForm("Loading");
      const fetchData = new DeviceService().getDevices(false, true, null, true)
      fetchData.then(
        response => {
          if (response.status === 200) {
            const respJson = response.json()
            respJson.then(
              deviceJson => {
                const deviceObj = DeviceModel.fromJsonList(deviceJson)
                setDevices(deviceObj);
                setCurrentForm(newForm);
              }
            )
          }
        },
        apierror => {
          console.log("settingcomponent func : opendialog 2", apierror)
        }
      )
    } else {
      setCurrentForm(newForm);
    }
  }

  const closeDialog = () => {
    setStatus("");
    setCurrentForm("");
  }

  const changeEmail = (password, newEmail) => {
    const fetchData = new AuthService().changeEmail(password, newEmail)
    fetchData.then(
      response => {
        if (response.status === 200) {
          setStatusTitle('Email Changed');
          setStatus('Your email has been changed successfully. Use it the next time you sign in.');
        } else if (response.status === 400) {
          response.json().then(error => setStatus(error['message']))
        }
      },
      apierror => {
        console.log("settingcomponent func : changeemail", apierror)
      }
    )
  }

  const changePassword = (password, newPassword, confirmPassword) => {
    const fetchData = new AuthService().changePassword(password, newPassword, confirmPassword)
    fetchData.then(
      response => {
        if (response.status === 200) {
          setStatusTitle('Password Changed');
          setStatus('Your password has been changed successfully.');
        } else if (response.status === 400) {
          const errResp = response.json()
          errResp.then(
            error => {
              setStatus(error['message']);
            }
          )

        }
      },
      apierror => {
        console.log("settingcomponent func : changepassword", apierror)
      }
    ).finally(
      () => { console.log('i came here'); setCurrentForm("Status") }
    )
  }

  const downloadServerLogs = async (type) => {
    setCurrentForm("Loading");
    try {
      const fetchData = await new AuthService().getServerLogs(type)
      if (fetchData !== null && fetchData.status === 200) {
        const respJson = await fetchData.json()
        if (respJson !== null) {
          const dataUrl = respJson["data"];
          const res = await fetch(dataUrl)
          const blob = await res.blob()
          const blobUrl = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = blobUrl;
          link.download = type + "_logs.txt";
          link.click();
          setStatusTitle('Logs Downloaded');
          setStatus('The logs have been downloaded successfully.');
          setCurrentForm("Status")
        } else {
          setStatusTitle('Logs Download Failed')
          setStatus('The logs failed to download.  Please try again later.');
          setCurrentForm("Status")
        }
      } else {
        setCurrentForm("Status")
        console.log("settingcomponent func : downloadServerLogs")
      }
    } catch (e) {
      setCurrentForm("Status")
      console.log(e, 'downloadserverlogs')
    }

  }

  const downloadDeviceLogs = async (deviceId) => {
    deviceId = +deviceId;
    setCurrentForm('Loading');
    try {
      const fetchData = await new AuthService().getDeviceLogs(deviceId)
      if (fetchData !== null && fetchData.status === 200) {
        const respJson = await fetchData.json()
        if (respJson !== null) {
          const dataUrl = respJson["data"];
          const res = await fetch(dataUrl)
          const blob = await res.blob()
          const blobUrl = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = blobUrl;
          link.download = "pod_" + deviceId + "_logs.txt";
          link.click();
          setStatusTitle('Logs Downloaded');
          setStatus('The logs have been downloaded successfully.');
          setCurrentForm("Status")
        } else {
          setStatusTitle('Logs Download Failed')
          setStatus('The logs failed to download.  Please try again later.');
          setCurrentForm("Status")
        }
      } else {
        const respJson = await fetchData.json()
        setStatus(respJson['message']);
        setStatusTitle('Logs Download Failed')
        setCurrentForm("Status")
        console.log("settingcomponent func : downloadDeviceLogs")
      }
    } catch (e) {
      setCurrentForm("Status")
      console.log(e, 'downloadserverlogs')
    }

  }

  const deleteServerLogs = async (type) => {
    setCurrentForm('Loading');
    const fetchData = await new AuthService().deleteServerLogs(type)
    if (fetchData != null && fetchData.status === 200) {
      setStatusTitle('Logs Deleted');
      setStatus('The logs have been deleted successfully.');
      setCurrentForm("Status")
    } else {
      const respJson = await fetchData.json()
      setStatus(respJson['message']);
      setStatusTitle('Logs Deleted');
      setCurrentForm("Status")
      console.log("settingcomponent func : deleteServerLogs")
    }
  }

  const deleteDeviceLogs = async (deviceId) => {
    deviceId = +deviceId;
    setCurrentForm('Loading');
    const fetchData = await new AuthService().deleteDeviceLogs(deviceId)
    if (fetchData != null && fetchData.status === 200) {
      setStatusTitle('Logs Deleted');
      setStatus('The logs have been deleted successfully.');
      setCurrentForm("Status")
    } else {
      const respJson = await fetchData.json()
      setStatus(respJson['message']);
      setStatusTitle('Logs Deleted');
      setCurrentForm("Status")
      console.log("settingcomponent func : delete devicelog")
    }

  }

  return (
    <SettingComponentPage
      navigateToHomescreen={navigateToHomescreen}
      signOut={signOut}
      openDialog={openDialog}
      user={user}
      currentForm={currentForm}
      status={status}
      statusTitle={statusTitle}
      changePassword={changePassword}
      changeEmail={changeEmail}
      devices={devices}
      deleteDeviceLogs={deleteDeviceLogs}
      deleteServerLogs={deleteServerLogs}
      downloadDeviceLogs={downloadDeviceLogs}
      downloadServerLogs={downloadServerLogs}
      closeDialog={closeDialog}
    />

  )
}

export { SettingsComponent }