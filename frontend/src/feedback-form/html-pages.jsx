import React, { useState } from 'react';
import { AppSpinner } from '../spinner/spinner-component';
import { GenericDialogBox } from '../dialog/dialog-component';
import { Appheader } from '../header/header-component';
import styles from './session-feedback-form.module.css';

function FeedbackFormPage({ sessionId, questions = [], onSubmit }) {
    const [responses, setResponses] = useState({});
    const [submitted, setSubmitted] = useState(false);

    const handleInputChange = (id, value) => {
        setResponses((prev) => ({ ...prev, [id]: value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (onSubmit) {
            onSubmit({ sessionId, responses });
        } else {
            console.log({ sessionId, responses });
        }
        setSubmitted(true);
    };

    return (
        <>
            <Appheader
                title="Session Feedback"
                leftText={false}
                rightText=""
                rightEnabled={false}
                nav={() => window.history.back()}
            />
            <div className={styles["feedbackContainer"]}>
                {submitted ? (
                    <div className={styles["thankYouMessage"]}>
                        <h2>Thank you for your feedback!</h2>
                        <p>We appreciate your time.</p>
                    </div>
                ) : (
                    <>
                        <form onSubmit={handleSubmit} className={styles["feedbackForm"]}>
                            {questions.filter(q => q.show).map((q, index) => (
                                <div key={q.id} className={styles["questionBlock"]}>
                                    <label className={styles["label"]}>
                                        {index + 1}. {q.label}
                                    </label>
                                    {q.type === "likert" && (
                                        <div className={styles["likertContainer"]}>
                                            {["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"].map((label, labelIndex) => {
                                                const value = labelIndex + 1;
                                                return (
                                                    <button
                                                        key={value}
                                                        type="button"
                                                        className={`${styles["likertButton"]} ${responses[q.id] === value ? styles["selected"] : ""}`}
                                                        onClick={() => handleInputChange(q.id, value)}
                                                    >
                                                        {label}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </form>
                        <button type="submit" className={styles["submitButton"]}>
                            Submit Feedback
                        </button>
                    </>
                )}
            </div>

            <GenericDialogBox show={false}>
                <div className={styles["dialogContent"]}>
                    <h2>Loading Feedback Form...</h2>
                    <AppSpinner />
                </div>
            </GenericDialogBox>
        </>
    );
}

export { FeedbackFormPage };
