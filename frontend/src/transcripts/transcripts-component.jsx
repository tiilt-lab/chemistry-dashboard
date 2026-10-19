import { useEffect, useMemo, useState } from 'react';
import { formatHMS as formatSeconds, buildSpeakerColors, filterSortByDevice, indexSpeakerInfo, speakerLabel, wallClockLabel } from "../globals";
import { useNavigate, useOutletContext,useParams, useSearchParams } from 'react-router-dom';
import {TranscriptComponentPage} from './html-pages'
import { decorateTranscripts } from './transcript-utils'
import { useD3 } from '../myhooks/custom-hooks';
import { ApiService } from '../services/api-service';
import { SessionService } from '../services/session-service';
import { decorateLines, lineAt, seekFor, toMergedClock } from '../pod-details/group-time';
import { sessionToVideo } from '../components/video-player/video-time';
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
  const [subscriptions] = useState([]);
  const [showKeywords, setShowKeywords] = useState(true);
  const [trigger, setTrigger] = useState(0)
  const [showDoA] = useState(false);
  const [roster, setRoster] = useState([])
  // The pod's breakout group: its merged transcript (both laptops, each
  // line once, on the reference laptop's clock), its laptops and the clock
  // alignment between them. The page shows the merge by default and can
  // fall back to this laptop's own rows; the audio can come from any
  // laptop of the group, seeks and the playhead crossing the alignment.
  const [group, setGroup] = useState(null)
  const [scope, setScope] = useState("group")
  const [viewDeviceId, setViewDeviceId] = useState(() => parseInt(sessionDeviceId, 10))
  // The pod's recording plays above the list: a click on a line's time
  // seeks it, and the line under the playhead is highlighted and kept in
  // view. segments is the recording's layout on the session clock
  // (audio-player.jsx), so elapsed times match the player's own counter.
  const [selectedTime, setSelectedTime] = useState(null)
  const [playbackTime, setPlaybackTime] = useState(null)
  const [segments, setSegments] = useState(null)
  // Elapsed from the first line (default) or the time of day.
  const [clock, setClock] = useState(() => {
    try {
      return window.localStorage.getItem("blinc.transcriptClock") === "wall" ? "wall" : "elapsed"
    } catch {
      return "elapsed"
    }
  })
  const [activeSessionService] = useOutletContext();
  const { sessionDeviceId } = useParams();
  const [searchParam] = useSearchParams();
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
         // Push the SUBSCRIPTION, not the observable: the old code pushed the
         // shared BehaviorSubject and discarded .subscribe()'s return, so
         // cleanup never unsubscribed and every pod visit leaked a live
         // subscriber running filter+sort+setState on every socket emit.
         const transcriptSub = activeSessionService.getTranscripts().subscribe(e => {
             if (Object.keys(e).length !== 0) {
                 const data = filterSortByDevice(e, sessionDeviceId, "start_time")
                 setTranscripts(data)
             }
         })
         subscriptions.push(transcriptSub);
     }
    }

    return () => {
      // unsubscribe() is idempotent; the old `if (sub.closed)` guard was
      // inverted and only ever cleaned already-closed subscriptions.
      subscriptions.forEach(sub => sub.unsubscribe());
      subscriptions.length = 0;
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
},[])

// Recompute the decorated rows whenever the transcript set changes. The
// previous one-shot `reload` flag latched true on the FIRST socket digest
// page — if that page held only other pods' rows (sessions with >200
// transcripts are paginated), later pages never re-triggered the display
// build and the list rendered permanently empty.
useEffect(()=>{
  createDisplayTranscripts();
  // eslint-disable-next-line react-hooks/exhaustive-deps
},[transcripts, group, scope])

useEffect(()=>{
  if(trigger > 0){
    createDisplayTranscripts();
  }
},[trigger])

