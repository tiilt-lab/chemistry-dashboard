import { useState, useEffect, useRef, useLayoutEffect } from "react";
import { formatHMS as formatSeconds } from "../../globals";
import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { MessageSquare, Brain, Clock3, Sparkles, Users, Eye, Mic, Activity, HelpCircle, Search, AlertTriangle, CheckCircle2, ChevronRight, Bot, BarChart3, Lightbulb, TrendingDown, TrendingUp, ArrowRight } from "lucide-react";

import { AppSectionBoxComponent } from "../section-box/section-box-component"
import { SurveyCompletion } from "../../student-dashboard/survey-question"

// One dashboard, three modes (this replaces the three ~700-line near-copies):
//  - "participant": pod-details review — participant picker, data keyed by
//    participant id (currentParticipant / selectedParticipantSynthesizedData).
//  - "student": student dashboard — session+group pickers, Survey tab,
//    gentler tone thresholds, data keyed by [sessionId][deviceId].
//  - "rating": expert rating — no pickers, data keyed by [sessionId][deviceId].

const SESSION_METRICS = [
  ["Verbal participation", "avg_verbalshare"],
  ["Turn taking share", "avg_turntaking"],
  ["Task focus", "avg_focusscore"],
  ["Idea contribution", "avg_ideacontributionscore"],
  ["Momentum", "avg_momentum"],
];

const GROUP_METRICS = [
  ["Verbal participation balance", "verbalparticipationbalance"],
  ["Turn taking balance", "turntakingbalance"],
  ["Shared task focus", "Sharedtaskfocus"],
  ["Idea contribution balance", "ideacontribution"],
  ["Momentum", "momentum"],
];

const MOMENT_TILES = [
  [Eye, "Focus", "focusscore", "bg-tiilt-soft"],
  [Mic, "Engagement", "engagementscore", "bg-violet-50"],
  [Lightbulb, "Ideas", "ideacontributionscore", "bg-amber-50"],
  [Brain, "Reasoning", "reasoningscore", "bg-emerald-50"],
  [Users, "Leader", "leadershipscore", "bg-rose-50"],
];

