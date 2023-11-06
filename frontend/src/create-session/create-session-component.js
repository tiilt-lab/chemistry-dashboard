import { DeviceService } from '../services/device-service';
import { SessionService } from '../services/session-service';
import { KeywordService } from '../services/keyword-service';
import { TopicModelService } from "../services/topic-model-service";
import { formatDate } from '../globals';
import { DeviceModel } from '../models/device'
import { KeywordListModel } from '../models/keyword-list'
import { SessionModel } from '../models/session'
import { FolderModel } from '../models/folder';
import { TopicModelModel } from '../models/topic-model';
import { unpackTopModels } from '../myhooks/custom-hooks';
import { useEffect, useState } from 'react';
import {CreateSessionPage} from './html-pages'
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';


function CreateSessionComponent(props) {
  const BLINK_DELAY = 15000;
  //Previous state
  const location = useLocation();
  const prevState = location.state;
  const changedState = prevState != null;
  // Page Data
  const [user, setUser] = useState(null);
  const [devices, setDevices] = useState([]);
  const [keywordLists, setKeywordLists] = useState([]);
  const [topicModels, setTopicModels] = useState([]);

  //menus = Menus;
  const [currentMenu, setCurrentMenu] = useState('Settings');
  const [pageTitle, setPageTitle] = useState('Create Session');
  //forms = Forms;
  const [currentForm, setCurrentForm] = useState("");
  const [displayText, setDisplayText] = useState('');

  // Session Data
  const [sessionName, setSessionName] = useState(changedState ? prevState.sessionName : '');
  const [byod, setByod] = useState(changedState ? prevState.byod : true);
  const [doa, setDoa] = useState(changedState ? prevState.doa : true);
  const [features, setFeatures] = useState(changedState ? prevState.features : true);
  const [selectedKeywordList, setSelectedKeywordList] = useState(null);
  const [selectedTopicModel, setSelectedTopicModel] = useState(null);
  const [selectedDevices, setSelectedDevices] = useState([]);
  const [folder, setFolder] = useState(changedState ? prevState.folder : -1);
  const [folderPath, setFolderPath] = useState(changedState ? prevState.folderPath : 'Home');
  const [folders, setFolders] = useState([]);
  const [folderSelect, setFolderSelect] = useState(null)
  const [breadCrumbSelect, setBreadCrumbSelect] = useState(null)
  const navigate = useNavigate();
  const [searchParam, setSearchParam] = useSearchParams()



  useEffect(() => {
    setUser(props.userdata);
    const fetchData = new DeviceService().getDevices(false, true, false, true)
    fetchData.then(
      response => {
        if (response == 200) {
          const resp2 = response.json()
          resp2.then(
            respdevices => {
              const deviceresult = DeviceModel.fromJsonList(respdevices)
              setDevices(deviceresult);
              setSelectedDevices([]);
              for (const device of deviceresult) {
                // Add custom view fields to pods.
                device['selected'] = false;
                device['blinking'] = false;
              }
            }
          )
        }
      },
      apierror => {
        console.log("create-session-components func: useEffect 1 ", apierror)
      }
    )

    const fetchData2 = new KeywordService().getKeywordLists();
    fetchData2.then(
      response => {
        if (response.status === 200) {
          const resp2 = response.json()
          resp2.then(
            respkeyword => {
              
              const keywordLists = KeywordListModel.fromJsonList(respkeyword)
              setKeywordLists(keywordLists);
              for (const keywordList of keywordLists) {
                keywordList['keywordsText'] = keywordList.keywords.join(', ');
              }
            }
          )
        }
      },
      apierror => {
        console.log("create-session-components func: useEffect 2 ", apierror)
      }
    )

    const fetchData3 = new SessionService().getFolders()
    fetchData3.then(
      response => {
        if (response.status == 200) {
          const resp = response.json()
          resp.then(
            folderss => {
              const folderresult = FolderModel.fromJsonList(folderss)
              setFolders(folderresult);
              const paramfolder = searchParam.get('folder');
              const passedFolderId = +parseInt(paramfolder, 10);
              if (folder > 0) {
              } else if (passedFolderId > -1) {
                setFolderLocation(passedFolderId, buildBreadcrumbs(passedFolderId));
              } else {
                setFolderLocation(passedFolderId, folderPath);
              }

            })
        }
      },
      apierror => {
        console.log("create-session-components func: useEffect 3 ", apierror)
      }
    )
    
    const fetchData4 = new TopicModelService().getTopicModels();
    fetchData4.then(
      (response) => {
        if (response.status === 200) {
          const resp = response.json()
          resp.then(
            (result) => {
              const topModels = TopicModelModel.fromJsonList(result);
              setTopicModels(unpackTopModels(topModels));
            },
            (err) => { console.log('CreateSessionComponent error func : useeffect 122' ,err) })

        } else {
          console.log('CreateSessionComponent error func : useeffect 1', response)
        }
      },
      (apierror) => {
        console.log('CreateSessionComponent error func : useeffect 2', apierror)
      }
    )

    goToSettings();

    return () => {
      const blinkingDevices = devices.filter(p => p.blinking === true);
      for (const device of blinkingDevices) {
        new DeviceService().blinkPod(device.id, 'stop');//.subscribe(() => { });
      }
    }
  }, [])



  const setFolderLocation = (folderId, pathString)=>{
    setFolder(folderId);
    setFolderPath(pathString);
    closeDialog();
  }
  
  const receiveEmmitedFolder = (e) =>{
    if (e === -1) {
      setFolder(null);
    } else {
      setFolder(e);
    }
    setCurrentForm("");
  }

  const buildBreadcrumbs = (folderId)=> {
    const breadcrumbs = [];
    let folderB = folders.find(f => f.id === folderId);
    if (folderB != null) {
      breadcrumbs.unshift(folderB);
      while (folderB.parent) {
        folderB = folders.find(f => f.id === folderB.parent);
        breadcrumbs.unshift(folderB);
      }
    }
    if (breadcrumbs.length > 0) {
      const crumbnames = breadcrumbs.map(b => b.name);
      crumbnames.unshift('Home');
      return crumbnames.join('/');
    }
  }

  const createSession = ()=> {
    if (!sessionName && sessionName.trim() === '') {
      openDialog("Error", 'Invalid Session Name');
      setCurrentMenu("Settings");
    } else {
      const deviceIds = selectedDevices.map(d => d.id);
      const keywordListId = (selectedKeywordList) ? selectedKeywordList.id : null;
      const topicModelId = (selectedTopicModel) ? selectedTopicModel.id : null;
      const fetchData = new SessionService().createNewSession(sessionName, deviceIds, keywordListId, topicModelId, byod, features, doa, folder)
      fetchData.then(
        response=>{
          if(response.status === 200){
            const resp = response.json();
            resp.then(
              result =>{
                const s = SessionModel.fromJson(result)
                navigate("/sessions/" + s.id);
                //  this.router.navigate(['sessions', s.id, 'overview']);
              }
            )
          }else{
            openDialog("Error", response.json()['message']);
            goToSettings();
          }
        },
        apierror=>{
          console.log("create-session-components func: createSession 1 ", apierror)
        }
      )  
    }
  }

  // ---------------------
  // Keyword Menu
  // ---------------------

  const formatKeywordDate = (date)=> {
    return formatDate(date);
  }

  // ---------------------
  // Device Menu
  // ---------------------

  const deviceSelected = (device)=> {
    if (!selectedDevices.includes(device)) {
      selectedDevices.push(device);
    } else {
      setSelectedDevices(selectedDevices.filter(d => d !== device));
    }
  }

  const onClickSelectAll = ()=> {
    if (selectedDevices.length === devices.length) {
      setSelectedDevices([]);
    } else {
      setSelectedDevices(devices);
    }
  }

  const blinkPod = (e, device)=> {
    e.stopPropagation();
    device.blinking = !device.blinking;
    if (device.blinking) {
      const fetchData = new DeviceService().blinkPod(device.id, 'start')
      fetchData.then(
        response => {
          if(response.status === 200){
            device.timeout = setTimeout(() => {
              device.timeoutId = null;
              device.blinking = false;
            }, BLINK_DELAY);
          }
        },
        apierror =>{
          console.log("create-session-components func: blinkPad 1 ", apierror)
        }
      )
    } else {
      const fetchData2 = new DeviceService().blinkPod(device.id, 'stop')
      fetchData2.then(
        response => {
          if(response.status === 200){
            if (device.timeoutId !== null) {
              clearTimeout(device.timeoutId);
              device.timeoutId = null;
            }
          }
        },
        apierror => {
          console.log("create-session-components func: blinkPad 2 ", apierror)
        }
      )
    }
  }

  // ---------------------
  // Navigation and Dialog
  // ---------------------

  const goToKeywords = ()=> {
    setCurrentMenu("Keywords");
    setPageTitle('Create Discussion: Keywords');
  }
  
  const goToTopModels = ()=> {
    setCurrentMenu("TopModels");
    setPageTitle('Create Discussion: Topic Models');
  }

  const goToSettings = ()=> {
    setCurrentMenu("Settings");
    setPageTitle('Create Discussion: Settings');
  }

  const goToDevices = () =>{
    setCurrentMenu("Devices");
    setPageTitle('Create Discussion: Devices');
  }

  const navigateToSessions = ()=> {
    navigate('/sessions');
  }
  
  const navigateToKeywordLists = () =>{
    navigate('/keyword-lists/new-session', {state: {sessionName: sessionName, byod: byod, features: features, doa: doa, folder: folder, folderPath: folderPath}});
  }
  
  const navigateToFileUpload = () => {
    navigate('/file_upload/new-session', {state: {sessionName: sessionName, byod: byod, features: features, doa: doa, folder: folder, folderPath: folderPath}});
  }

  const openDialog = (form, text)=> {
    setCurrentForm(form);
    setDisplayText(text);
  }

  const closeDialog = ()=> {
    setCurrentForm("");
  }

  return(
    <CreateSessionPage 
    pageTitle = {pageTitle}
    navigateToSessions = {navigateToSessions}
    currentMenu = {currentMenu}
    sessionName = {sessionName}
    setSessionName = {setSessionName}
    folderPath = {folderPath}
    setByod = {setByod}
    byod = {byod}
    doa = {doa}
    setDoa = {setDoa}
    features = {features}
    setFeatures = {setFeatures}
    goToKeywords = {goToKeywords}
    keywordLists = {keywordLists}
    selectedKeywordList = {selectedKeywordList}
    setSelectedKeywordList = {setSelectedKeywordList}
    topicModels = {topicModels}
    selectedTopicModel = {selectedTopicModel}
    setSelectedTopicModel = {setSelectedTopicModel}
    formatKeywordDate = {formatKeywordDate}
    navigateToKeywordLists = {navigateToKeywordLists}
    navigateToFileUpload = {navigateToFileUpload}
    goToSettings = {goToSettings}
    goToDevices = {goToDevices}
    devices = {devices}
    deviceSelected = {deviceSelected}
    selectedDevices = {selectedDevices}
    blinkPod = {blinkPod}
    onClickSelectAll = {onClickSelectAll}
    createSession = {createSession}
    closeDialog = {closeDialog}
    setFolderLocation = {setFolderLocation}
    displayText = {displayText}
    folders = {folders}
    currentForm = {currentForm}
    openDialog = {openDialog}
    folderSelect = {folderSelect}
    setFolderSelect = {setFolderSelect}
    breadCrumbSelect = {breadCrumbSelect}
    setBreadCrumbSelect = {setBreadCrumbSelect}
    goToTopModels = {goToTopModels}
    />
  )
}

export {CreateSessionComponent}
