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
import {PodComponentPages} from './html-pages'


function PodComponent() {

    const [sessionDevice, setSessionDevice] = useState({});
    const [session, setSession] = useState({});
    const [transcripts, setTransripts] = useState([]);
    const [displayTranscripts, setDisplayTranscripts] = useState([]);
    const [currentTranscript, setCurrentTranscript] = useState();
    const [currentForm, setCurrentForm] = useState("");
    const [sessionClosing, setSessionClosing] = useState(false);
    //const [subscriptions, setSubscriptions] = useState([]);
    const [deleteDeviceToggle, setDeleteDeviceToggle] = useState(false);
    const [timeRange, setTimeRange] = useState([0, 1]);
    const [startTime, setStartTime] = useState();
    const [endTime, setEndTime] = useState();
    const [intervalId, setIntervalId] = useState();
    const [activeSessionService, setActiveSessionService] = useOutletContext();
    const { sessionDeviceId } = useParams();
    const navigate = useNavigate()


    useEffect(() => {
       // if (sessionDeviceId !== undefined) {
            const sessionSub = activeSessionService.getSession();
            if(sessionSub !== undefined){  
                setSession(sessionSub);
            }

            const deviceSub = activeSessionService.getSessionDevice(sessionDeviceId);
            if(deviceSub !== undefined){  
                setSessionDevice(deviceSub);
            }
            
            const transcriptSub = activeSessionService.getSessionDeviceTranscripts(sessionDeviceId);
            if(transcriptSub!==undefined){
                setDisplayTranscripts(transcriptSub);
                setRange(timeRange);
            }

           // subscriptions.push(sessionSub, deviceSub, transcriptSub);
       // }



        // Refresh based on timeslider.
        setIntervalId(setInterval(() => {
            setRange(timeRange);
            if (session===undefined || !session.recording) {
                clearInterval(intervalId);
            }
        }, 2000));

        setRange(timeRange);

        // return () => {
        //     subscriptions.map(sub => sub.unsubscribe());
        //     clearInterval(intervalId);
        // }
    }, [])


    const setRange = (values) => {
        const sessionLen = session !== undefined ? session.length : 0;
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

    const onClickedTimeline = (transcript)=> {
        setCurrentForm("Transcript");
        setCurrentTranscript(transcript);
    }

    const openDialog = (form)=> {
        setDeleteDeviceToggle(false);
        setCurrentForm(form);
    }

    const closeDialog = ()=> {
        setCurrentForm("");
    }

    return(
        <PodComponentPages 
            sessionDevice = {sessionDevice}
            navigateToSession = {navigateToSession}
            setRange = {setRange}
            onClickedTimeline = {onClickedTimeline}
            session = {session}
            displayTranscripts = {displayTranscripts}
            startTime = {startTime}
            endTime = {endTime}
            transcripts = {transcripts}
            loading = {loading}
            onSessionClosing = {onSessionClosing}
            currentForm = {currentForm}
            currentTranscript = {currentTranscript}
            closeDialog = {closeDialog}
            seeAllTranscripts = {seeAllTranscripts}
            openDialog = {openDialog}
            deleteDeviceToggle = {deleteDeviceToggle}
            setDeleteDeviceToggle = {setDeleteDeviceToggle}
            removeDeviceFromSession = {removeDeviceFromSession}
        />
    )
}

export {PodComponent}