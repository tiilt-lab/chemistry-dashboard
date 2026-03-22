import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { MessageSquare, Brain, Clock3, Sparkles, Users, Eye, Mic, Activity, HelpCircle, Search, AlertTriangle, CheckCircle2, ChevronRight, Bot, BarChart3, Target, Lightbulb,TrendingDown, TrendingUp } from "lucide-react";

import { AppSectionBoxComponent } from "../section-box/section-box-component"

const participantsMetric = [
  {
    id: "noahh",
    name: "Noah",
    overall: {
      verbalParticipation: 22,
      turnShare: 19,
      ideaContribution: 14,
      responsivity: 18,
      taskFocus: 67,
      summary:
        "You stayed fairly task-focused, but your spoken contributions were less frequent and were more likely to clarify than extend peers' ideas.",
      strengths: ["Sustained task attention", "Occasional balanced contribution"],
      growth: ["Build more directly on peer ideas", "Increase verbal contribution in key moments"],
    },
  },
  {
    id: "hellohelio",
    name: "Helio",
    overall: {
      verbalParticipation: 39,
      turnShare: 34,
      ideaContribution: 28,
      responsivity: 24,
      taskFocus: 81,
      summary:
        "You were one of the more active speakers and remained highly task-focused, though some contributions could connect more explicitly to teammate ideas.",
      strengths: ["High verbal presence", "Strong task focus"],
      growth: ["Improve idea linkage", "Balance speaking with collaborative uptake"],
    },
  },
  {
    id: "mondrian",
    name: "Mondrian",
    overall: {
      verbalParticipation: 11,
      turnShare: 9,
      ideaContribution: 8,
      responsivity: 12,
      taskFocus: 54,
      summary:
        "You contributed selectively and appeared to shift between observing peers and the task, with fewer moments of verbal idea building.",
      strengths: ["Peer monitoring", "Selective contribution"],
      growth: ["Speak more often", "Increase idea-building moves"],
    },
  },
];

const timelineData = [
  {
    id: 1,
    range: "18:44–18:57",
    phase: "Early",
    focus: 92,
    participation: 74,
    idea: 68,
    responsivity: 45,
    emotion: "cognitive strain",
    transcript: "What's the difference between? What's the difference?",
    metrics: {
      attentionClass: "high and stable",
      objectFocus: "shared task artifact",
      participationScore: "dominant participation",
      newness: "high",
      responsivity: "low",
    },
    llmExplanation:
      "This moment suggests active verbal engagement and strong task focus. You appeared to be pressing for clarification, which can help move the group forward, though the contribution seems more question-driven than explicitly connected to a peer's prior idea.",
    reflectionQuestion: "How might you connect your question to what a teammate just said to deepen shared reasoning?",
  },
  {
    id: 2,
    range: "18:85–19:03",
    phase: "Middle",
    focus: 70,
    participation: 52,
    idea: 29,
    responsivity: 22,
    emotion: "strain / uncertainty",
    transcript: "I don't know if that's... I don't know. You're definitely doing something. Yeah.",
    metrics: {
      attentionClass: "medium and decreasing",
      objectFocus: "laptop",
      participationScore: "balanced participation",
      newness: "low",
      responsivity: "low",
    },
    llmExplanation:
      "Here, participation is present, but the contribution looks tentative and may reflect uncertainty or partial agreement. The analytics suggest you were engaged, but not strongly extending or integrating group ideas.",
    reflectionQuestion: "What evidence could you have added here to move from uncertainty to idea building?",
  },
  {
    id: 3,
    range: "19:19–19:29",
    phase: "Late",
    focus: 8,
    participation: 18,
    idea: 10,
    responsivity: 12,
    emotion: "low signal",
    transcript: "Yeah, I don't know what I'm sure. There's some side of that. Yeah.",
    metrics: {
      attentionClass: "no attention",
      objectFocus: "not captured",
      participationScore: "minimal participation",
      newness: "low",
      responsivity: "low",
    },
    llmExplanation:
      "This appears to be a lower-engagement moment. The system detected a drop in visual task focus and only a limited verbal contribution. It may represent fatigue, uncertainty, or a transition point in the discussion rather than disengagement alone.",
    reflectionQuestion: "What was happening in the group here, and what might have helped you re-enter more actively?",
  },
  {
    id: 4,
    range: "19:79–19:89",
    phase: "Late",
    focus: 12,
    participation: 34,
    idea: 14,
    responsivity: 16,
    emotion: "low signal",
    transcript: "...makes it like if it was the example before with...",
    metrics: {
      attentionClass: "no attention",
      objectFocus: "not captured",
      participationScore: "minimal participation",
      newness: "low",
      responsivity: "low",
    },
    llmExplanation:
      "This moment may show an attempt to reference an earlier example, which could be the start of idea linking. However, the overall signal still suggests limited uptake and low visible focus in this segment.",
    reflectionQuestion: "Could this have been a stronger bridge back to an earlier group idea?",
  },
];

