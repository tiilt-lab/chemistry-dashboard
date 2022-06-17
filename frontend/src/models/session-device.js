export class SessionDeviceModel {
  // Server Fields
  id;
  session_id;
  device_id;
  name;
  connected;
  button_pressed;

  static fromJson(json) {
    const model = new SessionDeviceModel();
    model.id = json['id'];
    model.session_id = json['session_id'];
    model.device_id = json['device_id'];
    model.name = json['name'];
    model.connected = json['connected'];
    model.button_pressed = json['button_pressed'];
    return model;
  }

  // Converts JSON to SessionDeviceModel[]
  static fromJsonList(jsonArray) {
    const sessionDevices = [];
    for (const el of jsonArray) {
      sessionDevices.push(SessionDeviceModel.fromJson(el));
    }
    return sessionDevices;
  }
}
