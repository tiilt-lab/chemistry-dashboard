import * as React from "react";
const SvgHome = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={24}
    height={24}
    fill="#7878FA"
    {...props}
  >
    <path
      fillRule="evenodd"
      d="m12 7-1-2H4L3 7v12h18V7zm7 2h-8.236l-1-2H5.236L5 7.472V17h14z"
      clipRule="evenodd"
    />
    <path
      fillRule="evenodd"
      d="M16.5 13H15v3h-2v-2h-2v2H9v-3H7.5l4.5-3z"
      clipRule="evenodd"
    />
  </svg>
);
export default SvgHome;
