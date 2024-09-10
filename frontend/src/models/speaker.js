export class SpeakerModel{
  // Speaker Fields
  id;
  alias;
  session_device_id;

  static fromJson(json){
    const model = new SpeakerModel();
    model.id = json['id'];
    model.alias = json['alias'];
    model.name = json['session_device_id'];
    return model;
  }

  // Converts JSON to KeywordListModel[]
  static fromJsonList(jsonArray){
    const speakers = [];
    for (const el of jsonArray) {
      speakers.push(SpeakerModel.fromJson(el));
    }
    return speakers;
  }
}
