import { AuthService } from '../services/auth-service';
import { ApiService } from '../services/api-service';
import { DeviceService } from '../services/device-service';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { StudentModel } from '../models/student';
import { RaterModel } from '../models/rater';
import { DeviceModel } from '../models/device'
import { SettingComponentPage } from './html-pages'

function SettingsComponent(props) {

  const user = props.userdata // The currently logged in user.
  const [students, setStudents] = useState()
  const [raters, setRaters] = useState()
  const [studentToDelete, setStudentToDelete] = useState();
  const [raterToDelete, setRaterToDelete] = useState();
  const [devices, setDevices] = useState();
  const [currentForm, setCurrentForm] = useState("");
  const [statusTitle, setStatusTitle] = useState('');
  const [status, setStatus] = useState('');
  const navigate = useNavigate()



  const navigateToHomescreen = () => {
    navigate('/home');
  }

  const signOut = () => {
    new AuthService().logout().then(
      () => navigate('/login'),
      () => navigate('/login'),
    )
  }

  const openDialog = (newForm, loadUsers = false, loadDevices = false) => {
    if (loadUsers && ["ViewStudentProfile", "DeleteStudentProfile"].includes(newForm)) {
      setCurrentForm("Loading");
      const fetchData = new AuthService().getStudentProfiles()
      fetchData.then(
        response => {
          if (response.status === 200) {
            const respJson = response.json()
            respJson.then(
              studentJson => {
                const stdsObj = StudentModel.fromJsonList(studentJson)
                setStudents(stdsObj);
                setCurrentForm(newForm);
              }
            )
          }
        },
        apierror => {
          console.log("settingcomponent func : opendialog ", apierror)
        }
      )
    } else if (loadUsers && ["ViewRaters", "DeleteRater"].includes(newForm)) {
      setCurrentForm("Loading");
      const fetchData = new AuthService().getRaters()
      fetchData.then(
        response => {
          if (response.status === 200) {
            const respJson = response.json()
            respJson.then(
              raterJson => {
                const raterObj = RaterModel.fromJsonList(raterJson)
                setRaters(raterObj);
                setCurrentForm(newForm);
              }
            )
          }
        },
        apierror => {
          console.log("settingcomponent func : opendialog ", apierror)
        }
      )
    } else if (loadDevices) {
      setCurrentForm("Loading");
      const fetchData = new DeviceService().getDevices(false, true, null, true)
      fetchData.then(
        response => {
          if (response.status === 200) {
            const respJson = response.json()
            respJson.then(
              deviceJson => {
                const deviceObj = DeviceModel.fromJsonList(deviceJson)
                setDevices(deviceObj);
                setCurrentForm(newForm);
              }
            )
          }
        },
        apierror => {
          console.log("settingcomponent func : opendialog 2", apierror)
        }
      )
    } else if (!loadDevices && newForm === "SyncStudentProfile") {
      setCurrentForm("Loading")
      syncStudentProfile()
    } else {
      setCurrentForm(newForm);
    }
  }

  const addStudentProfile = async (firstname, lastname, username) => {
    firstname = firstname.trim();
    lastname = lastname.trim();
    username = username.trim();
    if (!firstname || !lastname || !username) {
      setStatus("Please fill in first name, last name, and username.");
      return;
    }
    if (username.length < 5 || username.length > 10) {
      setStatus("Username must be 5-10 characters.");
      return;
    }
    setCurrentForm("Loading");
    try {
      const response = await new ApiService().httpRequestCall(
        "api/v1/student/addstudent", "POST",
        { firstname: firstname, lastname: lastname, username: username });
      if (response.status === 200) {
        setStatusTitle("Student Added");
        setStatus(username + " has been created.");
      } else {
        let message = "Could not create the student profile.";
        try {
          const err = await response.json();
          if (err["message"]) message = err["message"];
        } catch { /* non-JSON error body */ }
        setStatusTitle("Failed to Add Student");
        setStatus(message);
      }
    } catch {
      setStatusTitle("Failed to Add Student");
      setStatus("The server could not be reached.");
    }
    setCurrentForm("Status");
  }

  const syncStudentProfile = async () => {
    const response = await new AuthService().syncStudentProfile()
    if (response.status === 200) {
      setStatusTitle('Success');
      setStatus('Student Profile Syncing Completed.');
      setCurrentForm("Status")
    } else if (response.status === 400) {
      setStatusTitle('Error');
      setStatus('Student Profile Syncing Failed.');
      setCurrentForm("Status")
    }
  }
  
  const closeDialog = () => {
    setStatus("");
    setCurrentForm("");
  }

  const changeEmail = (password, newEmail) => {
    const fetchData = new AuthService().changeEmail(password, newEmail)
    fetchData.then(
      response => {
        if (response.status === 200) {
          setStatusTitle('Email Changed');
          setStatus('Your email has been changed successfully. Use it the next time you sign in.');
        } else if (response.status === 400) {
          response.json().then(error => setStatus(error['message']))
        }
      },
      apierror => {
        console.log("settingcomponent func : changeemail", apierror)
      }
    )
  }

  const changePassword = (password, newPassword, confirmPassword) => {
    const fetchData = new AuthService().changePassword(password, newPassword, confirmPassword)
    fetchData.then(
      response => {
        if (response.status === 200) {
          setStatusTitle('Password Changed');
          setStatus('Your password has been changed successfully.');
        } else if (response.status === 400) {
          const errResp = response.json()
          errResp.then(
            error => {
              setStatus(error['message']);
            }
          )

        }
      },
      apierror => {
        console.log("settingcomponent func : changepassword", apierror)
      }
    ).finally(
      () => { console.log('i came here'); setCurrentForm("Status") }
    )
  }

  const createRater = (sessionid, sessiondeviceid, speakerid, speakertag, raterid, type, evaluationcategory) => {
    const fetchData = new AuthService().createRater(sessionid, sessiondeviceid, speakerid, speakertag, raterid, type, evaluationcategory)
    fetchData.then(
      response => {
        if (response.status === 200) {
          const respJson = response.json()
          respJson.then(
            result => {
              setStatusTitle('Rater Created');
              setStatus('Rater Created Successfully');
            }, error => {
              setStatusTitle('Failed to Create Rater')
              setStatus(error.json()['message']);
            }
          )
        }
      },
      apierror => {
        console.log("settingcomponent func : createRater", apierror)
      }
    ).finally(
      () => setCurrentForm("Status")
    )
  }

  const confirmDeleteStudent = (studentId) => {
    studentId = +studentId;
    setStudentToDelete(students.find(s => s.id === studentId));
    setCurrentForm("ConfirmDeleteStudent");
  }

  const confirmDeleteRater = (id) => {
    id = +id;
    setRaterToDelete(raters.find(r => r.id === id));
    setCurrentForm("ConfirmDeleteRater");
  }

  const deleteSelectedStudent = () => {
    const fetchData = new AuthService().deleteStudent(studentToDelete.id)
    fetchData.then(
      response => {
        if (response.status === 200) {
          const respJson = response.json()
          respJson.then(
            result => {
              setStatusTitle('Student Deleted');
              setStatus(studentToDelete.username + ' has been deleted.');
            }, error => {
              setStatusTitle('Failed to Delete Student')
              setStatus(studentToDelete.username + ' could not be deleted.');
            }
          )
        }
      },
      apierror => {
        console.log("settingcomponent func : confirmDeleteUser", apierror)
      }
    ).finally(
      () => setCurrentForm("Status")
    )
  }

  const deleteSelectedRater = () => {
    const fetchData = new AuthService().deleteRater(raterToDelete.id)
    fetchData.then(
      response => {
        if (response.status === 200) {
          const respJson = response.json()
          respJson.then(
            result => {
              setStatusTitle('Rater Deleted');
              setStatus(raterToDelete.raterid + ' has been deleted.');
            }, error => {
              setStatusTitle('Failed to Delete Rater')
              setStatus(raterToDelete.raterid + ' could not be deleted.');
            }
          )
        }
      },
      apierror => {
        console.log("settingcomponent func : confirmDeleteUser", apierror)
      }
    ).finally(
      () => setCurrentForm("Status")
    )
  }

  const downloadServerLogs = async (type) => {
    setCurrentForm("Loading");
    try {
      const fetchData = await new AuthService().getServerLogs(type)
      if (fetchData !== null && fetchData.status === 200) {
        const respJson = await fetchData.json()
        if (respJson !== null) {
          const dataUrl = respJson["data"];
          const res = await fetch(dataUrl)
          const blob = await res.blob()
          const blobUrl = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = blobUrl;
          link.download = type + "_logs.txt";
          link.click();
          setStatusTitle('Logs Downloaded');
          setStatus('The logs have been downloaded successfully.');
          setCurrentForm("Status")
        } else {
          setStatusTitle('Logs Download Failed')
          setStatus('The logs failed to download.  Please try again later.');
          setCurrentForm("Status")
        }
      } else {
        setCurrentForm("Status")
        console.log("settingcomponent func : downloadServerLogs")
      }
    } catch (e) {
      setCurrentForm("Status")
      console.log(e, 'downloadserverlogs')
    }

  }

  const downloadDeviceLogs = async (deviceId) => {
    deviceId = +deviceId;
    setCurrentForm('Loading');
    try {
      const fetchData = await new AuthService().getDeviceLogs(deviceId)
      if (fetchData !== null && fetchData.status === 200) {
        const respJson = await fetchData.json()
        if (respJson !== null) {
          const dataUrl = respJson["data"];
          const res = await fetch(dataUrl)
          const blob = await res.blob()
          const blobUrl = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = blobUrl;
          link.download = "pod_" + deviceId + "_logs.txt";
          link.click();
          setStatusTitle('Logs Downloaded');
          setStatus('The logs have been downloaded successfully.');
          setCurrentForm("Status")
        } else {
          setStatusTitle('Logs Download Failed')
          setStatus('The logs failed to download.  Please try again later.');
          setCurrentForm("Status")
        }
      } else {
        const respJson = await fetchData.json()
        setStatus(respJson['message']);
        setStatusTitle('Logs Download Failed')
        setCurrentForm("Status")
        console.log("settingcomponent func : downloadDeviceLogs")
      }
    } catch (e) {
      setCurrentForm("Status")
      console.log(e, 'downloadserverlogs')
    }

  }

  const deleteServerLogs = async (type) => {
    setCurrentForm('Loading');
    const fetchData = await new AuthService().deleteServerLogs(type)
    if (fetchData != null && fetchData.status === 200) {
      setStatusTitle('Logs Deleted');
      setStatus('The logs have been deleted successfully.');
      setCurrentForm("Status")
    } else {
      const respJson = await fetchData.json()
      setStatus(respJson['message']);
      setStatusTitle('Logs Deleted');
      setCurrentForm("Status")
      console.log("settingcomponent func : deleteServerLogs")
    }
  }

  const deleteDeviceLogs = async (deviceId) => {
    deviceId = +deviceId;
    setCurrentForm('Loading');
    const fetchData = await new AuthService().deleteDeviceLogs(deviceId)
    if (fetchData != null && fetchData.status === 200) {
      setStatusTitle('Logs Deleted');
      setStatus('The logs have been deleted successfully.');
      setCurrentForm("Status")
    } else {
      const respJson = await fetchData.json()
      setStatus(respJson['message']);
      setStatusTitle('Logs Deleted');
      setCurrentForm("Status")
      console.log("settingcomponent func : delete devicelog")
    }

  }

  return (
    <SettingComponentPage
      navigateToHomescreen={navigateToHomescreen}
      signOut={signOut}
      openDialog={openDialog}
      addStudentProfile={addStudentProfile}
      user={user}
      currentForm={currentForm}
      status={status}
      statusTitle={statusTitle}
      changePassword={changePassword}
      changeEmail={changeEmail}
      students={students}
      raters={raters}
      devices={devices}
      confirmDeleteStudent={confirmDeleteStudent}
      confirmDeleteRater={confirmDeleteRater}
      studentToDelete={studentToDelete}
      raterToDelete={raterToDelete}
      deleteSelectedStudent={deleteSelectedStudent}
      deleteSelectedRater={deleteSelectedRater}
      deleteDeviceLogs={deleteDeviceLogs}
      deleteServerLogs={deleteServerLogs}
      downloadDeviceLogs={downloadDeviceLogs}
      downloadServerLogs={downloadServerLogs}
      createRater={createRater}
      closeDialog={closeDialog}
    />

  )
}

export { SettingsComponent }