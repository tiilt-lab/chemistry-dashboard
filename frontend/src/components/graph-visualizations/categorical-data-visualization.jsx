import React, { useMemo, useState } from "react";
import { CategoryTimelinePage } from "./html-page-timeline"
import { CategoryDistributionPage } from "./html-page-distribution"


// type Categoty = {
// start: number;
// end: number;
// duration: number;
// emotion: Emotion;
// };

// const EMOTION_COLORS = {
//     sad: "#6A7FDB", // indigo
//     happy: "#22C55E", // green-500
//     neutral: "#9CA3AF", // gray-400
//     angry: "#EF4444", // red-500
//     surprise: "#F59E0B", // amber-500
// };


// const EMOTION_LABELS = {
//     sad: "Sad",
//     happy: "Happy",
//     neutral: "Neutral",
//     angry: "Angry",
//     surprise: "Surprise",
//     disgust: "Disgust",
//     fear: "Fear"
// };

// const sampleData = [
//     { time: 0.0, category: "neutral" },
// ];

function formatSeconds(s) {
    const sign = s < 0 ? "-" : "";
    const abs = Math.max(0, Math.abs(s));
    const mm = Math.floor(abs / 60);
    const ss = (abs % 60).toFixed(2).padStart(5, "0");
    return mm > 0 ? `${sign}${mm}:${ss}` : `${sign}${ss}s`;
}

function median(values) {
    if (!values.length) return 1;
    const arr = [...values].sort((a, b) => a - b);
    const mid = Math.floor(arr.length / 2);
    return arr.length % 2 ? arr[mid] : (arr[mid - 1] + arr[mid]) / 2;
}

function chooseAggregate(samples, aggregate) {
    if (!samples.length) return null;
    if (aggregate === "first") return samples[0].category;
    if (aggregate === "last") return samples[samples.length - 1].category;
    // majority
    const counts = new Map();
    for (const s of samples) counts.set(s.category, (counts.get(s.category) || 0) + 1);
    let best = null;
    let bestCount = -1;
    for (const [e, c] of counts.entries()) {
        if (c > bestCount) {
            best = e;
            bestCount = c;
        }
    }
    return best;
}

function computeCategoryObject(data) {
    let Category = {}
    if (data.length > 0) {
        data.forEach((d) => {
            if (!(d in Category)) {
                Category[d] = d
            }
        })
    }

    return Category
}

// main function: build map for a list of labels
function buildSpacedColorMap(labels, { sat = 65, light = 55, minHueGap = 18 } = {}) {
    const usedHues = [];
    const labelColorMap = {};

    function nearestGapOK(h) {
        return usedHues.every(uh => {
            const diff = Math.abs(uh - h);
            const circ = Math.min(diff, 360 - diff);
            return circ >= minHueGap;
        });
    }

    function nextAcceptableHue(seedHue) {
        let h = seedHue % 360;
        if (usedHues.length === 0) return h;
        // try a few steps with golden angle to find a slot
        for (let i = 0; i < 360; i++) {
            const cand = (seedHue + i * 137.508) % 360;
            if (nearestGapOK(cand)) return cand;
        }
        return h; // fallback
    }

    function hslToHex(h, s, l) {
        s /= 100; l /= 100;
        const k = n => (n + h / 30) % 12;
        const a = s * Math.min(l, 1 - l);
        const f = n => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
        const toHex = x => Math.round(255 * x).toString(16).padStart(2, "0");
        return `#${toHex(f(0))}${toHex(f(8))}${toHex(f(4))}`;
    }

    function hashString(str) {
        let h = 5381;
        for (let i = 0; i < str.length; i++) h = ((h << 5) + h) + str.charCodeAt(i);
        return h >>> 0;
    }

    for (const label of labels) {
        const seedHue = hashString(String(label)) % 360;
        const hue = nextAcceptableHue(seedHue);
        usedHues.push(hue);
        labelColorMap[label] = hslToHex(hue, sat, light);
    }

    return labelColorMap;
}

