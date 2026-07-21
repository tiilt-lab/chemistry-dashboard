import { Observable } from "rxjs";
import { DeviceService } from "../services/device-service";
import { SessionService } from "../services/session-service";
import { ActiveSessionService } from "../services/active-session-service";
import { SessionModel } from "../models/session";
import { SessionDeviceModel } from "../models/session-device";
import { DeviceModel } from "../models/device";
import { TranscriptModel } from "../models/transcript";
import { KeywordUsageModel } from "../models/keyword-usage";
import { SpeakerModel } from "../models/speaker";
import { useEffect, useState, useRef } from "react";
import { useNavigate, useOutletContext, useParams, useSearchParams } from "react-router-dom";
import { ApiService } from "../services/api-service";
import { PodComponentPages } from "./html-pages";

// The dashboard views live in the URL (?view=...&speaker=...) so they are
// linkable, bookmarkable, and reload/back-button safe. "Group" is the clean
// URL. Slugs <-> the legacy `details` state values.
const VIEW_SLUGS = {
  Group: "group",
  Comparison: "comparison",
  "Reflection Dashboard": "reflection",
  Individual: "individual",
};
const SLUG_VIEWS = Object.fromEntries(
  Object.entries(VIEW_SLUGS).map(([view, slug]) => [slug, view]),
);

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
  // Human-visible reason when the AI reflection can't load (LLM/api errors
  // used to fail silently — the toolbar button just did nothing).
  const [llmError, setLlmError] = useState("");
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
  // Participant whose AI narrative is still generating (inline banner, not a
  // blocking dialog); guards against stale responses landing after a switch.
  const [llmPendingFor, setLlmPendingFor] = useState("")
  const latestParticipantRequest = useRef("")
  const prefetchStarted = useRef(false)
  const { sessionId, sessionDeviceId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
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
      } else {
        // Direct URL / stale store: fetch the pod so per-run provenance
        // (posthoc_models) and metadata are available regardless of how the
        // page was reached.
        new SessionService()
          .getSessionDeviceForClient(sessionDeviceId)
          .then((r) => (r.status === 200 ? r.json() : null))
          .then((d) => d && setSessionDevice(SessionDeviceModel.fromJson(d)))
          .catch(() => {});
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
      "Session timeline",
      "Keyword detection",
      "Session features",
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
      // Switch the view immediately — metrics are already local; the AI
      // narrative streams in via the pending banner when not yet cached.
      latestParticipantRequest.current = participantIDReflectionDashboard
      setCurrentParticipant(participantIDReflectionDashboard)
      extractParticipantData(participantIDReflectionDashboard)
    }
  }, [participantIDReflectionDashboard])

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
    if (currentTranscript != null && currentTranscript.id != null) {
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
    if(details === "Reflection Dashboard"){
      return Object.keys(llmSessionAnalysis.current).length <= 0
    }else{
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
    setEditDraft(transcript && transcript.transcript ? transcript.transcript : "");
    // Editing is the default action for a clicked segment — the dialog
    // opens straight into the inline editor.
    setPodEditing(true);
  };

  // Human corrections from the transcript dialog: fix the text, or fix who
  // said it (same endpoints as the full transcripts page). Editing is
  // inline like a title rename: click the text, Enter/blur saves.
  const [editDraft, setEditDraft] = useState("");
  const [podEditing, setPodEditing] = useState(false);
  const roster = [...new Set(speakers.map((s) => s.alias).filter(Boolean))].sort();
  const tagCounts = transcripts.reduce((m, t) => {
    if (t.speaker_tag) m[t.speaker_tag] = (m[t.speaker_tag] || 0) + 1;
    return m;
  }, {});

  // Reassign any row by id (transcript panel); the dialog variant below
  // just targets the currently open transcript.
  const reassignTranscriptRow = async (transcriptId, alias, applyToTag, guest) => {
    const target = transcripts.find((t) => t.id === transcriptId);
    const oldTag = target ? target.speaker_tag : null;
    const res = await new ApiService().httpRequestCall(
      `api/v1/transcripts/${transcriptId}/reassign`, "POST",
      { alias, apply_to_tag: !!applyToTag, allow_guest: !!guest });
    if (res.status !== 200) return;
    setTranscripts(transcripts.map((row) => {
      const hit = applyToTag && oldTag
        ? row.speaker_tag === oldTag
        : row.id === transcriptId;
      return hit ? { ...row, speaker_tag: alias } : row;
    }));
    if (currentTranscript && currentTranscript.id === transcriptId) {
      setCurrentTranscript({ ...currentTranscript, speaker_tag: alias });
    }
    if (guest) getSpeakers();
  };

  const reassignTranscriptSpeaker = (alias, applyToTag, guest) => {
    if (!currentTranscript || currentTranscript.id == null) return;
    return reassignTranscriptRow(currentTranscript.id, alias, applyToTag, guest);
  };

  const saveTranscriptText = async () => {
    const t = currentTranscript;
    const clean = (editDraft || "").trim();
    if (!t || t.id == null || !clean || clean === t.transcript) {
      setPodEditing(false);
      setEditDraft(t && t.transcript ? t.transcript : "");
      return;
    }
    const res = await new ApiService().httpRequestCall(
      `api/v1/transcripts/${t.id}/edit_text`, "POST", { transcript: clean });
    if (res.status !== 200) return;
    setTranscripts(transcripts.map((row) =>
      row.id === t.id ? { ...row, transcript: clean } : row));
    setCurrentTranscript({ ...t, transcript: clean });
    setPodEditing(false);
  };

  // Inline correction from the transcript panel (id + text, no dialog).
  const editTranscriptText = async (transcriptId, text) => {
    const clean = (text || "").trim();
    const orig = transcripts.find((t) => t.id === transcriptId);
    if (!clean || !orig || orig.transcript === clean) return;
    const res = await new ApiService().httpRequestCall(
      `api/v1/transcripts/${transcriptId}/edit_text`, "POST", { transcript: clean });
    if (res.status !== 200) return;
    setTranscripts(transcripts.map((row) =>
      row.id === transcriptId ? { ...row, transcript: clean } : row));
    if (currentTranscript && currentTranscript.id === transcriptId) {
      setCurrentTranscript({ ...currentTranscript, transcript: clean });
    }
  };

  const cancelPodEdit = () => {
    setPodEditing(false);
    setEditDraft(currentTranscript && currentTranscript.transcript
      ? currentTranscript.transcript : "");
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

  // Reflect the open view into the URL. Group is the clean URL; Individual
  // carries the speaker id. No-op when the URL already matches, so the
  // param->state sync effect below can call the loaders without history spam.
  const writeViewParams = (view, speakerId) => {
    const next = new URLSearchParams();
    const slug = VIEW_SLUGS[view] || "group";
    if (slug !== "group") next.set("view", slug);
    if (slug === "individual" && speakerId != null)
      next.set("speaker", String(speakerId));
    if (next.toString() !== searchParams.toString()) setSearchParams(next);
  };

  const dashboardView = (view) => {
    setDetails(view);
    writeViewParams(view);
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

  // Non-blocking participant load: the synthesized metrics for EVERY
  // participant are already in memory (one fetch per pod), so a switch shows
  // the new student's metrics instantly; only the AI narrative may need a
  // ~30s Gemini generation, which renders as an inline pending banner instead
  // of a page-blocking dialog. `background` prefetches without touching what
  // is on screen (used to warm the remaining participants after first load).
  const extractParticipantData = async (participantId, background = false) => {
    let respObj = buildData("Participant level sesssion analysis", participantId, null, null)

    if (!respObj || Object.keys(respObj).length === 0) {
      return false;
    }

    if (participantId in llmSessionAnalysis.current) {
      if (!background) {
        selectedParticipantLLMAnalysis.current = llmSessionAnalysis.current[participantId]
        selectedParticipantSynthesizedData.current = respObj
        setSelectedMomentIdAndIndex([0, selectedParticipantSynthesizedData.current.participant_level_metric[0].windowid])
        setLlmPendingFor("")
      }
      return true
    }

    if (!background) {
      // Show this participant's metrics right away; AI panels go pending.
      selectedParticipantLLMAnalysis.current = null
      selectedParticipantSynthesizedData.current = respObj
      setSelectedMomentIdAndIndex([0, respObj.participant_level_metric[0].windowid])
      setLlmPendingFor(participantId)
    }

    try {
      const response = await new SessionService().getLLMFeedbackBasedOnMetrics(respObj);

      if (response.status === 200) {
        const jsonObj = await response.json()
        llmSessionAnalysis.current[participantId] = jsonObj.answer;
        // Only update the screen if the user is still on this participant.
        if (!background && latestParticipantRequest.current === participantId) {
          selectedParticipantLLMAnalysis.current = llmSessionAnalysis.current[participantId]
          loadprompthistory(participantId)
          setLlmPendingFor("")
        }
        return true
      } else {
        const errObj = await response.json().catch(() => ({}))
        if (!background) {
          setLlmPendingFor("")
          setLlmError(
            "Couldn't generate the AI reflection: " +
            (errObj.message || ("server returned " + response.status)),
          )
        }
        return false
      }
    } catch (error) {
      if (!background) {
        setLlmPendingFor("")
        setLlmError("Couldn't generate the AI reflection: " + error)
      }
      return false
    }
  }

  // After the first participant's reflection is up, quietly generate the
  // rest so switching students is instant (reports persist server-side too).
  // Cost control: prefetching every participant's AI reflection multiplied
  // each first dashboard open by group size (4-5x Gemini spend) and helped
  // exhaust the monthly cap. Reports generate on demand per participant now
  // (cached in the DB after the first time); flip to true only if budget
  // allows the instant-switching nicety.
  const PREFETCH_ALL_PARTICIPANTS = false
  const prefetchRemainingParticipants = async () => {
    if (!PREFETCH_ALL_PARTICIPANTS || prefetchStarted.current) return
    prefetchStarted.current = true
    for (const p of participants.current) {
      if (!(p in llmSessionAnalysis.current)) {
        try { await extractParticipantData(p, true) } catch { /* best effort */ }
      }
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
    if (participants.current.length === 0) {
      setLlmError(
        "No synthesized participant data for this pod yet — run a full analysis first.",
      )
      return
    }
    if (participants.current.length > 0) {
      const first = participants.current[0]
      latestParticipantRequest.current = first
      setCurrentParticipant(first)
      setDetails(view);
      writeViewParams(view);
      const actionstatus = await extractParticipantData(first)
      if (actionstatus) {
        // Warm the other participants in the background so switching between
        // students is instant.
        prefetchRemainingParticipants()
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
    writeViewParams("Individual", speakerId);
  }

  // URL -> state: open the view named in the URL (deep link, reload, back/
  // forward). Group/Comparison are plain state; Individual waits for the
  // speakers list; Reflection waits for the synthesized-metrics fetch to fill
  // participants (a ref, hence the short poll rather than a dependency).
  useEffect(() => {
    const view = SLUG_VIEWS[searchParams.get("view")] || "Group";
    if (view === details) return;
    if (view === "Group" || view === "Comparison") {
      setDetails(view);
      return;
    }
    if (view === "Individual") {
      const spId = parseInt(searchParams.get("speaker"), 10);
      const s = speakers.find((x) => x.id === spId);
      if (s) loadSpeakerMetrics(s.id, s.alias);
      else if (speakers.length > 0) setDetails("Individual");
      // speakers not loaded yet: effect re-runs when they arrive
      return;
    }
    // Reflection Dashboard
    if (participants.current.length > 0) {
      loadReflectiondashboard("Reflection Dashboard");
      return;
    }
    const t = setInterval(() => {
      if (participants.current.length > 0) {
        clearInterval(t);
        loadReflectiondashboard("Reflection Dashboard");
      }
    }, 400);
    const stop = setTimeout(() => clearInterval(t), 15000);
    return () => {
      clearInterval(t);
      clearTimeout(stop);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, speakers, details]);

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
      llmError={llmError}
      clearLlmError={() => setLlmError("")}
      currentTranscript={currentTranscript}
      roster={roster}
      tagCounts={tagCounts}
      editDraft={editDraft}
      setEditDraft={setEditDraft}
      podEditing={podEditing}
      setPodEditing={setPodEditing}
      cancelPodEdit={cancelPodEdit}
      saveTranscriptText={saveTranscriptText}
      editTranscriptText={editTranscriptText}
      reassignTranscriptRow={reassignTranscriptRow}
      reassignTranscriptSpeaker={reassignTranscriptSpeaker}
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
      llmPendingFor={llmPendingFor}
      selectedMomentIdAndIndex={selectedMomentIdAndIndex}
      setSelectedMomentIdAndIndex={setSelectedMomentIdAndIndex}
    />
  );
}

export { PodComponent };
