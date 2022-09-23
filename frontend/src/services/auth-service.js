
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
    const val = new ApiService().httpRequestCall("api/v1/admin/users", 'POST', body);
    return val
  }

  deleteUser(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users" + userId, 'DELETE', {}, false);
  }

  getUsers() {
    return new ApiService().httpRequestCall("api/v1/admin/users", 'GET', {}, true);
  }

  lockUser(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/lock", 'POST', {}, true);
  }

  unlockUser(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/unlock", 'POST', {}, true);
  }

  changeUserRole(userId, role) {
    const body = {
      role: role,
    };
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/role", 'POST', body, true);
  }

  resetUserPassword(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/reset", 'POST', {}, false);
  }

  // Type can be either 'dcs' or 'aps'.
  getServerLogs(type) {
    const query = {
      log_type: type,
    };
    const observable = new ApiService().httpRequestCall("api/v1/admin/server/logs", 'GET', query);
    return observable.map((response) => {
      const jsonData = response.json();
      const dataUrl = jsonData["data"];
      fetch(dataUrl)
        .then((res) => res.blob())
        .then((blob) => {
          const blobUrl = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = blobUrl;
          link.download = type + "_logs.txt";
          link.click();
        });
      return true;
    });
  }

  getDeviceLogs(deviceId) {
    const observable = new ApiService().httpRequestCall("api/v1/admin/devices/" + deviceId + "/logs", 'GET', {});
    return observable.map((response) => {
      const jsonData = response;
      const dataUrl = jsonData["data"];
      fetch(dataUrl)
        .then((res) => res.blob())
        .then((blob) => {
          const blobUrl = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = blobUrl;
          link.download = "pod_" + deviceId + "_logs.txt";
          link.click();
        });
      return true;
    });
  }

  deleteServerLogs(type) {
    const query = {
      log_type: type,
    };
    return new ApiService().httpRequestCall("api/v1/admin/users/logs", 'DELETE', query, false);
  }

  deleteDeviceLogs(deviceId) {
    return new ApiService().httpRequestCall("api/v1/admin/devices/" + deviceId + "/logs", 'DELETE', {}, false);
  }

  allowAPIAccess(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/api", 'POST', {}, true);
  }

  revokeAPIAccess(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId + "/api", 'DELETE', {}, false);
  }

  getuser(userId) {
    return new ApiService().httpRequestCall("api/v1/admin/users/" + userId, 'GET', {}, true);
  }

}

export { AuthService }


