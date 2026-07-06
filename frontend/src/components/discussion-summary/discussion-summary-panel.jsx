import { useState } from "react"
import { btnPrimary } from "../dialog-styles"
import { ApiService } from "../../services/api-service"

// On-demand LLM summary of a pod's discussion (overview, key moments,
// participation read, suggestions). Triggered by a button since it calls Gemini.
export function DiscussionSummaryPanel({ sessionId, sessionDeviceId }) {
    const [data, setData] = useState(null)
    const [state, setState] = useState("idle") // idle | loading | error

    const generate = () => {
        setState("loading")
        new ApiService()
            .httpRequestCall(
                `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/summary`,
                "GET",
                {},
            )
            .then((r) => (r.status === 200 ? r.json() : Promise.reject()))
            .then((d) => {
                if (d && d.summary) {
                    setData(d)
                    setState("idle")
                } else {
                    setState("error")
                }
            })
            .catch(() => setState("error"))
    }

    return (
        <div className="flex w-full flex-col gap-3">
            {!data ? (
                <div className="flex items-center gap-3">
                    <button
                        onClick={generate}
                        disabled={state === "loading"}
                        className={btnPrimary + " disabled:opacity-50"}
                    >
                        {state === "loading"
                            ? "Generating…"
                            : "Generate AI summary"}
                    </button>
                    {state === "error" ? (
                        <span className="text-xs text-tiilt-danger">
                            Couldn't generate a summary — check that a valid
                            GOOGLE_API_KEY is configured.
                        </span>
                    ) : (
                        <span className="text-xs text-tiilt-muted">
                            Uses the transcript to produce an overview, key
                            moments, and suggestions.
                        </span>
                    )}
                </div>
            ) : (
                <div className="flex flex-col gap-4 text-sm">
                    <p className="text-tiilt-ink">{data.summary}</p>
                    {data.key_moments && data.key_moments.length ? (
                        <div>
                            <div className="font-ahamono mb-1 text-[11px] tracking-wider text-tiilt-muted uppercase">
                                Key moments
                            </div>
                            <ul className="list-disc pl-5 text-tiilt-ink">
                                {data.key_moments.map((m, i) => (
                                    <li key={i}>{m}</li>
                                ))}
                            </ul>
                        </div>
                    ) : null}
                    {data.participation ? (
                        <div>
                            <div className="font-ahamono mb-1 text-[11px] tracking-wider text-tiilt-muted uppercase">
                                Participation
                            </div>
                            <p className="text-tiilt-ink">{data.participation}</p>
                        </div>
                    ) : null}
                    {data.suggestions && data.suggestions.length ? (
                        <div>
                            <div className="font-ahamono mb-1 text-[11px] tracking-wider text-tiilt-muted uppercase">
                                Suggestions
                            </div>
                            <ul className="list-disc pl-5 text-tiilt-ink">
                                {data.suggestions.map((m, i) => (
                                    <li key={i}>{m}</li>
                                ))}
                            </ul>
                        </div>
                    ) : null}
                </div>
            )}
        </div>
    )
}
