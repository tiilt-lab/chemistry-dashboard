import React from "react"

function CategoryTimelinePage(props) {
    return (
        <div className="w-full max-w-5xl mx-auto p-4">
            <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold tracking-tight">{props.title} Timeline ({props.mode})</h2>
                <div className="text-sm text-gray-500">Total: {props.formatSeconds(props.duration)}</div>
            </div>


            {/* Timeline container */}
            <div className="relative w-full select-none">
                {/* Grid / ticks */}
                <div className="relative h-10">
                    <div className="absolute inset-0 bg-gradient-to-b from-gray-100 to-gray-50 rounded-xl" />
                    {/* tick lines */}
                    <div className="absolute inset-0">
                        {props.ticks.map((t, idx) => {
                            const left = (t / (props.duration || 1)) * 100;
                            return (
                                <div key={`tick-${t}-${idx}`} className="absolute top-0 h-full" style={{ left: `${left}%` }}>
                                    <div className="w-px h-full bg-gray-200" />
                                    <div className="absolute -translate-x-1/2 mt-2 text-[10px] text-gray-500">{Math.round(t)}s</div>
                                </div>
                            );
                        })}
                    </div>


                    {/* segments */}
                    <div className="absolute inset-0 flex rounded-xl overflow-hidden" style={{height: props.height }}>
                        {props.segments.map((s, i) => {
                            const left = (s.start / (props.duration || 1)) * 100;
                            const width = (s.duration / (props.duration || 1)) * 100;
                            const borderRadius = props.rounded ? (i === 0 ? "16px 0 0 16px" : i === props.segments.length - 1 ? "0 16px 16px 0" : "0") : "0";
                            return (
                                <div
                                    key={i}
                                    className="absolute top-0 h-full cursor-pointer transition-transform hover:scale-y-105"
                                    style={{ left: `${left}%`, width: `${width}%`, backgroundColor: props.CATEGORY_COLORS[s.category], borderRadius }}
                                    onMouseEnter={() => props.setHover(s)}
                                    onMouseLeave={() => props.setHover(null)}
                                    aria-label={`${props.CATEGORY_LABELS[s.category]} from ${props.formatSeconds(s.start)} to ${props.formatSeconds(s.end)}`}
                                />
                            );
                        })}
                    </div>


                    {/* hover tooltip */}
                    {props.hover && (
                        <div
                            className="absolute -top-12 left-0 transform -translate-x-1/2 rounded-xl shadow-lg bg-white px-3 py-2 text-xs border border-gray-200"
                            style={{ left: `${((props.hover.start + props.hover.end) / 2 / (props.duration || 1)) * 100}%` }}
                        >
                            <div className="font-medium" style={{ color: props.CATEGORY_COLORS[props.hover.category] }}>
                                {props.CATEGORY_LABELS[props.hover.category]}
                            </div>
                            <div className="text-gray-600">
                                {props.formatSeconds(props.hover.start)} → {props.formatSeconds(props.hover.end)}
                            </div>
                            <div className="text-gray-500">{props.hover.duration.toFixed(2)}s</div>
                        </div>
                    )}
                </div>
            </div>

            {/* Legend + distribution */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex flex-wrap items-center gap-3">
                    {(Object.keys(props.CATEGORY_COLORS)).map((e) => (
                        <div key={e} className="flex items-center gap-2">
                            <span className="inline-block w-3 h-3 rounded" style={{ backgroundColor: props.CATEGORY_COLORS[e] }} />
                            <span className="text-sm text-gray-700">{props.CATEGORY_LABELS[e]}</span>
                        </div>
                    ))}
                </div>


                {/* Distribution bar */}
                <div className="relative w-full h-3 rounded-full overflow-hidden bg-gray-100">
                    {(Object.keys(props.CATEGORY_COLORS)).map((e) => {
                        const dur = props.distribution.get(e) || 0;
                        const pct = props.duration > 0 ? (dur / props.duration) * 100 : 0;
                        if (pct <= 0) return null;
                        return (
                            <div key={`dist-${e}`} className="absolute top-0 bottom-0" style={{ width: `${pct}%`, backgroundColor: props.CATEGORY_COLORS[e] }} />
                        );
                    })}
                </div>
                <div className="text-xs text-gray-500">
                    {(Object.keys(props.CATEGORY_COLORS))
                        .map((e) => {
                            const dur = props.distribution.get(e) || 0;
                            const pct = props.duration > 0 ? (dur / props.duration) * 100 : 0;
                            return `${props.CATEGORY_LABELS[e]} ${pct.toFixed(1)}%`;
                        })
                        .join(" · ")}
                </div>
            </div>
        </div>
    );

}
export { CategoryTimelinePage }