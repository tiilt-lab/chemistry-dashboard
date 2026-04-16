
import { ApiService } from "./api-service";
import { UserModel } from "../models/user";
import { StudentModel } from "../models/student";
class AuthService {

  login(email, password, setLoginStatus, setAuthObject) {
    const body = {
      email: email,
      password: password,
    };
    const fetchRes = new ApiService().httpRequestCall("api/v1/login", 'POST', body);
    fetchRes.then(
      (response) => {
        setLoginStatus(response);
        if (response.status === 200) {
          response.json().then(
            userobj => {
              const user = UserModel.fromJson(userobj);
              setAuthObject(user)
            }
          )
        }
      },
      (apiError) => {
        apiError.status = 600
        setLoginStatus(apiError);
      })
  }

  logout() {
    return new ApiService().httpRequestCall("api/v1/logout", 'POST', {});
  }

  createStudentProfile(lastname, firstname, username,setStudentObject,setAlertMessage,setShowAlert) {
    const body = {
      lastname: lastname,
      firstname: firstname,
      username: username
    };
    const fetchRes =  new ApiService().httpRequestCall("api/v1/student/addstudent", 'POST', body);
    fetchRes.then(
      (response) => {
        if (response.status === 200) {
          response.json().then(
            userobj => {
              const student = StudentModel.fromJson(userobj);
              setStudentObject(student)
            }
          )
        }else if (response.status === 400) {
           response.json().then(
            err => {
              if (err["message"] === "Username already exists."){
                const student = StudentModel.fromJson(err["data"] );
                if (student.biometric_captured === "yes"){
                  setAlertMessage("The Username has been selected by another student, please enter a different one")
                  setShowAlert(true)
                }else{
                  setStudentObject(student)
                }
              }
            }
          )
          
          }
      },
      (apiError) => {
        apiError.status = 600
        setAlertMessage("A fatal error occured!!!");
        setShowAlert(true);
      })
  }

    updateStudentProfile(id,lastname, firstname,biometric_captured,setStudentUpdated,setAlertMessage,setShowAlert) {
    const body = {
      id:id,
      lastname: lastname,
      firstname: firstname,
      biometric_captured: biometric_captured
    };
    const fetchRes =  new ApiService().httpRequestCall("api/v1/student/updatestudent", 'POST', body);
    fetchRes.then(
      (response) => {
        if (response.status === 200) {
          response.json().then(
            userobj => {
              const student = StudentModel.fromJson(userobj);
              setStudentUpdated(true)
            }
          )
        }else if (response.status === 400) {
           response.json().then(
            err => {
              if (err["message"] === "Update unsuccessful"){
                setAlertMessage("The profile update is unsuccessful, please contact administrator")
                setShowAlert(true)
              }else if(err["message"]==="Student  Id must be provided"){
                setAlertMessage("Student  Id must be provided, please contact administrator")
                setShowAlert(true)
              }
            }
          )
          
          }
      },
      (apiError) => {
        apiError.status = 600
        setAlertMessage("A fatal error occured!!!");
        setShowAlert(true);
      })
  }

  syncStudentProfile() {
    const body = {};
    return new ApiService().httpRequestCall("api/v1/callback/syncstudenttable", 'POST', body);
  }
 
  getStudentProfileByID(username) {
    return new ApiService().httpRequestCall("api/v1/student/getstudentbyid/"+ username, 'GET', {});
  }

  getStudentProfiles() {
    return new ApiService().httpRequestCall("api/v1/admin/students", 'GET', {});
  }

  getRaters() {
    return new ApiService().httpRequestCall("api/v1/admin/raters", 'GET', {});
  }

  me(stateSetter) {
    const fetchRes = new ApiService().httpRequestCall("api/v1/me", 'GET', {});
    fetchRes.then(
      (response) => {
        if (response.status === 200) {
          response.json().then(
            userobj => {
              const user = UserModel.fromJson(userobj);
              stateSetter(user);
            }
          )
        }else{
          stateSetter("cors error");
        }
      },
      (apiError) => {
        apiError.status = 600
        stateSetter("cors error");
      })
  }

  changePassword(currentPassword, newPassword, confirmPassword) {
    const body = {
      password: currentPassword,
      new: newPassword,
      confirm: confirmPassword,
    };
    return new ApiService().httpRequestCall("api/v1/password", 'POST', body);
  }

  async createUser(email, role) {
    const body = {
      email: email,
      role: role,
    };
    return new ApiService().httpRequestCall("api/v1/admin/users", 'POST', body);
  }

  async createRater(sessionid,sessiondeviceid,speakerid,speakertag,raterid,type,evaluationcategory) {
    const body = {
      sessionid: sessionid,
      sessiondeviceid: sessiondeviceid,
      speakerid: speakerid,
      speakertag: speakertag,
      raterid: raterid,
      type: type,
      evaluationcategory: evaluationcategory
    };
    return new ApiService().httpRequestCall("api/v1/admin/raters", 'POST', body);
  }
  

  deleteUser(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId, 'DELETE', {});
  }

  deleteStudent(studentId) {
    return new ApiService().httpRequestCall("api/v1/admin/students/" + studentId, 'DELETE', {});
  }

  deleteRater(id) {
    return new ApiService().httpRequestCall("api/v1/admin/raters/" + id, 'DELETE', {});
  }

  deleteSessionDeviceData(session_device_id, data_type) {
    return new ApiService().httpRequestCall("api/v1/admin/devicedata/sessiondeviceid/" + session_device_id+ "/data_type/"+data_type, 'DELETE', {});
  }


  getUsers() {
    return new ApiService().httpRequestCall("api/v1/admin/users", 'GET', {});
  }

  lockUser(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/lock", 'POST', {});
  }

  unlockUser(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/unlock", 'POST', {});
  }

  changeUserRole(userId, role) {
    const body = {
      role: role,
    };
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/role", 'POST', body);
  }

  resetUserPassword(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/reset", 'POST', {});
  }

  // Type can be either 'dcs' or 'aps'.
  getServerLogs(type) {
    const query = {
      log_type: type,
    };
    return new ApiService().httpRequestCall("api/v1/admin/server/logs", 'GET', query);
    
  }

  getDeviceLogs(deviceId) {
    return new ApiService().httpRequestCall("api/v1/admin/devices/" + deviceId + "/logs", 'GET', {});
  }

  deleteServerLogs(type) {
    const query = {
      log_type: type,
    };
    return new ApiService().httpRequestCall("api/v1/admin/server/logs", 'DELETE', query);
  }

  deleteDeviceLogs(deviceId) {
    return new ApiService().httpRequestCall("api/v1/admin/devices/" + deviceId + "/logs", 'DELETE', {});
  }

  allowAPIAccess(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/api", 'POST', {});
  }

  revokeAPIAccess(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/api", 'DELETE', {});
  }

  getuser(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId, 'GET', {});
  }

  disconnectSessionDevices() {
    return new ApiService().httpRequestCall("/api/v1/admin/devices/reset", 'PATCH', {});
  }

}

export { AuthService }


