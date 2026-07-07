import { similarityToRGB } from '../globals';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppKeywordsPage } from './html-pages'


function AppKeywordsComponent(props) {
  // Words view: one chip per distinct keyword, aggregated across the whole
  // discussion (count + strongest match), strongest matches first.
  const [displayKeywords, setDisplayKeywords] = useState([]);
  const [showGraph, setShowGraph] = useState(false);
  const [keywordPoints, setKeywordPoints] = useState({});
  const [showDialog, setShowDialog] = useState(false);
  const timelineWidth = 240;
  const navigate = useNavigate()

  useEffect(() => {
    if (showGraph) refreshTimeline();
    else refreshKeywords();
  }, [props.transcripts, showGraph, props.start, props.end]);

  const refreshKeywords = () => {
    // word -> {count, best similarity, transcript of the best match}
    const byWord = new Map();
    for (const transcript of props.transcripts) {
      for (const usage of transcript.keywords) {
        const entry = byWord.get(usage.word) || { count: 0, similarity: -1, transcript_id: transcript.id };
        entry.count += 1;
        if (usage.similarity > entry.similarity) {
          entry.similarity = usage.similarity;
          entry.transcript_id = transcript.id;
        }
        byWord.set(usage.word, entry);
      }
    }
    const list = [...byWord.entries()].map(([word, e]) => ({
      word,
      count: e.count,
      similarity: e.similarity,
      color: similarityToRGB(e.similarity),
      transcript_id: e.transcript_id,
    }));
    list.sort((a, b) => b.similarity - a.similarity || b.count - a.count);
    setDisplayKeywords(list);
  }

  const showKeywordContext = (transcriptId) => {
    if (props.fromclient) {
      props.clickedKeyword(transcriptId)
    } else if (props.sessionDevice && props.sessionDevice.id) {
      navigate('/sessions/' + props.session.id + '/pods/' + props.sessionDevice.id + '/transcripts?index=' + transcriptId);
    }
    // Session-level comparison renders without a single pod to link into;
    // chips are informational there.
  }

  const refreshTimeline = () => {
    // Build locally, then set: the old in-place mutation wrote into the
    // PREVIOUS state object (undefined on first toggle) and crashed the view.
    const points = {};
    for (const keyword of (props.session.keywords || [])) {
      points[keyword] = [];
    }
    const duration = (props.end - props.start) || 1;
    for (const transcript of props.transcripts) {
      const keywordTracker = {};
      for (const keywordUsage of transcript.keywords) {
        if (!(keywordUsage.keyword in points)) points[keywordUsage.keyword] = [];
        const transcriptText = transcript.transcript;
        const word = keywordUsage.word;
        keywordTracker[word] = (keywordTracker[word] ?? -1) + 1;
        const tPos = (transcriptText.indexOf(word, keywordTracker[word]) / transcriptText.length) * transcript.length;
        const pos = (((transcript.start_time + tPos) - props.start) / duration) * timelineWidth;
        points[keywordUsage.keyword].push({
          x: Math.max(0, Math.min(timelineWidth, pos)),
          color: similarityToRGB(keywordUsage.similarity),
          word,
          transcript_id: transcript.id,
        });
      }
    }
    setKeywordPoints(points);
  }

  return (
    <AppKeywordsPage
      showGraph={showGraph}
      setShowGraph={setShowGraph}
      displayKeywords={displayKeywords}
      showKeywordContext={showKeywordContext}
      session={props.session}
      keywordPoints={keywordPoints}
      showDialog={showDialog}
      setShowDialog={setShowDialog}
    />
  )
}

export { AppKeywordsComponent }
