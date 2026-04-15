import { SessionService } from "../services/session-service";
import { ApiService } from '../services/api-service';
import { SpeakerModel } from "../models/speaker";
import { useEffect, useState, useRef, useReducer } from "react";
import { useNavigate, useOutletContext, useParams } from "react-router-dom";
import { PodComponentPages } from "./html-pages";
import { Satellite } from "lucide-react";

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
  const [participantIDReflectionDashboard, setParticipantIDRefectionDashboard] = useState("")
  const { sessionId, sessionDeviceId } = useParams();
  const synthesizedFeedbackMetrics = useRef(null);
  const participants = useRef([])
  const selectedParticipantSynthesizedData = useRef({})
  const selectedParticipantLLMAnalysis = useRef(null)
  const llmSessionAnalysis = useRef({})
  const promptHistory = useRef({})
  const [currentParticipant, setCurrentParticipant] = useState("")
  const promptResponses = useRef({})
  const [isThinking, setIsThinking] = useState(false)
  const [selectedMomentIdAndIndex, setSelectedMomentIdAndIndex] = useState(null);
  const [displayText, setDisplayText] = useState("")
  const heartbeatIntervalRef = useRef(null)

  const audiowebsocket = useRef(null)
  const videowebsocket = useRef(null)
  const navigate = useNavigate();
  const apiService = new ApiService()

  //Reducer and state for managing connection and streaming status
  const initialState = {
    audioSocketOpen: false,
    videoSocketOpen: false,
    audioSocketReady: false,
    videoSocketReady: false,
    audioProcessStarted: false,
    videoProcessStarted: false,
    audioProcessCompleted: false,
    videoProcessCompleted: false,
    audioSocketClosed: false,
    videoSocketClosed: false
  };

  function reducer(state, action) {
    switch (action.type) {
      case "AUDIO_SOCKET_OPEN":
        return { ...state, audioSocketOpen: action.payload };
      case "VIDEO_SOCKET_OPEN":
        return { ...state, videoSocketOpen: action.payload };
      case "AUDIO_SOCKET_READY":
        return { ...state, audioSocketReady: action.payload };  
      case "VIDEO_SOCKET_READY":
        return { ...state, videoSocketReady: action.payload };    
      case "AUDIO_PROCESSING_STARTED":
        return { ...state, audioProcessStarted: action.payload };
      case "VIDEO_PROCESSING_STARTED":
        return { ...state, videoProcessStarted: action.payload };  
      case "AUDIO_PROCESS_COMPLETED":
        return { ...state, audioProcessCompleted: action.payload };
      case "VIDEO_PROCESS_COMPLETED":
        return { ...state, videoProcessCompleted: action.payload };  
      case "AUDIO_SOCKET_CLOSED":
        return { ...state, audioSocketClosed: action.payload };
      case "VIDEO_SOCKET_CLOSED":
        return { ...state, videoSocketClosed: action.payload };  
      default:
        return state;
    }
  }
  const [state, dispatch] = useReducer(reducer, initialState);

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
    if (synthesizedFeedbackMetrics.current === null) {
      const fetchData = new SessionService().getSynthesizedFeedbackMetrics(sessionId, sessionDeviceId);
      fetchData.then(
        (response) => {
          if (response.status === 200)
            response.json().then((jsonObj) => {
              synthesizedFeedbackMetrics.current = jsonObj;
              participants.current = Object.keys(synthesizedFeedbackMetrics.current["participants_level"])
              console.log("Fetched synthesized feedback metrics onto pod component", jsonObj)
              console.log("Participants for reflection dashboard", participants.current)
            });
        },
        (apierror) => {
          console.log("podcomponent useEffect getSynthesizedFeedbackMetrics", apierror);
        }
      );
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
      setSpeakerTranscripts();
    }

    if (displayVideoMetrics) {
      setSpeakerVideoMetrics()
    }


  }, [displayTranscripts, displayVideoMetrics, selectedSpkrId1, selectedSpkrId2, details]);

  useEffect(() => {
    if (trigger > 0) {
    }
  }, [trigger]);

  useEffect(() => {
    if (sessionDeviceId && session.id) getSpeakers();
    else setSpeakers([]);
  }, [sessionDeviceId, session]);

  useEffect(() => {
    if (participantIDReflectionDashboard !== "") {
      let actionstatus = extractParticipantData(participantIDReflectionDashboard)
      if (actionstatus) {
        setCurrentParticipant(participantIDReflectionDashboard)
      }
    }
  }, [participantIDReflectionDashboard])

  useEffect(() => {
    let message = null
    if (state.audioSocketOpen) {
      message = {
        type: "Initialize_audio_processing_analytics",
        sessionid: sessionId,
        server_start:session.creation_date,
        keywords: session.keywords,
        sessiondeviceid: sessionDeviceId,
        speakers: speakers.map((sp) => { return {id:sp.id, alias:sp.alias} })
      }
      console.log("sending message")
      audiowebsocket.current.send(JSON.stringify(message))
    } else if (state.videoSocketOpen ) {
      message = {
        type: "Initialize_video_processing_analytics",
        sessionid: sessionId,
        server_start:session.creation_date,
        sessiondeviceid: sessionDeviceId,
        speakers: speakers.map((sp) => { return {id:sp.id, alias:sp.alias} })
      }
      videowebsocket.current.send(JSON.stringify(message))
    }


  }, [state.audioSocketOpen, state.videoSocketOpen])

  useEffect(() => {
    if (state.audioSocketReady) {
      audiowebsocket.current.send( JSON.stringify({ type: "start_posthoc_audio_processing"}));
    }else if(state.videoSocketReady){
      videowebsocket.current.send( JSON.stringify({ type: "start_posthoc_video_processing"}));
    }

  }, [state.audioSocketReady,state.videoSocketReady])

  useEffect(() => {
    if (state.audioProcessStarted || state.videoProcessStarted) {
      setCurrentForm("posthocanalytics");
      
      // start sending heartbeat till
      const clearHeartbeat = () => {
            if (heartbeatIntervalRef.current) {
                clearInterval(heartbeatIntervalRef.current);
                heartbeatIntervalRef.current = null;
            }
        };

        const sendHeartbeat = () => {
            if (audiowebsocket.current?.readyState === WebSocket.OPEN) {
                audiowebsocket.current.send(
                    JSON.stringify({ type: "heartbeat_from_posthoc_processing", key: "no key (posthoc processing)" })
                )
                console.log("sent heart beat")
            }else if(videowebsocket.current?.readyState === WebSocket.OPEN){
              videowebsocket.current.send(JSON.stringify({ type: "heartbeat_from_posthoc_processing", key: "no key (posthoc processing)" }))
            } else {
                clearHeartbeat();
            }
        };

        // Stop heartbeat immediately once processing is complete
        if (state.audioProcessCompleted || state.videoProcessCompleted) {
            clearHeartbeat();
            return;
        }

        sendHeartbeat(); // send immediately
        heartbeatIntervalRef.current = setInterval(sendHeartbeat, 20000);

        return () => {
            clearHeartbeat();
        };

    }

  }, [state.audioProcessStarted,state.videoProcessStarted,state.audioProcessCompleted,state.videoProcessCompleted])

  useEffect(() => {
    if (state.audioProcessCompleted) {
      setDisplayText("PostHoc Audio Analytics Processing Completed")
      setCurrentForm("success")
      audiowebsocket.current.close()
    }else if (state.videoProcessCompleted) {
      setDisplayText("PostHoc Video Analytics Processing Completed")
      setCurrentForm("success")
      videowebsocket.current.close()
    }
  }, [state.audioProcessCompleted, state.videoProcessCompleted])

  useEffect(() => {
    if (state.audioSocketClosed) {
      setCurrentForm("")
      if (audiowebsocket.current != null) {
        audiowebsocket.current.close()
        audiowebsocket.current = null
        console.log("Closed audio post hoc analytics processing ")
      }
    }else  if (state.videoSocketClosed) {
      setCurrentForm("")
      if (videowebsocket.current != null) {
        videowebsocket.current.close()
        videowebsocket.current = null
        console.log("Closed video post hoc analytics processing ")
      }
    }

  }, [state.audioSocketClosed,state.videoSocketClosed])


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
          ) {
            values.push(transcript);
          }
          return values;
        }, [])
      );
      setSpkr2Transcripts(
        displayTranscripts.reduce((values, transcript) => {
          if (transcript.speaker_id === selectedSpkrId2
          ) {
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
          ) {
            values.push(videometrics)
          }
          return values
        }, []),
      )
      setSpkr2VideoMetrics(
        displayVideoMetrics.reduce((values, videometrics) => {
          if (videometrics.student_username === speakerAlias2
          ) {
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

  const loading = (details) => {
    if (details === "Reflection Dashboard") {
      return Object.keys(llmSessionAnalysis.current).length <= 0
    } else {
      return session === null || transcripts === null;
    }
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

  const dashboardView = (view) => {
    setDetails(view);
  };

  const buildData = (reporttype, participantId, defaultQuestionId, question) => {
    let retObj = {}
    if (reporttype === "Participant level sesssion analysis") {
      retObj["participant_name"] = participantId
      retObj["sessionid"] = sessionId
      retObj["sessiondeviceid"] = sessionDeviceId
      retObj["retrieve_existing_report"] = "true"
      retObj["participant_level_metric"] = synthesizedFeedbackMetrics.current["participants_level"][participantId]
      retObj["session_level_metric"] = synthesizedFeedbackMetrics.current["session_level"][participantId]
      retObj["group_level_metric"] = synthesizedFeedbackMetrics.current["group_level"]
    } else if (reporttype === "interactive prompting") {
      retObj["participant_name"] = participantId
      retObj["sessionid"] = sessionId
      retObj["sessiondeviceid"] = sessionDeviceId
      retObj["retrieve_existing_answer"] = "true"
      retObj["default_question_id"] = defaultQuestionId
      retObj["question"] = question
      retObj["window_level_metric"] = synthesizedFeedbackMetrics.current["window_level"]
      retObj["session_level_metric"] = synthesizedFeedbackMetrics.current["session_level"]
      retObj["group_level_metric"] = synthesizedFeedbackMetrics.current["group_level"]
    }

    return retObj
  }

  const extractParticipantData = async (participantId) => {
    let respObj = buildData("Participant level sesssion analysis", participantId, null, null)

    if (!respObj || Object.keys(respObj).length === 0) {
      return false;
    }

    if (participantId in llmSessionAnalysis.current) {
      selectedParticipantLLMAnalysis.current = llmSessionAnalysis.current[participantId]
      selectedParticipantSynthesizedData.current = respObj
      setSelectedMomentIdAndIndex([0, selectedParticipantSynthesizedData.current.participant_level_metric[0].windowid])
      return true
    }

    try {
      setDisplayText("Please wait ...")
      setCurrentForm("awaitingllmresponse");
      const response = await new SessionService().getLLMFeedbackBasedOnMetrics(respObj);

      if (response.status === 200) {
        const jsonObj = await response.json()
        llmSessionAnalysis.current[participantId] = jsonObj.answer;
        selectedParticipantLLMAnalysis.current = llmSessionAnalysis.current[participantId]
        selectedParticipantSynthesizedData.current = respObj
        loadprompthistory(participantId)
        setSelectedMomentIdAndIndex([0, selectedParticipantSynthesizedData.current.participant_level_metric[0].windowid])
        setCurrentForm("");
        return true
      } else if (response.status === 400) {
        console.log("LLM api response", response.message)
        setCurrentForm("")
        return false
      }
    } catch (error) {
      console.log(
        "podcomponent loadReflectiondashboard",
        error,
      )
      return false
    }
  }

  const loadprompthistory = async (participantId) => {
    try {
      const response = await new SessionService().get_llm_question_answer_interactions(sessionId, sessionDeviceId, participantId);

      if (response.status === 200) {
        const jsonObj = await response.json()
        promptHistory.current[participantId] = jsonObj
      } else if (response.status === 400) {
        // console.log("LLM api response", response.message)
      }
    } catch (error) {
      console.log(
        "podcomponent loadprompthistory",
        error,
      )
    }
  }

  const loadReflectiondashboard = async (view) => {
    if (participants.current.length > 0) {
      let actionstatus = await extractParticipantData(participants.current[0])
      if (actionstatus) {
        setCurrentParticipant(participants.current[0])
        setDetails(view);
      }
    }
  };

  const interactivePromptFnc = async (participantId, default_question_id, question) => {
    let respObj = buildData("interactive prompting", participantId, default_question_id, question)
    let existingPrompt = null
    if (participantId in promptHistory.current) {
      existingPrompt = promptHistory.current[participantId].find(p => (default_question_id !== -1 && p?.default_question_id === default_question_id)) ?? null;
    }

    if (existingPrompt !== null) {
      if (participantId in promptResponses.current) {
        promptResponses.current[participantId].push([question, existingPrompt.answer])
      } else {
        promptResponses.current[participantId] = [[question, existingPrompt.answer]]
      }

    } else {
      try {

        const response = await new SessionService().getLLMPromptResponse(respObj);

        if (response.status === 200) {
          const jsonObj = await response.json()
          if (participantId in promptResponses.current) {
            promptResponses.current[participantId].push([question, jsonObj.answer])
          } else {
            promptResponses.current[participantId] = [[question, jsonObj.answer]]
          }
          // console.log(jsonObj.answer)
        } else if (response.status === 400) {
          console.log("LLM api response", response.message)
        }
      } catch (error) {
        console.log(
          "podcomponent interactivePromptFnc",
          error,
        )
      }
    }
  }


  const loadSpeakerMetrics = (speakerId, speakrAlias) => {
    setSelectedSpkrId1(speakerId)
    setSelectedSpkralias(speakrAlias)
    setDetails("Individual");
  }

  const connecttoaudioservice = () => {
    if (!state.audioSocketOpen) {
      audiowebsocket.current = new WebSocket(apiService.getAudioPosthocWebsocketEndpoint())
      connect_audio_posthoc_processor_service()
    } 

  }

  const connecttovideoservice = (speakerId, speakrAlias) => {
    if (!state.videoSocketOpen) {
      videowebsocket.current = new WebSocket(apiService.getVideoPosthocWebsocketEndpoint())
      connect_video_processor_service()
    } 
  }

  // Connects to processor websocket server.
  const connect_audio_posthoc_processor_service = () => {
    audiowebsocket.current.binaryType = "arraybuffer"

    audiowebsocket.current.onopen = (e) => {
      dispatch({ type: "AUDIO_SOCKET_OPEN", payload: true })
    };

    audiowebsocket.current.onmessage = (e) => {
      if (typeof e.data === 'string') {
        const message = JSON.parse(e.data);
        if (message['type'] === 'init posthoc analytics completed') {
          dispatch({ type: "AUDIO_SOCKET_READY", payload: true })
        }else if (message['type'] === 'audio posthoc analytics started') {
          setDisplayText(message['message'])
          dispatch({ type: "AUDIO_PROCESSING_STARTED", payload: true })
        }else if (message['type'] === 'process_completed') {
          dispatch({ type: "AUDIO_PROCESS_COMPLETED", payload: true })
        }
        else if (message['type'] === 'error') {
          setDisplayText(message['message'])
          console.log("message from the audio server is " + message["message"])
          setCurrentForm("audiowebsocketerror")
        }
      }
    };

    audiowebsocket.current.onclose = e => {
      dispatch({ type: "AUDIO_SOCKET_CLOSED", payload: true })
      console.log('Disconnected]');
    };

  }

  // Connects to processor websocket server.
  const connect_video_processor_service = () => {
    videowebsocket.current.binaryType = "arraybuffer"

    videowebsocket.current.onopen = (e) => {
      dispatch({ type: "VIDEO_SOCKET_OPEN", payload: true })
    };

    videowebsocket.current.onmessage = (e) => {
      if (typeof e.data === 'string') {
        const message = JSON.parse(e.data);
        if (message['type'] === 'init posthoc analytics completed') {
          dispatch({ type: "VIDEO_SOCKET_READY", payload: true })
        }else if (message['type'] === 'video posthoc analytics started') {
          setDisplayText(message['message'])
          dispatch({ type: "VIDEO_PROCESSING_STARTED", payload: true })
        }else if (message['type'] === 'process_completed') {
          dispatch({ type: "VIDEO_PROCESS_COMPLETED", payload: true })
        }
        else if (message['type'] === 'error') {
          setDisplayText(message['message'])
          console.log("message from the video server is " + message["message"])
          setCurrentForm("videowebsocketerror")
        }
      }
    };

    videowebsocket.current.onclose = e => {
      dispatch({ type: "VIDEO_SOCKET_CLOSED", payload: true })
      console.log('Disconnected]');
    };

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
      dashboardView={dashboardView}
      open={open}
      setOpen={setOpen}
      loadSpeakerMetrics={loadSpeakerMetrics}
      selectedSpkralias={selectedSpkralias}
      loadReflectiondashboard={loadReflectiondashboard}
      participants={participants.current}
      selectedParticipantLLMAnalysis={selectedParticipantLLMAnalysis.current}
      selectedParticipantSynthesizedData={selectedParticipantSynthesizedData.current}
      interactivePromptFnc={interactivePromptFnc}
      promptResponses={promptResponses.current}
      isThinking={isThinking}
      setIsThinking={setIsThinking}
      setParticipantIDRefectionDashboard={setParticipantIDRefectionDashboard}
      currentParticipant={currentParticipant}
      selectedMomentIdAndIndex={selectedMomentIdAndIndex}
      setSelectedMomentIdAndIndex={setSelectedMomentIdAndIndex}

      //Process audio analytics 
      connecttoaudioservice={connecttoaudioservice}
      connecttovideoservice={connecttovideoservice}
      displayText = {displayText}

    />
  );
}

export { PodComponent };
