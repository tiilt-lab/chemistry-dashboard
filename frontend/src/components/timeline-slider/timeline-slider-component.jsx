import { useEffect, useState, useRef } from "react";
import style from "./timeline-slider.module.css";
import { adjDim } from "../../myhooks/custom-hooks";

function AppTimelineSlider(props) {
  const [min, setMin] = useState(0.0);
  const [max, setMax] = useState(1.0);
  const [dragging, setDragging] = useState(false);
  const initalDragPos = useRef([-1,-1]);
  //const [draggingHandle, setDraggingHandle] = useState(null);
  const draggingHandleRef = useRef(null);

  const TIMELINE_WIDTH = 100;
  const HANDLE_WIDTH = 4;
  const timelineBackgroundRef = useRef(null);

  useEffect(() => {
    // Initial update to parent component
    sendUpdate();
  }, []);

  useEffect(() => {
    sendUpdate();
  }, [dragging, min, max]);

  // Send updated slider values to parent
  const sendUpdate = () => {
    if (!dragging) {
      console.log("Handle finish dragging")
      props.inputChanged([min, max]);
      initalDragPos.current = [-1,-1]
    }
  };

  // Calculate pixel position for each handle based on normalized values
  const handlePos = (handleId) => {
    return (handleId === 0 ? min : max) * TIMELINE_WIDTH + "%";
  };

  // Calculate the left position of the timeline bar
  const barLeft = () => {
    return min * TIMELINE_WIDTH + "%";
  };

  // Calculate the width of the timeline bar
  const barWidth = () => {
    return (max - min) * TIMELINE_WIDTH + "%";
  };

  // Function to start dragging
  const startDragging = (handleId, e) => {
    e.preventDefault(); // prevent text selection or unwanted behavior
    //setDraggingHandle(handleId);
    draggingHandleRef.current = handleId;
    initalDragPos.current =  [e.clientX, e.clientY]

    // Listen on document for smoother dragging, even outside the slider area
    document.addEventListener("mousemove", handleDrag);
    document.addEventListener("mouseup", stopDragging);
    //console.log("Dragging started for handle:", handleId);  
    setDragging(true);
  };

  // Handle dragging movement
  const handleDrag = (e) => {
    //if (draggingHandle === null) return;
    if (draggingHandleRef.current === null || initalDragPos[0] === -1) return;

    moveHandles(draggingHandleRef.current, e);

    //console.log("handleDrag called");
  };


  // Stop dragging and clean up event listeners
  const stopDragging = () => {
    draggingHandleRef.current = null;
    document.removeEventListener("mousemove", handleDrag);
    document.removeEventListener("mouseup", stopDragging);
    setDragging(false);
  };

  // Move the handle based on mouse position
  const moveHandles = (handleId, e) => {
    console.log(handleId)
    if (!timelineBackgroundRef.current) return; // Add safety check

    // Get timeline's position relative to the viewport
    const rect = timelineBackgroundRef.current.getBoundingClientRect();
    const left = rect.x;
    const right = rect.right;
    const delta = (e.clientX - initalDragPos.current[0]) / (right-left);
    console.log(e.clientX)
    console.log(initalDragPos.current[0])
    console.log(delta)

    // Add some logging to debug
    //console.log(`Moving handle ${handleId}, clientX: ${e.clientX}, offset: ${offset}, end: ${end}, delta: ${delta}`);
    const newMin = handleId === 1 ? min : min + delta
    const newMax =  handleId === 0 ? max : max + delta;
    if(newMax > 1)
      return;
    // Update state based on which handle is being dragged
    if (handleId === 0 || handleId ===2) {
      if(newMin < 0 || newMin > newMax - HANDLE_WIDTH/TIMELINE_WIDTH)
        return;
      setMin(newMin);
      console.log(`Setting min to: ${newMin}`);
    }
    if (handleId === 1 || handleId === 2) {
      if(newMax < newMin + HANDLE_WIDTH/TIMELINE_WIDTH)
        return;
      setMax(newMax);
      console.log(`Setting max to: ${newMax}`);
    }
  };

  return (
    <div className={style.timeline}>
      <div
        className={style["timeline-background"]}
        style={{ width: TIMELINE_WIDTH + "%" }}
        ref={timelineBackgroundRef}
      ></div>
      <div
        className={style["timeline-bar"]}
        style={{ left: barLeft(), width: barWidth() }}
        onMouseDown={(e) => startDragging(2, e)}

      ></div>
      <div
        className={style["timeline-handle"]}
        onMouseDown={(e) => startDragging(0, e)}
        style={{ left: handlePos(0) }}
      ></div>
      <div
        className={style["timeline-handle"]}
        onMouseDown={(e) => startDragging(1, e)}
        style={{ left: handlePos(1) }}
      ></div>
      <div
        className={style["timeline-text"]}
        style={{ left: "0px", top: "50px" }}
      >
        {props.leftText}
      </div>
      <div
        className={style["timeline-text"]}
        style={{ right: "0px", top: "50px" }}
      >
        {props.rightText}
      </div>
    </div>
  );
}

export { AppTimelineSlider };