// Utility to compute distribution with the same logic as the timeline
function computeDistribution({
    data,
    labelColor,
    totalDuration,
    mode = "discrete",
    granularity = 1,
    aggregate = "majority",
}) {
    const sorted = [...data].sort((a, b) => a.time - b.time);
    if (sorted.length === 0) return {
        distribution: new Map(), duration: 0
    };

    let dur = 0;
    if (typeof totalDuration === "number" && totalDuration > 0) {
        dur = totalDuration;
    } else if (mode === "segments") {
        const steps = [];
        for (let i = 1; i < sorted.length; i++) steps.push(sorted[i].time - sorted[i - 1].time);
        const defaultStep = median(steps) || 1;
        dur = sorted[sorted.length - 1].time + defaultStep;
    } else {
        dur = Math.ceil(sorted[sorted.length - 1].time + (granularity || 1));
    }

    const distribution = new Map();
    (Object.keys(labelColor)).forEach((e) => distribution.set(e, 0));

    if (mode === "segments") {
        for (let i = 0; i < sorted.length; i++) {
            const start = Math.max(0, sorted[i].time);
            const end = i < sorted.length - 1 ? sorted[i + 1].time : dur;
            const d = Math.max(0, end - start);
            distribution.set(sorted[i].category, (distribution.get(sorted[i].category) || 0) + d);
        }
    } else {
        const step = Math.max(0.1, granularity || 1);
        const bins = Math.max(1, Math.ceil(dur / step));
        let idx = 0;
        for (let b = 0; b < bins; b++) {
            const start = b * step;
            const end = Math.min(dur, (b + 1) * step);
            const inBin = [];
            while (idx < sorted.length && sorted[idx].time < end) {
                if (sorted[idx].time >= start) inBin.push(sorted[idx]);
                idx++;
            }
            const cat = chooseAggregate(inBin, aggregate);
            if (cat) distribution.set(cat, (distribution.get(cat) || 0) + (end - start));
        }
    }

    return { distribution, duration: dur };
}


/**
 * 
 * Components
 */

