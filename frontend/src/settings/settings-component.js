import { AuthService } from '../services/auth-service';
import { DeviceService } from '../services/device-service';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserModel } from '../models/user';
import {DeviceModel} from '../models/device'
import {SettingComponentPage} from './html-pages'

function SettingsComponent(props){

  const user = props.userdata // The currently logged in user.
  const [users, setUsers]  = useState()
  const [userToDelete, setUserToDelete] = useState();
  const [devices, setDevices] = useState();
  const [currentForm, setCurrentForm] = useState("");
  const [statusTitle, setStatusTitle] = useState('');
  const [status, setStatus] = useState('');
  const navigate = useNavigate()

  

  const navigateToHomescreen = ()=> {
    navigate('/home');
  }

  const openDialog = (newForm, loadUsers= false, loadDevices= false)=> {
    if (loadUsers) {
      setCurrentForm("Loading");
      const fetchData = new AuthService().getUsers()
      fetchData.then(
       response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            userJson =>{
              const userObj = UserModel.fromJsonList(userJson)
              setUsers(userObj.filter(u => u.id !== user.id));
              setCurrentForm(newForm);
            }
          )
        }
       } ,
       apierror=>{
        console.log("settingcomponent func : opendialog ",apierror)
       }
      )
    } else if (loadDevices) {
      setCurrentForm("Loading");
      const fetchData = new DeviceService().getDevices(false, true, null, true)
      fetchData.then(
        response=>{
          if(response.status === 200){
            const respJson = response.json()
            respJson.then(
              deviceJson=>{
                const deviceObj = DeviceModel.fromJsonList(deviceJson)
                setDevices(deviceObj);
                setCurrentForm(newForm);
              }
            )
          }
        },
        apierror=>{
          console.log("settingcomponent func : opendialog 2",apierror)
        }
      )
    } else {
      setCurrentForm(newForm);
    }
  }

  const closeDialog = () =>{
    setStatus("");
    setCurrentForm("");
  }

  const changePassword = (password, newPassword, confirmPassword)=> {
    const fetchData = new AuthService().changePassword(password, newPassword, confirmPassword)
    fetchData.then(
      response=>{
        if(response.status === 200){
            setStatusTitle('Password Changed');
            setStatus('Your password has been changed successfully.');
        }else if(response.status === 400){
          const errResp = response.json()
          errResp.then(
            error=>{
              setStatus(error['message']);
            }
          )
        
        }
      },
      apierror=>{
        console.log("settingcomponent func : changepassword",apierror)
      }
    ).finally(
      ()=>{ console.log('i came here'); setCurrentForm("Status")}
    )
  }

  const createUser = (email, role) =>{
    const fetchData = new AuthService().createUser(email, role)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              setStatusTitle('User Created');
              setStatus('User has been given the password...\n' + result['password']);
            }, error => {
              setStatusTitle('Failed to Create User')
              setStatus(error.json()['message']);
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : createuser",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    )
  }

  const confirmDeleteUser = (userId) => {
    userId = +userId;
    setUserToDelete(users.find(u => u.id === userId));
    setCurrentForm("ConfirmDeleteUser");
  }

  const deleteSelectedUser = () => {
    const fetchData = new AuthService().deleteUser(userToDelete.id)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              setStatusTitle('User Deleted');
              setStatus(userToDelete.email + ' has been deleted.');
            }, error => {
              setStatusTitle('Failed to Delete User')
              setStatus(userToDelete.email + ' could not be deleted.');
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : confirmDeleteUser",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    )
  }

  const lockUser = (userId)=> {
    userId = +userId;
    const fetchData = new AuthService().lockUser(userId)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('User Locked');
              setStatus(user.email + ' has been locked out.');
            }, error => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('Failed to Lock User')
              setStatus(user.email + ' could not be locked out.');
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : lockUser",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    )
  }

  const unlockUser  = (userId)=> {
    userId = +userId;
    const fetchData = new AuthService().unlockUser(userId)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('User Unlocked');
              setStatus(user.email + '  has been unlocked and can now login.');
            }, error => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('Failed to Unlock User')
              setStatus(user.email + ' could not be unlocked.');
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : unlockUser",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    )
  }

  const changeUserRole = (userId, role)=> {
    userId = +userId;
    const fetchData = new AuthService.changeUserRole(userId, role)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('User Role Updated');
              setStatus(user.email + '\'s role is now "' + role + '".');
            }, error => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('Failed to Update Role')
              setStatus(user.email + '\'s role could not be updated.');
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : changeUserRole",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    ) 
  }

  const resetUserPassword = (userId)=> {
    userId = +userId;
    const fetchData = new AuthService.resetUserPassword(userId)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('User\'s Password Reset');
              setStatus(user.email + '\s new password is...\n' + result['password']);
            }, error => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('Failed to Reset User\'s Password')
              setStatus(user.email + '\'s password could not be reset.');
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : resetuserpassword",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    ) 
  }

  const downloadServerLogs = (type)=> {
    setCurrentForm("Loading");
    const fetchData = new AuthService().getServerLogs(type)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              setStatusTitle('Logs Downloaded');
              setStatus('The logs have been downloaded successfully.');
            }, error => {
              setStatusTitle('Logs Download Failed')
              setStatus('The logs failed to download.  Please try again later.');
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : resetuserpassword",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    ) 
  }

  const downloadDeviceLogs = (deviceId)=> {
    deviceId = +deviceId;
    setCurrentForm('Loading');
    const fetchData =new AuthService().getDeviceLogs(deviceId)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => { 
              setStatusTitle('Logs Downloaded');
              setStatus('The logs have been downloaded successfully.');
            }, error => {
              setStatusTitle('Logs Download Failed')
              setStatus('The logs failed to download.  Please try again later.');
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : resetuserpassword",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    ) 
  }

  const deleteServerLogs = (type)=> {
    setCurrentForm('Loading');
    const fetchData = new AuthService().deleteServerLogs(type)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              setStatusTitle('Logs Deleted');
              setStatus('The logs have been deleted successfully.');
            }, error => {
              setStatusTitle('Logs Failed to Delete')
              setStatus('The logs failed to delete.  Please try again later.');
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : resetuserpassword",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    ) 
  }

  const deleteDeviceLogs = (deviceId) =>{
    deviceId = +deviceId;
    setCurrentForm('Loading');
    const fetchData = new AuthService.deleteDeviceLogs(deviceId)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              setStatusTitle('Logs Deleted');
              setStatus('The logs have been deleted successfully.');
            }, error => {
              setStatusTitle('Logs Failed to Delete')
              setStatus('The logs failed to delete.  Please try again later.');
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : delete devicelog",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    ) 
  }

  const allowAPIAccess = (userId)=> {
    userId = +userId;
    setCurrentForm("Loading");
   const fetchData  = new AuthService().allowAPIAccess(userId)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('User Updated');
              setStatus(user.email + ' can now access the API publicly...\n\nClient ID: \n'
              + result['api_client']['client_id'] + '\n\nClient Secret: \n' + result['client_secret']);
            }, error => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('Failed to Update User')
              setStatus('Failed to grant API access to user.');
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : resetuserpassword",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    ) 
  }

  const revokeAPIAccess = (userId)=> {
    userId = +userId;
    setCurrentForm("Loading");
   const fetchData  = new AuthService().revokeAPIAccess(userId)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('User Updated');
              setStatus(user.email + ' can no longer access the API publicly.');
            }, error => {
              const user = users.find(u => u.id === userId);
              setStatusTitle('Failed to Update User')
              setStatus('Failed to revoke API access.');
            }
          )
        }
      },
      apierror=>{
        console.log("settingcomponent func : revokeApiAccess",apierror)
      }
    ).finally(
      ()=> setCurrentForm("Status")
    ) 
  }

  return(
      <SettingComponentPage
        navigateToHomescreen = {navigateToHomescreen}
        openDialog = {openDialog}
        user = {user}
        currentForm = {currentForm}
        status = {status}
        statusTitle = {statusTitle}
        changePassword = {changePassword}
        users = {users}
        confirmDeleteUser = {confirmDeleteUser}
        userToDelete = {userToDelete}
        deleteSelectedUser = {deleteSelectedUser}
        revokeAPIAccess = {revokeAPIAccess}
        allowAPIAccess = {allowAPIAccess}
        deleteDeviceLogs = {deleteDeviceLogs}
        deleteServerLogs = {deleteServerLogs}
        downloadDeviceLogs = {downloadDeviceLogs}
        downloadServerLogs = {downloadServerLogs}
        changeUserRole = {changeUserRole}
        unlockUser = {unlockUser}
        lockUser = {lockUser}
        createUser = {createUser}
        closeDialog = {closeDialog}
      />

  )
}

export {SettingsComponent}