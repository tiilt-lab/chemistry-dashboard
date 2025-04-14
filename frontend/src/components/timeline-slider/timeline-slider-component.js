/*import { useEffect, useState, useRef } from "react";
import style from './timeline-slider.module.css';
import { adjDim } from '../../myhooks/custom-hooks';
//import ReactSlider from 'react-slider';

function AppTimelineSlider(props) {
  
  DEFAULT CODE
  const [currentSliderId, setCurrentSliderId] = useState(null);
  const [curPos, setCurPos] = useState(0);
  const [sliderValues, setSliderValues] = useState([0.0, 1.0]);
  const TIMELINE_WIDTH = adjDim(280);
  const HANDLE_WIDTH = adjDim(20);
  //const [trigger, setTrigger] = useState(0);


  useEffect(() => {
    props.inputChanged(sliderValues);
  }, [])

  const sendUpdate = () => {
    console.log("Slider values sent from slider component");
    console.log(sliderValues);
    props.inputChanged(sliderValues);
  }

  // -----------
  // Handles
  // -----------

  const handlePos = (handleId) => {
    console.log(sliderValues);
    return (sliderValues[handleId] * TIMELINE_WIDTH) + 'px';
  }

  const grabHandle = (handleId, e) => {
    if (currentSliderId != null) {
      releaseHandle(null);
    }
    setCurrentSliderId((oldId) => {
      return handleId;
    });
    if (window.TouchEvent && e instanceof TouchEvent) {
      setCurPos(e.changedTouches[0].clientX);
      document.addEventListener('touchend', releaseHandle);
      document.addEventListener('touchmove', moveHandle);
    } else {
      setCurPos(e.clientX);
      document.addEventListener('mouseup', releaseHandle);
      document.addEventListener('mousemove', moveHandle);
    }
  }

  const moveHandle = (e) => {
    const newPos = window.TouchEvent && e instanceof TouchEvent ? e.changedTouches[0].clientX : e.clientX;
    setCurPos((prevPos) => {
      const change = newPos - prevPos;
      if (currentSliderId === 0) {
        setSliderValues((prevValues) => {
          const newValues = [...prevValues];
          newValues[0] = Math.min(Math.max(0, (newValues[0] * TIMELINE_WIDTH) + change),
        (newValues[1] * TIMELINE_WIDTH) - HANDLE_WIDTH) / TIMELINE_WIDTH;
          return newValues;
        });
      } else {
        setSliderValues((prevValues) => {
          const newValues = [...prevValues];
          newValues[1] = Math.min(Math.max((newValues[0] * TIMELINE_WIDTH) + HANDLE_WIDTH,
        (newValues[1] * TIMELINE_WIDTH) + change), TIMELINE_WIDTH) / TIMELINE_WIDTH;
          return newValues;
        });
      }
      return newPos;
    });
  }

  const releaseHandle = (e) => {
    if (window.TouchEvent && e instanceof TouchEvent) {
      document.removeEventListener('touchend', releaseHandle);
      document.removeEventListener('touchmove', moveHandle);
    } else {
      document.removeEventListener('mouseup', releaseHandle);
      document.removeEventListener('mousemove', moveHandle);
    }
    sendUpdate();
    //setCurrentSliderId(null);
  }

  // -----------
  // Bar
  // -----------

  const barLeft = () => {
    return ((sliderValues[0] * TIMELINE_WIDTH) + (HANDLE_WIDTH / 2)) + 'px';
  }

  const barWidth = () => {
    return ((sliderValues[1] - sliderValues[0]) * TIMELINE_WIDTH) + 'px';
  }

  const grabBar = (e) => {
    if (currentSliderId != null) {
      releaseHandle(null);
    }
    if (window.TouchEvent && e instanceof TouchEvent) {
      setCurPos(e.changedTouches[0].clientX);
      document.addEventListener('touchend', releaseBar);
      document.addEventListener('touchmove', moveBar);
    } else {
      setCurPos(e.clientX);
      document.addEventListener('mousemove', moveBar);
      document.addEventListener('mouseup', releaseBar);
    }
  }

  const moveBar = (e) => {
    //console.log("Sliding");
    console.log(sliderValues);
    const newPos = window.TouchEvent && e instanceof TouchEvent ? e.changedTouches[0].clientX : e.clientX;
    setCurPos((prevPos) => {
      //console.log("curPos render");
      const change = newPos - prevPos;
      if (change < 0) {
        setSliderValues((prevValues) => {
          //console.log("sliderValue render");
          const newValues = [...prevValues];
          newValues[0] = Math.max(0, prevValues[0] * TIMELINE_WIDTH + change) / TIMELINE_WIDTH;
          newValues[1] -= Math.abs(prevValues[0] - newValues[0]);
          //sendUpdate();
          //console.log(newValues);
          return newValues;
        });
      } else if (change > 0) {
        setSliderValues((prevValues) => {
          //console.log("sliderValue render");
          const newValues = [...prevValues];
          newValues[1] = Math.min(prevValues[1] * TIMELINE_WIDTH + change, TIMELINE_WIDTH) / TIMELINE_WIDTH;
          newValues[0] += Math.abs(prevValues[1] - newValues[1]);
          //sendUpdate();
          //console.log(newValues);
          console.log(sliderValues);
          return newValues;
        });
      }
      return newPos;
    });
    //sendUpdate();
  }

  const releaseBar = (e) => {
    if (window.TouchEvent && e instanceof TouchEvent) {
      document.removeEventListener('touchend', releaseBar);
      document.removeEventListener('touchmove', moveBar);
    } else {
      document.removeEventListener('mouseup', releaseBar);
      document.removeEventListener('mousemove', moveBar);
    }
    sendUpdate();
  }

  return (
    <div className={style.timeline}>

      <ReactSlider
    //className="timeline-background"
    //thumbClassName="timeline-handle"
    //trackClassName="example-track"
    defaultValue={[0, 100]}
    //ariaLabel={['Lower thumb', 'Upper thumb']}
    //ariaValuetext={state => `Thumb value ${state.valueNow}`}
    onChange = {(vals) => {sendUpdate(vals)}}
    //onAfterChange = {(vals) => {sendUpdate(vals)}}
    renderThumb={(props, state) => <div {...props}>{state.valueNow}</div>}
    //pearling
    minDistance={10}
/>

      <div className={style["timeline-text"]} style={{ left: "0px", top: "50px" }}>{props.leftText}</div>
      <div className={style["timeline-text"]} style={{ right: "0px", top: "50px" }}>{props.rightText}</div>
    </div>
  )*/
  
  /* In btwn the timeline background and timeline text
<div className={style["timeline-background"]}
      style={{ width: adjDim(280) + 'px',}}></div>
<div className={style["timeline-bar"]} onMouseDown={(event) => grabBar(event)} onTouchStart={(event) => grabBar(event)} style={{ left: barLeft(), width: barWidth() }}></div>
      <div className={style["timeline-handle"]} onMouseDown={(event) => grabHandle(0, event)} onTouchStart={(event) => grabHandle(0, event)} style={{ left: handlePos(0) }}></div>
      <div className={style["timeline-handle"]} onMouseDown={(event) => grabHandle(1, event)} onTouchStart={(event) => grabHandle(1, event)} style={{ left: handlePos(1) }}></div>
      
<ReactSlider
    //className="timeline-background"
    //thumbClassName="timeline-handle"
    //trackClassName="example-track"
    defaultValue={[0, 100]}
    //ariaLabel={['Lower thumb', 'Upper thumb']}
    //ariaValuetext={state => `Thumb value ${state.valueNow}`}
    onChange = {(vals) => {sendUpdate(vals)}}
    //onAfterChange = {(vals) => {sendUpdate(vals)}}
    renderThumb={(props, state) => <div {...props}>{state.valueNow}</div>}
    //pearling
    minDistance={10}
/>*/
  
  //TRY NEW CODE HERE
