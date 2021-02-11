import { Injectable } from "@angular/core";
import { ApiService } from "./api.service";
import { Observable } from "rxjs/Observable";
import { DeviceModel } from "../models/device";
import "rxjs/add/operator/map";

@Injectable()
export class DeviceService {
  constructor(private api: ApiService) {}

  getDevices(
    archived: boolean = false,
    connected: boolean = null,
    inUse: boolean = null,
    isPod: boolean = true
  ): Observable<any> {
    const query = {
      archived: archived,
      connected: connected,
      inUse: inUse,
      isPod: isPod,
    };
    return this.api.get("api/v1/devices", query).map((response) => {
      return DeviceModel.fromJsonList(response.json());
    });
  }

  addDevice(macAddress: string) {
    const body = {
      macAddress: macAddress,
    };
    return this.api.post("api/v1/devices", body).map((response) => {
      return DeviceModel.fromJson(response.json());
    });
  }

  removeDevice(deviceId: number): Observable<any> {
    return this.api.delete(`api/v1/devices/${deviceId}`).map((response) => {
      return response.json();
    });
  }

  blinkPod(deviceId, op): Observable<any> {
    const body = {
      op: op,
      time: 15,
    };
    return this.api
      .post(`api/v1/devices/${deviceId}/blink`, body)
      .map((response) => {
        return response.json();
      });
  }

  getDevice(deviceId): Observable<any> {
    return this.api.get(`api/v1/devices/${deviceId}`).map((response) => {
      return DeviceModel.fromJson(response.json());
    });
  }

  setDevice(deviceId, data): Observable<any> {
    return this.api.put(`api/v1/devices/${deviceId}`, data).map((response) => {
      return DeviceModel.fromJson(response.json());
    });
  }
}
