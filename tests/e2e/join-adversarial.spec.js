// Adversarial E2E for the join client — the safety net for the join-machine
// migration (esp. step 4, collapsing the reducer). Each scenario reproduces a
// bug class we actually shipped and fixed this cycle, so a regression in the
// state machine fails here instead of in a classroom.
//
// Runs against a LIVE deployment (creates + deletes its own session), so it
// needs credentials and stays OUT of CI (public repo). Run manually:
//
//   BLINC_BASE_URL=https://... BLINC_EMAIL=... BLINC_PASSWORD=... \
//   BLINC_SAVED_ALIAS=<enrolled username> node tests/e2e/join-adversarial.spec.js
//
// Requires playwright (chromium) resolvable via NODE_PATH if not local.
//
// NOT automatable here, verify by hand on a real iPhone:
//   * iOS silently muting the mic on an audio-route change (AirPods/Siri/call)
//     — the mic watchdog should raise "No microphone signal" within ~10s.
//     Chromium can't reproduce iOS audio-session behavior.
const { chromium } = require("playwright")

const BASE = process.env.BLINC_BASE_URL
const EMAIL = process.env.BLINC_EMAIL
const PASSWORD = process.env.BLINC_PASSWORD
const ALIAS = process.env.BLINC_SAVED_ALIAS // enrolled username, optional

if (!BASE || !EMAIL || !PASSWORD) {
    console.error("Set BLINC_BASE_URL, BLINC_EMAIL, BLINC_PASSWORD")
    process.exit(2)
}

