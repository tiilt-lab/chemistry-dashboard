import { SessionService } from "../services/session-service";
import { SpeakerModel } from "../models/speaker";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useOutletContext, useParams } from "react-router-dom";
import { PodComponentPages } from "./html-pages";

function PodComponent() {
  const [sessionDevice, setSessionDevice] = useState({});
  const [session, setSession] = useState({});
  const [transcripts, setTranscripts] = useState([]);
  const [displayTranscripts, setDisplayTranscripts] = useState([]);
  const [currentTranscript, setCurrentTranscript] = useState({});
  const [currentForm, setCurrentForm] = useState("");
  const [deleteDeviceToggle, setDeleteDeviceToggle] = useState(false);
  const [timeRange, setTimeRange] = useState([0, 1]);
  const [startTime, setStartTime] = useState();
  const [endTime, setEndTime] = useState();
  const [activeSessionService] = useOutletContext();
  const [showFeatures, setShowFeatures] = useState([]);
  const [showBoxes, setShowBoxes] = useState([]);
  const [radarTrigger, setRadarTrigger] = useState(0);
  const [details, setDetails] = useState("Group");

  // speakers
  const [speakers, setSpeakers] = useState([]);
  const [selectedSpkrId1, setSelectedSpkrId1] = useState(-1);
  const [selectedSpkrId2, setSelectedSpkrId2] = useState(-1);
  const [spkr1Transcripts, setSpkr1Transcripts] = useState([]);
  const [spkr2Transcripts, setSpkr2Transcripts] = useState([]);

  // MULTI-SESSION overlay for Group mode only
  const [deviceOptions, setDeviceOptions] = useState([]);
  const [selectedDeviceIds, setSelectedDeviceIds] = useState([]);
  const [multiSeries, setMultiSeries] = useState([]);
  const pairsCache = useRef(new Map());

  const { sessionDeviceId } = useParams();
  const navigate = useNavigate();

  // ---------- initial load ----------
  useEffect(() => {
    if (!session.id) {
      const s = activeSessionService.getSession();
      if (s) setSession(s);
    }
    if (!sessionDevice.id) {
      const d = activeSessionService.getSessionDevice(sessionDeviceId);
      if (d) setSessionDevice(d);
    }
    if (transcripts.length === 0) {
      const sub = activeSessionService.getTranscripts();
      sub.subscribe((arr) => {
        if (!arr || !arr.length) return;
        const data = arr
          .filter((t) => t.session_device_id === parseInt(sessionDeviceId, 10))
          .sort((a, b) => (a.start_time > b.start_time ? 1 : -1));
        setTranscripts(data);
      });
    }
    // toolbars
    setShowFeatures(
      [
        "Emotional tone","Analytic thinking","Clout","Authenticity","Confusion",
        "Participation","Social Impact","Responsivity","Internal Cohesion","Newness","Communication Density",
      ].map((label, idx) => ({ label, value: idx, clicked: true }))
    );
    setShowBoxes(
      [
        "Timeline control","Discussion timeline","Keyword detection","Discussion features","Radar chart",
        "Participation","AI Analysis","Social Impact","Responsivity","Internal Cohesion","Newness","Communication Density",
      ].map((label, idx) => ({ label, value: idx, clicked: true }))
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------- derive time window + displayTranscripts ----------
  useEffect(() => {
    const len = session?.length ?? 0;
    const sTime = Math.round(len * timeRange[0] * 100) / 100;
    const eTime = Math.round(len * timeRange[1] * 100) / 100;
    setStartTime(sTime); 
    setEndTime(eTime);
    setDisplayTranscripts(transcripts.filter(t => t.start_time >= sTime && t.start_time <= eTime));
  }, [session?.length, timeRange, transcripts]);

  // ---------- speaker slices ----------
  useEffect(() => {
    if (displayTranscripts.length) {
      setSpkr1Transcripts(displayTranscripts.filter(t => selectedSpkrId1 === -1 || t.speaker_id === selectedSpkrId1));
      setSpkr2Transcripts(displayTranscripts.filter(t => selectedSpkrId2 === -1 || t.speaker_id === selectedSpkrId2));
    } else { 
      setSpkr1Transcripts([]); 
      setSpkr2Transcripts([]); 
    }
  }, [displayTranscripts, selectedSpkrId1, selectedSpkrId2]);

  // ---------- load speakers ----------
  useEffect(() => {
    if (!session?.id || !sessionDeviceId) return;
    const svc = new SessionService().getSessionDeviceSpeakers(session.id, sessionDeviceId);
    svc.then(r => {
      if (r.status === 200) {
        r.json().then(json => {
          const list = SpeakerModel.fromJsonList(json);
          if (list && list.length) setSpeakers(list);
        });
      }
    });
  }, [session?.id, sessionDeviceId]);

  // ---------- build session-device options ONLY FOR GROUP MODE ----------
  useEffect(() => {
    // Only build options if we're in Group mode
    if (details !== "Group") return;
    
    async function buildOptions() {
      let sessions = [];
      try {
        const r = await fetch("/api/v1/sessions");
        sessions = r.ok ? await r.json() : [];
      } catch { 
        sessions = []; 
      }

      const out = [];
      for (const s of sessions) {
        let devices = [];
        try {
          const r2 = await fetch(`/api/v1/sessions/${s.id}/devices`);
          devices = r2.ok ? await r2.json() : [];
        } catch { 
          devices = []; 
        }

        for (const d of devices) {
          out.push({
            id: `${s.id}:${d.id}`,
            label: `${s.name || s.id} (${d.name || d.id})`,
          });
        }
      }

      // Always include the current pair
      if (session?.id && sessionDevice?.id) {
        const curId = `${session.id}:${sessionDevice.id}`;
        if (!out.find(o => o.id === curId)) {
          out.unshift({
            id: curId,
            label: `${session.name || session.id} (${sessionDevice.name || sessionDevice.id})`,
          });
        }
      }

      setDeviceOptions(out);
    }
    
    buildOptions();
  }, [session?.id, session?.name, sessionDevice?.id, sessionDevice?.name, details]);

  // ---------- keep current pair LIVE in cache/multiSeries (GROUP MODE ONLY) ----------
  useEffect(() => {
    if (!session?.id || !sessionDevice?.id || details !== "Group") return;
    
    const curPairId = `${session.id}:${sessionDevice.id}`;
    const label = `${session.name || session.id} (${sessionDevice.name || sessionDevice.id})`;
    const slice = displayTranscripts || [];
    const payload = { id: curPairId, label, transcripts: slice };
    pairsCache.current.set(curPairId, payload);

    // first time -> default to current only
    if (selectedDeviceIds.length === 0) {
      setSelectedDeviceIds([curPairId]);
      setMultiSeries([payload]);
      return;
    }

    // if selected contains current, update it live
    if (selectedDeviceIds.includes(curPairId)) {
      const merged = selectedDeviceIds.map(id =>
        id === curPairId ? payload : (pairsCache.current.get(id) || { id, label: id, transcripts: [] })
      );
      setMultiSeries(merged);
    }
  }, [session?.id, sessionDevice?.id, session?.name, sessionDevice?.name, details, displayTranscripts, selectedDeviceIds]);

  // ---------- selection handler (Apply from picker) - GROUP MODE ONLY ----------
  async function loadPairTranscripts(pairId) {
    // current pair uses the live slice already cached above
    if (pairsCache.current.has(pairId)) return pairsCache.current.get(pairId);

    const [sid, did] = pairId.split(":");
    let label = deviceOptions.find(o => o.id === pairId)?.label || pairId;

    let arr = [];
    try {
      const r = await fetch(`/api/v1/sessions/${sid}/devices/${did}/transcripts`);
      arr = r.ok ? await r.json() : [];
    } catch { 
      arr = []; 
    }

    const payload = { id: pairId, label, transcripts: arr.sort((a, b) => a.start_time - b.start_time) };
    pairsCache.current.set(pairId, payload);
    return payload;
  }

  async function handleDeviceSelection(nextIds) {
    // Only handle in Group mode
    if (details !== "Group") return;
    
    // de-dupe and keep only ids that exist in options
    const allowed = new Set(deviceOptions.map(o => o.id));
    const ids = Array.from(new Set(nextIds.filter(id => allowed.has(id))));
    if (ids.length === 0) return;

    const loaded = await Promise.all(ids.map(loadPairTranscripts));
    setSelectedDeviceIds(ids);
    setMultiSeries(loaded);
  }

  // ---------- Reset state when switching modes ----------
  useEffect(() => {
    // When leaving Group mode, clear multi-session state
    if (details !== "Group") {
      setMultiSeries([]);
      setSelectedDeviceIds([]);
      pairsCache.current.clear();
    } else {
      // When entering Group mode, initialize with current session
      if (session?.id && sessionDevice?.id) {
        const curPairId = `${session.id}:${sessionDevice.id}`;
        const label = `${session.name || session.id} (${sessionDevice.name || sessionDevice.id})`;
        const payload = { id: curPairId, label, transcripts: displayTranscripts };
        pairsCache.current.set(curPairId, payload);
        setSelectedDeviceIds([curPairId]);
        setMultiSeries([payload]);
      }
    }
  }, [details]);

  // ---------- misc ----------
  const navigateToSession = () => navigate("/sessions/" + session.id);
  const onClickedTimeline = (t) => { 
    setCurrentForm("Transcript"); 
    setCurrentTranscript(t); 
  };
  const openDialog = (f) => { 
    setDeleteDeviceToggle(false); 
    setCurrentForm(f); 
  };
  const closeDialog = () => setCurrentForm("");
  const handleCheck = (e, arr, setArr) => { 
    const tmp = [...arr]; 
    tmp[e.option.value].clicked = !tmp[e.option.value].clicked; 
    setArr(tmp); 
  };
  const handleCheckFeats = (v, e) => { 
    handleCheck(e, showFeatures, setShowFeatures); 
    setRadarTrigger(x => x + 1); 
  };
  const handleCheckBoxes = (v, e) => { 
    handleCheck(e, showBoxes, setShowBoxes); 
  };

  const viewComparison = () => setDetails("Comparison");
  const viewIndividual = () => setDetails("Individual");
  const viewGroup = () => setDetails("Group");

  return (
    <PodComponentPages
      sessionDevice={sessionDevice}
      navigateToSession={navigateToSession}
      setRange={setTimeRange}
      onClickedTimeline={onClickedTimeline}
      session={session}
      displayTranscripts={displayTranscripts}
      startTime={startTime}
      endTime={endTime}
      transcripts={transcripts}
      loading={() => session === null || transcripts === null}
      onSessionClosing={() => {}}
      currentForm={currentForm}
      currentTranscript={currentTranscript}
      closeDialog={closeDialog}
      seeAllTranscripts={() => navigate(`/sessions/${session.id}/pods/${sessionDeviceId}/transcripts`)}
      openDialog={openDialog}
      deleteDeviceToggle={deleteDeviceToggle}
      setDeleteDeviceToggle={setDeleteDeviceToggle}
      removeDeviceFromSession={() => {}}
      showFeatures={showFeatures}
      showBoxes={showBoxes}
      handleCheckFeats={handleCheckFeats}
      handleCheckBoxes={handleCheckBoxes}
      radarTrigger={radarTrigger}
      speakers={speakers}
      selectedSpkrId1={selectedSpkrId1}
      setSelectedSpkrId1={setSelectedSpkrId1}
      selectedSpkrId2={selectedSpkrId2}
      setSelectedSpkrId2={setSelectedSpkrId2}
      spkr1Transcripts={spkr1Transcripts}
      spkr2Transcripts={spkr2Transcripts}
      details={details}
      setDetails={setDetails}
      viewIndividual={viewIndividual}
      viewComparison={viewComparison}
      viewGroup={viewGroup}
      open={true}
      setOpen={() => {}}

      // Multi-session props ONLY for Group mode
      multiSeries={details === "Group" ? multiSeries : undefined}
      deviceOptions={details === "Group" ? deviceOptions : undefined}
      selectedDeviceIds={details === "Group" ? selectedDeviceIds : undefined}
      onDeviceSelectionChange={details === "Group" ? handleDeviceSelection : undefined}
      currentSessionDeviceId={`${session.id}:${sessionDevice.id}`}
    />
  );
}

export { PodComponent };