import {
  CanActivate,
  ActivatedRouteSnapshot,
  RouterStateSnapshot,
} from "@angular/router";
import { Router } from "@angular/router";
import { Injectable } from "@angular/core";
import { Observable } from "rxjs/Observable";
import { ApiService } from "./api.service";
import { UserModel } from "../models/user";

@Injectable()
export class AuthService {
  private _user: any;

  constructor(private api: ApiService) {}

  login(email: string, password: string): Observable<any> {
    const body = {
      email: email,
      password: password,
    };
    const retVal = this.api.post("api/v1/login", body);
    return retVal.map((response) => {
      this._user = UserModel.fromJson(response.json());
      return this._user;
    });
  }

  logout(): Observable<any> {
    return this.api.post("api/v1/logout", {}).map((response) => {
      return response.json();
    });
  }

  me(): Observable<any> {
    return this.api.get("api/v1/me").map((response) => {
      this._user = UserModel.fromJson(response.json());
      return this._user;
    });
  }

  changePassword(
    currentPassword: string,
    newPassword: string,
    confirmPassword: string
  ): Observable<any> {
    const body = {
      password: currentPassword,
      new: newPassword,
      confirm: confirmPassword,
    };
    return this.api.post("api/v1/password", body).map((response) => {
      return response.json();
    });
  }

  createUser(email: string, role: string): Observable<any> {
    const body = {
      email: email,
      role: role,
    };
    return this.api.post("api/v1/admin/users", body).map((response) => {
      const json = response.json();
      json["user"] = UserModel.fromJson(json["user"]);
      return json;
    });
  }

  deleteUser(userId): Observable<any> {
    return this.api.delete("api/v1/admin/users/" + userId).map((response) => {
      return response.json();
    });
  }

  getUsers(): Observable<any> {
    return this.api.get("api/v1/admin/users").map((response) => {
      return UserModel.fromJsonList(response.json());
    });
  }

  lockUser(userId): Observable<any> {
    return this.api
      .post("api/v1/admin/users/" + userId + "/lock", {})
      .map((response) => {
        return UserModel.fromJsonList(response.json());
      });
  }

  unlockUser(userId): Observable<any> {
    return this.api
      .post("api/v1/admin/users/" + userId + "/unlock", {})
      .map((response) => {
        return UserModel.fromJsonList(response.json());
      });
  }

  changeUserRole(userId, role: string): Observable<any> {
    const body = {
      role: role,
    };
    return this.api
      .post("api/v1/admin/users/" + userId + "/role", body)
      .map((response) => {
        return UserModel.fromJsonList(response.json());
      });
  }

  resetUserPassword(userId): Observable<any> {
    return this.api
      .post("api/v1/admin/users/" + userId + "/reset", {})
      .map((response) => {
        return response.json();
      });
  }

  // Type can be either 'dcs' or 'aps'.
  getServerLogs(type: string) {
    const query = {
      log_type: type,
    };

    return this.api.get("api/v1/admin/server/logs", query).map((response) => {
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

  getDeviceLogs(deviceId: number) {
    return this.api
      .get("api/v1/admin/devices/" + deviceId + "/logs")
      .map((response) => {
        const jsonData = response.json();
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

  deleteServerLogs(type: string) {
    const query = {
      log_type: type,
    };
    return this.api
      .delete("api/v1/admin/server/logs", query)
      .map((response) => {
        return response.json();
      });
  }

  deleteDeviceLogs(deviceId: number) {
    return this.api
      .delete("api/v1/admin/devices/" + deviceId + "/logs")
      .map((response) => {
        return response.json();
      });
  }

  allowAPIAccess(userId: number) {
    return this.api
      .post("api/v1/admin/users/" + userId + "/api", {})
      .map((response) => {
        return response.json();
      });
  }

  revokeAPIAccess(userId: number) {
    return this.api
      .delete("api/v1/admin/users/" + userId + "/api")
      .map((response) => {
        return response.json();
      });
  }

  get user(): any {
    return this._user;
  }
}

@Injectable()
export class LoginGuard implements CanActivate {
  constructor(private authService: AuthService, private router: Router) {}

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    return Observable.create((obs) => {
      this.authService.me().subscribe(
        (response) => {
          obs.next(true);
          obs.complete();
        },
        (error) => {
          obs.next(false);
          obs.complete();
        }
      );
    });
  }
}
