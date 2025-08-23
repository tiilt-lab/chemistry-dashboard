import { useEffect, useState, useRef } from "react"
import { ProfileCreationPage } from "./html-pages"
import { AuthService } from '../services/auth-service';
import { ApiService } from "../services/api-service"
import { useNavigate, useParams } from "react-router-dom"
import fixWebmDuration from "fix-webm-duration"


function SignupPage() {
    const [pageTitle, setPageTitle] = useState("Create Account")
    const [nextPage, setNextPage] = useState("profile_creation")
    const [studentObject, setStudentObject] = useState(null);
    const [showAlert, setShowAlert] = useState(false)
    const [alertMessage, setAlertMessage] = useState("")
    const [constraintObj, setConstraintObj] = useState(null)
    const [streamReference, setStreamReference] = useState(null)
    const [mediaRecorder, setMediaRecorder] = useState(null)
    const [authenticated, setAuthenticated] = useState(false)
    const [socketProccesorConnected, setSocketProccesorConnected] = useState(false)
    const [videoBlob, setVideoBlob] = useState(null)
    const [currentForm, setCurrentForm] = useState("")
    const [displayText, setDisplayText] = useState("")
    const chunk = useRef([])
    const [isRecordingStopped, setIsRecordingStopped] = useState(false);
    const ws = useRef(null)
    const ws = useRef(null)
    const navigate = useNavigate()

    const apiService = new ApiService()
    const POD_COLOR = "#FF6655"
    const GLOW_COLOR = "#ffc3bd"
    const interval = 10000

    let wakeLock = null

    useEffect(() => {
        if (studentObject != null) {
            setNextPage("video_audio_capture_page")
            const constraint = {}
            constraint.video = {
                facingMode: "user",
                width: 500, //{ min: 640, ideal: 1280, max: 1920 },
                height: 500, //{ min: 480, ideal: 720, max: 1080 }
            }
            setConstraintObj(constraint)
        }
    }, [studentObject])

    useEffect(() => {
        if (socketProccesorConnected) {
            requestStartAudioVideoProcessing()
        }
    }, [socketProccesorConnected])


    useEffect(() => {
        if (authenticated) {
            const videoPlay = () => {
                let video = document.getElementById('video_preview')
                console.log("video tag ", video)
                console.log("streamReference ", streamReference)
                video.srcObject = streamReference
                console.log("video.srcObject ", video.srcObject)
                video.onloadedmetadata = function (ev) {
                    video.play()
                    mediaRecorder.start()
                }

                mediaRecorder.ondataavailable = async function (ev) {
                    if (ev.data.size) {
                        chunk.current.push(ev.data);
                    }

                }

                // When stopped, you can combine the chunks into a single Blob:
                mediaRecorder.onstop = function () {
                    const blob = new Blob(chunk.current, { type: mediaRecorder.mimeType });
                    setVideoBlob(blob)
                    chunk.current = [];
                    video.pause();
                    video.srcObject = null;
                    setIsRecordingStopped(true)
                };
            }



            videoPlay()

        }
    }, [authenticated])

    useEffect(() => {
        if (document.getElementById('video_playback') !== null) {

            setAuthenticated(false)
            setSocketProccesorConnected(false)
            if (wakeLock) {
                releaseWakeLock()
            }
            if (streamReference != null) {
                streamReference.getAudioTracks().forEach((track) => track.stop())
                setStreamReference(null)
            }

            if (mediaRecorder != null) {
                mediaRecorder.stop()
                setMediaRecorder(null)
            }

            
            const url = URL.createObjectURL(videoBlob);
            document.getElementById('video_playback').src = url;
        }
    }, [isRecordingStopped])

    const stopRecording = () => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop(); // <-- this will fire mediaRecorder.onstop
        }
    };

    const saveRecording = () => {
        audiows.current.send(videoBlob)
    };

    const closeResources = ()=>{
        setIsRecordingStopped(false)
        setSocketProccesorConnected(false)
        if (audiows.current != null) {
            audiows.current.close();
            audiows.current = null;
        }
        navigateToLogin();
    }

    const startRecording = async () => {
        try {
            //reset all parameter in case of video recapturing
            await acquireWakeLock()
            setIsRecordingStopped(false)
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

                setStreamReference(stream)

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


                //activate video websocket 
                audiows.current = new WebSocket(apiService.getAudioWebsocketEndpoint())
                connect_audio_websocket_processor_service();

                videows.current = new WebSocket(apiService.getVideoWebsocketEndpoint())
                connect_video_websocket_processor_service();


            } else {
                setShowAlert(true)
                setAlertMessage("No media devices detected.")
            }

        } catch (ex) {
            console.log(ex)
            setShowAlert(true)
            setAlertMessage("Failed to get user audio-visual source.")
        }
    };



    const verifyUserProfileInput = (lastname, firstname, username) => {
        if (lastname === '') {
            setAlertMessage("Please Enter Your Last Name");
            setShowAlert(true);
            document.getElementById("lastname").focus();
        } else if (firstname === '') {
            setAlertMessage("Please Enter Your First Name");
            setShowAlert(true);
            document.getElementById("firstname").focus();
        } else if (username === '') {
            setAlertMessage("Please Enter Your User Id");
            setShowAlert(true);
            document.getElementById("username").focus();
        } else if (username.length < 5 || username.length > 10) {
            setAlertMessage("User name should be atleast 5 characters and not more than 10 characters");
            setShowAlert(true);
            document.getElementById("username").focus();
        } else {
            new AuthService().createStudentProfile(lastname, firstname, username, setStudentObject, setAlertMessage, setShowAlert);
        }
    }


    // Connects to audio processor websocket server.
    const connect_audio_websocket_processor_service = () => {
        audiows.current.binaryType = "blob"

        ws.current.onopen = (e) => {
            console.log("[Connected to webscoket processor services]")
            setSocketProccesorConnected(true)
        }

        audiows.current.onmessage = (e) => {
            if (typeof e.data === 'string') {
                const message = JSON.parse(e.data);
                if (message['type'] === 'saveaudiovideo') {
                    setAuthenticated(true);
                }
                // else if(message['type'] === 'attention_data'){

                // }
                else if (message['type'] === 'error') {
                    stopRecording();
                    setAlertMessage(message['message']);
                    setShowAlert(true);

                }
                else if (message['type'] === 'saved') {
                    setDisplayText("Biometric data captured successfully")
                    setCurrentForm("success")
                }
            } 
        };

        audiows.current.onclose = e => {
            console.log('[Audio Websocket Disconnected]');
        };
    }

    // Connects to video processor websocket server.
    const connect_video_websocket_processor_service = () => {
        audiows.current.binaryType = "blob"

        videows.current.onopen = (e) => {
            console.log("[Connected to webscoket processor services]")
            setSocketProccesorConnected(true)
        }

        videows.current.onmessage = (e) => {
            if (typeof e.data === 'string') {
                const message = JSON.parse(e.data);
                if (message['type'] === 'saveaudiovideo') {
                    setAuthenticated(true);
                }
                // else if(message['type'] === 'attention_data'){

                // }
                else if (message['type'] === 'error') {
                    stopRecording();
                    setAlertMessage(message['message']);
                    setShowAlert(true);

                }
                else if (message['type'] === 'saved') {
                    setDisplayText("Biometric data captured successfully")
                    setCurrentForm("success")
                }
            } 
        };

        videows.current.onclose = e => {
            console.log('[Disconnected]');
        };
    }


    // Begin capturing and sending student video sample.
    const requestStartAudioVideoProcessing = async () => {
        let message = null
        console.log('starting audio and video processing')
        if (audiows.current === null) {
            return
        }

        if (videows.current === null) {
            return
        }
        message = {
            type: "save-audio-video-fingerprinting",
            stage: "start",
            id: studentObject.id,
            alias: studentObject.username,
            start_time: 0.0,
            sample_rate: 16000,
            encoding: "pcm_f16le",
            video_encoding: "video/mp4",
            channels: 2,
            streamdata: "audio-video-fingerprint"
        }
        // await waitForOpen(ws.current);
        audiows.current.send(JSON.stringify(message))
    }



    const closeAlert = () => {
        setShowAlert(false)
    }

    const closeDialog = () => {
        setCurrentForm("")
    }


    const navigateToLogin = (confirmed = false) => {
        return navigate("/")
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




    return (
        <ProfileCreationPage
            nextPage={nextPage}
            closeAlert={closeAlert}
            showAlert={showAlert}
            alertMessage={alertMessage}
            verifyUserProfileInput={verifyUserProfileInput}
            GLOW_COLOR={GLOW_COLOR}
            POD_COLOR={POD_COLOR}
            navigateToLogin={navigateToLogin}
            pageTitle={pageTitle}
            startRecording={startRecording}
            stopRecording={stopRecording}
            isRecordingStopped={isRecordingStopped}
            saveRecording={saveRecording}
            closeResources={closeResources}
            closeDialog={closeDialog}
            displayText={displayText}
            currentForm={currentForm}
        
        />
    )
}

export { SignupPage }
