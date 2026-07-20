// E2E: the full pod lifecycle against a running deployment.
//   join by passcode -> device check -> saved-fingerprint speaker ->
//   start recording -> timer ticks -> end recording -> flushed artifact.
//
// Runs against a LIVE server (it creates and deletes its own session), so
// it needs credentials and is NOT part of default CI:
//
//   BLINC_BASE_URL=https://... BLINC_EMAIL=... BLINC_PASSWORD=... \
//   BLINC_SAVED_ALIAS=<enrolled username> node tests/e2e/join-record.spec.js
//
// Requires: npm i -D playwright (chromium), a reachable deployment.
const { chromium } = require('playwright');

const BASE = process.env.BLINC_BASE_URL;
const EMAIL = process.env.BLINC_EMAIL;
const PASSWORD = process.env.BLINC_PASSWORD;
const ALIAS = process.env.BLINC_SAVED_ALIAS; // optional: enrolled username

if (!BASE || !EMAIL || !PASSWORD) {
  console.error('Set BLINC_BASE_URL, BLINC_EMAIL, BLINC_PASSWORD');
  process.exit(2);
}

async function api(context, path, body) {
  const r = await context.request.post(BASE + path, { data: body });
  if (!r.ok()) throw new Error(path + ' -> ' + r.status());
  return r.json();
}

(async () => {
  const browser = await chromium.launch({
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
  });
  const context = await browser.newContext({
    viewport: { width: 393, height: 852 },
    permissions: ['camera', 'microphone'],
  });

  // bootstrap: login + disposable session via API
  await api(context, '/api/v1/login', { email: EMAIL, password: PASSWORD });
  const session = await api(context, '/api/v1/sessions', {
    // session names reject punctuation — keep it to letters/spaces
    name: 'E2E join record', devices: 0, keyword_list_id: null,
    topic_model_id: null, byod: true, features: [], doa: false, folder: null,
  });
  console.log('session', session.id, session.passcode);

  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  try {
    await page.goto(`${BASE}/join/${session.passcode}`, { waitUntil: 'networkidle' });
    await page.selectOption('#joinwith', 'Video');
    await page.click('text=Connect to server');

    await page.waitForSelector('text=Check your devices', { timeout: 20000 });
    await page.click('text=Looks good — join session');

    await page.waitForSelector('text=Speaker Fingerprint', { timeout: 30000 });
    if (ALIAS) {
      await page.getByRole('button', { name: '+ Add speaker' }).click();
      await page.waitForSelector('#newspeakername', { timeout: 10000 });
      await page.fill('#newspeakername', ALIAS);
      await page.getByRole('button', { name: 'Add', exact: true }).click();
      await page.waitForSelector('[aria-label="Fingerprinted"]', { timeout: 30000 });
    }
    await page.getByRole('button', { name: 'Join Session' }).click();

    await page.waitForSelector('text=Connected — not recording yet', { timeout: 30000 });
    await page.getByRole('button', { name: 'Start recording' }).click();
    await page.waitForSelector('text=Recording', { timeout: 20000 });
    await page.waitForTimeout(15000); // stream a bit; > 1 media chunk

    await page.getByRole('button', { name: 'End recording' }).click();
    await page.click('button:has-text("Yes")');
    await page.waitForSelector('text=recording has ended', { timeout: 20000 });

    if (errors.length) throw new Error('console errors: ' + errors.join(' | '));
    console.log('PASS');
  } finally {
    await context.request.post(`${BASE}/api/v1/sessions/${session.id}/stop`).catch(() => {});
    await context.request.delete(`${BASE}/api/v1/sessions/${session.id}`).catch(() => {});
    await browser.close();
  }
})().catch((e) => { console.error('FAIL:', e.message); process.exit(1); });
