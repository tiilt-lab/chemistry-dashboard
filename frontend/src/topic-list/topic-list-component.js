import {useState,useEffect} from 'react'
import { useNavigate, useLocation } from 'react-router-dom';
import { FileUploadService } from "../services/file-upload-service";
import {TopicListPage} from './html-pages'
import { TopicModelService } from "../services/topic-model-service";
import { KeywordService } from "../services/keyword-service";

function TopicListComponent(props){
  const [user, setUser] = useState();
  const navigate = useNavigate();
  const location = useLocation();
  const [showDialog, setShowDialog] = useState(false);
  const [currentDialog, setCurrentDialog] = useState("");
  const [showedInd, setShowedInd] = useState(-1);
  const [editMode, setEditMode] = useState(location.state.names === undefined);
  const [viewTitle, setViewTitle] = useState(location.state.title);
  
  //parses the inputted string for topic models into a data structure we can use
  const makeTopicListStruct = (topicStr) => {
    let topics = []
    let allTopics = topicStr.split(",");
    let allNames = editMode ? [] : location.state.names.split(",");
    const SUBTOPICLEN = 10;  //right now this is a norm
    for (let i = 0; i < allTopics.length; i++) {
    	let l = i + 1;
    	let temptopic = [];
        temptopic.tname = editMode ? ("Topic" + l) : allNames[i];
        temptopic.clicked = false;
    	let subTopics = allTopics[i].split("+");
    	if (subTopics.length != SUBTOPICLEN) {
    	  continue;
    	}
    	let kwdprobs = [];
    	let kwds = [];
    	for (let j = 0; j < SUBTOPICLEN; j++) {
    	  let numNames = subTopics[j].split("*");
    	  let num = numNames[0].trim();
    	  kwdprobs.push(parseFloat(num));
    	  let name = numNames[1].trim();
    	  name = name.slice(1, name.length - 1);
    	  kwds.push(name);
    	}
    	temptopic.kwdprobs = kwdprobs;
    	temptopic.kwds = kwds;
    	topics.push(temptopic);
    }
    return topics;
  }
  
  const [topicListStruct, setTopicListStruct] = useState(makeTopicListStruct(location.state.topics));
  const [currInput, setCurrInput] = useState("");
  const [wrongInput, setWrongInput] = useState(false);
  const [changedName, setChangedName] = useState(false);
  const [trigger, setTrigger] = useState(0);
  const [nameInput, setNameInput] = useState("");

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

  const getSelectNameList = (inQuestion) => {
    let temp = [];
    for (let i = 0; i < topicListStruct.length; i++) {
      if (topicListStruct[i].clicked) {
        temp.push(topicListStruct[i].tname);
      }
    }
    let str = temp.join(", ");
    if (str.length > 0 && inQuestion) {
      str += "?";
    }
    return str;
  }
  
  const getUnparsedSubtopics = (topicStr) => {
    let allTopics = topicStr.split(",");
    let temp = []
    for (let i = 0; i < topicListStruct.length; i++) {
      if (topicListStruct[i].clicked) {
        temp.push(allTopics[i]);
      }
    }
    return temp.join(",");
  }

  const navTopicModels = () => {
    if (location.pathname == '/topic-list/new-session') {
      navigate('/sessions/new', {state: location.state});
    } else {
      navigate('/topic-models');
    }
  }

  const isValid = () => {
    //list of topics can't be empty, and neither can the name. add
    return topicListStruct.filter(tlist => tlist.clicked) != [] && nameInput != "";
  }

  const saveNewModel = () => {
    //const topics = topicListStruct.filter(tlist => tlist.clicked).map(tlist => tlist.tname);
    //so far only for creation, but need to update it soon (aka if (keywordListID === '-1'))
    new TopicModelService().saveTopicModel(nameInput, (location.state === null) ? "Nothing here" : (getSelectNameList(false) + "\n" + getUnparsedSubtopics(location.state.topics))).then(
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
        editMode = {editMode}
        navTopicModels = {navTopicModels}
        viewTitle = {viewTitle}
      />
  )
}

export {TopicListComponent}
