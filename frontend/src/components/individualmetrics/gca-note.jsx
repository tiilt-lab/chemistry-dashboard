// Attribution shown wherever the Participation & Impact metrics render: the
// scores implement the Group Communication Analysis framework, and the credit
// belongs in the UI, not just the pipeline code.
function GcaNote() {
    return (
        <div className="text-xs text-tiilt-muted">
            Metrics from Group Communication Analysis (GCA) —{" "}
            <a
                className="underline"
                href="https://doi.org/10.3758/s13428-018-1102-z"
                target="_blank"
                rel="noreferrer"
            >
                Dowell, Nixon &amp; Graesser (2019)
            </a>
        </div>
    )
}

export { GcaNote }
