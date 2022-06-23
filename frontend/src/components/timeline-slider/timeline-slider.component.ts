import { Component, OnInit, Output, EventEmitter, Input} from '@angular/core';

@Component({
  selector: 'app-timeline-slider',
  templateUrl: './timeline-slider.component.html',
  styleUrls: ['./timeline-slider.component.scss']
})
export class TimelineSliderComponent implements OnInit {
  @Input('leftText') leftText = 'Start';
  @Input('rightText') rightText = 'End';
  @Output() inputChanged = new EventEmitter<number[]>();
  moveHandleEvent = this.moveHandle.bind(this);
  releaseHandleEvent = this.releaseHandle.bind(this);
  moveBarEvent = this.moveBar.bind(this);
  releaseBarEvent = this.releaseBar.bind(this);
  currentSliderId: number;
  curPos: any;
  sliderValues: number[] = [0.0, 1.0];
  TIMELINE_WIDTH = 280;
  HANDLE_WIDTH = 20;

  constructor() { }

  ngOnInit() {
    this.inputChanged.emit(this.sliderValues);
  }

  sendUpdate() {
    this.inputChanged.emit(this.sliderValues);
  }

  // -----------
  // Handles
  // -----------

  handlePos(handleId: number) {
    return (this.sliderValues[handleId] * 280) + 'px';
  }

  grabHandle(handleId: number, e: any) {
    if (this.currentSliderId != null) {
      this.releaseHandle(null);
    }
    this.currentSliderId = handleId;
    if (e instanceof TouchEvent) {
      this.curPos = e.changedTouches[0].clientX;
      document.addEventListener('touchend', this.releaseHandleEvent);
      document.addEventListener('touchmove', this.moveHandleEvent);
    } else {
      this.curPos = e.clientX;
      document.addEventListener('mouseup', this.releaseHandleEvent);
      document.addEventListener('mousemove', this.moveHandleEvent);
    }
  }

  moveHandle(e: any) {
    let change = 0;
    if (e instanceof TouchEvent) {
      change = e.changedTouches[0].clientX - this.curPos;
      this.curPos = e.changedTouches[0].clientX;
    } else {
      change = e.clientX - this.curPos;
      this.curPos = e.clientX;
    }

    if (this.currentSliderId === 0) {
      this.sliderValues[0] = Math.min(Math.max(0, (this.sliderValues[0] * this.TIMELINE_WIDTH) + change),
                            (this.sliderValues[1] * this.TIMELINE_WIDTH) - this.HANDLE_WIDTH) / this.TIMELINE_WIDTH;
    } else {
      this.sliderValues[1] = Math.min(Math.max((this.sliderValues[0] * this.TIMELINE_WIDTH) + this.HANDLE_WIDTH,
                            (this.sliderValues[1] * this.TIMELINE_WIDTH) + change), this.TIMELINE_WIDTH) / this.TIMELINE_WIDTH;
    }
  }

  releaseHandle(e: any) {
    if (e instanceof TouchEvent) {
      document.removeEventListener('touchend', this.releaseHandleEvent);
      document.removeEventListener('touchmove', this.moveHandleEvent);
    } else {
      document.removeEventListener('mouseup', this.releaseHandleEvent);
      document.removeEventListener('mousemove', this.moveHandleEvent);
    }
    this.sendUpdate();
    this.currentSliderId = null;
  }

  // -----------
  // Bar
  // -----------

  get barLeft(): string {
    return ((this.sliderValues[0] * this.TIMELINE_WIDTH) + (this.HANDLE_WIDTH / 2)) + 'px';
  }

  get barWidth(): string {
    return ((this.sliderValues[1] - this.sliderValues[0]) * this.TIMELINE_WIDTH) + 'px';
  }

  grabBar(e: any) {
    if (this.currentSliderId != null) {
      this.releaseHandle(null);
    }
    if (e instanceof TouchEvent) {
        this.curPos = e.changedTouches[0].clientX;
        document.addEventListener('touchend', this.releaseBarEvent);
        document.addEventListener('touchmove', this.moveBarEvent);
    } else {
        this.curPos = e.clientX;
        document.addEventListener('mouseup', this.releaseBarEvent);
        document.addEventListener('mousemove', this.moveBarEvent);
    }
  }

  moveBar(e: any) {
    let change = 0;
    if (e instanceof TouchEvent) {
      change = e.changedTouches[0].clientX - this.curPos;
      this.curPos = e.changedTouches[0].clientX ;
    } else {
      change = e.clientX - this.curPos;
      this.curPos = e.clientX;
    }
    if (change < 0) {
      const newPos = Math.max(0, this.sliderValues[0] * this.TIMELINE_WIDTH + change) / this.TIMELINE_WIDTH;
      this.sliderValues[1] -= Math.abs(this.sliderValues[0] - newPos);
      this.sliderValues[0] = newPos;
    } else if (change > 0) {
      const newPos = Math.min(this.sliderValues[1] * this.TIMELINE_WIDTH + change, this.TIMELINE_WIDTH) / this.TIMELINE_WIDTH;
      this.sliderValues[0] += Math.abs(this.sliderValues[1] - newPos);
      this.sliderValues[1] = newPos;
    }
  }

  releaseBar(e: any) {
    if (e instanceof TouchEvent) {
      document.removeEventListener('touchend', this.releaseBarEvent);
      document.removeEventListener('touchmove', this.moveBarEvent);
    } else {
      document.removeEventListener('mouseup', this.releaseBarEvent);
      document.removeEventListener('mousemove', this.moveBarEvent);
    }
    this.sendUpdate();
  }
}
