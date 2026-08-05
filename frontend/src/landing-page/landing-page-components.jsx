import { useNavigate } from "react-router-dom"
import { Instruction } from "../utilities/utility-components"
import { updateTime } from "../utilities/helper-functions"
import { isLargeScreen } from "../myhooks/custom-hooks"

const timeOfDay = updateTime()

function Greeting() {
    return (
        <div className="mt-8 mb-1 font-sans text-4xl/relaxed font-bold text-[#6466E3]">
            Good {timeOfDay}!
        </div>
    )
}

function IntroBox() {
    return (
        <div className="wide-section flex flex-col items-center text-center">
            <Greeting />
            <Instruction instructions="Welcome to the BLINC platform. Please sign in to manage recordings or join a session." />
        </div>
    )
}

function LandingPageComponent() {
    const navigate = useNavigate()

    return (
        <div className="main-container items-center">
            <IntroBox />
            <button className="lanky-button" onClick={() => navigate("/login")}>
                Sign In
            </button>

            <button className="lanky-button" onClick={() => navigate("/join")}>
                Join Discussion
            </button>
        </div>
    )
}
export default LandingPageComponent
