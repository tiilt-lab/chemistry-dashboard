import style from './timeline.module.css'
import { formatSeconds } from '../globals';
import { useEffect, useState } from 'react';


function AppTimeline(props) {
    const TIMELINE_LEFT = 16;
    const TIMELINE_WIDTH = 341;
    const MIN_UTTERANCE_WIDTH = 1;
    const [_transcripts, setTranscripts] = useState(props.transcripts)
    const [displayTranscripts, setDisplayTranscripts] = useState([]);
    const [previousTranscriptCount, setPreviousTranscriptCount] = useState(0);
    const [startText, setStartText] = useState('Start');
    const [endText, setEndText] = useState('Now');
    const [_start, setStart] = useState();
    const [_end, setEnd] = useState();
    //const [reload, setReload] = useState(false);

    useEffect(() => {
        if (props.transcripts !== undefined) {
            setTranscripts(props.transcripts);
            refreshTimeline();
        }

        if (props.start !== undefined) {
            setStart(props.start);
            if (props.start === 0) {
                setStartText('Start');
            } else {
                setStartText(formatSeconds(_start));
            }
            refreshTimeline();
        }

        if (props.end !== undefined) {
            setEnd(props.end);
            if (props.end === props.session.length) {
                setEndText((props.session.recording) ? 'Now' : 'End');
            } else {
                setEndText(formatSeconds(_end));
            }
            refreshTimeline();
        }
        //setReload(true)
    }, [props.transcripts])


    const refreshTimeline = () => {
        const duration = _end - _start;
        const temptranscript = [] 
        if(props.transcripts !== undefined){
        for (const transcript of props.transcripts) {
            const pct_start = (transcript.start_time - _start) / duration;
            const pct_length = transcript.length / duration;
            const displayTranscript = {};
            displayTranscript['transcript'] = transcript;
            displayTranscript['left'] = pct_start * TIMELINE_WIDTH + TIMELINE_LEFT;
            displayTranscript['width'] = Math.min(Math.max(pct_length * TIMELINE_WIDTH,
                MIN_UTTERANCE_WIDTH), TIMELINE_WIDTH * (1 - pct_start));
                temptranscript.push(displayTranscript);
        }
    }
        setDisplayTranscripts(temptranscript);
    }

    const openTranscriptDialog = (transcript) => {
        props.clickedTimeline(transcript);
    }
   

    return (
        <div className={style["timeline-container"]}>
            <div className={style.legend}>
                <span className={`${style["color-box"]} ${style.question}`}></span>
                <span className={style["legend-text"]}>Question</span>
                <span className={`${style["color-box"]} ${style.discussion}`}></span>
                <span className={style["legend-text"]}>Discussion</span>
                <span className={`${style["color-box"]} ${style.silence}`}></span>
                <span className={style["legend-text"]}>Silence</span>
            </div>
            <div className={style.line}></div>
            <div className={style.timeline}>
                {
                    displayTranscripts.map((transcript, index) => (
                        <span key={index}>
                            <span
                                className={transcript.transcript.question ? `${style["utterance"]} ${style["question"]}` : style["utterance"]}
                                onClick={() => openTranscriptDialog(transcript.transcript)}
                                style={{ left: `${transcript.left}` + 'px', width: `${transcript.width}` + 'px' }}>
                            </span>
                        </span>
                    ))
                }

            </div>
            <div className={style["time-textbox"]}>
                <div className={style["time-text"]}>{startText}</div>
                <div className={style["time-text"]}>{endText}</div>
            </div>
        </div>
    )
}

export {AppTimeline}