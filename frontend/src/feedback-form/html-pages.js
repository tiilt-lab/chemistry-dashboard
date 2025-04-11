import styles from './session-feedback-form.module.css';
import { AppSpinner } from '../spinner/spinner-component';
import { GenericDialogBox } from '../dialog/dialog-component';
import { Appheader } from '../header/header-component';
import React from 'react';

function FeedbackFormPage({ loading, sessionId, onClose }) {
    return (
        <>
            <div className={styles.feedbackPage}>
                {loading ? (
                    <div className={styles.loadingContainer}>
                        <AppSpinner />
                        <p>Loading feedback form...</p>
                    </div>
                ) : (
                    <div className={styles.formContainer}>
                        <p>Scan the QR code to provide feedback on your phone:</p>
                        <div className={styles.qrCodeWrapper}>
                            <img
                                src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${window.location.origin}/feedback-form/${sessionId}`}
                                alt="Feedback QR Code"
                            />
                        </div>
                        <p>or <a href={`/feedback-form/${sessionId}`} target="_blank" rel="noopener noreferrer">click here</a> to fill out the form.</p>
                    </div>
                )}
            </div>

            <GenericDialogBox show={loading}>
                <div className={styles.dialogContent}>
                    <h2>Loading Feedback Form...</h2>
                    <AppSpinner />
                </div>
            </GenericDialogBox>
        </>
    );
}

export { FeedbackFormPage };
