import * as React from "react";
const SvgCheckmark = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    xmlSpace="preserve"
    width={32}
    height={32}
    {...props}
  >
    <path
      fillRule="evenodd"
      d="M27.704 8.397a1.016 1.016 0 0 0-1.428 0L11.988 22.59l-6.282-6.193a1.016 1.016 0 0 0-1.428 0 .994.994 0 0 0 0 1.414l6.999 6.899c.39.386 1.039.386 1.429 0L27.704 9.811a.99.99 0 0 0 0-1.414c-.394-.391.395.39 0 0"
      clipRule="evenodd"
    />
  </svg>
);
export default SvgCheckmark;