function CollaborationFeedbackDashboard(props) {
  const mode = props.mode || "participant";

  // ---- per-mode identity + data plumbing ---------------------------------
  const participantId = props.currentParticipant;
  const sessionId = mode === "student" ? props.selectedSessionId1 : props.selectedSessionId;
  const deviceId = mode === "student" ? props.selectedSessionDeviceId1 : props.selectedSessionDeviceId;

  const promptResponses =
    mode === "participant"
      ? props.promptResponses[participantId] || []
      : props.promptResponses?.[sessionId]?.[deviceId] || [];

  const ask = (qid, qtext) =>
    mode === "participant"
      ? props.interactivePromptFnc(participantId, qid, qtext)
      : props.interactivePromptFnc(sessionId, deviceId, qid, qtext);

  // Guarded access: render a graceful fallback when the LLM analysis or the
  // synthesized data is missing, but keep the hooks below unconditional.
  const _analysis = props.llmSessionAnalysis || {}
  const selectedParticipantData =
    (mode === "participant" ? props.selectedParticipantSynthesizedData : props.selectedSynthesizedData) || {}
  const _participantMetrics = selectedParticipantData.participant_level_metric || []
  const _hasAnalysis = Boolean(_analysis.Session_summary && _participantMetrics.length)
  const llmresponse_session_summary = _analysis.Session_summary || {}
  const llmresponse_session_metric_summary = llmresponse_session_summary.Session_metric_summary || {}
  const llmresponse_group_summary = _analysis.Group_summary || {}
  const llmresponse_window_summary = _analysis.Window_summary || {}
  const session_level = selectedParticipantData.session_level_metric || {}
  const group_level = selectedParticipantData.group_level_metric || {}
  const window_length = _participantMetrics.length
  const [selectedMoment, setSelectedMoment] = useState(_participantMetrics[0])
  const [question, setQuestion] = useState([0, ""]);
  const lastItemRef = useRef(null)
  const viewportRef = useRef(null);

  useLayoutEffect(() => {
    const viewport = viewportRef.current;
    const lastItem = lastItemRef.current;

    if (!viewport || !lastItem) return;

    requestAnimationFrame(() => {
      const viewportRect = viewport.getBoundingClientRect();
      const itemRect = lastItem.getBoundingClientRect();

      const offset = itemRect.top - viewportRect.top + viewport.scrollTop;

      viewport.scrollTop = offset;
    });
  }, [promptResponses.length]);

  useEffect(() => {
    setSelectedMoment(_participantMetrics.find((m) => m.windowid === props.selectedMomentIdAndIndex[1]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.selectedMomentIdAndIndex]);

  const defaultQuestion = mode === "student"
    ? [
        [0, "How was my collaboration activity overall?"],
        [1, "When did I contribute ideas most strongly?"],
        [2, "Did I respond to peers often?"],
        [3, "Where did my engagement drop?"],
        [4, "How did my collaboration pattern change over time?"],
      ]
    : [
        [0, "When did I contribute ideas most strongly?"],
        [1, "Did I respond to peers often?"],
        [2, "Where did my engagement drop?"],
        [3, "How did my collaboration pattern change over time?"],
      ];

  // Students get gentler tone thresholds than the review/rating views.
  const [toneHi, toneMid] = mode === "student" ? [50, 30] : [75, 50];

  function statusClasses(status, selected = false) {
    if (status === 1) return selected ? "border-emerald-500 bg-emerald-50" : "border-emerald-200 bg-emerald-50/60";
    if (status === -1) return selected ? "border-rose-500 bg-rose-50" : "border-rose-200 bg-rose-50/60";
    return selected ? "border-amber-500 bg-amber-50" : "border-amber-200 bg-amber-50/60";
  }

  function statusBadge(status) {
    if (status === 1) return <Badge className="bg-emerald-600 hover:bg-emerald-600"><TrendingUp className="h-4 w-4" /></Badge>;
    if (status === -1) return <Badge className="bg-rose-600 hover:bg-rose-600"><TrendingDown className="h-4 w-4" /></Badge>;
    return <Badge className="bg-amber-500 hover:bg-amber-500 text-black"><ArrowRight className="h-4 w-4" /></Badge>;
  }

  function toneClass(value) {
    if (value >= toneHi) return "bg-emerald-500";
    if (value >= toneMid) return "bg-amber-400";
    return "bg-rose-500";
  }

  function toneSurface(value) {
    if (value >= toneHi) return "border-emerald-200 bg-emerald-50";
    if (value >= toneMid) return "border-amber-200 bg-amber-50";
    return "border-rose-200 bg-rose-50";
  }

  function changeBackground(value, color) {
    if (value) return color
  }

  // One indicator row (value bar + LLM one-liner) — was copy-pasted 10x.
  function IndicatorRow({ label, value, description }) {
    const v = value == null ? 0 : value;
    return (
      <div className={`rounded-xl border p-4 ${toneSurface(v)}`}>
        <div className="flex items-center justify-between">
          <div>
            <div className="font-semibold">{label}</div>
            <div className="text-sm text-muted-foreground">{description}</div>
          </div>
          <div className="text-lg font-bold">{v}%</div>
        </div>
        <div className="mt-4 h-2 rounded-full bg-white/70">
          <div className={`h-2 rounded-full ${toneClass(v)}`} style={{ width: `${v}%` }} />
        </div>
      </div>
    );
  }

  function TimelinePill({ item, item_index, window_length, selected, onClick }) {
    return (
      <button
        onClick={onClick}
        className={`w-full rounded-2xl border p-3 text-left transition hover:shadow-sm ${statusClasses(item.trenddirection, selected)}`}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">{formatSeconds(item.starttime)}-{formatSeconds(item.endtime)} </div>
            <div className="text-xs text-muted-foreground">{item_index <= ((window_length / 3) * 1) ? "Early" : item_index <= ((window_length / 3) * 2) ? "Middle" : "Late"} phase</div>
          </div>
          {statusBadge(item.trenddirection)}
        </div>
        <div className="mt-3 grid grid-cols-5 gap-2 text-[11px]">
          {MOMENT_TILES.map(([, label, key]) => (
            <div key={key} className="rounded-xl bg-white/80 p-2">
              <div className="text-muted-foreground">{label}</div>
              <div className="font-semibold">{item[key]}</div>
            </div>
          ))}
        </div>
      </button>
    );
  }

  function ChatTrail({ question, response, selected }) {
    return (
      <div className={`w-full rounded-2xl border p-3 text-left transition hover:shadow-sm ${changeBackground(selected, "bg-muted")}`}>
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">{question} </div>
          </div>
        </div>

        <div className="rounded-2xl p-5 text-sm leading-7">
          {response.Prompt_summary.Summary}
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border p-4">
            <div className="text-xs text-muted-foreground">Evidence windows</div>
            <ul className="mt-3 space-y-2 text-sm text-emerald-900/80">
              {response.Prompt_summary.Evidencewindows.map((item) => (
                <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border p-4">
            <div className="text-xs text-muted-foreground">Computed metrics used</div>
            <ul className="mt-3 space-y-2 text-sm text-emerald-900/80">
              {response.Prompt_summary.Computedmetricsused.map((item) => (
                <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  }

  if (!_hasAnalysis) {
    return (
      <div className="rounded-xl border border-tiilt-line bg-white p-6 text-center text-sm text-tiilt-muted">
        AI collaboration analysis isn't available for this pod yet — it needs a
        completed full re-run and a configured LLM (GOOGLE_API_KEY).
      </div>
    );
  }

  const strengthBox = (
    <div className="rounded-2xl border p-4 text-sm leading-6">
      <div className="flex items-center gap-2 font-medium"><Brain className="h-4 w-4" />Your Strength</div>
      <p className="mt-2 text-muted-foreground">
        {(llmresponse_session_summary.Strengths || []).join("\n")}
      </p>
    </div>
  );

  return (

    <div className={mode === "rating" ? "infographics-container text-left mx-6" : "infographics-container"}>
      <AppSectionBoxComponent
        type={"large-section"}
        heading={"Collaboration Reflection Dashboard"}
      >
        <div className={mode === "rating" ? "text-left" : "large-section text-left"}>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
            className="grid gap-4 mb-4 lg:grid-cols-[1.2fr_.8fr]"
          >
            <Card className="rounded-3xl border-0 shadow-sm">
              <CardHeader>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <CardDescription className="mt-2 max-w-2xl text-sm leading-6">
                      A student-facing Dashboard for session synthesis, moment-by-moment explanation, group performance,  and reflective Q&amp;A grounded in multimodal collaboration analytics.
                    </CardDescription>
                  </div>
                  <Badge className="rounded-full px-4 py-1 text-xs"><Sparkles className="mr-1 h-3.5 w-3.5" />AI-Enhanced</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 grid-cols-1 lg:grid-cols-4">
                  {mode === "participant" ? (
                    <div className="rounded-2xl bg-tiilt-soft p-4 ring-1 ring-tiilt-soft">
                      <div className="flex items-center gap-2 text-sm text-tiilt"><Users className="h-4 w-4" />Student</div>
                      <div className="mt-2 text-lg font-semibold">{participantId}</div>
                    </div>
                  ) : (
                    <div className="rounded-2xl bg-tiilt-soft p-4 ring-1 ring-tiilt-soft">
                      <div className="flex items-center gap-2 text-sm text-tiilt"><Users className="h-4 w-4" />Session - Group</div>
                      <div className="text-sm text-muted-foreground">{props.sessionNameForReflecDashboard}</div>
                      <div className="mt-2 text-lg font-semibold">{props.groupNameForReflecDashboard}</div>
                    </div>
                  )}
                  <div className="rounded-2xl bg-muted p-4">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground"><BarChart3 className="h-4 w-4" />Session Pattern</div>
                    <div className="mt-2 text-sm ">{llmresponse_session_summary.Sessionpattern}</div>
                  </div>
                  {mode === "student" ? (
                    <div className="rounded-2xl bg-violet-50 p-4 ring-1 ring-violet-100">
                      <div className="flex items-center gap-2 text-sm text-violet-700"><TrendingUp className="h-4 w-4" />Strong zone</div>
                      <div className="mt-2 text-sm ">{Array.isArray(llmresponse_session_summary.Strongzones)? llmresponse_session_summary.Strongzones[0] : llmresponse_session_summary.Strongzones}</div>
                    </div>
                  ) : (
                    <div className="rounded-2xl bg-emerald-50 p-4 ring-1 ring-emerald-100">
                      <div className="flex items-center gap-2 text-sm text-emerald-700"><TrendingUp className="h-4 w-4" />Strong zone</div>
                      <div className="mt-2 text-sm ">{Array.isArray(llmresponse_session_summary.Strongzones)? llmresponse_session_summary.Strongzones[0] : llmresponse_session_summary.Strongzones}</div>
                    </div>
                  )}
                  {mode === "student" ? (
                    <div className="rounded-2xl bg-amber-50 p-4 ring-1 ring-amber-50">
                      <div className="flex items-center gap-2 text-sm text-amber-700"><TrendingDown className="h-4 w-4" />Caution zone</div>
                      <div className="mt-2 text-sm">{Array.isArray(llmresponse_session_summary.Declinezones)? llmresponse_session_summary.Declinezones[0] :llmresponse_session_summary.Declinezones}</div>
                    </div>
                  ) : (
                    <div className="rounded-2xl bg-rose-50 p-4 ring-1 ring-rose-100">
                      <div className="flex items-center gap-2 text-sm text-rose-700"><TrendingDown className="h-4 w-4" />Decline zone</div>
                      <div className="mt-2 text-sm">{Array.isArray(llmresponse_session_summary.Declinezones)? llmresponse_session_summary.Declinezones[0] :llmresponse_session_summary.Declinezones}</div>
                    </div>
                  )}
                </div>

                {mode === "student" ? (
                  <div className="rounded-2xl border bg-emerald-50 p-4 mt-4 text-lg leading-6">
                    <div className="flex items-center gap-2 font-medium text-emerald-700"><Brain className="h-4 w-4" />Your Strength</div>
                    <p className="mt-2 text-sm">
                      {(llmresponse_session_summary.Strengths || []).join("\n")}
                    </p>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card className="rounded-3xl border-0 shadow-sm">
              <CardHeader>
                <CardTitle className="text-xl">Controls</CardTitle>
                <CardDescription>
                  {mode === "participant"
                    ? "Choose a student, inspect a moment, and ask grounded questions."
                    : "Choose another session and group, inspect a moment, and ask grounded questions."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {mode === "participant" ? (
                  <>
                    <div className="w-full">
                      <div className="mb-2 text-sm font-medium">Participant</div>
                      <Select value={participantId} onValueChange={props.setParticipantIDRefectionDashboard}>
                        <SelectTrigger className="w-full rounded-2xl">
                          <SelectValue placeholder="Select participant" />
                        </SelectTrigger>
                        <SelectContent>
                          {props.participants.map((p) => (
                            <SelectItem key={p} value={p}>{p}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    {strengthBox}
                  </>
                ) : null}

                {mode === "student" ? (
                  <>
                    <div className="w-full">
                      <div className="mb-2 text-sm font-medium">Session</div>
                      <Select value={sessionId} onValueChange={props.getSessionDevices}>
                        <SelectTrigger className="w-full rounded-2xl">
                          <SelectValue placeholder="Select Session" />
                        </SelectTrigger>
                        <SelectContent>
                          {props.previousSessions.map((sess) => (
                            <SelectItem key={sess.id} value={sess.id}>{sess.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="w-full">
                      <div className="mb-2 text-sm font-medium">Group</div>
                      <Select value={deviceId} onValueChange={props.loadReflectionDashboardForNewSelection}>
                        <SelectTrigger className="w-full rounded-2xl">
                          <SelectValue placeholder="Select Group" />
                        </SelectTrigger>
                        <SelectContent>
                          {props.selectFilteredDevice1.map((device) => (
                            <SelectItem key={device.id} value={device.id}>{device.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </>
                ) : null}

                {mode === "rating" ? strengthBox : null}
              </CardContent>
            </Card>
          </motion.div>

          <Tabs defaultValue="session" className="space-y-6 mt-8">
            <Card className="rounded-3xl border-0 shadow-sm">
              <CardContent className="h-30 lg:h-10">
                <TabsList className={`grid w-full grid-cols-1 gap-2 rounded-2xl ${mode === "student" ? "lg:grid-cols-4" : "lg:grid-cols-3"}`}>
                  <TabsTrigger className="h-10 text-base lg:h-8 lg:text-2xl" value="session">1. Session synthesis</TabsTrigger>
                  <TabsTrigger className="h-10 text-base lg:h-8 lg:text-2xl" value="moment">2. Moment explanation</TabsTrigger>
                  <TabsTrigger className="h-10 text-base lg:h-8 lg:text-2xl" value="qa">3. Reflective Q&amp;A</TabsTrigger>
                  {mode === "student" ? (
                    <TabsTrigger className="h-10 text-base lg:h-8 lg:text-2xl" value="survey">4. Survey</TabsTrigger>
                  ) : null}
                </TabsList>
              </CardContent>
            </Card>

            <TabsContent value="session" className="space-y-6">
              <div className="grid gap-3 lg:grid-cols-[.75fr_.75fr_1fr]">
                <Card className="rounded-3xl border-0 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl"><Activity className="h-5 w-5" />Individual collaboration indicators</CardTitle>
                    <CardDescription>These are your session-level measure of relevant collaboration quality indicators.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    {SESSION_METRICS.map(([label, key]) => (
                      <IndicatorRow
                        key={key}
                        label={label}
                        value={session_level[key]}
                        description={llmresponse_session_metric_summary[key]}
                      />
                    ))}
                  </CardContent>
                </Card>

                <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl"><Users className="h-5 w-5" />Group collaboration indicators</CardTitle>
                    <CardDescription>Group-level Performace provided to give you an insight of how your contributions impacted group outcomes.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {GROUP_METRICS.map(([label, key]) => (
                      <IndicatorRow
                        key={key}
                        label={label}
                        value={group_level[key]}
                        description={llmresponse_group_summary[key]}
                      />
                    ))}
                  </CardContent>
                </Card>


                <Card className="rounded-3xl border-0 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl"><Sparkles className="h-5 w-5" />Session Performance Analysis</CardTitle>
                    <CardDescription>Grounded, plain-language feedback generated from computed metrics and selected evidence.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <div className="rounded-2xl bg-muted p-4 text-sm leading-7">
                      {llmresponse_session_summary.Summary}
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                        <div className="flex items-center gap-2 font-medium text-emerald-800"><CheckCircle2 className="h-4 w-4" />What is going well</div>
                        <ul className="mt-3 space-y-2 text-sm text-emerald-900/80">
                          {(llmresponse_session_summary.Strengths || []).map((item) => (
                            <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                          ))}
                        </ul>
                      </div>
                      {mode === "student" ? (
                        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
                          <div className="flex items-center gap-2 font-medium text-amber-800"><AlertTriangle className="h-4 w-4" />What to pay attention to</div>
                          <ul className="mt-3 space-y-2 text-sm text-amber-900/80">
                            {(llmresponse_session_summary.Concerns || []).map((item) => (
                              <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                            ))}
                          </ul>
                        </div>
                      ) : (
                        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
                          <div className="flex items-center gap-2 font-medium text-rose-800"><AlertTriangle className="h-4 w-4" />What went wrong</div>
                          <ul className="mt-3 space-y-2 text-sm text-rose-900/80">
                            {(llmresponse_session_summary.Concerns || []).map((item) => (
                              <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    <div className="rounded-2xl bg-violet-50 p-4 ring-1 ring-violet-100">
                      <div className="flex items-center gap-2 font-medium text-violet-700"><Lightbulb className="h-4 w-4" />What to work on</div>
                      <ul className="mt-3 space-y-2 text-sm text-violet-700">
                        {(llmresponse_session_summary.Actions || []).map((item) => (
                          <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                        ))}
                      </ul>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="moment" className="space-y-6">
              <div className="grid gap-6 lg:grid-cols-[.8fr_1.2fr]">
                <Card className="rounded-3xl border-0 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl"><Clock3 className="h-5 w-5" />Timeline explorer</CardTitle>
                    <CardDescription>Select a time window to inspect local evidence, computed metrics, and synthesized explanation.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[480px] pr-3">
                      <div className="space-y-3">
                        {_participantMetrics.map((item, index) => (
                          <TimelinePill
                            key={item.windowid}
                            item={item}
                            item_index={index}
                            window_length={window_length}
                            selected={selectedMoment.windowid === item.windowid}
                            onClick={() => props.setSelectedMomentIdAndIndex([index, item.windowid])}
                          />
                        ))}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>

                <Card className={`rounded-3xl border-0 shadow-sm ${selectedMoment.trenddirection === -1 ? "ring-2 ring-rose-200" : selectedMoment.trenddirection === 1 ? "ring-2 ring-emerald-200" : "ring-2 ring-amber-200"}`}>
                  <CardHeader>
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <CardTitle className="text-xl">Moment explanation: {formatSeconds(selectedMoment.starttime)}-{formatSeconds(selectedMoment.endtime)}</CardTitle>
                        <CardDescription>{props.selectedMomentIdAndIndex[0] <= ((window_length / 3) * 1) ? "Early" : props.selectedMomentIdAndIndex[0] <= ((window_length / 3) * 2) ? "Middle" : "Late"} phase • click different moments to compare changes over time</CardDescription>
                      </div>
                      {statusBadge(selectedMoment.trenddirection)}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <div className="grid gap-3 md:grid-cols-4">
                      {MOMENT_TILES.map(([Icon, label, key, bg]) => (
                        <div key={key} className={`rounded-2xl ${bg} p-4`}>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground"><Icon className="h-3.5 w-3.5" />{label}</div>
                          <div className="mt-2 text-2xl font-semibold">{selectedMoment[key]}</div>
                        </div>
                      ))}
                    </div>

                    <div className="grid gap-4 md:grid-cols-[.9fr_1.1fr]">
                      <div className="space-y-4 rounded-2xl border p-4">
                        <div>
                          <div className="text-sm font-medium">Transcript snippet</div>
                          <p className="mt-2 text-sm leading-6 text-muted-foreground">“{selectedMoment.transcript}”</p>
                        </div>
                        <Separator />
                        <div>
                          <div className="text-sm font-medium">Structured metrics</div>
                          <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                            <div>Analytic thinking: <span className="font-medium text-foreground">{selectedMoment.analyticthinking < 50 ? "low" : selectedMoment.analyticthinking > 50 ? "high" : "balanced"}</span></div>
                            <div>Object focus: <span className="font-medium text-foreground">{selectedMoment.objectfocuson}</span></div>
                            <div>Participation score: <span className="font-medium text-foreground">{selectedMoment.participationscore < 33 ? "low participation" : selectedMoment.participationscore < 67 ? "balanced participation" : "high participation"}</span></div>
                            <div>Newness: <span className="font-medium text-foreground">{selectedMoment.newness < 50 ? "low" : selectedMoment.newness > 50 ? "high" : "balanced"}</span></div>
                            <div>Verbal share: <span className="font-medium text-foreground">{selectedMoment.verbalshare < 50 ? "low" : selectedMoment.verbalshare > 50 ? "high" : "balanced"}</span></div>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-4 rounded-2xl border p-4">
                        <div className="flex items-center gap-2 font-medium"><Bot className="h-4 w-4" />Interpretation</div>
                        <p className="text-sm leading-7 text-muted-foreground">{llmresponse_window_summary[props.selectedMomentIdAndIndex[1]]?.Summary}</p>
                        <div className="rounded-2xl bg-muted p-4">
                          <div className="flex items-center gap-2 text-sm font-medium"><HelpCircle className="h-4 w-4" />Suggestion</div>
                          <p className="mt-2 text-sm leading-6 text-muted-foreground">{llmresponse_window_summary[props.selectedMomentIdAndIndex[1]]?.Action}</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="qa" className="space-y-6">
              <div className="grid gap-6 lg:grid-cols-[.85fr_1.15fr]">
                <Card className="rounded-3xl border-0 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl"><MessageSquare className="h-5 w-5" />Reflective Q&amp;A</CardTitle>
                    <CardDescription>Interact with the Agent to get more insights into your collaboration activity.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <div className="flex gap-2">
                        <Input
                          value={question[1]}
                          onChange={(e) => setQuestion([-1, e.target.value])}
                          placeholder=""
                          className="rounded-2xl"
                          disabled={props.isThinking}
                        />
                        <Button
                          onClick={async () => {
                            props.setIsThinking(true);
                            try {
                              await ask(question[0], question[1]);
                            } finally {
                              props.setIsThinking(false);
                              setQuestion([-1, ""])
                            }
                          }}
                          className="rounded-2xl"
                          disabled={props.isThinking}>
                          <Search className="h-4 w-4" />
                        </Button>
                      </div>
                      {props.isThinking && (
                        <div className="text-lg font-medium text-rose-400 animate-pulse">
                          thinking...
                        </div>
                      )}
                    </div>

                    <div>
                      <div className="mb-2 text-sm font-medium">Suggested questions</div>
                      <div className="flex flex-wrap gap-2">
                        {defaultQuestion.map((q) => (
                          <button
                            key={q[0]}
                            onClick={async () => {
                              setQuestion([q[0], q[1]])
                              props.setIsThinking(true);
                              try {
                                await ask(q[0], q[1]);
                              } finally {
                                props.setIsThinking(false);
                                setQuestion([-1, ""])
                              }
                            }}
                            className="rounded-full border px-3 py-1.5 text-sm transition hover:bg-muted"
                          >
                            {q[1]}
                          </button>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>


                <Card className="rounded-3xl border-0 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl"><Sparkles className="h-5 w-5" />Agent Response</CardTitle>
                    <CardDescription>The response is derived from a synhesis metrics tracked during your activity.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea viewportRef={viewportRef} className="h-[480px] pr-3">
                      <div className="space-y-3">
                        {promptResponses.map((item, index) => (
                          <div key={index} ref={index === promptResponses.length - 1 ? lastItemRef : null}>
                            <ChatTrail
                              question={item[0]}
                              response={item[1]}
                              selected={index === (promptResponses.length - 1)}
                            />
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {mode === "student" ? (
              <TabsContent value="survey" className="space-y-6">
                <SurveyCompletion
                  surveyquestion={props.surveyquestion}
                  likertOptions={props.likertOptions}
                  completedCount={props.completedCount}
                  ratings={props.ratings}
                  handleRate={props.handleRate}
                  handleSubmit={props.handleSubmit}
                  submitted={props.submitted}
                  setNotes={props.setNotes}
                  notes={props.notes}
                />
              </TabsContent>
            ) : null}
          </Tabs>
        </div>
      </AppSectionBoxComponent>
    </div>
  );
}

export { CollaborationFeedbackDashboard }
