import * as React from "react";
const SvgOpenFolder = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={24}
    height={24}
    fill="none"
    {...props}
  >
    <mask id="open-folder_svg__a" fill="#fff">
      <path
        fillRule="evenodd"
        d="m11 5 1 2h9v3h2l-3 9H3V7l1-2zM5.775 17h12.783l1.667-5H7.442zM19 10H6l-1 3V7.472L5.236 7h4.528l1 2H19z"
        clipRule="evenodd"
      />
    </mask>
    <path
      fill="#F8F8F8"
      fillRule="evenodd"
      d="m11 5 1 2h9v3h2l-3 9H3V7l1-2zM5.775 17h12.783l1.667-5H7.442zM19 10H6l-1 3V7.472L5.236 7h4.528l1 2H19z"
      clipRule="evenodd"
    />
    <path
      fill="#7878FA"
      d="m12 7-1.789.894L10.764 9H12zm-1-2 1.789-.894L12.236 3H11zm10 2h2V5h-2zm0 3h-2v2h2zm2 0 1.897.633L25.775 8H23zm-3 9v2h1.442l.455-1.367zM3 19H1v2h2zM3 7l-1.789-.894L1 6.528V7zm1-2V3H2.764L2.21 4.106zm1.775 12-1.898-.633L3 19h2.775zm12.783 0v2H20l.456-1.367zm1.667-5 1.897.633L23 10h-2.775zM7.442 12v-2H6l-.456 1.367zM19 10v2h2v-2zM6 10V8H4.558l-.455 1.368zm-1 3H3l3.897.633zm0-5.528-1.789-.894L3 7v.472zM5.236 7V5H4l-.553 1.106zm4.528 0 1.789-.894L11 5H9.764zm1 2-1.789.894L9.528 11h1.236zM19 9h2V7h-2zm-5.211-2.894-1-2L9.21 5.894l1 2zM21 5h-9v4h9zm2 5V7h-4v3zm0-2h-2v4h2zm-1.103 11.633 3-9-3.794-1.265-3 9zM19.5 21h.5v-4h-.5zM3 21h16.5v-4H3zM1 7v12h4V7zm1.211-2.894-1 2L4.79 7.894l1-2zM11 3H4v4h7zM5.775 19h12.783v-4H5.775zm14.68-1.367 1.668-5-3.795-1.265-1.667 5zM20.226 10H7.442v4h12.783zm-14.68 1.367-1.668 5 3.795 1.265 1.667-5zM19 8H6v4h13zM4.103 9.368l-1 3 3.794 1.265 1-3zM3 7.472V13h4V7.472zm.447-1.366-.236.472L6.79 8.367l.236-.473zM9.764 5H5.236v4h4.528zm2.789 3.106-1-2-3.578 1.788 1 2zM19 7h-8.236v4H19zm2 3V9h-4v1z"
      mask="url(#open-folder_svg__a)"
    />
  </svg>
);
export default SvgOpenFolder;
