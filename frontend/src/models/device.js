export class DeviceModel {
  // Server Fields
  id;
  ip_address;
  name;
  connected;
  mac_address;
  archived;
  is_pod;

  static fromJson(json){
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
  static fromJsonList(jsonArray){
    const deviceList = [];
    for (const el of jsonArray) {
      deviceList.push(DeviceModel.fromJson(el));
    }
    return deviceList;
  }
}
