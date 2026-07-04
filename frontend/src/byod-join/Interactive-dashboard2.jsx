import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import {
  Bot,
  Brain,
  CalendarRange,
  Flame,
  Gauge,
  GitBranch,
  Lightbulb,
  MessageSquare,
  PlayCircle,
  ScanSearch,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  Users,
  Waves,
  ChevronRight,
  Zap,
} from "lucide-react";

const participants = [
  {
    id: "hellohelio",
    name: "Helio",
    role: "High verbal presence",
    summary:
      "You were consistently active and focused. Your next step is strengthening idea uptake and making your responses more explicitly connected to peers.",
    metrics: {
      taskFocus: 81,
      verbalShare: 39,
      ideaMoves: 28,
      responsivity: 24,
      momentum: 72,
      recovery: 58,
      consistency: 76,
      initiative: 83,
      alignment: 61,
      listeningPresence: 74,
    },
    highlights: [
      "Strong early question-driven engagement",
      "High sustained attention to task artifact",
      "Good momentum across the early and middle phases",
    ],
    watchouts: [
      "Responsivity stays lower than speaking rate",
      "Idea linkage weakens in later windows",
      "Some contributions clarify more than they extend",
    ],
  },
  {
    id: "noahh",
    name: "Noah",
    role: "Focused but quieter contributor",
    summary:
      "You stayed reasonably focused, but your contribution pattern was quieter and more tentative. Your biggest opportunity is moving from observation to explicit idea-building.",
    metrics: {
      taskFocus: 67,
      verbalShare: 22,
      ideaMoves: 14,
      responsivity: 18,
      momentum: 41,
      recovery: 33,
      consistency: 55,
      initiative: 29,
      alignment: 57,
      listeningPresence: 69,
    },
    highlights: [
      "Solid task attention in earlier windows",
      "Occasional balanced participation",
      "Maintained listening presence when not speaking",
    ],
    watchouts: [
      "Late-phase engagement drop",
      "Few explicit uptake moves",
      "Low initiative in entering the discussion",
    ],
  },
  {
    id: "mondrian",
    name: "Mondrian",
    role: "Selective observer",
    summary:
      "You appear to monitor peers and task conditions, but contribute selectively. The next step is converting observation into clearer, timely contributions.",
    metrics: {
      taskFocus: 54,
      verbalShare: 11,
      ideaMoves: 8,
      responsivity: 12,
      momentum: 26,
      recovery: 44,
      consistency: 38,
      initiative: 17,
      alignment: 63,
      listeningPresence: 72,
    },
    highlights: [
      "Observed peers closely in some windows",
      "Shows monitoring behavior rather than disengagement alone",
      "Potential for stronger collaborative timing",
    ],
    watchouts: [
      "Sparse verbal contribution",
      "Low idea-building density",
      "Late windows show reduced visible engagement",
    ],
  },
];

const moments = [
  {
    id: 1,
    time: "18:44–18:57",
    label: "Launch",
    energy: 88,
    focus: 92,
    uptake: 45,
    novelty: 68,
    stability: 80,
    transcript: "What's the difference between? What's the difference?",
    explanation:
      "This is a strong launch moment. Energy, focus, and initiative are high, with clear effort to move the discussion. The main growth area is linking the question back to a peer contribution.",
  },
  {
    id: 2,
    time: "18:85–19:03",
    label: "Probe",
    energy: 59,
    focus: 70,
    uptake: 22,
    novelty: 29,
    stability: 51,
    transcript: "I don't know if that's... I don't know. You're definitely doing something. Yeah.",
    explanation:
      "This looks like a tentative probe rather than a strong idea-building move. Focus remains fair, but uptake and novelty are weaker, suggesting uncertainty or partial agreement.",
  },
  {
    id: 3,
    time: "19:19–19:29",
    label: "Dip",
    energy: 18,
    focus: 8,
    uptake: 12,
    novelty: 10,
    stability: 16,
    transcript: "Yeah, I don't know what I'm sure. There's some side of that. Yeah.",
    explanation:
      "This is a low-energy moment. The pattern suggests an engagement dip, likely a fatigue or uncertainty phase, with limited visual focus and weak collaborative momentum.",
  },
  {
    id: 4,
    time: "19:79–19:89",
    label: "Re-entry",
    energy: 33,
    focus: 12,
    uptake: 16,
    novelty: 14,
    stability: 27,
    transcript: "...makes it like if it was the example before with...",
    explanation:
      "This may be an attempted re-entry into the discussion. It hints at reconnecting to an earlier example, but the move remains underdeveloped and low in uptake.",
  },
];