/* 
  const [min, setMin] = useState(0.0);
  const [max, setMax] = useState(1.0);
  const TIMELINE_WIDTH = adjDim(280);
  const HANDLE_WIDTH = adjDim(20);
  const timelineBackgroundRef = useRef(null);
  
  useEffect(() => {
    let sliderValues = [min, max];
    props.inputChanged(sliderValues);
  }, [])

  const sendUpdate = () => {
    let sliderValues = [min, max];
    props.inputChanged(sliderValues);
  }
  
  const handlePos = (handleId) => {
    let sliderValues = [min, max];
    return (sliderValues[handleId] * TIMELINE_WIDTH) + 'px';
  }
  
  const barLeft = () => {
    return ((min * TIMELINE_WIDTH) + (HANDLE_WIDTH / 2)) + 'px';
  }

  const barWidth = () => {
    return ((max - min) * TIMELINE_WIDTH) + 'px';
  }
  
  const moveHandle = (handleId, e) => {
    //calculate distance of left of screen to left of timeline
    const element = timelineBackgroundRef.current;
    const rect = element.getBoundingClientRect();
    const offset = rect.x;
    //so position of your mouse in respect to the timeline
    const newVal = e.clientX - offset;
    if (handleId == 0 && (max * TIMELINE_WIDTH) >= newVal + HANDLE_WIDTH) {
      let val = Math.min(Math.max(0, newVal),
      (max * TIMELINE_WIDTH) - HANDLE_WIDTH) / TIMELINE_WIDTH;
      setMin(val);
    }
    if (handleId == 1 && newVal >= (min * TIMELINE_WIDTH) + HANDLE_WIDTH) {
      let val = Math.min(Math.max((min * TIMELINE_WIDTH) + HANDLE_WIDTH,
      newVal), TIMELINE_WIDTH) / TIMELINE_WIDTH;
      setMax(val);
    }
    sendUpdate();
  }
    
  
  return (
    <div className={style.timeline}>
      <div className={style["timeline-background"]}
      style={{ width: adjDim(280) + 'px',}} ref={timelineBackgroundRef}></div>
      <div className={style["timeline-bar"]} style={{ left: barLeft(), width: barWidth() }}></div>
      <div className={style["timeline-handle"]} onMouseMove={(event) => moveHandle(0, event)} style={{ left: handlePos(0) }}></div>
      <div className={style["timeline-handle"]} onMouseMove={(event) => moveHandle(1, event)} style={{ left: handlePos(1) }}></div>
      <div className={style["timeline-text"]} style={{ left: "0px", top: "50px" }}>{props.leftText}</div>
      <div className={style["timeline-text"]} style={{ right: "0px", top: "50px" }}>{props.rightText}</div>
    </div>
  )
  
}
export { AppTimelineSlider }

*/

import { useEffect, useState, useRef } from "react";
import style from './timeline-slider.module.css';
import { adjDim } from '../../myhooks/custom-hooks';

function AppTimelineSlider(props) {
  const [min, setMin] = useState(0.0);
  const [max, setMax] = useState(1.0);
  const [draggingHandle, setDraggingHandle] = useState(null);
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
    setDraggingHandle(handleId);
    // Listen on document for smoother dragging, even outside the slider area
    document.addEventListener('mousemove', handleDrag);
    document.addEventListener('mouseup', stopDragging);
  };

  // Handle dragging movement
  const handleDrag = (e) => {
    if (draggingHandle === null) return;
    moveHandle(draggingHandle, e);
  };

  // Stop dragging and clean up event listeners
  const stopDragging = () => {
    setDraggingHandle(null);
    document.removeEventListener('mousemove', handleDrag);
    document.removeEventListener('mouseup', stopDragging);
    sendUpdate();
  };

  // Replace the existing moveHandle function with this updated version:
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
