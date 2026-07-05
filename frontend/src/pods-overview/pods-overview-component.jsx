import { SessionService } from "../services/session-service";
import { SessionModel } from "../models/session";
import { DeviceService } from "../services/device-service";
import { DeviceModel } from "../models/device";
import { SpeakerModel } from "../models/speaker";
import { useState, useEffect } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { PodsOverviewPages } from "./html-pages";

function PodsOverviewComponent() {
  const [sessionClosing, setSessionClosing] = useState(false);
  const [openingDialog, setOpeningDialog] = useState(false);
  const [sessionDevices, setSessionDevices] = useState(null);
  const [session, setSession] = useState(null);
  const [sessionSpeaker, setSessionSpeakers] = useState([])
  const [selectedSessionDevice, setSelectedSessionDevice] = useState(null);
  //const [subscriptions, setSubscriptions] = useState([]);
  const [devices, setDevices] = useState([]);
  // Enriched per-pod info (duration, participants, has_data, analysis_running)
  // straight from the devices endpoint — the shared in-memory source strips
  // these fields. Polled so the Analyzing badge updates live.
  const [enriched, setEnriched] = useState({});
  const [selected, setSelected] = useState({});
  const [queueState, setQueueState] = useState({});
  const toggleSelect = (id) =>
    setSelected((cur) => ({ ...cur, [id]: !cur[id] }));
  const toggleSelectAll = (ids) =>
    setSelected((cur) => {
      const allOn = ids.length > 0 && ids.every((id) => cur[id]);
      const next = {};
      for (const id of ids) next[id] = !allOn;
      return next;
    });
  const loadQueue = (sid) =>
    new SessionService().getPosthocQueue(sid).then(
      (r) => {
        if (r.status === 200)
          r.json().then((list) => {
            const m = {};
            for (const j of list) m[j.device_id] = j.state;
            setQueueState(m);
          });
      },
      () => {},
    );
  useEffect(() => {
    if (session === null || !session.id) return;
    loadQueue(session.id);
    const t = setInterval(() => loadQueue(session.id), 15000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);
  const stopRuns = () => {
    if (session === null) return;
    new SessionService().stopPosthocQueue(session.id).then(
      () => loadQueue(session.id),
      () => {},
    );
  };
  const runSelected = () => {
    const ids = Object.keys(selected).filter((k) => selected[k]);
    if (!ids.length || session === null) return;
    new SessionService().enqueuePosthoc(session.id, ids).then(
      () => {
        setSelected({});
        loadQueue(session.id);
      },
      () => {},
    );
  };
  useEffect(() => {
    if (session === null || !session.id) return;
    let alive = true;
    const load = () =>
      new SessionService().getSessionDevices(session.id).then(
        (r) => {
          if (r.status === 200)
            r.json().then((list) => {
              if (!alive) return;
              const map = {};
              for (const d of list) map[d.id] = d;
              setEnriched(map);
            });
        },
        () => {},
      );
    load();
    const t = setInterval(load, 15000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [session]);
  const [currentForm, setCurrentForm] = useState("");
  const [activeSessionService, setActiveSessionService] = useOutletContext();
  const navigate = useNavigate();
  const [trigger, setTrigger] = useState(0);
  const interval = 2000;

  useEffect(() => {
    if (activeSessionService !== null) {
      const nextSession = activeSessionService.getSession();
      setSession(nextSession);
      const nextSessionDevices = activeSessionService.getSessionDevices();
      setSessionDevices(nextSessionDevices);

      getSessionSpeakers(nextSession.id)

      let intervalLoad = setInterval(() => {
        const nextSession = activeSessionService.getSession();
        setSession(nextSession);
        const nextSessionDevices = [
          ...activeSessionService.getSessionDevices(),
        ];
        setSessionDevices(nextSessionDevices);
      }, interval);

      // subscriptions.push(sessionSub, deviceSub);

      // return () => {
      //     subscriptions.map(sub => sub.unsubscribe());
      // }
      return () => {
        clearInterval(intervalLoad);
      };
    }
  }, [activeSessionService]);

  // so that the passcode renders in time
  useEffect(() => {
    console.log("reload");
  }, [trigger]);

  const goToDevice = (sessionDevice) => {
    navigate("/sessions/" + session.id + "/pods/" + sessionDevice.id);
  };

  const goToSpeakerMetrics = (speakerID) => {
    navigate("/sessions/" + session.id + "/pods_session/" + speakerID);
  };

  const onSessionClosing = (isClosing) => {
    setSessionClosing(isClosing);
  };

  const navigateToSessions = () => {
    if (session.folder) {
      navigate("/sessions?folder=" + session.folder);
    } else {
      navigate("/sessions", { replace: true });
    }
  };

  const openDialog = (form) => {
    if (form === "AddDevice") {
      const fetchData = new DeviceService().getDevices(
        false,
        true,
        false,
        true
      );
      fetchData.then(
        (response) => {
          if (response.status === 200) {
            const resp2 = response.json();
            resp2.then((respdevices) => {
              const deviceresult = DeviceModel.fromJsonList(respdevices);
              setDevices(deviceresult);
              setCurrentForm(form);
            });
          }
        },
        (apierror) => {
          console.log("pods-overview-components func: openDialog 1 ", apierror);
        }
      );
    } else if (form === "Passcode" && session.end_date == null) {
      setCurrentForm(form);
    }
  };

  // Status (closed/locked) renders as a non-clickable pill; only a live
  // passcode stays a clickable header action (opens the Passcode dialog).
  const getRightPill = () => {
    if (session !== null && session.end_date) return "Closed";
    if (session !== null && session.passcode == null) return "Locked";
    return null;
  };

  const getPasscode = () => {
    if (session !== null && !session.end_date && session.passcode != null) {
      return session.passcode;
    }
    return "";
  };

  const addPodToSession = (deviceId) => {
    const fetchData = new SessionService().addPodToSession(
      this.session.id,
      deviceId
    );
    fetchData.then(
      (response) => {
        if (response.status === 200) {
          closeDialog();
        }
      },
      (apierror) => {
        console.log(
          "pods-overview-components func: addPodToSession 1 ",
          apierror
        );
      }
    );
  };

  const setPasscodeState = (state) => {
    const fetchData = new SessionService().setPasscodeStatus(session.id, state);
    fetchData.then(
      (response) => {
        if (response.status === 200) {
          closeDialog();
        }
        setSession(activeSessionService.getSession());
        setTrigger(trigger + 1);
      },
      (apierror) => {
        console.log(
          "pods-overview-components func: setPasscodeState 1 ",
          apierror
        );
      }
    );
  };

  // to make it easier on the user
  const copyPasscode = () => {
    let pwd = getPasscode();
    navigator.clipboard.writeText(pwd);
  };

  const exportSessionMetricsData = (type,windowsize,format) => {
    let fetchData = null;
    if (type == "audiometrics") {
      fetchData = new SessionService().downloadSessionTranscriptMetrics(session.id, session.title,windowsize,format);
    } else if (type == "videometrics") {
      fetchData = new SessionService().downloadSessionVideoMetrics(session.id, session.title,windowsize,format);
    } else if (type == "transcriptvideometrics") {
      fetchData = new SessionService().downloadSessionTranscriptVideoMetrics(session.id, session.title,windowsize,format);
    }
    if (fetchData != null) {
      fetchData.then(
        (response) => {
          if (response.status === 200) {
            response.text().then((Data) => {
              const anchor = document.createElement("a");
              anchor.href =
                "data:attachment/csv;charset=utf-8," + encodeURI(Data);
              let extension = format === "csv" ? ".csv" : ".json"  
              anchor.download = session.title + extension;
              anchor.click();
             
              //return true;
              /* {const resp = response.json()
                    resp.then() }*/
            });
          } else {
            alert("Failed to download transcript metrics.");
          }
        },
        (apierror) => {
          console.log(
            "pods-overview-components func: exportSessionTranscriptMetrics 1 ",
            apierror
          );
          alert("Failed to download transcript metrics.");
        }
      );
    }
  };

 

  const downloadData = (windowsize, datatype,format) => {
    exportSessionMetricsData(datatype,windowsize,format);
  }

  const closeDialog = () => {
    setCurrentForm("");
  };

  const openDownloadOptionDialog = (dialog) => {
    setCurrentForm(dialog);
  };

  const goToGraph = () => {
    navigate("/sessions/" + session.id + "/graph");
  };

  const getSessionSpeakers = (sessionID) => {
    const fetchData = new SessionService().getSessionSpeakers(sessionID);
    fetchData.then(
      (response) => {
        if (response.status === 200)
          response.json().then((jsonObj) => {
            const input = SpeakerModel.fromJsonList(jsonObj)
            const identified_speakers = []
            const uniqueSpeakers = []
            if (input && input.length) {
              input.map((spkr, index) => {
                if (identified_speakers.indexOf(spkr.alias) == -1) {
                  uniqueSpeakers.push(spkr)
                  identified_speakers.push(spkr.alias)
                }
              })
              setSessionSpeakers(uniqueSpeakers);
            }
          });
      },
      (apierror) => {
        console.log("pod-overview-component func getspeakers 1", apierror);
      }
    );
  };


  return (
    <PodsOverviewPages
      enriched={enriched}
      selected={selected}
      toggleSelect={toggleSelect}
      toggleSelectAll={toggleSelectAll}
      runSelected={runSelected}
      stopRuns={stopRuns}
      queueState={queueState}
      righttext={getPasscode()}
      rightpill={getRightPill()}
      session={session}
      openDialog={openDialog}
      navigateToSessions={navigateToSessions}
      sessionDevices={sessionDevices}
      goToDevice={goToDevice}
      goToGraph={goToGraph}
      currentForm={currentForm}
      closeDialog={closeDialog}
      setPasscodeState={setPasscodeState}
      copyPasscode={copyPasscode}
      onSessionClosing={onSessionClosing}
      initialized={activeSessionService.initialized}
      sessionSpeaker={sessionSpeaker}
      devices={devices}
      goToSpeakerMetrics={goToSpeakerMetrics}
      openDownloadOptionDialog={openDownloadOptionDialog}
      downloadData={downloadData}
    />
  );
}

export { PodsOverviewComponent };
