export class SpeakerModel {
  // Speaker Fields
  id;
  alias;
  session_device_id;
  fingerprinted;

  static fromJson(json) {
    const model = new SpeakerModel();
    model.id = json["id"];
    model.alias = json["alias"];
    model.session_device_id = json["session_device_id"];
    model.fingerprinted = false;
    return model;
  }

  // Converts JSON to SpeakerListModel[]
  static fromJsonList(jsonArray) {
    const speakers = [];
    for (const el of jsonArray) {
      speakers.push(SpeakerModel.fromJson(el));
    }
    return speakers;
  }
}
