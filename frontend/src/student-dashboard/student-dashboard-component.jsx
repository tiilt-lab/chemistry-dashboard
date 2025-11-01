
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom"
import { StudentSessionDashboardPages } from "./html-pages";
import { AuthService } from "../services/auth-service"
import { SessionService } from "../services/session-service";
import { StudentModel } from "../models/student"
import { SessionModel } from "../models/session";
import { SpeakerModel } from "../models/speaker";

function StudentSessionDashboard() {

  const [nextPage, setNextPage] = useState("reportoptionpage")
  const [pageTitle, setPageTitle] = useState("Dashboard")
  const [currentForm, setCurrentForm] = useState("")
  const [showFeatures, setShowFeatures] = useState([])
  const [showBoxes, setShowBoxes] = useState([])
  const [sessiontype, setSessiontype] = useState("")
  const [session, setSession] = useState(null)
  const [sessionId, setSessionId] = useState(-1)
  const [previousSessions, setPreviousSessions] = useState([])
  const [wrongInput, setWrongInput] = useState(false)
  const [pcode, setPcode] = useState("")
  const [userDetail, setUserDetail] = useState(null)

  const [transcripts, setTranscripts] = useState([])
  const [videoMetrics, setVideoMetrics] = useState([])
  const [startTime, setStartTime] = useState()
  const [endTime, setEndTime] = useState()
  const [radarTrigger, setRadarTrigger] = useState(0);
  const [displayTranscripts, setDisplayTranscripts] = useState([])
  const [displayVideoMetrics, setDisplayVideoMetrics] = useState([])
  const [currentTranscript, setCurrentTranscript] = useState(null)
  const [details, setDetails] = useState("Individual")


  const [timeRange, setTimeRange] = useState([0, 1])
  const [showAlert, setShowAlert] = useState(false)
  const [alertMessage, setAlertMessage] = useState("")


  const [selectedSessionId1, setSelectedSessionId1] = useState(-1);
  const [selectedSessionId2, setSelectedSessionId2] = useState(-1);
  const [session1Transcripts, setSession1Transcripts] = useState([]);
  const [session2Transcripts, setSession2Transcripts] = useState([]);
  const [session1VideoMetrics, setSession1VideoMetrics] = useState([])
  const [session2VideoMetrics, setSession2VideoMetrics] = useState([])
  const [displaySingleSession, setDisplaySingleSession] = useState(false);
  const [displayCompareSession, setDisplayCompareSession] = useState(false);
  const [firstLoad, setFirstLoad] = useState(false);
  const [transcriptDoneLoading, setTranscriptDoneLoading] = useState(false);
  const [videoMetricDoneLoading, setVideoMetricDoneLoading] = useState(false);
  const [currentSessionRunning, setCurrentSessionRunning] = useState(false);
  const [sessionPart, setSessionPart] = useState("");

  const sessionDataObjects = useRef({});
  const sessionsObjects = useRef({});

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


  useEffect(() => {
    let intervalLoad
    // fetch the transcript
    if (session !== null && userDetail !== null && sessiontype !== "" && !firstLoad) {
      fetchTranscript(session.id, setTranscripts)
      fetchVideoMetric(session.id, setVideoMetrics)

      //only load for current session every 2 seconds
      if (sessiontype === "currentsession") {
        setCurrentSessionRunning(true);
        intervalLoad = setInterval(() => {
          fetchTranscript(session.id, setTranscripts)
          fetchVideoMetric(session.id, setVideoMetrics)
        }, 2000)
      }

    }

    return () => {
      clearInterval(intervalLoad)
    }
  }, [session, userDetail, sessiontype])


  useEffect(() => {
    if (session !== null && !firstLoad) {
      const sessionLen =
        Object.keys(session).length > 0 ? session.length : 0
      const sTime = Math.round(sessionLen * timeRange[0] * 100) / 100
      const eTime = Math.round(sessionLen * timeRange[1] * 100) / 100
      setStartTime(sTime)
      setEndTime(eTime)
      generateDisplayTranscripts(transcripts, sTime, eTime)
      generateDisplayVideoMetrics(videoMetrics, sTime, eTime)
    } else if (session !== null && firstLoad && currentSessionRunning) {
      const sessionLen =
        Object.keys(session).length > 0 ? session.length : 0
      const sTime = Math.round(sessionLen * timeRange[0] * 100) / 100
      const eTime = Math.round(sessionLen * timeRange[1] * 100) / 100
      setStartTime(sTime)
      setEndTime(eTime)
      generateDisplayTranscripts(transcripts, sTime, eTime)
      generateDisplayVideoMetrics(videoMetrics, sTime, eTime)
    }

  }, [transcripts, videoMetrics, session, timeRange, currentSessionRunning])


  useEffect(() => {
    if (transcriptDoneLoading && videoMetricDoneLoading && !firstLoad) {
      setSelectedSessionId1(session.id);

      if (!sessionDataObjects.current.hasOwnProperty(sessionId)) {
        sessionDataObjects.current[sessionId] = {
          transcripts: transcripts,
          videoMetrics: videoMetrics
        }
      }
      setNextPage("displayreportpage")
      setFirstLoad(true);
    }

  }, [transcriptDoneLoading, videoMetricDoneLoading]);

  useEffect(() => {

    if (displayCompareSession || displaySingleSession) {
      setSessionTranscripts()
      setSessionVideoMetrics()
    }
    if (details === "Individual" && displaySingleSession) {
      setDisplaySingleSession(false);
    } else if (details === "Comparison" && displayCompareSession) {
      setDisplayCompareSession(false);
    }

  }, [details, displaySingleSession, displayCompareSession]);


  useEffect(() => {
    if (transcriptDoneLoading && videoMetricDoneLoading && firstLoad) {
      if (!sessionDataObjects.current.hasOwnProperty(sessionId)) {
        sessionDataObjects.current[sessionId] = {
          transcripts: session1Transcripts,
          videoMetrics: session1VideoMetrics
        }
      }
      setNextPage("displayreportpage")
    }

  }, [transcriptDoneLoading, videoMetricDoneLoading, firstLoad]);

  const initChecklistData = (featuresArr, setFn) => {
    let valueInd = 0
    let showFeats = []
    for (const feature of featuresArr) {
      showFeats.push({ label: feature, value: valueInd, clicked: true })
      valueInd++
    }
    setFn(showFeats)
  }

  const loadSession = (username) => {
    if (sessiontype === "previoussessions") {
      const fetchData = sessionService.getSessionsByAlias(username)
      fetchData
        .then(
          (response) => {
            if (response.status === 200) {
              response.json().then((jsonArrayObj) => {
                const session_data = SessionModel.fromJsonList(jsonArrayObj)
                setPreviousSessions(session_data)
                if (session_data.length > 0) {
                  setSession(session_data[0])
                  setPageTitle(session_data[0].name)
                  setSessionId(session_data[0].id);

                  session_data.forEach((s) => {
                    sessionsObjects.current[s.id] = s
                  })
                }
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
  }

  const loadDashboard = (preference, username) => {
    if (preference === '') {
      setAlertMessage("Please Select a Preffered Session");
      setShowAlert(true);
      document.getElementById("preference").focus();
    } else if (username === '') {
      setAlertMessage("Please Enter Your User Name");
      setShowAlert(true);
      document.getElementById("username").focus();
    } else if (sessiontype === "currentsession" && pcode === "") {
      setAlertMessage("Please Enter the Pass Code");
      setShowAlert(true);
      document.getElementById("passcode").focus();
    } else {
      verifyUsername(username)
      if (sessiontype === "currentsession") {
        fetchSession(pcode)
      }

    }
  }

  const verifyUsername = async (username) => {
    const fetchData = authService.getStudentProfileByID(username)
    fetchData
      .then(
        (response) => {
          if (response.status === 200) {
            response.json().then((jsonObj) => {
              const student_data = StudentModel.fromJson(jsonObj)
              setUserDetail(student_data)
              loadSession(username)
            })
          } else {
            setAlertMessage("Invalid Username");
            setShowAlert(true);
          }
        },
        (apierror) => {
          console.log(
            "Student dashboard func: verifyUsername 1 ",
            apierror,
          )
        },
      )
  }


  const fetchSession = async (pcode) => {
    const fetchData = sessionService.getSessionByPasscode(pcode)
    fetchData
      .then(
        (response) => {
          if (response.status === 200) {
            response.json().then((jsonObj) => {
              const session_data = SessionModel.fromJsonList(jsonObj)
              setSession(session_data[0])
              setPageTitle(session_data[0].name)
              setSessionId(session_data[0].id);
            })
          } else {
            setAlertMessage("Invalid Passcode or Session Expired");
            setShowAlert(true);
          }
        },
        (apierror) => {
          console.log(
            "Student dashboard func: fetchSession 1 ",
            apierror,
          )
        },
      )
  }


  const fetchTranscript = async (sessionId, setMetric) => {
    try {
      const response =
        await sessionService.getSessionTranscriptsForClient(sessionId, userDetail.username)

      if (response.status === 200) {
        const jsonObj = await response.json()
        const fetched_trancript_metrics = jsonObj.map((trancript_metrics) => {
          return { ...trancript_metrics['transcript'], speaker_metrics: trancript_metrics['speaker_metrics'] }
        })

        const sessionLen =
          Object.keys(session).length > 0 ? session.length : 0
        setStartTime(Math.round(sessionLen * timeRange[0] * 100) / 100)
        setEndTime(Math.round(sessionLen * timeRange[1] * 100) / 100)

        setMetric(fetched_trancript_metrics)
        setTranscriptDoneLoading(true);
      } else if (response.status === 400 || response.status === 401) {
        console.log(response, "no transcript obj")
      }
    } catch (error) {
      console.log(
        "byod-join-component error func : fetch transcript",
        error,
      )
    }
  }

  const fetchVideoMetric = async (sessionId, setMetric) => {
    try {
      const response =
        await sessionService.getSessionVideoMetricsForClient(sessionId, userDetail.username)

      if (response.status === 200) {
        const fetched_video_metrics = await response.json()

        setMetric(fetched_video_metrics)
        setVideoMetricDoneLoading(true);
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


  const loadSelectedSessionMetrics = (newSession) => {
    setTranscriptDoneLoading(false);
    setVideoMetricDoneLoading(false);
    setSession1Transcripts([]);
    setSession1VideoMetrics([]);
    setSession2Transcripts([]);
    setSession2VideoMetrics([]);
    setSelectedSessionId1(newSession.id)
    setSessionId(newSession.id);
    setSelectedSessionId2(-1)
    setPageTitle(newSession.name)
    setSession(newSession)
    setDetails("Individual");
    setDisplaySingleSession(true);
  }

  const loadComparedSessionMetrics = (selectedSessionId, sessionPart) => {
    setTranscriptDoneLoading(false);
    setVideoMetricDoneLoading(false);
    setSessionPart(sessionPart);
    if (sessionPart === "sessionOne") {
      setSession1Transcripts([]);
      setSession1VideoMetrics([]);
      setSelectedSessionId1(selectedSessionId)
    } else if (sessionPart === "sessionTwo") {
      setSession2Transcripts([]);
      setSession2VideoMetrics([]);
      setSelectedSessionId2(selectedSessionId)
    }
    setSessionId(selectedSessionId);
    setPageTitle("Comparing Sessions")
    setDisplayCompareSession(true);
  }


  const generateDisplayTranscripts = (transcripts, s, e) => {
    setSession1Transcripts(
      transcripts.filter((t) => t.start_time >= s && t.start_time <= e),
    )
  }

  const generateDisplayVideoMetrics = (videoMetrics, s, e) => {
    setSession1VideoMetrics(
      videoMetrics.filter((v) => v.time_stamp >= s && v.time_stamp <= e),
    )
  }

  const setSessionTranscripts = () => {
    if (selectedSessionId1 !== -1) {
      if (sessionDataObjects.current.hasOwnProperty(selectedSessionId1)) {
        console.log("loading saved session transcript metrics for session 1")
        loadSavedSessionTranscriptMetrics(selectedSessionId1, sessionDataObjects.current[selectedSessionId1].transcripts, setSession1Transcripts)
      } else {
        fetchTranscript(selectedSessionId1, setSession1Transcripts)
      }
    }

    if (selectedSessionId2 !== -1) {
      if (sessionDataObjects.current.hasOwnProperty(selectedSessionId2)) {
        console.log("loading saved session transcript metrics for session 2")
        loadSavedSessionTranscriptMetrics(selectedSessionId2, sessionDataObjects.current[selectedSessionId2].transcripts, setSession2Transcripts)
      } else {
        fetchTranscript(selectedSessionId2, setSession2Transcripts)
      }
    }
  }

  const setSessionVideoMetrics = () => {
    if (selectedSessionId1 !== -1) {
        if (sessionDataObjects.current.hasOwnProperty(selectedSessionId1)) {
          console.log("loading saved session video metrics for session 1")
        loadSavedSessionVideoMetrics(sessionDataObjects.current[selectedSessionId1].videoMetrics, setSession1VideoMetrics)
      } else {
        fetchVideoMetric(selectedSessionId1, setSession1VideoMetrics)
      }
      
    }

    if (selectedSessionId2 !== -1) {
        if (sessionDataObjects.current.hasOwnProperty(selectedSessionId2)) {
          console.log("loading saved session video metrics for session 2")
        loadSavedSessionVideoMetrics(sessionDataObjects.current[selectedSessionId2].videoMetrics, setSession2VideoMetrics)
      } else {
        fetchVideoMetric(selectedSessionId2, setSession2VideoMetrics)
      }
    }
  }


  const loadSavedSessionTranscriptMetrics = (sessionId, transcript, setSessionTranscript) => {
    const sessionData = sessionsObjects.current[sessionId];
    const sessionLen =
      Object.keys(sessionData).length > 0 ? sessionData.length : 0
    setStartTime(Math.round(sessionLen * timeRange[0] * 100) / 100)
    setEndTime(Math.round(sessionLen * timeRange[1] * 100) / 100)

    setSessionTranscript(transcript)
    setTranscriptDoneLoading(true);
  }

  const loadSavedSessionVideoMetrics = (videoMetric, setSessionVideoMetric) => {
    setSessionVideoMetric(videoMetric)
    setVideoMetricDoneLoading(true);
  }


  const viewComparison = () => {
    setDetails("Comparison")
    setDisplaySingleSession(false);
  }

  const viewIndividual = () => {
    setDetails("Individual")
  }

  const ResetTimeRange = (values) => {
    if (session !== null) {
      const sessionLen =
        Object.keys(session).length > 0 ? session.length : 0
      setTimeRange(values)
      const start = Math.round(sessionLen * values[0] * 100) / 100
      const end = Math.round(sessionLen * values[1] * 100) / 100
      setStartTime(start)
      setEndTime(end)
      generateDisplayTranscripts(session1Transcripts, start, end)
      generateDisplayVideoMetrics(session1VideoMetrics, start, end)
    }
  }

  const seeAllTranscripts = () => {
    if (Object.keys(currentTranscript) > 0) { //&& sessionDevice !== null
      setCurrentForm("gottoselectedtranscript")
    }
    // else if (sessionDevice !== null) {
    //     setCurrentForm("gototranscript")
    // }
  }

  const closeDialog = () => {
    setCurrentForm("")
  }
  const navigateToLogin = (confirmed = false) => {
    return navigate("/")
  }

  const loading = () => {
    return session === null || transcripts.length === 0
  }

  const changeTouppercase = (e) => {
    let val = e.target.value.toUpperCase()
    if (val.length <= 4) {
      setWrongInput(false)
    } else {
      setWrongInput(true)
    }
    setPcode(val)
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
    <StudentSessionDashboardPages
      currentForm={currentForm}
      closeDialog={closeDialog}
      nextPage={nextPage}
      pageTitle={pageTitle}
      navigateToLogin={navigateToLogin}
      sessiontype={sessiontype}
      setSessiontype={setSessiontype}
      changeTouppercase={changeTouppercase}
      setShowAlert={setShowAlert}
      showAlert={showAlert}
      closeAlert={closeAlert}
      alertMessage={alertMessage}
      pcode={pcode}
      loadDashboard={loadDashboard}
      wrongInput={wrongInput}
      setRange={ResetTimeRange}
      loading={loading}
      displayTranscripts={displayTranscripts}
      displayVideoMetrics={displayVideoMetrics}
      showFeatures={showFeatures}
      showBoxes={showBoxes}
      userDetail={userDetail}
      session={session}
      previousSessions={previousSessions}
      startTime={startTime}
      endTime={endTime}
      transcripts={transcripts}
      videoMetrics={videoMetrics}
      onClickedTimeline={onClickedTimeline}
      onClickedKeyword={onClickedKeyword}
      details={details}
      viewComparison={viewComparison}
      viewIndividual={viewIndividual}
      loadSelectedSessionMetrics={loadSelectedSessionMetrics}
      loadComparedSessionMetrics={loadComparedSessionMetrics}
      selectedSessionId1={selectedSessionId1}
      setSelectedSessionId1={setSelectedSessionId1}
      selectedSessionId2={selectedSessionId2}
      setSelectedSessionId2={setSelectedSessionId2}
      session1Transcripts={session1Transcripts}
      session2Transcripts={session2Transcripts}
      session1VideoMetrics={session1VideoMetrics}
      session2VideoMetrics={session2VideoMetrics}
      seeAllTranscripts={seeAllTranscripts}
      currentTranscript={currentTranscript}
      transcriptDoneLoading={transcriptDoneLoading}
      videoMetricDoneLoading={videoMetricDoneLoading}
    />
  );
}

export { StudentSessionDashboard };
