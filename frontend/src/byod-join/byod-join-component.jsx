import { useEffect, useState, useRef } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { SessionService } from "../services/session-service"
import { ByodJoinPage } from "./html-pages"
import { SessionModel } from "../models/session"
import { SessionDeviceModel } from "../models/session-device"
import { SpeakerModel } from "../models/speaker"
import { StudentModel } from "../models/student"
import { ApiService } from "../services/api-service"
import { AuthService } from "../services/auth-service"
import fixWebmDuration from "fix-webm-duration"

/*
BYOD Connection Order

1. VerifyInputAndAudio
2. RequestAccessKey
3. ConnectToProcessors
4. DetermineSpeakers*
5. requestStartToProcessing
6. Media Socket Worklets
*/

function JoinPage() {
    // Audio connection data
    const audiows = useRef(null)
    const [videows, setVideoWs] = useState(null)
    const [audioconnected, setAudioConnected] = useState(false)
    const [videoconnected, setVideoConnected] = useState(false)
    const [authenticated, setAuthenticated] = useState(false)
    const [streamReference, setStreamReference] = useState(null)
    const [audioContext, setAudioContext] = useState(null)
    const [mediaRecorder, setMediaRecorder] = useState(null)
    const [processor, setProcessor] = useState(null)
    const [audioSenderProcessor, setAudioSenderProcessor] = useState(null)
    const [source, setSource] = useState(null)
    const [ending, setEnding] = useState({ value: false })
    const [reconnectCounter, setReconnectCounter] = useState(0)
    const [showAlert, setShowAlert] = useState(false)
    const [alertMessage, setAlertMessage] = useState("")
    const [frameBuffer, setFrameBuffer] = useState([]); // Buffer for cartoonized frames
    const [frameBufferLength, setFrameBufferLength] = useState(0);
    const [cartoonImgUrl, setCartoonImgUrl] = useState("");
    const [cartoonImgBatch, setCartoonImgBatch] = useState(1);
    const [renderingStarted, setRenderingStarted] = useState(false)

    // Session data
    const [sessionDevice, setSessionDevice] = useState(null)
    const [session, setSession] = useState(null)
    const [key, setKey] = useState(null)

    const sessionService = new SessionService()
    const apiService = new ApiService()

    const [transcripts, setTranscripts] = useState([])
    const [videoMetrics, setVideoMetrics] = useState([])
    const [startTime, setStartTime] = useState()
    const [endTime, setEndTime] = useState()
    const [displayTranscripts, setDisplayTranscripts] = useState([])
    const [displayVideoMetrics, setDisplayVideoMetrics] = useState([])
    const [currentTranscript, setCurrentTranscript] = useState({})
    const [timeRange, setTimeRange] = useState([0, 1])
    const [selectedSpkrId1, setSelectedSpkrId1] = useState(-1)
    const [selectedSpkrId2, setSelectedSpkrId2] = useState(-1)
    const [spkr1Transcripts, setSpkr1Transcripts] = useState([])
    const [spkr2Transcripts, setSpkr2Transcripts] = useState([])
    const [spkr1VideoMetrics, setSpkr1VideoMetrics] = useState([])
    const [spkr2VideoMetrics, setSpkr2VideoMetrics] = useState([])
    const [selectedSpkralias, setSelectedSpkralias] = useState("");
    const [details, setDetails] = useState("Group")

    const [currentForm, setCurrentForm] = useState("")
    const [displayText, setDisplayText] = useState("")
    const [reload, setReload] = useState(false)
    const [pageTitle, setPageTitle] = useState("Join Discussion")
    const [sessionClosing, setSessionClosing] = useState(false)

    const [name, setName] = useState("")
    const [pcode, setPcode] = useState("")
    const [wrongInput, setWrongInput] = useState(false)
    const [joinwith, setJoinwith] = useState("")
    const [preview, setPreview] = useState(false)
    const [previewLabel, setPreviewLabel] = useState("Turn On Preview")
    const navigate = useNavigate()

    const [showFeatures, setShowFeatures] = useState([])
    const [showBoxes, setShowBoxes] = useState([])

    const [numSpeakers, setNumSpeakers] = useState()
    const [speakers, setSpeakers] = useState([])
    const [speakersValidated, setSpeakersValidated] = useState(false)
    const [selectedSpeaker, setSelectedSpeaker] = useState(null)
    const [currBlob, setCurrBlob] = useState(null)
    const [invalidName, setInvalidName] = useState(false)
    const [constraintObj, setConstraintObj] = useState(null)
    const [registeredStudentData, setRegisteredStudentData] = useState(null)
    const [registeredUserAliasChanged, setRegisteredUserAliasChanged] = useState(false)
    const [registeredAudioFingerprintAdded, setRegisteredAudioFingerprintAdded] = useState(false)
    const [registeredVideoFingerprintAdded, setRegisteredVideoFingerprintAdded] = useState(false)
    

    const POD_COLOR = "#FF6655"
    const GLOW_COLOR = "#ffc3bd"
    const interval = 10000

    let wakeLock = null

    useEffect(() => {
        // initialize the options toolbar
        let featuresArr = [
            "Emotional tone",
            "Analytic thinking",
            "Clout",
            "Authenticity",
            "Confusion",
            "Participation",
            "Social Impact",
            "Responsivity",
            "Internal Cohesion",
            "Newness",
            "Communication Density",
            "Attention Level",
            "Facial Emotions",
            "Object Focused On"
        ]
        initChecklistData(featuresArr, setShowFeatures)
        // initialize the components toolbar
        let boxArr = [
            "Timeline control",
            "Discussion timeline",
            "Keyword detection",
            "Discussion features",
            "Radar chart",
            "Participation",
            "Social Impact",
            "Responsivity",
            "Internal Cohesion",
            "Newness",
            "Communication Density",
            "Video Metrics"
        ]
        initChecklistData(boxArr, setShowBoxes)
    }, [])

    //Use effect to display processed cartoonized image
    useEffect(() => {
        console.log('inside renderframe buffer useeffect ', frameBufferLength)
        renderFrameFromBuffer()
    }, [frameBufferLength])

    useEffect(() => {
        if (constraintObj && pcode !== "" && joinwith !== "") handleStream()
    }, [constraintObj, pcode, joinwith])
    /*
        useEffect(() => {
            if (
                audiows.current != null
            ) {
                console.log("called connect_audio_processor_service")
                connect_audio_processor_service()
            }
        }, [audiows.current])
    */
    useEffect(() => {
        if (videows != null) {
            console.log("called connect_video_processor_service")
            connect_video_processor_service()
        }
    }, [videows])

    //Use effect to intermetently reload the transcript
    useEffect(() => {
        let intervalLoad
        // fetch the transcript
        if (session !== null && sessionDevice !== null) {
            fetchTranscript(sessionDevice.id)
            fetchVideoMetric(sessionDevice.id)
            intervalLoad = setInterval(() => {
                fetchTranscript(sessionDevice.id)
                fetchVideoMetric(sessionDevice.id)
            }, 2000)
        }

        return () => {
            clearInterval(intervalLoad)
        }
    }, [session, sessionDevice])

    useEffect(() => {
        if (session !== null && speakersValidated) {
            const sessionLen =
                Object.keys(session).length > 0 ? session.length : 0
            const sTime = Math.round(sessionLen * timeRange[0] * 100) / 100
            const eTime = Math.round(sessionLen * timeRange[1] * 100) / 100
            setStartTime(sTime)
            setEndTime(eTime)
            generateDisplayTranscripts(sTime, eTime)
            generateDisplayVideoMetrics(sTime, eTime)
        }
    }, [transcripts, videoMetrics,startTime, endTime, session, speakersValidated, timeRange])

    useEffect(() => {
        if (displayTranscripts) {
            console.log("reloaded page - displayTranscripts")
            setSpeakerTranscripts()
        }
        if(displayVideoMetrics){
            console.log("reloaded page - displayVideoMetrics")
            setSpeakerVideoMetrics()
        }
    }, [displayTranscripts, displayVideoMetrics,selectedSpkrId1, selectedSpkrId2, details])

    //Use effect to start audio and video processing
    useEffect(() => {
        if (audioconnected && !videoconnected) {
            requestStartAudioProcessing()
        }
        if (audioconnected && videoconnected) {
            requestStartVideoProcessing()
        }
    }, [audioconnected, videoconnected])

    //Use effect to start the camera and microphone for video and audio capturing
    useEffect(() => {
        if (authenticated) {
            const loadWorklet = async () => {
                await audioContext.audioWorklet.addModule(
                    "audio-sender-processor.js",
                )
                const workletProcessor = new AudioWorkletNode(
                    audioContext,
                    "audio-sender-processor",
                )
                workletProcessor.port.onmessage = (data) => {
                    audiows.current.send(data.data.buffer)
                }
                source
                    .connect(workletProcessor)
                    .connect(audioContext.destination)
                setAudioSenderProcessor(workletProcessor)
            }

            const videoPlay = () => {
                let video = document.querySelector("video")
                console.log("video tag ", video)
                console.log("streamReference ", streamReference)
                video.srcObject = streamReference
                console.log("video.srcObject ", video.srcObject)
                video.onloadedmetadata = function (ev) {
                    video.play()
                    mediaRecorder.start(interval)
                }

                mediaRecorder.ondataavailable = async function (ev) {
                    const bufferdata = await ev.data.arrayBuffer()
                    fixWebmDuration(
                        ev.data,
                        interval * 6 * 60 * 24,
                        (fixedblob) => {
                            videows.send(fixedblob)
                            audiows.current.send(fixedblob)
                        },
                    )
                }
            }

            if (authenticated && joinwith === "Audio") {
                loadWorklet().catch(console.error)
            } else if (
                authenticated && speakersValidated &&
                (joinwith === "Video" || joinwith === "Videocartoonify")
            ) {
                console.log(audioconnected, authenticated, speakersValidated)
                videoPlay()
            }
        }
    }, [authenticated, speakersValidated])

    //Use effect to toggle video view pane
    useEffect(() => {
        if (preview) {
            setPreviewLabel("Turn Off Preview")
        } else {
            setPreviewLabel("Turn On Preview")
        }
    }, [preview])

    useEffect(() => {
        if (registeredStudentData != null) {
            changeAliasName(registeredStudentData.username)
        }
    }, [registeredStudentData])

    useEffect(() => {
        if (registeredUserAliasChanged) {
            addSavedSpeakerFingerprint()
        }
    }, [registeredUserAliasChanged])

    useEffect(() => {
        let proceed = false
        if (joinwith === "Video" || joinwith === "Videocartoonify")  {
                if (registeredAudioFingerprintAdded && registeredVideoFingerprintAdded) {
                    proceed = true
                }
            }else{
                if (registeredAudioFingerprintAdded){
                    proceed = true
                }
            }
        if (proceed) {

            const updatedSpeakers = speakers.map((s) =>
            s.id === selectedSpeaker.id ? { ...s, fingerprinted: true } : s,)
            setSpeakers(updatedSpeakers)
            setSelectedSpeaker(null)
            console.log("register fingerprint for " + registeredStudentData.username + " Added")
            setRegisteredStudentData(null)
            setRegisteredUserAliasChanged(false)
            setRegisteredAudioFingerprintAdded(false)
            setRegisteredVideoFingerprintAdded(false)
            closeDialog()
        }
    }, [registeredAudioFingerprintAdded, registeredVideoFingerprintAdded])

    //Use effect to display processed cartoonized image
    // useEffect(() => {
    //     console.log('inside renderframe buffer useeffect ', frameBufferLength)
    //     renderFrameFromBuffer()
    // }, [frameBufferLength])

    const openForms = (form, speaker = null) => {
        setCurrentForm(form)
        if (form === "fingerprintAudio" || form === "renameAlias" || form === "savedAudioVideoFingerprint") {
            setSelectedSpeaker(speaker)
        }
    }

    const closeForm = () => {
        setCurrentForm("")
    }

    // Disconnects from websocket server and audio stream.
    const disconnect = (permanent = false) => {
        console.log("disconnect called", permanent)
        if (ending.value)
            return
        if (permanent) {
            setPageTitle("Join Discussion")
            setName("")
            setPcode("")
            ending.value = true
            setSpeakersValidated(false)
            setSpeakers(null)
            setSession(null)
            setSessionDevice(null)
            setKey(null)
        }

        if (wakeLock) releaseWakeLock()

        if (source != null) {
            source.disconnect()
            setSource(null)
        }
        if (audioContext != null) {
            setAudioSenderProcessor(null)
        }
        if (mediaRecorder != null) {
            mediaRecorder.stop()
            setMediaRecorder(null)
        }

        if (streamReference != null) {
            streamReference.getAudioTracks().forEach((track) => track.stop())
            setStreamReference(null)
        }

        setAudioConnected(false)
        setVideoConnected(false)
        setAuthenticated(false)

        if (audiows.current != null) {
            audiows.current.close();
            audiows.current = null;
        }
        if (videows != null) {
            videows.close()
            setVideoWs(null)
        }
    }

    const confirmSpeakers = () => {
        console.log(speakers)
        if (speakers.every((s) => s.fingerprinted)) {
            let message = null
            message = {
                type: "speaker",
                id: "done",
                speakers: speakers,
            }
            audiows.current.send(JSON.stringify(message))
            
            if (joinwith === "Video" || joinwith === "Videocartoonify")  {
                videows.send(JSON.stringify(message))
            }
            setSpeakersValidated(true)
        } else {
            setDisplayText(
                "Not all added speakers have a fingerprint. Please record one for each speaker",
            )
            setCurrentForm("FingerprintingError")
        }
    }

    const saveAudioFingerprint = (audioblob) => {
        //store blob for confirmation
        setCurrBlob(audioblob)
    }

    const addSpeakerFingerprint = async () => {
        if (audiows.current === null) {
            return
        }

        let message = null
        message = {
            type: "speaker",
            id: selectedSpeaker.id,
            alias: selectedSpeaker.alias,
            size: currBlob.size,
            blob_type: currBlob.type,
        }
        let data = await currBlob.arrayBuffer()
        let audiodata = await audioContext.decodeAudioData(data)
        console.log(speakers)

        const updatedSpeakers = speakers.map((s) =>
            s.id === selectedSpeaker.id ? { ...s, fingerprinted: true } : s,
        )

        setSpeakers(updatedSpeakers)
        audiows.current.send(JSON.stringify(message))
        audiows.current.send(audiodata.getChannelData(0))
        console.log("sent speaker fingerprint")
        setCurrBlob(null)
        closeDialog()
    }

    const startProcessingSavedSpeakerFingerprint = async (registeredUsername) => {

        const fetchData = new AuthService().getStudentProfileByID(registeredUsername)
        fetchData
            .then(
                (response) => {
                    if (response.status === 200) {
                        response.json().then((jsonObj) => {
                            console.log(jsonObj)
                            const student_data = StudentModel.fromJson(jsonObj)
                            setRegisteredStudentData(student_data)
                        })
                    } else {
                        setInvalidName(true)
                    }
                },
                (apierror) => {
                    console.log(
                        "byod-join-components func: startProcessingSavedSpeakerFingerprint 1 ",
                        apierror,
                    )
                },
            )

    }

    const addSavedSpeakerFingerprint = async () => {

        let message = null
        message = {
            type: "add-saved-fingerprint",
            id: selectedSpeaker.id,
            alias: registeredStudentData.username
        }

        console.log(speakers)

        if (joinwith === "Video" || joinwith === "Videocartoonify") {

            if (videows === null || audiows.current === null) {
                return
            }
            audiows.current.send(JSON.stringify(message))
            videows.send(JSON.stringify(message))
        } else {
            if (audiows.current === null) {
                return
            }

            audiows.current.send(JSON.stringify(message))
        }


    }

    const changeAliasName = (newAlias) => {
        if (newAlias === "") {
            setInvalidName(true)
            return
        }
        console.log(
            `Speaker ID: ${selectedSpeaker.id} with new alias: ${newAlias}`,
        )
        setInvalidName(false)
        const speakerId = selectedSpeaker.id
        const fetchData = new SessionService().updateCollaborator(
            speakerId,
            newAlias,
        )
        fetchData
            .then(
                (response) => {
                    if (response.status === 200) {
                        response.json().then((jsonObj) => {
                            console.log(jsonObj)
                            const speaker = SpeakerModel.fromJson(jsonObj)
                            console.log(speaker)
                            const updatedSpeakers = speakers.map((s) =>
                                s.id === selectedSpeaker.id
                                    ? { ...s, alias: speaker.alias }
                                    : s,
                            )
                            setSpeakers(updatedSpeakers)
                            //only set to null when change alias is invoked by cicking the change alias option 
                            if (registeredStudentData === null) {
                                setSelectedSpeaker(null)
                            }
                            if (registeredStudentData !== null) {
                                setRegisteredUserAliasChanged(true)
                            }
                        })
                    } else {
                        setShowAlert(true)
                        setAlertMessage(response.json()["message"])
                    }
                },
                (apierror) => {
                    console.log(
                        "byod-join-components func: changealiasname 1 ",
                        apierror,
                    )
                },
            )
            .finally(() => {
                closeDialog()
            })
    }

    const handleStream = async () => {
        try {
            //Await wake lock for screen first
            await acquireWakeLock()
            //handle older browsers that might implement getUserMedia in some way

            if (navigator.mediaDevices === undefined) {
                navigator.mediaDevices = {}
                navigator.mediaDevices.getUserMedia = function (constraintObj) {
                    let getUserMedia =
                        navigator.webkitGetUserMedia ||
                        navigator.mozGetUserMedia
                    if (!getUserMedia) {
                        return Promise.reject(
                            new Error(
                                "getUserMedia is not implemented in this browser",
                            ),
                        )
                    }
                    return new Promise(function (resolve, reject) {
                        getUserMedia.call(
                            navigator,
                            constraintObj,
                            resolve,
                            reject,
                        )
                    })
                }
            } else {
                navigator.mediaDevices
                    .enumerateDevices()
                    .then((devices) => {
                        devices.forEach((device) => {

                            // console.log(device.kind.toUpperCase(), device.label);
                            //, device.deviceId
                        })
                    })
                    .catch((err) => {
                        console.log(err.name, err.message)
                    })
            }

            if (navigator.mediaDevices != null) {
                const stream =
                    await navigator.mediaDevices.getUserMedia(constraintObj)

                // media.then(function (stream) {
                setStreamReference(stream)
                //keep this here for now to enable to capturing of audio finger printing
                const context = new AudioContext({ sampleRate: 16000 })
                setSource(context.createMediaStreamSource(stream))
                setAudioContext(context)
                if (joinwith === "Audio") {
                    console.log("connect to websocket");
                    audiows.current = new WebSocket(
                        apiService.getAudioWebsocketEndpoint(),
                    )
                    connect_audio_processor_service();

                } else if (
                    joinwith === "Video" ||
                    joinwith === "Videocartoonify"
                ) {
                    var opt
                    if (
                        MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
                    ) {
                        opt = { mimeType: "video/webm; codecs=vp9,opus" }
                    } else if (
                        MediaRecorder.isTypeSupported("video/webm;codecs=vp8")
                    ) {
                        opt = { mimeType: "video/webm; codecs=vp8,opus" }
                    } else {
                        opt = { mimeType: "video/webm" }
                    }

                    const mediaRec = new MediaRecorder(stream, opt)
                    setMediaRecorder(mediaRec)

                    //Since we are implementing distributed  processing for audio and video,
                    //The audio and  video socket needs to be enabled to receive the  video data
                    // The server listening to the audio_socket will extract audio stream from the
                    // video data for processing, while the server for video_socket will extract the video
                    // for processing.

                    audiows.current = new WebSocket(
                        apiService.getAudioWebsocketEndpoint(),
                    )

                    connect_audio_processor_service();

                    //activate video websocket 
                    setVideoWs(
                        new WebSocket(
                            apiService.getVideoWebsocketEndpoint(),
                        ),
                    )

                }
            } else {
                setDisplayText("No media devices detected.")
                setCurrentForm("JoinError")
                disconnect(true)
            }
        } catch (ex) {
            console.log(ex)
            setDisplayText("Failed to get user audio source.")
            setCurrentForm("JoinError")
            disconnect(true)
        }
    }

    // Verifies the users connection input and that the user
    // has a microphone accessible to the browser.
    const verifyInputAndAudio = (names, passcode, joinswith, collaborators) => {
        if (names === null) {
            names = "User Device"
        }
        setName(names)
        setJoinwith(joinswith)
        setNumSpeakers(collaborators)
        requestAccessKey(names, passcode, collaborators, joinswith)
    }

    // Requests session access from the server.
    const requestAccessKey = (names, passcode, collaborators, joinwith) => {
        ending.value = false
        setCurrentForm("Connecting")
        const constraint = {}
        if (joinwith === "Video" || joinwith === "Videocartoonify") {
            constraint.audio = true
            constraint.video = {
                facingMode: "user",
                width: 640, //{ min: 640, ideal: 1280, max: 1920 },
                height: 480, //{ min: 480, ideal: 720, max: 1080 }
            }
        } else {
            constraint.audio = true
            constraint.video = false
        }
        sessionService.joinByodSession(names, passcode, collaborators).then(
            (response) => {
                if (response.status === 200) {
                    response.json().then((jsonObj) => {
                        setSession(SessionModel.fromJson(jsonObj["session"]))
                        setSessionDevice(
                            SessionDeviceModel.fromJson(
                                jsonObj["session_device"],
                            ),
                        )
                        setSpeakers(
                            SpeakerModel.fromJsonList(jsonObj["speakers"]),
                        )
                        setKey(jsonObj.key);
                        setConstraintObj(constraint)
                        setPcode(passcode)
                        setJoinwith(joinwith)
                    })
                } else if (response.status === 400 || response.status === 401) {
                    response.json().then((jsonObj) => {
                        setDisplayText(jsonObj["message"])
                        setCurrentForm("JoinError")
                        disconnect(true)
                    })
                }
            },
            (apierror) => {
                setDisplayText("Contact Administrator")
                setCurrentForm("JoinError")
                disconnect(true)
                console.log(
                    "byod-join-component error func : requestAccessKey 1",
                    apierror,
                )
            },
        )
    }

    const closeAlert = () => {
        setShowAlert(false)
    }

    // Connects to audio processor websocket server.
    const connect_audio_processor_service = () => {
        audiows.current.binaryType = "arraybuffer"

        audiows.current.onopen = (e) => {
            console.log("[Connected audio processor service]")
            console.log("speakers ", speakers)
            setAudioConnected(true)
            setReconnectCounter(0)
            setPageTitle(name)
            setReload(true)
            setCurrentForm("")
        };

        audiows.current.onmessage = (e) => {
            const message = JSON.parse(e.data)
            setAuthenticated(true)
            if (message["type"] === "start") {
                closeDialog()
            } else if (message['type'] === 'registeredfingerprintadded') {
                console.log("got a response from audio endpoint....")
                setRegisteredAudioFingerprintAdded(true)

            } else if (message["type"] === "error") {
                disconnect(true)
                setDisplayText(
                    "The connection to the session has been closed by the audio server.",
                )
                console.log("message from the audio server is "+ message["message"])
                setCurrentForm("ClosedSession")
            } else if (message["type"] === "end") {
                disconnect(true)
                setDisplayText("The session has been closed by the owner.")
                setCurrentForm("ClosedSession")
            }
        }

        audiows.current.onclose = (e) => {
            console.log("[Disconnected]", ending.value)
            if (!ending.value) {
                if (reconnectCounter <= 5) {
                    setCurrentForm("Connecting")
                    disconnect()
                    setReconnectCounter(reconnectCounter + 1)
                    console.log("reconnecting ....")
                    setTimeout(handleStream, 2000)
                }
                setDisplayText("Connection to the session has been lost.")
                setCurrentForm("ClosedSession")
                disconnect(true)
            } else {
                console.log("ending ...")
            }
        }
    }

    // Connects to video processor websocket server.
    const connect_video_processor_service = () => {
        videows.binaryType = "blob"

        videows.onopen = (e) => {
            console.log("[Connected to video processor services]")
            setVideoConnected(true)
        }

        videows.onmessage = (e) => {
            if (typeof e.data === 'string') {
                const message = JSON.parse(e.data);
                if (message['type'] === 'start') {
                    setAuthenticated(true);
                    closeDialog();
                } else if (message['type'] === 'attention_data') {

                } else if (message['type'] === 'registeredfingerprintadded') {
                    console.log("got a response from video endpoint....")
                    setRegisteredVideoFingerprintAdded(true)
                } else if (message['type'] === 'error') {
                    disconnect(true);
                    setDisplayText('The connection to the session has been closed by the video server.');
                     console.log("message from the video server is "+ message["message"])
                    setCurrentForm('ClosedSession');
                } else if (message['type'] === 'end') {
                    disconnect(true);
                    setDisplayText('The session has been closed by the owner.');
                    setCurrentForm('ClosedSession');
                }
            } else if (e.data instanceof Blob) {
                const url = URL.createObjectURL(e.data);
                // Add the processed frame to the buffer

                setFrameBuffer(prevBuffer => {
                    const newItems = [...prevBuffer, url]
                    if (newItems.length % 40 === 0) {
                        setFrameBufferLength(newItems.length)
                    }

                    return newItems
                }
                );

                setRenderingStarted(true)
            }
        };

        videows.onclose = e => {
            console.log('[Disconnected]', ending.value);
        };
    }

    // Begin capturing and sending client audio.
    const requestStartAudioProcessing = () => {
        console.log("Starting Audio")
        let message = null
        if (audiows.current === null) {
            return
        }
        if (joinwith === "Audio") {
            message = {
                type: "start",
                key: key,
                start_time: 0.0,
                sample_rate: audioContext.sampleRate,
                encoding: "pcm_f32le",
                channels: 1,
                streamdata: "audio",
                tag: true,
                embeddings_file: sessionDevice.embeddings,
                deviceid: sessionDevice.id,
                sessionid: session.id,
                numSpeakers: numSpeakers,
            }
        } else if (joinwith === "Video" || joinwith === "Videocartoonify") {
            message = {
                type: "start",
                key: key,
                start_time: 0.0,
                sample_rate: 16000,
                encoding: "pcm_f16le",
                video_encoding: "video/mp4",
                channels: 1,
                streamdata: "video",
                tag: true,
                embeddings_file: sessionDevice.embeddings,
                deviceid: sessionDevice.id,
                sessionid: session.id,
                numSpeakers: numSpeakers,
            }
        }
        console.log(joinwith)
        audiows.current.send(JSON.stringify(message))
    }

    // Begin capturing and sending client video.
    const requestStartVideoProcessing = () => {
        let message = null
        console.log('starting video processing')
        if (videows === null) {
            return
        }
        if (joinwith === "Video") {
            message = {
                type: "start",
                key: key,
                start_time: 0.0,
                sample_rate: 16000,
                encoding: "pcm_f16le",
                video_encoding: "video/mp4",
                channels: 2,
                streamdata: "video",
                embeddings_file: sessionDevice.embeddings,
                deviceid: sessionDevice.id,
                Video:true,
                sessionid: session.id,
                numSpeakers: numSpeakers,
            }
        } else if (joinwith === "Videocartoonify") {
            message = {
                type: "start",
                key: key,
                start_time: 0.0,
                sample_rate: 16000,
                encoding: "pcm_f16le",
                video_encoding: "video/mp4",
                channels: 2,
                streamdata: "video",
                embeddings_file: sessionDevice.embeddings,
                deviceid: sessionDevice.id,
                sessionid: session.id,
                Video_cartoonify: true,
                numSpeakers: numSpeakers,
            }
        }
        console.log(joinwith)
        videows.send(JSON.stringify(message))
    }

    const requestHelp = () => {
        sessionDevice.button_pressed = !sessionDevice.button_pressed
        sessionService.setDeviceButton(
            sessionDevice.id,
            sessionDevice.button_pressed,
            key,
        )
    }

    const navigateToLogin = (confirmed = false) => {
        if (!confirmed && (audioconnected || videoconnected)) {
            setCurrentForm("NavGuard")
        } else {
            disconnect(true)
            setCurrentForm("")
            return navigate("/")
        }
    }

    const getSpeakerAliasFromID = (selectedSpkrId)=>{
        if (selectedSpkrId !== -1){
             const speaker = speakers.filter((s) => s.id === selectedSpkrId )
             if(speaker.length !== 0){
                return speaker[0].alias
             }
        }else{
            return -1
        }
    }

    const fetchSpeakerMetrics = async (transcript) => {
        try {
            const response = await sessionService.getTranscriptSpeakerMetrics(
                transcript.id,
            )
            if (response.status === 200) {
                const jsonObj = await response.json()
                return { ...transcript, speaker_metrics: jsonObj }
            } else if (response.status === 400 || response.status === 401) {
                console.log(response, "no speaker metric for transcript id")
                return { ...transcript, speaker_metrics: null }
            }
        } catch (error) {
            console.log(
                "byod-join-component error func : fetch Speaker Metrics",
                error,
            )
        }
    }

    const fetchTranscript = async (deviceid) => {
        try {
            const response =
                await sessionService.getSessionDeviceTranscriptsForClient(
                    deviceid,
                )

            if (response.status === 200) {
                const jsonObj = await response.json()
                const fetched_transcripts = jsonObj.sort((a, b) =>
                    a.start_time > b.start_time ? 1 : -1,
                )

                const fetch_metrics_promises =
                    fetched_transcripts.map(fetchSpeakerMetrics)
                const fetched_trancript_metrics = await Promise.all(
                    fetch_metrics_promises,
                )

                setTranscripts(fetched_trancript_metrics)
                const sessionLen =
                    Object.keys(session).length > 0 ? session.length : 0
                setStartTime(Math.round(sessionLen * timeRange[0] * 100) / 100)
                setEndTime(Math.round(sessionLen * timeRange[1] * 100) / 100)
            } else if (response.status === 400 || response.status === 401) {
                console.log(response, "no transcript obj")
            }
        } catch (error) {
            console.log(
                "byod-join-component error func : fetch transcript",
                error,
            )
        }
    }

    const fetchVideoMetric = async (deviceid) => {
        try {
            const response =
                await sessionService.getSessionDeviceVideoMetricsForClient(
                    deviceid,
                )

            if (response.status === 200) {
                const jsonObj = await response.json()
                const fetched_video_metrics = jsonObj.sort((a, b) =>
                    a.time_stamp > b.time_stamp ? 1 : -1,
                )

                setVideoMetrics(fetched_video_metrics)
            } else if (response.status === 400 || response.status === 401) {
                console.log(response, "no videometrics obj")
            }
        } catch (error) {
            console.log(
                "byod-join-component error func : fetch video metrics",
                error,
            )
        }
    }

    //function to render the cartoonized image
    const renderFrameFromBuffer = () => {
        console.log('frameBufferLength = ', frameBufferLength, ' cartoonImgBatch = ', cartoonImgBatch)
        if (frameBufferLength > (40 * cartoonImgBatch)) {
            for (var i = (cartoonImgBatch - 1) * 40; i < cartoonImgBatch * 40; i++) {

                setInterval(() => {
                    setCartoonImgUrl(frameBuffer[i]);
                    console.log('i called setcartoonimgurl ', i)
                }, 500)

            }
            setCartoonImgBatch(prevCount => prevCount + 1)

        }

    }

    const ResetTimeRange = (values) => {
        if (session !== null) {
            const sessionLen =
                Object.keys(session).length > 0 ? session.length : 0
            setTimeRange(values)
            const start = Math.round(sessionLen * values[0] * 100) / 100
            const end = Math.round(sessionLen * values[1] * 100) / 100
            setStartTime(start)
            setEndTime(end)
            generateDisplayTranscripts(start, end)
        }
    }

    const generateDisplayTranscripts = (s, e) => {
        setDisplayTranscripts(
            transcripts.filter((t) => t.start_time >= s && t.start_time <= e),
        )
    }

    const generateDisplayVideoMetrics = (s, e) => {
        setDisplayVideoMetrics(
            videoMetrics.filter((v) => v.time_stamp >= s && v.time_stamp <= e),
        )
    }


    const setSpeakerTranscripts = () => {
    if (displayTranscripts.length) {
      setSpkr1Transcripts(
        displayTranscripts.reduce((values, transcript) => {
          
          if (transcript.speaker_id === selectedSpkrId1
          ){
            values.push(transcript);
          }
          return values;
        }, [])
      );
      setSpkr2Transcripts(
        displayTranscripts.reduce((values, transcript) => {
          if (transcript.speaker_id === selectedSpkrId2
          ){
            values.push(transcript);
         }
          return values;
        }, [])
      );
    } else {
      setSpkr1Transcripts([]);
      setSpkr2Transcripts([]);
    }
  };

  const setSpeakerVideoMetrics = () => {
    console.log(selectedSpkrId1,selectedSpkrId2)
    if (displayVideoMetrics.length) {
      let speakerAlias1 = getSpeakerAliasFromID(selectedSpkrId1)
      let speakerAlias2 = getSpeakerAliasFromID(selectedSpkrId2)
      setSpkr1VideoMetrics(
        displayVideoMetrics.reduce((values, videometrics) => {
          if (videometrics.student_username === speakerAlias1
          ){
            values.push(videometrics)
          }
          return values
        }, []),
      )
      setSpkr2VideoMetrics(
        displayVideoMetrics.reduce((values, videometrics) => {
          if (videometrics.student_username === speakerAlias2
          ){
            values.push(videometrics)  
          }
          return values
        }, []),
      )
    } else {
      setSpkr1VideoMetrics([])
      setSpkr2VideoMetrics([])
    }
  }

    const seeAllTranscripts = () => {
        if (Object.keys(currentTranscript) > 0 && sessionDevice !== null) {
            setCurrentForm("gottoselectedtranscript")
        } else if (sessionDevice !== null) {
            setCurrentForm("gototranscript")
        }
    }

    const loading = () => {
        return session === null || transcripts === null
    }

    const onClickedTimeline = (transcript) => {
        setCurrentForm("Transcript")
        setCurrentTranscript(transcript)
    }

    const onClickedKeyword = (transcript) => {
        setCurrentTranscript(transcript)
        setCurrentForm("gottoselectedtranscript")
    }

    const openDialog = (form) => {
        setCurrentForm(form)
    }

    const closeDialog = () => {
        setCurrentForm("")
    }

    const changeTouppercase = (e) => {
        let val = e.target.value.toUpperCase()
        if (val.length <= 4) {
            setWrongInput(false)
        } else {
            setWrongInput(true)
        }
        setPcode(val)
    }

    const togglePreview = () => {
        setCurrentForm("")
        setPreview(!preview)
    }

    const onSessionClosing = (isClosing) => {
        setSessionClosing(isClosing)
    }

    const acquireWakeLock = async () => {
        if (!("wakeLock" in navigator)) {
            console.error(
                "Screen Wake Lock API is not supported by the browser",
            )
            return
        }

        try {
            wakeLock = await navigator.wakeLock.request("screen")
            console.log("Wake lock is activated.")
            wakeLock.addEventListener("release", () => {
                console.log("Wake Lock has been released")
            })
            document.addEventListener("visibilitychange", async () => {
                if (
                    wakeLock !== null &&
                    document.visibilityState === "visible"
                ) {
                    wakeLock = await navigator.wakeLock.request("screen")
                }
            })
        } catch (err) {
            console.log(err)
        }
    }

    const releaseWakeLock = async () => {
        try {
            wakeLock.release().then(() => {
                wakeLock = null
            })
        } catch (err) {
            console.log(`WakeLock release error: ${err}`)
        }
    }

    const initChecklistData = (featuresArr, setFn) => {
        let valueInd = 0
        let showFeats = []
        for (const feature of featuresArr) {
            showFeats.push({ label: feature, value: valueInd, clicked: true })
            valueInd++
        }
        setFn(showFeats)
    }

    const viewComparison = () => {
        setDetails("Comparison")
    }

    const viewIndividual = () => {
        setDetails("Individual")
    }

    const viewGroup = () => {
        setDetails("Group")
    }

    const sessionDevBtnPressed =
        sessionDevice !== null ? sessionDevice.button_pressed : null

    const loadSpeakerMetrics = (speakerId, speakrAlias) => {
    setSelectedSpkrId1(speakerId)
    setSelectedSpkralias(speakrAlias)
    setPageTitle(speakrAlias)
    setDetails("Individual");
  }

    return (
        <ByodJoinPage
            connected={audioconnected}
            authenticated={authenticated}
            GLOW_COLOR={GLOW_COLOR}
            POD_COLOR={POD_COLOR}
            button_pressed={sessionDevBtnPressed}
            verifyInputAndAudio={verifyInputAndAudio}
            closeDialog={closeDialog}
            currentForm={currentForm}
            displayText={displayText}
            navigate={navigate}
            navigateToLogin={navigateToLogin}
            pageTitle={pageTitle}
            requestHelp={requestHelp}
            pcode={pcode}
            setPcode={setPcode}
            wrongInput={wrongInput}
            changeTouppercase={changeTouppercase}
            joinwith={joinwith}
            preview={preview}
            previewLabel={previewLabel}
            togglePreview={togglePreview}
            disconnect={disconnect}
            sessionDevice={sessionDevice}
            setRange={ResetTimeRange}
            onClickedTimeline={onClickedTimeline}
            onClickedKeyword={onClickedKeyword}
            session={session}
            displayTranscripts={displayTranscripts}
            displayVideoMetrics={displayVideoMetrics}
            startTime={startTime}
            endTime={endTime}
            transcripts={transcripts}
            loading={loading}
            onSessionClosing={onSessionClosing}
            currentTranscript={currentTranscript}
            seeAllTranscripts={seeAllTranscripts}
            openDialog={openDialog}
            setCurrentForm={setCurrentForm}
            showBoxes={showBoxes}
            showFeatures={showFeatures}
            videoApiEndpoint={apiService.getVideoServerEndpoint()}
            setSpeakersValidated={setSpeakersValidated}
            speakersValidated={speakersValidated}
            speakers={speakers}
            authKey={key}
            openForms={openForms}
            closeForm={closeForm}
            selectedSpkrId1={selectedSpkrId1}
            setSelectedSpkrId1={setSelectedSpkrId1}
            selectedSpkrId2={selectedSpkrId2}
            setSelectedSpkrId2={setSelectedSpkrId2}
            getSpeakerAliasFromID = {getSpeakerAliasFromID}
            spkr1Transcripts={spkr1Transcripts}
            spkr2Transcripts={spkr2Transcripts}
            selectedSpeaker={selectedSpeaker}
            spkr1VideoMetrics={spkr1VideoMetrics}
            spkr2VideoMetrics={spkr2VideoMetrics}
            setSelectedSpeaker={setSelectedSpeaker}
            saveAudioFingerprint={saveAudioFingerprint}
            addSpeakerFingerprint={addSpeakerFingerprint}
            confirmSpeakers={confirmSpeakers}
            closeAlert={closeAlert}
            changeAliasName={changeAliasName}
            details={details}
            setDetails={setDetails}
            viewIndividual={viewIndividual}
            viewComparison={viewComparison}
            viewGroup={viewGroup}
            cartoonImgUrl={cartoonImgUrl}
            invalidName={invalidName}
            startProcessingSavedSpeakerFingerprint={startProcessingSavedSpeakerFingerprint}
            loadSpeakerMetrics={loadSpeakerMetrics}
            selectedSpkralias={selectedSpkralias}
        />
    )
}

export { JoinPage }
