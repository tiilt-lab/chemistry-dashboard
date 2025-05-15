import style from './settings.module.css'
import { Appheader } from '../header/header-component'
import { GenericDialogBox } from '../dialog/dialog-component'
import React from 'react'
import { adjDim } from '../myhooks/custom-hooks';


function SettingComponentPage(props) {
  return (
    <>
      <div className={style.container}>
        <Appheader
          title={'Settings'}
          leftText={false}
          rightText={""}
          rightEnabled={false}
          nav={props.navigateToHomescreen}
        />

        <div className={style["section-header"]}>Account Settings</div>
        <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("ChangePassword")}>Change Password</div>
        {(props.user.isAdmin || props.user.isSuper) ?
          <React.Fragment>
            <div className={style["section-header"]}>Manage Accounts</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("ViewUsers", true)}>View Users</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("AddUser")}>Add User</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("DeleteUser", true)}>Delete User</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("UserRole", true)}>Change User Role</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("LockUser", true)}>Lock User</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("UnlockUser", true)}>Unlock User</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("ResetUser", true)}>Reset User Password</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("DisconnectSessionDevices", true)}>Disconnect Session Devices</div>
          </React.Fragment>
          :
          <></>
        }

        {(props.user.isSuper) ?
          <React.Fragment>
            <div className={style["section-header"]}>Manage Server</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("ServerLogs")}>Download Server Logs</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("DeviceLogs", false, true)}>Download Device Logs</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("DeleteServerLogs")}>Clear Server Logs</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("DeleteDeviceLogs", false, true)}>Clear Device Logs</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("AllowAPI", true)}>Allow API Access</div>
            <div className={style["option-button"]} style ={{width: adjDim(300) + 'px',}} onClick={() => props.openDialog("RevokeAPI", true)}>Revoke API Access</div>
          </React.Fragment>
          :
          <></>
        }

      </div>

      <GenericDialogBox show={props.currentForm !== ""}>
        {props.currentForm === "ChangePassword" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Change Password</div>
            <div className={style["input-header"]}>Current password</div>
            <input id='txtCurrent' className={style["field-input"]} type="password" />
            <div className={style["input-header"]}>New password</div>
            <input id='txtNew' className={style["field-input"]} type="password" />
            <div className={style["input-header"]}>Confirm new password</div>
            <input id='txtConfirm' className={style["field-input"]} type="password" />
            {props.status ? <div className={style["error-status"]}>{props.status}</div> : <></>}
            <button className={style["basic-button"]} onClick={() => props.changePassword(document.getElementById('txtCurrent').value, document.getElementById('txtNew').value, document.getElementById('txtConfirm').value)}>Change Password</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "ViewUsers" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>View Users</div>
            <div className={style["user-table"]}>
              <div className={style["user-row"]}>
                <span className={style["user-name bold"]}>Username / Email</span>
                <span className={style["user-role bold"]}>Role</span>
                <span className={style["user-locked bold"]}>Locked</span>
                <span className={style["user-api bold"]}>API</span>
              </div>
              {props.users.map((u, index) => (
                <div key={index} className={style["user-row"]}>
                  <span className={style["user-name"]}>{u.email}</span>
                  <span className={style["user-role"]}>{u.role}</span>
                  <span className={style["user-locked"]}>{JSON.stringify(u.locked)}</span>
                  <span className={style["user-api"]}>{JSON.stringify(u.api_access)}</span>
                </div>
              ))}
            </div>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Close</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "AddUser" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Add User</div>
            <div className={style["input-header"]}>Email</div>
            <input id='txtName' className={style["field-input"]} type="text" />
            <div className={style["input-header"]}>Role</div>
            <select id='ddRole' className={style["dropdown-input"]}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
            {props.status ? <div className={style["error-status"]}>{props.status}</div> : <></>}
            <button className={style["basic-button"]} onClick={() => props.createUser(document.getElementById('txtName').value, document.getElementById('ddRole').value)}>Create User</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }
        {props.currentForm === "DeleteUser" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Delete User</div>
            <div className={style["input-header"]}>Select user</div>
            <select id='ddUser' className={style["dropdown-input"]}>
              {props.users.map((u, index) => (
                <option key={index} value={u.id}>{u.email}</option>
              ))}
            </select>

            {props.status ? <div className={style["error-status"]}>{props.status}</div> : <></>}
            <button className={style["basic-button"]} onClick={() => props.confirmDeleteUser(document.getElementById('ddUser').value)}>Delete User</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }
        {props.currentForm === "ConfirmDeleteUser" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Are you sure you want to delete {props.userToDelete.email}?</div>
            <button className={style["basic-button"]} onClick={props.deleteSelectedUser}>Delete User</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "LockUser" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Lock User</div>
            <div className={style["input-header"]}>Select user</div>
            <select id='ddUser' className={style["dropdown-input"]}>
              {props.users.map((u, index) => (
                <option key={index} value={u.id}>{u.email}</option>
              ))}
            </select>
            {props.status ? <div className={style["error-status"]}>{props.status}</div> : <></>}
            <button className={style["basic-button"]} onClick={() => props.lockUser(document.getElementById('ddUser').value)}>Lock User</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "UnlockUser" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Unlock User</div>
            <div className={style["input-header"]}>Select user</div>
            <select id='ddUser' className={style["dropdown-input"]}>
              {props.users.map((u, index) => (
                <option key={index} value={u.id}>{u.email}</option>
              ))}
            </select>
            {props.status ? <div className={style["error-status"]}>{props.status}</div> : <></>}
            <button className={style["basic-button"]} onClick={() => props.unlockUser(document.getElementById('ddUser').value)}>Unlock User</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }
        {props.currentForm === "UserRole" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Change Role</div>
            <div className={style["input-header"]}>Select user</div>
            <select id='ddUser' className={style["dropdown-input"]}>
              {props.users.map((u, index) => (
                <option key={index} value={u.id}>{u.email}</option>
              ))}
            </select>
            <div className={style["input-header"]}>Select role</div>
            <select id='ddRole' className={style["dropdown-input"]}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
            <button className={style["basic-button"]} onClick={() => props.changeUserRole(document.getElementById('ddUser').value, document.getElementById('ddRole').value)}>Change Role</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "ResetUser" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Reset User Password</div>
            <div className={style["input-header"]}>User</div>
            <select id='ddUser' className={style["dropdown-input"]}>
              {props.users.map((u, index) => (
                <option key={index} value={u.id}>{u.email}</option>
              ))}
            </select>
            {props.status ? <div className={style["error-status"]}>{props.status}</div> : <></>}
            <button className={style["basic-button"]} onClick={() => props.resetUserPassword(document.getElementById('ddUser').value)}>Reset Password</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "DisconnectSessionDevices" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Disconnect Session Devices</div>
            {props.status ? <div className={style["error-status"]}>{props.status}</div> : <></>}
            <button className={style["basic-button"]} onClick={() => props.disconnectSessionDevices()}>Disconnect All</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "ServerLogs" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Download Server Logs</div>
            <div className={style["input-header"]}>Select service</div>
            <select id='ddService' className={style["dropdown-input"]}>
              <option value="dcs">Discussion Capture Server</option>
              <option value="aps">Audio Processing Service</option>
            </select>
            <button className={style["basic-button"]} onClick={() => props.downloadServerLogs(document.getElementById('ddService').value)}>Download logs</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "DeviceLogs" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Download Device Logs</div>
            <div className={style["input-header"]}>Select device</div>
            <select id='ddDevice' className={style["dropdown-input"]}>
              {props.devices.map((u, index) => (
                <option key={index} value={u.id}>{u.name}</option>
              ))}
            </select>
            <button className={style["basic-button"]} onClick={() => props.downloadDeviceLogs(document.getElementById('ddDevice').value)}>Download logs</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "DeleteServerLogs" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Clear Server Logs</div>
            <div className={style["input-header"]}>Select service</div>
            <select id='ddService' className={style["dropdown-input"]}>
              <option value="dcs">Discussion Capture Server</option>
              <option value="aps">Audio Processing Service</option>
            </select>
            <button className={style["basic-button"]} onClick={() => props.deleteServerLogs(document.getElementById('ddService').value)}>Clear logs</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "DeleteDeviceLogs" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Clear Device Logs</div>
            <div className={style["input-header"]}>Select device</div>
            <select id='ddDevice' className={style["dropdown-input"]}>
              {props.devices.map((u, index) => (
                <option key={index} value={u.id}>{u.name}</option>
              ))}
            </select>
            <button className={style["basic-button"]} onClick={() => props.deleteDeviceLogs(document.getElementById('ddDevice').value)}>Clear logs</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "AllowAPI" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Allow API Access</div>
            <div className={style["input-header"]}>Select user</div>
            <select id='ddUser' className={style["dropdown-input"]}>
              {props.users.map((u, index) => (
                <option key={index} value={u.id}>{u.email}</option>
              ))}
            </select>
            {props.status ? <div className={style["error-status"]}>{props.status}</div> : <></>}
            <button className={style["basic-button"]} onClick={() => props.allowAPIAccess(document.getElementById('ddUser').value)}>Allow</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "RevokeAPI" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Revoke API Access</div>
            <div className={style["input-header"]}>Select user</div>
            <select id='ddUser' className={style["dropdown-input"]}>
              {props.users.map((u, index) => (
                <option key={index} value={u.id}>{u.email}</option>
              ))}

            </select>
            {props.status ? <div className={style["error-status"]}>{props.status}</div> : <></>}
            <button className={style["basic-button"]} onClick={() => props.revokeAPIAccess(document.getElementById('ddUser').value)}>Revoke</button>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
          </div>
          :
          <></>
        }

        {props.currentForm === "Loading" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>Loading...please wait...</div>
          </div>
          :
          <></>
        }

        {props.currentForm === "Status" ?
          <div className={style["add-dialog"]}>
            <div className={style["dialog-heading"]}>{props.statusTitle}</div>
            <div>{props.status}</div>
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Close</button>
          </div>
          :
          <></>
        }
      </GenericDialogBox>
    </>
  )
}

export {SettingComponentPage}