const qaExamples = [
  "When did I contribute ideas most strongly?",
  "Did I respond to peers often?",
  "Where did my engagement drop?",
  "How did my collaboration pattern change over time?",
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

function TimelinePill({ item, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full rounded-2xl border p-3 text-left transition ${selected ? "border-primary bg-primary/5" : "hover:bg-muted/60"}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">{item.range}</div>
          <div className="text-xs text-muted-foreground">{item.phase} phase</div>
        </div>
        <Badge variant={selected ? "default" : "secondary"}>{item.metrics.attentionClass}</Badge>
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-[11px]">
        <div className="rounded-xl bg-muted p-2">
          <div className="text-muted-foreground">Focus</div>
          <div className="font-semibold">{item.focus}</div>
        </div>
        <div className="rounded-xl bg-muted p-2">
          <div className="text-muted-foreground">Talk</div>
          <div className="font-semibold">{item.participation}</div>
        </div>
        <div className="rounded-xl bg-muted p-2">
          <div className="text-muted-foreground">Ideas</div>
          <div className="font-semibold">{item.idea}</div>
        </div>
        <div className="rounded-xl bg-muted p-2">
          <div className="text-muted-foreground">Respond</div>
          <div className="font-semibold">{item.responsivity}</div>
        </div>
      </div>
    </button>
  );
}

function CollaborationFeedbackDashboard(props) {
  const selectedParticipantId = props.currentParticipant;
  const llmresponse = props.llmSessionAnalysis
  const selectedParticipantData = props.selectedParticipantSynthesizedData
  const [selectedMomentId, setSelectedMomentId] = useState(timelineData[1].id);
  const [question, setQuestion] = useState("");

  const selectedParticipant = useMemo(
    () => participantsMetric.find((p) => p.id === selectedParticipantId) ?? participantsMetric[0],
    [selectedParticipantId]
  );

  const selectedMoment = useMemo(
    () => timelineData.find((m) => m.id === selectedMomentId) ?? timelineData[0],
    [selectedMomentId]
  );

  const syntheticResponse = useMemo(() => {
    const q = question.trim().toLowerCase();
    if (!q) {
      return "Ask a question about your collaboration, such as when your focus dropped, when you contributed new ideas, or whether you responded directly to peers. The LLM layer uses computed metrics plus nearby evidence to give grounded explanations rather than raw score dumps.";
    }
    if (q.includes("respond")) {
      return "Your responsive contribution rate is lower than your overall speaking rate. This suggests you spoke regularly, but fewer of your contributions explicitly built on teammate statements. The clearest opportunities to improve appear in middle and late moments where participation stayed present but responsivity remained low.";
    }
    if (q.includes("idea") || q.includes("contribute")) {
      return "Your strongest idea contribution appears earlier in the discussion, where newness and verbal participation are both relatively high. Later contributions seem more clarifying or tentative than generative. A useful next step would be pairing your questions with a proposal or evidence claim.";
    }
    if (q.includes("engagement") || q.includes("focus") || q.includes("drop")) {
      return "The biggest engagement drop appears in later windows where visual task focus falls sharply while verbal contributions become shorter and less connected. This could reflect fatigue, uncertainty, or a transition in the group discussion rather than disengagement alone.";
    }
    return "Based on the current evidence, your collaboration pattern combines strong task focus with uneven idea uptake. You were present and engaged, but the biggest opportunity is making your contributions more explicitly responsive to peers and more visible as idea-building moves.";
  }, [question]);

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
                <div className="grid gap-4 md:grid-cols-4">
                  <div className="rounded-2xl bg-sky-50 p-4 ring-1 ring-sky-100">
                    <div className="flex items-center gap-2 text-sm text-sky-700"><Users className="h-4 w-4" />Student</div>
                    <div className="mt-2 text-lg font-semibold">{selectedParticipantId}</div>
                  </div>
                  <div className="rounded-2xl bg-muted p-4">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground"><BarChart3 className="h-4 w-4" />Session Pattern</div>
                    <div className="mt-2 text-sm ">{llmresponse.Sessionpattern}</div>
                  </div>
                  <div className="rounded-2xl bg-emerald-50 p-4 ring-1 ring-emerald-100">
                    <div className="flex items-center gap-2 text-sm text-emerald-700"><TrendingUp className="h-4 w-4" />Strong zone</div>
                    <div className="mt-2 text-sm ">{llmresponse.Strongzones[0]}</div>
                  </div>
                  <div className="rounded-2xl bg-rose-50 p-4 ring-1 ring-rose-100">
                    <div className="flex items-center gap-2 text-sm text-rose-700"><TrendingDown className="h-4 w-4" />Decline zone</div>
                    <div className="mt-2 text-sm">{llmresponse.Declinezones[0]}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-3xl border-0 shadow-sm">
              <CardHeader>
                <CardTitle className="text-xl">Controls</CardTitle>
                <CardDescription>Choose a student, inspect a moment, and ask grounded questions.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="w-full">
                  <div className="mb-2 text-sm font-medium">Participant</div>
                  <Select value={selectedParticipantId} onValueChange={props.setParticipantRefectionID}>
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
                <div className="rounded-2xl border p-4 text-sm leading-6">
                  <div className="flex items-center gap-2 font-medium"><Brain className="h-4 w-4" />Your Strength</div>
                  <p className="mt-2 text-muted-foreground">
                    {llmresponse.Strengths.join("\n")}
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <Tabs defaultValue="session" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3 rounded-2xl">
              <TabsTrigger value="session">1. Session synthesis</TabsTrigger>
              <TabsTrigger value="moment">2. Moment explanation</TabsTrigger>
              <TabsTrigger value="qa">3. Reflective Q&amp;A</TabsTrigger>
            </TabsList>

            <TabsContent value="session" className="space-y-6">
              <div className="grid gap-6 lg:grid-cols-[1.05fr_.95fr]">
                <Card className="rounded-3xl border-0 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl"><Activity className="h-5 w-5" />Computed collaboration indicators</CardTitle>
                    <CardDescription>These are deterministic session-level measure of relevant collaboration quality indicators.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <MetricBar label="Verbal participation" value={selectedParticipantData["session_level_metric"].avg_verbalshare} hint="share of spoken contribution" emphasize= {selectedParticipantData["session_level_metric"].avg_verbalshare < 50 ? "risk" : "good" }/>
                    <MetricBar label="Turn share" value={selectedParticipantData["session_level_metric"].avg_turntaking} hint="share of speaking windows" emphasize= {selectedParticipantData["session_level_metric"].avg_turntaking < 50 ? "risk" : "good" } />
                    <MetricBar label="Idea contribution" value={selectedParticipantData["session_level_metric"].avg_ideacontributionscore} hint="novel or extending moves" emphasize= {selectedParticipantData["session_level_metric"].avg_ideacontributionscore < 50 ? "risk" : "good" } />
                    <MetricBar label="Responsivity" value={selectedParticipantData["session_level_metric"].avg_responsivity} hint="direct peer uptake" emphasize= {selectedParticipantData["session_level_metric"].avg_responsivity < 50 ? "risk" : "good" } />
                    <MetricBar label="Task focus" value={selectedParticipantData["session_level_metric"].avg_focusscore} hint="task-oriented attention windows" emphasize= {selectedParticipantData["session_level_metric"].avg_focusscore < 50 ? "risk" : "good" } />
                  </CardContent>
                </Card>

                <Card className="rounded-3xl border-0 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl"><Sparkles className="h-5 w-5" />Session Performance Analysis</CardTitle>
                    <CardDescription>Grounded, plain-language feedback generated from computed metrics and selected evidence.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <div className="rounded-2xl bg-muted p-4 text-sm leading-7">
                      {llmresponse.Summary}
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                         <div className="flex items-center gap-2 font-medium text-emerald-800"><CheckCircle2 className="h-4 w-4" />What is going well</div>
                          <ul className="mt-3 space-y-2 text-sm text-emerald-900/80">
                          {llmresponse.Strengths.map((item) => (
                            <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
                        <div className="flex items-center gap-2 font-medium text-rose-800"><AlertTriangle className="h-4 w-4" />What went wrong</div>
                        <ul className="mt-3 space-y-2 text-sm text-rose-900/80">
                          {llmresponse.Concerns.map((item) => (
                            <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <div className="rounded-2xl bg-violet-50 p-4 ring-1 ring-violet-100">
                            <div className="flex items-center gap-2 font-medium text-violet-700"><Lightbulb className="h-4 w-4" />What to work on</div>
                            <ul className="mt-3 space-y-2 text-sm text-violet-700">
                          {llmresponse.Actions.map((item) => (
                            <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                          ))}
                        </ul>
                      </div>

                    {/* <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                      What to work on: {llmresponse.Confidence}
                    </div> */}
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
                        {timelineData.map((item) => (
                          <TimelinePill
                            key={item.id}
                            item={item}
                            selected={selectedMoment.id === item.id}
                            onClick={() => setSelectedMomentId(item.id)}
                          />
                        ))}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>

                <Card className="rounded-3xl border-0 shadow-sm">
                  <CardHeader>
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <CardTitle className="text-xl">Moment explanation: {selectedMoment.range}</CardTitle>
                        <CardDescription>{selectedMoment.phase} phase • click different moments to compare changes over time</CardDescription>
                      </div>
                      <Badge variant="secondary">{selectedMoment.emotion}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <div className="grid gap-3 md:grid-cols-4">
                      <div className="rounded-2xl bg-muted p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Eye className="h-3.5 w-3.5" />Focus</div>
                        <div className="mt-2 text-2xl font-semibold">{selectedMoment.focus}</div>
                      </div>
                      <div className="rounded-2xl bg-muted p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Mic className="h-3.5 w-3.5" />Participation</div>
                        <div className="mt-2 text-2xl font-semibold">{selectedMoment.participation}</div>
                      </div>
                      <div className="rounded-2xl bg-muted p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Lightbulb className="h-3.5 w-3.5" />Ideas</div>
                        <div className="mt-2 text-2xl font-semibold">{selectedMoment.idea}</div>
                      </div>
                      <div className="rounded-2xl bg-muted p-4">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Users className="h-3.5 w-3.5" />Respond</div>
                        <div className="mt-2 text-2xl font-semibold">{selectedMoment.responsivity}</div>
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
                            <div>Attention class: <span className="font-medium text-foreground">{selectedMoment.metrics.attentionClass}</span></div>
                            <div>Object focus: <span className="font-medium text-foreground">{selectedMoment.metrics.objectFocus}</span></div>
                            <div>Participation score: <span className="font-medium text-foreground">{selectedMoment.metrics.participationScore}</span></div>
                            <div>Newness: <span className="font-medium text-foreground">{selectedMoment.metrics.newness}</span></div>
                            <div>Responsivity: <span className="font-medium text-foreground">{selectedMoment.metrics.responsivity}</span></div>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-4 rounded-2xl border p-4">
                        <div className="flex items-center gap-2 font-medium"><Bot className="h-4 w-4" />LLM interpretation</div>
                        <p className="text-sm leading-7 text-muted-foreground">{selectedMoment.llmExplanation}</p>
                        <div className="rounded-2xl bg-muted p-4">
                          <div className="flex items-center gap-2 text-sm font-medium"><HelpCircle className="h-4 w-4" />Reflection prompt</div>
                          <p className="mt-2 text-sm leading-6 text-muted-foreground">{selectedMoment.reflectionQuestion}</p>
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
                    <CardDescription>Students can ask natural-language questions. The LLM answers from retrieved moments plus precomputed indicators.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2">
                      <Input
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder="Ask: When did I contribute ideas most strongly?"
                        className="rounded-2xl"
                      />
                      <Button className="rounded-2xl"><Search className="h-4 w-4" /></Button>
                    </div>
                    <div>
                      <div className="mb-2 text-sm font-medium">Suggested questions</div>
                      <div className="flex flex-wrap gap-2">
                        {qaExamples.map((q) => (
                          <button
                            key={q}
                            onClick={() => setQuestion(q)}
                            className="rounded-full border px-3 py-1.5 text-sm transition hover:bg-muted"
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-2xl border p-4 text-sm leading-6 text-muted-foreground">
                      <div className="font-medium text-foreground">Retrieval logic behind this answer</div>
                      <ul className="mt-2 space-y-2">
                        <li>• Pull relevant windows based on the question intent.</li>
                        <li>• Add participant-level metrics and nearby context.</li>
                        <li>• Ask the LLM to explain patterns without recomputing core numbers.</li>
                      </ul>
                    </div>
                  </CardContent>
                </Card>

                <Card className="rounded-3xl border-0 shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl"><Sparkles className="h-5 w-5" />Grounded LLM answer</CardTitle>
                    <CardDescription>Prototype response panel for conversational collaboration reflection.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="rounded-2xl bg-muted p-5 text-sm leading-7">
                      {syntheticResponse}
                    </div>
                    <div className="grid gap-3 md:grid-cols-3">
                      <div className="rounded-2xl border p-4">
                        <div className="text-xs text-muted-foreground">Evidence windows</div>
                        <div className="mt-2 font-semibold">3 retrieved</div>
                      </div>
                      <div className="rounded-2xl border p-4">
                        <div className="text-xs text-muted-foreground">Computed metrics used</div>
                        <div className="mt-2 font-semibold">5 indicators</div>
                      </div>
                      <div className="rounded-2xl border p-4">
                        <div className="text-xs text-muted-foreground">Output style</div>
                        <div className="mt-2 font-semibold">Explain + coach</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </AppSectionBoxComponent>
    </div>
  );
}

export { CollaborationFeedbackDashboard }