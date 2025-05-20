import React from "react";
import { QRCodeCanvas } from "qrcode.react";
import style from "./session-qrcode.module.css";

function SessionQRCode({ sessionId }) {
  if (!sessionId) return null;

  const feedbackLink = `${window.location.origin}/feedback-form/${sessionId}`;
  // const feedbackLink = "https://example.com/";

  console.log("Feedback Link:", feedbackLink);
  console.log("Session ID:", sessionId);

  return (
    <div className={style.qrContainer}>
      <div className={style.qrBox}>
        <h2 className={style.title}>Scan to Give Feedback</h2>
        <QRCodeCanvas value={feedbackLink} size={256} />
        <p className={style.instructions}>
          Scan the QR code with your phone to submit feedback or click the link below.
        </p>
        <a className="option-button small-section" href={feedbackLink} >Submit Feedback</a>
      </div>
    </div>
  );
}

export default SessionQRCode;