function CategoricalTimeline({
    data,
    title,
    labels,
    totalDuration,
    height = 24,
    rounded = true,
    mode = "discrete",
    granularity = 1,
    aggregate = "majority",
}) {
    const [hover, setHover] = useState(null);

    const CATEGORY_LABELS = computeCategoryObject(labels)
    const CATEGORY_COLORS = buildSpacedColorMap(labels)
    const { segments, duration, distribution } = useMemo(() => {
        if (!data || data.length === 0) {
            return { segments, duration, distribution: new Map() };
        }


        const sorted = [...data].sort((a, b) => a.time - b.time);


        // Infer duration
        let dur = 0;
        if (typeof totalDuration === "number" && totalDuration > 0) {
            dur = totalDuration;
        } else if (mode === "segments") {
            const steps = [];
            for (let i = 1; i < sorted.length; i++) steps.push(sorted[i].time - sorted[i - 1].time);
            const defaultStep = median(steps) || 1;
            dur = sorted[sorted.length - 1].time + defaultStep;
        } else {
            dur = Math.ceil(sorted[sorted.length - 1].time + (granularity || 1));
        }


        let segs = [];


        if (mode === "segments") {
            // Previous behavior: persistence until next start
            for (let i = 0; i < sorted.length; i++) {
                const start = Math.max(0, sorted[i].time);
                const end = i < sorted.length - 1 ? sorted[i + 1].time : dur;
                const duration = Math.max(0, end - start);
                if (duration > 0.0001) segs.push({ start, end, duration, category: sorted[i].category });
            }
        } else {
            // NEW: discrete bins (no persistence). Each bin is granularity seconds.
            const step = Math.max(0.1, granularity || 1);
            const bins = Math.max(1, Math.ceil(dur / step));
            let idx = 0;
            for (let b = 0; b < bins; b++) {
                const start = b * step;
                const end = Math.min(dur, (b + 1) * step);
                const inBin = [];
                while (idx < sorted.length && sorted[idx].time < end) {
                    if (sorted[idx].time >= start) inBin.push(sorted[idx]);
                    idx++;
                }
                const cat = chooseAggregate(inBin, aggregate);
                if (cat) {
                    segs.push({ start, end, duration: end - start, category: cat });
                } else {
                    // If no sample in this bin, we leave a gap (transparent). Alternatively, carry last value.
                }
            }

            // Merge adjacent bins with the same category into larger segments for cleaner rendering
            const merged = [];
            for (const s of segs) {
                const last = merged[merged.length - 1];
                if (last && last.category === s.category && Math.abs(last.end - s.start) < 1e-9) {
                    last.end = s.end;
                    last.duration += s.duration;
                } else {
                    merged.push({ ...s });
                }
            }
            segs = merged;
        }


        // Clamp and compute distribution
        segs.forEach((s) => {
            s.end = Math.min(s.end, dur);
            s.duration = Math.max(0, s.end - s.start);
        });


        const dist = new Map();
        (Object.keys(CATEGORY_COLORS)).forEach((e) => dist.set(e, 0));
        segs.forEach((s) => dist.set(s.category, (dist.get(s.category) || 0) + s.duration));


        return { segments: segs, duration: dur, distribution: dist };
    }, [data, totalDuration, mode, granularity, aggregate]);


    const ticks = useMemo(() => {
        if (duration <= 0) return [];
        const desired = Math.min(10, Math.max(3, Math.round(duration / 5)));
        const step = Math.max(1, Math.round(duration / desired));
        const arr = [];
        for (let t = 0; t <= duration; t += step) arr.push(Math.min(duration, t));
        if (arr[arr.length - 1] !== duration) arr.push(duration);
        return arr;
    }, [duration])

    return (
        <CategoryTimelinePage
            mode={mode}
            title={title}
            formatSeconds={formatSeconds}
            duration={duration}
            ticks={ticks}
            segments={segments}
            rounded={rounded}
            height={height}
            CATEGORY_COLORS={CATEGORY_COLORS}
            CATEGORY_LABELS={CATEGORY_LABELS}
            hover={hover}
            setHover={setHover}
            distribution={distribution}
        />
    )

}

function CategoricalDistributionChart({
    data,
    totalDuration,
    title,
    labels,
    mode = "discrete",
    granularity = 1,
    aggregate = "majority",
    heightPerBar = 26,
    barRadius = 10,
    showValues = true,
}) {

    const CATEGORY_LABELS = computeCategoryObject(labels)
    const CATEGORY_COLORS = buildSpacedColorMap(labels)
    const { distribution, duration } = useMemo(() => {
        // Reuse the timeline computation to ensure identical logic
        const temp = CategoricalTimeline({
            // @ts-expect-error invoke to reuse memo logic; we won't render this
            data,
            title,
            labels,
            totalDuration,
            mode,
            granularity,
            aggregate,
            height: 0,
            rounded: false,
        });
        // Above "invocation" is not correct in React. We'll replicate distribution calc here instead.
        return computeDistribution({ data, labelColor: CATEGORY_COLORS, totalDuration, mode, granularity, aggregate });
    }, [data, CATEGORY_COLORS, totalDuration, mode, granularity, aggregate]);

    // Build sorted list for stable order (Sad, Happy, Neutral, Angry, Surprise)
    const categorys = Object.keys(CATEGORY_LABELS) ;
    const rows = categorys.map((e) => ({ category: e, seconds: distribution.get(e) || 0 }));
    const maxSec = Math.max(1, ...rows.map((r) => r.seconds));
    const width = 720;
    const height = rows.length * heightPerBar + 40; // + axis area


    return (
        <CategoryDistributionPage
            title={title}
            formatSeconds={formatSeconds}
            maxSec={maxSec}
            width={width}
            height={height}
            rows={rows}
            heightPerBar={heightPerBar}
            CATEGORY_LABELS={CATEGORY_LABELS}
            CATEGORY_COLORS={CATEGORY_COLORS}
            barRadius={barRadius}
            showValues={showValues}
            duration={duration}
        />
    )
}

export { CategoricalTimeline, CategoricalDistributionChart }