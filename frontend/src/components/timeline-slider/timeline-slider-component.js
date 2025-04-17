import { useEffect, useState, useRef } from "react";
import style from './timeline-slider.module.css';
import { adjDim } from '../../myhooks/custom-hooks';

function AppTimelineSlider(props) {
  const [min, setMin] = useState(0.0);
  const [max, setMax] = useState(1.0);
  //const [draggingHandle, setDraggingHandle] = useState(null);
  const draggingHandleRef = useRef(null);

  const TIMELINE_WIDTH = adjDim(280);
  const HANDLE_WIDTH = adjDim(20);
  const timelineBackgroundRef = useRef(null);

  useEffect(() => {
    // Initial update to parent component
    props.inputChanged([min, max]);
  }, []);

  // Send updated slider values to parent
  const sendUpdate = () => {
    props.inputChanged([min, max]);
  };

  // Calculate pixel position for each handle based on normalized values
  const handlePos = (handleId) => {
    return (handleId === 0 ? min : max) * TIMELINE_WIDTH + 'px';
  };

  // Calculate the left position of the timeline bar
  const barLeft = () => {
    return ((min * TIMELINE_WIDTH) + (HANDLE_WIDTH / 2)) + 'px';
  };

  // Calculate the width of the timeline bar
  const barWidth = () => {
    return ((max - min) * TIMELINE_WIDTH) + 'px';
  };

  // Function to start dragging
  const startDragging = (handleId, e) => {
    e.preventDefault(); // prevent text selection or unwanted behavior
    //setDraggingHandle(handleId);
    draggingHandleRef.current = handleId;

    // Listen on document for smoother dragging, even outside the slider area
    document.addEventListener('mousemove', handleDrag);
    document.addEventListener('mouseup', stopDragging);
    console.log("Dragging started for handle:", handleId);
  };

  // Handle dragging movement
  const handleDrag = (e) => {
    //if (draggingHandle === null) return;
    if (draggingHandleRef.current === null) return;

    moveHandle(draggingHandleRef.current, e);
    console.log("handleDrag called");

  };

  // Stop dragging and clean up event listeners
  const stopDragging = () => {
    draggingHandleRef.current = null;
    document.removeEventListener('mousemove', handleDrag);
    document.removeEventListener('mouseup', stopDragging);
    sendUpdate();
  };

  // Move the handle based on mouse position
  const moveHandle = (handleId, e) => {
    if (!timelineBackgroundRef.current) return; // Add safety check

    // Get timeline's position relative to the viewport
    const rect = timelineBackgroundRef.current.getBoundingClientRect();
    const offset = rect.x;
    const newVal = e.clientX - offset;

    // Add some logging to debug
    console.log(`Moving handle ${handleId}, clientX: ${e.clientX}, offset: ${offset}, newVal: ${newVal}`);

    // Update state based on which handle is being dragged
    if (handleId === 0 && newVal + HANDLE_WIDTH <= max * TIMELINE_WIDTH) {
      const newMin = Math.min(Math.max(0, newVal), (max * TIMELINE_WIDTH) - HANDLE_WIDTH) / TIMELINE_WIDTH;
      setMin(newMin);

      console.log(`Setting min to: ${newMin}`);
    }
    if (handleId === 1 && newVal >= (min * TIMELINE_WIDTH) + HANDLE_WIDTH) {
      const newMax = Math.min(Math.max((min * TIMELINE_WIDTH) + HANDLE_WIDTH, newVal), TIMELINE_WIDTH) / TIMELINE_WIDTH;
      setMax(newMax);
      console.log(`Setting max to: ${newMax}`);
    }
  };

  return (
    <div className={style.timeline}>
      <div 
        className={style["timeline-background"]}
        style={{ width: TIMELINE_WIDTH + 'px' }}
        ref={timelineBackgroundRef}
      ></div>
      <div 
        className={style["timeline-bar"]} 
        style={{ left: barLeft(), width: barWidth() }}
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
      <div className={style["timeline-text"]} style={{ left: "0px", top: "50px" }}>
        {props.leftText}
      </div>
      <div className={style["timeline-text"]} style={{ right: "0px", top: "50px" }}>
        {props.rightText}
      </div>
    </div>
  );
}

export { AppTimelineSlider };
