import React, { useState } from "react";
import { useParams } from "react-router-dom";
import styles from "./session-feedback-form.module.css"; 

const feedbackQuestions = [
  {
    id: "satisfaction",
    type: "rating",
    label: "How satisfied were you with this discussion?"
  },
  {
    id: "clarity",
    type: "rating",
    label: "How clear was the conversation flow?"
  },
  {
    id: "comments",
    type: "text",
    label: "Any additional comments or suggestions?",
    placeholder: "Your thoughts..."
  }
];

const SessionFeedbackForm = () => {
  const { sessionId } = useParams();
  const [questions, setQuestions] = useState(feedbackQuestions);
  const [responses, setResponses] = useState({});
  const [submitted, setSubmitted] = useState(false);

  const handleInputChange = (id, value) => {
    setResponses((prev) => ({ ...prev, [id]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log({ sessionId, responses });
    setSubmitted(true);
  };

  return (
    <div className={styles.feedbackContainer}>
      {submitted ? (
        <div className={styles.thankYouMessage}>
          <h2>Thank you for your feedback!</h2>
          <p>We appreciate your time.</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className={styles.feedbackForm}>
          <h2>Session Feedback</h2>

          {questions.map((q) => (
            <div key={q.id} className={styles.questionBlock}>
              <label className={styles.label}>{q.label}</label>
              {q.type === "rating" && (
                <div className={styles.ratingContainer}>
                  {[1, 2, 3, 4, 5].map((num) => (
                    <button
                      key={num}
                      type="button"
                      className={`${styles.ratingButton} ${
                        responses[q.id] === num ? styles.selected : ""
                      }`}
                      onClick={() => handleInputChange(q.id, num)}
                    >
                      {num} ⭐
                    </button>
                  ))}
                </div>
              )}
              {q.type === "text" && (
                <textarea
                  className={styles.commentBox}
                  placeholder={q.placeholder || "Write your response..."}
                  value={responses[q.id] || ""}
                  onChange={(e) => handleInputChange(q.id, e.target.value)}
                />
              )}
            </div>
          ))}

          <button type="submit" className={styles.submitButton}>
            Submit Feedback
          </button>
        </form>
      )}
    </div>
  );
};

export { SessionFeedbackForm };
