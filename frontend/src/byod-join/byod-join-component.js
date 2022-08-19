import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { SessionService } from '../services/session-service';
import { ByodJoinPage } from './html-pages';
import { SessionModel } from '../models/session';
import { SessionDeviceModel } from '../models/session-device';
import { ApiService } from '../services/api-service';




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
    const [ending, setEnding] = useState(false);
    const [reconnectCounter, setReconnectCounter] = useState(0);

    // Session data
    const [sessionDevice, setSessionDevice] = useState(null);
    const [session, setSession] = useState(null);
    const [key, setKey] = useState(null);

    const [sessionService, setSessionService] = useState(new SessionService())
    const [apiService, setApiService] = useState(new ApiService())



    const [currentForm, setCurrentForm] = useState("");
    const [displayText, setDisplayText] = useState("");
    const [reload, setReload] = useState(false)
    const [pageTitle, setPageTitle] = useState('Join Discussion');

    const [name, setName] = useState("");
    const [pcode, setPcode] = useState("");
    const [joinwith, setJoinwith] = useState("");
    const [chunk, setChunk] = useState([])
    const [isStop, setIsStop] = useState()
    const [recordedvideo, setRecordedVideo] = useState(null)
    const navigate = useNavigate();

    const POD_COLOR = '#FF6655';
    const GLOW_COLOR = '#ffc3bd';

    useEffect(() => {
        if (source !== null && audioContext !== null && name != "" && pcode != "") {

            requestAccessKey(name, pcode);
        }

    }, [source, audioContext, name, pcode])

    useEffect(() => {
        console.log("ws: ", ws);
        if (ws != null) {
            connect();
        }

    }, [ws])

    useEffect(() => {
        if (mediaRecorder !== null && joinwith === 'Video' && !isStop) {
            requestAccessKey(name, pcode);
        }

    }, [reconnectCounter, mediaRecorder, joinwith, isStop])

    useEffect(() => {
        console.log("ws before requestStart: ", ws);
        console.log("context before requestStart: ", audioContext);
        requestStart();
        // if (connected && joinwith === 'Audio')
        //     requestStart();
        // else if (connected && joinwith === 'Video') {
        //     videoPlay();
        // }

    }, [connected])

    useEffect(() => {
        const loadWorklet = async () => {
           
            await audioContext.audioWorklet.addModule('audio-sender-processor.js');
            const workletProcessor = new AudioWorkletNode(audioContext, 'audio-sender-processor');
            workletProcessor.port.onmessage = data => {
                console.log("sending data: ", data.data)
                console.log("sending data buffer: ", data.data.buffer)
                ws.send(data.data.buffer);
            }
            source.connect(workletProcessor).connect(audioContext.destination);
            setAudioSenderProcessor(workletProcessor);
        }

        const videoPlay =  () => {
            let video = document.querySelector('video')
            video.srcObject = streamReference
            video.onloadedmetadata = function (ev) {
                //show in the video element what is being captured by the webcam
                video.play();
                mediaRecorder.start(1000); 
                console.log(mediaRecorder.state);
            };
            
            mediaRecorder.ondataavailable = async function (ev) {
                console.log(ev.data, "video data")
                const bufferdata = await ev.data.arrayBuffer()
                ws.send(bufferdata);
                chunk.push(ev.data);
            }
            mediaRecorder.onstop = async (ev) => {
                console.log(chunk.length, 'video chunks')
                let blob = new Blob(chunk, { 'type': 'video/mp4;' });
                console.log(blob, "blob data")
                const bufferdata = await blob.arrayBuffer()
                console.log(bufferdata, "arrayBuffer data")
                setIsStop(true)
                setRecordedVideo(window.URL.createObjectURL(blob))
            }
    
        }
        if (authenticated && joinwith === 'Audio')
            loadWorklet().catch(console.error);
        else if (authenticated && joinwith === 'Video')
            videoPlay()    

    }, [authenticated])

    useEffect(() => {
        if (isStop) {
            setChunk([])
        }
    }, [isStop])

    // Disconnects from websocket server and audio stream.
    const disconnect = (permanent = false) => {
        if (permanent) {
            setEnding(true);
            setPageTitle('Join Session');
            setName("")
            setPcode("")
        }

        setConnected(false);
        setAuthenticated(false);

        if (source != null) {
            source.disconnect();
            setSource(null);
        }
        if (audioContext != null) {
            audioContext.close();
            setAudioContext(null);
        }
        if (audioSenderProcessor != null) {
            audioSenderProcessor.disconnect();
            setAudioSenderProcessor(null);
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
    // ngOnDestroy() {
    //   this.disconnect(true);
    // }

    // Verifies the users connection input and that the user
    // has a microphone accessible to the browser.
    const verifyInputAndAudio = (names, passcode, joinswith) => {
        if (names === null || name.length === 0) {
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
                width: 640, //{ min: 640, ideal: 1280, max: 1920 },
                height: 480//{ min: 480, ideal: 720, max: 1080 }
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
                            console.log(device.kind.toUpperCase(), device.label);
                            //, device.deviceId
                        })
                    })
                    .catch(err => {
                        console.log(err.name, err.message);
                    })
            }

            if (navigator.mediaDevices != null) {
                navigator.mediaDevices.getUserMedia(constraintObj)
                    .then(function (stream) {
                        setStreamReference(stream);
                        if (joinswith === 'Audio') {
                            const context = new AudioContext();
                            setSource(context.createMediaStreamSource(stream));
                            setAudioContext(context);
                        } else if (joinswith === 'Video') {
                            const mediaRec = new MediaRecorder(stream);
                            setMediaRecorder(mediaRec)
                            setIsStop(false)
                        }

                    },
                        error => {
                            setDisplayText('Failed to get user audio source.');
                            setCurrentForm("JoinError");
                            disconnect(true);
                        });
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
        setEnding(false);
        setCurrentForm('Connecting');
        sessionService.joinByodSession(name, pcode).then(
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
            setPageTitle(sessionDevice.name);
            setReload(true)
            setCurrentForm("");
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
            console.log('[Disconnected]');
            if (!ending) {
                if (reconnectCounter <= 5) {
                    setCurrentForm('Connecting');
                    disconnect();
                    console.log('reconnecting ....')
                    setTimeout(() => {
                        verifyInputAndAudio(name, pcode, joinwith)
                        setReconnectCounter(reconnectCounter + 1);
                    }, 1000);
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
                'streamdata' : 'audio'
            };
        } else if (joinwith === 'Video') {
            message = {
                'type': 'start',
                'key': key,
                'start_time': 0.0,
                'sample_rate': 44100,
                'encoding': 'pcm_f32le',
                'video_encoding': 'video/mp4',
                'channels': 1,
                'streamdata' : 'video'
            };
        }
        console.log("requesting start", message)
        ws.send(JSON.stringify(message));

    }

    const videoPlay = () => {
        let video = document.querySelector('video')
        video.srcObject = streamReference
        video.onloadedmetadata = function (ev) {
            //show in the video element what is being captured by the webcam
            video.play();
        };
        mediaRecorder.start(1000); 
        console.log(mediaRecorder.state);
        mediaRecorder.ondataavailable = function (ev) {
            console.log(ev.data, "video data")
            ev.data.arrayBuffer().then(data=>{
                console.log(data, "arrayBuffer data")
            })
            
            chunk.push(ev.data);
        }
        mediaRecorder.onstop = (ev) => {
            console.log(chunk.length, 'video chunks')
            let blob = new Blob(chunk, { 'type': 'video/mp4;' });
            console.log(blob, "blob data")
            setIsStop(true)
            setRecordedVideo(window.URL.createObjectURL(blob))
        }

    }
    const requestHelp = () => {
        sessionDevice.button_pressed = !sessionDevice.button_pressed;
        sessionService.setDeviceButton(sessionDevice.id, sessionDevice.button_pressed, key);
    }

    const navigateToLogin = (confirmed = false) => {
        if (!confirmed && connected) {
            setCurrentForm('NavGuard');
        } else {
            return navigate('/login');
        }
    }

    const closeDialog = () => {
        setCurrentForm("");
    }

    const changeTouppercase = (e) => {
        setPcode(e.target.value.toUpperCase())
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
            changeTouppercase={changeTouppercase}
            joinwith={joinwith}
            mediaRecorder={mediaRecorder}
            isStop={isStop}
            recordedvideo = {recordedvideo}

        />
    )
}


export { JoinPage }
