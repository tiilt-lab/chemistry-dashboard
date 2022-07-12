
import { Fragment } from 'react';
import style from './folder-select.module.css'
import backIcon from '../../assets/img/icon-back.svg'
import folderIcon from '../../assets/img/folder.svg'
import forwardIcon from "../../assets/img/icon-forward.svg"
import homeIcon from "../../assets/img/home.svg"

function AppFolderPage(props) {
  
  return (
    <div className={style["list-container"]}>
      {(props.visibleFolders.length == 0) ? <div> There is no valid location for this item. </div> : <></>}
      {(props.visibleFolders.length > 0) ?
        <Fragment >
          <div className={style["breadcrumb-container"]}>
            {(props.breadcrumbs.length == 1) ? <img alt="arrow" src={backIcon} className={style["breadcrumb-arrow-icon"]} onClick={props.displayFolder} /> : <></>}
            {(props.breadcrumbs.length > 1) ? <img alt="arrow" src={backIcon} className={style["breadcrumb-arrow-icon"]} onClick={() => props.displayFolder(props.breadcrumbs[props.breadcrumbs.length - 2].id)} /> : <></>}
            <span onClick={props.displayFolder} className={style["crumb-name"]}> Home</span>
            {(props.breadcrumbs.length > 1) ? <span className={style.breadcrumbs}> / . . . / </span> : <></>}
            {(props.breadcrumbs.length == 1) ? <span className={style.breadcrumbs}> / </span> : <></>}
            {(props.breadcrumbs.length > 0) ? <div className={style["crumb-name"]}>{props.breadcrumbs[props.breadcrumbs.length - 1].name}</div> : <></>}
          </div>
          <ul className={style.list}>
            {
              props.visibleFolders.map((folder,index) => (
                <li key={index} className={folder.id === props.selectedFolder ? `${style["folder-item"]} ${style["selected"]}` : style["folder-item"]} onClick={() => props.setSelectedFolderEvent(folder.id)} >
                  <img src={folderIcon} className={style["folder-icon"]} />
                  <div className={style["folder-title"]}>{folder.name}</div>
                  {(props.hasChildren(folder)) ? <img alt="forwardicon" src={forwardIcon} className={style["open-folder-icon"]} onClick={() => props.displayFolder(folder.id)} /> : <></>}
                </li>
              ))
            }

            {(props.visibleFolders[0] && (!props.visibleFolders[0].parent || props.visibleFolders[0].parent === null)) ?
              <li className={-1 == props.selectedFolder ? `${style["folder-item"]} ${style["selected"]}` : style["folder-item"]} onClick={() => props.setSelectedFolderEvent(-1)}>
                <img alt="home" src={homeIcon} className={style["add-to-home"]} />
                <div className={style["folder-title"]}> Home </div>
              </li>
              :
              <></>
            }
          </ul>
        </Fragment>
        :
        <></>
      }
    </div>
  )
}

export {AppFolderPage}

