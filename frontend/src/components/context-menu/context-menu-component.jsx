import style from './context-menu.module.css';
import OptionIcon from "@icons/IconKebab";
import { useState, useEffect } from 'react';
import React from 'react';
import { useLocation } from 'react-router-dom';


function AppContextMenu(props) {
  // Legacy inverted state: true = menu CLOSED, false = menu OPEN.
  const [isOpen, setIsopen] = useState(true);
  let location = useLocation();
  const ref = React.useRef(null);

  useEffect(() => {
    if(props.setcallback!=undefined){
    props.setcallback(toggle)
    }
  }, [])

  // Close on outside click — listener exists only while the menu is open.
  // (It used to be registered permanently per menu instance and called
  // preventDefault on every click, which cancelled native default actions
  // like checkbox toggles anywhere on the page.)
  useEffect(() => {
    if (isOpen) return;
    document.body.addEventListener("click", onClickOutside);
    return () => document.body.removeEventListener("click", onClickOutside);
  }, [isOpen])

  // Escape closes the open menu and returns focus to the trigger.
  useEffect(() => {
    if (isOpen) return;
    const onKey = (e) => {
      if (e.key === "Escape") {
        setIsopen(true);
        if (ref.current) ref.current.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen])

  const onClickOutside = (e) => {
      const element = e.target;
      if (ref.current && !ref.current.contains(element)) {
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

  const dynamicInnerChild = () => {
    if (!isOpen) {
      return (
        <div className={style["dropdown-menu-container"]} role="menu">
          {props.children}
        </div>)
    }
  }

  return (
    <div className={style["menu-container"]}>
      <button
        className={style["menu-button"]}
        ref={ref}
        onClick={() => toggle(isOpen)}
        aria-label={props.label || "Options"}
        aria-haspopup="menu"
        aria-expanded={!isOpen}
      >
        <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
          <OptionIcon></OptionIcon>
        </svg>
      </button>
      {dynamicInnerChild()}
    </div>
  )
}
export { AppContextMenu }
