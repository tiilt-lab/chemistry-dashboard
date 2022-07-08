import style from './context-menu.module.css';
import optionIcon from "../../assets/img/icon-kebab.svg";
import { useState, useEffect } from 'react';

function AppContextMenu(props) {

  const [isOpen, setIsopen] = useState(true);

  useEffect(() => {
    if(props.setcallback!=undefined){
    props.setcallback(toggle)
    }
  }, [])

  const toggle = (state) => {
    setIsopen(!state);
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