import {useState,useEffect} from 'react'
import { useNavigate } from 'react-router-dom';
import {useLocation} from 'react-router-dom';
import { FileUploadService } from "../services/file-upload-service";
import {TopicListPage} from './html-pages'
//trying this out
import { TopicModelService } from "../services/topic-model-service";
import { KeywordService } from "../services/keyword-service";

function TopicListComponent(props){
  const [user, setUser] = useState();
  const navigate = useNavigate();
  const location = useLocation();
  const [showDialog, setShowDialog] = useState(false);
  const [currentDialog, setCurrentDialog] = useState("");
  const [showedInd, setShowedInd] = useState(-1);
  const array_testing = [[0.9, [["depression", "health", "anxiety", "stress", "score","depression", "health", "anxiety", "stress", "score"], [0.1231, 0.00032, 0.3231, 0.7452, 0.9995,0.1231, 0.00032, 0.3231, 0.7452, 0.9995]]], [0.01, [["school", "homework", "deadline", "test", "gpa","depression", "health", "anxiety", "stress", "score"], [0.1231, 0.00032, 0.3231, 0.7452, 0.9995,0.1231, 0.00032, 0.3231, 0.7452, 0.9995]]], [0.015, [["fall", "spring", "winter", "summer", "seasons","depression", "health", "anxiety", "stress", "score"], [0.1231, 0.00032, 0.3231, 0.7452, 0.9995,0.1231, 0.00032, 0.3231, 0.7452, 0.9995]]], [0.02, [["jan", "feb", "march", "april", "may","depression", "health", "anxiety", "stress", "score"], [0.1231, 0.00032, 0.3231, 0.7452, 0.9995,0.1231, 0.00032, 0.3231, 0.7452, 0.9995]]], [0.35, [["skiing", "ice", "snow", "snowboard", "mountain","depression", "health", "anxiety", "stress", "score"], [0.1231, 0.00032, 0.3231, 0.7452, 0.9995,0.1231, 0.00032, 0.3231, 0.7452, 0.9995]]]];
  const makeTopicListStruct = () => {
    let topics = [];
    for (let i = 0; i < array_testing.length; i++) {
      let j = i + 1;
      let temptopic = [];
      temptopic.tname = "Topic" + j;
      temptopic.clicked = false;
      temptopic.prob = array_testing[i][0];
      temptopic.kwds = array_testing[i][1][0];
      temptopic.kwdprobs = array_testing[i][1][1];
      topics.push(temptopic);
    }
    return topics;
  }
  const [topicListStruct, setTopicListStruct] = useState(makeTopicListStruct());
  const [currInput, setCurrInput] = useState("");
  const [wrongInput, setWrongInput] = useState(false);
  const [changedName, setChangedName] = useState(false);
  const [trigger, setTrigger] = useState(0);
  const [nameInput, setNameInput] = useState("");


  const [topics, setTopics] = useState(location.state.topics)

  console.log(topics)


  useEffect(()=> {
    if (props.userdata !== undefined && Object.keys(props.userdata).length !==0) {
      setUser(props.userdata);
      console.log("Current User: ", props.userdata);
    }
  },[])

  useEffect(()=>{
    if(trigger > 0){
      console.log('reloaded page')
    }
  },[trigger])

  const navigateToFileUpload = ()=> {
    navigate('/file_upload');
  }

  const notDupeCurrInput = () => {
    for (let i = 0; i < topicListStruct.length; i++) {
      if (topicListStruct[i].tname == currInput) {
        return false;
      }
    }
    return true;
  }

  const setTopicName = () => {
    if (currInput != '' && notDupeCurrInput()) {
      //regex match
      if (/^\w+$/.test(currInput)) {
        let temparr = topicListStruct;
        temparr[showedInd].tname = currInput;
        setTopicListStruct(temparr);
        setChangedName(true);
        setWrongInput(false);
      } else {
        setChangedName(false);
        setWrongInput(true);
      }
    }
    setTrigger(trigger + 1);
  }

  const toggleDisplay = (bool, currDia, ind) => {
    setShowDialog(bool);
    setCurrentDialog(currDia);
    if (currDia == "rename") {
      setShowedInd(ind);
      setChangedName(false);
      setWrongInput(false);
      toggleClicked(ind);
    }
  }

  const stringFormat = (kwds, kwdprobs, onRight) => {
    let inner = [];
    //assumption of even number
    let startInd = onRight ? kwds.length / 2 : 0;
    for (let i = startInd; i < startInd + (kwds.length / 2); i++) {
      let temp = kwds[i] + " " + kwdprobs[i];
      inner.push(temp);
    }
    return inner.join("\n");
  }

  const toggleClicked = (count) => {
    let temp = topicListStruct;
    temp[count].clicked = !temp[count].clicked;
    setTopicListStruct(temp);
    setTrigger(trigger+1);
  }

  const getSelectNameList = () => {
    let temp = [];
    for (let i = 0; i < topicListStruct.length; i++) {
      if (topicListStruct[i].clicked) {
        temp.push(topicListStruct[i].tname);
      }
    }
    let str = temp.join(", ");
    if (str.length > 0) {
      str += "?";
    }
    return str;
  }

  const navTopicModels = () => {
    navigate('/topic-models');
  }

  const isValid = () => {
    //list of topics can't be empty, and neither can the name. add
    return topicListStruct.filter(tlist => tlist.clicked) != [] && nameInput != "";
  }

  const saveNewModel = () => {
    //const topics = topicListStruct.filter(tlist => tlist.clicked).map(tlist => tlist.tname);
    //so far only for creation, but need to update it soon (aka if (keywordListID === '-1'))
    new TopicModelService().saveTopicModel(nameInput, topics).then(
      response => {
        if (response.status === 200) {
          navTopicModels();
        } else {
          alert(response.json()['message']);
        }
      },
      apierror => {
        console.log("Keyword-items-components func: saveKeywordList 2 ", apierror)
      });
    /*
    } else {
      new KeywordService().updateKeywordList(keywordListID, keywordList.name, keywords).then(
        response => {
          if (response.status === 200) {
            navTopicModels();
          } else {
            alert(response.json()['message']);
          }
        },
        apierror => {
          console.log("Keyword-items-components func: saveKeywordList 3 ", apierror)
        });
    }*/
  }


  return(
      <TopicListPage
        navigateToFileUpload = {navigateToFileUpload}
        saveNewModel = {saveNewModel}
        showDialog = {showDialog}
        showedInd = {showedInd}
        toggleDisplay = {toggleDisplay}
        setCurrInput = {setCurrInput}
        setNameInput = {setNameInput}
        stringFormat = {stringFormat}
        setTopicName = {setTopicName}
        wrongInput = {wrongInput}
        changedName = {changedName}
        currentDialog = {currentDialog}
        topicListStruct = {topicListStruct}
        toggleClicked = {toggleClicked}
        getSelectNameList = {getSelectNameList}
      />
  )
}

export {TopicListComponent}
