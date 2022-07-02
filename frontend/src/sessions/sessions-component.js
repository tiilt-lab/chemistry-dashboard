import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { SessionService } from '../services/session-service';
import { SessionModel } from '../models/session'
import { FolderModel } from '../models/folder'
import { DiscussionSessionPage } from './html-pages';


function SessionsComponent(props) {

  //forms = Forms;
  const [currentForm, setCurrentForm] = useState("");
  const [sessions, setSessions] = useState([]);
  const [folders, setFolders] = useState([]);
  const [displayedFolders, setDisplayedFolders] = useState([]);
  const [displayedSessions, setDisplayedSessions] = useState([]);
  const [selectableFolders, setSelectableFolders] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showAlert, setShowAlert] = useState(false);
  const [alertMessage, setAlertMessage] = useState("");
  const [breadcrumbs, setBreadCrumbs] = useState([]);
  const [currentFolder, setCurrentFolder] = useState("");
  const [folderPath, setFolderPath] = useState("");
  const [folderSelect, setFolderSelect] = useState(null)
  const navigate = useNavigate();
  const [searchParam, setSearchParam] = useSearchParams();


  useEffect(() => {
    const fetchData = new SessionService().getSessions();
    fetchData.then(response => {
      if (response.status === 200) {
        const resp = response.json()
        resp.then(
          session => {
            const sessresult = SessionModel.fromJsonList(session)
            setSessions(sessresult);
            const fetchData2 = new SessionService().getFolders();
            fetchData2.then(
              response => {
                //console.log(response,'response')
                if (response.status === 200) {
                  const resp2 = response.json()
                  resp2.then(
                    folders => {
                      //console.log(folders,'folders')
                      const folderresult = FolderModel.fromJsonList(folders)
                      //console.log(folderresult,'folderresult')
                      setFolders(folderresult)
                      // const folder = searchParam.get('folder');
                      // displayFolder(parseInt(folder, 10));
                    }
                  )
                }
              },
              apierror2 => {
                console.log("sessions-components func: useEffect 4 ", apierror2)
              });
          },
          error => {
            console.log("sessions-components func: useEffect 1 ", error)
          }
        )
      }
    },
      apierror => {
        console.log("sessions-components func: useEffect 2 ", apierror)
      });
    setIsLoading(false);
  }, [currentForm])

  useEffect(() => {
    const folder = searchParam.get('folder');
    displayFolder(parseInt(folder, 10));
  },[folders])

  const navigateToHomescreen = () => {
    navigate('/home',{replace:true});
  }

  const newRecording = () => {
    if (currentFolder !== "") {
      navigate('/sessions/new?folder='+currentFolder, {replace:true})
    } else {
      navigate('/sessions/new', {replace:true})
    }
    //navigate('/sessions/new'+"?folder=", { queryParams: { folder: this.currentFolder } });
  }

  const goToSession = (session) => {
    navigate('/sessions/' + session.id);
  }

  // ----------
  // Folders
  // ----------

  const displayFolder = (folderId) => {
    if (!folderId) {
      setDisplayedFolders(folders.filter(f => f.parent == null));
      setDisplayedSessions(sessions.filter(s => s.folder == null));
      setBreadCrumbs([]);
      setCurrentFolder("");
      navigate('/sessions')
      // const url = '/sessions';
      // this.location.replaceState(url);
    } else {
      setDisplayedFolders(folders.filter(x => x.parent === folderId));
      setDisplayedSessions(sessions.filter(s => s.folder === folderId));
      setCurrentFolder(folderId);
      buildBreadcrumbs(folderId);
      setSearchParam({ folder: folderId }, { replace: true })
      // const url = '/sessions/?folder=' + folderId;
      // this.location.replaceState(url);
    }
  }

  const buildBreadcrumbs = (folderId) => {
    let folder = folders.find(f => f.id === folderId);
    const bread = []
    if (folder != null) {
      bread.unshift(folder);
      while (folder.parent) {
        folder = folders.find(f => f.id === folder.parent);
        bread.unshift(folder);
      }
    }
    setBreadCrumbs(bread);
  }

  const buildBreadcrumbString = () => {
    if (breadcrumbs.length > 0) {
      const crumbnames = breadcrumbs.map(b => b.name);
      crumbnames.unshift('Home');
      setFolderPath(crumbnames.join('/'));
    }
  }

  const goBackToPrevious = () => {
    if (breadcrumbs.length > 1) {
      displayFolder(breadcrumbs[breadcrumbs.length - 2].id);
    } else {
      displayFolder();
    }
  }

  const addFolder = (newName, locationId) => {
    if (!newName) {
      setShowAlert(true);
      setAlertMessage('Please enter folder name');
      closeDialog();
    } else {
      const fetchData = new SessionService().addFolder(newName, locationId)
      fetchData.then(
        response => {
          if (response.status === 200) {
            const folder = FolderModel.fromJson(response.json());
            folders.push(folder);
            if (locationId) {
              displayFolder(folder.parent);
            } else {
              displayFolder();
            }
          } else {
            setShowAlert(true);
            setAlertMessage(response.json()['message']);
          }
        },
        apierror => {
          console.log("sessions-components func: addFolder 1 ", apierror)
        }
      ).finally(() => {
        closeDialog();
      })
    }
  }

  const changeFolderName = (newName) => {
    setCurrentForm("Loading");
    const folderId = selectedFolder.id;
    const fetchData = new SessionService().updateFolder(folderId, null, newName)
    fetchData.then(
      response => {
        if (response.status === 200) {
          const folder = FolderModel.fromJson(response.json());
          const folderIndex = folders.findIndex(s => s.id === folder.id);
          folders[folderIndex] = folder;
          displayFolder(folder.parent);
        } else {
          setShowAlert(true);
          setAlertMessage(response.json()['message']);
        }
      },
      apierror => {
        console.log("sessions-components func: changefoldername 1 ", apierror)
      }
    ).finally(() => {
      closeDialog();
    })
  }

  const moveFolder = (newFolderId) => {
    const fetchData = new SessionService().updateFolder(selectedFolder.id, newFolderId, null)
    fetchData.then(
      response => {
        if (response.status === 200) {
          const updatedFolder = FolderModel.fromJson(response.json());
          const index = folders.findIndex(f => f.id === updatedFolder.id);
          folders[index] = updatedFolder;
          displayFolder(updatedFolder.parent);
        } else {
          setShowAlert(true);
          setAlertMessage(response.json()['message']);
        }
      },
      apierror => {
        console.log("sessions-components func: movefolder 1 ", apierror)
      }
    ).finally(() => {
      closeDialog();
    })
  }

  const deleteFolder = () => {
    setCurrentForm("Loading");
    const folderId = selectedFolder.id;
    const parentId = selectedFolder.parent;
    const fetchData = new SessionService().deleteFolder(folderId)
    fetchData.then(
      response => {
        if (response.status === 200) {
          //const updatedFolder = FolderModel.fromJson(response.json());
          const foldersToRemove = [folderId];
          const children = folders.filter(f => f.parent === folderId);
          while (children.length > 0) {
            const child = children.pop();
            foldersToRemove.push(child.id);
            folders.filter(f => f.parent === child.id).forEach(f => children.push(f));
          }
          setFolders(folders.filter(f => foldersToRemove.indexOf(f.id) === -1));
          setSessions(sessions.filter(s => foldersToRemove.indexOf(s.folder) === -1));
          if (parentId) {
            displayFolder(parentId);
          } else {
            displayFolder();
          }
        } else {
          setShowAlert(true);
          setAlertMessage(response.json()['message']);
        }
      },
      apierror => {
        console.log("sessions-components func: movefolder 1 ", apierror)
      }
    ).finally(() => {
      closeDialog();
    })
  }

  // ----------
  // Sessions
  // ----------

  const endSession = (session) => {
    setCurrentForm("Loading");
    const sessionId = session.id;
    setSelectedSession(null);
    const fetchData = new SessionService().endSession(sessionId)
    fetchData.then(
      response => {
        if (response.status === 200) {
          const endedSession = SessionModel.fromJson(response.json());
          const sessionIndex = sessions.findIndex(s => s.id === endedSession.id);
          sessions[sessionIndex] = endedSession;
          displayFolder(endedSession.folder);
        } else {
          setShowAlert(true);
          setAlertMessage(response.json()['message']);
        }
      },
      apierror => {
        console.log("sessions-components func: endsession 1 ", apierror)
      }
    ).finally(() => {
      closeDialog();
    })
  }

  const changeSessionName = (newName) => {
    setCurrentForm("Loading");
    const sessionId = selectedSession.id;
    const fetchData = new SessionService().updateSession(sessionId, newName)
    fetchData.then(
      response => {
        if (response.status === 200) {
          const session = SessionModel.fromJson(response.json())
          const sessionIndex = sessions.findIndex(s => s.id === session.id);
          if (sessionIndex > -1) {
            sessions[sessionIndex] = session;
            displayFolder(session.folder);

          } else {
            setShowAlert(true);
            setAlertMessage(response.json()['message']);
          }
        }
      },
      apierror => {
        console.log("sessions-components func:changesesion 1 ", apierror)
      });
    closeDialog();
  }

  const moveSession = (newParentId) => {
    const fetchData = new SessionService().updateSessionFolder(selectedSession.id, newParentId)
    fetchData.then(
      response => {
        if (response.status === 200) {
          const updatedSession = SessionModel.fromJson(response.json())
          const index = sessions.findIndex(s => s.id === updatedSession.id);
          sessions[index] = updatedSession;
          displayFolder(updatedSession.folder);
        } else {
          setShowAlert(true);
          setAlertMessage(response.json()['message']);
        }

      },
      apierror => {
        console.log("sessions-components func:movesession 1 ", apierror)
      }
    ).finally(() => {
      closeDialog();
    })
  }

  const deleteSession = () => {
    setCurrentForm("Loading");
    const sessionId = selectedSession.id;
    const fetchData = new SessionService().deleteSession(sessionId)
    fetchData.then(
      response => {
        if (response.status === 200) {
          const parent = folders.find(f => f.id === selectedSession.folder);
          setSessions(sessions.filter(s => s.id !== sessionId));
        } else {
          setShowAlert(true);
          setAlertMessage(response.json()['message']);
        }
      },
      apierror => {
        console.log("sessions-components func deletesession 1 ", apierror)
      }
    ).finally(() => {
      closeDialog();
    })
  }

  // ----------
  // Dialogs
  // ----------

  const openSessionDialog = (newForm, selectedSession) => {
    setCurrentForm(newForm);
    setSelectedSession(selectedSession);
    if (currentForm === "MoveSession") {
      setSelectableFolders(folders);
    }
  }

  const openFolderDialog = (newForm, selectedFolder) => {
    setCurrentForm(newForm);
    setSelectedFolder(selectedFolder);
    if (newForm === "MoveFolder") {
      setSelectableFolders(folders.filter(f => f.parent !== selectedFolder.id && f.id !== selectedFolder.id));
    }
  }

  const closeDialog = () => {
    setCurrentForm("");
    setSelectedSession(null);
    setSelectedFolder(null);
    setFolderSelect(null)
  }

  const closeAlert = () => {
    setShowAlert(false);
  }

  return (
    <DiscussionSessionPage
      openFolderDialog={openFolderDialog}
      navigateToHomescreen={navigateToHomescreen}
      isLoading={isLoading}
      sessions={sessions}
      folders={folders}
      breadcrumbs={breadcrumbs}
      goBackToPrevious={goBackToPrevious}
      displayFolder={displayFolder}
      displayedFolders={displayedFolders}
      displayedSessions={displayedSessions}
      goToSession={goToSession}
      openSessionDialog={openSessionDialog}
      alertMessage={alertMessage}
      showAlert={showAlert}
      closeAlert={closeAlert}
      currentForm={currentForm}
      closeDialog={closeDialog}
      selectedSession={selectedSession}
      changeSessionName={changeSessionName}
      changeFolderName={changeFolderName}
      deleteSession={deleteSession}
      deleteFolder={deleteFolder}
      addFolder={addFolder}
      newRecording={newRecording}
      moveFolder={moveFolder}
      moveSession={moveSession}
      selectedFolder = {selectedFolder}
      selectableFolders = {selectableFolders}
      folderSelect = {folderSelect} 
      setFolderSelect = {setFolderSelect}
    />
  )
}

export { SessionsComponent }