const results = []
const record = (name, ok, detail) => {
    results.push({ name, ok, detail })
    console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`)
}

const phase = (p) => p.evaluate(() => document.body.dataset.joinPhase || null)

// Drive a fresh pod up to the live recording screen, ready to Start.
async function joinToReady(ctx, passcode, { video = true, alias } = {}) {
    const p = await ctx.newPage()
    p._consoleErrors = []
    p.on("pageerror", (e) => p._consoleErrors.push(e.message))
    await p.goto(`${BASE}/join/${passcode}`, { waitUntil: "networkidle" })
    if (video) await p.selectOption("#joinwith", "Video")
    await p.click("text=Connect to server")
    await p.waitForSelector("text=Check your devices", { timeout: 20000 })
    await p.click("text=Looks good — join session")
    await p.waitForSelector("text=Speaker Fingerprint", { timeout: 30000 })
    if (alias) {
        await p.getByRole("button", { name: "+ Add speaker" }).click()
        await p.waitForSelector("#newspeakername", { timeout: 10000 })
        await p.fill("#newspeakername", alias)
        await p.getByRole("button", { name: "Add", exact: true }).click()
        await p.waitForSelector('[aria-label="Fingerprinted"]', { timeout: 30000 })
    }
    await p.getByRole("button", { name: "Join Session" }).click()
    await p.waitForSelector("text=Connected — not recording yet", { timeout: 30000 })
    return p
}

async function api(ctx, path, body, method = "post") {
    const r = await ctx.request[method](BASE + path, body ? { data: body } : undefined)
    return r
}

async function main() {
    const browser = await chromium.launch({
        args: [
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
        ],
    })
    const ctx = await browser.newContext({
        viewport: { width: 393, height: 852 },
        permissions: ["camera", "microphone"],
    })
    await api(ctx, "/api/v1/login", { email: EMAIL, password: PASSWORD })
    const session = await (
        await api(ctx, "/api/v1/sessions", {
            name: "E2E adversarial",
            devices: 0,
            keyword_list_id: null,
            topic_model_id: null,
            byod: true,
            features: [],
            doa: false,
            folder: null,
        })
    ).json()
    console.log("session", session.id, session.passcode)

    try {
        // --- Scenario 1: mid-session disconnect reconnects and does NOT
        // dead-end. The stale-closure onclose bug sent every drop to
        // "Couldn't reach the session server"; it should instead reconnect
        // (armed survives) with no "Binary audio data sent before start".
        try {
            const p = await joinToReady(ctx, session.passcode, { alias: ALIAS })
            await p.getByRole("button", { name: "Start recording" }).click()
            await p.waitForSelector("text=Recording", { timeout: 20000 })
            const before = await phase(p)

            await ctx.setOffline(true)
            await p.waitForTimeout(3500) // let the socket drop + onclose fire
            await ctx.setOffline(false)

            // Within a few retry cycles it should recover — NOT show the
            // dead-end, and NOT the binary-before-start error.
            await p.waitForTimeout(12000)
            const body = await p.evaluate(() => document.body.innerText)
            const deadEnd = /Couldn't reach the session server/i.test(body)
            const binaryErr = /Binary audio data sent before start/i.test(body)
            const after = await phase(p)
            const recovered =
                after === "recording" ||
                after === "connecting" ||
                after === "enrolling" ||
                after === "ready"
            record(
                "disconnect reconnects without dead-end",
                before === "recording" && recovered && !deadEnd && !binaryErr,
                `phase ${before}->${after}, deadEnd=${deadEnd}, binaryErr=${binaryErr}`,
            )
            await p.close()
        } catch (e) {
            record("disconnect reconnects without dead-end", false, e.message.split("\n")[0])
        }

        // --- Scenario 2: a recording shorter than the 10s chunk interval must
        // still end cleanly (the flush-on-end fix); no hang, no error.
        try {
            const p = await joinToReady(ctx, session.passcode, { alias: ALIAS })
            await p.getByRole("button", { name: "Start recording" }).click()
            await p.waitForSelector("text=Recording", { timeout: 20000 })
            await p.waitForTimeout(4000) // < 10s chunk boundary
            await p.getByRole("button", { name: "End recording" }).click()
            await p.click('button:has-text("Yes")')
            await p.waitForSelector("text=recording has ended", { timeout: 20000 })
            record("short recording ends cleanly", true)
            await p.close()
        } catch (e) {
            record("short recording ends cleanly", false, e.message.split("\n")[0])
        }

        // --- Scenario 3: the session-ended dialog has real content (the ghost
        // empty-square dialog regression).
        try {
            const p = await joinToReady(ctx, session.passcode, { alias: ALIAS })
            await p.getByRole("button", { name: "Start recording" }).click()
            await p.waitForSelector("text=Recording", { timeout: 20000 })
            await p.getByRole("button", { name: "End recording" }).click()
            await p.click('button:has-text("Yes")')
            const dialog = await p.waitForSelector("text=recording has ended", {
                timeout: 15000,
            })
            const txt = (await dialog.innerText()).trim()
            record("ended dialog is not an empty ghost", txt.length > 10, `"${txt.slice(0, 40)}"`)
            const phaseEnded = (await phase(p)) === "ended"
            record("phase reaches 'ended'", phaseEnded)
            await p.close()
        } catch (e) {
            record("ended dialog is not an empty ghost", false, e.message.split("\n")[0])
        }

        // --- Scenario 4: a saved-fingerprint lookup for an unknown username
        // surfaces an error instead of hanging (the never-replied crash).
        try {
            const p = await ctx.newPage()
            await p.goto(`${BASE}/join/${session.passcode}`, { waitUntil: "networkidle" })
            await p.selectOption("#joinwith", "Video")
            await p.click("text=Connect to server")
            await p.waitForSelector("text=Check your devices", { timeout: 20000 })
            await p.click("text=Looks good — join session")
            await p.waitForSelector("text=Speaker Fingerprint", { timeout: 30000 })
            await p.getByRole("button", { name: "+ Add speaker" }).click()
            await p.waitForSelector("#newspeakername", { timeout: 10000 })
            // Unknown but validation-legal name (NAME_CHARS excludes '_').
            await p.fill("#newspeakername", "GuestTester")
            await p.getByRole("button", { name: "Add", exact: true }).click()
            // The invariant this guards is "no hang / no crash" — a speaker
            // row appears and the screen stays functional (Join Session
            // still reachable), NOT the exact rendered name.
            await p.waitForSelector('[aria-label^="Options for"]', { timeout: 15000 })
            const joinable = await p
                .getByRole("button", { name: "Join Session" })
                .isVisible()
            record("unknown saved-fingerprint username does not hang", joinable)
            await p.close()
        } catch (e) {
            record("unknown saved-fingerprint username does not hang", false, e.message.split("\n")[0])
        }
    } finally {
        await api(ctx, `/api/v1/sessions/${session.id}/stop`).catch(() => {})
        await api(ctx, `/api/v1/sessions/${session.id}`, null, "delete").catch(() => {})
        await browser.close()
    }

    const failed = results.filter((r) => !r.ok)
    console.log(`\n${results.length - failed.length}/${results.length} passed`)
    process.exit(failed.length ? 1 : 0)
}

main().catch((e) => {
    console.error("HARNESS ERROR:", e.message)
    process.exit(1)
})
