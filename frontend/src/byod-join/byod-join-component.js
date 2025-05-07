import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { SessionService } from '../services/session-service';
import { ByodJoinPage } from './html-pages';
import { SessionModel } from '../models/session';
import { SessionDeviceModel } from '../models/session-device';
import { ApiService } from '../services/api-service';
import fixWebmDuration from "fix-webm-duration"
import { range } from 'underscore';




function JoinPage() {

    // Audio connection data
    const [audiows, setAudioWs] = useState(null);
    const [videows, setVideoWs] = useState(null);
    const [audioconnected, setAudioConnected] = useState(false);
    const [videoconnected, setVideoConnected] = useState(false);
    const [authenticated, setAuthenticated] = useState(false);
    const [streamReference, setStreamReference] = useState(null);
    const [audioContext, setAudioContext] = useState(null);
    const [mediaRecorder, setMediaRecorder] = useState(null);
    const [processor, setProcessor] = useState(null);
    const [audioSenderProcessor, setAudioSenderProcessor] = useState(null);
    const [source, setSource] = useState(null);
    const [ending, setEnding] = useState({ value: false });
    const [reconnectCounter, setReconnectCounter] = useState(0);
    const [frameBuffer, setFrameBuffer] = useState([]); // Buffer for cartoonized frames
    const [frameBufferLength, setFrameBufferLength] = useState(0);
    const [cartoonImgUrl, setCartoonImgUrl] = useState("");
    const [cartoonImgBatch, setCartoonImgBatch] = useState(1);
    const [renderingStarted, setRenderingStarted] = useState(false)
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
    const [joinwith, setJoinwith] = useState("");
    const [preview, setPreview] = useState(false)
    const [previewLabel, setPreviewLabel] = useState("Turn On Preview")
    const navigate = useNavigate();

    const POD_COLOR = '#FF6655';
    const GLOW_COLOR = '#ffc3bd';
    const interval = 10000

    let wakeLock;

    //Use effect for audio websocket duplex communication
    useEffect(() => {
        if (audiows != null) {
            console.log('called connect_audio_processor_service')
            connect_audio_processor_service();
        }

        

    }, [audiows])

    //Use effect for video websocket duplex communication
    useEffect(() => {
        
        if (videows != null) {
            console.log('called connect_video_processor_service')
            connect_video_processor_service();
        }

    }, [videows])

    //Use effect to validate passcode when joining with audio access
    useEffect(() => {
        if (source !== null && audioContext !== null && name != "" && pcode != "") {
            requestAccessKey(name, pcode);
        }

    }, [source, audioContext, name, pcode])


    //Use effect to validate passcode when joining with video access
    useEffect(() => {
        if (mediaRecorder !== null && (joinwith === 'Video' || joinwith ==='Videocartoonify')) {
            requestAccessKey(name, pcode);
        }

    }, [mediaRecorder,reconnectCounter, joinwith])


    //Use effect to intermetently reload the transcript
    useEffect(() => {
        let intervalLoad

        // fetch the transcript   
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

    //Use effect to intermetently display the transcript
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

    //Use effect to start audio and video processing
    useEffect(() => {
        if(audioconnected && !videoconnected){
            requestStartAudioProcessing();
        }
        if(audioconnected && videoconnected){
            requestStartVideoProcessing();
        }
    }, [audioconnected,videoconnected])

    //Use effect to start the camera and microphone for video and audio capturing
    useEffect(() => {
        if(authenticated){
        const loadWorklet = async () => {

            await audioContext.audioWorklet.addModule('audio-sender-processor.js');
            const workletProcessor = new AudioWorkletNode(audioContext, 'audio-sender-processor');
            workletProcessor.port.onmessage = data => {
                audiows.send(data.data.buffer);
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
                    videows.send(fixedblob);
                    audiows.send(fixedblob);
                })
            }
        }

        if (authenticated && joinwith === 'Audio'){
            loadWorklet().catch(console.error);
        }else if (authenticated && (joinwith === 'Video' || joinwith === 'Videocartoonify')){
            videoPlay()
        }
    }
    }, [authenticated])

    //Use effect to toggle video view pane
    useEffect(() => {
        if (preview) {
            setPreviewLabel("Turn Off Preview")
        } else {
            setPreviewLabel("Turn On Preview")
        }
    }, [preview])

    //Use effect to display processed cartoonized image
    useEffect(() => {
        console.log('inside renderframe buffer useeffect ', frameBufferLength)
        renderFrameFromBuffer()
    }, [frameBufferLength])

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
        setAudioConnected(false);
        setVideoConnected(false);
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
        if (audiows != null) {
            audiows.close();
            setAudioWs(null);
        }
        if (videows != null) {
            videows.close();
            setVideoWs(null);
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
        if (joinswith === 'Video' || joinswith === 'Videocartoonify') {
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
                        } else if (joinswith === 'Video' || joinswith === 'Videocartoonify') {
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
            console.log(ex)
            setDisplayText('Failed to get user audio source.');
            setCurrentForm('JoinError');
            disconnect(true);
        }
    }

    const handleStream =  async () => {

        const constraintObj = {}
        if (joinwith === 'Video' || joinwith === 'Videocartoonify') {
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
                        } else if (joinwith === 'Video' || joinwith === 'Videocartoonify') {
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
                            setVideoWs(new WebSocket(apiService.getVideoWebsocketEndpoint())); //video
                        }
                        setAudioWs(new WebSocket(apiService.getAudioWebsocketEndpoint()));
            } else {
                setDisplayText('No media devices detected.');
                setCurrentForm('JoinError');
                disconnect(true);
            }
        } catch (ex) {
            console.log(ex)
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
                        setAudioWs(new WebSocket(apiService.getAudioWebsocketEndpoint()));
                        
                        //activate video websocket also if user joins with video
                        if (joinwith === 'Video' || joinwith === 'Videocartoonify') { 
                            setVideoWs(new WebSocket(apiService.getVideoWebsocketEndpoint())); 
                        }
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



    // Connects to audio processor websocket server.
    const connect_audio_processor_service = () => {
        audiows.binaryType = 'arraybuffer';

        audiows.onopen = e => {
            console.log('[Connected audio processor service]');
            setAudioConnected(true);
            setPageTitle(name);
            setReload(true)
            setCurrentForm("");
            acquireWakeLock();
        };

        audiows.onmessage = e => {
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

        audiows.onclose = e => {
            console.log('[Disconnected]',ending.value);
            if (!ending.value) {
                if (reconnectCounter <= 5) {
                    setCurrentForm('Connecting');
                    setReconnectCounter(reconnectCounter + 1);
                    disconnect();
                    console.log('reconnecting ....')
                    setTimeout(handleStream, 10000);
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

    // Connects to video processor websocket server.
    const connect_video_processor_service = () => {
        videows.binaryType = 'blob';

        videows.onopen = e => {
            console.log('[Connected to video processor services]');
            setVideoConnected(true);
        };

        videows.onmessage = e => {
           if (typeof e.data === 'string'){
                const message = JSON.parse(e.data);
                if (message['type'] === 'start') {
                    setAuthenticated(true);
                    closeDialog();
                }else if(message['type'] === 'attention_data'){

                }else if (message['type'] === 'error') {
                    disconnect(true);
                    setDisplayText('The connection to the session has been closed by the server.');
                    setCurrentForm('ClosedSession');
                } else if (message['type'] === 'end') {
                    disconnect(true);
                    setDisplayText('The session has been closed by the owner.');
                    setCurrentForm('ClosedSession');
                }
            }else if (e.data instanceof Blob){
                const url = URL.createObjectURL(e.data);
                // Add the processed frame to the buffer
                
                setFrameBuffer(prevBuffer =>{
                        const newItems = [...prevBuffer, url]
                        if (newItems.length % 40 == 0) {
                            setFrameBufferLength(newItems.length)
                            // setCartoonImgBatch(prevCount => prevCount + 1)
                            // setFrameBufferLength(prevCount => prevCount + 1)
                        }
                        
                        return newItems
                    } 
                );

                setRenderingStarted(true)
            }
        };

        videows.onclose = e => {
            console.log('[Disconnected]',ending.value);
        };

    }


    // Begin capturing and sending client audio.
    const requestStartAudioProcessing = () => {
        let message = null
        if (audiows === null) {
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
                'embeddingsFile': sessionDevice.embeddings,
                'deviceid':sessionDevice.id,
                'sessionid': session.id
            };
        } else if (joinwith === 'Video' || joinwith === 'Videocartoonify') {
            message = {
                'type': 'start',
                'key': key,
                'start_time': 0.0,
                'sample_rate': 16000,
                'encoding': 'pcm_f16le',
                'video_encoding': 'video/mp4',
                'channels': 2,
                'streamdata': 'video',
                'embeddingsFile': sessionDevice.embeddings,
                'deviceid':sessionDevice.id,
                'sessionid': session.id
            };
        }
        audiows.send(JSON.stringify(message));

    }

    // Begin capturing and sending client video.
    const requestStartVideoProcessing = () => {
        let message = null
        if (videows === null) {
            return;
        }
        if (joinwith === 'Video') {
            message = {
                'type': 'start',
                'key': key,
                'start_time': 0.0,
                'sample_rate': 16000,
                'encoding': 'pcm_f16le',
                'video_encoding': 'video/mp4',
                'channels': 2,
                'streamdata': 'video',
                'embeddingsFile': sessionDevice.embeddings,
                'deviceid':sessionDevice.id,
                'sessionid': session.id
            };
        }else if(joinwith === 'Videocartoonify') {
            message = {
                'type': 'start',
                'key': key,
                'start_time': 0.0,
                'sample_rate': 16000,
                'encoding': 'pcm_f16le',
                'video_encoding': 'video/mp4',
                'channels': 2,
                'streamdata': 'video',
                'embeddingsFile': sessionDevice.embeddings,
                'deviceid':sessionDevice.id,
                'sessionid': session.id,
                'Video_cartoonify' : true
            };
        }
        
        
        videows.send(JSON.stringify(message));

    }

    const requestHelp = () => {
        sessionDevice.button_pressed = !sessionDevice.button_pressed;
        sessionService.setDeviceButton(sessionDevice.id, sessionDevice.button_pressed, key);
    }

    const navigateToLogin = (confirmed = false) => {
        if (!confirmed && (audioconnected || videoconnected)) {
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

    //function to render the cartoonized image
    const renderFrameFromBuffer = () => {
        console.log('frameBufferLength = ', frameBufferLength,' cartoonImgBatch = ', cartoonImgBatch)
        if (frameBufferLength > (40 * cartoonImgBatch)) {
            for (var i = (cartoonImgBatch-1)*40; i < cartoonImgBatch*40; i++){
                
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
        setPcode(e.target.value.toUpperCase());
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
                        videoApiEndpoint = {apiService.getVideoServerEndpoint()}
                        cartoonImgUrl = {cartoonImgUrl}
                        authKey = {key}

                    />
    )
}


export { JoinPage }
