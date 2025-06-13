import React, { useState } from "react"
import { AppSpinner } from "../spinner/spinner-component"
import { GenericDialogBox } from "../dialog/dialog-component"
import { Appheader } from "../header/header-component"
import styles from "./session-feedback-form.module.css"

function FeedbackFormPage({ sessionId, questions = [], onSubmit }) {
    const [responses, setResponses] = useState({})
    const [submitted, setSubmitted] = useState(false)
    const [invalidQuestions, setInvalidQuestions] = useState([]);
    const [errorMessage, setErrorMessage] = useState("");

    const handleInputChange = (id, value) => {
        setResponses((prev) => ({ ...prev, [id]: value }))
    }

    const handleSubmit = async (e) => {
        e.preventDefault();

        const requiredQuestions = questions.filter((q) => q.show);
        const unanswered = requiredQuestions.filter((q) => !responses[q.id]).map((q) => q.id);

        if (unanswered.length > 0) {
            setInvalidQuestions(unanswered);
            setErrorMessage("Please answer all questions before submitting.");
            return;
        }

        setInvalidQuestions([]);
        setErrorMessage("");

        try {
            if (onSubmit) {
                await onSubmit({ sessionId, responses });
            } else {
                // console.log({ sessionId, responses });
            }
            setSubmitted(true);
        } catch (error) {
            // console.error("Error submitting feedback:", error);
            setErrorMessage("Failed to submit feedback. Please try again.");
        }
    };

    return (
        <div className="main-container">
            <Appheader
                title="Session Feedback"
                leftText={false}
                rightText=""
                rightEnabled={false}
                nav={() => window.history.back()}
            />
            <div className="center-column-container">
                <div className={styles["feedbackContainer"]}>
                    {submitted ? (
                        <div className={styles["thankYouMessage"]}>
                            <h2>Thank you for your feedback!</h2>
                            <p>We appreciate your time.</p>
                        </div>
                    ) : (
                        <>
                            <form
                                onSubmit={handleSubmit}
                                className={styles["feedbackForm"]}
                            >
                                {questions
                                    .filter((q) => q.show)
                                    .map((q, index) => (
                                        <div
                                            key={q.id}
                                            className={`${styles["questionBlock"]} ${invalidQuestions.includes(q.id) ? styles["invalid"] : ""}`}
                                        >
                                            <label className={styles["label"]}>
                                                {index + 1}. {q.label}
                                            </label>
                                            {q.type === "likert" && (
                                                <div
                                                    className={
                                                        styles["likertContainer"]
                                                    }
                                                >
                                                    {[
                                                        "Strongly Disagree",
                                                        "Disagree",
                                                        "Neutral",
                                                        "Agree",
                                                        "Strongly Agree",
                                                    ].map(
                                                        (label, labelIndex) => {
                                                            const value =
                                                                labelIndex + 1
                                                            return (
                                                                <button
                                                                    key={value}
                                                                    type="button"
                                                                    className={`${styles["likertButton"]} ${responses[q.id] === value ? styles["selected"] : ""}`}
                                                                    onClick={() => handleInputChange(q.id, value,)}
                                                                >
                                                                    {label}
                                                                </button>
                                                            )
                                                        },
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                            </form>
                            {errorMessage && (
                                <div className={styles["errorMessage"]}>{errorMessage}</div>
                            )}
                            <div className={styles["submitContainer"]}>
                                <button type="submit" className={styles["submitButton"]} onClick={handleSubmit}>
                                    Submit Feedback
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>

            <GenericDialogBox show={false}>
                <div className={styles["dialogContent"]}>
                    <h2>Loading Feedback Form...</h2>
                    <AppSpinner />
                </div>
            </GenericDialogBox>
        </div>
    )
}

export { FeedbackFormPage }
