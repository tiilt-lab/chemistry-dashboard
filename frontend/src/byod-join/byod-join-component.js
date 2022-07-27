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
    const [source, setSource] = useState(null);
    const [ending, setEnding] = useState(false);
    const [reconnectCounter, setReconnectCouner] = useState(0);

    // Session data
    const [sessionDevice, setSessionDevice] = useState(null);
    const [session, setSession] = useState(null);
    const [key, setKey] = useState(null);

    const [currentForm, setCurrentForm] = useState("");
    const [displayText, setDisplayText] = useState("");
    const [pageTitle, setPageTitle] = useState('Join Discussion');

    const [pcode, setPcode] = useState("");

    const navigate = useNavigate();

    const POD_COLOR = '#FF6655';
    const GLOW_COLOR = '#ffc3bd';

    // useEffect(()=>{
    //     console.log(currentForm)
    // },[currentForm])

    // Disconnects from websocket server and audio stream.
    const disconnect = (permanent = false) => {
        if (permanent) {
            setEnding(true);
        }
        setConnected(false);
        setAuthenticated(false);
        setPageTitle('Join Session');
        if (processor != null) {
            processor.onaudioprocess = null;
            processor.disconnect();
            setProcessor(null);
        }
        if (source != null) {
            source.disconnect();
            setSource(null);
        }
        if (audioContext != null) {
            audioContext.close();
            setAudioContext(null);
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
    const verifyInputAndAudio = (name, passcode) => {
        if (name === null || name.trim().length === 0) {
            name = 'User Device';
        }
        try {
            if (navigator.mediaDevices != null) {
                navigator.mediaDevices.getUserMedia({ audio: true, video: false })
                    .then(stream => {
                        stream.getAudioTracks().forEach(track => track.stop());
                        requestAccessKey(name, passcode);
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
        const fetchData = new SessionService().joinByodSession(names, passcode);
        fetchData.then(
            (response) => {
                if (response.status === 200) {
                    const json = response.json();
                    //console.log(json,"se first")
                    json.then(jsonObj => {
                        const sess = SessionModel.fromJson(jsonObj['session']);
                        const sessDev = SessionDeviceModel.fromJson(jsonObj['session_device']);
                        setSession(sess);
                        setSessionDevice(sessDev);
                        setKey(jsonObj.key);
                        handleStream(sessDev);
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

    // Creates stream with the users audio input.
    const handleStream = (sessDev) => {
        navigator.mediaDevices.getUserMedia({ audio: true, video: false })
            .then(stream => {
                setStreamReference(stream);
                const audioCont = new ((window).AudioContext || (window).webkitAudioContext)()
                setAudioContext(audioCont);
                const src = audioCont.createMediaStreamSource(stream)
                const proc = audioCont.createScriptProcessor(16384, 1, 1)
                setSource(src);
                setProcessor(proc);

                src.connect(proc);
                proc.connect(audioCont.destination);

                proc.onaudioprocess = e => {

                    if (connected && authenticated) {
                        const data = e.inputBuffer.getChannelData(0);
                        ws.send(data.buffer);
                    }
                };

                connect(sessDev);
            }, error => {
                setDisplayText('Failed to get user audio source.');
                setCurrentForm('JoinError');
                disconnect(true);
            });
    }

    // Connects to websocket server.
    const connect = (sessDev) => {
        const wss = new WebSocket(new ApiService().getWebsocketEndpoint())
        setWs(wss);
        wss.binaryType = 'arraybuffer';

        wss.onopen = e => {
            console.log('[Connected]');
            setConnected(true);
            setPageTitle(sessDev.name);
            setCurrentForm("");
            setReconnectCouner(0);
            requestStart();
        };

        wss.onmessage = e => {
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

        wss.onclose = e => {
            console.log('[Disconnected]');
            if (!ending) {
                if (reconnectCounter < 5) {
                    setCurrentForm('Connecting');
                    setReconnectCouner(reconnectCounter + 1);
                    disconnect();
                    setTimeout(() => {
                        handleStream(sessDev);
                    }, 1000);
                } else {
                    setDisplayText('Connection to the session has been lost.');
                    setCurrentForm('ClosedSession');
                    disconnect(true);
                }
            }
        };
    }



    // Begin capturing and sending client audio.
    const requestStart = () => {
        if (ws === null) {
            return;
        }
        const context = new ((window).AudioContext || (window).webkitAudioContext)();
        const message = {
            'type': 'start',
            'key': key,
            'start_time': 0.0,
            'sample_rate': context.sampleRate,
            'encoding': 'pcm_f32le',
            'channels': 1
        };
        context.close();
        ws.send(JSON.stringify(message));
        
    }

    const requestHelp = () => {
        sessionDevice.button_pressed = !sessionDevice.button_pressed;
        new SessionService().setDeviceButton(sessionDevice.id, sessionDevice.button_pressed, key);
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
            pcode = {pcode}
            setPcode = {setPcode}
            changeTouppercase = {changeTouppercase}
        />
    )
}






export { JoinPage }