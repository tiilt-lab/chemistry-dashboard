import { BehaviorSubject } from "rxjs"
import { map } from "rxjs"
import { SocketService } from "./socket-service"
import { SessionService } from "./session-service"
import { SessionModel } from "../models/session"
import { SessionDeviceModel } from "../models/session-device"
import { TranscriptModel } from "../models/transcript"
import { SpeakerMetricsModel } from "../models/speaker-metrics"

export class ActiveSessionService {
    socketService = new SocketService()
    sessionService = new SessionService()

    sessionSource = new BehaviorSubject(null)
    sessionDeviceSource = new BehaviorSubject([])
    transcriptSource = new BehaviorSubject([])

    socket
    sessionId
    initialized = false

    initialize(sessionId, setInitialized) {
        console.log('ActiveSessionService.initialize called for sessionId:', sessionId, 'current:', this.sessionId, 'initialized:', this.initialized);

        // If already initialized for this session AND we have data, just set the flag and return
        if (this.sessionId === sessionId && this.initialized && this.sessionSource.getValue() !== null) {
            console.log('ActiveSessionService: Already initialized with data, returning early');
            if (setInitialized) setInitialized(true);
            return;
        }

        // Only close if switching to a DIFFERENT session
        if (this.sessionId !== null && this.sessionId !== sessionId) {
            console.log('ActiveSessionService: Closing for session change');
            this.close();
        }

        this.sessionId = sessionId
        this.initialized = false // Reset initialized flag to ensure we fetch data
        // Call APIs.
        const fetchRes = this.sessionService.getSession(sessionId)
        fetchRes.then(
            (response) => {
                if (response.status === 200) {
                    const respSess = response.json()
                    respSess.then((session) => {
                        const sessionObj = SessionModel.fromJson(session)
                        this.sessionSource.next(sessionObj)
                        const fectdev =
                            this.sessionService.getSessionDevices(sessionId)
                        fectdev.then(
                            (response) => {
                                if (response.status === 200) {
                                    const respDev = response.json()
                                    respDev.then((devices) => {
                                        const devicesObj =
                                            SessionDeviceModel.fromJsonList(
                                                devices,
                                            )
                                        this.sessionDeviceSource.next(
                                            devicesObj,
                                        )
                                        this.initializeSocket()
                                        setInitialized(true)
                                    })
                                }
                            },
                            (apierror) => {
                                console.log(
                                    "file active-session-service: func initialize 1",
                                    apierror,
                                )
                            },
                        )
                    })
                }
            },
            (apiError) => {
                console.log(
                    "file active-session-service: func initialize 2",
                    apiError,
                )
            },
        )
    }

