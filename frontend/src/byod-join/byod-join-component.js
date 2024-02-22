import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { SessionService } from '../services/session-service';
import { ByodJoinPage } from './html-pages';
import { SessionModel } from '../models/session';
import { SessionDeviceModel } from '../models/session-device';
import { ApiService } from '../services/api-service';
import fixWebmDuration from "fix-webm-duration"




function JoinPage() {

    // Audio connection data
    const [ws, setWs] = useState(null);
    const [connected, setConnected] = useState(false);
    const [authenticated, setAuthenticated] = useState(false);
    const [streamReference, setStreamReference] = useState(null);
    const [audioContext, setAudioContext] = useState(null);
    const [mediaRecorder, setMediaRecorder] = useState(null);
    const [processor, setProcessor] = useState(null);
    const [audioSenderProcessor, setAudioSenderProcessor] = useState(null);
    const [source, setSource] = useState(null);
    const [ending, setEnding] = useState({ value: false });
    const [reconnectCounter, setReconnectCounter] = useState(0);

    // Session data
    const [sessionDevice, setSessionDevice] = useState(null);
    const [session, setSession] = useState(null);
    const [key, setKey] = useState(null);


    const sessionService = new SessionService()
    const apiService = new ApiService()

    const [transcripts, setTransripts] = useState([]);
    const [startTime, setStartTime] = useState();
    const [endTime, setEndTime] = useState();
    const [displayTranscripts, setDisplayTranscripts] = useState([]);
    const [currentTranscript, setCurrentTranscript] = useState({});
    const [timeRange, setTimeRange] = useState([0, 1]);


    const [currentForm, setCurrentForm] = useState("");
    const [displayText, setDisplayText] = useState("");
    const [reload, setReload] = useState(false)
    const [pageTitle, setPageTitle] = useState('Join Discussion');

    const [name, setName] = useState("");
    const [pcode, setPcode] = useState("");
    const [wrongInput, setWrongInput] = useState(false);
    const [joinwith, setJoinwith] = useState("");
    const [preview, setPreview] = useState(false)
    const [previewLabel, setPreviewLabel] = useState("Turn On Preview")
    const navigate = useNavigate();

    const POD_COLOR = '#FF6655';
    const GLOW_COLOR = '#ffc3bd';
    const interval = 10000

    let wakeLock;

    useEffect(() => {
        if (source !== null && audioContext !== null && name != "" && pcode != "") {
            requestAccessKey(name, pcode);
        }

    }, [source, audioContext, name, pcode])

    useEffect(() => {
        if (ws != null) {
            connect();
        }

    }, [ws])

    useEffect(() => {
        if (mediaRecorder !== null && joinwith === 'Video') {
            requestAccessKey(name, pcode);
        }

    }, [mediaRecorder,reconnectCounter, joinwith])


    useEffect(() => {
        let intervalLoad
        if (session !== null && sessionDevice !== null) {
            fetchTranscript(sessionDevice.id)

            intervalLoad = setInterval(() => {
                fetchTranscript(sessionDevice.id)
            }, 2000)
        }

        return () => {
            clearInterval(intervalLoad)

        }

    }, [session, sessionDevice])


    useEffect(() => {
        if (session !== null) {
            const sessionLen = Object.keys(session).length > 0 ? session.length : 0;
            const sTime = Math.round(sessionLen * timeRange[0] * 100) / 100;
            const eTime = Math.round(sessionLen * timeRange[1] * 100) / 100;
            setStartTime(sTime)
            setEndTime(eTime)
            setDisplayTranscripts(transcripts.filter(t => t.start_time >= sTime && t.start_time <= eTime));
        }
    }, [endTime])


    useEffect(() => {
        if(connected){
            requestStart();
        }
    }, [connected])

    useEffect(() => {
        if(authenticated){
        const loadWorklet = async () => {

            await audioContext.audioWorklet.addModule('audio-sender-processor.js');
            const workletProcessor = new AudioWorkletNode(audioContext, 'audio-sender-processor');
            workletProcessor.port.onmessage = data => {
                ws.send(data.data.buffer);
            }
            source.connect(workletProcessor).connect(audioContext.destination);
            setAudioSenderProcessor(workletProcessor);
        }

        const videoPlay = () => {
            let video = document.querySelector('video')
            video.srcObject = streamReference
            video.onloadedmetadata = function (ev) {
                video.play();
                mediaRecorder.start(interval);
            };

            mediaRecorder.ondataavailable = async function (ev) {
                const bufferdata = await ev.data.arrayBuffer()
                fixWebmDuration(ev.data, interval * 6 * 60 * 24, (fixedblob) => {
                    ws.send(fixedblob);
                })
            }
        }

        if (authenticated && joinwith === 'Audio'){
            loadWorklet().catch(console.error);
        }else if (authenticated && joinwith === 'Video'){
            videoPlay()
        }
    }
    }, [authenticated])

    useEffect(() => {
        if (preview) {
            setPreviewLabel("Turn Off Preview")
        } else {
            setPreviewLabel("Turn On Preview")
        }
    }, [preview])

    // Disconnects from websocket server and audio stream.
    const disconnect = (permanent = false) => {
        console.log('disconnect called',permanent)
        if (permanent) {
            setPageTitle('Join Discussion');
            setName("")
            setPcode("")
            ending.value = true;
        }

        releaseWakeLock();
        setConnected(false);
        setAuthenticated(false);

        if (source != null) {
            source.disconnect();
            setSource(null);
        }
        if (audioContext != null) {
            setAudioSenderProcessor(null);
        }
        if (mediaRecorder != null) {
            mediaRecorder.stop()
            setMediaRecorder(null)
        }

        if (streamReference != null) {
            streamReference.getAudioTracks().forEach(track => track.stop());
            setStreamReference(null);
        }
        if (ws != null) {
            ws.close();
            setWs(null);
        }


    }


    // Verifies the users connection input and that the user
    // has a microphone accessible to the browser.
    const verifyInputAndAudio = async (names, passcode, joinswith) => {
        if (names === null) {
            names = 'User Device';
        }
        setName(names);
        setPcode(passcode);
        setJoinwith(joinswith);
        const constraintObj = {}
        if (joinswith === 'Video') {
            constraintObj.audio = true
            constraintObj.video = {
                facingMode: "user",
                width: 150, //{ min: 640, ideal: 1280, max: 1920 },
                height: 80//{ min: 480, ideal: 720, max: 1080 }
            }
        } else {
            constraintObj.audio = true
            constraintObj.video = false
        }

        try {
            //handle older browsers that might implement getUserMedia in some way
            if (navigator.mediaDevices === undefined) {
                navigator.mediaDevices = {};
                navigator.mediaDevices.getUserMedia = function (constraintObj) {
                    let getUserMedia = navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
                    if (!getUserMedia) {
                        return Promise.reject(new Error('getUserMedia is not implemented in this browser'));
                    }
                    return new Promise(function (resolve, reject) {
                        getUserMedia.call(navigator, constraintObj, resolve, reject);
                    });
                }
            } else {
                navigator.mediaDevices.enumerateDevices()
                    .then(devices => {
                        devices.forEach(device => {
                            //console.log(device.kind.toUpperCase(), device.label);
                            //, device.deviceId
                        })
                    })
                    .catch(err => {
                        console.log(err.name, err.message);
                    })
            }

            if (navigator.mediaDevices != null) {
                const stream = await navigator.mediaDevices.getUserMedia(constraintObj)
                   // media.then(function (stream) {
                        setStreamReference(stream);
                        if (joinswith === 'Audio') {
                            const context = new AudioContext({sampleRate:16000});
                            setSource(context.createMediaStreamSource(stream));
                            setAudioContext(context);
                        } else if (joinswith === 'Video') {
                            var opt;
                            if (MediaRecorder.isTypeSupported('video/webm;codecs=vp9')) {
                                opt = { mimeType: 'video/webm; codecs=vp9,opus' };
                            } else if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8')) {
                                opt = { mimeType: 'video/webm; codecs=vp8,opus' };
                            } else {
                                opt = { mimeType: 'video/webm' };
                            }

                            const mediaRec = new MediaRecorder(stream, opt);
                            setMediaRecorder(mediaRec)
                        }
            } else {
                setDisplayText('No media devices detected.');
                setCurrentForm('JoinError');
                disconnect(true);
            }
        } catch (ex) {
            setDisplayText('Failed to get user audio source.');
            setCurrentForm('JoinError');
            disconnect(true);
        }
    }

    const handleStream =  async () => {

        const constraintObj = {}
        if (joinwith === 'Video') {
            constraintObj.audio = true
            constraintObj.video = {
                facingMode: "user",
                width: 150, //{ min: 640, ideal: 1280, max: 1920 },
                height: 80//{ min: 480, ideal: 720, max: 1080 }
            }
        } else {
            constraintObj.audio = true
            constraintObj.video = false
        }

        try {

            if (navigator.mediaDevices != null) {
                const stream = await navigator.mediaDevices.getUserMedia(constraintObj)
                   // media.then(function (stream) {
                        setStreamReference(stream);
                        if (joinwith === 'Audio') {
                            const context = new AudioContext({sampleRate:16000});
                            setSource(context.createMediaStreamSource(stream));
                            setAudioContext(context);
                        } else if (joinwith === 'Video') {
                            var opt;
                            if (MediaRecorder.isTypeSupported('video/webm;codecs=vp9')) {
                                opt = { mimeType: 'video/webm; codecs=vp9,opus' };
                            } else if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8')) {
                                opt = { mimeType: 'video/webm; codecs=vp8,opus' };
                            } else {
                                opt = { mimeType: 'video/webm' };
                            }

                            const mediaRec = new MediaRecorder(stream, opt);
                            setMediaRecorder(mediaRec)
                        }
                        setWs(new WebSocket(apiService.getWebsocketEndpoint()));
            } else {
                setDisplayText('No media devices detected.');
                setCurrentForm('JoinError');
                disconnect(true);
            }
        } catch (ex) {
            setDisplayText('Failed to get user audio source.');
            setCurrentForm('JoinError');
            disconnect(true);
        }
    }

    // Requests session access from the server.
    const requestAccessKey = (names, passcode) => {
        ending.value = false;
        setCurrentForm('Connecting');
        sessionService.joinByodSession(names, passcode).then(
            (response) => {
                if (response.status === 200) {
                    response.json().then(jsonObj => {
                        setSession(SessionModel.fromJson(jsonObj['session']));
                        setSessionDevice(SessionDeviceModel.fromJson(jsonObj['session_device']));
                        setKey(jsonObj.key);
                        setWs(new WebSocket(apiService.getWebsocketEndpoint()));
                    })

                } else if (response.status === 400 || response.status === 401) {
                    setDisplayText(response.json()['message']);
                    setCurrentForm('JoinError');
                    disconnect(true);
                }
            },
            (apierror) => {
                setDisplayText("Contact Administrator");
                setCurrentForm('JoinError');
                disconnect(true);
                console.log('byod-join-component error func : requestAccessKey 1', apierror)
            }
        )

    }



    // Connects to websocket server.
    const connect = () => {
        ws.binaryType = 'arraybuffer';

        ws.onopen = e => {
            console.log('[Connected]');
            setConnected(true);
            setPageTitle(name);
            setReload(true)
            setCurrentForm("");
            acquireWakeLock();
        };

        ws.onmessage = e => {
            const message = JSON.parse(e.data);
            if (message['type'] === 'start') {
                setAuthenticated(true);
                closeDialog();
            } else if (message['type'] === 'error') {
                disconnect(true);
                setDisplayText('The connection to the session has been closed by the server.');
                setCurrentForm('ClosedSession');
            } else if (message['type'] === 'end') {
                disconnect(true);
                setDisplayText('The session has been closed by the owner.');
                setCurrentForm('ClosedSession');
            }
        };

        ws.onclose = e => {
            console.log('[Disconnected]',ending.value);
            if (!ending.value) {
                if (reconnectCounter <= 5) {
                    setCurrentForm('Connecting');
                    setReconnectCounter(reconnectCounter + 1);
                    disconnect();
                    console.log('reconnecting ....')
                    setTimeout(handleStream, 10000);
                    //  setTimeout(() => {
                    //     console.log('i came in here to reconect..')
                        // verifyInputAndAudio(name, pcode, joinwith)


                    //  }, 1000);
                } else {
                    setDisplayText('Connection to the session has been lost.');
                    setCurrentForm('ClosedSession');
                    disconnect(true);

                }
            } else {
                console.log('ending ...')
            }
        };

    }



    // Begin capturing and sending client audio.
    const requestStart = () => {
        let message = null
        if (ws === null) {
            return;
        }
        if (joinwith === 'Audio') {
            message = {
                'type': 'start',
                'key': key,
                'start_time': 0.0,
                'sample_rate': audioContext.sampleRate,
                'encoding': 'pcm_f32le',
                'channels': 1,
                'streamdata': 'audio',
                'tag': true,
                'embeddingsFile': sessionDevice.embeddings
            };
        } else if (joinwith === 'Video') {
            message = {
                'type': 'start',
                'key': key,
                'start_time': 0.0,
                'sample_rate': 16000,
                'encoding': 'pcm_f16le',
                'video_encoding': 'video/mp4',
                'channels': 2,
                'streamdata': 'video',
                'tag' : false,
                'embeddingsFile': sessionDevice.embeddings
            };
        }
        ws.send(JSON.stringify(message));

    }

    const requestHelp = () => {
        sessionDevice.button_pressed = !sessionDevice.button_pressed;
        sessionService.setDeviceButton(sessionDevice.id, sessionDevice.button_pressed, key);
    }

    const navigateToLogin = (confirmed = false) => {
        if (!confirmed && connected) {
            setCurrentForm('NavGuard');
        } else {
            disconnect(true)
            setCurrentForm("")
            return navigate('/');
        }
    }

    const fetchTranscript = async (deviceid) => {
        try {
            const response = await sessionService.getSessionDeviceTranscriptsForClient(deviceid)

            if (response.status === 200) {
                const jsonObj = await response.json()
                const data = jsonObj.sort((a, b) => (a.start_time > b.start_time) ? 1 : -1)
                setTransripts(data)
                const sessionLen = Object.keys(session).length > 0 ? session.length : 0;
                setStartTime(Math.round(sessionLen * timeRange[0] * 100) / 100)
                setEndTime(Math.round(sessionLen * timeRange[1] * 100) / 100)


            } else if (response.status === 400 || response.status === 401) {
                console.log(response, 'no transcript obj')
            }

        } catch (error) {
            console.log('byod-join-component error func : requestAccessKey 1', error)
        }

    }

    const ResetTimeRange = (values) => {
        if (session !== null) {
            const sessionLen = Object.keys(session).length > 0 ? session.length : 0;
            setTimeRange(values);
            setStartTime(Math.round(sessionLen * values[0] * 100) / 100);
            setEndTime(Math.round(sessionLen * values[1] * 100) / 100);
            generateDispalyTranscripts();
        }
    }

    const generateDispalyTranscripts = () => {
        setDisplayTranscripts(transcripts.filter(t => t.start_time >= startTime && t.start_time <= endTime));
    }

    const seeAllTranscripts = () => {
        if (Object.keys(currentTranscript) > 0  && sessionDevice !== null) {
            setCurrentForm("gottoselectedtranscript");

        } else if (sessionDevice !== null) {
            setCurrentForm("gototranscript");
        }

    }

    const loading = () => {
        return (session === null || transcripts === null);
    }


    const onClickedTimeline = (transcript) => {
        setCurrentForm("Transcript");
        setCurrentTranscript(transcript);
    }

    const onClickedKeyword = (transcript) => {
        setCurrentTranscript(transcript);
        setCurrentForm("gottoselectedtranscript");
    }

    const openDialog = (form) => {
        setCurrentForm(form);
    }

    const closeDialog = () => {
        setCurrentForm("");
    }

    const changeTouppercase = (e) => {
        let val = e.target.value.toUpperCase();
        if (val.length <= 4) {
          setWrongInput(false);
        } else {
          setWrongInput(true);
        }
        setPcode(val);
    }

    const togglePreview = () => {
        setCurrentForm('');
        setPreview(!preview)
    }


    const acquireWakeLock = async () => {
      try {
        wakeLock = await navigator.wakeLock.request('screen');
        console.log('Wake lock is activated.');
        wakeLock.addEventListener("release", () => {
          // the wake lock has been released
          console.log("Wake Lock has been released");
        });
        document.addEventListener("visibilitychange", async () => {
          if (wakeLock !== null && document.visibilityState === "visible") {
            wakeLock = await navigator.wakeLock.request("screen");
          }
        });
      } catch (err) {
        console.log(err);
      }
    }

    const releaseWakeLock = async () => {
      try {
        wakeLock.release();
        console.log('Wake lock has been released.');
      } catch (err) {
        console.log(err);
      }
    }

    const sessionDevBtnPressed = sessionDevice !== null ? sessionDevice.button_pressed : null;

    return (
                    <ByodJoinPage
                        connected={connected}
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
                        startTime={startTime}
                        endTime={endTime}
                        transcripts={transcripts}
                        loading={loading}
                        currentTranscript={currentTranscript}
                        seeAllTranscripts={seeAllTranscripts}
                        openDialog={openDialog}
                        setCurrentForm = {setCurrentForm}

                    />
    )
}


export { JoinPage }
