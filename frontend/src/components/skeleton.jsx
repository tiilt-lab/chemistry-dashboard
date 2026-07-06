// Pulsing placeholder rows shown while lists load (perceived-speed win
// over a spinner + "Loading..." text).
function SkeletonRows({ rows = 6, className = "" }) {
    return (
        <div
            aria-hidden="true"
            className={"flex animate-pulse flex-col gap-1.5 " + className}
        >
            {Array.from({ length: rows }, (_, i) => (
                <div
                    key={i}
                    className="flex items-center gap-2.5 rounded-lg border border-tiilt-line bg-white px-3 py-2.5"
                >
                    <div className="h-8 w-8 flex-none rounded-md bg-tiilt-soft" />
                    <div className="flex min-w-0 grow flex-col gap-1.5">
                        <div
                            className="h-3 rounded bg-tiilt-line/60"
                            style={{ width: `${45 + ((i * 17) % 35)}%` }}
                        />
                        <div
                            className="h-2.5 rounded bg-tiilt-line/40"
                            style={{ width: `${25 + ((i * 23) % 30)}%` }}
                        />
                    </div>
                </div>
            ))}
        </div>
    )
}

export { SkeletonRows }
