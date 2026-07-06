import React from "react"
import { btnPrimaryTall } from "../components/dialog-styles"
import { ErrorDialog } from "../components/error-dialog"
import { Appheader } from "../header/header-component"
import { DialogBox, WaitingDialog } from "../dialog/dialog-component"
import { BrandCard } from "../components/brand-panel"
import { RecordingCoach } from "./recording-coach"

const inputClass =
    "h-12 w-full rounded-lg border border-tiilt-line bg-white px-3.5 text-base text-tiilt-ink transition outline-none " +
    "focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"

function ProfileCreationPage(props) {
    return (
        <>
            {props.nextPage === "profile_creation" && (
                <BrandCard>
                    <button
                        onClick={() => props.navigateToLogin()}
                        className="mb-4 self-start text-sm font-semibold text-tiilt-muted hover:text-tiilt"
                    >
                        &larr; Back
                    </button>
                    <h2 className="text-xl font-semibold text-tiilt-ink">
                        {props.pageTitle}
                    </h2>
                    <p className="mt-1 mb-6 text-sm text-tiilt-muted">
                        Enter your name and a username. On the next page you
                        will record a short video so BLINC can match your voice
                        and face during analytics.
                    </p>

                    <div className="flex max-w-md flex-col gap-4">
                        <div className="flex flex-col gap-1.5">
                            <label
                                htmlFor="firstname"
                                className="text-sm font-semibold text-tiilt-ink"
                            >
                                First name
                            </label>
                            <input
                                id="firstname"
                                maxLength={50}
                                autoComplete="given-name"
                                placeholder="First name"
                                className={inputClass}
                            />
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label
                                htmlFor="lastname"
                                className="text-sm font-semibold text-tiilt-ink"
                            >
                                Last name
                            </label>
                            <input
                                id="lastname"
                                maxLength={50}
                                autoComplete="family-name"
                                placeholder="Last name"
                                className={inputClass}
                            />
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label
                                htmlFor="username"
                                className="text-sm font-semibold text-tiilt-ink"
                            >
                                Username
                            </label>
                            <input
                                id="username"
                                minLength={5}
                                maxLength={10}
                                autoCapitalize="off"
                                spellCheck="false"
                                placeholder="5–10 characters"
                                className={inputClass}
                            />
                        </div>

                        <button
                            className={btnPrimaryTall}
                            onClick={() =>
                                props.verifyUserProfileInput(
                                    document
                                        .getElementById("lastname")
                                        .value.trim(),
                                    document
                                        .getElementById("firstname")
                                        .value.trim(),
                                    document
                                        .getElementById("username")
                                        .value.trim(),
                                )
                            }
                        >
                            Continue
                        </button>
                    </div>
                </BrandCard>
            )}

            {props.nextPage === "video_audio_capture_page" && (
                <div role="main" className="main-container">
                    <Appheader
                        title={props.pageTitle}
                        leftText={false}
                        rightText={""}
                        nav={() => props.navigateToLogin()}
                    />
                    <RecordingCoach
                        maxDurationSec={60}
                        minDurationSec={20}
                        onTestClip={(blob, diag) =>
                            console.log("test", blob, diag)
                        }
                        onComplete={(blob, diag) =>
                            console.log("full", blob, diag)
                        }
                        saveRecording={props.saveRecording}
                    />
                </div>
            )}

            <ErrorDialog message={props.alertMessage} show={props.showAlert} onClose={props.closeAlert} />

            <DialogBox
                itsclass={"add-dialog"}
                heading={"Success"}
                message={props.displayText}
                show={props.currentForm === "success"}
                closedialog={props.closeDialog}
            />

            <WaitingDialog
                itsclass={"add-dialog"}
                heading={"Processing..."}
                message={"Please wait..."}
                show={props.currentForm === "processing"}
            />
        </>
    )
}

export { ProfileCreationPage }
