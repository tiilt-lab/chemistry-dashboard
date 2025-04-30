export class SpeakerMetricsModel {
  // Server Fields
  id;
  speaker_id;
  transcript_id;
  participation_score;
  internal_cohesion;
  responsivity;
  social_impact;
  newness;
  communication_density;

  static fromJson(json) {
    const model = new SpeakerMetricsModel();
    model.id = json["id"];
    model.speaker_id = json["speaker_id"];
    model.transcript_id = json["transcript_id"];
    model.participation_score = json["participation_score"];
    model.internal_cohesion = json["internal_cohesion"];
    model.responsivity = json["responsivity"];
    model.social_impact = json["social_impact"];
    model.newness = json["newness"];
    model.communication_density = json["communication_density"];
    return model;
  }

  // Converts JSON to TranscriptModel[]
  static fromJsonList(jsonArray) {
    const metrics = [];
    for (const el of jsonArray) {
      metrics.push(SpeakerMetricsModel.fromJson(el));
    }
    return metrics;
  }
}
