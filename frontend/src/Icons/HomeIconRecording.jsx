import * as React from "react";
const SvgHomeIconRecording = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={28} height={28} {...props}>
    <defs>
      <linearGradient
        id="home_icon_recording_svg__a"
        x1="-33.288%"
        x2="133.29%"
        y1="-94.434%"
        y2="167.969%"
      >
        <stop offset="0%" stopColor="#764BFF" stopOpacity={0.96} />
        <stop offset="100%" stopColor="#7BB7F1" />
      </linearGradient>
      <linearGradient
        id="home_icon_recording_svg__b"
        x1="-10.857%"
        x2="103.932%"
        y1="-78.877%"
        y2="115.546%"
      >
        <stop offset="0%" stopColor="#764BFF" />
        <stop offset="100%" stopColor="#7BB7F1" />
      </linearGradient>
    </defs>
    <g fill="none" fillRule="evenodd" transform="translate(-2 -2)">
      <circle cx={16} cy={16} r={8} fill="url(#home_icon_recording_svg__a)" />
      <circle
        cx={16}
        cy={16}
        r={13}
        stroke="url(#home_icon_recording_svg__b)"
        strokeWidth={2}
      />
    </g>
  </svg>
);
export default SvgHomeIconRecording;
