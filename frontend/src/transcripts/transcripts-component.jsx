import { useEffect, useState } from 'react';
import { useNavigate, useOutletContext, useParams, useSearchParams, useLocation } from 'react-router-dom';
import { similarityToRGB } from '../globals';
import {TranscriptComponentPage} from './html-pages'
import { useD3 } from '../myhooks/custom-hooks';
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
  const [hasScrolled, setHasScrolled] = useState(false);
  const [showKeywords, setShowKeywords] = useState(true);
  const [trigger, setTrigger] = useState(0)
  const [showDoA,setShowDoA] = useState(false);
  const [reload, setReload] = useState(false)
  const [highlightRange, setHighlightRange] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState(null);
  const location = useLocation();
  const params = useParams();
  const [searchParam, setSearchParam] = useSearchParams();
  const navigate = useNavigate();

  // Check if we're in device-only mode (new route) vs session mode (nested route)
  const isDeviceOnlyMode = location.pathname.startsWith('/transcripts/device/');

  // Always call useOutletContext unconditionally (returns undefined if not in outlet)
  const contextValue = useOutletContext();

  // Use context only if available and not in device-only mode
  const [activeSessionService, setActiveSessionService] = isDeviceOnlyMode
    ? [null, null]
    : (contextValue || [null, null]);

  // Get the device ID from the appropriate param based on mode
  const sessionDeviceId = isDeviceOnlyMode ? params.deviceId : params.sessionDeviceId;

  const colorTopicDict = ['hsl(0, 100%, 100%)', 'hsl(151, 58%, 87%)', 'hsl(109, 67%, 92%)', 'hsl(49, 94%, 93%)', 'hsl(34, 100%, 89%)', 'hsl(30, 79%, 85%)'];


  useEffect(() => {
  let transcriptSub; // Local variable to store subscription

  const index = searchParam.get('index');
  if(index !== undefined){
    setTranscriptIndex(parseInt(index, 10))
  }

  const conceptHighlight = sessionStorage.getItem('conceptHighlight');
  if (conceptHighlight) {
    const data = JSON.parse(conceptHighlight);
    sessionStorage.removeItem('conceptHighlight');
    setHighlightRange({
      start: Math.max(0, parseFloat(data.timestamp) - 15),
      end: parseFloat(data.timestamp) + 15
    });
  }

  const highlightTime = searchParam.get('highlight_time') || sessionStorage.getItem('highlightTime');
  if (highlightTime) {
    sessionStorage.removeItem('highlightTime');
  }
  if (highlightTime) {
    setHighlightRange({
      start: Math.max(0, parseFloat(highlightTime) - 15),
      end: parseFloat(highlightTime) + 15
    });
  }

  if(sessionDeviceId !== undefined){
    // Handle device-only mode (from RAG search)
    if (isDeviceOnlyMode) {
      console.log('TranscriptsComponent: Device-only mode, fetching transcripts via public API for device:', sessionDeviceId);

      // Set minimal session/device info for display
      setSession({ id: 'N/A', name: 'Device View' });
      setSessionDevice({ id: sessionDeviceId, name: `Device ${sessionDeviceId}` });
      setIsLoading(true);
      setFetchError(null);

      // Use the public endpoint that doesn't require authentication
      fetch(`/api/v1/devices/${sessionDeviceId}/transcripts/client`)
        .then(res => {
          if (!res.ok) {
            throw new Error(`HTTP ${res.status}: Failed to fetch transcripts`);
          }
          return res.json();
        })
        .then(data => {
          if (Array.isArray(data)) {
            const sorted = data.sort((a, b) => a.start_time - b.start_time);
            setTranscripts(sorted);
            setReload(true);
            setIsLoading(false);
            console.log(`TranscriptsComponent: Successfully loaded ${sorted.length} transcripts from public API`);
          } else {
            throw new Error('Invalid response format: expected array');
          }
        })
        .catch(err => {
          console.error('Failed to load transcripts from public API:', err);
          setFetchError(err.message);
          setIsLoading(false);
          setTranscripts([]);
          setReload(true);
        });
    }
    // Handle normal session mode (nested route)
    else {
      // Try using activeSessionService first (preferred for real-time updates)
      if (activeSessionService && activeSessionService.getSession) {
        try {
          const sessSub = activeSessionService.getSession();
          if(sessSub !== undefined) {
            setSession(sessSub);
          }

          const deviceSub = activeSessionService.getSessionDevice(sessionDeviceId)
          if(deviceSub !== undefined){
            setSessionDevice(deviceSub);
          }

          // Subscribe to real-time transcript updates
          transcriptSub = activeSessionService.getTranscripts();
          if (transcriptSub && transcriptSub.subscribe) {
            transcriptSub.subscribe(e => {
              console.log("RAW WEBSOCKET DATA:", e);
              console.log("Array length:", e.length);
              // Check if there are duplicates in the raw data
              const ids = e.map(t => t.id);
              const uniqueIds = [...new Set(ids)];
              console.log("Total IDs:", ids.length, "Unique IDs:", uniqueIds.length);

              if (Object.keys(e).length !== 0) {
                const data = e.filter(t => t.session_device_id === parseInt(sessionDeviceId, 10))
                    .sort((a, b) => (a.start_time > b.start_time) ? 1 : -1)
                setTranscripts(data)
                setReload(true)
              }
            })
          }
        } catch (err) {
          console.error('Service access error:', err);
        }
      }

      // Fetch from API if no activeSessionService (page refresh scenario)
      // or if WebSocket hasn't provided transcripts yet
      if (!activeSessionService || transcripts.length === 0) {
        const pathParts = window.location.pathname.split('/');
        const sessionId = pathParts[pathParts.indexOf('sessions') + 1];

        console.log('TranscriptsComponent: Fetching transcripts from API (WebSocket not loaded yet)');
        setSession({id: sessionId});
        setSessionDevice({id: sessionDeviceId, name: `Device ${sessionDeviceId}`});
        setIsLoading(true);
        setFetchError(null);

        fetch(`/api/v1/sessions/${sessionId}/devices/${sessionDeviceId}/transcripts`)
          .then(res => {
            if (!res.ok) {
              throw new Error(`HTTP ${res.status}: Failed to fetch transcripts`);
            }
            return res.json();
          })
          .then(data => {
            if (Array.isArray(data)) {
              const sorted = data.sort((a, b) => a.start_time - b.start_time);
              setTranscripts(sorted);
              setReload(true);
              setIsLoading(false);
              console.log(`TranscriptsComponent: Successfully loaded ${sorted.length} transcripts from API`);
            } else {
              throw new Error('Invalid response format: expected array');
            }
          })
          .catch(err => {
            console.error('Failed to load transcripts:', err);
            setFetchError(err.message);
            setIsLoading(false);
            // Set empty transcripts array so page doesn't stay completely blank
            setTranscripts([]);
            setReload(true);
          });
      }
    }
  }

  return () => {
    // Clean up the subscription properly
    if (transcriptSub && transcriptSub.unsubscribe) {
      try {
        transcriptSub.unsubscribe();
      } catch (e) {
        // Ignore errors during cleanup
      }
    }
  }
}, [sessionDeviceId, activeSessionService, isDeviceOnlyMode]) // Re-run when any of these change


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

