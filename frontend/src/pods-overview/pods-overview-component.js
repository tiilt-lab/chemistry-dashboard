import { SessionService } from '../services/session-service';
import { SessionModel } from '../models/session';
import { DeviceService } from '../services/device-service';
import { DeviceModel } from '../models/device';
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, useOutletContext } from 'react-router-dom';
import {PodsOverviewPages} from './html-pages'

// enum Forms {
//     Passcode = 1,
//     AddDevice
// }


function PodsOverviewComponent() {
    const [sessionClosing, setSessionClosing] = useState(false);
    const [openingDialog, setOpeningDialog] = useState(false);
    const [sessionDevices, setSessionDevices] = useState();
    const [session, setSession] = useState(null);
    const [selectedSessionDevice, setSelectedSessionDevice] = useState(null);
    const [subscriptions, setSubscriptions] = useState([]);
    const [devices, setDevices] = useState([])
    const [currentForm, setCurrentForm] = useState("");
    const [activeSessionService, setActiveSessionService] = useOutletContext();
    const [searchParam, setSearchParam] = useSearchParams();
    const navigate = useNavigate();

    const POD_ON_COLOR = '#FF6655';
    const POD_OFF_COLOR = '#D0D0D0';
    const GLOW_COLOR = '#ffc3bd';


    useEffect(() => {
        const sessionSub = activeSessionService.getSession().subscribe(e => {
            setSession(e);
        });
        const deviceSub = activeSessionService.getSessionDevices().subscribe(e => {
            setSessionDevices(e);
        });
        subscriptions.push(sessionSub, deviceSub);

        return () => {
            subscriptions.map(sub => sub.unsubscribe());
        }
    }, [])



    const goToDevice = (sessionDevice) => {
        navigate('/sessions' + session.id + '/pods/' + sessionDevice.id);
    }

    const onSessionClosing = (isClosing) => {
        setSessionClosing(isClosing);
    }

    const navigateToSessions = () => {
        if (session.folder) {
            setSearchParam({ folder: session.folder })
        } else {
            navigate('/sessions', { replace: true })
        }
        //this.router.navigate(['sessions'], {queryParams: {folder: this.session.folder}});
    }

    const openDialog = (form) => {
        if (form === "AddDevice") {
            const fetchData = new DeviceService().getDevices(false, true, false, true)
            fetchData.then(
                response => {
                    if (response == 200) {
                        const resp2 = response.json()
                        resp2.then(
                            respdevices => {
                                const deviceresult = DeviceModel.fromJsonList(respdevices)
                                setDevices(deviceresult);
                                setCurrentForm(form);
                            }
                        )
                    }
                },
                apierror => {
                    console.log("pods-overview-components func: openDialog 1 ", apierror)
                }
            );
        } else if (form === "Passcode" && session.end_date == null) {
            setCurrentForm(form);
        }
    }

    const getPasscode = () => {
        if (session.end_date) {
            return 'CLOSED';
        } else if (session.passcode == null) {
            return 'LOCKED';
        } else {
            return session.passcode;
        }
    }

    const addPodToSession = (deviceId) => {
        const fetchData = new SessionService().addPodToSession(this.session.id, deviceId)
        fetchData.then(response => {
            if (response.status === 200) {
                closeDialog();
            }
        },
            apierror => {
                console.log("pods-overview-components func: addPodToSession 1 ", apierror)
            });
    }

    const setPasscodeState = (state) => {
        const fetchData = new SessionService().setPasscodeStatus(session.id, state)
        fetchData.then(response => {
            if (response.status === 200) {
                closeDialog();
            }
        },
            apierror => {
                console.log("pods-overview-components func: setPasscodeState 1 ", apierror)
            });
    }

    const exportSession = () => {
        const fetchData = new SessionService().downloadSessionReport(session.id, session.title)
        fetchData.then(
            response => {
                if (response.status === 200) {
                    const anchor = document.createElement('a');
                    anchor.href = 'data:attachment/csv;charset=utf-8,' + encodeURI((response)._body)
                        anchor.download = session.title + '.csv';
                    anchor.click();
                    console.log('Download successful.')
                    //return true;
                    {/* const resp = response.json()
                    resp.then() */}
                } else {
                    alert('Failed to download session report.');
                }
            },
            apierror => {
                console.log("pods-overview-components func: exportsession 1 ", apierror)
                alert('Failed to download session report.');
            });
    }

    const closeDialog = ()=> {
        setCurrentForm("");
    }

    const goToGraph = ()=> {
        navigate('/sessions/' + session.id + '/graph');
    }

    return (
        <PodsOverviewPages 
            getPasscode = {getPasscode}
            session = {session}
            openDialog = {openDialog}
            navigateToSessions = {navigateToSessions}
            sessionDevices = {sessionDevices}
            goToDevice = {goToDevice}
            exportSession = {exportSession}
            goToGraph = {goToGraph}
            currentForm = {currentForm}
            closeDialog = {closeDialog}
            setPasscodeState = {setPasscodeState}
            onSessionClosing = {onSessionClosing}
            POD_ON_COLOR = {POD_ON_COLOR}
            POD_OFF_COLOR = {POD_OFF_COLOR}
            GLOW_COLOR = {GLOW_COLOR}
        />
    )
}

export {PodsOverviewComponent}