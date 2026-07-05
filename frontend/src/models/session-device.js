export class SessionDeviceModel {
  // Server Fields
  id;
  session_id;
  device_id;
  name;
  connected;
  button_pressed;
  posthoc_analyzed_date;
  posthoc_models;

  static fromJson(json) {
    const model = new SessionDeviceModel();
    model.id = json['id'];
    model.session_id = json['session_id'];
    model.device_id = json['device_id'];
    model.name = json['name'];
    model.connected = json['connected'];
    model.button_pressed = json['button_pressed'];
    // Post-hoc provenance: which run analyzed this pod and with which models.
    // This model previously dropped these, which silently broke every consumer
    // of per-run provenance (e.g. the "Transcribed with ..." label).
    model.posthoc_analyzed_date = json['posthoc_analyzed_date'] ?? null;
    model.posthoc_models = json['posthoc_models'] ?? null;
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
