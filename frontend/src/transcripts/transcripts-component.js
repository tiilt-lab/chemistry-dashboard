import { useEffect, useState } from 'react';
import { useNavigate, useOutletContext,useParams } from 'react-router-dom';
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

  
  const [sessionDevice, setSessionDevice] = useState();
  const [session, setSession] = useState();
  const [transcripts, setTranscripts] = useState([]);
  const [transcriptIndex, setTranscriptIndex] = useState("");
  const [dialogKeywords, setDialogKeywords] = useState();
  const [currentForm, setCurrentForm] = useState("");
  const [displayTranscripts, setDisplayTranscripts] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [hasScrolled, setHasScrolled] = useState(false);
  const [showKeywords, setShowKeywords] = useState(true);
  const [showDoA,setShowDoA] = useState(false);
  const [activeSessionService, setActiveSessionService] = useOutletContext();
  const { sessionDeviceId } = useParams(); 
  const {index} = useParams();
  const navigate = useNavigate()
  
  useEffect(()=>{
    if(index !== undefined){
      setTranscriptIndex(index)
    }

    if(sessionDeviceId !== undefined){
      const sessSub = activeSessionService.getSession();
      if(sessSub !== undefined) {
        setSession(sessSub);
      }

      if(sessionDeviceId !== undefined){
      const deviceSub = activeSessionService.getSessionDevice(sessionDeviceId)
      if(deviceSub !== undefined){
        setSessionDevice(deviceSub);
      }

      const transcriptSub = activeSessionService.getSessionDeviceTranscripts(sessionDeviceId)
      if(transcriptSub !== undefined){
        setTranscripts(transcriptSub);
        createDisplayTranscripts();
      }
    }
      
      //subscriptions.push(deviceSub, transcriptSub);
    }
    

  // return ()=> {
  //   subscriptions.map(sub => sub.unsubscribe());
  // }
},[])

  const createDisplayTranscripts = ()=> {
    setDisplayTranscripts([]);
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
      transcript['doaColor'] = (this.showDoA) ? this.angleToColor(transcript.direction) : this.angleToColor(-1);
      displayTranscripts.push(transcript);
    }
  }

  const angleToColor = (angle)=> {
    if (angle === -1) {
      return 'hsl(0, 100%, 100%)';
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
      navigateToSession = {navigateToSession}
      displayTranscripts = { displayTranscripts}
      formatSeconds = {formatSeconds}
      openKeywordDialog = {openKeywordDialog}
      closeDialog = {closeDialog}
      dialogKeywords = {dialogKeywords}
      showDoA = {showDoA}
      transcriptIndex = {transcriptIndex}
      createDisplayTranscripts = {createDisplayTranscripts}
    />
  )
}

export {TranscriptsComponent}
