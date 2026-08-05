import style from './context-menu.module.css';
import OptionIcon from "@icons/IconKebab";
import { useState, useEffect, useRef } from 'react';
import React from 'react';
import { useLocation } from 'react-router-dom';


function AppContextMenu(props) {
  const [isOpen, setIsopen] = useState(true);
  let location = useLocation();
  const ref = React.useRef(null);

  useEffect(() => {
    if(props.setcallback!=undefined){
    props.setcallback(toggle)
    }
    document.body.addEventListener("click", onClickOutside);
    return () => document.removeEventListener("click", onClickOutside);
  }, [])
  
  const onClickOutside = (e) => {
      const element = e.target;
      if (ref.current && !ref.current.contains(element)) {
        e.preventDefault();
        e.stopPropagation();
        setIsopen(true);
      }
  };
  

  const toggle = (state) => {
    setIsopen(!state);
    //prevent triggering click interaction
    if (location.pathname == "/topic-list" || location.pathname == "/topic-list/new-session") {
      props.reverseToggle();
    }
  }

  //@HostListener('window:click', ['$event.target'])
  // const onClick = (targetElement) => {
  //   const clickedInside = this.elementRef.nativeElement.contains(targetElement);
  //   if (!clickedInside && isOpen) {
  //     setIsopen(false);
  //   }
  // }

  const dynamicInnerChild = () => {
    if (!isOpen) {
      return (
        <div className={style["dropdown-menu-container"]}>
          {props.children}
        </div>)
    }
  }

  return (
    <div className={style["menu-container"]}>
      <button className={style["menu-button"]} ref={ref} onClick={() => toggle(isOpen)}>
        <svg x="0" y="0" width="24" height="24" viewBox="0 0 24 24">
          <OptionIcon></OptionIcon>
        </svg>
      </button>
      {dynamicInnerChild()}
    </div>
  )
}
export { AppContextMenu }
