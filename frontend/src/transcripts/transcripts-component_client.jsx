import { useEffect, useState } from 'react';
import { SessionService } from '../services/session-service';
import { useNavigate, useOutletContext,useParams, useSearchParams } from 'react-router-dom';
import { similarityToRGB } from '../globals';
import {TranscriptComponentPage} from './html-pages'

function TranscriptsComponentClient(props){
  const [transcripts, setTransripts] = useState([]);
  const [dialogKeywords, setDialogKeywords] = useState();
  const [currentForm, setCurrentForm] = useState("");
  const [displayTranscripts, setDisplayTranscripts] = useState([]);
  const [showKeywords, setShowKeywords] = useState(true);
  const [showDoA,setShowDoA] = useState(false);
  const [reload,setReload] = useState(false);
  const navigate = useNavigate()
  const sessionService = new SessionService()
  
  
  useEffect(() => {
    let intervalLoad
    if ( props.sessionDevice !== null) {
        fetchTranscript(props.sessionDevice.id)

        intervalLoad = setInterval(() => {
            fetchTranscript(props.sessionDevice.id)
        }, 2000)
    }

    return () => {
        clearInterval(intervalLoad)

    }

  }, [props.sessionDevice])



  /*
  useEffect(()=>{
    if(transcripts.length > 0){
      createDisplayTranscripts();
    }
  },[transcripts.length]) 
  */
  
  // hook for more frequent results (speaker tags for instance)
  useEffect(()=>{
    if(reload == true){
      createDisplayTranscripts();
    }
  },[reload])


const fetchTranscript = async (deviceid) => {
  try {
      const response = await sessionService.getSessionDeviceTranscriptsForClient(deviceid)

      if (response.status === 200) {
          setReload(false);
          const jsonObj = await response.json()
          const data = jsonObj.sort((a, b) => (a.start_time > b.start_time) ? 1 : -1)
          setTransripts(data);
          setReload(true);
      } else if (response.status === 400 || response.status === 401) {
          console.log(response, 'no transcript obj fromtranscripts-Component-client.js')
      }

  } catch (error) {
      console.log('Transript-component-client error func : requestAccessKey 1', error)
  }

}

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
      transcript['doaColor'] = showDoA ? angleToColor(transcript.direction) : angleToColor(-1);
      accdisplaytrans.push(transcript);
    }
    console.log("IN CREATE THING");
    console.log(accdisplaytrans);
    setDisplayTranscripts(accdisplaytrans)
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
    setCurrentForm("");
  }

  const closeDialog = ()=> {
    setCurrentForm("");
  }

  const formatSeconds = (s)=> {
    const date = new Date(1000 * Math.floor(s));
    return date.toISOString().substr(11, 8);
  }

  const navigateToSession = ()=> {
    props.setParentCurrentForm("")
  }

  return(
    <TranscriptComponentPage
      sessionDevice = {props.sessionDevice}
      currentForm = {currentForm}
      navigateToSession = {navigateToSession}
      displayTranscripts = { displayTranscripts}
      formatSeconds = {formatSeconds}
      openKeywordDialog = {openKeywordDialog}
      closeDialog = {closeDialog}
      dialogKeywords = {dialogKeywords}
      showDoA = {showDoA}
      transcriptIndex = {props.transcriptIndex}
      createDisplayTranscripts = {createDisplayTranscripts}
      openOptionsDialog = {openOptionsDialog}
      isenabled = {false}
    />
  )
}

export {TranscriptsComponentClient}
