import {Component, OnInit, OnDestroy} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { DeviceService } from '../services/device.service';
import { AuthService } from '../services/auth.service';
import 'rxjs/add/operator/finally';

const BLINK_DELAY = 15000;

enum Forms {
  Remove = 1,
  Add,
  Rename
}

@Component({
  selector: 'app-pods',
  templateUrl: './pods.component.html',
  styleUrls: ['./pods.component.scss']
})
export class PodsComponent implements OnInit, OnDestroy {
  loading = false;
  devices: any[];
  currentForm: Forms;
  forms = Forms;
  selectedDevice: any;
  user: any;
  statusText = '  ';

  constructor(private route: ActivatedRoute,
              private router: Router,
              private deviceService: DeviceService,
              private authService: AuthService) { }

  ngOnInit() {
    this.user = this.authService.user;
    this.deviceService.getDevices(false, null, null, true).subscribe(devices => {
      this.devices = devices;
      for (const device of this.devices) {
        device['blinking'] = false;
      }
    });
  }

  ngOnDestroy() {
    const blinkingDevices = this.devices.filter(p => p.blinking === true);
    for (const device of blinkingDevices) {
      this.deviceService.blinkPod(device.id, 'stop').subscribe(() => { });
    }
  }

  blinkPod(device: any) {
    device.blinking = !device.blinking;
    if (device.blinking) {
      this.deviceService.blinkPod(device.id, 'start').subscribe(() => {
        device.timeout = setTimeout(() => {
          device.timeoutId = null;
          device.blinking = false;
        }, BLINK_DELAY);
      });
    } else {
      this.deviceService.blinkPod(device.id, 'stop').subscribe(() => {
        if (device.timeoutId !== null) {
          clearTimeout(device.timeoutId);
          device.timeoutId = null;
        }
      });
    }
  }

  openDialog(form: any, device: any) {
    this.currentForm = form;
    this.selectedDevice = device;
  }

  closeDialog() {
    this.currentForm = null;
    this.selectedDevice = null;
    this.statusText = '';
  }

  addDevice(macAddress) {
    macAddress = macAddress.trim();
    this.deviceService.addDevice(macAddress).finally(() => {
      this.closeDialog();
    }).subscribe(device => {
      this.devices.push(device);
    }, error => {
      alert('Failed to add pod: ' + error.json()['message']);
    });
  }

  removeDevice() {
    const device = this.selectedDevice;
    this.deviceService.removeDevice(device.id).finally(() => {
      this.closeDialog();
    }).subscribe(result => {
      this.devices = this.devices.filter(d => d !== device);
    }, error => {
      alert(error.json()['message']);
    });
  }

  renameDevice(newName) {
    if (this.selectedDevice.name === newName) {
      this.statusText = 'No change detected.';
    } else {
      const deviceId = this.selectedDevice.id;
      this.deviceService.setDevice(deviceId, {'name': newName}).finally(() => {
        this.closeDialog();
      }).subscribe(device => {
        const deviceIndex = this.devices.findIndex(s => s.id === device.id);
        if (deviceIndex > -1) {
          this.devices[deviceIndex].name = newName;
        }
      }, error => {
        alert(error.json()['message']);
      });
    }
  }

  navigateToHomescreen() {
    this.router.navigate(['homescreen']);
  }
}
