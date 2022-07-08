import { similarityToRGB, formatSeconds } from '../globals';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOutletContext } from 'react-router-dom';
import { DiscussionPage } from './html-pages'


function DiscussionGraphComponent() {

  // Server data
  const [session, setSession] = useState({});
  const [transcripts, setTranscripts] = useState([]);
  const [sessionDevices, setSessionDevices] = useState([]);
  const [contributions, setContributions] = useState();
  const [speakingTime, setSpeakingTime] = useState();
  const [showQuestions, setShowQuestions] = useState(false);
  const [showGraph, setShowGraph] = useState(false);
  const [cumulativePercent, setCumulativePercent] = useState(0);
  //const [subscriptions, setSubscriptions] = useState([]);
  const [currentForm, setCurrentForm] = useState("");

  const [displayKeywords, setDisplayKeywords] = useState()
  const [displayQuestions, setDisplayQuestions] = useState([]);
  const [displayDevices, setDisplayDevices] = useState([]);
  const [timestamps, setTimestamps] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState();
  const [selectedPercent, setSelectedPercent] = useState();
  const [activeSessionService, setActiveSessionService] = useOutletContext();
  const navigate = useNavigate()

  useEffect(() => {
    const deviceSub = activeSessionService.getSessionDevices()
    if (deviceSub !== undefined) {
      setSessionDevices(deviceSub);
      deviceSub.map(sd => {
        sd['visible'] = true;
        sd['transcripts'] = [];
      });
      updateGraph();
    };

    const sessionTranscripts = activeSessionService.getTranscripts()
    if (sessionTranscripts !== undefined) {
      setTranscripts(sessionTranscripts);
      updateGraph();
    };

    const sessionModel = activeSessionService.getSession();
    if (sessionModel !== undefined) {
      setSession(sessionModel);
    };
    // subscriptions.push(deviceSub, sessionTranscripts, sessionModel);

    // return () => {
    //   subscriptions.map(sub => sub.unsubscribe());
    // }
  }, [])


  const openForms = (form, data = null) => {
    setCurrentForm(form);
    if (currentForm === "stats") {
      setSelectedDevice(data);
      let totalTime = 0;
      const contributionsArray = transcripts.filter(transcript => transcript.session_device_id === selectedDevice.id);
      setContributions(contributionsArray.length);
      for (let i = 0; i < contributionsArray.length; i++) {
        const transcript = contributionsArray[i];
        totalTime += transcript.length;
      }
      setSpeakingTime(totalTime);
      setDisplayQuestions(parseQuestions(selectedDevice));
    } else if (currentForm === "keywords") {
      setDisplayKeywords(data);
    }
  }

  const closeForm = () => {
    setCurrentForm("");
    setShowQuestions(false);
    setShowGraph(false);
  }

  const updateGraph = () => {
    if (transcripts.length > 0 && sessionDevices.length > 0) {
      setDisplayDevices([]);
      for (const device of sessionDevices) {
        if (device['visible']) {
          displayDevices.push(device); // This will not work if user has deactivated some devices!!
        }
      }
      for (const transcript of transcripts) {
        const matchingDevice = displayDevices.find(d => d.id === transcript.session_device_id);
        if (matchingDevice != null) {
          matchingDevice['transcripts'].push(createDisplayTranscript(transcript));
        }
      }
      generateTimestamps();
    }
  }

  const navigateToSession = () => {
    navigate('/sessions/' + session.id);
  }

  const generateTimestamps = () => {
    setTimestamps(['00:00']);
    const lastTranscript = transcripts[transcripts.length - 1];
    const totalSeconds = (lastTranscript.start_time + lastTranscript.length);
    const stepSize = 5;
    for (let i = stepSize; i < totalSeconds; i += stepSize) {
      timestamps.push(formatSeconds(i));
    }
  }

  const parseQuestions = (session_device) => {
    const contributionsArray = transcripts.filter(transcript => transcript.session_device_id === session_device.id);
    const questionTranscripts = contributionsArray.filter(transcript => transcript.question);

    const questions = [];
    for (const transcript of questionTranscripts) {
      const sentences = transcript.transcript.match(/[^\.!\?]+[\.!\?]+/g);
      for (const sentence of sentences) {
        if (sentence.includes('?')) {
          questions.push(sentence);
        }
      }
    }
    return questions;
  }

  const createDisplayTranscript = (transcript, highlight = false) => {
    const sentences = transcript.transcript.match(/([^\.!\?]+[\.!\?]+)|([^\.!\?]+$)/g);
    const words = [];
    for (const sentence of sentences) {
      sentence.split(' ').map(word => words.push({ 'word': word, 'highlight': sentence.includes('?') && highlight }));
    }
    for (const word of words) {
      const matchingKeywords = [];
      let highestSimilarity = 0;
      for (const keyword of transcript.keywords) {
        if (word.word.toLowerCase().startsWith(keyword.word.toLowerCase())
          && !matchingKeywords.find(item => item.keyword === keyword.keyword)) {
          if (keyword.similarity > highestSimilarity) {
            highestSimilarity = keyword.similarity;
          }
          matchingKeywords.push(keyword);
        }
      }
      word['matchingKeywords'] = (matchingKeywords.length > 0) ? matchingKeywords : null;
      word['color'] = similarityToRGB(highestSimilarity);
    }
    return {
      'transcript_id': transcript.id,
      'speaker_tag': transcript.speaker_tag,
      'question': transcript.question,
      'highlight': highlight,
      'start_time': transcript.start_time,
      'transcript': words,
      'device_id': transcript.session_device_id,
      'length': transcript.length,
    };
  }

  const toggleGraph = (open, device = null) => {
    setShowGraph(open);
    if (open) {
      const huedelta = Math.trunc(360 / displayDevices.length);
      const percent = getSpeakingPercent(device);
      const roundedPercent = Math.floor(percent * 100);
      setSelectedPercent(roundedPercent);
      for (let i = 0; i < displayDevices.length; i++) {
        displayDevices[i]['path'] = setPiePieceProperties(displayDevices[i]);
        if (displayDevices[i] === device) {
          displayDevices[i]['selected'] = true;
          displayDevices[i]['color'] = `hsl(${i * huedelta},100%,80%)`;
        } else {
          displayDevices[i]['selected'] = false;
          displayDevices[i]['color'] = `hsl(${i * huedelta},100%,90%)`;
        }
      }
    }
  }

  const toggleQuestions = () => {
    setShowQuestions(!showQuestions);
  }

  const getSpeakingPercent = (device) => {
    setShowGraph(true);
    let totalTime = 0;
    const deviceContribution = transcripts.filter(transcript => transcript.session_device_id === device.id);
    for (let i = 0; i < deviceContribution.length; i++) {
      const transcript = deviceContribution[i];
      totalTime += transcript.length;
    }
    const rawPercent = totalTime / getTotalSpeakingTime();
    return rawPercent;
  }

  const getTotalSpeakingTime = () => {
    let allDeviceContributions = 0;
    const validTranscripts = [];
    for (const dev of displayDevices) {
      const deviceTranscripts = transcripts.filter(transcript => transcript.session_device_id === dev.id);
      for (const trans of deviceTranscripts) {
        validTranscripts.push(trans);
      }
    }
    for (const transcript of validTranscripts) {
      allDeviceContributions += transcript.length;
    }
    return allDeviceContributions;
  }

  const getDisplayPercent = (device) => {
    const percent = getSpeakingPercent(device);
    const roundedPercent = Math.floor(percent * 100);
    setSelectedPercent(roundedPercent);
    return roundedPercent;
  }

  const setPiePieceProperties = (device) => {
    const slice = { percent: this.getSpeakingPercent(device) };
    const [startX, startY] = getCoordinatesForPercent(cumulativePercent);
    this.cumulativePercent += slice.percent;
    const [endX, endY] = getCoordinatesForPercent(cumulativePercent);
    const largeArcFlag = slice.percent > .5 ? 1 : 0;

    const pathData = [
      `M ${startX} ${startY}`,
      `A 1 1 0 ${largeArcFlag} 1 ${endX} ${endY}`,
      `L 0 0`
    ].join(' ');
    return pathData;
  }

  const getCoordinatesForPercent = (percent) => {
    const x = Math.cos(2 * Math.PI * percent);
    const y = Math.sin(2 * Math.PI * percent);
    return [x, y];
  }

  const highlightQuestions = (transcript) => {
    transcript['highlight'] = !transcript['highlight'];
    const foundTranscript = transcripts.find(t => t.id === transcript.transcript_id);
    const newTranscript = this.createDisplayTranscript(foundTranscript, transcript['highlight']);
    Object.assign(transcript, newTranscript);
  }

  return (
    <DiscussionPage
      navigateToSession={navigateToSession}
      displayDevices={displayDevices}
      openForms={openForms}
      timestamps={timestamps}
      highlightQuestions={highlightQuestions}
      currentForm={currentForm}
      displayKeywords={displayKeywords}
      toggleGraph={toggleGraph}
      selectedDevice={selectedDevice}
      showGraph={showGraph}
      contributions={contributions}
      selectedPercent={selectedPercent}
      displayQuestions={displayQuestions}
      toggleQuestions={toggleQuestions}
      showQuestions={showQuestions}
      closeForm={closeForm}
      updateGraph={updateGraph}
    />
  )
}

export { DiscussionGraphComponent }