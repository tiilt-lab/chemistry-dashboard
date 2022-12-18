import { Observable } from 'rxjs';
import { DeviceService } from '../services/device-service';
import { SessionService } from '../services/session-service';
import { ActiveSessionService } from '../services/active-session-service';
import { SessionModel } from '../models/session';
import { DeviceModel } from '../models/device';
import { TranscriptModel } from '../models/transcript';
import { KeywordUsageModel } from '../models/keyword-usage';
import { useEffect, useState } from 'react';
import { useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { PodComponentPages } from './html-pages'



function PodComponent() {

    const [sessionDevice, setSessionDevice] = useState({});
    const [session, setSession] = useState({});
    const [transcripts, setTransripts] = useState([]);
    const [displayTranscripts, setDisplayTranscripts] = useState([]);
    const [currentTranscript, setCurrentTranscript] = useState({});
    const [currentForm, setCurrentForm] = useState("");
    const [sessionClosing, setSessionClosing] = useState(false);
    const [subscriptions, setSubscriptions] = useState([]);
    const [deleteDeviceToggle, setDeleteDeviceToggle] = useState(false);
    const [timeRange, setTimeRange] = useState([0, 1]);
    const [startTime, setStartTime] = useState();
    const [endTime, setEndTime] = useState();
    const [intervalId, setIntervalId] = useState();
    const [reload, setReload] = useState(false)
    const [activeSessionService, setActiveSessionService] = useOutletContext();
    const { sessionDeviceId } = useParams();
    const navigate = useNavigate()

    useEffect(() => {
        // if (endTime === undefined) {
        //console.log('i was here')
        if (Object.keys(session).length <= 0) {
            const sessionSub = activeSessionService.getSession();
            if (sessionSub !== undefined) {
                setSession(sessionSub);
            }
        }

        if (Object.keys(sessionDevice).length <= 0) {
            const deviceSub = activeSessionService.getSessionDevice(sessionDeviceId);
            if (deviceSub !== undefined) {
                setSessionDevice(deviceSub);
            }
        }
        if (transcripts.length <= 0) {
           const transcriptSub = activeSessionService.getTranscripts()
            //const transcriptSub = activeSessionService.getSessionDeviceTranscripts(sessionDeviceId, setTransripts);

            transcriptSub.subscribe(e => {
                if (Object.keys(e).length !== 0) {
                    const data = e.filter(t => t.session_device_id === parseInt(sessionDeviceId, 10))
                        .sort((a, b) => (a.start_time > b.start_time) ? 1 : -1)
                    // console.log(data,session, 'testing refresh still debugging ...')
                    setTransripts(data)
                    const sessionLen = Object.keys(session).length > 0 ? session.length : 0;
                    setStartTime(Math.round(sessionLen * timeRange[0] * 100) / 100)
                    setEndTime(Math.round(sessionLen * timeRange[1] * 100) / 100)
                }
            })
            subscriptions.push(transcriptSub);
        }

        // Refresh based on timeslider.
        setIntervalId(setInterval(() => {
            //ResetTimeRange(timeRange);
            if (session === undefined || !session.recording) {
                clearInterval(intervalId);
            }
        }, 2000));

        return () => {
            subscriptions.map(sub => {
                if (sub.closed) {
                    sub.unsubscribe()
                }
            });
            clearInterval(intervalId);
        }
    }, [])

    useEffect(()=>{
        const sessionLen = Object.keys(session).length > 0 ? session.length : 0;
        const sTime = Math.round(sessionLen * timeRange[0] * 100) / 100;
        const eTime = Math.round(sessionLen * timeRange[1] * 100) / 100;
        setStartTime(sTime)
        setEndTime(eTime)
        setDisplayTranscripts(transcripts.filter(t => t.start_time >= sTime && t.start_time <= eTime));
    },[endTime])

    //console.log(session, transcripts, '-', sessionDevice, '-', displayTranscripts, '-', startTime, '-', endTime, '-', 'session .......')

    const ResetTimeRange = (values) => {
        const sessionLen = Object.keys(session).length > 0 ? session.length : 0;
        setTimeRange(values);
        setStartTime(Math.round(sessionLen * values[0] * 100) / 100);
        setEndTime(Math.round(sessionLen * values[1] * 100) / 100);
        generateDispalyTranscripts();
    }

    const generateDispalyTranscripts = () => {
        setDisplayTranscripts(transcripts.filter(t => t.start_time >= startTime && t.start_time <= endTime));
    }

    const navigateToSession = () => {
        navigate('/sessions/' + session.id);
    }

    const onSessionClosing = (isClosing) => {
        setSessionClosing(isClosing);
    }

    const seeAllTranscripts = () => {
        if (currentTranscript !== undefined) {
            navigate('/sessions/' + session.id + '/pods/' + sessionDeviceId + '/transcripts?index=' + currentTranscript.id)
        } else {
            navigate('/sessions/' + session.id + '/pods/' + sessionDeviceId + '/transcripts')
        }

    }

    const loading = () => {
        return (session === null || transcripts === null);
    }

    const removeDeviceFromSession = (deleteDevice = false) => {
        const fetchData = new SessionService().removeDeviceFromSession(session.id, sessionDeviceId, deleteDevice)
        fetchData.then(
            response => {
                if (response.status === 200) {
                    closeDialog();
                    if (deleteDevice) {
                        navigateToSession();
                    }
                }

            },
            apierror => {
                console.log('podcomponent func removedevicesession 1', apierror)
            }
        )
    }

    const onClickedTimeline = (transcript) => {
        setCurrentForm("Transcript");
        setCurrentTranscript(transcript);
    }

    const openDialog = (form) => {
        setDeleteDeviceToggle(false);
        setCurrentForm(form);
    }

    const closeDialog = () => {
        setCurrentForm("");
    }

    return (

        <PodComponentPages
            sessionDevice={sessionDevice}
            navigateToSession={navigateToSession}
            setRange={ResetTimeRange}
            onClickedTimeline={onClickedTimeline}
            session={session}
            displayTranscripts={displayTranscripts}
            startTime={startTime}
            endTime={endTime}
            transcripts={transcripts}
            loading={loading}
            onSessionClosing={onSessionClosing}
            currentForm={currentForm}
            currentTranscript={currentTranscript}
            closeDialog={closeDialog}
            seeAllTranscripts={seeAllTranscripts}
            openDialog={openDialog}
            deleteDeviceToggle={deleteDeviceToggle}
            setDeleteDeviceToggle={setDeleteDeviceToggle}
            removeDeviceFromSession={removeDeviceFromSession}
        />
    )
}

export { PodComponent }
