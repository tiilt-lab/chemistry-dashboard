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
    const [mimetype, setMimeType] = useState(null)
    const [mimeExtension, setMimeExtension] = useState(null);
    const [studentUpdate, setStudentUpdated] = useState(false)
    const [audioDisconnected, setAudioDisconnected] = useState(false)
    const [videoDisconnected, setVideoDisconnected] = useState(false)
    // const [userProfileDetails, setUserProfileDetail] = useState(null)
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
            setCurrentForm("processing")
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
        if (constraintObj !== null) {
            detectMediaSouceType()

        }
    }, [constraintObj])



    useEffect(() => {
        if (mimeExtension !== null && mimetype !== null) {
            if (mimeExtension !== "" && (mimetype.endsWith("opus") || mimetype.endsWith("aac") || mimetype.endsWith("mp4a.40.2"))) {
                //activate video websocket 
                audiows.current = new WebSocket(apiService.getAudioWebsocketEndpoint())
                videows.current = new WebSocket(apiService.getVideoWebsocketEndpoint())
                connect_audio_websocket_processor_service();
                connect_video_websocket_processor_service();
            } else {
                setAlertMessage("No Audio Source detected, please use another device");
                setShowAlert(true);
            }
        }
    }, [mimetype, mimeExtension])

    useEffect(() => {
        if (audioSocketProccesorConnected && videoSocketProccesorConnected) {
            requestStartAudioVideoProcessing()
        }
    }, [audioSocketProccesorConnected, videoSocketProccesorConnected])

    useEffect(() => {
        if (audioAuthenticated && videoAuthenticated) {
            setCurrentForm("")
            setNextPage("video_audio_capture_page")

        } else {
            // setCurrentForm("processing")
        }
    }, [audioAuthenticated, videoAuthenticated])

    useEffect(() => {
        if (streamReference && mediaRecorder) {
            setCurrentForm("")
            const videoPlay = () => {
                let video = document.getElementById('video_preview')
                video.srcObject = streamReference
                video.onloadedmetadata = function (ev) {
                    video.play()
                    mediaRecorder.start(interval)
                }

                mediaRecorder.ondataavailable = async function (ev) {

                    if (ev.data.size && video_captured.current === null) {
                        if (ev.data && ev.data.size !== 0) {
                            video_captured.current = ev.data
                            setVideoData(ev.data)
                            stopRecording()
                        }
                    }

                }

                // When stopped, you can combine the chunks into a single Blob:
                mediaRecorder.onstop = function () {
                    const blob = new Blob([video_captured.current], { type: mimetype });
                    setVideoBlob(blob)
                    video.pause();
                    video.srcObject = null;
                    setIsRecordingStopped(true)
                };
            }



            videoPlay()

        }
    }, [streamReference, mediaRecorder])

    useEffect(() => {
        if (document.getElementById('video_playback') !== null) {

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

    useEffect(() => {
        if (audioSaved && videoSaved) {
            new AuthService().updateStudentProfile(studentObject.id, studentObject.lastname, studentObject.firstname, "yes", setStudentUpdated, setAlertMessage, setShowAlert);
        }
    }, [audioSaved, videoSaved])

    useEffect(() => {
        if (studentUpdate) {
            setDisplayText("Biometric data captured successfully")
            setCurrentForm("success")
        }
    }, [studentUpdate])

    useEffect(() => {
        if (audioDisconnected || videoDisconnected) {
            setAlertMessage("You are Disconnected from the Server, please reload the page");
            setShowAlert(true);
        }
    }, [audioDisconnected, videoDisconnected])

    useEffect(() => {
        if (audioAuthenticated && videoAuthenticated) {
            if (audiows.current === null || audiows.current.readyState !== WebSocket.OPEN || videows.current === null || videows.current.readyState !== WebSocket.OPEN) return;

            const send = () => {
                if (audiows.current.readyState === WebSocket.OPEN && videows.current.readyState === WebSocket.OPEN) {
                    console.log("i am firering heartbeat")
                    audiows.current.send(JSON.stringify({ type: "heartbeat", key:"No key" }));
                    videows.current.send(JSON.stringify({ type: "heartbeat",key:"no key" }));

                } else {
                    clearInterval(id);
                }
            };

            // fire once immediately, then on interval
            send();
            const id = setInterval(send, 20000);

            return () => {
                console.log("i called clear interval...")
                clearInterval(id);
            };
        }
    }, [audiows, videows, audioAuthenticated, videoAuthenticated]);


    const stopRecording = () => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop(); // <-- this will fire mediaRecorder.onstop
        }
    };

    const saveRecording = async (videoBlob, duration) => {
        if (videoBlob) {
            if (mimetype.startsWith('video/webm')) {
                const fixedBlob = await fixWebmDuration(videoBlob, duration*1000);
                console.log("videoBlob- duration ", videoBlob, duration)
                videows.current.send(fixedBlob)
                audiows.current.send(fixedBlob)
                setCurrentForm("processing")
            } else if (mimetype.startsWith('video/mp4')) {

            }

        }
    };

    // const saveRecording = () => {
    //     if (videoData) {
    //         if (mimetype.startsWith('video/webm')) {
    //             fixWebmDuration(
    //                 videoData,
    //                 interval,
    //                 (fixedblob) => {
    //                     videows.current.send(fixedblob)
    //                     audiows.current.send(fixedblob)
    //                     setCurrentForm("processing")
    //                 },
    //             )
    //         } else if (mimetype.startsWith('video/mp4')) {

    //         }

    //     }
    // };





    const resetForRecording = () => {
        if (videoData !== null) {
            setVideoData(null)
        }
        if (video_captured.current != null) {
            video_captured.current = null
        }
        if (isRecordingStopped) {
            setIsRecordingStopped(false)
        }
        if (streamReference != null) {
            streamReference.getAudioTracks().forEach((track) => track.stop())
            setStreamReference(null)
        }

        if (mediaRecorder != null) {
            mediaRecorder.stop()
            setMediaRecorder(null)
        }
    }

    const startRecording = async () => {
        try {
            //reset all parameter in case of video recapturing
            await acquireWakeLock()

            resetForRecording()

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



                if (mimetype !== "") {
                    const mediaRec = new MediaRecorder(stream, { mimeType: mimetype })
                    setStreamReference(stream)
                    setMediaRecorder(mediaRec)
                }



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

    const closeResources = () => {
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
        if (video_captured.current != null) {
            video_captured.current = null
        }

        if (isRecordingStopped) {
            setIsRecordingStopped(false)
        }
        if (streamReference != null) {
            streamReference.getAudioTracks().forEach((track) => track.stop())
            setStreamReference(null)
        }

        if (mediaRecorder != null) {
            stopRecorder(mediaRecorder)
            // mediaRecorder.stop()
            setMediaRecorder(null)
        }
        navigateToLogin();
    }

    function stopRecorder(mediarec) {
        if (!mediarec) return Promise.resolve();
        if (mediarec.state === 'inactive') return Promise.resolve();

        return new Promise (res => {
            const onStop = () => {
                mediarec.removeEventListener('stop', onStop);
                res();
            };
            mediarec.addEventListener('stop', onStop, { once: true });
            try { mediarec.stop(); } catch { res(); }
        });
    }

    const detectMediaSouceType = async () => {
        const mediaType = await pickMimeType(constraintObj)
        const mediaExt = (mediaType !== "" && mediaType.indexOf("webm") !== -1) ? "webm" : (mediaType !== "" && mediaType.indexOf("mp4") !== -1) ? "mp4" : ""
        setMimeType(mediaType)
        setMimeExtension(mediaExt)
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
            // setUserProfileDetail([lastname, firstname, username])
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
            setAudioDisconnected(true)
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
            setVideoDisconnected(true)
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
            video_encoding: "video/webm",
            mimeextension: mimeExtension,
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
        if (studentUpdate) {
            closeResources()
        }
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
