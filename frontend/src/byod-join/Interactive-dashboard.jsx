import React, { useMemo, useState } from "react";
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
import { MessageSquare, Brain, Clock3, Sparkles, Users, Eye, Mic, Activity, HelpCircle, Search, ChevronRight, Bot, BarChart3, Target, Lightbulb, AlertTriangle, TrendingDown, TrendingUp, LayoutGrid, PanelLeftClose, PanelsTopLeft, Gauge, Zap, CheckCircle2 } from "lucide-react";

const participants = [
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
      declineZones: ["Late phase attention drop", "Low responsivity across multiple speaking moments"],
      strongZones: ["Consistent task focus early on", "Some balanced participation windows"],
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
      declineZones: ["Idea linkage weakens in middle-to-late session", "Responsivity remains lower than speaking rate"],
      strongZones: ["Strong early question-driven engagement", "High focus sustained across most windows"],
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
      declineZones: ["Sparse verbal contribution", "Lower task focus in later moments"],
      strongZones: ["Good observational awareness", "Moments of selective peer attention"],
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
    status: "strong",
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
    status: "watch",
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
    status: "decline",
    transcript: "Yeah, I don't know what I'm sure. There's some side of that. Yeah.",
    metrics: {
      attentionClass: "no attention",
      objectFocus: "not captured",
      participationScore: "minimal participation",
      newness: "low",
      responsivity: "low",
    },
    llmExplanation:
      "This appears to be a lower-engagement moment. The system detected a drop in visual task focus and only a limited verbal contribution. It may represent fatigue, uncertainty, or a transition point in the session rather than disengagement alone.",
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
    status: "decline",
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

const versions = [
  { id: "v1", name: "Version 1", subtitle: "Balanced coach view", icon: LayoutGrid },
  { id: "v2", name: "Version 2", subtitle: "Alert-driven insights", icon: AlertTriangle },
  { id: "v3", name: "Version 3", subtitle: "Storyline timeline", icon: PanelsTopLeft },
  { id: "v4", name: "Version 4", subtitle: "Comparison workspace", icon: PanelLeftClose },
];

function statusClasses(status, selected = false) {
  if (status === "strong") return selected ? "border-emerald-500 bg-emerald-50" : "border-emerald-200 bg-emerald-50/60";
  if (status === "decline") return selected ? "border-rose-500 bg-rose-50" : "border-rose-200 bg-rose-50/60";
  return selected ? "border-amber-500 bg-amber-50" : "border-amber-200 bg-amber-50/60";
}

function statusBadge(status) {
  if (status === "strong") return <Badge className="bg-emerald-600 hover:bg-emerald-600">Strong</Badge>;
  if (status === "decline") return <Badge className="bg-rose-600 hover:bg-rose-600">Decline</Badge>;
  return <Badge className="bg-amber-500 hover:bg-amber-500 text-black">Watch</Badge>;
}

function versionAccent(version) {
  if (version === "v2") return "from-rose-50 via-background to-amber-50";
  if (version === "v3") return "from-tiilt-soft via-background to-violet-50";
  if (version === "v4") return "from-emerald-50 via-background to-cyan-50";
  return "from-background via-background to-muted/30";
}

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
      className={`w-full rounded-2xl border p-3 text-left transition hover:shadow-sm ${statusClasses(item.status, selected)}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">{item.range}</div>
          <div className="text-xs text-muted-foreground">{item.phase} phase</div>
        </div>
        {statusBadge(item.status)}
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-[11px]">
        <div className="rounded-xl bg-white/80 p-2">
          <div className="text-muted-foreground">Focus</div>
          <div className="font-semibold">{item.focus}</div>
        </div>
        <div className="rounded-xl bg-white/80 p-2">
          <div className="text-muted-foreground">Talk</div>
          <div className="font-semibold">{item.participation}</div>
        </div>
        <div className="rounded-xl bg-white/80 p-2">
          <div className="text-muted-foreground">Ideas</div>
          <div className="font-semibold">{item.idea}</div>
        </div>
        <div className="rounded-xl bg-white/80 p-2">
          <div className="text-muted-foreground">Respond</div>
          <div className="font-semibold">{item.responsivity}</div>
        </div>
      </div>
    </button>
  );
}

function VersionCards({ version, setVersion }) {
  return (
    <div className="grid gap-3 md:grid-cols-4">
      {versions.map((v) => {
        const Icon = v.icon;
        const active = v.id === version;
        return (
          <button
            key={v.id}
            onClick={() => setVersion(v.id)}
            className={`rounded-2xl border p-4 text-left transition ${active ? "border-primary bg-primary/5 shadow-sm" : "hover:bg-muted/50"}`}
          >
            <div className="flex items-center justify-between">
              <Icon className="h-4 w-4" />
              {active ? <Badge>Previewing</Badge> : null}
            </div>
            <div className="mt-3 font-semibold">{v.name}</div>
            <div className="mt-1 text-sm text-muted-foreground">{v.subtitle}</div>
          </button>
        );
      })}
    </div>
  );
}

function OverviewStrip({ selectedParticipant }) {
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <div className="rounded-2xl bg-tiilt-soft p-4 ring-1 ring-tiilt-soft">
        <div className="flex items-center gap-2 text-sm text-tiilt"><Users className="h-4 w-4" />Student</div>
        <div className="mt-2 text-lg font-semibold">{selectedParticipant.name}</div>
      </div>
      <div className="rounded-2xl bg-emerald-50 p-4 ring-1 ring-emerald-100">
        <div className="flex items-center gap-2 text-sm text-emerald-700"><TrendingUp className="h-4 w-4" />Strong zone</div>
        <div className="mt-2 text-sm font-semibold">{selectedParticipant.overall.strongZones[0]}</div>
      </div>
      <div className="rounded-2xl bg-rose-50 p-4 ring-1 ring-rose-100">
        <div className="flex items-center gap-2 text-sm text-rose-700"><TrendingDown className="h-4 w-4" />Decline zone</div>
        <div className="mt-2 text-sm font-semibold">{selectedParticipant.overall.declineZones[0]}</div>
      </div>
      <div className="rounded-2xl bg-violet-50 p-4 ring-1 ring-violet-100">
        <div className="flex items-center gap-2 text-sm text-violet-700"><Bot className="h-4 w-4" />Feedback mode</div>
        <div className="mt-2 text-lg font-semibold">Explain + reflect</div>
      </div>
    </div>
  );
}

function CollaborationFeedbackDashboardPrototype() {
  const [selectedParticipantId, setSelectedParticipantId] = useState(participants[1].id);
  const [selectedMomentId, setSelectedMomentId] = useState(timelineData[1].id);
  const [question, setQuestion] = useState("");
  const [version, setVersion] = useState("v1");

  const selectedParticipant = useMemo(
    () => participants.find((p) => p.id === selectedParticipantId) ?? participants[0],
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
      return "Your strongest idea contribution appears earlier in the session, where newness and verbal participation are both relatively high. Later contributions seem more clarifying or tentative than generative. A useful next step would be pairing your questions with a proposal or evidence claim.";
    }
    if (q.includes("engagement") || q.includes("focus") || q.includes("drop")) {
      return "The biggest engagement drop appears in later windows where visual task focus falls sharply while verbal contributions become shorter and less connected. This could reflect fatigue, uncertainty, or a transition in the group session rather than disengagement alone.";
    }
    return "Based on the current evidence, your collaboration pattern combines strong task focus with uneven idea uptake. You were present and engaged, but the biggest opportunity is making your contributions more explicitly responsive to peers and more visible as idea-building moves.";
  }, [question]);

  const VersionOne = () => (
    <div className="space-y-6">
      <OverviewStrip selectedParticipant={selectedParticipant} />
      <div className="grid gap-6 lg:grid-cols-[1.05fr_.95fr]">
        <Card className="rounded-3xl border-0 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl"><Activity className="h-5 w-5" />Computed collaboration indicators</CardTitle>
            <CardDescription>Green areas indicate stronger performance. Rose marks the indicators that deserve attention.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <MetricBar label="Verbal participation" value={selectedParticipant.overall.verbalParticipation} hint="share of spoken contribution" emphasize="risk" />
            <MetricBar label="Turn share" value={selectedParticipant.overall.turnShare} hint="share of speaking windows" emphasize="risk" />
            <MetricBar label="Idea contribution" value={selectedParticipant.overall.ideaContribution} hint="novel or extending moves" emphasize="risk" />
            <MetricBar label="Responsivity" value={selectedParticipant.overall.responsivity} hint="direct peer uptake" emphasize="risk" />
            <MetricBar label="Task focus" value={selectedParticipant.overall.taskFocus} hint="task-oriented attention windows" emphasize="good" />
          </CardContent>
        </Card>

        <Card className="rounded-3xl border-0 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl"><Sparkles className="h-5 w-5" />LLM session synthesis</CardTitle>
            <CardDescription>Balanced coach-style feedback with strengths and growth areas side by side.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="rounded-2xl bg-muted p-4 text-sm leading-7">{selectedParticipant.overall.summary}</div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                <div className="flex items-center gap-2 font-medium text-emerald-800"><CheckCircle2 className="h-4 w-4" />What is going well</div>
                <ul className="mt-3 space-y-2 text-sm text-emerald-900/80">
                  {selectedParticipant.overall.strongZones.map((item) => (
                    <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
                <div className="flex items-center gap-2 font-medium text-rose-800"><AlertTriangle className="h-4 w-4" />What to work on</div>
                <ul className="mt-3 space-y-2 text-sm text-rose-900/80">
                  {selectedParticipant.overall.declineZones.map((item) => (
                    <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  const VersionTwo = () => (
    <div className="grid gap-6 lg:grid-cols-[.82fr_1.18fr]">
      <Card className="rounded-3xl border-0 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl"><AlertTriangle className="h-5 w-5 text-rose-600" />Priority alerts</CardTitle>
          <CardDescription>Optimized for attention-catching decline zones first, then strengths.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {selectedParticipant.overall.declineZones.map((item) => (
            <div key={item} className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
              <div className="flex items-center gap-2 font-medium text-rose-800"><TrendingDown className="h-4 w-4" />Decline detected</div>
              <div className="mt-2 text-sm text-rose-900/80">{item}</div>
            </div>
          ))}
          {selectedParticipant.overall.strongZones.map((item) => (
            <div key={item} className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
              <div className="flex items-center gap-2 font-medium text-emerald-800"><TrendingUp className="h-4 w-4" />Strong pattern</div>
              <div className="mt-2 text-sm text-emerald-900/80">{item}</div>
            </div>
          ))}
          <div className="rounded-2xl border bg-amber-50 p-4">
            <div className="flex items-center gap-2 font-medium text-amber-800"><Gauge className="h-4 w-4" />Why this layout</div>
            <p className="mt-2 text-sm text-amber-900/80">Best when you want students to notice risk areas immediately and then drill down into them.</p>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-6">
        <Card className="rounded-3xl border-0 shadow-sm">
          <CardHeader>
            <CardTitle className="text-xl">Color-coded performance panel</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4"><div className="text-xs text-rose-700">Verbal participation</div><div className="mt-2 text-2xl font-semibold">{selectedParticipant.overall.verbalParticipation}%</div></div>
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4"><div className="text-xs text-rose-700">Turn share</div><div className="mt-2 text-2xl font-semibold">{selectedParticipant.overall.turnShare}%</div></div>
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4"><div className="text-xs text-rose-700">Idea contribution</div><div className="mt-2 text-2xl font-semibold">{selectedParticipant.overall.ideaContribution}%</div></div>
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4"><div className="text-xs text-amber-700">Responsivity</div><div className="mt-2 text-2xl font-semibold">{selectedParticipant.overall.responsivity}%</div></div>
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4"><div className="text-xs text-emerald-700">Task focus</div><div className="mt-2 text-2xl font-semibold">{selectedParticipant.overall.taskFocus}%</div></div>
          </CardContent>
        </Card>

        <Card className="rounded-3xl border-0 shadow-sm">
          <CardHeader>
            <CardTitle className="text-xl">Recommended next actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {selectedParticipant.overall.growth.map((item) => (
              <div key={item} className="rounded-2xl border p-4 text-sm">{item}</div>
            ))}
            <div className="rounded-2xl bg-muted p-4 text-sm leading-7">{selectedParticipant.overall.summary}</div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  const VersionThree = () => (
    <div className="grid gap-6 lg:grid-cols-[.78fr_1.22fr]">
      <Card className="rounded-3xl border-0 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl"><PanelsTopLeft className="h-5 w-5" />Storyline timeline</CardTitle>
          <CardDescription>Best for moment-by-moment reflection. Strong moments are green, declines are rose.</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[560px] pr-3">
            <div className="space-y-3">
              {timelineData.map((item) => (
                <TimelinePill key={item.id} item={item} selected={selectedMoment.id === item.id} onClick={() => setSelectedMomentId(item.id)} />
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      <div className="space-y-6">
        <Card className={`rounded-3xl border-0 shadow-sm ${selectedMoment.status === "decline" ? "ring-2 ring-rose-200" : selectedMoment.status === "strong" ? "ring-2 ring-emerald-200" : "ring-2 ring-amber-200"}`}>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <div>
                <CardTitle className="text-xl">Moment explanation: {selectedMoment.range}</CardTitle>
                <CardDescription>{selectedMoment.phase} phase • the selected card changes color to match the performance pattern</CardDescription>
              </div>
              {statusBadge(selectedMoment.status)}
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-2xl bg-tiilt-soft p-4"><div className="text-xs text-tiilt">Focus</div><div className="mt-2 text-2xl font-semibold">{selectedMoment.focus}</div></div>
              <div className="rounded-2xl bg-violet-50 p-4"><div className="text-xs text-violet-700">Talk</div><div className="mt-2 text-2xl font-semibold">{selectedMoment.participation}</div></div>
              <div className="rounded-2xl bg-amber-50 p-4"><div className="text-xs text-amber-700">Ideas</div><div className="mt-2 text-2xl font-semibold">{selectedMoment.idea}</div></div>
              <div className="rounded-2xl bg-emerald-50 p-4"><div className="text-xs text-emerald-700">Respond</div><div className="mt-2 text-2xl font-semibold">{selectedMoment.responsivity}</div></div>
            </div>
            <div className="grid gap-4 md:grid-cols-[.9fr_1.1fr]">
              <div className="space-y-4 rounded-2xl border p-4">
                <div><div className="text-sm font-medium">Transcript snippet</div><p className="mt-2 text-sm leading-6 text-muted-foreground">“{selectedMoment.transcript}”</p></div>
                <Separator />
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div>Attention class: <span className="font-medium text-foreground">{selectedMoment.metrics.attentionClass}</span></div>
                  <div>Object focus: <span className="font-medium text-foreground">{selectedMoment.metrics.objectFocus}</span></div>
                  <div>Participation score: <span className="font-medium text-foreground">{selectedMoment.metrics.participationScore}</span></div>
                  <div>Newness: <span className="font-medium text-foreground">{selectedMoment.metrics.newness}</span></div>
                  <div>Responsivity: <span className="font-medium text-foreground">{selectedMoment.metrics.responsivity}</span></div>
                </div>
              </div>
              <div className="space-y-4 rounded-2xl border p-4">
                <div className="flex items-center gap-2 font-medium"><Bot className="h-4 w-4" />LLM interpretation</div>
                <p className="text-sm leading-7 text-muted-foreground">{selectedMoment.llmExplanation}</p>
                <div className="rounded-2xl bg-muted p-4"><div className="flex items-center gap-2 text-sm font-medium"><HelpCircle className="h-4 w-4" />Reflection prompt</div><p className="mt-2 text-sm leading-6 text-muted-foreground">{selectedMoment.reflectionQuestion}</p></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  const VersionFour = () => (
    <div className="grid gap-6 xl:grid-cols-[.8fr_.7fr_1fr]">
      <Card className="rounded-3xl border-0 shadow-sm">
        <CardHeader>
          <CardTitle className="text-xl">Session snapshot</CardTitle>
          <CardDescription>Compact overview for quick comparison with moment and Q&amp;A panels.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <MetricBar label="Verbal participation" value={selectedParticipant.overall.verbalParticipation} emphasize="risk" />
          <MetricBar label="Idea contribution" value={selectedParticipant.overall.ideaContribution} emphasize="risk" />
          <MetricBar label="Task focus" value={selectedParticipant.overall.taskFocus} emphasize="good" />
          <div className="rounded-2xl bg-muted p-4 text-sm leading-6">{selectedParticipant.overall.summary}</div>
        </CardContent>
      </Card>

      <Card className="rounded-3xl border-0 shadow-sm">
        <CardHeader>
          <CardTitle className="text-xl">Moment queue</CardTitle>
          <CardDescription>Fast side panel for scanning strong versus declining moments.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {timelineData.map((item) => (
              <TimelinePill key={item.id} item={item} selected={selectedMoment.id === item.id} onClick={() => setSelectedMomentId(item.id)} />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-3xl border-0 shadow-sm">
        <CardHeader>
          <CardTitle className="text-xl">Live coach workspace</CardTitle>
          <CardDescription>Designed for active questioning while viewing the selected moment.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-2xl border p-4">
            <div className="flex items-center justify-between">
              <div className="font-medium">Selected moment</div>
              {statusBadge(selectedMoment.status)}
            </div>
            <div className="mt-2 text-sm text-muted-foreground">{selectedMoment.range} • {selectedMoment.transcript}</div>
          </div>
          <div className="flex gap-2">
            <Input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about this moment or the whole session" className="rounded-2xl" />
            <Button className="rounded-2xl"><Zap className="h-4 w-4" /></Button>
          </div>
          <div className="rounded-2xl bg-muted p-4 text-sm leading-7">{syntheticResponse}</div>
          <div className="rounded-2xl border p-4">
            <div className="text-sm font-medium">Suggested additions for this version</div>
            <ul className="mt-2 space-y-2 text-sm text-muted-foreground">
              <li>• Peer comparison toggle</li>
              <li>• Replay clip button for the selected moment</li>
              <li>• Teacher feedback lane</li>
              <li>• Confidence meter for each explanation</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <div className={`min-h-screen bg-gradient-to-b ${versionAccent(version)} p-6`}>
      <div className="mx-auto max-w-7xl space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="space-y-4"
        >
          <Card className="rounded-3xl border-0 shadow-sm">
            <CardHeader>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-3xl">Collaboration Reflection Dashboard</CardTitle>
                  <CardDescription className="mt-2 max-w-3xl text-sm leading-6">
                    Four compareable dashboard directions for student-facing collaboration feedback. Each version uses attention-catching color cues to mark strong patterns, decline zones, and moments that deserve closer reflection.
                  </CardDescription>
                </div>
                <Badge className="rounded-full px-4 py-1 text-xs"><Sparkles className="mr-1 h-3.5 w-3.5" />LLM-Enhanced</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <VersionCards version={version} setVersion={setVersion} />
              <div className="grid gap-4 lg:grid-cols-[1fr_.7fr]">
                <div>
                  <div className="mb-2 text-sm font-medium">Participant</div>
                  <Select value={selectedParticipantId} onValueChange={setSelectedParticipantId}>
                    <SelectTrigger className="rounded-2xl">
                      <SelectValue placeholder="Select participant" />
                    </SelectTrigger>
                    <SelectContent>
                      {participants.map((p) => (
                        <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="rounded-2xl border p-4 text-sm leading-6">
                  <div className="flex items-center gap-2 font-medium"><Brain className="h-4 w-4" />How to compare the versions</div>
                  <p className="mt-2 text-muted-foreground">Version 1 is balanced, Version 2 is alert-first, Version 3 is timeline-first, and Version 4 is a multitasking workspace. This makes it easier to choose the layout that best fits your research goal and student workflow.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <Tabs defaultValue="session" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 rounded-2xl">
            <TabsTrigger value="session">Session synthesis</TabsTrigger>
            <TabsTrigger value="moment">Moment explanation</TabsTrigger>
            <TabsTrigger value="qa">Reflective Q&amp;A</TabsTrigger>
          </TabsList>

          <TabsContent value="session" className="space-y-6">
            {version === "v1" && <VersionOne />}
            {version === "v2" && <VersionTwo />}
            {version === "v3" && <VersionThree />}
            {version === "v4" && <VersionFour />}
          </TabsContent>

          <TabsContent value="moment" className="space-y-6">
            <VersionThree />
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
                    <Input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask: When did I contribute ideas most strongly?" className="rounded-2xl" />
                    <Button className="rounded-2xl"><Search className="h-4 w-4" /></Button>
                  </div>
                  <div>
                    <div className="mb-2 text-sm font-medium">Suggested questions</div>
                    <div className="flex flex-wrap gap-2">
                      {qaExamples.map((q) => (
                        <button key={q} onClick={() => setQuestion(q)} className="rounded-full border px-3 py-1.5 text-sm transition hover:bg-muted">{q}</button>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-2xl border p-4 text-sm leading-6 text-muted-foreground">
                    <div className="font-medium text-foreground">Additional components you may want to add</div>
                    <ul className="mt-2 space-y-2">
                      <li>• Peer comparison lane to show balance against group averages</li>
                      <li>• Replay or transcript-scroll synced to the selected moment</li>
                      <li>• Confidence badge showing how strong the evidence is</li>
                      <li>• Goal-setting widget where students save one next-step action</li>
                      <li>• Teacher or facilitator note lane</li>
                      <li>• Trend sparkline for each indicator across the session</li>
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
                  <div className="rounded-2xl bg-muted p-5 text-sm leading-7">{syntheticResponse}</div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="rounded-2xl border p-4"><div className="text-xs text-muted-foreground">Evidence windows</div><div className="mt-2 font-semibold">3 retrieved</div></div>
                    <div className="rounded-2xl border p-4"><div className="text-xs text-muted-foreground">Computed metrics used</div><div className="mt-2 font-semibold">5 indicators</div></div>
                    <div className="rounded-2xl border p-4"><div className="text-xs text-muted-foreground">Output style</div><div className="mt-2 font-semibold">Explain + coach</div></div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default CollaborationFeedbackDashboardPrototype;
