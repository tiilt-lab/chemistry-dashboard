import React from "react"
import { AppSpinner } from "../../spinner/spinner-component"

import style from "../../student-dashboard/student-dashboard.module.css"

function CategoryDistributionPage(props) {
    return (
      <> 
    <div className="w-full max-w-5xl mx-auto">
      <h3 className="text-base font-semibold mb-2">{props.title} Distribution</h3>
      <div className="text-xs text-gray-500 mb-3">Total duration: {props.formatSeconds(props.duration)}</div>
      <svg viewBox={`0 0 ${props.width} ${props.height}`} className="w-full">
        {/* X-axis ticks */}
        {Array.from({ length: 6 }).map((_, i) => {
          const t = (i / 5) * props.maxSec;
          const x = 140 + (t / props.maxSec) * (props.width - 160);
          return (
            <g key={i} transform={`translate(${x},0)`}>
              <line x1={0} y1={10} x2={0} y2={props.height - 20} className="stroke-gray-200" />
              <text x={0} y={10} textAnchor="middle" className="fill-gray-500 text-[10px]">
                {Math.round(t)}s
              </text>
            </g>
          );
        })}

        {props.rows.map((r, idx) => {
          const y = 20 + idx * props.heightPerBar + 4;
          const barW = ((r.seconds || 0) / props.maxSec) * (props.width - 160);
          const x = 140;
          return (
            <g key={r.category}>
              {/* label */}
              <text x={0} y={y + props.heightPerBar * 0.7} className="fill-gray-700 text-xs">
                {props.CATEGORY_LABELS[r.category]}
              </text>

              {/* bar background */}
              <rect x={x} y={y} width={props.width - 160} height={props.heightPerBar - 8} rx={props.barRadius} ry={props.barRadius} fill="#F3F4F6" />

              {/* value bar */}
              <rect x={x} y={y} width={barW} height={props.heightPerBar - 8} rx={props.barRadius} ry={props.barRadius} fill={props.CATEGORY_COLORS[r.category]} />

              {/* value label */}
              {props.showValues && (
                <text x={x + barW + 6} y={y + props.heightPerBar * 0.7} className="fill-gray-600 text-xs">
                  {props.formatSeconds(r.seconds)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
    </>
  );

    
}

export{CategoryDistributionPage}