const groupMetrics = [
  { label: "Participation balance", value: 64, note: "How evenly talk was distributed" },
  { label: "Shared focus", value: 71, note: "How often members converged on the task artifact" },
  { label: "Idea relay", value: 42, note: "How often one idea was picked up by another person" },
  { label: "Recovery capacity", value: 53, note: "How well the group bounced back after dips" },
];

const questionStarters = [
  "Where did I lose momentum?",
  "When was I listening well but not speaking?",
  "Which moments show the best idea relay?",
  "How often did I re-enter after a dip?",
];

function toneClass(value) {
  if (value >= 75) return "bg-emerald-500";
  if (value >= 45) return "bg-amber-400";
  return "bg-rose-500";
}

function toneSurface(value) {
  if (value >= 75) return "border-emerald-200 bg-emerald-50";
  if (value >= 45) return "border-amber-200 bg-amber-50";
  return "border-rose-200 bg-rose-50";
}

function MiniBar({ label, value }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold">{value}</span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div className={`h-2 rounded-full ${toneClass(value)}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function RadialDial({ label, value, sublabel }) {
  const angle = (value / 100) * 360;
  return (
    <div className="flex flex-col items-center gap-3 rounded-3xl border bg-background p-4">
      <div
        className="relative flex h-28 w-28 items-center justify-center rounded-full"
        style={{ background: `conic-gradient(rgb(139 92 246) 0deg ${angle}deg, rgb(228 228 231) ${angle}deg 360deg)` }}
      >
        <div className="flex h-20 w-20 flex-col items-center justify-center rounded-full bg-background">
          <div className="text-2xl font-bold">{value}</div>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground">score</div>
        </div>
      </div>
      <div className="text-center">
        <div className="text-sm font-semibold">{label}</div>
        <div className="text-xs text-muted-foreground">{sublabel}</div>
      </div>
    </div>
  );
}

function HeatStrip({ title, values }) {
  return (
    <div className="space-y-3 rounded-3xl border bg-background p-4">
      <div className="flex items-center gap-2 text-sm font-semibold"><Waves className="h-4 w-4" />{title}</div>
      <div className="grid grid-cols-8 gap-2">
        {values.map((v, idx) => (
          <div key={idx} className={`h-10 rounded-xl ${toneClass(v)} opacity-${100}`} title={`Segment ${idx + 1}: ${v}`} />
        ))}
      </div>
      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span>Start</span>
        <span>Session flow</span>
        <span>End</span>
      </div>
    </div>
  );
}

