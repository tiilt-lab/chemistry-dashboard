import { Appheader } from "../header/header-component"
import { Instruction } from "../utilities/utility-components"

function FileUploadPage(props) {
    return (
        <>
            <div className="main-container items-center">
                <Appheader
                    title={"Upload Files"}
                    leftText={false}
                    rightText={""}
                    rightEnabled={false}
                    nav={props.navTopicModels}
                />
                <div className="wide-section flex flex-col items-center text-center">
                    <div className="mt-8 mb-1 font-sans text-4xl/relaxed font-bold text-[#6466E3]">
                        Upload files for topic modeling.
                    </div>
                </div>
                <form
                    onSubmit={props.onSubmit}
                    action="#"
                    encType="multipart/form-data"
                    className="flex w-full flex-col items-center text-center"
                >
                    <div className="flex w-fit flex-col items-center">
                        <label htmlFor="file-upload" className="wide-button">
                            Select File
                        </label>
                        <input
                            id="file-upload"
                            className="hidden"
                            type="file"
                            name="fileUpload"
                            multiple
                            onChange={props.onFileSelect}
                        />
                    </div>
                    <Instruction instructions={props.selectStr} />
                    <button className="wide-button" type="submit">
                        Upload
                    </button>
                    <Instruction instructions={props.uploadStr} />
                </form>
                <div>
                    <button
                        className="lanky-button"
                        onClick={props.createTopicModel}
                    >
                        View Topic Model
                    </button>
                </div>
                {props.watchOutFlag == true ? (
                    <p> Upload a file before proceeding. </p>
                ) : (
                    <></>
                )}
            </div>
        </>
    )
}

export { FileUploadPage }
