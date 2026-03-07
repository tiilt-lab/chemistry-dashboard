import { useReducer, useEffect, useState, useRef, useCallback } from "react"
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
    const sessionService = new SessionService()
    const apiService = new ApiService()
    // Audio connection data
    const audiows = useRef(null)
    const videows = useRef(null)
    const streamReference = useRef(null)
    const audioContext = useRef(null)
    const mediaRecorder = useRef(null)
    const source = useRef(null)
    const ending = useRef(false)
    const reconnectCounter = useRef(0)
    const frameBuffer = useRef([]); // Buffer for cartoonized frames
    const playbackIntervalRef = useRef(null);
    const isPlayingBatchRef = useRef(false);
    const [key, setKey] = useState(null)
    const [transcripts, setTranscripts] = useState([])
    const [videoMetrics, setVideoMetrics] = useState([])

    const initialState = {
        audioSocketOpen: false,
        videoSocketOpen: false,
        audioReady: false,
        videoReady: false,
        speakersValidated: false,
        streaming: false,
    };

    function reducer(state, action) {
        switch (action.type) {
            case "AUDIO_SOCKET_OPEN":
                return { ...state, audioSocketOpen: action.payload };
            case "VIDEO_SOCKET_OPEN":
                return { ...state, videoSocketOpen: action.payload };
            case "AUDIO_READY":
                return { ...state, audioReady: action.payload };
            case "VIDEO_READY":
                return { ...state, videoReady: action.payload };
            case "SPEAKERS_VALIDATED":
                return { ...state, speakersValidated: action.payload };
            case "START_STREAMING":
                return { ...state, streaming: true };
            case "STOP_STREAMING":
                return { ...state, streaming: false };
            default:
                return state;
        }
    }
    const [state, dispatch] = useReducer(reducer, initialState);







    const [frameBufferLength, setFrameBufferLength] = useState(0);
    const [cartoonImgUrl, setCartoonImgUrl] = useState("");
    const [cartoonImgBatch, setCartoonImgBatch] = useState(1);

    // Session data
    const [sessionDevice, setSessionDevice] = useState(null)
    const [session, setSession] = useState(null)
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
    const [prevSessionId, setPrevSessionId] = useState(-1)

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

    const [selectedSpeaker, setSelectedSpeaker] = useState(null)
    const [currBlob, setCurrBlob] = useState(null)
    const [invalidName, setInvalidName] = useState(false)
    const [constraintObj, setConstraintObj] = useState(null)
    const [mimetype, setMimeType] = useState(null)
    const [mimeExtension, setMimeExtension] = useState(null);
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
        if (frameBufferLength > 0) {
            console.log('inside renderframe buffer useeffect ', frameBufferLength)
            renderFrameFromBuffer()
        }
    }, [frameBufferLength])

    useEffect(() => {
        if (constraintObj !== null && mimetype !== null && pcode !== "" && joinwith !== "") handleStream()
    }, [constraintObj, pcode, joinwith, mimetype])



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
        if (session !== null && state.speakersValidated) {
            const sessionLen =
                Object.keys(session).length > 0 ? session.length : 0
            const sTime = Math.round(sessionLen * timeRange[0] * 100) / 100
            const eTime = Math.round(sessionLen * timeRange[1] * 100) / 100
            setStartTime(sTime)
            setEndTime(eTime)
            generateDisplayTranscripts(sTime, eTime)
            generateDisplayVideoMetrics(sTime, eTime)
        }
    }, [transcripts, videoMetrics, startTime, endTime, session, state.speakersValidated, timeRange])

    useEffect(() => {
        if (displayTranscripts) {
            setSpeakerTranscripts()
        }
        if (displayVideoMetrics) {
            setSpeakerVideoMetrics()
        }
    }, [displayTranscripts, displayVideoMetrics, selectedSpkrId1, selectedSpkrId2, details])

    //Use effect to start audio and video processing
    useEffect(() => {
        if (joinwith == "Audio" && state.audioSocketOpen) {
            requestStartAudioProcessing()
        }
        if ((joinwith === "Video" || joinwith === "Videocartoonify") && state.audioSocketOpen && state.videoSocketOpen) {
            requestStartAudioProcessing()
            requestStartVideoProcessing()
        }
    }, [joinwith, state.audioSocketOpen, state.videoSocketOpen])

    //Use effect to start the camera and microphone for video and audio capturing
    useEffect(() => {
        if (state.audioReady || state.videoReady) {
            const loadWorklet = async () => {
                await audioContext.current.audioWorklet.addModule(
                    "audio-sender-processor.js",
                )
                const workletProcessor = new AudioWorkletNode(
                    audioContext.current,
                    "audio-sender-processor",
                )
                workletProcessor.port.onmessage = (data) => {
                    audiows.current.send(data.data.buffer)
                }
                source.current.connect(workletProcessor).connect(audioContext.current.destination)
            }

            const videoPlay = () => {
                let video = document.querySelector("video")
                video.srcObject = streamReference.current
                video.onloadedmetadata = function (ev) {
                    video.play()
                    mediaRecorder.current.start(interval)
                }

                mediaRecorder.current.ondataavailable = async function (ev) {

                    const bufferdata = await ev.data.arrayBuffer()

                    if (ev.data && ev.data.size !== 0) {
                        if (ev.data.type.startsWith('video/webm')) {
                            fixWebmDuration(
                                ev.data,
                                interval * 6 * 60 * 24,
                                (fixedblob) => {
                                    videows.current.send(fixedblob)
                                },
                            )
                        } else if (ev.data.type.startsWith('video/mp4')) {
                            console.log("inside mp4 send")
                            const repairedMp4Data = await fixMp4DurationWithMp4Box(ev.data)
                            videows.current.send(repairedMp4Data)
                        }

                    }

                }
            }

            if (state.audioReady && joinwith === "Audio") {
                loadWorklet().catch(console.error)
            } else if (state.audioReady && state.videoReady && state.speakersValidated &&
                (joinwith === "Video" || joinwith === "Videocartoonify")
            ) {
                loadWorklet().catch(console.error)
                videoPlay()
            }
        }
    }, [state.audioReady, state.videoReady, state.speakersValidated])

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
        if (joinwith === "Video" || joinwith === "Videocartoonify") {
            if (registeredAudioFingerprintAdded && registeredVideoFingerprintAdded) {
                proceed = true
            }
        } else {
            if (registeredAudioFingerprintAdded) {
                proceed = true
            }
        }
        if (proceed) {

            const updatedSpeakers = speakers.map((s) =>
                s.id === selectedSpeaker.id ? { ...s, fingerprinted: true } : s,)
            setSpeakers(updatedSpeakers)
            setSelectedSpeaker(null)
            setCurrentForm("")
            // console.log("register fingerprint for " + registeredStudentData.username + " Added")
            setRegisteredStudentData(null)
            setRegisteredUserAliasChanged(false)
            setRegisteredAudioFingerprintAdded(false)
            setRegisteredVideoFingerprintAdded(false)
            closeDialog()
        }
    }, [registeredAudioFingerprintAdded, registeredVideoFingerprintAdded])


    //The is usefull to keep the connection alive while th users are adding their finger prints.
    //This will stop sending heartbeats once the fingerprints are added
    useEffect(() => {
        let Intervalid = 0

        if (joinwith === "Audio") {
            if (state.audioSocketOpen && state.audioReady) {
                if (audiows.current === null || audiows.current.readyState !== WebSocket.OPEN) return;
                setCurrentForm("")
                const send = () => {
                    if (audiows.current.readyState === WebSocket.OPEN) {
                        audiows.current.send(JSON.stringify({ type: "heartbeat", key: key }));

                    } else {
                        console.log("clearing interval heartbeat inside audio");
                        clearInterval(Intervalid);
                    }
                };

                // fire once immediately, then on interval
                send();
                Intervalid = setInterval(send, 20000);


            }

        } else if (joinwith === "Video" || joinwith === "Videocartoonify") {
            if (state.audioSocketOpen && state.videoSocketOpen && state.audioReady && state.videoReady) {
                if (audiows.current === null || audiows.current.readyState !== WebSocket.OPEN || videows.current === null || videows.current.readyState !== WebSocket.OPEN) {
                    // console.log("returning from heartbeat setup");
                    return;
                }
                setCurrentForm("")
                const send = () => {
                    if (audiows.current.readyState === WebSocket.OPEN && videows.current.readyState === WebSocket.OPEN) {
                        console.log("returning from heartbeat setup");
                        audiows.current.send(JSON.stringify({ type: "heartbeat", key: key }));
                        videows.current.send(JSON.stringify({ type: "heartbeat", key: key }));

                    } else {
                        console.log("clearing interval heartbeat inside video");
                        clearInterval(Intervalid);
                    }
                };
                // fire once immediately, then on interval
                send();
                Intervalid = setInterval(send, 20000);

            }
        }

        return () => {
            console.log("clearing interval heartbeat inside return");
            clearInterval(Intervalid);
        };
        // }
    }, [audiows, videows, state.audioSocketOpen, state.videoSocketOpen, state.audioReady, state.videoReady]); //speakersValidated



    const fixMp4DurationWithMp4Box = async (blob) => {

        const isMp4 = blob.type?.startsWith("video/mp4");
        if (!isMp4) return blob; // WebM/others pass-through

        // if (!MP4Box) console.log("MP4Box not loaded yet");

        const ab = await blob.arrayBuffer();
        // MP4Box API expects `fileStart` on each appended buffer.
        ab.fileStart = 0;

        return new Promise((resolve, reject) => {
            try {
                const MP4Box = (window).MP4Box;
                const mp4boxfile = MP4Box.createFile();
                let outBuffer = null;

                mp4boxfile.onError = (e) => reject(e);
                mp4boxfile.onReady = (info) => {
                    const secs = info?.duration && info?.timescale
                        ? info.duration / info.timescale
                        : null;
                    console.log("duration is. .... ", secs)
                    // Export a finalized, non-fragmented MP4 with proper duration.
                    const out = mp4boxfile.exportFile(); // ArrayBuffer
                    outBuffer = out;
                };

                mp4boxfile.appendBuffer(ab);
                mp4boxfile.flush();

                if (!outBuffer) {
                    reject(new Error("MP4Box failed to export file"));
                    return;
                }
                resolve(new Blob([outBuffer], { type: "video/mp4" }));
            } catch (err) {
                reject(err);
            }
        });
    }

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
        if (ending.current)
            return
        if (permanent) {
            setPageTitle("Join Discussion")
            setName("")
            setPcode("")
            ending.current = true
            dispatch({ type: "SPEAKERS_VALIDATED", payload: false })
            setSpeakers(null)
            setPrevSessionId(session.id)
            setSession(null)
            setSessionDevice(null)
            setKey(null)
        }

        if (wakeLock) releaseWakeLock()

        if (source.current != null) {
            source.current.disconnect()
            source.current = null
        }
        if (audioContext.current != null) {
            audioContext.current.close()
            audioContext.current = null
        }
        if (mediaRecorder.current != null) {
            mediaRecorder.current.stop()
            mediaRecorder.current = null
        }

        if (streamReference.current != null) {
            streamReference.current.getAudioTracks().forEach((track) => track.stop())
            streamReference.current = null
        }

        dispatch({ type: "AUDIO_SOCKET_OPEN", payload: false })
        dispatch({ type: "VIDEO_SOCKET_OPEN", payload: false })
        dispatch({ type: "AUDIO_READY", payload: false })
        dispatch({ type: "VIDEO_READY", payload: false })

        if (audiows.current != null) {
            audiows.current.close();
            audiows.current = null;
        }
        if (videows.current != null) {
            videows.current.close()
            videows.current = null
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

            if (joinwith === "Video" || joinwith === "Videocartoonify") {
                videows.current.send(JSON.stringify(message))
            }
            dispatch({ type: "SPEAKERS_VALIDATED", payload: true })
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
        let audiodata = await audioContext.current.decodeAudioData(data)
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

    const addSavedSpeakerFingerprint = () => {

        let message = null
        message = {
            type: "add-saved-fingerprint",
            id: selectedSpeaker.id,
            alias: registeredStudentData.username
        }

        console.log(speakers)

        if (joinwith === "Video" || joinwith === "Videocartoonify") {

            if (videows.current === null || audiows.current === null) {
                return
            }
            audiows.current.send(JSON.stringify(message))
            videows.current.send(JSON.stringify(message))
            setCurrentForm("processing")
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
                const stream = await navigator.mediaDevices.getUserMedia(constraintObj)

                // media.then(function (stream) {
                streamReference.current = stream
                //keep this here for now to enable to capturing of audio finger printing
                const context = new AudioContext({ sampleRate: 16000 })
                source.current = context.createMediaStreamSource(stream)
                audioContext.current = context
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

                    if (mimetype !== "") {
                        const mediaRec = new MediaRecorder(stream, { mimeType: mimetype })
                        mediaRecorder.current = mediaRec

                        //Since we are implementing distributed  processing for audio and video,
                        //The audio and  video socket needs to be enabled to receive the  video data
                        // The server listening to the audio_socket will extract audio stream from the
                        // video data for processing, while the server for video_socket will extract the video
                        // for processing.

                        audiows.current = new WebSocket(apiService.getAudioWebsocketEndpoint(),)
                        connect_audio_processor_service();

                        //activate video websocket 
                        videows.current = new WebSocket(apiService.getVideoWebsocketEndpoint(),)
                        connect_video_processor_service()

                    }


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
    const requestAccessKey = async (names, passcode, collaborators, joinwith) => {
        ending.current = false
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
        const mediaType = await pickMimeType(constraint)
        const mediaExt = (mediaType !== "" && mediaType.indexOf("webm") !== -1) ? "webm" : (mediaType !== "" && mediaType.indexOf("mp4") !== -1) ? "mp4" : ""
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
                        setMimeType(mediaType)
                        setMimeExtension(mediaExt)
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

    const pickMimeType = async (constraintObj) => {
        const stream = await navigator.mediaDevices.getUserMedia(constraintObj)
        const hasAudio = stream.getAudioTracks().length > 0;

        // Try best-to-widest support order.
        const candidates = [
            // WebM (Android/desktop Chrome)
            hasAudio ? "video/webm;codecs=vp9,opus" : "video/webm;codecs=vp9",
            hasAudio ? "video/webm;codecs=vp8,opus" : "video/webm;codecs=vp8",
            "video/webm",

            // MP4 (iOS/iPadOS Safari/WebKit, incl. Chrome on iPad)
            // H.264 (avc1) + AAC (mp4a) are the usual fourccs
            hasAudio ? "video/mp4;codecs=h264,aac" : "video/mp4;codecs=h264",
            hasAudio ? "video/mp4;codecs=avc1.42E01E,mp4a.40.2" : "video/mp4;codecs=avc1.42E01E",
        ];

        for (const mt of candidates) {
            try {
                if (typeof MediaRecorder.isTypeSupported === "function" &&
                    MediaRecorder.isTypeSupported(mt)) {
                    return mt;
                }
            } catch { /* some engines throw on probe; ignore and continue */ }
        }
        return ""; // no explicit mimeType — let the browser pick or we’ll handle failure
    }



    // Connects to audio processor websocket server.
    const connect_audio_processor_service = () => {
        audiows.current.binaryType = "arraybuffer"

        audiows.current.onopen = (e) => {
            console.log("[Connected audio processor service]")
            console.log("speakers ", speakers)
            dispatch({ type: "AUDIO_SOCKET_OPEN", payload: true })
            reconnectCounter.current = 0
            setPageTitle(name)
            setReload(true)

        };

        audiows.current.onmessage = (e) => {
            const message = JSON.parse(e.data)

            if (message["type"] === "start") {
                console.log("audio authenticated ....")
                dispatch({ type: "AUDIO_READY", payload: true })
                closeDialog()
            } else if (message['type'] === 'registeredfingerprintadded') {
                console.log("got a response from audio endpoint....")
                setRegisteredAudioFingerprintAdded(true)

            } else if (message["type"] === "error") {
                disconnect(true)
                setDisplayText(
                    "The connection to the session has been closed by the audio server.",
                )
                console.log("message from the audio server is " + message["message"])
                setCurrentForm("ClosedSession")
            } else if (message["type"] === "end") {
                disconnect(true)
                setDisplayText("The session has been closed by the owner.")
                setCurrentForm("ClosedSession")
            }
        }

        audiows.current.onclose = (e) => {
            console.log("[Disconnected]", ending.current)
            if (!ending.current) {
                if (reconnectCounter <= 5) {
                    setCurrentForm("Connecting")
                    disconnect()
                    reconnectCounter.current = reconnectCounter.current + 1
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
        videows.current.binaryType = "blob"

        videows.current.onopen = (e) => {
            console.log("[Connected to video processor services]")
            dispatch({ type: "VIDEO_SOCKET_OPEN", payload: true })
        }

        videows.current.onmessage = (e) => {
            if (typeof e.data === 'string') {
                const message = JSON.parse(e.data);
                if (message['type'] === 'start') {
                    console.log("video authenticated ....")
                    dispatch({ type: "VIDEO_READY", payload: true })
                    closeDialog();
                } else if (message['type'] === 'attention_data') {

                } else if (message['type'] === 'registeredfingerprintadded') {
                    console.log("got a response from video endpoint....")
                    setRegisteredVideoFingerprintAdded(true)
                } else if (message['type'] === 'error') {
                    disconnect(true);
                    setDisplayText(message["message"]);
                    console.log("message from the video server is " + message["message"])
                    setCurrentForm('ClosedSession');
                } else if (message['type'] === 'end') {
                    disconnect(true);
                    setDisplayText('The session has been closed by the owner.');
                    setCurrentForm('ClosedSession');
                } else if (message['type'] === 'heartbeat') {
                    console.log("got a a heattbeat response from video endpoint....")
                }
            } else if (e.data instanceof Blob) {
                const url = URL.createObjectURL(e.data);
                // Add the processed frame to the buffer
                frameBuffer.current.push(url);
                if (frameBuffer.current.length % 40 === 0) {
                    setFrameBufferLength(frameBuffer.current.length)
                }
            }
        };

        videows.current.onclose = e => {
            console.log('[Disconnected]', ending.current);
        };
    }

    // Begin capturing and sending client audio.
    const requestStartAudioProcessing = () => {
        console.log("Starting Audio Processing")
        let message = null
        if (audiows.current === null) {
            return
        }
        message = {
            type: "start",
            key: key,
            start_time: 0.0,
            sample_rate: audioContext.current.sampleRate,
            encoding: "pcm_f32le",
            channels: 1,
            streamdata: "audio",
            tag: true,
            embeddings_file: sessionDevice.embeddings,
            deviceid: sessionDevice.id,
            sessionid: session.id,
            numSpeakers: numSpeakers,
        }
        audiows.current.send(JSON.stringify(message))
    }

    // Begin capturing and sending client video.
    const requestStartVideoProcessing = () => {
        let message = null
        console.log('starting video processing')
        if (videows.current === null) {
            return
        }
        if (joinwith === "Video") {
            message = {
                type: "start",
                key: key,
                start_time: 0.0,
                sample_rate: 16000,
                encoding: "pcm_f16le",
                video_encoding: "video/webm",
                channels: 2,
                streamdata: "video",
                mimeextension: mimeExtension,
                embeddings_file: sessionDevice.embeddings,
                deviceid: sessionDevice.id,
                Video: true,
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
                video_encoding: "video/webm",
                channels: 2,
                streamdata: "video",
                mimeextension: mimeExtension,
                embeddings_file: sessionDevice.embeddings,
                deviceid: sessionDevice.id,
                sessionid: session.id,
                Video_cartoonify: true,
                numSpeakers: numSpeakers,
            }
        }
        videows.current.send(JSON.stringify(message))
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
        if (!confirmed && (state.audioSocketOpen || state.videoSocketOpen)) {
            setCurrentForm("NavGuard")
        } else {
            disconnect(true)
            setCurrentForm("")
            return navigate("/")
        }
    }

    const getSpeakerAliasFromID = (selectedSpkrId) => {
        if (selectedSpkrId !== -1) {
            const speaker = speakers.filter((s) => s.id === selectedSpkrId)
            if (speaker.length !== 0) {
                return speaker[0].alias
            }
        } else {
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


    const renderFrameFromBuffer = useCallback(() => {
        if (isPlayingBatchRef.current) return;
        if (frameBufferLength - (40 * (cartoonImgBatch - 1)) < 40) return

        const startIndex = (cartoonImgBatch - 1) * 40;
        const endIndex = cartoonImgBatch * 40;

        if (frameBufferLength < endIndex) return;
        console.log("I am here 4")

        isPlayingBatchRef.current = true;

        let currentIndex = startIndex;

        playbackIntervalRef.current = setInterval(() => {
            const frame = frameBuffer.current[currentIndex];
            if (frame) {
                setCartoonImgUrl(frame);
            }

            currentIndex += 1;

            if (currentIndex >= endIndex) {
                if (playbackIntervalRef.current) {
                    clearInterval(playbackIntervalRef.current);
                    playbackIntervalRef.current = null;
                }

                isPlayingBatchRef.current = false;
                setCartoonImgBatch((prev) => prev + 1);
            }
        }, 33);
    }, [cartoonImgBatch,frameBufferLength]);

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
                    ) {
                        values.push(transcript);
                    }
                    return values;
                }, [])
            );
            setSpkr2Transcripts(
                displayTranscripts.reduce((values, transcript) => {
                    if (transcript.speaker_id === selectedSpkrId2
                    ) {
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
        if (displayVideoMetrics.length) {
            let speakerAlias1 = getSpeakerAliasFromID(selectedSpkrId1)
            let speakerAlias2 = getSpeakerAliasFromID(selectedSpkrId2)
            setSpkr1VideoMetrics(
                displayVideoMetrics.reduce((values, videometrics) => {
                    if (videometrics.student_username === speakerAlias1
                    ) {
                        values.push(videometrics)
                    }
                    return values
                }, []),
            )
            setSpkr2VideoMetrics(
                displayVideoMetrics.reduce((values, videometrics) => {
                    if (videometrics.student_username === speakerAlias2
                    ) {
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
        if (currentForm === "ClosedSession")
            setPrevSessionId(-1)
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
            state={state}
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
            speakers={speakers}
            authKey={key}
            openForms={openForms}
            closeForm={closeForm}
            selectedSpkrId1={selectedSpkrId1}
            setSelectedSpkrId1={setSelectedSpkrId1}
            selectedSpkrId2={selectedSpkrId2}
            setSelectedSpkrId2={setSelectedSpkrId2}
            getSpeakerAliasFromID={getSpeakerAliasFromID}
            spkr1Transcripts={spkr1Transcripts}
            spkr2Transcripts={spkr2Transcripts}
            selectedSpeaker={selectedSpeaker}
            spkr1VideoMetrics={spkr1VideoMetrics}
            spkr2VideoMetrics={spkr2VideoMetrics}
            setSelectedSpeaker={setSelectedSpeaker}
            saveAudioFingerprint={saveAudioFingerprint}
            addSpeakerFingerprint={addSpeakerFingerprint}
            confirmSpeakers={confirmSpeakers}
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
            prevSessionId={prevSessionId}
        />
    )
}

export { JoinPage }
