import { useEffect, useState } from 'react';
import { useNavigate, useOutletContext,useParams, useSearchParams } from 'react-router-dom';
import { similarityToRGB } from '../globals';
import {TranscriptComponentPage} from './html-pages'

function TranscriptsComponent(){

  // @ViewChildren('transcriptElement') set transcriptElements(elements: QueryList<ElementRef>) {
  //   if (elements && !this.hasScrolled) {
  //     const match = elements.find(el => el.nativeElement.id === this.transcriptIndex);
  //     if (match) {
  //       match.nativeElement.scrollIntoView();
  //       this.hasScrolled = true;
  //     }
  //   }
  // }

  
  const [sessionDevice, setSessionDevice] = useState({});
  const [session, setSession] = useState({});
  const [transcripts, setTranscripts] = useState([]);
  const [transcriptIndex, setTranscriptIndex] = useState("");
  const [dialogKeywords, setDialogKeywords] = useState();
  const [currentForm, setCurrentForm] = useState("");
  const [displayTranscripts, setDisplayTranscripts] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [hasScrolled, setHasScrolled] = useState(false);
  const [showKeywords, setShowKeywords] = useState(true);
  const [showDoA,setShowDoA] = useState(false);
  const [reload, setReload] = useState(false)
  const [activeSessionService, setActiveSessionService] = useOutletContext();
  const { sessionDeviceId } = useParams(); 
  const [searchParam, setSearchParam] = useSearchParams();
  const navigate = useNavigate()
  
  const colorTopicDict = ['hsl(0, 100%, 100%)', 'hsl(151, 58%, 87%)', 'hsl(109, 67%, 92%)', 'hsl(49, 94%, 93%)', 'hsl(34, 100%, 89%)', 'hsl(30, 79%, 85%)'];
  
  useEffect(()=>{
    const index = searchParam.get('index');
    if(index !== undefined){
      setTranscriptIndex(parseInt(index, 10))
    }

    if(sessionDeviceId !== undefined){
      const sessSub = activeSessionService.getSession();
      if(sessSub !== undefined) {
        setSession(sessSub);
      }

      const deviceSub = activeSessionService.getSessionDevice(sessionDeviceId)
      if(deviceSub !== undefined){
        setSessionDevice(deviceSub);
      }

      if (transcripts.length <= 0) {
        const transcriptSub = activeSessionService.getTranscripts()
         //const transcriptSub = activeSessionService.getSessionDeviceTranscripts(sessionDeviceId, setTransripts);

         transcriptSub.subscribe(e => {
             if (Object.keys(e).length !== 0) {
                 const data = e.filter(t => t.session_device_id === parseInt(sessionDeviceId, 10))
                     .sort((a, b) => (a.start_time > b.start_time) ? 1 : -1)
                 setTranscripts(data)
                 setReload(true)
             }
         })
         subscriptions.push(transcriptSub);
     }
    }
      
    

    return () => {
      subscriptions.map(sub => {
          if (sub.closed) {
              sub.unsubscribe()
          }
      });
  }
},[])

useEffect(()=>{
  if(reload){
    createDisplayTranscripts();
  }
},[reload])

//console.log(transcripts, displayTranscripts, 'states ... ')
const createDisplayTranscripts = ()=> {
    const accdisplaytrans = [];
    for (const transcript of transcripts) {
      const result = [];
      const words = transcript.transcript.split(' ');
      for (const word of words) {
        const matchingKeywords = [];
        let highestSimilarity = 0;
        if (showKeywords) {
          for (const keyword of transcript.keywords) {
            if (word.toLowerCase().startsWith(keyword.word.toLowerCase())
                && !matchingKeywords.find(item => item.keyword === keyword.keyword)) {
              if (keyword.similarity > highestSimilarity) {
                highestSimilarity = keyword.similarity;
              }
              matchingKeywords.push(keyword);
            }
          }
        }
        result.push({
          'word': word,
          'matchingKeywords': (matchingKeywords.length > 0) ? matchingKeywords : null,
          'color': similarityToRGB(highestSimilarity)
        });
      }
      transcript['words'] = result;
      transcript['doaColor'] = showDoA ? angleToColor(transcript.direction, transcript.topic_id) : angleToColor(-1, transcript.topic_id);
      accdisplaytrans.push(transcript);
    }
    setDisplayTranscripts(accdisplaytrans)
  }

  const angleToColor = (angle, id)=> {
    if (angle === -1) {
      return colorTopicDict[id + 1];
    } else {
      return 'hsl(' + angle + ', 100%, 95%)';
    }
  }

  const openKeywordDialog = (dialogKeywords) =>{
    setDialogKeywords(dialogKeywords);
    setCurrentForm("Keyword");
  }

  const openOptionsDialog = ()=> {
    setCurrentForm("Options");
  }

  const closeDialog = ()=> {
    setCurrentForm("");
  }

  const formatSeconds = (s)=> {
    const date = new Date(1000 * Math.floor(s));
    return date.toISOString().substr(11, 8);
  }

  const navigateToSession = ()=> {
    navigate('/sessions/' + session.id + '/pods/' + sessionDeviceId);
  }

  return(
    <TranscriptComponentPage
      sessionDevice = {sessionDevice}
      currentForm = {currentForm}
      navigateToSession = {navigateToSession}
      displayTranscripts = { displayTranscripts}
      formatSeconds = {formatSeconds}
      openKeywordDialog = {openKeywordDialog}
      closeDialog = {closeDialog}
      dialogKeywords = {dialogKeywords}
      showDoA = {showDoA}
      transcriptIndex = {transcriptIndex}
      createDisplayTranscripts = {createDisplayTranscripts}
      openOptionsDialog = {openOptionsDialog}
      isenabled = {true}
    />
  )
}

export {TranscriptsComponent}
