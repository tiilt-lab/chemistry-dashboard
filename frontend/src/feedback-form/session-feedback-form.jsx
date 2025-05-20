import React from "react";
import { useParams } from "react-router-dom";
import { FeedbackFormPage } from "./html-pages";
import { SessionService } from "../services/session-service";

const feedbackQuestions = [
  { id: "q1", label: "We know our strengths as learners", show: true, type: "likert" },
  { id: "q2", label: "We know how to select relevant information", show: true, type: "likert" },
  { id: "q3", label: "We know how to use the material", show: true, type: "likert" },
  { id: "q4", label: "We know how to organize new information", show: false, type: "likert" },
  { id: "q5", label: "We know how to connect new information with prior knowledge", show: true, type: "likert" },
  { id: "q6", label: "We plan the activities", show: true, type: "likert" },
  { id: "q7", label: "We determine what the task requires", show: true, type: "likert" },
  { id: "q8", label: "We select the appropriate tools", show: true, type: "likert" },
  { id: "q9", label: "We identify the strategies depending on the task", show: true, type: "likert" },
  { id: "q10", label: "We organize our time depending on the task", show: true, type: "likert" },
  { id: "q11", label: "We modify our work according to other group participants’ suggestions", show: true, type: "likert" },
  { id: "q12", label: "We ask questions to check our understanding", show: true, type: "likert" },
  { id: "q13", label: "We check our approach to improve our outcomes", show: true, type: "likert" },
  { id: "q14", label: "We improve our work with group processes", show: true, type: "likert" },
  { id: "q15", label: "We detect and correct errors", show: true, type: "likert" },
  { id: "q16", label: "We make judgments on the difficulty of the task", show: true, type: "likert" },
  { id: "q17", label: "We make judgments on the workload", show: true, type: "likert" },
  { id: "q18", label: "We make judgments on the instruments", show: true, type: "likert" },
  { id: "q19", label: "We make judgments on our learning outcomes", show: true, type: "likert" },
  { id: "q20", label: "We make judgments on the teamwork process", show: true, type: "likert" },
];


const SessionFeedbackForm = () => {
  const { sessionId } = useParams();

  const onSubmit = async ({ sessionId, responses }) => {
    const sessionService = new SessionService();
    try {
      const res = await sessionService.submitFeedback(sessionId, responses);
      if (res.status !== 200) {
        throw new Error("Failed to submit feedback");
      }
      console.log("Feedback submitted successfully!");
    } catch (err) {
      console.error("Submission error:", err);
      alert("Failed to submit feedback. Please try again later.");
    }
  };

  return (
    <FeedbackFormPage
      sessionId={sessionId}
      questions={feedbackQuestions}
      onSubmit={onSubmit}
    />
  );
};

export { SessionFeedbackForm };
