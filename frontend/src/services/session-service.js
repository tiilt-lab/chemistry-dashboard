import { ApiService } from "./api-service";
//import 'rxjs/add/operator/map';

class SessionService {
  deviceIds = [];
  keywordListId = "";
  api = new ApiService();

  endSession(sessionId) {
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/stop`,
      "POST",
      {}
    );
  }

  getSessions() {
    return this.api.httpRequestCall("api/v1/sessions", "GET", {});
  }

  getSession(sessionId) {
    return this.api.httpRequestCall(`api/v1/sessions/${sessionId}`, "GET", {});
  }

  deleteSession(sessionId) {
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}`,
      "DELETE",
      {}
    );
  }

  updateSession(sessionId, name) {
    const body = {
      name: name,
    };
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}`,
      "PUT",
      body
    );
  }

  updateSessionFolder(sessionId, folder) {
    const body = {
      folder: folder,
    };
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}`,
      "PUT",
      body
    );
  }

  getSessionDevice(sessionId, sessionDeviceId) {
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/devices/${sessionDeviceId}`,
      "GET",
      {}
    );
  }

  getSessionDevices(sessionId) {
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/devices`,
      "GET",
      {}
    );
  }

  getSessionDeviceTranscripts(sessionId, sessionDeviceId, startTime = 0) {
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/devices/${sessionDeviceId}/transcripts`,
      "GET",
      {}
    );
  }

  getSessionDeviceSpeakers(sessionId, sessionDeviceId) {
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/devices/${sessionDeviceId}/speakers`,
      "GET",
      {}
    );
  }

  getSessionSpeakers(sessionId) {
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/speakers`,
      "GET",
      {}
    );
  }

  getSessionDeviceTranscriptsForClient(sessionDeviceId, startTime = 0) {
    return this.api.httpRequestCall(
      `api/v1/devices/${sessionDeviceId}/transcripts/client`,
      "GET",
      {}
    );
  }

  getSessionDeviceVideoMetricsForClient(sessionDeviceId, startTime = 0) {
    return this.api.httpRequestCall(
      `api/v1/devices/${sessionDeviceId}/videometrics/client`,
      "GET",
      {}
    );
  }

  getSpeakerIdTranscripts(deviceId, speakerId) {
    return this.api.httpRequestCall(
      `api/v1/sessions/devices/${deviceId}>/speakers/${speakerId}/transcripts`,
      "GET",
      {}
    );
  }

  getSessionDeviceSpeakerMetrics(sessionDeviceId) {
    return this.api.httpRequestCall(
      `api/v1/devices/${sessionDeviceId}/transcripts/speaker_metrics`,
      "GET",
      {}
    );
  }

  getSessionSpeakerMetrics(sessionId){
    const body = {
      sessionId: sessionId,
    };
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/transcripts/speaker_metrics`,
      "POST",
      body
    );
  }

  getTranscriptSpeakerMetrics(transcriptId) {
    return this.api.httpRequestCall(
      `api/v1/transcripts/${transcriptId}/speaker_metrics`,
      "GET",
      {}
    );
  }

  getSpeakerIdTranscriptsForClient(deviceId, speakerId) {
    return this.api.httpRequestCall(
      `api/v1/sessions/devices/${deviceId}>/speakers/${speakerId}/transcripts/client`,
      "GET",
      {}
    );
  }

  setDeviceButton(sessionDeviceId, pressed, key) {
    const body = {
      id: sessionDeviceId,
      activated: pressed,
    };
    const headers = {
      "X-Processing-Key": key,
    };
    return this.api.httpRequestCallWithHeader(
      `api/v1/help_button`,
      "POST",
      body,
      headers
    );
  }

  createNewSession(
    name,
    devices,
    keywordListId,
    topicModelId,
    byod,
    features,
    doa,
    folder
  ) {
    const body = {
      name: name,
      devices: devices,
      keywordListId: keywordListId,
      topicModelId: topicModelId,
      byod: byod,
      features: features,
      doa: doa,
      folder: folder,
    };

    return this.api.httpRequestCall("api/v1/sessions", "POST", body);
  }

  joinByodSession(name, passcode, collaborators) {
    const body = {
      name: name,
      passcode: passcode,
      collaborators: collaborators,
    };
    return this.api.httpRequestCall("api/v1/sessions/byod", "POST", body);
  }

  updateCollaborator(speakerId, alias) {
    const body = {
      alias: alias,
    };
    return this.api.httpRequestCall(`api/speakers/${speakerId}`, "POST", body);
  }

  addPodToSession(sessionId, podId) {
    const body = {
      sessionId: sessionId,
      podId: podId,
    };
    return this.api.httpRequestCall("api/v1/sessions/pod", "POST", body);
  }

  setPasscodeStatus(sessionId, state) {
    const body = {
      state: state,
    };
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/passcode`,
      "POST",
      body
    );
  }

  removeDeviceFromSession(sessionId, sessionDeviceId, shouldDelete = false) {
    const query = {
      delete: shouldDelete,
    };
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/devices/${sessionDeviceId}`,
      "DELETE",
      query
    );
  }

  downloadSessionReport(sessionId, fileName) {
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/export`,
      "GET",
      {}
    );
  }

  getFolders() {
    return this.api.httpRequestCall(`api/folders`, "GET", {});
  }

  addFolder(name, parent) {
    const body = {
      name: name,
      parent: parent,
    };
    return this.api.httpRequestCall(`api/folder`, "POST", body);
  }

  updateFolder(folderId, parent, name) {
    const body = {
      parent: parent,
      name: name,
    };
    return this.api.httpRequestCall(`api/folders/${folderId}`, "POST", body);
  }

  deleteFolder(folderId) {
    return this.api.httpRequestCall(`api/folders/${folderId}`, "DELETE", {});
  }
}

export { SessionService };
