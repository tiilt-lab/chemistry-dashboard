export class DeviceModel {
  // Server Fields
  id: number;
  ip_address: string;
  name: string;
  connected: boolean;
  mac_address: string;
  archived: boolean;
  is_pod: boolean;

  static fromJson(json): DeviceModel {
    const model = new DeviceModel();
    model.id = json['id'];
    model.ip_address = json['ip_address'];
    model.name = json['name'];
    model.connected = json['connected'];
    model.mac_address = json['mac_address'];
    model.archived = json['archived'];
    model.is_pod = json['is_pod'];
    return model;
  }

  // Converts JSON to DeviceModel[]
  static fromJsonList(jsonArray: any): DeviceModel[] {
    const deviceList = [];
    for (const el of jsonArray) {
      deviceList.push(DeviceModel.fromJson(el));
    }
    return deviceList;
  }
}
