import { ApiService } from "./api-service";


export class DeviceService {
  api = new ApiService();

  getDevices(
    archived = false,
    connected= null,
    inUse = null,
    isPod = true
  ) {
    const query = {
      archived: archived,
      connected: connected,
      inUse: inUse,
      isPod: isPod,
    };
    return this.api.httpRequestCall("api/v1/devices",'GET', query);
  }

  addDevice(macAddress) {
    const body = {
      macAddress: macAddress,
    };
    return this.api.httpRequestCall("api/v1/devices",'POST', body);
  }

  removeDevice(deviceId){
    return this.api.httpRequestCall('api/v1/devices/${deviceId}','DELETE',{});
  }

  blinkPod(deviceId, op) {
    const body = {
      op: op,
      time: 15,
    };
    return this.api.httpRequestCall(`api/v1/devices/${deviceId}/blink`,'POST', body);
  }

  getDevice(deviceId){
    return this.api.httpRequestCall(`api/v1/devices/${deviceId}`,'GET',{});
  }

  setDevice(deviceId, data) {
    return this.api.httpRequestCall(`api/v1/devices/${deviceId}`,'PUT', data);
  }
}
