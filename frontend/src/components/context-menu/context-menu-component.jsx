import style from './context-menu.module.css';
import OptionIcon from "@icons/IconKebab";
import { useState, useEffect } from 'react';
import React from 'react';
import { useLocation } from 'react-router-dom';


// Only one context menu may be open at a time, app-wide: opening a menu
// closes whichever one was open before it.
let closeOpenMenu = null;

function AppContextMenu(props) {
  // Legacy inverted state: true = menu CLOSED, false = menu OPEN.
  const [isOpen, setIsopen] = useState(true);
  // Viewport coords for the fixed-position dropdown (escapes overflow
  // containers like the table wrappers).
  const [menuPos, setMenuPos] = useState({ top: 0, right: 0 });
  let location = useLocation();
  const ref = React.useRef(null);
  // When this menu opened. Auto-close handlers (outside click, scroll) ignore
  // events in the first moment after opening — otherwise closing a sibling
  // menu and this one opening in the same click can immediately re-close it.
  const openedAt = React.useRef(0);
  const settledRecently = () => Date.now() - openedAt.current < 250;

  // A fixed-position menu doesn't follow its trigger when an ancestor
  // scrolls — close it instead of letting it float away.
  useEffect(() => {
    if (isOpen) return;
    const close = () => {
      if (!settledRecently()) setIsopen(true);
    };
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => {
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    };
  }, [isOpen]);

  useEffect(() => {
    if(props.setcallback!=undefined){
    props.setcallback(toggle)
    }
  }, [])

  // Close on outside click — listener exists only while the menu is open.
  // (It used to be registered permanently per menu instance and called
  // preventDefault on every click, which cancelled native default actions
  // like checkbox toggles anywhere on the page.)
  // Attach on the next tick so the very click that opened this menu (still
  // bubbling to the body) doesn't immediately close it.
  useEffect(() => {
    if (isOpen) return;
    const id = setTimeout(() => {
      document.body.addEventListener("click", onClickOutside);
    }, 0);
    return () => {
      clearTimeout(id);
      document.body.removeEventListener("click", onClickOutside);
    };
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
      if (settledRecently()) return;
      const element = e.target;
      if (ref.current && !ref.current.contains(element)) {
        setIsopen(true);
      }
  };


  const toggle = (state) => {
    if (state && ref.current) {
      // Close any other open menu first, then register ours.
      if (closeOpenMenu) closeOpenMenu();
      closeOpenMenu = () => setIsopen(true);
      openedAt.current = Date.now();
      // Opening: anchor the fixed dropdown under the trigger's right edge,
      // or above it when the viewport bottom would cut the menu off.
      const rect = ref.current.getBoundingClientRect();
      const estimatedHeight =
        React.Children.count(props.children) * 40 + 10;
      const openUp =
        window.innerHeight - rect.bottom < estimatedHeight &&
        rect.top > estimatedHeight;
      setMenuPos({
        top: openUp ? undefined : rect.bottom + 4,
        bottom: openUp ? window.innerHeight - rect.top + 4 : undefined,
        right: Math.max(8, window.innerWidth - rect.right),
      });
    }
    setIsopen(!state);
    //prevent triggering click interaction
    if (location.pathname == "/topic-list" || location.pathname == "/topic-list/new-session") {
      props.reverseToggle();
    }
  }

  const dynamicInnerChild = () => {
    if (!isOpen) {
      return (
        <div
          className={style["dropdown-menu-container"]}
          style={{ top: menuPos.top, bottom: menuPos.bottom, right: menuPos.right }}
          role="menu"
        >
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
