import { SessionService } from '../services/session-service';
import { useEffect, useState } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import { AppSessionPage } from './html-pages'

function AppSessionToolbar(props) {
    // @Input('session') session: SessionModel;
    // @Output() closingSession = new EventEmitter<boolean>();
    
    const [timeText, setTimeText] = useState('');
    const [sessionEnding, setSessionEnding] = useState();
    const [intervalId, setInterValid] = useState();
    const [searchParam, setSearchParam] = useSearchParams();
    const [fromClient, setFromClient] = useState(false);
    const navigate = useNavigate();
    const location = useLocation()


    useEffect(() => {
        console.log(props.session.length,'session length')
        if(props.fromClient)
            setFromClient(props.fromClient)
        const intvalId = setInterval(() => {
            updateTime();
        }, 1000);
        setInterValid(intvalId)
        updateTime();
        //destroy function
        return () => {
            clearInterval(intvalId);
        }
    }, [props.session])


    const updateTime = () => {
        //console.log(props.session.length,'session length')
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
        // do smth diff for just deleting one thing, I think I have it tho
        let deleteDevice = location.pathname == '/join';
        setSessionEnding(true);
        props.closingSession(true);
        const fetchData = deleteDevice ? (new SessionService().removeDeviceFromSession(props.session.id, props.sessionDevice.id, true)) : (new SessionService().endSession(props.session.id));
        fetchData.then(response => {
            if (response.status === 200) {
                setSessionEnding(false);
                if (deleteDevice) {
                    navigate('/join')
                } else {
                    if (props.session.folder) {
                    	 // works now, just had to switch the lines
                    	 setSearchParam({ folder: props.session.folder })
                        navigate('/sessions?folder=' + props.session.folder);
                    } else {
                        navigate('/sessions', { replace: true })
                    }
                }
            }
        })
    }

    return (
        < AppSessionPage
            sessionEnding={sessionEnding}
            timeText={timeText}
            innerhtml={props.children}
            session={props.session}
            onEndSession={onEndSession}
            menus={props.menus}
            speakers = {props.participants}
            seesions={props.seesions}
            fromClient={props.fromClient}
        />
    )
}

export { AppSessionToolbar }
