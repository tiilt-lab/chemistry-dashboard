import { useEffect, useState } from "react";
import style from './timeline-slider.module.css';
import { adjDim } from '../../myhooks/custom-hooks';

function AppTimelineSlider(props) {
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
    props.inputChanged(sliderValues);
  }

  // -----------
  // Handles
  // -----------

  const handlePos = (handleId) => {
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
      document.addEventListener('mouseup', releaseBar);
      document.addEventListener('mousemove', moveBar);
    }
  }

  const moveBar = (e) => {
    const newPos = window.TouchEvent && e instanceof TouchEvent ? e.changedTouches[0].clientX : e.clientX;
    setCurPos((prevPos) => {
      const change = newPos - prevPos;
      if (change < 0) {
        setSliderValues((prevValues) => {
          const newValues = [...prevValues];
          newValues[0] = Math.max(0, prevValues[0] * TIMELINE_WIDTH + change) / TIMELINE_WIDTH;
          newValues[1] -= Math.abs(prevValues[0] - newValues[0]);
          return newValues;
        });
      } else if (change > 0) {
        setSliderValues((prevValues) => {
          const newValues = [...prevValues];
          newValues[1] = Math.min(prevValues[1] * TIMELINE_WIDTH + change, TIMELINE_WIDTH) / TIMELINE_WIDTH;
          newValues[0] += Math.abs(prevValues[1] - newValues[1]);
          return newValues;
        });
      }
      return newPos;
    });
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
      <div className={style["timeline-background"]}
      style={{ width: adjDim(280) + 'px',}}></div>
      <div className={style["timeline-bar"]} onMouseDown={(event) => grabBar(event)} onTouchStart={(event) => grabBar(event)} style={{ left: barLeft(), width: barWidth() }}></div>
      <div className={style["timeline-handle"]} onMouseDown={(event) => grabHandle(0, event)} onTouchStart={(event) => grabHandle(0, event)} style={{ left: handlePos(0) }}></div>
      <div className={style["timeline-handle"]} onMouseDown={(event) => grabHandle(1, event)} onTouchStart={(event) => grabHandle(1, event)} style={{ left: handlePos(1) }}></div>
      <div className={style["timeline-text"]} style={{ left: "0px", top: "50px" }}>{props.leftText}</div>
      <div className={style["timeline-text"]} style={{ right: "0px", top: "50px" }}>{props.rightText}</div>
    </div>
  )
}
export { AppTimelineSlider }
