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
  return accdisplaytrans;
}
