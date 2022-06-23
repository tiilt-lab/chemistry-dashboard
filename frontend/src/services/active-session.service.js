import { BehaviorSubject } from 'rxjs/BehaviorSubject';
import { SocketService } from './socket-service';
import { SessionService } from './session-service';
import { SessionModel } from '../models/session';
import { SessionDeviceModel } from '../models/session-device';
import { TranscriptModel } from '../models/transcript';


export class ActiveSessionService {

    socketService = new SocketService();
    sessionService = new SessionService();

    sessionSource = new BehaviorSubject(null);
    sessionDeviceSource = new BehaviorSubject([]);
    transcriptSource = new BehaviorSubject([]);

    socket;
    sessionId;
    initialized = false;

    initialize(sessionId) {
        if (this.sessionId === sessionId) {
            return;
        }
        this.close();
        this.sessionId = sessionId;
        // Call APIs.
        const fetchRes = this.sessionService.getSession(sessionId);
        fetchRes.then((response) => {
            if(response.status === 200){
            const session = SessionModel.fromJson(response.json());
            this.sessionSource.next(session);
            const fectdev = this.sessionService.getSessionDevices(sessionId)
            fectdev.then(
                (response) => {
                    if(response.status === 200){
                    const devices = SessionDeviceModel.fromJsonList(response.json())
                    this.sessionDeviceSource.next(devices);
                    this.initializeSocket();
                    this.initialized = true;
                }},
                (apierror) => { console.log("file active-session-service: func initialize 1", apierror) }
            )}},
            (apiError) => { console.log("file active-session-service: func initialize 2", apiError) });
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
        this.socket.on('room_joined', e => { });

        // Update transcripts.
        this.socket.on('transcript_update', e => {
            const data = JSON.parse(e);
            const currentTranscripts = this.transcriptSource.getValue();
            currentTranscripts.push(TranscriptModel.fromJson(data));
            this.transcriptSource.next(currentTranscripts);
        });

        // Initial digest of transcripts.
        this.socket.on('transcript_digest', e => {
            const data = JSON.parse(e);
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

    getSessionDevice(sessionDeviceId) {
        return this.sessionDeviceSource.map(devices => {
            return devices.find(d => d.id === sessionDeviceId);
        });
    }

    getSessionDevices() {
        return this.sessionDeviceSource;
    }

    getSessionDeviceTranscripts(sessionDeviceId) {
        return this.transcriptSource.map(ts => ts.filter(t => t.session_device_id === sessionDeviceId)
            .sort((a, b) => (a.start_time > b.start_time) ? 1 : -1));
    }
    getTranscripts() {
        return this.transcriptSource;
    }
}
