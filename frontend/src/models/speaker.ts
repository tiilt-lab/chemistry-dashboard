export interface SpeakerJson {
  id: number
  alias: string
  session_device_id: number
}

export class SpeakerModel {
  id!: number
  alias!: string
  session_device_id!: number
  fingerprinted = false

  static fromJson(json: SpeakerJson): SpeakerModel {
    const model = new SpeakerModel()
    model.id = json["id"]
    model.alias = json["alias"]
    model.session_device_id = json["session_device_id"]
    model.fingerprinted = false
    return model
  }

  static fromJsonList(jsonArray: SpeakerJson[]): SpeakerModel[] {
    return jsonArray.map((el) => SpeakerModel.fromJson(el))
  }
}
