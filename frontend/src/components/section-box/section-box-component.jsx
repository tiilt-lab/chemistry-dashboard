import React, { useState } from "react"
import style from "./section-box.module.css"

function AppSectionBoxComponent(props) {
    const [isExpanded, setIsExpanded] = useState(true)

    const toggleExpand = () => {
        setIsExpanded(!isExpanded)
        console.log("Toggled! isExpanded:", !isExpanded) // Debugging output
    }

    return (
        <>
            <div
                className={
                    "relative border-black bg-[#FCFDFF] text-center font-sans text-base/relaxed font-normal h-min"
                }
                style={
                    props.maxHeight !== undefined
                        ? { maxHeight: props.maxHeight + "px" }
                        : {}
                }
            >
                <div
                    className="my-2 rounded-sm border-b-black bg-[#375faf] px-0.5 font-sans text-lg/relaxed font-bold text-[#ffffff]"
                    onClick={toggleExpand}
                    style={{ cursor: "pointer" }}
                >
                    {props.heading}
                </div>
                <React.Fragment>{isExpanded && props.children}</React.Fragment>
            </div>
        </>
    )
}

export { AppSectionBoxComponent }
