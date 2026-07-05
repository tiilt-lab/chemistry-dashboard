import { useNavigate } from "react-router-dom"
import { updateTime } from "../utilities/helper-functions"
import { BrandCard } from "../components/brand-panel"

const timeOfDay = updateTime()

const primaryClass =
    "flex h-12 items-center justify-center rounded-lg bg-tiilt text-base font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
const secondaryClass =
    "flex h-12 items-center justify-center rounded-lg border border-tiilt-line bg-white text-base font-semibold text-tiilt transition hover:border-tiilt hover:bg-tiilt-soft active:translate-y-px"

function LandingPageComponent() {
    const navigate = useNavigate()

    return (
        <BrandCard>
            <h1 className="text-xl font-semibold text-tiilt-ink">
                Good {timeOfDay}!
            </h1>
            <p className="mt-1 mb-6 text-sm text-tiilt-muted">
                Welcome to the BLINC platform. Sign in to manage recordings, or
                join a live session.
            </p>

            <div className="flex max-w-md flex-col gap-3">
                <button
                    className={primaryClass}
                    onClick={() => navigate("/login")}
                >
                    Sign in
                </button>
                <div className="grid grid-cols-2 gap-3">
                    <button
                        className={secondaryClass}
                        onClick={() => navigate("/join")}
                    >
                        Join session
                    </button>
                    <button
                        className={secondaryClass}
                        onClick={() => navigate("/signup")}
                    >
                        Create account
                    </button>
                </div>

                <div className="mt-4 border-t border-tiilt-line pt-4">
                    <div className="mb-2 font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                        Students &amp; raters
                    </div>
                    <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
                        <button
                            className="font-semibold text-tiilt hover:underline"
                            onClick={() => navigate("/student/dashboard")}
                        >
                            Student dashboard
                        </button>
                        <button
                            className="font-semibold text-tiilt hover:underline"
                            onClick={() => navigate("/student/survey")}
                        >
                            Submit survey
                        </button>
                        <button
                            className="font-semibold text-tiilt hover:underline"
                            onClick={() => navigate("/expert/rating")}
                        >
                            Expert rating
                        </button>
                    </div>
                </div>
            </div>
        </BrandCard>
    )
}
export default LandingPageComponent
