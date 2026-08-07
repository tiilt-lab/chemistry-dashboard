import { AuthService } from '../services/auth-service';
import { DeviceService } from '../services/device-service';
import { clearAuthCache } from '../routes/protected-route';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DeviceModel } from '../models/device'
import { SettingComponentPage } from './html-pages'
import { downloadBlob } from "../utilities/download"

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
          console.error("settingcomponent func : opendialog 2", apierror)
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
        console.error("settingcomponent func : changeemail", apierror)
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
        console.error("settingcomponent func : changepassword", apierror)
      }
    ).finally(
      () => { setCurrentForm("Status") }
    )
  }

  // One implementation for both log scopes; the four exported names below
  // keep the page props stable. (These were four near-identical copies, and
  // the delete pair crashed on a null response.)
  const fetchLogs = (scope, id) =>
    scope === "server"
      ? new AuthService().getServerLogs(id)
      : new AuthService().getDeviceLogs(+id)

  const removeLogs = (scope, id) =>
    scope === "server"
      ? new AuthService().deleteServerLogs(id)
      : new AuthService().deleteDeviceLogs(+id)

  const downloadLogs = async (scope, id) => {
    setCurrentForm("Loading");
    try {
      const response = await fetchLogs(scope, id)
      if (response !== null && response.status === 200) {
        const respJson = await response.json()
        if (respJson !== null) {
          const res = await fetch(respJson["data"])
          downloadBlob(await res.blob(),
            scope === "server" ? id + "_logs.txt" : "pod_" + id + "_logs.txt")
          setStatusTitle('Logs Downloaded');
          setStatus('The logs have been downloaded successfully.');
        } else {
          setStatusTitle('Logs Download Failed')
          setStatus('The logs failed to download.  Please try again later.');
        }
      } else {
        setStatusTitle('Logs Download Failed')
        setStatus(response !== null ? (await response.json())['message'] : 'The logs failed to download.');
      }
    } catch (e) {
      console.error(e, 'downloadLogs', scope)
      setStatusTitle('Logs Download Failed')
      setStatus('The logs failed to download.  Please try again later.');
    }
    setCurrentForm("Status")
  }

  const deleteLogs = async (scope, id) => {
    setCurrentForm('Loading');
    try {
      const response = await removeLogs(scope, id)
      setStatusTitle('Logs Deleted');
      if (response !== null && response.status === 200) {
        setStatus('The logs have been deleted successfully.');
      } else {
        setStatus(response !== null ? (await response.json())['message'] : 'The logs failed to delete.');
        console.error("settingcomponent func : deleteLogs", scope)
      }
    } catch (e) {
      console.error(e, 'deleteLogs', scope)
      setStatusTitle('Logs Delete Failed')
      setStatus('The logs failed to delete.  Please try again later.');
    }
    setCurrentForm("Status")
  }

  const downloadServerLogs = (type) => downloadLogs("server", type)
  const downloadDeviceLogs = (deviceId) => downloadLogs("device", deviceId)
  const deleteServerLogs = (type) => deleteLogs("server", type)
  const deleteDeviceLogs = (deviceId) => deleteLogs("device", deviceId)

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