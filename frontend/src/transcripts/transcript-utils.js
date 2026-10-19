import { similarityToRGB } from "../globals";

// Decorates raw transcripts with per-word keyword matches/colors and a
// direction-of-arrival color. The live and client transcript views share
// this loop; only their angleToColor fallback differs, so it's injected.
export function decorateTranscripts(transcripts, showKeywords, showDoA, angleToColor) {
  const accdisplaytrans = [];
  for (const transcript of transcripts) {
    const result = [];
    const words = transcript.transcript.split(' ');
    for (const word of words) {
      const matchingKeywords = [];
      let highestSimilarity = 0;
      if (showKeywords) {
        for (const keyword of transcript.keywords) {
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
  const over = speakingOver(accdisplaytrans);
  for (const transcript of accdisplaytrans) {
    transcript['speakingOver'] = over.get(transcript.id) || [];
  }
  return accdisplaytrans;
}

// Seconds two lines must share before one counts as speaking over the other.
// Live rows are stamped in whole seconds, so a line that starts the second
// the previous one ends is a turn change, not an overlap.
export const OVERLAP_MIN_SECONDS = 0.5;

// For each line, the speakers it talks over: earlier lines by someone else
// that are still going when it starts, by at least OVERLAP_MIN_SECONDS.
// The later line is the one that cuts in, so it carries the mark. Unnamed
// lines are left out on either side: the overlap cannot be told from a
// recognizer cutting one voice in two. Returns Map(line id -> [speaker tags]).
export function speakingOver(lines, minOverlap = OVERLAP_MIN_SECONDS) {
  const timed = (lines || [])
    .filter((l) => l && l.speaker_tag && l.start_time != null && l.length != null)
    .map((l) => ({ id: l.id, tag: l.speaker_tag, start: Number(l.start_time), end: Number(l.start_time) + Number(l.length) }))
    .filter((l) => Number.isFinite(l.start) && Number.isFinite(l.end))
    .sort((a, b) => a.start - b.start || a.end - b.end);
  const out = new Map();
  for (let i = 0; i < timed.length; i++) {
    const b = timed[i];
    for (let j = i - 1; j >= 0; j--) {
      const a = timed[j];
      if (b.start - a.start > 120) break; // no line in a negotiation runs two minutes
      if (a.tag === b.tag) continue;
      if (Math.min(a.end, b.end) - b.start >= minOverlap) {
        const tags = out.get(b.id) || [];
        if (!tags.includes(a.tag)) tags.push(a.tag);
        out.set(b.id, tags);
      }
    }
  }
  return out;
}
