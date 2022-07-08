import {useState,useEffect} from 'react'
import { useNavigate } from 'react-router-dom';
import { FileUploadService } from "../services/file-upload-service";
import {FileUploadPage} from './html-pages'

function FileUploadComponent(props){
  const [user, setUser] = useState();
  const [selectedFile, setSelectedFile] = useState(null);
  const [myFiles, setMyfile] = useState([]);
  const [topics, setTopics] = useState([]);
  const navigate = useNavigate();

  useEffect(()=> {
    if (props.userdata !== undefined && Object.keys(props.userdata).length !==0) {
      setUser(props.userdata);
      console.log("Current User: ", props.userdata);
    }
  },[])

  const onFileSelect = (event) =>{
    if (event.target.files.length > 0) {
      for (var i = 0; i < event.target.files.length; i++) {
        const file = event.target.files[i];
        // this.uploadForm.get("fileUpload").setValue(file);
        myFiles.push(file);
      }
    }
  }

  const navigateToHomescreen = ()=> {
    navigate('/home');
  }

  const createTopicModel = ()=> {
    const fetchData = new FileUploadService().getTopics()
    fetchData.then(
      response=>{
        if(response.status === 200){
          const repJson = response.json()
          repJson.then(
            (resptopics) => {
              setTopics(resptopics);
              for (const topic of resptopics) {
                console.log("Topic: ", topic);
              }
            }
          )
        }
      },
      apierror=>{
        console.log('Fileuploadcomponent error func : createTopicModel 1', apierror)
      }
    )
  }

  const onSubmit = ()=> {
    const formData = new FormData();
    for (var i = 0; i < myFiles.length; i++) {
      console.log("My files: ", myFiles[i]);
      formData.append("fileUpload[]", myFiles[i], myFiles[i].name);
    }
    console.log("formData: ", formData.get("fileUpload[]"));
    const URL = `api/v1/uploads/${props.userdata.id}`;
    const fetchData = new FileUploadService().uploadFile(URL, formData)
    fetchData.then(
      response=>{
        if(response.status === 200){
          response.json().then(
            (result) => {
              console.log(result);
            }
          )
        }
      },
      apierror =>{
        console.log('Fileuploadcomponent error func : onsubmit 1', apierror)
      }
    )
  }

  return(
      <FileUploadPage
        navigateToHomescreen = {navigateToHomescreen}
        createTopicModel = {createTopicModel}
        onFileSelect = {onFileSelect}
        onSubmit = {onSubmit}
      />
  )
}

export {FileUploadComponent}