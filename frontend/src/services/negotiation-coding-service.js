import { ApiService } from "./api-service"

// Negotiation coding (Kellogg "Viking" case): a local LLM codes every
// utterance of a pod's transcript on four dimensions, rolled up per team
// (the two sides named by the session's pod setup) and per speaker. Every call resolves to { status, body }
// where body is the parsed JSON (null when the response has none, e.g. a
// 404 for a pod that was never coded) so callers branch on the status.
const base = (sessionId, sessionDeviceId) =>
    `api/v1/sessions/${sessionId}/devices/${sessionDeviceId}/negotiation_coding`

function parse(r) {
    return r.json().then(
        (body) => ({ status: r.status, body }),
        () => ({ status: r.status, body: null }),
    )
}

export class NegotiationCodingService {
    api = new ApiService()

    // Latest run + teams + per-utterance codes + summary; 404 when never run.
    get(sessionId, sessionDeviceId) {
        return this.api
            .httpRequestCall(base(sessionId, sessionDeviceId), "GET", {})
            .then(parse)
    }

    // Queue a (re-)run. teams is optional {speaker_tag: <team name>};
    // resolves 202 {run_id, status: "queued"}.
    run(sessionId, sessionDeviceId, teams) {
        const body = teams && Object.keys(teams).length > 0 ? { teams } : {}
        return this.api
            .httpRequestCall(base(sessionId, sessionDeviceId), "POST", body)
            .then(parse)
    }

    // Re-assign speakers to teams; the summary is recomputed server-side and
    // the response has the same shape as get().
    setTeams(sessionId, sessionDeviceId, teams) {
        return this.api
            .httpRequestCall(base(sessionId, sessionDeviceId) + "/teams", "PUT", {
                teams: teams || {},
            })
            .then(parse)
    }

    // Paired sessions: this pod's breakout group and side ({group, side};
    // blank clears both). Resolves 200 {session_device, partner_device_id,
    // first_device_id}; the next run uses the new role.
    setRole(sessionId, sessionDeviceId, role) {
        return this.api
            .httpRequestCall(base(sessionId, sessionDeviceId) + "/role", "PUT", {
                group: (role && role.group) || "",
                side: (role && role.side) || "",
            })
            .then(parse)
    }

    // Absolute URL of the CSV download (a plain link: the session cookie goes
    // along with the navigation, so no fetch is needed).
    exportCsvUrl(sessionId, sessionDeviceId) {
        return this.api.getEndpoint() + base(sessionId, sessionDeviceId) + "/export.csv"
    }

    // Session-wide downloads (plain links, as above): every group's coded
    // transcript in one CSV, and every transcript row of every pod with what
    // the coding did with it (coded / stitched / dropped and why / uncoded).
    sessionExportCsvUrl(sessionId) {
        return this.api.getEndpoint() + `api/v1/sessions/${sessionId}/negotiation_coding/export.csv`
    }

    sessionTranscriptCsvUrl(sessionId) {
        return this.api.getEndpoint() + `api/v1/sessions/${sessionId}/negotiation_coding/transcript.csv`
    }

    // Fetch the CSV as text (for callers that want to save it themselves).
    exportCsv(sessionId, sessionDeviceId) {
        return this.api
            .httpRequestCall(base(sessionId, sessionDeviceId) + "/export.csv", "GET", {})
            .then((r) => r.text().then((text) => ({ status: r.status, text })))
    }
}
