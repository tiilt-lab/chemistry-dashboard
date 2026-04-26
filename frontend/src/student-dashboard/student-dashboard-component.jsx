
import { useEffect, useRef, useState,useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom"
import { StudentSessionDashboardPages } from "./html-pages";
import { AuthService } from "../services/auth-service"
import { SessionService } from "../services/session-service";
import { StudentModel } from "../models/student"
import { SessionModel } from "../models/session";
import { SessionDeviceModel } from "../models/session-device";
import { SpeakerModel } from "../models/speaker";

const surveyquestion = [
  ["communication rate","How would you rate the level of communication?"],
  ["climate rate","How would  you rate the climate (group dynamics) during the collaboration session?"],
  ["conflict frequency","How frequently did disagreements/conflict occur during the collaboration?"],
  ["Particpation balance","How balanced was participation among group members (verbal contribution, turn taking) of group members?"],
  ["reflection usefullness","How useful was the reflection feedback in helping you understand your collaboration?","(If you did not receive feedback, please answer based on how useful you think it would have been.)"],
  ["collaboration goal","What aspect of your collaboration would you want to improve on in future collaboration session (Objective) ?"],
  ["collaboration quality","How would you rate the overall quality of your team's collaboration this session?"],
  ["assessment accuracy","How would you rate the accuracy of the assessment scores?","(If you did not receive assessment, please select 'Did not receive')"]
]
const likertOptions = [["Very low","Low","Normal","High","Very high"],
                      ["Very poor","Poor","Neutral","Good","Excellent"],
                      ["Never","Rarely","Sometimes","Often","Very Often"],
                      ["Very unbalanced","Somewhat unbalanced",'Moderately balanced',"Mostly balanced","Very balanced"],
                      ["Not useful","Slightly useful","Moderately useful","Very useful","Extremely useful"],
                      ["Communication","Participation","Focused attention","Idea contribution","Momemtum"],
                      ["Very low","Low","Normal","High","Very high"],
                      ["Did not receive","low","Just right","High","Too high"]]
// const likertOptions = [1, 2, 3, 4, 5];

function StudentSessionDashboard() {
  const previousSessions = useRef([])
  const sessionsObjects = useRef({});
  const pageTitle = useRef("Dashboard")
  const session = useRef(null)
  const prevPages = useRef(["/"])


  const [sessionDevices, setSessionDevices] = useState([])
  const [selectedDeviceID, setSelectedDeviceID] = useState(-1)
  const [sessionId, setSessionId] = useState(-1)

  const [selectFilteredDevice1, setSelectFilteredDevice1] = useState([])
  const [selectFilteredDevice2, setSelectFilteredDevice2] = useState([])
  const [reload, setReload] = useState(0)

  const [nextPage, setNextPage] = useState("reportoptionpage")
  
  const [currentForm, setCurrentForm] = useState("")
  const [showFeatures, setShowFeatures] = useState([])
  const [showBoxes, setShowBoxes] = useState([])
  const [sessiontype, setSessiontype] = useState("")


  const [wrongInput, setWrongInput] = useState(false)
  const [pcode, setPcode] = useState("")
  const [userDetail, setUserDetail] = useState(null)

  const [transcripts, setTranscripts] = useState([])
  const [videoMetrics, setVideoMetrics] = useState([])
  const [startTime, setStartTime] = useState()
  const [endTime, setEndTime] = useState()
  const [startTime2, setStartTime2] = useState()
  const [endTime2, setEndTime2] = useState()
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
  const [selectedSessionDeviceId1, setSelectedSessionDeviceId1] = useState(-1);
  const [selectedSessionDeviceId2, setSelectedSessionDeviceId2] = useState(-1);
  const [session1Transcripts, setSession1Transcripts] = useState([]);
  const [session2Transcripts, setSession2Transcripts] = useState([]);
  const [session1VideoMetrics, setSession1VideoMetrics] = useState([])
  const [session2VideoMetrics, setSession2VideoMetrics] = useState([])

  const [displaySingleSession, setDisplaySingleSession] = useState(false);
  const [displayCompareSession, setDisplayCompareSession] = useState(false);

  const [firstLoadCompleted, setFirstLoadCompleted] = useState(false);
  const [transcriptDoneLoading, setTranscriptDoneLoading] = useState(false);
  const [videoMetricDoneLoading, setVideoMetricDoneLoading] = useState(false);
  const [currentSessionRunning, setCurrentSessionRunning] = useState(false);
  const [surveyAlreadyCompleted, setSurveyAlreadyCompleted] = useState(false)

  const [sessionPart, setSessionPart] = useState("");
  const [loadedAfresh, setLoadedAfresh] = useState(true)

  const [reflectionDashboardDoneLoading, setReflectionDashboardDoneLoading] = useState(false);

  const sessionDataObjects = useRef({});

  const synthesizedFeedbackMetrics = useRef({});
  const llmSessionAnalysis = useRef({})
  const selectedSynthesizedData = useRef({})
  const selectedLLMAnalysis = useRef({})
  const promptHistory = useRef({})
  const promptResponses = useRef({})
  const [isThinking, setIsThinking] = useState(false)

  const [selectedMomentIdAndIndex, setSelectedMomentIdAndIndex] = useState(null);
  const [deviceIDReflectionDashboard, setdeviceIDRefectionDashboard] = useState(-1)
  const [sessionNameForReflecDashboard, setSessionNameForReflecDashboard] = useState("")
  const [groupNameForReflecDashboard, setGroupNameForReflecDashboard] = useState("")
  const [ratings, setRatings] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [notes, setNotes] = useState("");
  const [dialogHeading, setDialogHeading] = useState("Error");


  const navigate = useNavigate()

  //I want to use the same JSX to handle participants who joined the collaboration
  // but will not be exposed to either real-time or post-hoc feedback. However, the component is 
  // designed to display feedback, so in other to re-use it, i define a separate url in the route
  // but points it to this jSX, so this url has 'survey' at the end while the other url to the page
  //does 'dashboard'. So i use the useLocation hooks to get the path and detect the last path element
  // such that if is it 'survey', it will render only the survey page, else it will render the dashboard
  // including the survey page.
  const location = useLocation();
  const pathToSurveyOptions = location.pathname.split("/").at(-1)
  
  const sessionService = new SessionService()
  const authService = new AuthService()

  // USEEFFECTS AND INIT FUNCTIONS

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


  // ___________________________________________________________ 
  //  FIRST USEEFFECT:  CALL ONCE STEP 1,2, 2.1, 2.1.1, OR 2.2 HAS COMPLETED            
  // --------------------------------------------------------
  useEffect(() => {
    let intervalLoad

    if (session.current !== null && userDetail !== null && sessiontype !== "") {

      if (sessiontype === "previoussessions") {
        //Load session groups the student joined
        setSelectedSessionDeviceId1(-1)
        setSelectFilteredDevice1(sessionDevices)
        setNextPage("displaygrouppage")
      } else if (sessiontype === "currentsession" && !firstLoadCompleted) { //LOOK INTO THIS LOGIC, AND ENSURE SMOOTH OPERATION WITH LOADEDAFRESH
        // fetch the transcript
        fetchTranscript(session.current.id, setTranscripts)
        fetchVideoMetric(session.current.id, setVideoMetrics)
        setCurrentSessionRunning(true);
        //only load for current session every 2 seconds
        intervalLoad = setInterval(() => {
          fetchTranscript(session.current.id, setTranscripts)
          fetchVideoMetric(session.current.id, setVideoMetrics)
        }, 2000)
      }

    }

    return () => {
      clearInterval(intervalLoad)
    }
  }, [session.current, userDetail, sessionDevices, sessiontype])

  // ___________________________________________________________ 
  //  SECOND USEEFFECT:  CALL TO LOAD TRANSCRIPT FOR SELECTED DEVICE            
  // --------------------------------------------------------
  useEffect(() => {
    // fetch the transcript based on group selected
    if (selectedDeviceID > -1) {
      // console.log("tracking session and device ids inside useeffect  ", selectedSessionId1, selectedSessionDeviceId1,selectedDeviceID)
      //this is necessary if the first session and device were loaded from the entry page
      // and the user has not clicked on any session
      if (!firstLoadCompleted) {
        setSelectedSessionId1(sessionId)
      }
      setDetails("Individual");
      setDisplaySingleSession(true);
    }

  }, [selectedDeviceID])

  // ___________________________________________________________ 
  //  THIRD USEEFFECT:          
  // --------------------------------------------------------
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

  // ___________________________________________________________ 
  //  FOURTH USEEFFECT:  THIS IS TRIGGERED ONCE THE TRANSCRIPT AND VIDEO METRIC IS PULLED FROM THE DB            
  // --------------------------------------------------------
  useEffect(() => {
    if (session.current !== null && !firstLoadCompleted) {
      const sessionLen =
        Object.keys(session.current).length > 0 ? session.current.length : 0
      const sTime = Math.round(sessionLen * timeRange[0] * 100) / 100
      const eTime = Math.round(sessionLen * timeRange[1] * 100) / 100
      setStartTime(sTime)
      setEndTime(eTime)
      generateDisplayTranscripts(transcripts, sTime, eTime)
      generateDisplayVideoMetrics(videoMetrics, sTime, eTime)
    } else if (session.current !== null && firstLoadCompleted && currentSessionRunning) {
      const sessionLen =
        Object.keys(session.current).length > 0 ? session.current.length : 0
      const sTime = Math.round(sessionLen * timeRange[0] * 100) / 100
      const eTime = Math.round(sessionLen * timeRange[1] * 100) / 100
      setStartTime(sTime)
      setEndTime(eTime)
      generateDisplayTranscripts(transcripts, sTime, eTime)
      generateDisplayVideoMetrics(videoMetrics, sTime, eTime)
    }

  }, [transcripts, videoMetrics, session.current, timeRange, currentSessionRunning])


  useEffect(() => {
    if (transcriptDoneLoading && videoMetricDoneLoading && !firstLoadCompleted) {
      setSelectedSessionId1(session.current.id);

      // ///we maintain a store that keeps already fetched transcript base session and device id
      // updateTranscriptVideoMetricStore(loadedAfresh, sessiontype,selectedSessionId1, selectedSessionDeviceId1,session1Transcripts,session1VideoMetrics)
      
      setNextPage("displayreportpage")
      setFirstLoadCompleted(true);
    }

  }, [transcriptDoneLoading, videoMetricDoneLoading, loadedAfresh]);


  useEffect(() => {
    if (transcriptDoneLoading && videoMetricDoneLoading && firstLoadCompleted) {

      ///we maintain a store that keeps already fetched transcript base session and device id
      updateTranscriptVideoMetricStore(loadedAfresh, sessiontype, selectedSessionId1, selectedSessionDeviceId1, session1Transcripts, session1VideoMetrics)

      // if (loadedAfresh && (session2Transcripts.length > 0 || session2VideoMetrics.length > 0) && (selectedSessionId2 > -1)) {
      if (selectedSessionId2 > -1) {
        updateTranscriptVideoMetricStore(loadedAfresh, sessiontype, selectedSessionId2, selectedSessionDeviceId2, session2Transcripts, session2VideoMetrics)


        const sessionData = sessionsObjects.current[selectedSessionId2];
        const sessionLen =
          Object.keys(sessionData).length > 0 ? sessionData.length : 0
        setStartTime2(Math.round(sessionLen * timeRange[0] * 100) / 100)
        setEndTime2(Math.round(sessionLen * timeRange[1] * 100) / 100)
      }
      prevPages.current.push("displaygrouppage")
      setNextPage("displayreportpage")
    }

  }, [transcriptDoneLoading, videoMetricDoneLoading, loadedAfresh, firstLoadCompleted]);


  // THIS IS MEANT FOR REFLECTION DASHBOARD
  useEffect(() => {
    if (deviceIDReflectionDashboard !== -1) {
      setSelectedSessionDeviceId1(deviceIDReflectionDashboard)
      setRatings(Object.fromEntries(surveyquestion.map((item) => [item[0], ""])))
    }
  }, [deviceIDReflectionDashboard])


  const completedCount = useMemo(
      () => Object.values(ratings).filter((value) => value !== "").length,
      [ratings]
    );

  const updateTranscriptVideoMetricStore = (loaded, sessiontype, selectedSessionId, selectedSessionDeviceId, Transcripts, VideoMetrics) => {
    //if loaded afresh then update the store
    if (loaded && sessiontype === "previoussessions") {
      if (!sessionDataObjects.current.hasOwnProperty(selectedSessionId)) {
        sessionDataObjects.current[selectedSessionId] = {
          [selectedSessionDeviceId]: {
            transcripts: Transcripts,
            videoMetrics: VideoMetrics
          }
        }
      } else {
        if (!sessionDataObjects.current[selectedSessionId].hasOwnProperty(selectedSessionDeviceId)) {
          sessionDataObjects.current[selectedSessionId][selectedSessionDeviceId] = {
            transcripts: Transcripts,
            videoMetrics: VideoMetrics
          }
        }
      }
      // console.log("store ", sessionDataObjects.current)
    }
  }

  const initChecklistData = (featuresArr, setFn) => {
    let valueInd = 0
    let showFeats = []
    for (const feature of featuresArr) {
      showFeats.push({ label: feature, value: valueInd, clicked: true })
      valueInd++
    }
    setFn(showFeats)
  }


  // ___________________________________________________________ 
  //  STEP1: Clicking the  continue buttion   call this function to verify the selections and input              
  // --------------------------------------------------------

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

  // ___________________________________________________________ 
  //   STEP2: This is called to authenticate the username, fetch user data and call load session           
  // --------------------------------------------------------

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
              prevPages.current.push("reportoptionpage")
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

  // ___________________________________________________________ 
  //   STEP 2.1 : This is called inside step 2 to load the sessions the student have joined so far and then initialize the first session and first device/group          
  // --------------------------------------------------------

  const loadSession = (username) => {
    if (sessiontype === "previoussessions") {
      const fetchData = sessionService.getSessionsByAlias(username)
      fetchData
        .then(
          (response) => {
            if (response.status === 200) {
              response.json().then((jsonArrayObj) => {
                const session_data = SessionModel.fromJsonList(jsonArrayObj)

                if (session_data.length > 0) {
                  previousSessions.current = session_data
                  session.current = session_data[0]
                  pageTitle.current = session_data[0].name + ": " + new Date(session_data[0].creation_date).toDateString()
                  setSessionId(session_data[0].id);
                  session_data.forEach((s) => {
                    sessionsObjects.current[s.id] = s
                  })
                  loadSessionDevice(session_data[0].id, username)
                  setReload(reload + 1)
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

  // ___________________________________________________________ 
  //   STEP 2.1.1 : This is called inside step 2.1 to load the sessions device/group joined by the student         
  // --------------------------------------------------------

  const loadSessionDevice = (sessionid, username) => {
    if (sessiontype === "previoussessions") {
      getSessionDevicesBySessionAndAlias(sessionid, username, setSessionDevices)
    }
  }


  const getSessionDevicesBySessionAndAlias = (sessionid, username, setFnc) => {
    const fetchData = sessionService.getSessionsDeviceByAlias(sessionid, username)
    fetchData
      .then(
        (response) => {
          if (response.status === 200) {
            response.json().then((jsonArrayObj) => {
              const session_device_data = SessionDeviceModel.fromJsonList(jsonArrayObj)

              if (session_device_data.length > 0) {
                setFnc(session_device_data)
              }
            })
          } else {
            setFnc([])
            setAlertMessage("No  Sessions Group Found for this User");
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



  // ___________________________________________________________ 
  //   STEP 2.2: This is called inside step 2 if this student select to view current session           
  // --------------------------------------------------------
  const fetchSession = async (pcode) => {
    const fetchData = sessionService.getSessionByPasscode(pcode)
    fetchData
      .then(
        (response) => {
          if (response.status === 200) {
            response.json().then((jsonObj) => {
              const session_data = SessionModel.fromJsonList(jsonObj)
              session.current = session_data[0]
              pageTitle.current = session_data[0].name + ": " + new Date(session_data[0].creation_date).toDateString()
              setSessionId(session_data[0].id);
              setReload(reload + 1)
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


  const fetchTranscript = async (sessionId, setMetric, deviceId = null) => {
    try {
      let response = null
      if (deviceId === null) {
        response = await sessionService.getSessionTranscriptsForClient(sessionId, userDetail.username)
      } else {
        response = await sessionService.getSessionDeviceTranscriptsByAlias(sessionId, deviceId, userDetail.username)
      }


      if (response !== null && response.status === 200) {
        const jsonObj = await response.json()
        const fetched_trancript_metrics = jsonObj.map((trancript_metrics) => {
          return { ...trancript_metrics['transcript'], speaker_metrics: trancript_metrics['speaker_metrics'] }
        })

        const sessionLen =
          Object.keys(session.current).length > 0 ? session.current.length : 0
        setStartTime(Math.round(sessionLen * timeRange[0] * 100) / 100)
        setEndTime(Math.round(sessionLen * timeRange[1] * 100) / 100)

        setMetric(fetched_trancript_metrics)
        setLoadedAfresh(true)
        setTranscriptDoneLoading(true);
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

  const fetchVideoMetric = async (sessionId, setMetric, deviceId = null) => {
    try {
      let response = null
      if (deviceId === null) {
        response = await sessionService.getSessionVideoMetricsForClient(sessionId, userDetail.username)
      } else {
        response = await sessionService.getSessionDeviceVideoMetricsByAlias(sessionId, deviceId, userDetail.username)
      }


      if (response !== null && response.status === 200) {
        const fetched_video_metrics = await response.json()

        setMetric(fetched_video_metrics)
        setLoadedAfresh(true)
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
    setSelectedDeviceID(-1)
    pageTitle.current = newSession.name + ": " + new Date(newSession.creation_date).toDateString()
    session.current = newSession
    loadSessionDevice(newSession.id, userDetail.username)
    // console.log("tracking session and device ids  ", selectedSessionId1, selectedSessionDeviceId1)
  }

  const loadSelectedSessionDeviceMetrics = (deviceId) => {
    // console.log("tracking session and device ids inside group click  ", selectedSessionId1, selectedSessionDeviceId1,deviceId,selectedDeviceID)
    setTranscriptDoneLoading(false);
    setVideoMetricDoneLoading(false);
    setRatings({})
    setNotes("")
    setSession1Transcripts([]);
    setSession1VideoMetrics([]);
    setSession2Transcripts([]);
    setSession2VideoMetrics([]);
    setSelectedSessionDeviceId1(-1)
    setSelectedDeviceID(-1)
    setSelectedSessionDeviceId2(-1)
    setSelectedSessionDeviceId1(deviceId)
    setSelectedDeviceID(deviceId)
    if (pathToSurveyOptions === "survey") {
      getSurveySubmittedForSurveyPath(sessionId,deviceId)
    }
  }

  const getSurveySubmittedForSurveyPath = async (sessId,deviceId) => {
      let surv_resp = await getSurveySubmitted(sessId,deviceId)
      console.log("survey response ", surv_resp)
      if(surv_resp !== null){
        setNotes(surv_resp.notes)
        const {notes, ...rest } = surv_resp;
        setRatings(rest)
        setSurveyAlreadyCompleted(true)
      }
  }

  const getSessionDevices = (selectedSessionId, sessionPart = "sessionOne") => {
    if (sessionPart === "sessionOne") {
      getSessionDevicesBySessionAndAlias(selectedSessionId, userDetail.username, setSelectFilteredDevice1)
      setSelectedSessionId1(selectedSessionId)
    } else if (sessionPart === "sessionTwo") {
      getSessionDevicesBySessionAndAlias(selectedSessionId, userDetail.username, setSelectFilteredDevice2)
      setSelectedSessionId2(selectedSessionId)
    }
    setSessionId(selectedSessionId);
  }

  const loadComparedSessionDeviceMetrics = (selectedSessionDeviceId, sessionPart) => {
    setTranscriptDoneLoading(false);
    setVideoMetricDoneLoading(false);
    setSessionPart(sessionPart);
    if (sessionPart === "sessionOne") {
      setSession1Transcripts([]);
      setSession1VideoMetrics([]);
      setSelectedSessionDeviceId1(selectedSessionDeviceId)
    } else if (sessionPart === "sessionTwo") {
      setSession2Transcripts([]);
      setSession2VideoMetrics([]);
      setSelectedSessionDeviceId2(selectedSessionDeviceId)
    }
    pageTitle.current = "Comparing Sessions"
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
        if (sessionDataObjects.current[selectedSessionId1].hasOwnProperty(selectedSessionDeviceId1)) {
          // console.log("loading saved session transcript metrics for session 1")
          loadSavedSessionTranscriptMetrics(selectedSessionId1, sessionDataObjects.current[selectedSessionId1][selectedSessionDeviceId1].transcripts, setSession1Transcripts)
        } else {
          // console.log("fetching session transcript metrics for session 1")
          fetchTranscript(selectedSessionId1, setSession1Transcripts, selectedSessionDeviceId1)
        }
      } else {
        // console.log("fetching session transcript metrics for session 2")
        fetchTranscript(selectedSessionId1, setSession1Transcripts, selectedSessionDeviceId1)
      }
    }

    if (selectedSessionId2 !== -1) {
      if (sessionDataObjects.current.hasOwnProperty(selectedSessionId2)) {
        if (sessionDataObjects.current[selectedSessionId2].hasOwnProperty(selectedSessionDeviceId2)) {
          // console.log("loading saved session transcript metrics for session 2")
          loadSavedSessionTranscriptMetrics(selectedSessionId2, sessionDataObjects.current[selectedSessionId2][selectedSessionDeviceId2].transcripts, setSession1Transcripts)
        } else {
          // console.log("fetching transcript 2 level 1")
          fetchTranscript(selectedSessionId2, setSession2Transcripts, selectedSessionDeviceId2)
        }
      } else {
        // console.log("fetching transcript 2 level 2")
        fetchTranscript(selectedSessionId2, setSession2Transcripts, selectedSessionDeviceId2)
      }
    }
  }

  const setSessionVideoMetrics = () => {
    if (selectedSessionId1 !== -1) {
      if (sessionDataObjects.current.hasOwnProperty(selectedSessionId1)) {
        if (sessionDataObjects.current[selectedSessionId1].hasOwnProperty(selectedSessionDeviceId1)) {
          // console.log("loading saved session video metrics for session 1")
          loadSavedSessionVideoMetrics(sessionDataObjects.current[selectedSessionId1][selectedSessionDeviceId1].videoMetrics, setSession1VideoMetrics)
        } else {
          //  console.log("fetching session video metrics for session 1")
          fetchVideoMetric(selectedSessionId1, setSession1VideoMetrics, selectedSessionDeviceId1)
        }
      } else {
        //  console.log("fetching session video metrics for session 2")
        fetchVideoMetric(selectedSessionId1, setSession1VideoMetrics, selectedSessionDeviceId1)
      }

    }

    if (selectedSessionId2 !== -1) {
      if (sessionDataObjects.current.hasOwnProperty(selectedSessionId2)) {
        if (sessionDataObjects.current[selectedSessionId2].hasOwnProperty(selectedSessionDeviceId2)) {
          // console.log("loading saved session video metrics for session 2")
          loadSavedSessionVideoMetrics(sessionDataObjects.current[selectedSessionId2][selectedSessionDeviceId2].videoMetrics, setSession2VideoMetrics)
        } else {
          // console.log("fetching video metric 2 level 1")
          fetchVideoMetric(selectedSessionId2, setSession2VideoMetrics, selectedSessionDeviceId2)
        }
      } else {
        // console.log("fetching video metric 2 level 2")
        fetchVideoMetric(selectedSessionId2, setSession2VideoMetrics, selectedSessionDeviceId2)
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
    setLoadedAfresh(false)
    setTranscriptDoneLoading(true);
  }

  const loadSavedSessionVideoMetrics = (videoMetric, setSessionVideoMetric) => {
    setSessionVideoMetric(videoMetric)
    setLoadedAfresh(false)
    setVideoMetricDoneLoading(true);
  }

  ///------------------------------------------------------------------------//
  // IMPLEMENTATION FOR THE REFLECTION DASHBOARD 
  //-----------------------------------------------------------------------//

  const loadReflectiondashboard = async (view) => {
    if (selectedSessionId1 === -1 || selectedSessionDeviceId1 === -1) {
      setAlertMessage("Please select a session and a group to load the reflection dashboard ");
      setShowAlert(true);
    } else {
      setReflectionDashboardDoneLoading(false)
      setSurveyAlreadyCompleted(false)
      let actionstatus = await extractParticipantData(selectedSessionDeviceId1)
      let surv_resp = await getSurveySubmitted(selectedSessionId1,selectedSessionDeviceId1)
      if(surv_resp !== null){
        setNotes(surv_resp.notes)
        const {notes, ...rest } = surv_resp;
        setRatings(rest)
        setSurveyAlreadyCompleted(true)
      }
      if (actionstatus) {
        const sess = previousSessions.current.find((ses) => ses.id === selectedSessionId1);
        const group = sessionDevices.find((dev) => dev.id === selectedSessionDeviceId1);
        setSessionNameForReflecDashboard(sess?.name + ": " + new Date(sess?.creation_date).toDateString())
        setGroupNameForReflecDashboard(group?.name)
        prevPages.current.push("displaygrouppage")
        setNextPage(view);
        setReflectionDashboardDoneLoading(true)
      }else{
        setReflectionDashboardDoneLoading(false)
        setDialogHeading("Error")
        setAlertMessage("No reflection data available for this session");
        setShowAlert(true);

      }
    }

  };

  const loadReflectionDashboardForNewSelection = async (newSessionDeviceID) => {
    setdeviceIDRefectionDashboard(newSessionDeviceID)
    setReflectionDashboardDoneLoading(false)
    setSurveyAlreadyCompleted(false)
    let actionstatus = await extractParticipantData(newSessionDeviceID)
    let surv_resp = await getSurveySubmitted(selectedSessionId1,newSessionDeviceID)

    if(surv_resp !== null){
      setNotes(surv_resp.notes)
      const {notes, ...rest } = surv_resp;
      setRatings(rest)
      setSurveyAlreadyCompleted(true)
    }
    if (actionstatus) {
      const sess = previousSessions.current.find((ses) => ses.id === selectedSessionId1);
      const group = selectFilteredDevice1.find((dev) => dev.id === newSessionDeviceID);
      setSessionNameForReflecDashboard(sess.name + ": " + new Date(sess.creation_date).toDateString())
      setGroupNameForReflecDashboard(group.name)
      setReflectionDashboardDoneLoading(true)
    }else{
      setDialogHeading("Error")
      setAlertMessage("No reflection data available for this session");
      setShowAlert(true);
    }
  }


  const extractParticipantData = async (deviceId) => {
    const resp = await loadSynthesizedMetric(deviceId)

    let respObj = buildData("Participant level sesssion analysis", selectedSessionId1, deviceId, null, null)
  
    if (resp === false  || Object.keys(respObj).length === 0) {
      return false;
    }

    if(respObj["participant_level_metric"] === undefined){
      return false;
    }

    // console.log("Synthesized feedback: ",respObj)

    const ret = await loadLLMAnalytics(respObj, deviceId)
    if (ret) {
      // console.log("llm response: ",llmSessionAnalysis.current[selectedSessionId1][deviceId])
      selectedLLMAnalysis.current = llmSessionAnalysis.current[selectedSessionId1][deviceId]
      selectedSynthesizedData.current = respObj
      await loadprompthistory(deviceId)
      setSelectedMomentIdAndIndex([0, selectedSynthesizedData.current.participant_level_metric[0]?.windowid])

      return ret
    } else {
      return ret
    }
  }

  const interactivePromptFnc = async (selSessionId, selSessionDeviceId, default_question_id, question) => {
    let respObj = buildData("interactive prompting", selSessionId, selSessionDeviceId, default_question_id, question)
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

  const buildData = (reporttype, sessionId, deviceId, defaultQuestionId, question) => {
    let retObj = {}
    if (synthesizedFeedbackMetrics.current.hasOwnProperty(sessionId) && synthesizedFeedbackMetrics.current[sessionId].hasOwnProperty(deviceId)) {
      if (reporttype === "Participant level sesssion analysis") {
        retObj["participant_name"] = userDetail.username
        retObj["sessionid"] = sessionId
        retObj["sessiondeviceid"] = deviceId
        retObj["retrieve_existing_report"] = "true"
        retObj["source"] = "student"
        retObj["promptcontext"] = ""
        retObj["promptrefinement"] = ""
        retObj["participant_level_metric"] = synthesizedFeedbackMetrics.current[sessionId][deviceId]["participants_level"][userDetail.username]
        retObj["session_level_metric"] = synthesizedFeedbackMetrics.current[sessionId][deviceId]["session_level"][userDetail.username]
        retObj["group_level_metric"] = synthesizedFeedbackMetrics.current[sessionId][deviceId]["group_level"]
      } else if (reporttype === "interactive prompting") {
        retObj["participant_name"] = userDetail.username
        retObj["sessionid"] = sessionId
        retObj["sessiondeviceid"] = deviceId
        retObj["retrieve_existing_answer"] = "true"
        retObj["default_question_id"] = defaultQuestionId
        retObj["question"] = question
        retObj["window_level_metric"] = synthesizedFeedbackMetrics.current[sessionId][deviceId]["window_level"]
        retObj["session_level_metric"] = synthesizedFeedbackMetrics.current[sessionId][deviceId]["session_level"]
        retObj["group_level_metric"] = synthesizedFeedbackMetrics.current[sessionId][deviceId]["group_level"]
      }
    }
    return retObj
  }

  const loadSynthesizedMetric = async (deviceId) => {
    // This is needed to load the synthesized feedback for the Reflection dashboard
    if (!synthesizedFeedbackMetrics.current.hasOwnProperty(selectedSessionId1)) {
      const data = await getSynthesizedMetric(deviceId)

      if (data === null) {
        return false
      }
      synthesizedFeedbackMetrics.current[selectedSessionId1] = {
        [deviceId]: data
      }
    } else {
      if (!synthesizedFeedbackMetrics.current[selectedSessionId1].hasOwnProperty(deviceId)) {
        const data = await getSynthesizedMetric(deviceId)

        if (data === null) {
          return false
        }
        synthesizedFeedbackMetrics.current[selectedSessionId1][deviceId] = data
      }

    }
    return true
  }

  const loadLLMAnalytics = async (respObj, deviceId) => {

    if (!llmSessionAnalysis.current.hasOwnProperty(selectedSessionId1)) {
      const analysis = await getLLMAnalytics(respObj)

      if (analysis === null) {
        return false
      }

      llmSessionAnalysis.current[selectedSessionId1] = {
        [deviceId]: analysis
      }
    } else {
      if (!llmSessionAnalysis.current[selectedSessionId1].hasOwnProperty(deviceId)) {

        const analysis = await getLLMAnalytics(respObj)
        if (analysis === null) {
          return false
        }

        llmSessionAnalysis.current[selectedSessionId1][deviceId] = analysis

      }

    }
    return true
  }

  const loadprompthistory = async (deviceId) => {
    if (!promptHistory.current.hasOwnProperty(selectedSessionId1)) {
      const prompt = await getPrompthistory(deviceId)

      if (prompt === null) {
        return false
      }

      promptHistory.current[selectedSessionId1] = {
        [deviceId]: prompt
      }
    } else {
      if (!promptHistory.current[selectedSessionId1].hasOwnProperty(deviceId)) {

        const prompt = await getPrompthistory(deviceId)
        if (prompt === null) {
          return false
        }

        promptHistory.current[selectedSessionId1][deviceId] = prompt

      }

    }
    return true
  }


  const getSynthesizedMetric = async (deviceId) => {
    try {
      const response = await new SessionService().getSynthesizedFeedbackMetrics(selectedSessionId1, deviceId);
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

  const getSurveySubmitted = async (sessId,deviceId) =>{
    try {
      const response = await new SessionService().getSurveyResponseSubmitted(sessId, deviceId,userDetail.username);
      if (response.status === 200) {
        const jsonObj = await response.json()
        return jsonObj.response
      } else {
        return null
      }
    } catch (error) {
      console.log(
        "student dashboard getSurveySubmitted",
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

  const getPrompthistory = async (deviceId) => {
    try {
      const response = await new SessionService().get_llm_question_answer_interactions(selectedSessionId1, deviceId, userDetail.username);

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

  const viewComparison = () => {
    setDetails("Comparison")
    setDisplaySingleSession(false);
  }

  const viewIndividual = () => {
    setDetails("Individual")
  }

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

  const seeAllTranscripts = () => {
    if (Object.keys(currentTranscript) > 0 && sessionDevices.length > 0 && selectedSessionDeviceId1 !== -1 && sessiontype === "previoussessions") { 
      setCurrentForm("gottoselectedtranscript")
    }else if (sessionDevices.length > 0 && selectedSessionDeviceId1 !== -1 && sessiontype === "previoussessions") {
        setCurrentForm("gototranscript")
    }
  }

  const closeDialog = () => {
    setCurrentForm("")
  }
  const navigateToLogin = (confirmed = false) => {
    return navigate("/")
  }

  const loading = () => {
    return session.current === null || transcripts.length === 0
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

  const handleRate = (criterion, value) => {
    setRatings((prev) => ({ ...prev, [criterion]: value }));
    setSubmitted(false);
  };

  const handleSubmit = async (allComplete) => {
    // e.preventDefault();
    if (!allComplete) return;

    ratings.notes = notes
    const payload = {
      sessionid: selectedSessionId1,
      sessionDeviceId: selectedSessionDeviceId1,
      username: userDetail.username,
      response: ratings,
    };

    // console.log("payload ",payload)
    try {
      const response = await new SessionService().postSurveyResponse(payload);

      if (response.status === 200) {
        // console.log("Submitted rating form:", payload);
        setRatings({})
        setDialogHeading("Success")
        setSubmitted(true);
        setAlertMessage("Survey Submission Successful");
        setShowAlert(true);
      } else if (response.status === 400) {
        setDialogHeading("Error")
        setAlertMessage("Survey Submission Unsuccessful, Please contact Admin");
        setShowAlert(true);
      }
    } catch (error) {
      console.log(
        "Student dashboard handle submit",
        error,
      )
      return null
    }

  };

  const onClickedTimeline = (transcript) => {
    setCurrentForm("Transcript")
    setCurrentTranscript(transcript)
  }

  const onClickedKeyword = (transcript) => {
    setCurrentTranscript(transcript)
    setCurrentForm("gottoselectedtranscript")
  }

  const navBackTo = ()=>{
    if(prevPages.current.length === 1 && prevPages.current[0]  === "/"){
      navigateToLogin()
    }else{
      let last = prevPages.current.pop(-1)
      while (prevPages.current.at(-1) === last){
        last = prevPages.current.pop(-1)
      }
      setNextPage(last)
    }
  }
  return (
    <StudentSessionDashboardPages
      currentForm={currentForm}
      closeDialog={closeDialog}
      nextPage={nextPage}
      pageTitle={pageTitle.current}
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
      session={session.current}
      previousSessions={previousSessions.current}
      startTime={startTime}
      endTime={endTime}
      startTime2={startTime2}
      endTime2={endTime2}
      transcripts={transcripts}
      videoMetrics={videoMetrics}
      onClickedTimeline={onClickedTimeline}
      onClickedKeyword={onClickedKeyword}
      details={details}
      viewComparison={viewComparison}
      viewIndividual={viewIndividual}
      loadSelectedSessionMetrics={loadSelectedSessionMetrics}
      loadComparedSessionDeviceMetrics={loadComparedSessionDeviceMetrics}
      selectedSessionId1={selectedSessionId1}
      setSelectedSessionId1={setSelectedSessionId1}
      selectedSessionDeviceId1={selectedSessionDeviceId1}
      selectedSessionDeviceId2={selectedSessionDeviceId2}
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
      sessionDevices={sessionDevices}
      loadSelectedSessionDeviceMetrics={loadSelectedSessionDeviceMetrics}
      getSessionDevices={getSessionDevices}
      selectFilteredDevice1={selectFilteredDevice1}
      selectFilteredDevice2={selectFilteredDevice2}
      dialogHeading = {dialogHeading}
      setCurrentForm = {setCurrentForm}
      navBackTo = {navBackTo}

      loadReflectiondashboard={loadReflectiondashboard}
      reflectionDashboardDoneLoading={reflectionDashboardDoneLoading}
      selectedLLMAnalysis={selectedLLMAnalysis.current}
      selectedSynthesizedData={selectedSynthesizedData.current}
      promptResponses={promptResponses.current}
      isThinking={isThinking}
      setIsThinking={setIsThinking}
      selectedMomentIdAndIndex={selectedMomentIdAndIndex}
      setSelectedMomentIdAndIndex={setSelectedMomentIdAndIndex}
      setdeviceIDRefectionDashboard={setdeviceIDRefectionDashboard}
      sessionNameForReflecDashboard={sessionNameForReflecDashboard}
      groupNameForReflecDashboard={groupNameForReflecDashboard}
      interactivePromptFnc={interactivePromptFnc}
      loadReflectionDashboardForNewSelection={loadReflectionDashboardForNewSelection}


      //Survey props
      surveyquestion = {surveyquestion}
      likertOptions={likertOptions}
      completedCount = {completedCount}
      ratings = {ratings}
      handleRate = {handleRate}
      handleSubmit ={handleSubmit}
      submitted ={submitted}
      setNotes ={setNotes}
      notes = {notes}
      pathToSurveyOptions = {pathToSurveyOptions}
      surveyAlreadyCompleted = {surveyAlreadyCompleted}

    />
  );
}

export { StudentSessionDashboard };
