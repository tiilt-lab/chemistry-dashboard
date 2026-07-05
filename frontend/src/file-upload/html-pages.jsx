import { dlgPrimary, dlgCancel } from '../components/dialog-styles'
import { pageShell, formCard } from '../components/layout-styles'
import { Appheader } from '../header/header-component'

function FileUploadPage(props) {
  return (
    <>
      <div role="main" className="main-container">
        <Appheader
          title={"Upload Files"}
          leftText={false}
          rightText={""}
          rightEnabled={false}
          nav={props.navTopicModels}
        />
        <div className={pageShell}>
        <div className={formCard}>
        <div className="mx-auto flex w-full max-w-md grow flex-col gap-4 overflow-y-auto px-4 py-8">
          <div className="text-center">
            <div className="text-lg font-semibold text-tiilt-ink">
              Upload files for topic modeling
            </div>
            <div className="mt-1 text-sm text-tiilt-muted">
              Add one or more text files to build a topic model.
            </div>
          </div>

          <form
            onSubmit={props.onSubmit}
            action="#"
            encType="multipart/form-data"
            className="flex flex-col gap-2"
          >
            <label
              htmlFor="file-upload"
              className={dlgCancel + " flex w-full cursor-pointer items-center justify-center"}
            >
              Select file
            </label>
            <input
              id="file-upload"
              type="file"
              name="fileUpload"
              multiple
              onChange={props.onFileSelect}
              className="hidden"
            />
            {props.selectStr ? (
              <p className="text-center text-sm text-tiilt-muted">
                {props.selectStr}
              </p>
            ) : (
              <></>
            )}
            <button className={dlgPrimary + " w-full"} type="submit">
              Upload
            </button>
            {props.uploadStr ? (
              <p className="text-center text-sm text-tiilt-muted">
                {props.uploadStr}
              </p>
            ) : (
              <></>
            )}
          </form>

          <button
            className={dlgCancel + " w-full"}
            onClick={props.createTopicModel}
          >
            View topic model
          </button>

          {props.watchOutFlag == true ? (
            <p className="text-center text-sm text-tiilt-danger">
              Upload a file before proceeding.
            </p>
          ) : (
            <></>
          )}
        </div>
        </div>
        </div>
      </div>
    </>
  )
}

export { FileUploadPage }
