
import { ApiService } from "./api-service";
import { UserModel } from "../models/user";
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

  deleteUser(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId, 'DELETE', {});
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


