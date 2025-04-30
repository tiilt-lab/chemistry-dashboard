import { DeviceService } from '../services/device-service';
import { DeviceModel } from '../models/device';
import { AuthService } from '../services/auth-service';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {PodComponentPage} from './html-pages'


function PodsComponent(props){
  const BLINK_DELAY = 15000;
  const user = props.userdata
  const [loading, setLoading] = useState(false);
  const [devices,setDevices] = useState([]);
  const [currentForm, setCurrentForm] = useState("");
  const [selectedDevice, setSelectedDevice] = useState();
  const [statusText,setStatusText] = useState('  ');
  const navigate = useNavigate()

  
  useEffect(()=>{
    const fetchData = new DeviceService().getDevices(false, null, null, true)
    fetchData.then(
      response => {
        if (response == 200) {
          const resp2 = response.json()
          resp2.then(
            respdevices => {
              const deviceresult = DeviceModel.fromJsonList(respdevices)
              setDevices(deviceresult);
              for (const device of deviceresult) {
                device['blinking'] = false;
              }
            }
          )
        }
      },
      apierror => {
        console.log("pods-components func: useEffect 1 ", apierror)
      }
    )

    return ()=> {
      const blinkingDevices = devices.filter(p => p.blinking === true);
      for (const device of blinkingDevices) {
        const fetchData = new DeviceService().blinkPod(device.id, 'stop')
        fetchData.then(
          response=>{},
          apierror=>{console.log("pods-components func: useEffect 2 ", apierror)}
          )
      }
    }
  },[])

  

  const blinkPod = (device)=>{
    device.blinking = !device.blinking;
    if (device.blinking) {
      const fetchData = new DeviceService().blinkPod(device.id, 'start')
      fetchData.then(
        response=>{
          if(response.status === 200){
            device.timeout = setTimeout(() => {
              device.timeoutId = null;
              device.blinking = false;
            }, BLINK_DELAY);
          }
        },
        apierror=>{console.log("pods-components func: blinkpod 2 ", apierror)}
        )
    } else {
      this.deviceService.blinkPod(device.id, 'stop').subscribe(() => {
        if (device.timeoutId !== null) {
          clearTimeout(device.timeoutId);
          device.timeoutId = null;
        }
      });
    }
  }

  const openDialog = (form, device)=>{
    setCurrentForm(form);
    setSelectedDevice(device);
  }

  const closeDialog = ()=> {
    setCurrentForm("");
    setSelectedDevice(null);
    setStatusText('');
  }

  const addDevice = (macAddress)=>{
    macAddress = macAddress.trim();
    const fetchData = new DeviceService().addDevice(macAddress)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              const dev = DeviceModel.fromJson(result);
              devices.push(dev);
            }, error => {
              alert('Failed to add pod: ' + error.json()['message']);
            }
          )
        }
      },
      apierror=>{
        console.log("pods-component func : addDevice",apierror)
      }
    ).finally(
      ()=> closeDialog()
    )
  }

  const removeDevice = ()=> {
    const device = selectedDevice;
    const fetchData = new DeviceService().removeDevice(device.id)
    fetchData.then(
      response=>{
        if(response.status === 200){
          const respJson = response.json()
          respJson.then(
            result => {
              setDevices(devices.filter(d => d !== device));
            }, error => {alert(error.json()['message']);}
          )
        }
      },
      apierror=>{
        console.log("pods-component func : removeDevice",apierror)
      }
    ).finally(
      ()=> closeDialog()
    )
  }

  const renameDevice = (newName)=> {
    if (selectedDevice.name === newName) {
      setStatusText('No change detected.');
    } else {
      const deviceId = selectedDevice.id;
      const fetchData = new DeviceService().setDevice(deviceId, {'name': newName})
      fetchData.then(
        response=>{
          if(response.status === 200){
            const respJson = response.json()
            respJson.then(
              result => {
                const dev = DeviceModel.fromJson(result);
                const deviceIndex = devices.findIndex(s => s.id === dev.id);
                if (deviceIndex > -1) {
                  devices[deviceIndex].name = newName;
                }
              }, error => {
                alert(error.json()['message']);
              }
            )
          }
        },
        apierror=>{
          console.log("pods-component func : addDevice",apierror)
        }
      ).finally(
        ()=> closeDialog()
      )
    }
  }

  const navigateToHomescreen = ()=> {
    navigate('/home');
  }

  return(
    <PodComponentPage
      navigateToHomescreen = {navigateToHomescreen}
      devices = {devices}
      blinkPod = {blinkPod}
      openDialog = {openDialog}
      user = {user}
      loading = {loading}
      currentForm = {currentForm}
      selectedDevice = {selectedDevice}
      renameDevice = {renameDevice}
      statusText = {statusText}
      closeDialog = {closeDialog}
      addDevice = {addDevice}
      
      />
  )
}
export {PodsComponent}
