// File for generic functions.

// Date format expected 'YYYY-MM-DD HH:MM:SS.mmmmmm UTC'
export function stringToDate(dateString: string): Date {
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

export function formatSeconds(seconds: number, padding: boolean = false) {
  const h = Math.floor(seconds / 3600).toString();
  const m = Math.floor((seconds % 3600) / 60).toString();
  const s = Math.floor((seconds % 60)).toString();
  let result = '';
  if (h !== '0') {
    result = h.padStart(2, '0') + ':';
  }
  return result + m.padStart(2, '0') + ':' + s.padStart(2, '0');
}

export function similarityToRGB(similarity: number) {
  const color = Math.floor(230 - (230 * similarity / 100));
  return 'rgb(' + color + ',' + color + ', 255)';
}

export function validateIpAddress(ip_address) {
  // tslint:disable-next-line:max-line-length
  return /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/.test(ip_address);
}
