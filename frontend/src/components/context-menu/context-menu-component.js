import './context-menu-component.scss';
import optionIcon from "../../assets/img/icon-kebab.svg";
import { useState } from 'react';

function AppContextMenu(props) {

  const [isOpen, setIsopen] = useState(true);

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
      <div  className="dropdown-menu-container">
          {props.children}
      </div>)
        }
    }

  return (
    <div className="menu-container">
      <button className="menu-button" onClick={()=> toggle(isOpen)}>
        <svg x="0" y="0" width="24" height="24" viewBox="0 0 24 24">
          <use xlinkHref={`${optionIcon}#kebab`}></use>
        </svg>
      </button>
      {dynamicInnerChild()} 
    </div>
  )
}
export {AppContextMenu}