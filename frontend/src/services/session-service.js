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

  getSessionByPasscode(passcode) {
    return this.api.httpRequestCall(`api/v1/sessions/student/passcode/${passcode}`, "GET", {});
  }

  getSessionById(sessionId) {
    return this.api.httpRequestCall(`api/v1/sessions/student/sessionid/${sessionId}`, "GET", {});
  }

 
  getSessionsByAlias(alias) {
    return this.api.httpRequestCall(`api/v1/sessions/student/alias/${alias}`, "GET", {});
  }

 getSessionsDeviceByAlias(sessionid, alias) {
    return this.api.httpRequestCall(`api/v1/sessions/sessionid/${sessionid}/student/alias/${alias}`, "GET", {});
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

  getSessionDeviceForClient(session_device_id){
    return this.api.httpRequestCall(
      `/api/v1/devices/${session_device_id}/session_device`,
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

  getSessionDeviceTranscriptSpeakerMetricsForClient(sessionDeviceId, startTime = 0) {
    return this.api.httpRequestCall(
      `api/v1/devices/${sessionDeviceId}/transcriptspeakermetrics/client`,
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

  getSessionTranscriptsForClient(sessionId, alias,startTime = 0) {
    return this.api.httpRequestCall(
      `api/v1/session/${sessionId}/transcripts/student/${alias}`,
      "GET",
      {}
    );
  }

  getSessionVideoMetricsForClient(sessionId, alias,startTime = 0) {
    return this.api.httpRequestCall(
      `api/v1/session/${sessionId}/videometrics/student/${alias}`,
      "GET",
      {}
    );
  }

  getSessionDeviceTranscriptsByAlias(sessionId, deviceId, alias,startTime = 0) {
    return this.api.httpRequestCall(
      `api/v1/session/${sessionId}/sessiondevice/${deviceId}/transcripts/student/${alias}`,
      "GET",
      {}
    );
  }

  getSessionDeviceVideoMetricsByAlias(sessionId,deviceId, alias,startTime = 0) {
    return this.api.httpRequestCall(
      `api/v1/session/${sessionId}/sessiondevice/${deviceId}/videometrics/student/${alias}`,
      "GET",
      {}
    );
  }

  getRaterDetailByExpertId(expertId) {
    return this.api.httpRequestCall("api/v1/student/raters/" + expertId, 'GET', {});
  }

  postRating(payload){
    const body =  payload;
    return this.api.httpRequestCall(
      `api/v1/student/postrating`,
      "POST",
      body
    );
  }

  postSurveyResponse(payload){
    const body =  payload;
    return this.api.httpRequestCall(
      `api/v1/student/postsurveyresponse`,
      "POST",
      body
    );
  }

  postUserInteraction(payload){
    const body =  payload;
    return this.api.httpRequestCall(
      `api/v1/student/postuserinteraction`,
      "POST",
      body
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

  getSessionSpeakerMetrics(sessionId) {
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

  downloadSessionTranscriptMetrics(sessionId, fileName,windowsize,format) {
    if(windowsize === ""){
      windowsize = 0;
    }else{
      windowsize = parseInt(windowsize);
    }

    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/exporttranscriptmetrics/${windowsize}/${format}`,
      "GET",
      {}
    );
  }

  downloadSessionVideoMetrics(sessionId, fileName,windowsize,format) {
    if(windowsize === ""){
      windowsize = 0;
    }else{
      windowsize = parseInt(windowsize);
    }
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/exportvideometrics/${windowsize}/${format}`,
      "GET",
      {}
    );
  }

  downloadSessionTranscriptVideoMetrics(sessionId, fileName,windowsize,format) {
    if(windowsize === ""){
      windowsize = 0;
    }else{
      windowsize = parseInt(windowsize);
    }
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/exporttranscriptvideometrics/${windowsize}/${format}`,
      "GET",
      {}
    );
  }

  getSynthesizedFeedbackMetrics(sessionId, sessionDeviceId) {
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/synthesized_feedback_metrics`,
      "GET",
      {}
    );
  }

  getSynthesizedSessionAnalytics(sessionId, sessionName) {
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/sessionname/${sessionName}/synthesized_session_analytics`,
      "GET",
      {}
    );
  }

   getSurveyResponseSubmitted(sessionId, sessionDeviceId,username) {
    return this.api.httpRequestCall(
      `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/username/${username}/single_survey_response`,
      "GET",
      {}
    );
  }

  getLLMFeedbackBasedOnMetrics(metricData) {
    return this.api.httpRequestCall(
      `api/v1/llmqueries/generate_llm_feedback_based_on_metrics`,
      "POST",
      metricData
    );
  }

  getLLMPromptResponse(metricData) {
    return this.api.httpRequestCall(
      `api/v1/llmqueries/fetch_response_for_question`,
      "POST",
      metricData
    );
  }

  get_llm_question_answer_interactions(sessionId, sessionDeviceId,username) {
    return this.api.httpRequestCall(
      `api/v1/llminteractiveprompting/sessionid/${sessionId}/device/${sessionDeviceId}/username/${username}`,
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

  updateranscriptSpeaker(sessiondeviceId,transcriptId, speakerId, speakerAlias) {
    const body = {
      sessiondeviceId : sessiondeviceId,
      transcriptId: transcriptId,
      speakerId: speakerId,
      speakerAlias: speakerAlias
    };
    
    return this.api.httpRequestCall(`api/v1/updatetranscriptspeaker`, "POST", body);
  }

   deleteTranscriptById(sessiondeviceId,transcriptId) {
    
    return this.api.httpRequestCall(`api/v1/deletetranscriptById/${sessiondeviceId}/${transcriptId}`, "DELETE", {});
  }
}

export { SessionService };
