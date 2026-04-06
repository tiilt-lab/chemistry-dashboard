
import { useEffect, useRef, useState, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom"
import { ExpertRatingPage } from "./html-pages";
import { AuthService } from "../services/auth-service"
import { SessionService } from "../services/session-service";
import { RaterModel } from "../models/rater"
import { SessionModel } from "../models/session";
import { SessionDeviceModel } from "../models/session-device";
import { SpeakerModel } from "../models/speaker";

const likertOptions = [1, 2, 3, 4, 5];
const evaluaion_one = [
  ["Interpretability", "This dashboard makes the collaboration patterns easy to understand."],
  ["Usefulness for feedback", "This Feedbacks would help a learner reflect on and improve their collaboration."],
  ["Clarity", "The information presented in the dashboard is clear and easy to follow."],
  ["Actionability", "Interacting with this dashboard help learners determine actionable next steps."],
  ["Confidence in interpretation", "I can confidently rely on the  information provided in this dashboard to judge the learner’s/my collaboration pattern."]
]

const evaluaion_two = [
  ["Data modality", "The integration of different modal metric of impact on the quality of interpretation/synthesis."],
  ["Complementarity of Signals", "The feedback draws on classes of metrics that reinforce or support the same interpretation."],
  ["Contextual Interpretation", "The feedback is contextualized by interpreting a collaboration indicator in relation to one or more other collaboration indicators, rather than in isolation."],
  ["Relational Reasoning", "The feedback reflects how one collaboration indicator/behavior may influence or be associated with another."],
  ["Coverage ", "The feedback captures a broad range of behaviors rather than focusing narrowly on one aspect of collaboration."]
]

const evaluaion_three = [
  ["Claims Accuracy", "The feedback includes claims that are not clearly supported by the data."],
  ["Evidence Traceability", "The feedback clearly links its conclusions to specific elements of the data."],
  ["Consistency", "The feedback is internally consistent and does not contain contradictions."],
  ["Sepcifity", "The feedback provides specific, data-grounded insights rather than vague statements."],
  ["Trustworthiness", "I would trust this feedback as a reliable interpretation of the data."]
]
function ExpertRatingComponent() {

  const [expertDetail, setExpertDetail] = useState(null)
  const [nextPage, setNextPage] = useState("reportoptionpage")
  const [selectedItemForRating, setSelectedItemForRating] = useState(-1)
  const [itemsForRating, setItemsForRating] = useState(["Dashboard Option One", "Dashboard Option Two"])

  const pageTitle = useRef("Expert Rating")
  const session = useRef(null)
  const [currentForm, setCurrentForm] = useState("")
  const [evaluatorType, setEvaluatorType] = useState("")
  const [aliasExpertId, setAliasExpertId] = useState("")
  const [evaluationOption, setEvaluationOption] = useState([])
  const [feedbackParameters, setFeedbackParameters] = useState([])
  const [showAlert, setShowAlert] = useState(false)
  const [alertMessage, setAlertMessage] = useState("")
  const [notes, setNotes] = useState("");
  const [ratings, setRatings] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [sessionId, setSessionId] = useState(-1)
  const [sessionDeviceId, setSessionDeviceId] = useState(-1)
  const [sessionDevice, setSessionDevice] = useState(null)
  const [timeRange, setTimeRange] = useState([0, 1])

  const [transcripts, setTranscripts] = useState(null)
  const [videoMetrics, setVideoMetrics] = useState(null)
  const [session1Transcripts, setSession1Transcripts] = useState([]);
  const [session1VideoMetrics, setSession1VideoMetrics] = useState([])
  const [transcriptDoneLoading, setTranscriptDoneLoading] = useState(false);
  const [videoMetricDoneLoading, setVideoMetricDoneLoading] = useState(false);
  const [reflectionDashboardDoneLoading, setReflectionDashboardDoneLoading] = useState(false);
  const [dashboardPage, setDashboardPage] = useState("")
  const [startTime, setStartTime] = useState()
  const [endTime, setEndTime] = useState()
  const [details, setDetails] = useState("Individual")
  const [currentTranscript, setCurrentTranscript] = useState(null)
  const [showFeatures, setShowFeatures] = useState([])
  const [showBoxes, setShowBoxes] = useState([])

  const synthesizedFeedbackMetrics = useRef(null);
  const llmSessionAnalysis = useRef(null)
  const promptHistory = useRef({})
  const promptResponses = useRef({})
  const synthesizedData = useRef({})
   const [selectedMomentIdAndIndex, setSelectedMomentIdAndIndex] = useState(null);
  const [sessionNameForReflecDashboard, setSessionNameForReflecDashboard] = useState("")
  const [groupNameForReflecDashboard, setGroupNameForReflecDashboard] = useState("")
  const [isThinking, setIsThinking] = useState(false)

  const navigate = useNavigate()
  const sessionService = new SessionService()
  const authService = new AuthService()

  useEffect(() => {
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
  }, []);

  // first useEffect to be called one the evalutor class is selected
  useEffect(() => {
    if (evaluatorType === "student" && aliasExpertId !== "") {
      setEvaluationOption(evaluaion_one)
      setFeedbackParameters([158, 443, "dklee1004"])
      setRatings(Object.fromEntries(evaluaion_one.map((item) => [item[0], 0])))
      setNextPage("dashboardratingpage")

    } else if (evaluatorType === "expert" && aliasExpertId !== "") {
      verifyExpertId(aliasExpertId)

    }
  }, [evaluatorType, aliasExpertId])

  useEffect(() => {
    if (selectedItemForRating !== -1 && sessionId !== -1) {
      if (selectedItemForRating === "Dashboard Option One") {
        fetchTranscript(sessionId, feedbackParameters[1], feedbackParameters[2], setTranscripts)
        fetchVideoMetric(sessionId, feedbackParameters[1], feedbackParameters[2], setVideoMetrics)
      } else if (selectedItemForRating === "Dashboard Option Two") {
        loadReflectiondashboard(feedbackParameters[0],feedbackParameters[1],feedbackParameters[2])
         setDashboardPage("option two dashboard")

      }
    }
  }, [selectedItemForRating, sessionId])

  useEffect(() => {
    if (transcripts !== null && videoMetrics !== null) {
      const sessionLen = Object.keys(session.current).length > 0 ? session.current.length : 0
      const sTime = Math.round(sessionLen * timeRange[0] * 100) / 100
      const eTime = Math.round(sessionLen * timeRange[1] * 100) / 100
      setStartTime(sTime)
      setEndTime(eTime)

      generateDisplayTranscripts(transcripts, sTime, eTime)
      generateDisplayVideoMetrics(videoMetrics, sTime, eTime)
    }

  }, [transcripts, videoMetrics]);

  useEffect(() => {
    if (transcriptDoneLoading && videoMetricDoneLoading) {
      setDashboardPage("option one dashboard")
    }
  }, [transcriptDoneLoading, videoMetricDoneLoading])

  const completedCount = useMemo(
    () => Object.values(ratings).filter((value) => value > 0).length,
    [ratings]
  );


  // ___________________________________________________________ 
  //  STEP1: Clicking the  continue buttion   call this function to verify the selections and input              
  // --------------------------------------------------------

  const getUserParameters = (evaluatorType, alias_expertid) => {
    if (evaluatorType === '') {
      setAlertMessage("Please Select Your Role");
      setShowAlert(true);
      document.getElementById("evaluaortype").focus();
    } else if (alias_expertid === '') {
      setAlertMessage("Please Enter Your Expert ID");
      setShowAlert(true);
      document.getElementById("expertid").focus();
    } else {
      setAliasExpertId(alias_expertid)
    }
  }

  // ___________________________________________________________ 
  //   STEP2: This is called to authenticate the username, fetch user data and call load session           
  // --------------------------------------------------------

  const verifyExpertId = async (expertid) => {
    const fetchData = authService.getRaterDetailByExpertId(expertid)
    fetchData
      .then(
        (response) => {
          if (response.status === 200) {
            response.json().then((jsonObj) => {
              const expert_data = RaterModel.fromJson(jsonObj)
              setExpertDetail(expert_data)
            })
          } else {
            setAlertMessage("Invalid Expert ID");
            setShowAlert(true);
          }
        },
        (apierror) => {
          console.log(
            "Expert Rating: verifyExpertId 1 ",
            apierror,
          )
        },
      )
  }

  const loadDashboard = (selecteditem) => {
    loadSession(feedbackParameters[0])
    loadSessionDevice(feedbackParameters[1])
    setSelectedItemForRating(selecteditem)
  }

  const loadSession = (sessionid) => {
    const fetchData = sessionService.getSessionById(sessionid)
    fetchData
      .then(
        (response) => {
          if (response.status === 200) {
            response.json().then((jsonArrayObj) => {
              const session_data = SessionModel.fromJson(jsonArrayObj)

              session.current = session_data
              pageTitle.current = session_data.name
              setSessionId(session_data.id);
              // setReload(reload + 1)
            })
          } else {
            setAlertMessage("No Previous Sessions Found for this User");
            setShowAlert(true);
          }
        },
        (apierror) => {
          console.log(
            "Student dashboard func: loadSession 1 ",
            apierror,
          )
        },
      )
  }

  const loadSessionDevice = (session_device_id) => {
    const fetchData = sessionService.getSessionDeviceForClient(session_device_id)
    fetchData
      .then(
        (response) => {
          if (response.status === 200) {
            response.json().then((jsonObj) => {
              const session_device = SessionDeviceModel.fromJson(jsonObj)
              setSessionDevice(session_device)
              setSessionDeviceId(session_device.id);
            })
          } else {
            setAlertMessage("No Previous Sessions Found for this User");
            setShowAlert(true);
          }
        },
        (apierror) => {
          console.log(
            "Student dashboard func: loadSession 1 ",
            apierror,
          )
        },
      )
  }

  const fetchTranscript = async (sessionId, deviceId, username, setMetric) => {
    try {
      let response = null
      response = await sessionService.getSessionDeviceTranscriptsByAlias(sessionId, deviceId, username)

      if (response !== null && response.status === 200) {
        const jsonObj = await response.json()
        const fetched_trancript_metrics = jsonObj.map((trancript_metrics) => {
          return { ...trancript_metrics['transcript'], speaker_metrics: trancript_metrics['speaker_metrics'] }
        })

        setMetric(fetched_trancript_metrics)
      } else if (response !== null && (response.status === 400 || response.status === 401)) {
        console.log(response, "no transcript obj")
      }
    } catch (error) {
      console.log(
        "byod-join-component error func : fetch transcript",
        error,
      )
    }
  }

  const fetchVideoMetric = async (sessionId, deviceId, username, setMetric) => {
    try {
      let response = null
      response = await sessionService.getSessionDeviceVideoMetricsByAlias(sessionId, deviceId, username)

      if (response !== null && response.status === 200) {
        const fetched_video_metrics = await response.json()

        setMetric(fetched_video_metrics)
      } else if (response.status === 400 || response.status === 401) {
        console.log(response, "no videometrics obj")
      }
    } catch (error) {
      console.log(
        "byod-join-component error func : fetch video metrics",
        error,
      )
    }
  }

  const generateDisplayTranscripts = (transcripts, s, e) => {
    setSession1Transcripts(
      transcripts.filter((t) => t.start_time >= s && t.start_time <= e),
    )
    setTranscriptDoneLoading(true);
  }

  const generateDisplayVideoMetrics = (videoMetrics, s, e) => {
    setSession1VideoMetrics(
      videoMetrics.filter((v) => v.time_stamp >= s && v.time_stamp <= e),
    )
    setVideoMetricDoneLoading(true);
  }

  ///------------------------------------------------------------------------//
  //Dashboard option two implementation
  //-----------------------------------------------------------------------//

  const loadReflectiondashboard = async (sessionid,deviceid,username) => {
    setReflectionDashboardDoneLoading(false)
    let actionstatus = await extractParticipantData(sessionid,deviceid,username)
    if (actionstatus) {
      setSessionNameForReflecDashboard(session.current?.name)
      setGroupNameForReflecDashboard(sessionDevice?.name)
      setReflectionDashboardDoneLoading(true)
    }

  };


  const extractParticipantData = async (sessionid,deviceId,username) => {
    const resp = await loadSynthesizedMetric(sessionid,deviceId)

    let respObj = buildData("Participant level sesssion analysis", sessionid, deviceId,username, null, null)
    if (Object.keys(respObj).length === 0 || resp === false) {
      return false;
    }

    const ret = await loadLLMAnalytics(respObj)

    if (ret) {
      synthesizedData.current = respObj
      await loadprompthistory(sessionid,deviceId,username)
      setSelectedMomentIdAndIndex([0, synthesizedData.current.participant_level_metric[0].windowid])
    } 
    
    return ret
    
  }

  const interactivePromptFnc = async (selSessionId, selSessionDeviceId, default_question_id, question) => {
    let respObj = buildData("interactive prompting", selSessionId, selSessionDeviceId, feedbackParameters[2],default_question_id, question)
    let existingPrompt = null
    if (promptHistory.current.hasOwnProperty(selSessionId) && promptHistory.current[selSessionId].hasOwnProperty(selSessionDeviceId)) {
      existingPrompt = promptHistory.current[selSessionId][selSessionDeviceId].find(p => (default_question_id !== -1 && p?.default_question_id === default_question_id)) ?? null;
    }

    if (existingPrompt !== null) {
      if (promptResponses.current.hasOwnProperty(selSessionId) && promptResponses.current[selSessionId].hasOwnProperty(selSessionDeviceId)) {
        promptResponses.current[selSessionId][selSessionDeviceId].push([question, existingPrompt.answer])
      } else if (promptResponses.current.hasOwnProperty(selSessionId)) {
        promptResponses.current[selSessionId][selSessionDeviceId] = [[question, existingPrompt.answer]]
      } else {
        promptResponses.current[selSessionId] = {
          [selSessionDeviceId]: [[question, existingPrompt.answer]]
        }
      }

    } else {
      try {

        const response = await new SessionService().getLLMPromptResponse(respObj);

        if (response.status === 200) {
          const jsonObj = await response.json()

          if (promptResponses.current.hasOwnProperty(selSessionId) && promptResponses.current[selSessionId].hasOwnProperty(selSessionDeviceId)) {
            promptResponses.current[selSessionId][selSessionDeviceId].push([question, jsonObj.answer])
          } else if (promptResponses.current.hasOwnProperty(selSessionId)) {
            promptResponses.current[selSessionId][selSessionDeviceId] = [[question, jsonObj.answer]]
          } else {
            promptResponses.current[selSessionId] = {
              [selSessionDeviceId]: [[question, jsonObj.answer]]
            }
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

  const buildData = (reporttype, sessionId, deviceId,username, defaultQuestionId, question) => {
    let retObj = {}
    if (synthesizedFeedbackMetrics.current ) {
      if (reporttype === "Participant level sesssion analysis") {
        retObj["participant_name"] = username
        retObj["sessionid"] = sessionId
        retObj["sessiondeviceid"] = deviceId
        retObj["retrieve_existing_report"] = "true"
        retObj["participant_level_metric"] = synthesizedFeedbackMetrics.current["participants_level"][username]
        retObj["session_level_metric"] = synthesizedFeedbackMetrics.current["session_level"][username]
        retObj["group_level_metric"] = synthesizedFeedbackMetrics.current["group_level"]
      } else if (reporttype === "interactive prompting") {
        retObj["participant_name"] = username
        retObj["sessionid"] = sessionId
        retObj["sessiondeviceid"] = deviceId
        retObj["retrieve_existing_answer"] = "true"
        retObj["default_question_id"] = defaultQuestionId
        retObj["question"] = question
        retObj["window_level_metric"] = synthesizedFeedbackMetrics.current["window_level"]
        retObj["session_level_metric"] = synthesizedFeedbackMetrics.current["session_level"]
        retObj["group_level_metric"] = synthesizedFeedbackMetrics.current["group_level"]
      }
    }
    return retObj
  }

  const loadSynthesizedMetric = async (sessionid,deviceId) => {
    const data = await getSynthesizedMetric(sessionid,deviceId)
    if (data === null) {
      return false
    }

    synthesizedFeedbackMetrics.current = data
      
    return true
  }

  const loadLLMAnalytics = async (respObj) => {

    const analysis = await getLLMAnalytics(respObj)
    if (analysis === null) {
      return false
    }

    llmSessionAnalysis.current = analysis

    return true
  }


  const loadprompthistory = async (sessionid,deviceid,username) => {
    if (!promptHistory.current.hasOwnProperty(sessionid)) {
      const prompt = await getPrompthistory(sessionid,deviceid,username)

      if (prompt === null) {
        return false
      }

      promptHistory.current[sessionid] = {
        [deviceid]: prompt
      }
    } else {
      if (!promptHistory.current[sessionid].hasOwnProperty(deviceid)) {

        const prompt = await getPrompthistory(sessionid,deviceid,username)
        if (prompt === null) {
          return false
        }

        promptHistory.current[sessionid][deviceid] = prompt

      }

    }
    return true
  }


  const getSynthesizedMetric = async (sessionid,deviceId) => {
    try {
      const response = await new SessionService().getSynthesizedFeedbackMetrics(sessionid, deviceId);
      if (response.status === 200) {
        const jsonObj = response.json()
        return jsonObj;
      } else {
        return null
      }
    } catch (error) {
      console.log(
        "student dashboard getSynthesizedMetric",
        error,
      )
      return null
    }
  }

  const getLLMAnalytics = async (respObj) => {
    try {
      const response = await new SessionService().getLLMFeedbackBasedOnMetrics(respObj);

      if (response.status === 200) {
        const jsonObj = await response.json()
        return jsonObj.answer
      } else if (response.status === 400) {
        console.log("LLM api response", response.message)
        return null
      }
    } catch (error) {
      console.log(
        "student dashboard loadReflectiondashboard",
        error,
      )
      return null
    }
  }

  const getPrompthistory = async (sessionid, deviceId,username) => {
    try {
      const response = await new SessionService().get_llm_question_answer_interactions(sessionid, deviceId, username);

      if (response.status === 200) {
        const jsonObj = await response.json()
        return jsonObj
      } else if (response.status === 400) {
        return null
      }
    } catch (error) {
      console.log(
        "student dashboard loadprompthistory",
        error,
      )
      return null
    }
  }


  ///------------------------------------------------------------------------//
  // END OF IMPLEMENTATION FOR THE REFLECTION DASHBOARD 
  //-----------------------------------------------------------------------//

  const handleRate = (criterion, value) => {
    setRatings((prev) => ({ ...prev, [criterion]: value }));
    setSubmitted(false);
  };

  const ResetTimeRange = (values) => {
    if (session.current !== null) {
      const sessionLen =
        Object.keys(session.current).length > 0 ? session.current.length : 0
      setTimeRange(values)
      const start = Math.round(sessionLen * values[0] * 100) / 100
      const end = Math.round(sessionLen * values[1] * 100) / 100
      setStartTime(start)
      setEndTime(end)
      generateDisplayTranscripts(session1Transcripts, start, end)
      generateDisplayVideoMetrics(session1VideoMetrics, start, end)
    }
  }

  const handleSubmit = (allComplete) => {
    // e.preventDefault();
    if (!allComplete) return;

    const payload = {
      selectedItemForRating,
      ratings,
      notes,
    };

    console.log("Submitted rating form:", payload);
    setSubmitted(true);
  };

  const seeAllTranscripts = () => {
    if (Object.keys(currentTranscript) > 0 && sessionDevice !== null) {
      setCurrentForm("gottoselectedtranscript")
    } else if (sessionDevice !== null) {
      setCurrentForm("gototranscript")
    }
  }

  const closeDialog = () => {
    setCurrentForm("")
  }
  const navigateToLogin = (confirmed = false) => {
    return navigate("/")
  }

  // const loading = () => {
  //   return session.current === null || transcripts.length === 0
  // }

  const initChecklistData = (featuresArr, setFn) => {
    let valueInd = 0
    let showFeats = []
    for (const feature of featuresArr) {
      showFeats.push({ label: feature, value: valueInd, clicked: true })
      valueInd++
    }
    setFn(showFeats)
  }

  const closeAlert = () => {
    setShowAlert(false)
  }

  const onClickedTimeline = (transcript) => {
    setCurrentForm("Transcript")
    setCurrentTranscript(transcript)
  }

  const onClickedKeyword = (transcript) => {
    setCurrentTranscript(transcript)
    setCurrentForm("gottoselectedtranscript")
  }

  return (
    <ExpertRatingPage
      currentForm={currentForm}
      closeDialog={closeDialog}
      nextPage={nextPage}
      pageTitle={pageTitle.current}
      navigateToLogin={navigateToLogin}
      setShowAlert={setShowAlert}
      showAlert={showAlert}
      closeAlert={closeAlert}
      alertMessage={alertMessage}
      getUserParameters={getUserParameters}
      // loading={loading}
      expertDetail={expertDetail}
      itemsForRating={itemsForRating}
      evaluatorType={evaluatorType}
      setEvaluatorType={setEvaluatorType}
      loadDashboard={loadDashboard}
      dashboardPage={dashboardPage}
      session1Transcripts={session1Transcripts}
      session1VideoMetrics={session1VideoMetrics}
      transcriptDoneLoading={transcriptDoneLoading}
      videoMetricDoneLoading={videoMetricDoneLoading}
      startTime={startTime}
      endTime={endTime}
      details={details}
      session={session.current}
      sessionDevice={sessionDevice}
      setRange={ResetTimeRange}
      onClickedTimeline={onClickedTimeline}
      onClickedKeyword={onClickedKeyword}
      showFeatures={showFeatures}
      showBoxes={showBoxes}
      seeAllTranscripts={seeAllTranscripts}
      currentTranscript={currentTranscript}
      setCurrentForm={setCurrentForm}
      reflectionDashboardDoneLoading={reflectionDashboardDoneLoading}

      llmSessionAnalysis = {llmSessionAnalysis.current}
      synthesizedData = {synthesizedData.current}
      promptResponses = {promptResponses.current}
      setSelectedMomentIdAndIndex = {setSelectedMomentIdAndIndex}
      selectedMomentIdAndIndex = {selectedMomentIdAndIndex}
      sessionNameForReflecDashboard = {sessionNameForReflecDashboard}
      groupNameForReflecDashboard = {groupNameForReflecDashboard}
      interactivePromptFnc = {interactivePromptFnc}
      isThinking={isThinking}
      setIsThinking={setIsThinking}
      sessionId = {sessionId}
      sessionDeviceId = {sessionDeviceId}

      //left pane props
      selectedItemForRating={selectedItemForRating}
      setSelectedItemForRating={setSelectedItemForRating}
      evaluationOption={evaluationOption}
      likertOptions={likertOptions}
      ratings={ratings}
      setRatings={setRatings}
      notes={notes}
      setNotes={setNotes}
      handleRate={handleRate}
      completedCount={completedCount}
      submitted={submitted}
      handleSubmit={handleSubmit}

    />
  );
}

export { ExpertRatingComponent };
