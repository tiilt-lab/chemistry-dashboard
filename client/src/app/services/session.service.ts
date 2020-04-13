import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs/Observable';
import { SessionModel } from '../models/session';
import { TranscriptModel } from '../models/transcript';
import { SessionDeviceModel } from '../models/session-device';
import { FolderModel } from '../models/folder';
import 'rxjs/add/operator/map';

@Injectable()
export class SessionService {
  public deviceIds = [];
  public keywordListId = '';
  constructor(private api: ApiService) {}

  endSession(sessionId: number) {
    return this.api.post(`api/v1/sessions/${sessionId}/stop`, {}).map(response => {
      return SessionModel.fromJson(response.json());
    });
  }

  getSessions(): Observable<any> {
    return this.api.get('api/v1/sessions').map(response => {
      return SessionModel.fromJsonList(response.json());
    });
  }

  getSession(sessionId: number): Observable<any> {
    return this.api.get(`api/v1/sessions/${sessionId}`).map(response => {
      return SessionModel.fromJson(response.json());
    });
  }

  deleteSession(sessionId: number): Observable<any> {
    return this.api.delete(`api/v1/sessions/${sessionId}`).map(response => {
      return response.json();
    });
  }

  updateSession(sessionId: number, name: string): Observable<any> {
    const body = {
      'name': name
    };
    return this.api.put(`api/v1/sessions/${sessionId}`, body).map(response => {
      return SessionModel.fromJson(response.json());
    });
  }

  updateSessionFolder(sessionId: number, folder: number): Observable<any> {
    const body = {
      'folder': folder
    };
    return this.api.put(`api/v1/sessions/${sessionId}`, body).map((x) => {
      return SessionModel.fromJson(x.json());
    });
  }

  getSessionDevice(sessionId: number, sessionDeviceId: number): Observable<any> {
    return this.api.get(`api/v1/sessions/${sessionId}/devices/${sessionDeviceId}`).map(response => {
      return SessionDeviceModel.fromJson(response.json());
    });
  }

  getSessionDevices(sessionId: number): Observable<any> {
    return this.api.get(`api/v1/sessions/${sessionId}/devices`).map(response => {
      return SessionDeviceModel.fromJsonList(response.json());
    });
  }

  getSessionDeviceTranscripts(sessionId: number, sessionDeviceId: number, startTime: number = 0) {
    return this.api.get(`api/v1/sessions/${sessionId}/devices/${sessionDeviceId}/transcripts`).map(response => {
      return TranscriptModel.fromJsonList(response.json());
    });
  }

  setDeviceButton(sessionDeviceId: any, pressed: boolean, key: string) {
    const body = {
      'id': sessionDeviceId,
      'activated': pressed
    };
    const headers = {
      'X-Processing-Key': key
    };
    return this.api.post(`api/v1/help_button`, body, {}, true, headers).map((x) => {
      return x.json();
    });
  }

  createNewSession(name: string, devices: number[], keywordListId: number, byod: boolean, features: boolean, doa: boolean, folder: number) {
    const body = {
      'name': name,
      'devices': devices,
      'keywordListId': keywordListId,
      'byod': byod,
      'features': features,
      'doa': doa,
      'folder': folder
    };

    return this.api.post('api/v1/sessions', body).map(response => {
      return SessionModel.fromJson(response.json());
    });
  }

  joinByodSession(name: string, passcode: string) {
    const body = {
      'name': name,
      'passcode': passcode
    };
    return this.api.post('api/v1/sessions/byod', body).map(response => {
      const json = response.json();
      json['session'] = SessionModel.fromJson(json['session']);
      json['session_device'] = SessionDeviceModel.fromJson(json['session_device']);
      return json;
    });
  }

  addPodToSession(sessionId: number, podId: number) {
    const body = {
      'sessionId': sessionId,
      'podId': podId
    };
    return this.api.post('api/v1/sessions/pod', body).map(response => {
      return SessionDeviceModel.fromJson(response.json());
    });
  }

  setPasscodeStatus(sessionId: number, state: string) {
    const body = {
      'state': state
    };
    return this.api.post(`api/v1/sessions/${sessionId}/passcode`, body).map(response => {
      return SessionDeviceModel.fromJson(response.json());
    });
  }

  removeDeviceFromSession(sessionId: number, sessionDeviceId: number, shouldDelete: boolean = false) {
    const query = {
      'delete': shouldDelete
    };
    return this.api.delete(`api/v1/sessions/${sessionId}/devices/${sessionDeviceId}`, query).map(response => {
      return response.json();
    });
  }

  downloadSessionReport(sessionId: number, fileName: string) {
    return this.api.get(`api/v1/sessions/${sessionId}/export`).map(response => {
      const anchor = document.createElement('a');
      anchor.href = 'data:attachment/csv;charset=utf-8,' + encodeURI((<any>response)._body),
      anchor.download = fileName + '.csv';
      anchor.click();
      return true;
    });
  }

  getFolders(): Observable<any> {
    return this.api.get(`api/folders`).map(response => {
      return FolderModel.fromJsonList(response.json());
   });
  }

  addFolder(name: string, parent: number) {
    const body = {
      'name': name,
      'parent': parent
    };
    return this.api.post(`api/folder`, body).map(response => {
      return FolderModel.fromJson(response.json());
    });
  }

  updateFolder(folderId: number, parent: number, name: string):  Observable<any> {
    const body = {
      'parent': parent,
      'name': name,
    };
    return this.api.post(`api/folders/${folderId}`, body).map((response) => {
      return FolderModel.fromJson(response.json());
    });
  }

  deleteFolder(folderId: number): Observable<any> {
    return this.api.delete(`api/folders/${folderId}`).map((x) => {
      return x.json();
    });
  }
}
