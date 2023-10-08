import {useState,useEffect} from 'react'
import { useNavigate } from 'react-router-dom';
import { FileUploadService } from "../services/file-upload-service";
import {FileUploadPage} from './html-pages'
import { TopicModelService } from "../services/topic-model-service";

function FileUploadComponent(props){
  const [user, setUser] = useState();
  const [selectedFile, setSelectedFile] = useState(null);
  const [myFiles, setMyfiles] = useState([]);
  const [topics, setTopics] = useState([]);
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
        files.push(file);
      }
      setMyfiles(files)
    }
  }

  const navTopicModels = ()=> {
    navigate('/topic-models');
  }

  const createTopicModel = ()=> {
    const fetchData = new TopicModelService().getTopicModel()
    fetchData.then(
      response=>{
        if(response.status === 200){
          const repJson = response.json()
          repJson.then(
            (topics) => {
              var topicString = ""
              setTopics(topics);
              console.log("ALL TOPICS")
              console.log(topics)
              for (const topic of topics) {
                console.log("Topic: ", topic);
                topicString += topic + ",";
              }
              navigate('/topic-list', {state: {topics:topicString}});
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
    for (var i = 0; i < myFiles.length; i++) {
      console.log("My files: ", myFiles[i]);
      formData.append("fileUpload[]", myFiles[i]);
    }
    console.log("formData: ", formData.get("fileUpload[]"));
    const URL = `api/v1/uploads/${props.userdata.id}`;
    new FileUploadService().uploadFile(URL, formData).then(
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
        navTopicModels = {navTopicModels}
        createTopicModel = {createTopicModel}
        onFileSelect = {onFileSelect}
        onSubmit = {onSubmit}
      />
  )
}

export {FileUploadComponent}
