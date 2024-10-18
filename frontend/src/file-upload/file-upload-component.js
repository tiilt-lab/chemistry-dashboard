import {useState,useEffect} from 'react'
import { useNavigate, useLocation } from 'react-router-dom';
import { FileUploadService } from "../services/file-upload-service";
import {FileUploadPage} from './html-pages'
import { TopicModelService } from "../services/topic-model-service";

function FileUploadComponent(props){
  const location = useLocation();
  const [user, setUser] = useState();
  const [selectedFile, setSelectedFile] = useState(null);
  const [myFiles, setMyfiles] = useState([]);
  const [topics, setTopics] = useState([]);
  const [fileStatus, setFileStatus] = useState({})
  const [selectStr, setSelectStr] = useState("No files selected")
  const [uploadStr, setUploadStr] = useState("No files uploaded")
  const [uploadFlag, setUploadFlag] = useState(false)
  const [watchOutFlag, setWatchOutFlag] = useState(false)
  const navigate = useNavigate();


  useEffect(()=> {
    if (props.userdata !== undefined && Object.keys(props.userdata).length !==0) {
      setUser(props.userdata);
      console.log("Current User: ", props.userdata);
    }
  },[])

  const onFileSelect = (event) =>{
    const files = []
    if (event.target.files.length > 0) {
      for (var i = 0; i < event.target.files.length; i++) {
        const file = event.target.files[i];
        // this.uploadForm.get("fileUpload").setValue(file);
        // handling duplicates
        if (!myFiles.includes(file)) {
          files.push(file);
          changeFileStatus(file['name'], false);
        }
      }
      //keep all files together
      setMyfiles(myFiles.concat(files))
      updateFileStatusText();
    }
  }

  const navTopicModels = ()=> {
    if (location.pathname == '/file_upload/new-session') {
      navigate('/sessions/new', {state: location.state});
    } else if ((location.state != null) && (location.state.fromManagedList)) {
      navigate('/keyword-lists');
    } else {
      navigate('/topic-models');
    }
  }

  const createTopicModel = ()=> {
    // you have to upload something in order to proceed
    if (uploadFlag == false){
      setWatchOutFlag(true);
      return
    }
    const fetchData = new TopicModelService().getTopicModel()
    fetchData.then(
      response=>{
        if(response.status === 200){
          const repJson = response.json()
          repJson.then(
            (topics) => {
              var topicString = ""
              setTopics(topics);
              for (const topic of topics) {
                console.log("Topic: ", topic);
                topicString += topic + ",";
              }
              if (location.pathname == '/file_upload/new-session') {
                const combinedState = {
                  ...location.state,
                  topics: topicString,
                };
                navigate('/topic-list/new-session', { state: combinedState });
              } else {
                navigate('/topic-list', {state: {topics:topicString}});
              }
            }
          )
        }
      },
      apierror=>{
        console.log('Fileuploadcomponent error func : createTopicModel 1', apierror)
        //should put some sort of alert here for the user
      }
    )
  }

  const onSubmit = (e)=> {
    e.preventDefault();
    const formData = new FormData();
    // upload only unuploaded things 
    let filesToUpload = myFiles.filter(file => !fileStatus[file['name']])
    for (var i = 0; i < filesToUpload.length; i++) {
      console.log("My files: ", filesToUpload[i]);
      formData.append("fileUpload[]", filesToUpload[i]);
      changeFileStatus(filesToUpload[i]['name'], true);
    }
    console.log("formData: ", formData.get("fileUpload[]"));
    const URL = `api/v1/uploads/${props.userdata.id}`;
    new FileUploadService().uploadFile(URL, formData).then(
      response=>{
        if(response.status === 200){
          response.json().then(
            (result) => {
              console.log(result);
              updateFileStatusText();
              setUploadFlag(true);
              setWatchOutFlag(false);
            }
          )
        }
      },
      apierror =>{
        console.log('Fileuploadcomponent error func : onsubmit 1', apierror)
      }
    )
  }
  
  // code for making sure that the user can see the names of the uploaded files
  const changeFileStatus = (fileName, status) => {
    // status is a bool determining if it's been uploaded or not
    let fs = fileStatus;
    fs[fileName] = status;
    setFileStatus(fs);
  }
  
  const updateFileStatusText = () => {
    let selectedFiles = Object.keys(fileStatus).filter(key => fileStatus[key] === false);
    let uploadedFiles = Object.keys(fileStatus).filter(key => fileStatus[key] === true);
    // update selected user feedback
    if (selectedFiles.length == 0) {
      setSelectStr("No files selected");
    } else {
      setSelectStr("Selected: " + selectedFiles.join(', '));
    }
    // update uploaded user feedback
    if (uploadedFiles.length == 0) {
      setUploadStr("No files uploaded");
    } else {
      setUploadStr("Uploaded: " + uploadedFiles.join(', '));
    }
  }

  return(
      <FileUploadPage
        navTopicModels = {navTopicModels}
        createTopicModel = {createTopicModel}
        onFileSelect = {onFileSelect}
        onSubmit = {onSubmit}
        selectStr = {selectStr}
        uploadStr = {uploadStr}
        watchOutFlag = {watchOutFlag}
      />
  )
}

export {FileUploadComponent}