// Auto-scroll to highlighted transcript when navigating from RAG search
useEffect(() => {
  if (highlightRange && displayTranscripts.length > 0 && !hasScrolled) {
    // Find first transcript in highlight range
    const highlightedTranscript = displayTranscripts.find(t =>
      t.start_time >= highlightRange.start &&
      t.start_time <= highlightRange.end
    );

    if (highlightedTranscript) {
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        const element = document.getElementById(`${highlightedTranscript.id}`);
        if (element) {
          console.log('TranscriptsComponent: Scrolling to highlighted transcript:', highlightedTranscript.id);
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          setHasScrolled(true);
        }
      }, 100);
    }
  }
}, [displayTranscripts, highlightRange, hasScrolled]);

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
          // Keywords field was removed - iterate over empty array if not present
          for (const keyword of (transcript.keywords || [])) {
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
    // In device-only mode, navigate back to discover page
    if (isDeviceOnlyMode) {
      navigate('/discover');
    } else {
      // In normal session mode, navigate to pod details
      navigate('/sessions/' + session.id + '/pods/' + sessionDeviceId);
    }
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
      sessionDeviceId = {sessionDeviceId}
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
      legendRef = {legendRef}
      showKeywords = {showKeywords}
      toggleKeywords = {toggleKeywords}
      highlightRange = {highlightRange}
    />
  )
}

export {TranscriptsComponent}
