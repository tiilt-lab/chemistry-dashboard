import { useState } from "react";
import style from './add-button.module.css'
function AddButtonComponent(props) {
  // @Input('isFocused') isFocused: boolean;
  // @Input('isInvalid') isInvalid: boolean;
  const [isClicked, setIsclicked] = useState(false);

  return (
    <div className={props.isClicked ? `${style["add-button"]} ${style["invalid"]}` : props.isInvalid ? `${style["add-button"]} ${style["invalid"]}` : style["add-button"]} onMouseDown={() => props.isClicked = true} onMouseUp={() => props.isClicked = false}>
      {props.isFocused ?
        <svg width="24px" height="24px" viewBox="0 0 24 24" version="1.1">
          <g id="atom/icon/add/default" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
            <g className={style["add-icon"]} transform="translate(2.000000, 2.000000)">
              <path d="M10,0 C15.523,0 20,4.477 20,10 C20,15.523 15.523,20 10,20 C4.477,20 0,15.523 0,10 C0,4.477 4.477,0 10,0 Z M14,9 L11,9 L11,6 C11,5.448 10.552,5 10,5 C9.448,5 9,5.448 9,6 L9,9 L6,9 C5.448,9 5,9.448 5,10 C5,10.552 5.448,11 6,11 L9,11 L9,14 C9,14.552 9.448,15 10,15 C10.552,15 11,14.552 11,14 L11,11 L14,11 C14.552,11 15,10.552 15,10 C15,9.448 14.552,9 14,9 Z" id="Combined-Shape"></path>
            </g>
          </g>
        </svg>
        :
        <></>
      }

      {!props.isFocused ?
        <svg width="24px" height="24px" viewBox="0 0 24 24" version="1.1">
          <g id="atom/icon/add-alt/default" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
            <g className={style["add-icon"]} transform="translate(2.000000, 2.000000)">
              <path d="M14,9 C14.552,9 15,9.448 15,10 C15,10.552 14.552,11 14,11 L11,11 L11,14 C11,14.552 10.552,15 10,15 C9.448,15 9,14.552 9,14 L9,11 L6,11 C5.448,11 5,10.552 5,10 C5,9.448 5.448,9 6,9 L9,9 L9,6 C9,5.448 9.448,5 10,5 C10.552,5 11,5.448 11,6 L11,9 L14,9 Z M10,0 C15.523,0 20,4.477 20,10 C20,15.523 15.523,20 10,20 C4.477,20 0,15.523 0,10 C0,4.477 4.477,0 10,0 Z M10,2 C5.589,2 2,5.589 2,10 C2,14.411 5.589,18 10,18 C14.411,18 18,14.411 18,10 C18,5.589 14.411,2 10,2 Z" id="Combined-Shape"></path>
            </g>
          </g>
        </svg>

        :
        <></>
      }

    </div>
  )
}
