import { useNavigate } from "react-router-dom"
import { updateTime } from "../utilities/helper-functions"
import { BrandCard } from "../components/brand-panel"

import { btnPrimaryTall as primaryClass, btnSecondaryTall as secondaryClass } from "../components/dialog-styles"

const timeOfDay = updateTime()

// Small tertiary action used inside the audience panels.
const linkBtn =
    "cursor-pointer rounded-lg border border-tiilt-line bg-white px-3 py-2 text-sm font-semibold text-tiilt-ink transition hover:border-tiilt hover:bg-tiilt-soft hover:text-tiilt"

function LandingPageComponent() {
    const navigate = useNavigate()

    return (
        <BrandCard>
            <h1 className="text-xl font-semibold text-tiilt-ink">
                Good {timeOfDay}!
            </h1>
            <p className="mt-1 mb-5 text-sm text-tiilt-muted">
                Welcome to the BLINC platform.
            </p>

            <div className="flex flex-col gap-4">
                {/* Students: reflect on past discussions, enroll, surveys.
                    (Recording devices are joined to live sessions by the
                    instructor, not by students — that lives below.) */}
                <section className="rounded-xl border border-tiilt-line bg-tiilt-ground/50 p-4">
                    <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                        Students
                    </div>
                    <p className="mt-1 mb-3 text-sm text-tiilt-muted">
                        Look back on your group discussions, or set up how BLINC
                        recognizes you.
                    </p>
                    <button
                        className={primaryClass + " w-full"}
                        onClick={() => navigate("/student/dashboard")}
                    >
                        My reflection dashboard
                    </button>
                    <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                        <button
                            className={linkBtn}
                            onClick={() => navigate("/signup")}
                            title="Record the voice and face sample BLINC uses to recognize you. Re-enroll any time with the same username."
                        >
                            Enroll voice &amp; face
                        </button>
                        <button
                            className={linkBtn}
                            onClick={() => navigate("/student/survey")}
                        >
                            Submit survey
                        </button>
                    </div>
                </section>

                {/* Instructors / researchers: sign in, or put a recording
                    device into a live session. */}
                <section className="rounded-xl border border-tiilt-line p-4">
                    <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                        Instructors &amp; researchers
                    </div>
                    <p className="mt-1 mb-3 text-sm text-tiilt-muted">
                        Manage sessions and analytics, or connect this device to
                        a running session as a group&apos;s recorder.
                    </p>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        <button
                            className={secondaryClass}
                            onClick={() => navigate("/login")}
                        >
                            Sign in
                        </button>
                        <button
                            className={secondaryClass}
                            onClick={() => navigate("/join")}
                        >
                            Join a live session
                        </button>
                    </div>
                </section>

                <button
                    className="self-start text-sm font-semibold text-tiilt hover:underline"
                    onClick={() => navigate("/expert/rating")}
                >
                    Invited expert? Rate a discussion &rarr;
                </button>
            </div>
        </BrandCard>
    )
}
export default LandingPageComponent
