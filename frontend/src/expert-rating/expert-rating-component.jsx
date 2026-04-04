
import { useEffect, useRef, useState,useMemo } from "react";
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
  ["Interpretability","This dashboard makes the collaboration patterns easy to understand."],
  ["Usefulness for feedback","This Feedbacks would help a learner reflect on and improve their collaboration."],
  ["Clarity","The information presented in the dashboard is clear and easy to follow."],
  ["Actionability","Interacting with this dashboard help learners determine actionable next steps."],
  ["Confidence in interpretation","I can confidently rely on the  information provided in this dashboard to judge the learner’s/my collaboration pattern."]
]

const evaluaion_two = [
  ["Data modality","The integration of different modal metric of impact on the quality of interpretation/synthesis."],
  ["Complementarity of Signals","The feedback draws on classes of metrics that reinforce or support the same interpretation."],
  ["Contextual Interpretation","The feedback is contextualized by interpreting a collaboration indicator in relation to one or more other collaboration indicators, rather than in isolation."],
  ["Relational Reasoning","The feedback reflects how one collaboration indicator/behavior may influence or be associated with another."],
  ["Coverage ","The feedback captures a broad range of behaviors rather than focusing narrowly on one aspect of collaboration."]
]

const evaluaion_three = [
  ["Claims Accuracy","The feedback includes claims that are not clearly supported by the data."],
  ["Evidence Traceability","The feedback clearly links its conclusions to specific elements of the data."],
  ["Consistency","The feedback is internally consistent and does not contain contradictions."],
  ["Sepcifity","The feedback provides specific, data-grounded insights rather than vague statements."],
  ["Trustworthiness","I would trust this feedback as a reliable interpretation of the data."]
]
function ExpertRatingComponent() {

  const [expertDetail, setExpertDetail] = useState(null)
  const [nextPage, setNextPage] = useState("reportoptionpage")
  const [selectedItemForRating, setSelectedItemForRating] = useState(-1)
  const [itemsForRating, setItemsForRating] = useState(["Dashboard Option One", "Dashboard Option Two"])

  const pageTitle = useRef("Expert Rating")
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

  const navigate = useNavigate()
  const sessionService = new SessionService()
  const authService = new AuthService()


  // first useEffect to be called one the evalutor class is selected
  useEffect(()=>{
    if (evaluatorType === "student" && aliasExpertId !== ""){
      setEvaluationOption(evaluaion_one) 
      setFeedbackParameters([158,443,"dklee1004"])
      setRatings(Object.fromEntries(evaluaion_one.map((item) => [item[0], 0])))
      setNextPage("dashboardratingpage")

    }else if(evaluatorType === "expert" && aliasExpertId !== ""){
      verifyExpertId(aliasExpertId)
      
    }
  },[evaluatorType,aliasExpertId])
  
const completedCount = useMemo(
    () => Object.values(ratings).filter((value) => value > 0).length,
    [ratings]
  );
  // ___________________________________________________________ 
  //  STEP1: Clicking the  continue buttion   call this function to verify the selections and input              
  // --------------------------------------------------------

  const loadDashboard = (evaluatorType, alias_expertid) => {
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

  const handleRate = (criterion, value) => {
    setRatings((prev) => ({ ...prev, [criterion]: value }));
    setSubmitted(false);
  };

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

  const closeDialog = () => {
    setCurrentForm("")
  }
  const navigateToLogin = (confirmed = false) => {
    return navigate("/")
  }

  // const loading = () => {
  //   return session.current === null || transcripts.length === 0
  // }

  const closeAlert = () => {
    setShowAlert(false)
  }

  // const onClickedTimeline = (transcript) => {
  //   setCurrentForm("Transcript")
  //   setCurrentTranscript(transcript)
  // }

  // const onClickedKeyword = (transcript) => {
  //   setCurrentTranscript(transcript)
  //   setCurrentForm("gottoselectedtranscript")
  // }

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
      loadDashboard={loadDashboard}
      // loading={loading}
      expertDetail = {expertDetail}
      itemsForRating = {itemsForRating}
      evaluatorType = {evaluatorType}
      setEvaluatorType = {setEvaluatorType}

      //left pane props
      selectedItemForRating = {selectedItemForRating}
      setSelectedItemForRating = {setSelectedItemForRating}
      evaluationOption = {evaluationOption}
      likertOptions={likertOptions}
      ratings={ratings}
      setRatings={setRatings}
      notes={notes}
      setNotes={setNotes}
      handleRate={handleRate}
      completedCount = {completedCount}
      submitted={submitted}
      handleSubmit={handleSubmit}
    />
  );
}

export {ExpertRatingComponent};
