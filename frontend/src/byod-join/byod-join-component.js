import { useEffect, useState } from 'react';
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
    const [reload,setReload] = useState(false)
    const [pageTitle, setPageTitle] = useState('Join Discussion');

    const [name, setName] = useState("");
    const [pcode, setPcode] = useState("");

    const navigate = useNavigate();

    const POD_COLOR = '#FF6655';
    const GLOW_COLOR = '#ffc3bd';
    
    useEffect(()=>{

        
        console.log("src: ", source);
        if(source !== null && audioContext !== null && name != "" && pcode != ""){
           
           requestAccessKey(name, pcode);
	    }
        
    }, [source, audioContext, name, pcode])
    
    useEffect(()=>{
        console.log("ws: ", ws);
        if(ws != null) 
        {
            connect();
	    }
        
    }, [ws])

    useEffect(() => {
        console.log("ws before requestStart: ", ws);
        console.log("context before requestStart: ", audioContext);
        if(connected)
            requestStart();
    }, [connected])
    
    useEffect(() => {
        const loadWorklet = async () => {
            await audioContext.audioWorklet.addModule('audio-sender-processor.js');
            const workletProcessor = new AudioWorkletNode(audioContext, 'audio-sender-processor');
            workletProcessor.port.onmessage = data => {
                //console.log("sending data: ", data.data)
                ws.send(data.data.buffer);
            }
            source.connect(workletProcessor).connect(audioContext.destination);
            setAudioSenderProcessor(workletProcessor);
        }

        if(authenticated)
            loadWorklet().catch(console.error);
        
    }, [authenticated])

    useEffect(()=>{
        return ()=>{
            disconnect(true)
        }
    },[])
    
    // Disconnects from websocket server and audio stream.
    const disconnect = (permanent = false) => {
        if (permanent) {
            setEnding(true);
            setPageTitle('Join Session');
            setName("");
            setPcode("");
        }

        setConnected(false);
        setAuthenticated(false);

        if (source != null) {
            source.disconnect();
            setSource(null);
        }
        if (audioContext != null) {
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
    const verifyInputAndAudio = (names, passcode) => {
        console.log("Name ", names)
        if (names === null || names.trim().length === 0) {
            names = 'User Device';
        }
        setName(names);
        setPcode(passcode);
        try {
            if (navigator.mediaDevices != null) {
                navigator.mediaDevices.getUserMedia({ audio: true, video: false })
                    .then(function(stream) {
                    	const context = new AudioContext();
                    	setStreamReference(stream);
                    	setSource(context.createMediaStreamSource(stream));
                    	setAudioContext(context);
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
        sessionService.joinByodSession(names, passcode).then(
            (response) => {
                if (response.status === 200) {
                    response.json().then(jsonObj => {
                    	console.log(jsonObj,"reponse first")
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
        };

        ws.onmessage = e => {
            const message = JSON.parse(e.data);
            console.log("Websocket message: ", message);
            if (message['type'] === 'start') {
                setAuthenticated(true);
                closeDialog();
            } else if (message['type'] === 'error') {
                disconnect(true);
                setDisplayText('The connection to the session has been closed by the server.');
                console.log('session closed 2')
                setCurrentForm('ClosedSession');
                setReload(false)
            } else if (message['type'] === 'end') {
                disconnect(true);
                setDisplayText('The session has been closed by the owner.');
                console.log('session closed 3')
                setCurrentForm('ClosedSession');
                setReload(false)
            }
        };

        ws.onclose = e => {
            console.log('[Disconnected]');
            if (!ending) {
                console.log(reconnectCounter, 'not ending ...')
                if (reconnectCounter <= 5) {
                    setCurrentForm('Connecting');
                    setReconnectCounter(reconnectCounter+1);
                    disconnect();
                    console.log('reconnecting ....')
                    setReload(false)
                    setTimeout(() => {
                        verifyInputAndAudio(name, pcode)
                    }, 1000);
                } else {
                    setDisplayText('Connection to the session has been lost.');
                    console.log('session closed 1')
                    setCurrentForm('ClosedSession');
                    setReload(false)
                    disconnect(true);
                    
                }
            }else{
                console.log('ending ...')
            }
        };
    }



    // Begin capturing and sending client audio.
    const requestStart = () => {
        if (ws === null) {
            console.log(ws, 'i am context ....')
            return;
        }
        console.log(audioContext, 'context ....')
        const message = {
            'type': 'start',
            'key': key,
            'start_time': 0.0,
            'sample_rate': audioContext.sampleRate,
            'encoding': 'pcm_f32le',
            'channels': 1
        };
        console.log("requesting start", message)
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
            return navigate('/login');
        }
    }

    const closeDialog = () => {
        setCurrentForm("");
    }

    const changeTouppercase = (e) => {
        setPcode(e.target.value.toUpperCase());
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
            pcode = {pcode}
            setPcode = {setPcode}
            changeTouppercase = {changeTouppercase}
        />
    )
}






export { JoinPage }
