import React from "react"
import { btnPrimaryTall } from "../components/dialog-styles"
import { ErrorDialog } from "../components/error-dialog"
import { Appheader } from "../header/header-component"
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
                        Choose a username and, if your class works in groups,
                        enter your group and team. On the next page you will
                        record a short sample so BLINC can recognize you
                        during analytics. Enrolled before? Enter the same
                        username, group and team to record a fresh sample —
                        it replaces your old one.
                    </p>

                    {/* No name is asked for: the username is how a student
                        appears in transcripts, and the group and team are
                        what the class calls them (the coding pass reads the
                        team off the profile). */}
                    <div className="flex max-w-md flex-col gap-4">
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
                                placeholder="5–10 letters and numbers"
                                className={inputClass}
                            />
                            <span className="text-xs text-tiilt-muted">
                                How you appear in transcripts. It must be unique,
                                so make it your own.
                            </span>
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label
                                htmlFor="group"
                                className="text-sm font-semibold text-tiilt-ink"
                            >
                                Group
                            </label>
                            <input
                                id="group"
                                maxLength={64}
                                autoComplete="off"
                                placeholder="e.g. Group 3"
                                className={inputClass}
                            />
                            <span className="text-xs text-tiilt-muted">
                                The group or table your class put you in, as
                                your instructor names it. Leave blank if there
                                are none.
                            </span>
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label
                                htmlFor="team"
                                className="text-sm font-semibold text-tiilt-ink"
                            >
                                Team
                            </label>
                            <input
                                id="team"
                                maxLength={64}
                                autoComplete="off"
                                placeholder="e.g. Team A"
                                className={inputClass}
                            />
                            <span className="text-xs text-tiilt-muted">
                                Your team or role within the group, if your
                                class has them.
                            </span>
                        </div>
                        {/* Voice only skips the camera entirely: a device
                            without one, or a student who would rather not be
                            filmed. It is all an audio-only session needs. */}
                        <fieldset className="flex flex-col gap-2">
                            <legend className="mb-1.5 text-sm font-semibold text-tiilt-ink">
                                What to enroll
                            </legend>
                            <label className="flex cursor-pointer items-start gap-2.5 text-sm text-tiilt-ink">
                                <input
                                    type="radio"
                                    name="enrollMode"
                                    value="both"
                                    defaultChecked
                                    className="mt-1 h-4 w-4 flex-none cursor-pointer accent-tiilt"
                                />
                                <span>
                                    Voice and face
                                    <span className="block text-xs text-tiilt-muted">
                                        Needs a camera and a microphone. BLINC can
                                        then recognize you on video as well as in
                                        audio.
                                    </span>
                                </span>
                            </label>
                            <label className="flex cursor-pointer items-start gap-2.5 text-sm text-tiilt-ink">
                                <input
                                    type="radio"
                                    name="enrollMode"
                                    value="voice"
                                    className="mt-1 h-4 w-4 flex-none cursor-pointer accent-tiilt"
                                />
                                <span>
                                    Voice only
                                    <span className="block text-xs text-tiilt-muted">
                                        Microphone only, no camera. Enough for
                                        sessions recorded with audio.
                                    </span>
                                </span>
                            </label>
                        </fieldset>

                        <button
                            className={btnPrimaryTall}
                            onClick={() =>
                                props.verifyUserProfileInput(
                                    document
                                        .getElementById("username")
                                        .value.trim(),
                                    document
                                        .getElementById("group")
                                        .value.trim(),
                                    document
                                        .getElementById("team")
                                        .value.trim(),
                                    (document.querySelector('input[name="enrollMode"]:checked') || {}).value === "voice",
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
                        voiceOnly={props.voiceOnly === true}
                        maxDurationSec={60}
                        minDurationSec={30}
                        onTestClip={() => {}}
                        onComplete={() => {}}
                        saveRecording={props.saveRecording}
                        enrollStatus={props.enrollStatus}
                        onDoneEnrolling={props.onDoneEnrolling}
                        onSkipEnrolling={props.onSkipEnrolling}
                    />
                </div>
            )}

            <ErrorDialog message={props.alertMessage} show={props.showAlert} onClose={props.closeAlert} />

            {/* Save spinner + success/failure now render inline in the
                RecordingCoach (see enrollStatus) rather than as popups. */}
        </>
    )
}

export { ProfileCreationPage }
