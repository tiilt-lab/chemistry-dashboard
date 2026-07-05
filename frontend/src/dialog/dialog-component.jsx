
import { useEffect, useRef } from 'react';
import style from './dialog.module.css';

// Shared modal behavior for every dialog primitive: real dialog semantics
// (role/aria-modal), focus moved inside on open, trapped while open,
// restored to the opener on close; Escape triggers onClose when provided.
function ModalShell({ onClose, label, containerClass, containerStyle, children }) {
  const ref = useRef(null);

  useEffect(() => {
    const node = ref.current;
    const opener = document.activeElement;
    const focusables = () =>
      [...node.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )].filter((el) => !el.disabled && el.offsetParent !== null);

    const first = focusables()[0];
    (first || node).focus();

    const onKey = (e) => {
      if (e.key === 'Escape' && onClose) {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key === 'Tab') {
        const f = focusables();
        if (f.length === 0) {
          e.preventDefault();
          return;
        }
        const i = f.indexOf(document.activeElement);
        if (e.shiftKey && i <= 0) {
          e.preventDefault();
          f[f.length - 1].focus();
        } else if (!e.shiftKey && i === f.length - 1) {
          e.preventDefault();
          f[0].focus();
        }
      }
    };
    node.addEventListener('keydown', onKey);
    return () => {
      node.removeEventListener('keydown', onKey);
      if (opener && typeof opener.focus === 'function') opener.focus();
    };
  }, []);

  return (
    <div className={style["dialog-background"]}>
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={label || undefined}
        tabIndex={-1}
        className={containerClass}
        style={containerStyle}
      >
        {children}
      </div>
    </div>
  );
}

function DialogBox(props) {
  if (!props.show) {
    return (
      <></>
    )
  }

  return (
    <ModalShell onClose={props.closedialog} label={props.heading} containerClass={style["dialog-container"]}>
      <div className={style[props.itsclass]}>
        <h2 className={style["dialog-heading"]}>{props.heading}</h2>
        {props.message}
        <button className={style["cancel-button"]} onClick={props.closedialog}>Close</button>
      </div>
    </ModalShell>
  )
}

function DialogBoxTwoOption(props) {
  if (!props.show) {
    return (<></>)
  }

  return (
    <ModalShell onClose={props.cancelbuttonaction} label={props.heading} containerClass={style["dialog-container"]}>
      <div className={props.itsclass}>
        <h2 className={style["dialog-heading"]}>{props.heading}</h2>
        <div className={style["dialog-body"]}>{props.body}</div>
        <button className={style["delete-button"]} onClick={props.deletebuttonaction} > Yes</button >
        <button className={style["cancel-button"]} onClick={props.cancelbuttonaction} > Cancel</button >
      </div>
    </ModalShell>
  )
}

function WaitingDialog(props) {
  if (!props.show) {
    return (
      <></>
    )
  }
  // No onClose: a waiting dialog must not be Escape-dismissable.
  return (
    <ModalShell label={props.heading} containerClass={style["dialog-container"]}>
      <div className={style[props.itsclass]}>
        <h2 className={style["dialog-heading"]}>{props.heading}</h2>
        {props.message}
      </div >
    </ModalShell>
  )
}

function GenericDialogBox(props) {

  if (!props.show) {
    return (
      <></>
    )
  }
  if (props.checkBox == "checkbox") {
    return (
      <ModalShell onClose={props.onClose} label={props.label || "Dialog"} containerClass={style["dialog-container-expanded"]}>
        {props.displayDevices.map((device, index) => (
          <label className={style["dc-checkbox"]}>{device.name}
              <input type="checkbox" checked={device.checked} value={device.checked} onChange={() => props.changeCheck(index)}  />
              <span className={style.checkmark}></span>
          </label>))}
        {props.children}
      </ModalShell>
    )
  }
  return (
    <ModalShell
      onClose={props.onClose}
      label={props.label || "Dialog"}
      containerClass={style["dialog-container"]}
      containerStyle={{'overflowY': props.optionsCase ? 'visible' : 'auto'}}
    >
      {props.children}
    </ModalShell>)
}
export { DialogBox, WaitingDialog, DialogBoxTwoOption,GenericDialogBox }
