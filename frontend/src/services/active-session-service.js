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
        if (this.sessionId === sessionId) {
            return
        }
        this.close()
        this.sessionId = sessionId
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
            this.sessionSource.next(SessionModel.fromJson(JSON.parse(e)))
        })

        // Handle room join.
        this.socket.on("room_joined", (e) => {
            this.initialized = true
           /* 
            this.sessionService
                .getSessionSpeakerMetrics(this.sessionId)
                .then((response) => response.json())
                .then((json) => {
                    const data = JSON.parse(json);
                    const transcripts = []
                    for (const transcript_metrics of data) {
                        const speaker_metrics = SpeakerMetricsModel.fromJsonList(
                            transcript_metrics["speaker_metrics"],
                        )
                        const transcript_model = TranscriptModel.fromJson(
                            transcript_metrics["transcript"],
                            speaker_metrics,
                        )
                        transcripts.push(transcript_model)
                    }
                    this.transcriptSource.next(transcripts)
                })
                    */
        })

        // Update transcripts and speaker metrics.
        this.socket.on("transcript_metrics_update", (e) => {
            const data = JSON.parse(e)

            const speaker_metrics = SpeakerMetricsModel.fromJsonList(
                data["speaker_metrics"],
            )
            const transcript_model = TranscriptModel.fromJson(
                data["transcript"],
                speaker_metrics,
            )
            const currentTranscripts = this.transcriptSource.getValue()

            currentTranscripts.push(transcript_model)
            this.transcriptSource.next(currentTranscripts)
        })

        // Initial digest of transcripts and speaker metrics.
        this.socket.on("transcript_metrics_digest", (e) => {
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
                transcripts.push(transcript_model)
            }
            this.transcriptSource.next(transcripts)
        })
    }

    close() {
        if (this.socket != null) {
            this.socket.disconnect()
        }
        this.initialized = false
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

        return this.transcriptSource
    }
    getTranscripts() {
        return this.transcriptSource
    }
}
