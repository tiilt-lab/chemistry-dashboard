
import React from 'react'
import style from './section-box.module.css'

function AppSectionBoxComponent(props) {

  return (
    <>
      <div className={style.heading}>
        {props.heading}
      </div>
      <div className={style["section-container"]} style={props.maxHeight!==undefined ? { maxHeight: props.maxHeight + 'px' } : {}}>
        <React.Fragment>
          {props.children}
        </React.Fragment>
      </div>
    </>
  )
}

export {AppSectionBoxComponent}