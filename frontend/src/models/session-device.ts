// The JSON shape the server sends for a session device (pod). Typing this
// boundary catches the field-drift bug this model already suffered once —
// posthoc_analyzed_date / posthoc_models were silently dropped, breaking
// every provenance consumer.
export interface SessionDeviceJson {
  id: number
  session_id: number
  device_id: number | null
  name: string
  connected: boolean
  button_pressed?: boolean
  posthoc_analyzed_date?: string | null
  posthoc_models?: Record<string, string> | null
}

export class SessionDeviceModel {
  id!: number
  session_id!: number
  device_id!: number | null
  name!: string
  connected!: boolean
  button_pressed?: boolean
  posthoc_analyzed_date: string | null = null
  posthoc_models: Record<string, string> | null = null

  static fromJson(json: SessionDeviceJson): SessionDeviceModel {
    const model = new SessionDeviceModel()
    model.id = json["id"]
    model.session_id = json["session_id"]
    model.device_id = json["device_id"]
    model.name = json["name"]
    model.connected = json["connected"]
    model.button_pressed = json["button_pressed"]
    // Post-hoc provenance: which run analyzed this pod and with which models.
    model.posthoc_analyzed_date = json["posthoc_analyzed_date"] ?? null
    model.posthoc_models = json["posthoc_models"] ?? null
    return model
  }

  static fromJsonList(jsonArray: SessionDeviceJson[]): SessionDeviceModel[] {
    return jsonArray.map((el) => SessionDeviceModel.fromJson(el))
  }
}