const createDisplayTranscripts = ()=> {
    setDisplayTranscripts(decorateTranscripts(sourceRows, showKeywords, showDoA, angleToColor))
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

  const groupName = (sessionDevice && sessionDevice.negotiation_group) || null
  const loadGroup = () => {
    if (!session || !session.id || !groupName) return
    new SessionService()
      .getGroupTranscript(session.id, groupName)
      .then((r) => (r.status === 200 ? r.json() : null))
      .then((d) => d && setGroup(d))
      .catch(() => {})
  }
  useEffect(() => {
    setGroup(null)
    loadGroup()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session && session.id, groupName])
  // A finished post-hoc run on any laptop of the group reaches the page as
  // a device update with a new analysed date: rebuild the merge.
  useEffect(() => {
    let key = ""
    const sub = activeSessionService.sessionDeviceSource.subscribe((devices) => {
      const list = devices || []
      const next = list
        .filter((d) => groupName && d.negotiation_group === groupName)
        .map((d) => d.id + ":" + (d.posthoc_analyzed_date || ""))
        .join("|")
      if (key && next !== key) loadGroup()
      key = next
    })
    return () => sub.unsubscribe()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupName, session && session.id])
  // The group's display names and team colours ("Pat 1"); empty for a pod
  // outside a group.
  const speakerInfo = useMemo(() => indexSpeakerInfo(group ? group.speakers : null), [group])
  const groupScope = !!group && scope === "group"
  const alignment = group ? group.alignment : null
  // Merged lines in the shape the row decoration expects (keywords and
  // direction are per-laptop analyses the merge does not carry).
  const groupLines = useMemo(
    () => (group ? decorateLines(group.lines, group.pods) : []).map((l) => ({
      keywords: [], direction: -1, topic_id: -1, ...l,
    })),
    [group],
  )
  const sourceRows = groupScope ? groupLines : transcripts

  // How many segments currently carry each tag (drives the "all N" bulk fix).
  const tagCounts = sourceRows.reduce((m, t) => {
    if (t.speaker_tag) m[t.speaker_tag] = (m[t.speaker_tag] || 0) + 1
    return m
  }, {})
  // In group scope the picker also offers every name the merge carries, so
  // a line the other laptop heard can be given to one of its students.
  const pickerRoster = groupScope
    ? [...new Set(roster.concat(groupLines.map((l) => l.speaker_tag).filter(Boolean)))].sort()
    : roster

  // One distinct, stable color per speaker — the same shared palette the
  // pod page's transcript panel uses, so a speaker keeps one color across
  // both views.
  const speakerColors = buildSpeakerColors(sourceRows, speakerInfo)
  const labelOf = (name) => speakerLabel(name, speakerInfo)
  const chooseClock = (mode) => {
    setClock(mode)
    try {
      window.localStorage.setItem("blinc.transcriptClock", mode)
    } catch {
      /* a private window: the choice lasts the page */
    }
  }
  const clockBase = session && session.creation_date instanceof Date && !isNaN(session.creation_date.getTime())
    ? session.creation_date : null
  const wall = clock === "wall" && !!clockBase
  let clockOrigin = null
  for (const t of sourceRows) if (t.start_time != null && (clockOrigin == null || t.start_time < clockOrigin)) clockOrigin = t.start_time
  // The merge sits on the reference laptop's clock, the player on its own
  // laptop's: in group scope the elapsed clock counts from the first line.
  const timeLabel = (s) => (wall
    ? wallClockLabel(clockBase, s)
    : formatSeconds(!groupScope && segments ? sessionToVideo(s, segments) : Math.max(0, s - (clockOrigin || 0))))
  // The laptop whose recording plays: any of the group's in group scope,
  // this one otherwise. A click on a line seeks that laptop's recording
  // to where the line plays on its clock; the playhead comes back onto the
  // merged clock to highlight the line.
  const playerDeviceId = groupScope ? viewDeviceId : parseInt(sessionDeviceId, 10)
  const playerSeek = (() => {
    if (selectedTime == null || !groupScope) return selectedTime
    const line = sourceRows.find((l) => l.start_time === selectedTime)
    return line ? seekFor(line, playerDeviceId, alignment) : selectedTime
  })()
  const onPlaybackTime = (deviceSeconds) =>
    setPlaybackTime(groupScope ? toMergedClock(deviceSeconds, playerDeviceId, alignment) : deviceSeconds)
  const switchView = (deviceId) => {
    // Land the new recording on the moment playing now.
    const line = lineAt(displayTranscripts || [], playbackTime)
    if (line) setSelectedTime(line.start_time)
    setViewDeviceId(deviceId)
  }

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
    if (groupScope) {
      setGroup((g) => (g ? { ...g, lines: g.lines.map((l) => ((applyToTag && oldTag ? l.speaker_tag === oldTag : l.id === transcriptId) ? { ...l, speaker_tag: alias } : l)) } : g))
      loadGroup()
    } else {
      setDisplayTranscripts(decorateTranscripts(next, showKeywords, showDoA, angleToColor))
    }
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
    if (editingId == null) return
    // Blur commits like the title-rename pattern, so a click-in click-out
    // with no change (or an emptied box) must not post an edit.
    const orig = sourceRows.find((t) => t.id === editingId)
    if (!text || (orig && orig.transcript === text)) {
      setEditingId(null)
      return
    }
    const res = await new ApiService().httpRequestCall(
      `api/v1/transcripts/${editingId}/edit_text`, "POST", { transcript: text })
    if (res.status !== 200) return
    const next = transcripts.map((t) =>
      t.id === editingId ? { ...t, transcript: text } : t)
    setTranscripts(next)
    if (groupScope) {
      setGroup((g) => (g ? { ...g, lines: g.lines.map((l) => (l.id === editingId ? { ...l, transcript: text } : l)) } : g))
      loadGroup()
    } else {
      setDisplayTranscripts(decorateTranscripts(next, showKeywords, showDoA, angleToColor))
    }
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
      roster = {pickerRoster}
      tagCounts = {tagCounts}
      speakerColors = {speakerColors}
      sessionId = {session.id}
      selectedTime = {selectedTime}
      playerSeek = {playerSeek}
      onSelectTime = {setSelectedTime}
      playbackTime = {playbackTime}
      onPlaybackTime = {onPlaybackTime}
      onSegments = {setSegments}
      group = {group}
      groupScope = {groupScope}
      scope = {scope}
      onSelectScope = {setScope}
      playerDeviceId = {playerDeviceId}
      onSelectView = {switchView}
      labelOf = {labelOf}
      timeLabel = {timeLabel}
      clock = {clock}
      chooseClock = {clockBase ? chooseClock : null}
      wallClock = {wall}
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
