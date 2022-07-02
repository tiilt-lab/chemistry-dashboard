import { SessionService } from '../services/session-service';
import { SessionModel } from '../models/session';
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AppSessionPage } from './html-pages'

function AppSessionToolbar(props) {
    // @Input('session') session: SessionModel;
    // @Output() closingSession = new EventEmitter<boolean>();

    const [timeText, setTimeText] = useState('');
    const [sessionEnding, setSessionEnding] = useState();
    const [intervalId, setInterValid] = useState();
    const [searchParam, setSearchParam] = useSearchParams();
    const navigate = useNavigate();



    useEffect(() => {
        const intvalId = setInterval(() => {
            updateTime();
            if (!props.session.recording) {
                clearInterval(intervalId);
            }
        }, 1000);
        setInterValid(intvalId)
        updateTime();

        //destroy function
        return () => {
            clearInterval(intervalId);
        }
    }, [])


    const updateTime = () => {
        // doesn't currently support displaying hours
        const m = Math.floor(props.session.length / 60);
        const s = Math.floor(props.session.length - m * 60);
        let secs_text;
        if (s < 10) {
            secs_text = '0' + s;
        } else {
            secs_text = '' + s;
        }
        setTimeText(m + ':' + secs_text);
    }

    const onEndSession = () => {
        setSessionEnding(true);
        props.onSessionClosing(true)
        //this.closingSession.emit(true);
        const fetchData = new SessionService().endSession(props.session.id)
        fetchData.then(response => {
            if (response.status === 200) {
                setSessionEnding(false);
                if (props.session.folder) {
                    navigate('/sessions?folder='+props.session.folder)
                    setSearchParam({ folder: props.session.folder })
                } else {
                    navigate('/sessions', { replace: true })
                }
            }
        })
    }

    const closeEndDialog = () => {
        setSessionEnding(false);
    }

    return (
        < AppSessionPage
            sessionEnding={sessionEnding}
            timeText={timeText}
            innerhtml={props.children}
            session={props.session}
            onEndSession={onEndSession}
        />
    )
}

export { AppSessionToolbar }