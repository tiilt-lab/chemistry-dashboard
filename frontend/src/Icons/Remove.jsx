import * as React from "react";
const SvgRemove = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={24}
    height={24}
    viewBox="0 0 12 12"
    {...props}
  >
    <path
      fill="#AAAAB3"
      d="M11.607 10.192 7.364 5.95l4.243-4.242A.999.999 0 1 0 10.193.293L5.95 4.535 1.707.293A.999.999 0 1 0 .294 1.707L4.536 5.95.293 10.192a.999.999 0 1 0 1.414 1.414l4.241-4.243 4.244 4.243a.999.999 0 1 0 1.414-1.414"
      className="remove_svg__remove-icon"
    />
  </svg>
);
export default SvgRemove;
