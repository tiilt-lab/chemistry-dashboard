import * as React from "react";
const SvgIconRecord = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={24} height={24} {...props}>
    <defs>
      <linearGradient
        id="icon-record_svg__a"
        x1="-33.288%"
        x2="133.29%"
        y1="-94.434%"
        y2="167.969%"
      >
        <stop offset="0%" stopColor="#764BFF" />
        <stop offset="100%" stopColor="#7BB7F1" />
      </linearGradient>
    </defs>
    <g fill="url(#icon-record_svg__a)" fillRule="nonzero">
      <circle cx={12} cy={12} r={4} />
      <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10A10 10 0 0 0 12 2m0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16" />
    </g>
  </svg>
);
export default SvgIconRecord;
