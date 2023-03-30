import style from './file-upload.module.css'
import { Appheader } from '../header/header-component'
import { isLargeScreen, adjDim } from '../myhooks/custom-hooks';

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
      <div className={style["intro-box"]}>
        <div className={style["padding-file"]}></div>
        <div className={style["load-text"]}>Upload files for topic modeling.</div>
      </div>
      <form onSubmit={props.onSubmit} action="#" encType="multipart/form-data">
        <div>
          <input type="file" name="fileUpload" multiple onChange={props.onFileSelect} />
        </div>
        <div>
          <button type="submit">Upload</button>
        </div>
      </form>
      <div>
        <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} style = {{width: adjDim(374) + 'px',}} onClick={props.createTopicModel}>
          Create Topic Model
        </button>
      </div>
      <div>
        <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} style = {{width: adjDim(374) + 'px',}} onClick={props.navigateToTopics}>
          See Topics
        </button>
      </div>
    </div>
   </>
  )
}

export { FileUploadPage }

