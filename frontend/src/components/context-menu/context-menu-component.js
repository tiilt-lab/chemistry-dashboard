import style from './context-menu.module.css';
import optionIcon from "../../assets/img/icon-kebab.svg";
import { useState, useEffect } from 'react';
import React from 'react';

function AppContextMenu(props) {
  //ask about this: using this link https://www.codedaily.io/tutorials/Create-a-Dropdown-in-React-that-Closes-When-the-Body-is-Clicked
  let container = React.createRef();
  const [isOpen, setIsopen] = useState(true);

  useEffect(() => {
    if(props.setcallback!=undefined){
    props.setcallback(toggle)
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.removeEventListener("mousedown", handleClickOutside);
  }, [])

  const toggle = (state) => {
    setIsopen(!state);
  }
  
  
  const handleClickOutside = (event) => {
    if (this.container.current && !this.container.current.contains(event.target)) {
      setIsopen(false);
    }
  };

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
    <div className={style["menu-container"]} ref={container}>
      <button className={style["menu-button"]} onClick={() => toggle(isOpen)}>
        <svg x="0" y="0" width="24" height="24" viewBox="0 0 24 24">
          <use xlinkHref={`${optionIcon}#kebab`}></use>
        </svg>
      </button>
      {dynamicInnerChild()}
    </div>
  )
}
export { AppContextMenu }
