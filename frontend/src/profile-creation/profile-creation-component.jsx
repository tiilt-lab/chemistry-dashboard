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
    const [audioAuthenticated, setAudioAuthenticated] = useState(false)
    const [videoAuthenticated, setVideoAuthenticated] = useState(false)
    const [audioSocketProccesorConnected, setAudioSocketProccesorConnected] = useState(false)
    const [videoSocketProccesorConnected, setVideoSocketProcesorConnected] = useState(false)
    const [audioSaved, setAudioSaved] = useState(false)
    const [videoSaved, setVideoSaved] = useState(false)
    const [videoBlob, setVideoBlob] = useState(null)
     const [videoData, setVideoData] = useState(null)
    const [currentForm, setCurrentForm] = useState("")
    const [displayText, setDisplayText] = useState("")
    const video_captured = useRef(null)
    const [isRecordingStopped, setIsRecordingStopped] = useState(false);
    const audiows = useRef(null)
    const videows = useRef(null)
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
            constraint.audio = true
            constraint.video = {
                facingMode: "user",
                width: 500, //{ min: 640, ideal: 1280, max: 1920 },
                height: 500, //{ min: 480, ideal: 720, max: 1080 }
            }
            setConstraintObj(constraint)
        }
    }, [studentObject])

    useEffect(() => {
        if (audioSocketProccesorConnected && videoSocketProccesorConnected) {
            requestStartAudioVideoProcessing()
        }
    }, [audioSocketProccesorConnected,videoSocketProccesorConnected])


    useEffect(() => {
        if (audioAuthenticated && videoAuthenticated) {
            const videoPlay = () => {
                let video = document.getElementById('video_preview')
                console.log("video tag ", video)
                console.log("streamReference ", streamReference)
                video.srcObject = streamReference
                console.log("video.srcObject ", video.srcObject)
                video.onloadedmetadata = function (ev) {
                    video.play()
                    mediaRecorder.start(interval)
                }

                mediaRecorder.ondataavailable = async function (ev) {
                    
                    if (ev.data.size && video_captured.current == null) {
                        video_captured.current = ev.data
                        setVideoData(ev.data)
                        stopRecording()
                    }

                }

                // When stopped, you can combine the chunks into a single Blob:
                mediaRecorder.onstop = function () {
                    const blob = new Blob([video_captured.current], { type: mediaRecorder.mimeType });
                    setVideoBlob(blob)
                    video.pause();
                    video.srcObject = null;
                    setIsRecordingStopped(true)
                };
            }



            videoPlay()

        }
    }, [audioAuthenticated,videoAuthenticated])

    useEffect(() => {
        if (document.getElementById('video_playback') !== null) {

            setAudioAuthenticated(false)
            setVideoAuthenticated(false)
            setAudioSocketProccesorConnected(false)
            setVideoSocketProcesorConnected(false)
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

            if(video_captured.current != null){
            video_captured.current = null
            }
            
            const url = URL.createObjectURL(videoBlob);
            document.getElementById('video_playback').src = url;
        }
    }, [isRecordingStopped])

     useEffect(() => {
        if (audioSaved && videoSaved) {
            setDisplayText("Biometric data captured successfully")
            setCurrentForm("success")
        }
    }, [audioSaved,videoSaved])

    
    const stopRecording = () => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop(); // <-- this will fire mediaRecorder.onstop
        }
    };

    const saveRecording = () => {
        fixWebmDuration(
                        videoData,
                        interval,
                        (fixedblob) => {
                            videows.current.send(fixedblob)
                            audiows.current.send(fixedblob)
                            setCurrentForm("processing")
                        },
                    )
        
    };

    const closeResources = ()=>{
        setIsRecordingStopped(false)
        setAudioSocketProccesorConnected(false)
        setVideoSocketProcesorConnected(false)
        if (audiows.current != null) {
            audiows.current.close();
            audiows.current = null;
        }

        if (videows.current != null) {
            videows.current.close();
            videows.current = null;
        }
        if(video_captured.current != null){
            video_captured.current = null
        }

        navigateToLogin();
    }

    const startRecording = async () => {
        try {
            //reset all parameter in case of video recapturing
            await acquireWakeLock()
            setIsRecordingStopped(false)
            if(video_captured.current != null){
            video_captured.current = null
            }
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
                videows.current = new WebSocket(apiService.getVideoWebsocketEndpoint())
                connect_audio_websocket_processor_service();
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

        audiows.current.onopen = (e) => {
            console.log("[Connected to audio webscoket processor services]")
            setAudioSocketProccesorConnected(true)
        }

        audiows.current.onmessage = (e) => {
            if (typeof e.data === 'string') {
                const message = JSON.parse(e.data);
                if (message['type'] === 'saveaudiovideo') {
                    setAudioAuthenticated(true);
                }
                // else if(message['type'] === 'attention_data'){

                // }
                else if (message['type'] === 'error') {
                    stopRecording();
                    setAlertMessage(message['message']);
                    setShowAlert(true);

                }
                else if (message['type'] === 'saved') {
                    setAudioSaved(true)
                }
            } 
        };

        audiows.current.onclose = e => {
            console.log('[audio Disconnected]');
        };
    }

// Connects to video processor websocket server.
    const connect_video_websocket_processor_service = () => {
        videows.current.binaryType = "blob"

        videows.current.onopen = (e) => {
            console.log("[Connected to video webscoket processor services]")
            setVideoSocketProcesorConnected(true)
        }

        videows.current.onmessage = (e) => {
            if (typeof e.data === 'string') {
                const message = JSON.parse(e.data);
                if (message['type'] === 'saveaudiovideo') {
                    setVideoAuthenticated(true);
                }
                // else if(message['type'] === 'attention_data'){

                // }
                else if (message['type'] === 'error') {
                    stopRecording();
                    setAlertMessage(message['message']);
                    setShowAlert(true);

                }
                else if (message['type'] === 'saved') {
                     setVideoSaved(true)
                }
            } 
        };

        videows.current.onclose = e => {
            console.log('[video Disconnected]');
        };
    }

    // Begin capturing and sending student video sample.
    const requestStartAudioVideoProcessing = async () => {
        let message = null
        console.log('starting video processing')
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
        audiows.current.send(JSON.stringify(message))
        videows.current.send(JSON.stringify(message))
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
