export class SpeakerVideoMetricsModel {
  // Server Fields
  id;
  session_device_id;
  student_username;
  time_stamp;
  facial_emotion;
  attention_level;
  object_on_focus;

  static fromJson(json) {
    const model = new SpeakerVideoMetricsModel();
    model.id = json["id"];
    model.session_device_id = json["session_device_id"];
    model.student_username = json["student_username"];
    model.time_stamp = json["time_stamp"];
    model.facial_emotion = json["facial_emotion"];
    model.attention_level = json["attention_level"];
    model.object_on_focus = json["object_on_focus"];
    return model;
  }

  // Converts JSON to TranscriptModel[]
  static fromJsonList(jsonArray) {
    const metrics = [];
    for (const el of jsonArray) {
      metrics.push(SpeakerVideoMetricsModel.fromJson(el));
    }
    return metrics;
  }
}
