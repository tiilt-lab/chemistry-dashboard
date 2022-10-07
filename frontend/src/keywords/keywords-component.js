import { TranscriptModel } from '../models/transcript';
import { formatSeconds, similarityToRGB } from '../globals';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {AppKeywordsPage} from './html-pages'


function AppKeywordsComponent(props) {
  const [displayKeywords, setDisplayKeywords] = useState([]);
  const [showGraph, setShowGraph] = useState(false);
  const [keywordPoints, setKeywordPoints] = useState();
  const [timelineWidth, setTimeLineWidth] = useState(240);
  const [_start, setStart] = useState(props.start);
  const [_end, setEnd]  = useState(props.end);
  const [callbackfunc, setCallbackFunc] = useState();
  const [reload, setReload] = useState(false);
  const navigate = useNavigate()

  
  useEffect(()=>{
  refresh()
  if(props.transcripts.length > 0){
    setReload(true)
  }
  },[props.transcripts])

  const toggleGraph = ()=> {
    setShowGraph(!showGraph);
    refresh();
  }

  const refresh = ()=> {
    if (showGraph) {
      refreshTimeline();
    } else {
      refreshKeywords();
    }
  }

  // --------
  // Text
  // --------

  const refreshKeywords = ()=> {
    const dispKeyword = [];
    for (const transcript of props.transcripts) {
      const words = new Set(transcript.keywords.map(k => k.word));
      words.forEach(word => {
        const highestSimilarity = Math.max(...transcript.keywords.filter(k => k.word === word).map(k => k.similarity));
        dispKeyword.push({'word': word, 'color': similarityToRGB(highestSimilarity), 'transcript_id': transcript.id});
      });
    }
    setDisplayKeywords(dispKeyword);
  }

  const showKeywordContext = (transcriptId)=> {
    if(props.fromclient){
      props.clickedKeyword(transcriptId)
    }else{
      navigate('/sessions/'+props.session.id+ '/pods/'+props.sessionDevice.id+ '/transcripts?index='+transcriptId);
    }
  }

  // --------
  // Graph
  // --------

  const refreshTimeline = ()=> {
    setKeywordPoints({});
    for (const keyword of props.session.keywords) {
      keywordPoints[keyword] = [];
    }

    for (const transcript of props.transcripts) {
      const duration = _end - _start;
      const keywordTracker = {};
      for (const keywordUsage of transcript.keywords) {
        const transcriptText = transcript.transcript;
        const word = keywordUsage.word;
        if (keywordUsage.word in keywordTracker) {
          keywordTracker[keywordUsage.word]++;
        } else {
          keywordTracker[keywordUsage.word] = 0;
        }
        const keywordIndex = keywordTracker[keywordUsage.word];
        const tPos = (transcriptText.indexOf(word, keywordIndex) / transcriptText.length) * transcript.length;
        const pos = (((transcript.start_time + tPos) - _start) / duration) * timelineWidth;
        keywordPoints[keywordUsage.keyword].push({
          'x': pos,
          'color': similarityToRGB(keywordUsage.similarity),
          'transcript_id': transcript.id
        });
      }
    }
  }

  const getSubstringIndex = (str, substring, n) =>{
    let times = 0, index = null;

    while (times < n && index !== -1) {
        index = str.indexOf(substring, index + 1);
        times++;
    }

    return index;
  }

  return (
    <AppKeywordsPage
        showGraph = {showGraph}
        displayKeywords = {displayKeywords}
        showKeywordContext = {showKeywordContext}
        session = {props.session}
        keywordPoints = {keywordPoints}
        callbackfunc = {callbackfunc}
        setCallbackFunc = {setCallbackFunc}
        toggleGraph = {toggleGraph}
    />
  )
}

export {AppKeywordsComponent}