function NodeLane({ items, selected, onSelect }) {
  return (
    <div className="space-y-3">
      {items.map((item, idx) => {
        const active = selected === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onSelect(item.id)}
            className={`w-full rounded-3xl border p-4 text-left transition ${active ? "border-violet-400 bg-violet-50 shadow-sm" : `${toneSurface(item.energy)} hover:shadow-sm`}`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold">{item.label}</div>
                <div className="text-xs text-muted-foreground">{item.time}</div>
              </div>
              <Badge variant="secondary">#{idx + 1}</Badge>
            </div>
            <div className="mt-3 grid grid-cols-4 gap-2 text-[11px]">
              <div className="rounded-xl bg-white/80 p-2">
                <div className="text-muted-foreground">Energy</div>
                <div className="font-semibold">{item.energy}</div>
              </div>
              <div className="rounded-xl bg-white/80 p-2">
                <div className="text-muted-foreground">Focus</div>
                <div className="font-semibold">{item.focus}</div>
              </div>
              <div className="rounded-xl bg-white/80 p-2">
                <div className="text-muted-foreground">Uptake</div>
                <div className="font-semibold">{item.uptake}</div>
              </div>
              <div className="rounded-xl bg-white/80 p-2">
                <div className="text-muted-foreground">Novelty</div>
                <div className="font-semibold">{item.novelty}</div>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function MetricOrbit({ metrics }) {
  const items = [
    ["Momentum", metrics.momentum],
    ["Recovery", metrics.recovery],
    ["Consistency", metrics.consistency],
    ["Initiative", metrics.initiative],
    ["Alignment", metrics.alignment],
    ["Listening", metrics.listeningPresence],
  ];
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {items.map(([label, value]) => (
        <div key={label} className={`rounded-3xl border p-4 ${toneSurface(value)}`}>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
          <div className="mt-2 text-3xl font-bold">{value}</div>
          <div className="mt-3 h-2 rounded-full bg-white/70">
            <div className={`h-2 rounded-full ${toneClass(value)}`} style={{ width: `${value}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function CollaborationFeedbackDashboardPrototype() {
  const [participantId, setParticipantId] = useState("hellohelio");
  const [momentId, setMomentId] = useState(2);
  const [question, setQuestion] = useState("");

  const participant = useMemo(
    () => participants.find((p) => p.id === participantId) ?? participants[0],
    [participantId]
  );

  const selectedMoment = useMemo(
    () => moments.find((m) => m.id === momentId) ?? moments[0],
    [momentId]
  );

  const coachAnswer = useMemo(() => {
    const q = question.trim().toLowerCase();
    if (!q) {
      return "I can help interpret your collaboration as a story: where you gained momentum, where you dipped, how you recovered, and whether your ideas were picked up by others. Select a moment or ask a question to start.";
    }
    if (q.includes("momentum")) {
      return "Your momentum is strongest early in the session, where energy, focus, and initiative move together. The main drop appears in the late phase, and recovery is only partial afterward.";
    }
    if (q.includes("listening")) {
      return "Your listening presence is stronger than your verbal share. That suggests you stay with the discussion even when you are not speaking, which is valuable, but there is room to convert that presence into clearer entry points.";
    }
    if (q.includes("relay") || q.includes("idea")) {
      return "Idea relay is one of the weaker group-level dimensions. You generate some promising moves, but they are not always picked up. A next step would be to explicitly anchor your comment to a teammate's earlier idea.";
    }
    if (q.includes("recover")) {
      return "Recovery after a dip is moderate. The data suggests the group sometimes re-stabilizes after lower-energy moments, but the bounce-back is not yet strong or immediate.";
    }
    return "Your profile combines strong task focus with uneven uptake. You appear engaged and thoughtful, but your strongest gains will likely come from making your contributions easier for teammates to notice, pick up, and extend.";
  }, [question]);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(139,92,246,0.12),_transparent_25%),radial-gradient(circle_at_top_right,_rgba(34,197,94,0.10),_transparent_22%),linear-gradient(to_bottom,_#fafafa,_#f4f4f5)] p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="grid gap-6 xl:grid-cols-[1.15fr_.85fr]">
          <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm backdrop-blur">
            <CardHeader>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-3xl">Collaboration Studio</CardTitle>
                  <CardDescription className="mt-2 max-w-2xl text-sm leading-6">
                    A completely redesigned prototype centered on collaboration flow, recovery, listening presence, idea relay, and momentum — not just static participation scores.
                  </CardDescription>
                </div>
                <Badge className="rounded-full bg-violet-600 px-4 py-1 text-xs hover:bg-violet-600"><Sparkles className="mr-1 h-3.5 w-3.5" />New design</Badge>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-4">
              <div className="rounded-3xl bg-violet-50 p-4 ring-1 ring-violet-100">
                <div className="flex items-center gap-2 text-sm text-violet-700"><Users className="h-4 w-4" />Selected learner</div>
                <div className="mt-2 text-lg font-semibold">{participant.name}</div>
                <div className="text-sm text-muted-foreground">{participant.role}</div>
              </div>
              <div className="rounded-3xl bg-emerald-50 p-4 ring-1 ring-emerald-100">
                <div className="flex items-center gap-2 text-sm text-emerald-700"><TrendingUp className="h-4 w-4" />Best signal</div>
                <div className="mt-2 text-lg font-semibold">Task focus</div>
                <div className="text-sm text-muted-foreground">{participant.metrics.taskFocus}% sustained</div>
              </div>
              <div className="rounded-3xl bg-rose-50 p-4 ring-1 ring-rose-100">
                <div className="flex items-center gap-2 text-sm text-rose-700"><TrendingDown className="h-4 w-4" />Most fragile signal</div>
                <div className="mt-2 text-lg font-semibold">Idea relay</div>
                <div className="text-sm text-muted-foreground">Needs stronger peer uptake</div>
              </div>
              <div className="rounded-3xl bg-tiilt-soft p-4 ring-1 ring-tiilt-soft">
                <div className="flex items-center gap-2 text-sm text-tiilt"><CalendarRange className="h-4 w-4" />View mode</div>
                <div className="mt-2 text-lg font-semibold">Session story</div>
                <div className="text-sm text-muted-foreground">Flow, dips, and recovery</div>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm backdrop-blur">
            <CardHeader>
              <CardTitle className="text-xl">Controls</CardTitle>
              <CardDescription>Choose a participant and navigate the collaboration story.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="mb-2 text-sm font-medium">Participant</div>
                <Select value={participantId} onValueChange={setParticipantId}>
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
              <div className="rounded-3xl border bg-muted/40 p-4 text-sm leading-6 text-muted-foreground">
                This design treats collaboration as a dynamic system. New rendered measures include <span className="font-medium text-foreground">momentum</span>, <span className="font-medium text-foreground">recovery capacity</span>, <span className="font-medium text-foreground">consistency</span>, <span className="font-medium text-foreground">initiative</span>, <span className="font-medium text-foreground">alignment</span>, and <span className="font-medium text-foreground">listening presence</span>.
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <Tabs defaultValue="studio" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 rounded-2xl">
            <TabsTrigger value="studio">Studio</TabsTrigger>
            <TabsTrigger value="flow">Flow map</TabsTrigger>
            <TabsTrigger value="group">Group pulse</TabsTrigger>
            <TabsTrigger value="coach">Coach</TabsTrigger>
          </TabsList>

          <TabsContent value="studio" className="space-y-6">
            <div className="grid gap-6 xl:grid-cols-[1.12fr_.88fr]">
              <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-xl"><Gauge className="h-5 w-5" />Participant instrument cluster</CardTitle>
                  <CardDescription>A cockpit-like view of multiple collaboration dimensions, including new derived measures.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid gap-4 md:grid-cols-3">
                    <RadialDial label="Momentum" value={participant.metrics.momentum} sublabel="staying active over time" />
                    <RadialDial label="Recovery" value={participant.metrics.recovery} sublabel="bouncing back after dips" />
                    <RadialDial label="Consistency" value={participant.metrics.consistency} sublabel="stability across windows" />
                  </div>
                  <MetricOrbit metrics={participant.metrics} />
                </CardContent>
              </Card>

              <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-xl"><Target className="h-5 w-5" />Reflection brief</CardTitle>
                  <CardDescription>LLM-ready summary built on computed measures.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="rounded-3xl bg-violet-50 p-4 text-sm leading-7 ring-1 ring-violet-100">
                    {participant.summary}
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-4">
                      <div className="flex items-center gap-2 font-medium text-emerald-800"><TrendingUp className="h-4 w-4" />Strength signals</div>
                      <ul className="mt-3 space-y-2 text-sm text-emerald-900/80">
                        {participant.highlights.map((item) => (
                          <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="rounded-3xl border border-rose-200 bg-rose-50 p-4">
                      <div className="flex items-center gap-2 font-medium text-rose-800"><TrendingDown className="h-4 w-4" />Fragile signals</div>
                      <ul className="mt-3 space-y-2 text-sm text-rose-900/80">
                        {participant.watchouts.map((item) => (
                          <li key={item} className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="flow" className="space-y-6">
            <div className="grid gap-6 xl:grid-cols-[.72fr_1.28fr]">
              <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-xl"><GitBranch className="h-5 w-5" />Moment stream</CardTitle>
                  <CardDescription>Each node represents a moment in the collaboration story rather than a flat timeline row.</CardDescription>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[560px] pr-3">
                    <NodeLane items={moments} selected={momentId} onSelect={setMomentId} />
                  </ScrollArea>
                </CardContent>
              </Card>

              <div className="space-y-6">
                <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-xl">Moment microscope</CardTitle>
                        <CardDescription>{selectedMoment.label} • {selectedMoment.time}</CardDescription>
                      </div>
                      <Badge className={selectedMoment.energy >= 75 ? "bg-emerald-600 hover:bg-emerald-600" : selectedMoment.energy >= 45 ? "bg-amber-500 hover:bg-amber-500 text-black" : "bg-rose-600 hover:bg-rose-600"}>
                        {selectedMoment.energy >= 75 ? "High energy" : selectedMoment.energy >= 45 ? "Medium energy" : "Low energy"}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <div className="grid gap-4 md:grid-cols-5">
                      <MiniBar label="Energy" value={selectedMoment.energy} />
                      <MiniBar label="Focus" value={selectedMoment.focus} />
                      <MiniBar label="Uptake" value={selectedMoment.uptake} />
                      <MiniBar label="Novelty" value={selectedMoment.novelty} />
                      <MiniBar label="Stability" value={selectedMoment.stability} />
                    </div>
                    <div className="grid gap-4 lg:grid-cols-[.9fr_1.1fr]">
                      <div className="rounded-3xl border p-4">
                        <div className="text-sm font-medium">Captured speech</div>
                        <p className="mt-2 text-sm leading-7 text-muted-foreground">“{selectedMoment.transcript}”</p>
                        <Separator className="my-4" />
                        <div className="grid gap-3 md:grid-cols-2">
                          <div className="rounded-2xl bg-muted p-3">
                            <div className="text-xs text-muted-foreground">Interpretive label</div>
                            <div className="mt-1 font-semibold">{selectedMoment.label}</div>
                          </div>
                          <div className="rounded-2xl bg-muted p-3">
                            <div className="text-xs text-muted-foreground">Potential clip action</div>
                            <div className="mt-1 flex items-center gap-2 font-semibold"><PlayCircle className="h-4 w-4" />Replay segment</div>
                          </div>
                        </div>
                      </div>
                      <div className="rounded-3xl border p-4">
                        <div className="flex items-center gap-2 text-sm font-medium"><Brain className="h-4 w-4" />Explanative synthesis</div>
                        <p className="mt-2 text-sm leading-7 text-muted-foreground">{selectedMoment.explanation}</p>
                        <div className="mt-4 rounded-2xl bg-violet-50 p-4 ring-1 ring-violet-100">
                          <div className="flex items-center gap-2 text-sm font-medium"><Lightbulb className="h-4 w-4" />Reflective prompt</div>
                          <p className="mt-2 text-sm leading-6 text-muted-foreground">How could this moment have shifted from individual uncertainty to a clearer bridge into shared reasoning?</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <HeatStrip title="Session energy heat strip" values={[88, 79, 70, 64, 59, 41, 18, 33]} />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="group" className="space-y-6">
            <div className="grid gap-6 xl:grid-cols-[.9fr_1.1fr]">
              <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-xl"><Users className="h-5 w-5" />Group pulse board</CardTitle>
                  <CardDescription>Additional group-level measures derived from the same underlying signals.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {groupMetrics.map((item) => (
                    <div key={item.label} className={`rounded-3xl border p-4 ${toneSurface(item.value)}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold">{item.label}</div>
                          <div className="text-sm text-muted-foreground">{item.note}</div>
                        </div>
                        <div className="text-3xl font-bold">{item.value}</div>
                      </div>
                      <div className="mt-4 h-2 rounded-full bg-white/70">
                        <div className={`h-2 rounded-full ${toneClass(item.value)}`} style={{ width: `${item.value}%` }} />
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-xl"><Flame className="h-5 w-5" />Creative metrics you can compute from this data</CardTitle>
                  <CardDescription>These go beyond the earlier participation and focus measures.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-3xl border p-4">
                    <div className="font-semibold">Momentum score</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">Captures whether attention, speech, and idea activity stay active across adjacent windows rather than spiking only once.</p>
                  </div>
                  <div className="rounded-3xl border p-4">
                    <div className="font-semibold">Recovery capacity</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">Measures how quickly a participant or group rebounds after a dip in focus, verbal participation, or uptake.</p>
                  </div>
                  <div className="rounded-3xl border p-4">
                    <div className="font-semibold">Listening presence</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">Uses non-speaking windows with attention signals to identify whether a learner appears engaged even when silent.</p>
                  </div>
                  <div className="rounded-3xl border p-4">
                    <div className="font-semibold">Idea relay</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">Approximates whether one person’s contribution is picked up by another in nearby windows through transcript and responsivity patterns.</p>
                  </div>
                  <div className="rounded-3xl border p-4">
                    <div className="font-semibold">Entry initiative</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">Measures how often a participant actively enters the conversation after silence or after another participant has spoken.</p>
                  </div>
                  <div className="rounded-3xl border p-4">
                    <div className="font-semibold">Alignment score</div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">Combines object focus, transcript relevance, and timing to estimate whether a contribution is aligned with the group’s shared task trajectory.</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="coach" className="space-y-6">
            <div className="grid gap-6 xl:grid-cols-[.8fr_1.2fr]">
              <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-xl"><ScanSearch className="h-5 w-5" />Ask the coach</CardTitle>
                  <CardDescription>This coach can work from selected moment context, participant summary, and computed metrics.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex gap-2">
                    <Input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about momentum, listening, relay, or recovery" className="rounded-2xl" />
                    <Button className="rounded-2xl"><Zap className="h-4 w-4" /></Button>
                  </div>
                  <div>
                    <div className="mb-2 text-sm font-medium">Question starters</div>
                    <div className="flex flex-wrap gap-2">
                      {questionStarters.map((q) => (
                        <button key={q} onClick={() => setQuestion(q)} className="rounded-full border px-3 py-1.5 text-sm transition hover:bg-muted">
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-3xl border bg-muted/40 p-4 text-sm leading-6 text-muted-foreground">
                    Recommended backend behavior: compute the metrics first, retrieve relevant windows, then ask the LLM to explain patterns and coach the student. That keeps the explanations grounded and auditable.
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-[28px] border-0 bg-white/90 shadow-sm">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2 text-xl"><Bot className="h-5 w-5" />Agent coach response</CardTitle>
                      <CardDescription>Context-aware feedback using the current moment and session profile.</CardDescription>
                    </div>
                    <Badge className="bg-violet-600 hover:bg-violet-600">Agentic LLM</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-3xl border bg-violet-50 p-4 ring-1 ring-violet-100">
                    <div className="text-sm font-medium">Active context</div>
                    <div className="mt-2 text-sm text-muted-foreground">{participant.name} • {selectedMoment.label} • {selectedMoment.time}</div>
                    <div className="mt-2 text-sm leading-6 text-foreground">{selectedMoment.transcript}</div>
                  </div>
                  <div className="rounded-3xl bg-muted p-5 text-sm leading-7">
                    {coachAnswer}
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="rounded-3xl border p-4">
                      <div className="text-xs text-muted-foreground">Metrics in use</div>
                      <div className="mt-2 font-semibold">10 derived measures</div>
                    </div>
                    <div className="rounded-3xl border p-4">
                      <div className="text-xs text-muted-foreground">Evidence mode</div>
                      <div className="mt-2 font-semibold">Moment + session</div>
                    </div>
                    <div className="rounded-3xl border p-4">
                      <div className="text-xs text-muted-foreground">Coaching style</div>
                      <div className="mt-2 font-semibold">Explain + next step</div>
                    </div>
                  </div>
                  <div className="rounded-3xl border p-4 text-sm text-muted-foreground">
                    Additional visualization ideas to add next: a peer-network relay graph, a rhythm chart of speaking versus listening windows, a confidence strip for low-signal moments, and a before-versus-after phase comparison card.
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
