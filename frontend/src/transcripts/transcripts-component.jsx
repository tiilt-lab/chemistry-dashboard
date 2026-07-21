import { useEffect, useState } from 'react';
import { formatHMS as formatSeconds } from "../globals";
import { useNavigate, useOutletContext,useParams, useSearchParams } from 'react-router-dom';
import {TranscriptComponentPage} from './html-pages'
import { decorateTranscripts } from './transcript-utils'
import { useD3 } from '../myhooks/custom-hooks';
import { ApiService } from '../services/api-service';
import * as d3 from 'd3';

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
  const [trigger, setTrigger] = useState(0)
  const [showDoA,setShowDoA] = useState(false);
  const [reload, setReload] = useState(false)
  const [roster, setRoster] = useState([])
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

useEffect(()=>{
  if(trigger > 0){
    createDisplayTranscripts();
  }
},[trigger])

const createDisplayTranscripts = ()=> {
    setDisplayTranscripts(decorateTranscripts(transcripts, showKeywords, showDoA, angleToColor))
  }

  // Roster of this pod, for the "this section is from…" speaker picker.
  useEffect(() => {
    if (sessionDeviceId === undefined) return
    new ApiService()
      .httpRequestCall(`api/v1/devices/${sessionDeviceId}/speakers`, "GET", {})
      .then((r) => (r.status === 200 ? r.json() : []))
      .then((list) => setRoster(
        [...new Set((list || []).map((s) => s.alias).filter(Boolean))].sort()))
      .catch(() => {})
  }, [sessionDeviceId])

  // How many segments currently carry each tag (drives the "all N" bulk fix).
  const tagCounts = transcripts.reduce((m, t) => {
    if (t.speaker_tag) m[t.speaker_tag] = (m[t.speaker_tag] || 0) + 1
    return m
  }, {})

  // Persist a human correction, then reflect it locally without a reload.
  // guest=true attributes to someone outside the roster (they get added as a
  // speaker on this group server-side).
  const reassignSpeaker = async (transcriptId, alias, applyToTag, guest) => {
    const target = transcripts.find((t) => t.id === transcriptId)
    const oldTag = target ? target.speaker_tag : null
    const res = await new ApiService().httpRequestCall(
      `api/v1/transcripts/${transcriptId}/reassign`, "POST",
      { alias, apply_to_tag: !!applyToTag, allow_guest: !!guest })
    if (res.status !== 200) return
    if (guest && !roster.includes(alias)) {
      setRoster((r) => [...r, alias].sort())
    }
    const next = transcripts.map((t) => {
      const hit = applyToTag && oldTag
        ? t.speaker_tag === oldTag
        : t.id === transcriptId
      return hit ? { ...t, speaker_tag: alias } : t
    })
    setTranscripts(next)
    setDisplayTranscripts(decorateTranscripts(next, showKeywords, showDoA, angleToColor))
  }

  // Click-to-edit the transcript text of one row. The server preserves the
  // original ASR text in voice_features.asr_text on first edit.
  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState("")
  const beginEdit = (t) => {
    setEditingId(t.id)
    setEditDraft(t.transcript || "")
  }
  const cancelEdit = () => setEditingId(null)
  const saveEdit = async () => {
    const text = editDraft.trim()
    if (!text || editingId == null) return
    const res = await new ApiService().httpRequestCall(
      `api/v1/transcripts/${editingId}/edit_text`, "POST", { transcript: text })
    if (res.status !== 200) return
    const next = transcripts.map((t) =>
      t.id === editingId ? { ...t, transcript: text } : t)
    setTranscripts(next)
    setDisplayTranscripts(decorateTranscripts(next, showKeywords, showDoA, angleToColor))
    setEditingId(null)
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


  const navigateToSession = ()=> {
    navigate('/sessions/' + session.id + '/pods/' + sessionDeviceId);
  }
  
  const toggleKeywords = ()=> {
    setShowKeywords(!showKeywords);
    setTrigger(trigger + 1)
  }
  
  const legendRef = useD3(
       (svg) => {
         const data = ["No topic", "1", "2", "3", "4", "5"];
         // Create a color scale
         const colorScale = d3.scaleOrdinal()
           .domain(data)
           .range(colorTopicDict.map((c) => d3.hsl(c)));

         // Create legend
         const legend = svg
          .selectAll(".legend")
          .data(data)
          .enter()
          .append("g")
          .attr("class", "legend")
          .attr("transform", (d, i) => `translate(0, ${i * 20})`);
       
        // Add colored rectangles to the legend
        legend
          .append("rect")
          .attr("width", 18)
          .attr("height", 18)
          .style("fill", (d) => colorScale(d));

        // Add text labels to the legend
        legend
          .append("text")
          .attr("x", 24)
          .attr("y", 9)
          .attr("dy", ".35em")
          .style("text-anchor", "start")
          .text((d) => d);
        }
  )  

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
      legendRef = {legendRef}
      showKeywords = {showKeywords}
      toggleKeywords = {toggleKeywords}
      roster = {roster}
      tagCounts = {tagCounts}
      reassignSpeaker = {reassignSpeaker}
      editingId = {editingId}
      editDraft = {editDraft}
      setEditDraft = {setEditDraft}
      beginEdit = {beginEdit}
      cancelEdit = {cancelEdit}
      saveEdit = {saveEdit}
    />
  )
}

export {TranscriptsComponent}
