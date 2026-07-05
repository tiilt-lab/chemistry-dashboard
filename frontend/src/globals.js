// File for generic functions.

// Date format expected 'YYYY-MM-DD HH:MM:SS.mmmmmm UTC'
export function stringToDate(dateString) {
  let date = new Date(dateString); // Chrome
  if (isNaN(date.getTime())) { // Firefox
    date = new Date(dateString.replace(' UTC', 'Z'));
  }
  if (isNaN(date.getTime())) { // Safari
    date = new Date(dateString.replace(' ', 'T').replace(' UTC', 'Z'));
  }
  return date;
}

export function formatDate(date) {
  const monthNames = [
    'January', 'February', 'March',
    'April', 'May', 'June', 'July',
    'August', 'September', 'October',
    'November', 'December'
  ];

  return date.getDate() + ' ' + monthNames[date.getMonth()] + ' ' + date.getFullYear();
}

export function degrees_to_radians(degrees) {
  return degrees * (Math.PI / 180);
}

export function sin(degrees) {
  let result = Math.round(Math.sin(degrees_to_radians(degrees)) * 1000) / 1000;
  if (result === 0) {
      result = Math.abs(result);
  }
  return result;
}

export function cos(degrees) {
  let result = Math.round(Math.cos(degrees_to_radians(degrees)) * 1000) / 1000;
  if (result === 0) {
      result = Math.abs(result);
  }
  return result;
}

export function formatSeconds(seconds, padding = false) {
  const h = Math.floor(seconds / 3600).toString();
  const m = Math.floor((seconds % 3600) / 60).toString();
  const s = Math.floor((seconds % 60)).toString();
  let result = '';
  if (h !== '0') {
    result = h.padStart(2, '0') + ':';
  }
  return result + m.padStart(2, '0') + ':' + s.padStart(2, '0');
}

export function similarityToRGB(similarity) {
  const color = Math.floor(230 - (230 * similarity / 100));
  return 'rgb(' + color + ',' + color + ', 255)';
}

// Canonical per-speaker colors: alphabetical name order -> palette index, so
// every panel (transcript, video analytics, dynamics) gives the same person
// the same color regardless of each panel's data ordering. Presentation only.
export const SPEAKER_PALETTE = [
    "#3a2163",
    "#00a79d",
    "#c0007a",
    "#b26a00",
    "#4d7c1f",
    "#2e3192",
    "#b3261e",
    "#6d28d9",
]
export function speakerColorFor(name, allNames) {
    const sorted = [...new Set(allNames || [])].sort()
    const i = Math.max(0, sorted.indexOf(name))
    return SPEAKER_PALETTE[i % SPEAKER_PALETTE.length]
}

// Clock-style HH:MM:SS from seconds (shared by transcripts + reflection dashboards).
export function formatHMS(s) {
  const date = new Date(1000 * Math.floor(s));
  return date.toISOString().substr(11, 8);
}