    initializeSocket() {
        // Create Socket.
        this.socket = this.socketService.createSocket("session", this.sessionId)
        // Update device.
        this.socket.on("device_update", (e) => {
            if (!this.initialized) return; // Guard against race conditions
            const updatedDevice = SessionDeviceModel.fromJson(JSON.parse(e))
            const currentDevices = this.sessionDeviceSource.getValue()
            const index = currentDevices.findIndex(
                (d) => d.id === updatedDevice.id,
            )
            if (index !== -1) {
                currentDevices[index] = updatedDevice
                this.sessionDeviceSource.next(currentDevices)
            } else {
                currentDevices.push(updatedDevice)
                this.sessionDeviceSource.next(currentDevices)
            }
        })

        //  Remove device
        this.socket.on("device_removed", (e) => {
            if (!this.initialized) return; // Guard against race conditions
            const removedDeviceId = JSON.parse(e)["id"]
            const currentDevices = this.sessionDeviceSource
                .getValue()
                .filter((d) => d.id !== removedDeviceId)
            const currentTranscripts = this.transcriptSource
                .getValue()
                .filter((d) => d.session_device_id !== removedDeviceId)

            this.sessionDeviceSource.next(currentDevices)
            this.transcriptSource.next(currentTranscripts)
        })

        // Update session.
        this.socket.on("session_update", (e) => {
            if (!this.initialized) return; // Guard against race conditions
            this.sessionSource.next(SessionModel.fromJson(JSON.parse(e)))
        })

        // Handle room join.
        this.socket.on("room_joined", (e) => {
            this.initialized = true
        })

        // Update transcripts.
        this.socket.on("transcript_update", (e) => {
            if (!this.initialized) return; // Guard against race conditions
            const data = JSON.parse(e);
            const currentTranscripts = this.transcriptSource.getValue();
            console.log(`BEFORE: ${currentTranscripts.length} transcripts, adding ID ${data.id}`);

            // Check if transcript already exists to prevent duplicates
            // Use Number() to normalize IDs for comparison (handles both string and number IDs)
            const existingIndex = currentTranscripts.findIndex(t => Number(t.id) === Number(data.id));
            if (existingIndex === -1) {
                currentTranscripts.push(TranscriptModel.fromJson(data));
            } else {
                // Update existing transcript
                currentTranscripts[existingIndex] = TranscriptModel.fromJson(data);
            }

            this.transcriptSource.next(currentTranscripts);
        });

        // Initial digest of transcripts.
        this.socket.on('transcript_digest', e => {
            if (!this.initialized) return; // Guard against race conditions
            const data = JSON.parse(e);
            const transcripts = [];
            for (const transcript of data) {
                transcripts.push(TranscriptModel.fromJson(transcript));
            }
            this.transcriptSource.next(transcripts);
        });

        // Update transcripts and speaker metrics.
        this.socket.on("transcript_metrics_update", (e) => {
            if (!this.initialized) return; // Guard against race conditions
            const data = JSON.parse(e)
            console.log(`METRICS UPDATE: adding/updating transcript ID ${data.transcript.id}`);

            const speaker_metrics = SpeakerMetricsModel.fromJsonList(
                data["speaker_metrics"],
            )
            const transcript_model = TranscriptModel.fromJson(
                data["transcript"],
                speaker_metrics,
            )
            const currentTranscripts = this.transcriptSource.getValue()

            // Check if transcript already exists to prevent duplicates
            // Use Number() to normalize IDs for comparison (handles both string and number IDs)
            const existingIndex = currentTranscripts.findIndex(t => Number(t.id) === Number(data.transcript.id));
            if (existingIndex === -1) {
                currentTranscripts.push(transcript_model);
            } else {
                // Update existing transcript with new metrics
                currentTranscripts[existingIndex] = transcript_model;
            }

            this.transcriptSource.next(currentTranscripts)
        })

        // Initial digest of transcripts and speaker metrics.
        this.socket.on("transcript_metrics_digest", (e) => {
            if (!this.initialized) return; // Guard against race conditions
            const data = JSON.parse(e)
            const transcripts = this.transcriptSource.getValue()
            for (const transcript_metrics of data) {
                const speaker_metrics = SpeakerMetricsModel.fromJsonList(
                    transcript_metrics["speaker_metrics"],
                )
                const transcript_model = TranscriptModel.fromJson(
                    transcript_metrics["transcript"],
                    speaker_metrics,
                )

                // Check if transcript already exists to prevent duplicates
                // Use Number() to normalize IDs for comparison (handles both string and number IDs)
                const existingIndex = transcripts.findIndex(t => Number(t.id) === Number(transcript_model.id));
                if (existingIndex === -1) {
                    transcripts.push(transcript_model);
                } else {
                    // Update existing transcript with new metrics
                    transcripts[existingIndex] = transcript_model;
                }
            }
            this.transcriptSource.next(transcripts)
        })
    }

    close() {
        // First mark as not initialized to prevent socket events from firing
        this.initialized = false

        // Then disconnect socket and remove all listeners
        if (this.socket != null) {
            this.socket.off();
            this.socket.disconnect()
            this.socket = null
        }

        // Finally reset state
        this.sessionId = null
        this.sessionSource.next(null)
        this.sessionDeviceSource.next([])
        this.transcriptSource.next([])
    }

    getSession() {
        return this.sessionSource.getValue()
    }

    getSessionDevice(sessionDeviceId) {
        return this.sessionDeviceSource
            .getValue()
            .find((d) => d.id === parseInt(sessionDeviceId, 10))
    }

    getSessionDevices() {
        return this.sessionDeviceSource.getValue()
    }

    getSessionDeviceTranscripts(sessionDeviceId, setState) {
        this.transcriptSource.subscribe((e) => {
            if (Object.keys(e).length !== 0) {
                const data = e
                    .filter(
                        (t) =>
                            t.session_device_id ===
                            parseInt(sessionDeviceId, 10),
                    )
                    .sort((a, b) => (a.start_time > b.start_time ? 1 : -1))
                //console.log(data,'still debugging ...')
                setState(data)
            }
        })

        return this.transcriptSource.asObservable()
    }
    getTranscripts() {
        return this.transcriptSource.asObservable()
    }
}
