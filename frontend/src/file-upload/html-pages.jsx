import style from './file-upload.module.css'
import { Appheader } from '../header/header-component'
import {isLargeScreen} from '../myhooks/custom-hooks';

function FileUploadPage(props) {
  return (
  <>
    <div className={style.container}>
      <Appheader
        title={"Upload Files"}
        leftText={false}
        rightText={""}
        rightEnabled={false}
        nav={props.navTopicModels}
      />
      <div style={{ width: "100%", maxWidth: "28rem", padding: "0 1rem", boxSizing: "border-box" }}>
        <div className={style["intro-box"]}>
          <div className={style["padding-file"]}></div>
          <div className={style["load-text"]}>Upload files for topic modeling.</div>
        </div>
        <form onSubmit={props.onSubmit} action="#" encType="multipart/form-data" style={{ width: "100%" }}>
          <div>
            <label htmlFor="file-upload" className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} style={{ width: "100%" }}>
              Select File
            </label>
            <input id="file-upload" type="file" name="fileUpload" multiple onChange={props.onFileSelect} />
          </div>
          <p className={style["instruction"]} style={{ marginTop: "1.5em" }}> {props.selectStr} </p>
          <div>
            <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} style={{ width: "100%", marginBottom: "0px" }} type="submit">Upload</button>
          </div>
          <p className={style["instruction"]}> {props.uploadStr} </p>
        </form>
        <div style={{ width: "100%" }}>
          <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} style={{ width: "100%" }} onClick={props.createTopicModel}>
            View Topic Model
          </button>
        </div>
        {(props.watchOutFlag == true) ?
          <p> Upload a file before proceeding. </p>
        :<></>}
      </div>
    </div>
   </>
  )
}

export { FileUploadPage }

