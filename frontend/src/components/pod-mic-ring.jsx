import MicIcon from "@icons/Mic"
import { GLOW_COLOR } from "./pod-colors"

// The 80x80 mic-in-ring pod visualization (mic glyph + steady ring + pulsing
// glow while the pod button is pressed). Was copy-pasted between
// student-dashboard and byod-join.
function PodMicRing({ color, pulsing = false, glowColor = GLOW_COLOR, pulseClassName, className, style }) {
    return (
        <svg
            width="80px"
            height="80px"
            viewBox="-40 -40 80 80"
            className={className}
            style={style}
        >
            <svg x="-8.5" y="-13.5" width="17" height="27" viewBox="0 0 17 27">
                <MicIcon fill={color} />
            </svg>
            {pulsing ? (
                <svg>
                    <circle
                        className={pulseClassName}
                        r="33.5"
                        fillOpacity="0"
                        stroke={glowColor}
                    />
                </svg>
            ) : null}
            <svg>
                <circle r="30.5" fillOpacity="0" strokeWidth="3" stroke={color} />
            </svg>
        </svg>
    )
}

export { PodMicRing }
