import { Observable } from "rxjs";
import { DeviceService } from "../services/device-service";
import { SessionService } from "../services/session-service";
import { ActiveSessionService } from "../services/active-session-service";
import { SessionModel } from "../models/session";
import { DeviceModel } from "../models/device";
import { TranscriptModel } from "../models/transcript";
import { KeywordUsageModel } from "../models/keyword-usage";
import { SpeakerModel } from "../models/speaker";
import { useEffect, useState } from "react";
import { useNavigate, useOutletContext, useParams } from "react-router-dom";
import { PodComponentPages } from "./html-pages";

function PodComponent() {
  const [sessionDevice, setSessionDevice] = useState({});
  const [session, setSession] = useState({});
  const [transcripts, setTranscripts] = useState([]);
  const [videoMetrics, setVideoMetrics] = useState([])
  const [speakerMetrics, setSpeakerMetrics] = useState([]);
  const [displayTranscripts, setDisplayTranscripts] = useState([]);
  const [displayVideoMetrics, setDisplayVideoMetrics] = useState([])
  const [currentTranscript, setCurrentTranscript] = useState({});
  const [currentForm, setCurrentForm] = useState("");
  const [sessionClosing, setSessionClosing] = useState(false);
  const [subscriptions, setSubscriptions] = useState([]);
  const [deleteDeviceToggle, setDeleteDeviceToggle] = useState(false);
  const [timeRange, setTimeRange] = useState([0, 1]);
  const [startTime, setStartTime] = useState();
  const [endTime, setEndTime] = useState();
  const [intervalId, setIntervalId] = useState();
  const [trigger, setTrigger] = useState(0);
  const [activeSessionService, setActiveSessionService] = useOutletContext();
  const [showFeatures, setShowFeatures] = useState([]);
  const [showBoxes, setShowBoxes] = useState([]);
  const [radarTrigger, setRadarTrigger] = useState(0);
  const [details, setDetails] = useState("Group");
  const [speakers, setSpeakers] = useState([]);
  const [selectedSpkrId1, setSelectedSpkrId1] = useState(-1);
  const [selectedSpkrId2, setSelectedSpkrId2] = useState(-1);
  const [spkr1Transcripts, setSpkr1Transcripts] = useState([]);
  const [spkr2Transcripts, setSpkr2Transcripts] = useState([]);
  const [spkr1VideoMetrics, setSpkr1VideoMetrics] = useState([])
  const [spkr2VideoMetrics, setSpkr2VideoMetrics] = useState([])
  const [open, setOpen] = useState(true);
  const [selectedSpkralias, setSelectedSpkralias] = useState("");
  const { sessionDeviceId } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    // if (endTime === undefined) {
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
      const transcriptSub = activeSessionService.getTranscripts();
      //const transcriptSub = activeSessionService.getSessionDeviceTranscripts(sessionDeviceId, setTranscripts);

      transcriptSub.subscribe((e) => {
        if (Object.keys(e).length !== 0) {
          const data = e
            .filter(
              (t) => t.session_device_id === parseInt(sessionDeviceId, 10)
            )
            .sort((a, b) => (a.start_time > b.start_time ? 1 : -1));
          setTranscripts(data);
          // console.log(data,session, 'testing refresh still debugging ...')

          const sessionLen =
            Object.keys(session).length > 0 ? session.length : 0;
          //console.log("Start and end times changed default useeffect");
          setStartTime(Math.round(sessionLen * timeRange[0] * 100) / 100);
          setEndTime(Math.round(sessionLen * timeRange[1] * 100) / 100);
        }
      });

      subscriptions.push(transcriptSub);
    }


    if (videoMetrics.length <= 0) {
      const videoMetricsSub = activeSessionService.getVideoMetrics();
      videoMetricsSub.subscribe((e) => {
        if (Object.keys(e).length !== 0) {
          const data = e
            .filter(
              (v) => v.session_device_id === parseInt(sessionDeviceId, 10)
            )
            .sort((a, b) => (a.time_stamp > b.time_stamp ? 1 : -1));
          setVideoMetrics(data);
          // console.log(data,session, 'testing refresh still debugging ...')

          const sessionLen =
            Object.keys(session).length > 0 ? session.length : 0;
          //console.log("Start and end times changed default useeffect");
          setStartTime(Math.round(sessionLen * timeRange[0] * 100) / 100);
          setEndTime(Math.round(sessionLen * timeRange[1] * 100) / 100);
        }
      });

      subscriptions.push(videoMetricsSub);
    }


    // Refresh based on timeslider.
    setIntervalId(
      setInterval(() => {
        // console.log("Fetched onto pod-component");
        //ResetTimeRange(timeRange);
        if (session === undefined || !session.recording) {
          clearInterval(intervalId);
        }
      }, 2000)
    );

    // initialize the options toolbar
    let featuresArr = [
      "Emotional tone",
      "Analytic thinking",
      "Clout",
      "Authenticity",
      "Confusion",
      "Participation",
      "Social Impact",
      "Responsivity",
      "Internal Cohesion",
      "Newness",
      "Communication Density",
      "Attention Level",
      "Facial Emotions",
      "Object Focused On"
    ]
    initChecklistData(featuresArr, setShowFeatures)
    // initialize the components toolbar
    let boxArr = [
      "Timeline control",
      "Discussion timeline",
      "Keyword detection",
      "Discussion features",
      "Radar chart",
      "Participation",
      "Social Impact",
      "Responsivity",
      "Internal Cohesion",
      "Newness",
      "Communication Density",
      "Video Metrics"
    ]
    initChecklistData(boxArr, setShowBoxes)


    return () => {
      subscriptions.map((sub) => {
        if (sub.closed) {
          sub.unsubscribe();
        }
      });
      clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    const sessionLen = Object.keys(session).length > 0 ? session.length : 0;
    const sTime = Math.round(sessionLen * timeRange[0] * 100) / 100;
    const eTime = Math.round(sessionLen * timeRange[1] * 100) / 100;
    setStartTime(sTime);
    setEndTime(eTime);
    generateDisplayTranscripts(sTime, eTime);
    generateDisplayVideoMetrics(sTime, eTime);
  }, [startTime, endTime, transcripts, videoMetrics, timeRange]);

  useEffect(() => {
    if (displayTranscripts) {
      console.log("reloaded page - display transcripts");
      setSpeakerTranscripts();
    }

    if (displayVideoMetrics) {
      console.log("reloaded page - displayVideoMetrics")
      setSpeakerVideoMetrics()
    }


  }, [displayTranscripts, displayVideoMetrics, selectedSpkrId1, selectedSpkrId2, details]);

  useEffect(() => {
    if (trigger > 0) {
      console.log("reloaded page");
    }
  }, [trigger]);

  useEffect(() => {
    if (sessionDeviceId && session.id) getSpeakers();
    else setSpeakers([]);
    console.log("loaded speaker data");
  }, [sessionDeviceId, session]);

  // useEffect(() => {
  //   if (participantDisplayed.length > 0) {
  //     setSelectedParticipantData(participantDisplayed[0], participantDisplayed[1])
  //   }
  //   console.log("loaded displayed participant data");
  // }, [participantDisplayed]);



  //console.log(session, transcripts, '-', sessionDevice, '-', displayTranscripts, '-', startTime, '-', endTime, '-', 'session .......')

  // to initialize the checklist data structures
  const initChecklistData = (featuresArr, setFn) => {
    let valueInd = 0;
    let showFeats = [];
    for (const feature of featuresArr) {
      showFeats.push({ label: feature, value: valueInd, clicked: true });
      valueInd++;
    }
    setFn(showFeats);
  };

  const ResetTimeRange = (values) => {
    setTimeRange(values);
  };

  const setSpeakerTranscripts = () => {
    if (displayTranscripts.length) {
      setSpkr1Transcripts(
        displayTranscripts.reduce((values, transcript) => {
          
          if (transcript.speaker_id === selectedSpkrId1
          ){
            values.push(transcript);
          }
          return values;
        }, [])
      );
      setSpkr2Transcripts(
        displayTranscripts.reduce((values, transcript) => {
          if (transcript.speaker_id === selectedSpkrId2
          ){
            values.push(transcript);
         }
          return values;
        }, [])
      );
    } else {
      setSpkr1Transcripts([]);
      setSpkr2Transcripts([]);
    }
  };

  const setSpeakerVideoMetrics = () => {
    
    if (displayVideoMetrics.length) {
      let speakerAlias1 = getSpeakerAliasFromID(selectedSpkrId1)
      let speakerAlias2 = getSpeakerAliasFromID(selectedSpkrId2)
      setSpkr1VideoMetrics(
        displayVideoMetrics.reduce((values, videometrics) => {
          if (videometrics.student_username === speakerAlias1
          ){
            values.push(videometrics)
          }
          return values
        }, []),
      )
      setSpkr2VideoMetrics(
        displayVideoMetrics.reduce((values, videometrics) => {
          if (videometrics.student_username === speakerAlias2
          ){
            values.push(videometrics)  
          }
          return values
        }, []),
      )
    } else {
      setSpkr1VideoMetrics([])
      setSpkr2VideoMetrics([])
    }
  }
  const generateDisplayTranscripts = (s, e) => {
    setDisplayTranscripts(
      transcripts.filter((t) => t.start_time >= s && t.start_time <= e)
    );
  };

  const generateDisplayVideoMetrics = (s, e) => {
    setDisplayVideoMetrics(
      videoMetrics.filter((v) => v.time_stamp >= s && v.time_stamp <= e),
    )
  }

  const getSpeakerAliasFromID = (selectedSpkrId) => {
    if (selectedSpkrId !== -1) {
      const speaker = speakers.filter((s) => s.id === selectedSpkrId)
      if (speaker.length !== 0) {
        return speaker[0].alias
      }
    } else {
      return -1
    }
  }

  const navigateToSession = () => {
    navigate("/sessions/" + session.id);
  };

  const onSessionClosing = (isClosing) => {
    setSessionClosing(isClosing);
  };

  const seeAllTranscripts = () => {
    if (currentTranscript !== undefined) {
      navigate(
        "/sessions/" +
        session.id +
        "/pods/" +
        sessionDeviceId +
        "/transcripts?index=" +
        currentTranscript.id
      );
    } else {
      navigate(
        "/sessions/" + session.id + "/pods/" + sessionDeviceId + "/transcripts"
      );
    }
  };

  const loading = () => {
    return session === null || transcripts === null;
  };

  const getSpeakers = () => {
    const fetchData = new SessionService().getSessionDeviceSpeakers(
      session.id,
      sessionDeviceId
    );
    fetchData.then(
      (response) => {
        if (response.status === 200)
          response.json().then((jsonObj) => {
            const input = SpeakerModel.fromJsonList(jsonObj)
            if (input && input.length) {
              setSpeakers(input);
            }
          });
      },
      (apierror) => {
        console.log("podcomponent func getspeakers 1", apierror);
      }
    );
  };

  const removeDeviceFromSession = (deleteDevice = false) => {
    const fetchData = new SessionService().removeDeviceFromSession(
      session.id,
      sessionDeviceId,
      deleteDevice
    );
    fetchData.then(
      (response) => {
        if (response.status === 200) {
          closeDialog();
          if (deleteDevice) {
            navigateToSession();
          }
        }
      },
      (apierror) => {
        console.log("podcomponent func removedevicesession 1", apierror);
      }
    );
  };

  const onClickedTimeline = (transcript) => {
    setCurrentForm("Transcript");
    setCurrentTranscript(transcript);
  };

  const openDialog = (form) => {
    setDeleteDeviceToggle(false);
    setCurrentForm(form);
  };

  const closeDialog = () => {
    setCurrentForm("");
  };

  /*
    const toggleDeleteVal = (val) => {
        setDeleteDeviceToggle(!val);
        setTrigger(trigger + 1);
    }

    const toggleDeleteValFalse = () => {toggleDeleteVal(false)}
    */

  // toggles the clicked status of the data field that was clicked
  const handleCheck = (event, propStruct, propFn) => {
    let featTemp = propStruct;
    featTemp[event.option.value]["clicked"] =
      !featTemp[event.option.value]["clicked"];
    propFn(featTemp);
    setTrigger(trigger + 1);
  };

  // toggles for showFeatures
  const handleCheckFeats = (value, event) => {
    handleCheck(event, showFeatures, setShowFeatures);
    setRadarTrigger(radarTrigger + 1);
  };

  // toggles for showBoxes
  const handleCheckBoxes = (value, event) => {
    handleCheck(event, showBoxes, setShowBoxes);
  };

  const viewComparison = () => {
    setDetails("Comparison");
  };

  const viewIndividual = () => {
    setDetails("Individual");
  };

  const viewGroup = () => {
    setDetails("Group");
  }


  const loadSpeakerMetrics = (speakerId, speakrAlias) => {
    setSelectedSpkrId1(speakerId)
    setSelectedSpkralias(speakrAlias)
    setDetails("Individual");
  }

  return (
    <PodComponentPages
      sessionDevice={sessionDevice}
      navigateToSession={navigateToSession}
      setRange={ResetTimeRange}
      onClickedTimeline={onClickedTimeline}
      session={session}
      displayTranscripts={displayTranscripts}
      displayVideoMetrics={displayVideoMetrics}
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
      showFeatures={showFeatures}
      showBoxes={showBoxes}
      handleCheckFeats={handleCheckFeats}
      handleCheckBoxes={handleCheckBoxes}
      radarTrigger={radarTrigger}
      speakers={speakers}
      selectedSpkrId1={selectedSpkrId1}
      setSelectedSpkrId1={setSelectedSpkrId1}
      selectedSpkrId2={selectedSpkrId2}
      setSelectedSpkrId2={setSelectedSpkrId2}
      spkr1Transcripts={spkr1Transcripts}
      spkr2Transcripts={spkr2Transcripts}
      spkr1VideoMetrics={spkr1VideoMetrics}
      spkr2VideoMetrics={spkr2VideoMetrics}
      getSpeakerAliasFromID={getSpeakerAliasFromID}
      details={details}
      setDetails={setDetails}
      viewIndividual={viewIndividual}
      viewComparison={viewComparison}
      viewGroup={viewGroup}
      open={open}
      setOpen={setOpen}
      loadSpeakerMetrics={loadSpeakerMetrics}
      selectedSpkralias={selectedSpkralias}
    />
  );
}

export { PodComponent };
