import { SessionService } from '../services/session-service';
import { SessionModel } from '../models/session';
import { DeviceService } from '../services/device-service';
import { DeviceModel } from '../models/device';
import { useState, useEffect } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import {PodsOverviewPages} from './html-pages'



function PodsOverviewComponent() {
    const [sessionClosing, setSessionClosing] = useState(false);
    const [openingDialog, setOpeningDialog] = useState(false);
    const [sessionDevices, setSessionDevices] = useState(null);
    const [session, setSession] = useState(null);
    const [selectedSessionDevice, setSelectedSessionDevice] = useState(null);
    //const [subscriptions, setSubscriptions] = useState([]);
    const [devices, setDevices] = useState([])
    const [currentForm, setCurrentForm] = useState("");
    const [activeSessionService, setActiveSessionService] = useOutletContext();
    const navigate = useNavigate();


    useEffect(() => {
        const sessionSub = activeSessionService.getSession();
        if(sessionSub !== undefined) {
            setSession(sessionSub);
        }
        const deviceSub = activeSessionService.getSessionDevices()
        if(sessionSub !== undefined) {
            setSessionDevices(deviceSub);
        }
        // subscriptions.push(sessionSub, deviceSub);

        // return () => {
        //     subscriptions.map(sub => sub.unsubscribe());
        // }
    }, [activeSessionService.sessionId])



    const goToDevice = (sessionDevice) => {
        navigate('/sessions/' + session.id + '/pods/' + sessionDevice.id);
    }

    const onSessionClosing = (isClosing) => {
        setSessionClosing(isClosing);
    }

    const navigateToSessions = () => {
        if (session.folder) {
           navigate('/sessions?folder='+session.folder)
        } else {
            navigate('/sessions', { replace: true })
        }
    }

    const openDialog = (form) => {
        if (form === "AddDevice") {
            const fetchData = new DeviceService().getDevices(false, true, false, true)
            fetchData.then(
                response => {
                    if (response.status === 200) {
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
        if (session!==null && session.end_date) {
            return 'CLOSED';
        } else if (session!==null && session.passcode == null) {
            return 'LOCKED';
        } else if(session!==null) {
            return session.passcode;
        }else{
            return "None"
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
                response.text().then(csvData => {
                  const anchor = document.createElement('a');
                  anchor.href = 'data:attachment/csv;charset=utf-8,' + encodeURI(csvData)
                  anchor.download = session.title + '.csv';
                  anchor.click();
                  console.log(csvData);
                  console.log('Download successful.');
                  //return true;
                  /* {const resp = response.json()
                  resp.then() }*/
                });
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

    const getRightEnabled = ()=>{
        if(session === null){
            return false
        }else if(session !== null){
            if(session.recording === undefined){
                return false
            }else{
                return session.recording
            }
        }
    }

    return (
        <PodsOverviewPages
            righttext = {getPasscode()}
            rightenabled = {getRightEnabled()}
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
            devices = {devices}
        />
   )
}

export {PodsOverviewComponent}
