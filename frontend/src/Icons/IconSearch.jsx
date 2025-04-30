import * as React from "react";
const SvgIconSearch = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={24} height={24} {...props}>
    <defs>
      <linearGradient
        id="icon-search_svg__a"
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
      fill="url(#icon-search_svg__a)"
      fillRule="nonzero"
      d="M10.993 3a7 7 0 0 0-4.066 12.698 6.99 6.99 0 0 0 8.252-.102l4.096 4.108a1 1 0 0 0 1.419 0 1 1 0 0 0 0-1.42l-4.106-4.098a7 7 0 0 0 .652-7.32A6.99 6.99 0 0 0 10.993 3m0 11.996a4.997 4.997 0 0 1-4.995-4.998 4.997 4.997 0 0 1 4.995-4.999 4.997 4.997 0 0 1 4.996 4.999 4.997 4.997 0 0 1-4.996 4.998"
    />
  </svg>
);
export default SvgIconSearch;
