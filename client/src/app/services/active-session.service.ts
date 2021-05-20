import { Injectable} from '@angular/core';
import { BehaviorSubject } from 'rxjs/BehaviorSubject';
import { SocketService } from './socket.service';
import { SessionService } from './session.service';
import { SessionModel } from '../models/session';
import { SessionDeviceModel } from '../models/session-device';
import { TranscriptModel } from '../models/transcript';

@Injectable()
export class ActiveSessionService {

  constructor(private socketService: SocketService,
              private sessionService: SessionService) { }

  private sessionSource = new BehaviorSubject<SessionModel>(null);
  private sessionDeviceSource = new BehaviorSubject<SessionDeviceModel[]>([]);
  private transcriptSource = new BehaviorSubject<TranscriptModel[]>([]);

  socket: any;
  sessionId: any;
  initialized = false;

  initialize(sessionId: any) {
    if (this.sessionId === sessionId) {
      return;
    }
    this.close();
    this.sessionId = sessionId;
    // Call APIs.
    this.sessionService.getSession(sessionId).subscribe(session => {
      this.sessionSource.next(session);
      this.sessionService.getSessionDevices(sessionId).subscribe(devices => {
        this.sessionDeviceSource.next(devices);
        this.initializeSocket();
        this.initialized = true;
      });
    });
  }

  initializeSocket() {
    // Create Socket.
    this.socket = this.socketService.createSocket('session', this.sessionId);

    // Update device.
    this.socket.on('device_update', e => {
      const updatedDevice = SessionDeviceModel.fromJson(JSON.parse(e));
      const currentDevices = this.sessionDeviceSource.getValue();
      const index = currentDevices.findIndex(d => d.id === updatedDevice.id);
      if (index !== -1) {
        currentDevices[index] = updatedDevice;
        this.sessionDeviceSource.next(currentDevices);
      } else {
        currentDevices.push(updatedDevice);
        this.sessionDeviceSource.next(currentDevices);
      }
    });

    //  Remove device
    this.socket.on('device_removed', e => {
      const removedDeviceId = JSON.parse(e)['id'];
      const currentDevices = this.sessionDeviceSource.getValue().filter(d => d.id !== removedDeviceId);
      const currentTranscripts = this.transcriptSource.getValue().filter(d => d.session_device_id !== removedDeviceId);

      this.sessionDeviceSource.next(currentDevices);
      this.transcriptSource.next(currentTranscripts);
    });

    // Update session.
    this.socket.on('session_update', e => {
      this.sessionSource.next(SessionModel.fromJson(JSON.parse(e)));
    });

    // Handle room join.
    this.socket.on('room_joined', e => {});

    // Update transcripts.
    this.socket.on('transcript_update', e => {
      const data = JSON.parse(e);
      const currentTranscripts = this.transcriptSource.getValue();
      currentTranscripts.push(TranscriptModel.fromJson(data));
      this.transcriptSource.next(currentTranscripts);
    });

    // Initial digest of transcripts.
    this.socket.on('transcript_digest', e => {
      console.log('digesting');
      const data = JSON.parse(e);
      console.log(data);
      const transcripts = [];
      for (const transcript of data) {
          transcripts.push(TranscriptModel.fromJson(transcript));
      }
      this.transcriptSource.next(transcripts);
    });
  }

  close() {
    if (this.socket != null) {
      this.socket.disconnect();
    }
    this.initialized = false;
    this.sessionId = null;
    this.sessionSource.next(null);
    this.sessionDeviceSource.next([]);
    this.transcriptSource.next([]);
  }

  getSession() {
    return this.sessionSource;
  }

  getSessionDevice(sessionDeviceId: number) {
    return this.sessionDeviceSource.map(devices => {
      return devices.find(d => d.id === sessionDeviceId);
    });
  }

  getSessionDevices() {
    return this.sessionDeviceSource;
  }

  getSessionDeviceTranscripts(sessionDeviceId: number) {
    return this.transcriptSource.map(ts => ts.filter(t => t.session_device_id === sessionDeviceId)
                                      .sort((a, b) => (a.start_time > b.start_time) ? 1 : -1));
  }
  getTranscripts() {
    return this.transcriptSource;
  }
}
