import { useEffect, useState } from "react";
import style from './timeline-slider.module.css'

function AppTimelineSlider(props) {
  const [currentSliderId, setCurrentSliderId] = useState(null);
  const [curPos, setCurPos] = useState();
  const [sliderValues, setSliderValues] = useState([0.0, 1.0]);
  const TIMELINE_WIDTH = 280;
  const HANDLE_WIDTH = 20;


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
    return (sliderValues[handleId] * 280) + 'px';
  }

  const grabHandle = (handleId, e) => {
    if (currentSliderId != null) {
      releaseHandle(null);
    }
    setCurrentSliderId(handleId);
    if (e instanceof TouchEvent) {
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
    let change = 0;
    if (e instanceof TouchEvent) {
      change = e.changedTouches[0].clientX - this.curPos;
      setCurPos(e.changedTouches[0].clientX);
    } else {
      change = e.clientX - curPos;
      setCurPos(e.clientX);
    }

    if (currentSliderId === 0) {
      sliderValues[0] = Math.min(Math.max(0, (sliderValues[0] * TIMELINE_WIDTH) + change),
        (sliderValues[1] * TIMELINE_WIDTH) - HANDLE_WIDTH) / TIMELINE_WIDTH;
    } else {
      sliderValues[1] = Math.min(Math.max((sliderValues[0] * TIMELINE_WIDTH) + HANDLE_WIDTH,
        (sliderValues[1] * TIMELINE_WIDTH) + change), TIMELINE_WIDTH) / TIMELINE_WIDTH;
    }
  }

  const releaseHandle = (e) => {
    if (e instanceof TouchEvent) {
      document.removeEventListener('touchend', releaseHandle);
      document.removeEventListener('touchmove', moveHandle);
    } else {
      document.removeEventListener('mouseup', releaseHandle);
      document.removeEventListener('mousemove', moveHandle);
    }
    sendUpdate();
    setCurrentSliderId(null);
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
    if (e instanceof TouchEvent) {
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
    let change = 0;
    if (e instanceof TouchEvent) {
      change = e.changedTouches[0].clientX - curPos;
      setCurPos(e.changedTouches[0].clientX);
    } else {
      change = e.clientX - curPos;
      setCurPos(e.clientX);
    }
    if (change < 0) {
      const newPos = Math.max(0, sliderValues[0] * TIMELINE_WIDTH + change) / TIMELINE_WIDTH;
      sliderValues[1] -= Math.abs(sliderValues[0] - newPos);
      sliderValues[0] = newPos;
    } else if (change > 0) {
      const newPos = Math.min(sliderValues[1] * TIMELINE_WIDTH + change, TIMELINE_WIDTH) / TIMELINE_WIDTH;
      sliderValues[0] += Math.abs(sliderValues[1] - newPos);
      sliderValues[1] = newPos;
    }
  }

  const releaseBar = (e) => {
    if (e instanceof TouchEvent) {
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
      <div className={style["timeline-background"]}></div>
      <div className={style["timeline-bar"]} onMouseDown={(event) => grabBar(event)} onTouchStart={(event) => grabBar(event)} style={{ left: barLeft(), width: barWidth() }}></div>
      <div className={style["timeline-handle"]} onMouseDown={(event) => grabHandle(0, event)} onTouchStart={(event) => grabHandle(0, event)} style={{ left: handlePos(0) }}></div>
      <div className={style["timeline-handle"]} onMouseDown={(event) => grabHandle(1, event)} onTouchStart={(event) => grabHandle(1, event)} style={{ left: handlePos(1) }}></div>
      <div className={style["timeline-text"]} style={{ left: "0px", top: "50px" }}>{props.leftText}</div>
      <div className={style["timeline-text"]} style={{ right: "0px", top: "50px" }}>{props.rightText}</div>
    </div>
  )
}
export { AppTimelineSlider }