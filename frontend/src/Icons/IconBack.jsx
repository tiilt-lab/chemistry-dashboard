import * as React from "react";
const SvgIconBack = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={24} height={24} {...props}>
    <defs>
      <linearGradient
        id="icon-back_svg__a"
        x1="-33.288%"
        x2="133.29%"
        y1="-94.434%"
        y2="167.969%"
      >
        <stop offset="0%" stopColor="#764BFF" />
        <stop offset="100%" stopColor="#7BB7F1" />
      </linearGradient>
    </defs>
    <path
      fill="url(#icon-back_svg__a)"
      fillRule="nonzero"
      d="M15.62 16.72 11.09 12l4.53-4.72a1.36 1.36 0 0 0 0-1.89 1.25 1.25 0 0 0-1.81 0l-5.43 5.67a1.35 1.35 0 0 0 0 1.88l5.43 5.67a1.25 1.25 0 0 0 1.81 0 1.36 1.36 0 0 0 0-1.89"
    />
  </svg>
);
export default SvgIconBack;
