import { useMemo, useState, useEffect, useRef, useLayoutEffect } from "react";
import { formatHMS as formatSeconds } from "../../globals";
import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { MessageSquare, Brain, Clock3, Sparkles, Users, User, Eye, Mic, Activity, HelpCircle, Search, AlertTriangle, CheckCircle2, ChevronRight, Bot, BarChart3, Target, Lightbulb, TrendingDown, TrendingUp, ArrowRight } from "lucide-react";

import { AppSectionBoxComponent } from "../section-box/section-box-component"
import {SurveyCompletion} from "../../student-dashboard/survey-question"


function CollaborationFeedbackDashboard(props) {
  const allComplete = props.completedCount === props.surveyquestion?.length && props.notes !== "";

  const selectedSessionId1 = props.selectedSessionId1
  const selectedSessionDeviceId1 = props.selectedSessionDeviceId1
  const promptResponses = (props.promptResponses.hasOwnProperty(selectedSessionId1) && props.promptResponses[selectedSessionId1].hasOwnProperty(selectedSessionDeviceId1)) ? props.promptResponses[selectedSessionId1][selectedSessionDeviceId1] : []
  const llmresponse_session_summary = props.llmSessionAnalysis.Session_summary
  const llmresponse_session_metric_summary = llmresponse_session_summary.Session_metric_summary
  const llmresponse_group_summary = props.llmSessionAnalysis.Group_summary
  const llmresponse_window_summary = props.llmSessionAnalysis.Window_summary
  const selectedParticipantData = props.selectedSynthesizedData
  const window_length = selectedParticipantData.participant_level_metric.length
  const [selectedMoment, setSelectedMoment] = useState(selectedParticipantData.participant_level_metric[0])
  const [question, setQuestion] = useState([0, ""]);
  const scrollRef = useRef(null);
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
    setSelectedMoment(selectedParticipantData.participant_level_metric.find((m) => m.windowid === props.selectedMomentIdAndIndex[1]))
  }, [props.selectedMomentIdAndIndex]);






  const defaultQuestion = [
    [0, "How was my collaboration activity overall?"],
    [1, "When did I contribute ideas most strongly?"],
    [2, "Did I respond to peers often?"],
    [3, "Where did my engagement drop?"],
    [4, "How did my collaboration pattern change over time?"],
  ];

  function MetricBar({ label, value, hint, emphasize }) {
    const barTone = emphasize === "good" ? "bg-emerald-100" : emphasize === "risk" ? "bg-rose-100" : "bg-muted";
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <div>
            <span className="font-medium">{label}</span>
            {hint ? <span className="ml-2 text-muted-foreground">{hint}</span> : null}
          </div>
          <span className="font-semibold">{value}%</span>
        </div>
        <div className={`rounded-full p-1 ${barTone}`}>
          <Progress value={value} className="h-2" />
        </div>
      </div>
    );
  }

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
    if (value >= 50) return "bg-emerald-500";
    if (value >= 30) return "bg-amber-400";
    return "bg-rose-500";
  }

  function toneSurface(value) {
    if (value >= 50) return "border-emerald-200 bg-emerald-50";
    if (value >= 30) return "border-amber-200 bg-amber-50";
    return "border-rose-200 bg-rose-50";
  }

  function changeBackground(value, color) {
    if (value) return color
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
          <div className="rounded-xl bg-white/80 p-2">
            <div className="text-muted-foreground">Focus</div>
            <div className="font-semibold">{item.focusscore}</div>
          </div>
          <div className="rounded-xl bg-white/80 p-2">
            <div className="text-muted-foreground">Engagement</div>
            <div className="font-semibold">{item.engagementscore}</div>
          </div>
          <div className="rounded-xl bg-white/80 p-2">
            <div className="text-muted-foreground">Ideas</div>
            <div className="font-semibold">{item.ideacontributionscore}</div>
          </div>
          <div className="rounded-xl bg-white/80 p-2">
            <div className="text-muted-foreground">Reasoning</div>
            <div className="font-semibold">{item.reasoningscore}</div>
          </div>
          <div className="rounded-xl bg-white/80 p-2">
            <div className="text-muted-foreground">Leader</div>
            <div className="font-semibold">{item.leadershipscore}</div>
          </div>

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

  return (

    <div className="infographics-container">
      <AppSectionBoxComponent
        type={"large-section"}
        heading={"Collaboration Reflection Dashboard"}
      >
        <div className="large-section text-left">

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
                    {/* <CardTitle className="text-3xl">Collaboration Reflection Dashboard</CardTitle> */}
                    <CardDescription className="mt-2 max-w-2xl text-sm leading-6">
                      A student-facing Dashboard for session synthesis, moment-by-moment explanation, group performance,  and reflective Q&amp;A grounded in multimodal collaboration analytics.
                    </CardDescription>
                  </div>
                  <Badge className="rounded-full px-4 py-1 text-xs"><Sparkles className="mr-1 h-3.5 w-3.5" />AI-Enhanced</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 grid-cols-1 lg:grid-cols-4">
                  <div className="rounded-2xl bg-tiilt-soft p-4 ring-1 ring-tiilt-soft">
                    <div className="flex items-center gap-2 text-sm text-tiilt"><Users className="h-4 w-4" />Session - Group</div>
                    <div className="text-sm text-muted-foreground">{props.sessionNameForReflecDashboard}</div>
                    <div className="mt-2 text-lg font-semibold">{props.groupNameForReflecDashboard}</div>
                  </div>
                  <div className="rounded-2xl bg-muted p-4">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground"><BarChart3 className="h-4 w-4" />Session Pattern</div>
                    <div className="mt-2 text-sm ">{llmresponse_session_summary.Sessionpattern}</div>
                  </div>
                  <div className="rounded-2xl bg-violet-50 p-4 ring-1 ring-violet-100"> 
                    <div className="flex items-center gap-2 text-sm text-violet-700"><TrendingUp className="h-4 w-4" />Strong zone</div>
                    <div className="mt-2 text-sm ">{Array.isArray(llmresponse_session_summary.Strongzones)? llmresponse_session_summary.Strongzones[0] : llmresponse_session_summary.Strongzones}</div>
                  </div>
                  <div className="rounded-2xl bg-amber-50 p-4 ring-1 ring-amber-50">
                    <div className="flex items-center gap-2 text-sm text-amber-700"><TrendingDown className="h-4 w-4" />Caution zone</div>
                    <div className="mt-2 text-sm">{Array.isArray(llmresponse_session_summary.Declinezones)? llmresponse_session_summary.Declinezones[0] :llmresponse_session_summary.Declinezones}</div>
                  </div>
                </div>

                <div className="rounded-2xl border bg-emerald-50 p-4 mt-4 text-lg leading-6">
                  <div className="flex items-center gap-2 font-medium text-emerald-700"><Brain className="h-4 w-4" />Your Strength</div>
                  <p className="mt-2 text-sm">
                    {llmresponse_session_summary.Strengths.join("\n")}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-3xl border-0 shadow-sm">
              <CardHeader>
                <CardTitle className="text-xl">Controls</CardTitle>
                <CardDescription>Choose another session and group, inspect a moment, and ask grounded questions.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="w-full">
                  <div className="mb-2 text-sm font-medium">Session</div>
                  <Select value={selectedSessionId1} onValueChange={props.getSessionDevices}>
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
                  <Select value={selectedSessionDeviceId1} onValueChange={props.loadReflectionDashboardForNewSelection}>
                    <SelectTrigger className="w-full rounded-2xl">
                      <SelectValue placeholder="Select Group" />
                    </SelectTrigger>
                    <SelectContent>
                      {props.selectFilteredDevice1.map((device) => (
                        <SelectItem key={device} value={device.id}>{device.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* <div className="rounded-2xl border p-4 text-sm leading-6">
                  <div className="flex items-center gap-2 font-medium"><Brain className="h-4 w-4" />Your Strength</div>
                  <p className="mt-2 text-muted-foreground">
                    {llmresponse_session_summary.Strengths.join("\n")}
                  </p>
                </div> */}
              </CardContent>
            </Card>
          </motion.div>

          <Tabs defaultValue="session" className="space-y-6 mt-8">
            <Card className="rounded-3xl border-0 shadow-sm">
              <CardContent className="h-30 lg:h-10">
                <TabsList className="grid w-full grid-cols-1 gap-2 rounded-2xl lg:grid-cols-4">
                  <TabsTrigger className="h-10 text-base lg:h-8 lg:text-2xl" value="session">1. Session synthesis</TabsTrigger>
                  <TabsTrigger className="h-10 text-base lg:h-8 lg:text-2xl" value="moment">2. Moment explanation</TabsTrigger>
                  <TabsTrigger className="h-10 text-base lg:h-8 lg:text-2xl" value="qa">3. Reflective Q&amp;A</TabsTrigger>
                  <TabsTrigger className="h-10 text-base lg:h-8 lg:text-2xl" value="survey">4. Survey</TabsTrigger>
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
                    <div className={`rounded-xl border p-4 ${toneSurface(selectedParticipantData.session_level_metric.avg_verbalshare)}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold">Verbal participation</div>
                          <div className="text-sm text-muted-foreground">{llmresponse_session_metric_summary.avg_verbalshare}</div>
                        </div>
                        <div className="text-lg font-bold">{selectedParticipantData.session_level_metric.avg_verbalshare}%</div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/70">
                        <div className={`h-2 rounded-full ${toneClass(selectedParticipantData.session_level_metric.avg_verbalshare)}`} style={{ width: `${selectedParticipantData.session_level_metric.avg_verbalshare}%` }} />
                      </div>
                    </div>

                    <div className={`rounded-xl border p-4 ${toneSurface(selectedParticipantData.session_level_metric.avg_turntaking)}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold">Turn taking share</div>
                          <div className="text-sm text-muted-foreground">{llmresponse_session_metric_summary.avg_turntaking}</div>
                        </div>
                        <div className="text-lg font-bold">{selectedParticipantData.session_level_metric.avg_turntaking}%</div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/70">
                        <div className={`h-2 rounded-full ${toneClass(selectedParticipantData.session_level_metric.avg_turntaking)}`} style={{ width: `${selectedParticipantData.session_level_metric.avg_turntaking}%` }} />
                      </div>
                    </div>

                    <div className={`rounded-xl border p-4 ${toneSurface(selectedParticipantData.session_level_metric.avg_focusscore)}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold">Task focus</div>
                          <div className="text-sm text-muted-foreground">{llmresponse_session_metric_summary.avg_focusscore}</div>
                        </div>
                        <div className="text-lg font-bold">{selectedParticipantData.session_level_metric.avg_focusscore}%</div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/70">
                        <div className={`h-2 rounded-full ${toneClass(selectedParticipantData.session_level_metric.avg_focusscore)}`} style={{ width: `${selectedParticipantData.session_level_metric.avg_focusscore}%` }} />
                      </div>
                    </div>

                    <div className={`rounded-xl border p-4 ${toneSurface(selectedParticipantData.session_level_metric.avg_ideacontributionscore)}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold">Idea contribution</div>
                          <div className="text-sm text-muted-foreground">{llmresponse_session_metric_summary.avg_ideacontributionscore}</div>
                        </div>
                        <div className="text-lg font-bold">{selectedParticipantData.session_level_metric.avg_ideacontributionscore}%</div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/70">
                        <div className={`h-2 rounded-full ${toneClass(selectedParticipantData.session_level_metric.avg_ideacontributionscore)}`} style={{ width: `${selectedParticipantData.session_level_metric.avg_ideacontributionscore}%` }} />
                      </div>
                    </div>

                    <div className={`rounded-xl border p-4 ${toneSurface(selectedParticipantData.session_level_metric.avg_momentum)}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold">Momentum</div>
                          <div className="text-sm text-muted-foreground">{llmresponse_session_metric_summary.avg_momentum}</div>
                        </div>
                        <div className="text-lg font-bold">{selectedParticipantData.session_level_metric.avg_momentum}%</div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/70">
                        <div className={`h-2 rounded-full ${toneClass(selectedParticipantData.session_level_metric.avg_momentum)}`} style={{ width: `${selectedParticipantData.session_level_metric.avg_momentum}%` }} />
                      </div>
                    </div>
                    {/* <MetricBar label="Verbal participation" value={selectedParticipantData["session_level_metric"].avg_verbalshare} hint="share of spoken contribution" emphasize={selectedParticipantData["session_level_metric"].avg_verbalshare < 50 ? "risk" : "good"} />
                        <MetricBar label="Turn share" value={selectedParticipantData["session_level_metric"].avg_turntaking} hint="share of speaking windows" emphasize={selectedParticipantData["session_level_metric"].avg_turntaking < 50 ? "risk" : "good"} />
                        <MetricBar label="Task focus" value={selectedParticipantData["session_level_metric"].avg_focusscore} hint="task-oriented attention windows" emphasize={selectedParticipantData["session_level_metric"].avg_focusscore < 50 ? "risk" : "good"} />
                        <MetricBar label="Idea contribution" value={selectedParticipantData["session_level_metric"].avg_ideacontributionscore} hint="novel or extending moves" emphasize={selectedParticipantData["session_level_metric"].avg_ideacontributionscore < 50 ? "risk" : "good"} />
                        <MetricBar label="Momentum" value={selectedParticipantData["session_level_metric"].avg_momentum} hint="direct peer uptake" emphasize={selectedParticipantData["session_level_metric"].avg_momentum < 50 ? "risk" : "good"} /> */}
                  </CardContent>
                </Card>

                <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl"><Users className="h-5 w-5" />Group collaboration indicators</CardTitle>
                    <CardDescription>Group-level Performace provided to give you an insight of how your contributions impacted group outcomes.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">

                    <div className={`rounded-xl border p-4 ${toneSurface(selectedParticipantData.group_level_metric.verbalparticipationbalance)}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold">Verbal participation balance</div>
                          <div className="text-sm text-muted-foreground">{llmresponse_group_summary.verbalparticipationbalance}</div>
                        </div>
                        <div className="text-lg font-bold">{selectedParticipantData.group_level_metric.hasOwnProperty('verbalparticipationbalance') ? selectedParticipantData.group_level_metric.verbalparticipationbalance : 0}%</div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/70">
                        <div className={`h-2 rounded-full ${toneClass(selectedParticipantData.group_level_metric.verbalparticipationbalance)}`} style={{ width: `${selectedParticipantData.group_level_metric.verbalparticipationbalance}%` }} />
                      </div>
                    </div>

                    <div className={`rounded-xl border p-4 ${toneSurface(selectedParticipantData.group_level_metric.turntakingbalance)}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold">Turn taking balance</div>
                          <div className="text-sm text-muted-foreground">{llmresponse_group_summary.turntakingbalance}</div>
                        </div>
                        <div className="text-lg font-bold">{selectedParticipantData.group_level_metric.hasOwnProperty('turntakingbalance') ? selectedParticipantData.group_level_metric.turntakingbalance : 0}%</div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/70">
                        <div className={`h-2 rounded-full ${toneClass(selectedParticipantData.group_level_metric.turntakingbalance)}`} style={{ width: `${selectedParticipantData.group_level_metric.turntakingbalance}%` }} />
                      </div>
                    </div>

                    <div className={`rounded-xl border p-4 ${toneSurface(selectedParticipantData.group_level_metric.Sharedtaskfocus)}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold">Shared task focus</div>
                          <div className="text-sm text-muted-foreground">{llmresponse_group_summary.Sharedtaskfocus}</div>
                        </div>
                        <div className="text-lg font-bold">{selectedParticipantData.group_level_metric.hasOwnProperty('Sharedtaskfocus') ? selectedParticipantData.group_level_metric.Sharedtaskfocus : 0}%</div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/70">
                        <div className={`h-2 rounded-full ${toneClass(selectedParticipantData.group_level_metric.Sharedtaskfocus)}`} style={{ width: `${selectedParticipantData.group_level_metric.Sharedtaskfocus}%` }} />
                      </div>
                    </div>

                    <div className={`rounded-xl border p-4 ${toneSurface(selectedParticipantData.group_level_metric.ideacontribution)}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold">Idea contribution balance</div>
                          <div className="text-sm text-muted-foreground">{llmresponse_group_summary.ideacontribution}</div>
                        </div>
                        <div className="text-lg font-bold">{selectedParticipantData.group_level_metric.hasOwnProperty('ideacontribution') ? selectedParticipantData.group_level_metric.ideacontribution : 0}%</div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/70">
                        <div className={`h-2 rounded-full ${toneClass(selectedParticipantData.group_level_metric.ideacontribution)}`} style={{ width: `${selectedParticipantData.group_level_metric.ideacontribution}%` }} />
                      </div>
                    </div>

                    <div className={`rounded-xl border p-4 ${toneSurface(selectedParticipantData.group_level_metric.momentum)}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold">Momentum</div>
                          <div className="text-sm text-muted-foreground">{llmresponse_group_summary.momentum}</div>
                        </div>
                        <div className="text-lg font-bold">{selectedParticipantData.group_level_metric.hasOwnProperty('momentum') ? selectedParticipantData.group_level_metric.momentum : 0}%</div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/70">
                        <div className={`h-2 rounded-full ${toneClass(selectedParticipantData.group_level_metric.momentum)}`} style={{ width: `${selectedParticipantData.group_level_metric.momentum}%` }} />
                      </div>
                    </div>

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
                          {llmresponse_session_summary.Strengths.map((item) => (
                            <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
                        <div className="flex items-center gap-2 font-medium text-amber-800"><AlertTriangle className="h-4 w-4" />What to pay attention to</div>
                        <ul className="mt-3 space-y-2 text-sm text-amber-900/80">
                          {llmresponse_session_summary.Concerns.map((item) => (
                            <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <div className="rounded-2xl bg-violet-50 p-4 ring-1 ring-violet-100">
                      <div className="flex items-center gap-2 font-medium text-violet-700"><Lightbulb className="h-4 w-4" />What to work on</div>
                      <ul className="mt-3 space-y-2 text-sm text-violet-700">
                        {llmresponse_session_summary.Actions.map((item) => (
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
                        {selectedParticipantData.participant_level_metric.map((item, index) => (
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
                      <div className="rounded-2xl bg-tiilt-soft p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Eye className="h-3.5 w-3.5" />Focus</div>
                        <div className="mt-2 text-2xl font-semibold">{selectedMoment.focusscore}</div>
                      </div>
                      <div className="rounded-2xl bg-violet-50 p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Mic className="h-3.5 w-3.5" />Engagement</div>
                        <div className="mt-2 text-2xl font-semibold">{selectedMoment.engagementscore}</div>
                      </div>
                      <div className="rounded-2xl bg-amber-50 p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Lightbulb className="h-3.5 w-3.5" />Ideas</div>
                        <div className="mt-2 text-2xl font-semibold">{selectedMoment.ideacontributionscore}</div>
                      </div>
                      <div className="rounded-2xl bg-emerald-50 p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Brain className="h-3.5 w-3.5" />Reasoning</div>
                        <div className="mt-2 text-2xl font-semibold">{selectedMoment.reasoningscore}</div>
                      </div>
                      <div className="rounded-2xl bg-rose-50 p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Users className="h-3.5 w-3.5" />Leader</div>
                        <div className="mt-2 text-2xl font-semibold">{selectedMoment.leadershipscore}</div>
                      </div>
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
                              await props.interactivePromptFnc(
                                selectedSessionId1,
                                selectedSessionDeviceId1,
                                question[0],
                                question[1]
                              );
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
                                await props.interactivePromptFnc(
                                  selectedSessionId1,
                                  selectedSessionDeviceId1,
                                  q[0],
                                  q[1]
                                );
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
                    <CardDescription>The response is derive from a synhesis metrics tracked during your activity.</CardDescription>
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
          </Tabs>
        </div>
      </AppSectionBoxComponent >
    </div >
  );
}

export { CollaborationFeedbackDashboard }