import React, { useState } from 'react';
import style from './section-box.module.css';

function AppSectionBoxComponent(props) {
  const [isExpanded, setIsExpanded] = useState(true);

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
    console.log("Toggled! isExpanded:", !isExpanded);  // Debugging output
  };

  return (
    <>
      <div className={style.heading} onClick={toggleExpand} style={{ cursor: 'pointer' }}>
        {props.heading}
      </div>
      {isExpanded && (
        <div className={style["section-container"]} style={props.maxHeight !== undefined ? { maxHeight: props.maxHeight + 'px' } : {}}>
          <React.Fragment>
            {props.children}
          </React.Fragment>
        </div>
      )}
    </>
  );
}

export { AppSectionBoxComponent };
