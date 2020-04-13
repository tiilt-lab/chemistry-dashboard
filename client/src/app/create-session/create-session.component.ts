import { Component, OnInit, OnDestroy } from '@angular/core';
import { DeviceService } from '../services/device.service';
import { AuthService } from '../services/auth.service';
import { SessionService } from '../services/session.service';
import { KeywordService } from '../services/keyword.service';
import { Router, ActivatedRoute } from '@angular/router';
import { formatDate } from '../globals';
import { FolderModel } from '../models/folder';

enum Menus {
  Settings = 1,
  Keywords,
  Devices
}

enum Forms {
  Error = 1,
  Folder = 2
}

const BLINK_DELAY = 15000;

@Component({
  selector: 'app-create-session',
  templateUrl: './create-session.component.html',
  styleUrls: ['./create-session.component.scss']
})
export class CreateSessionComponent implements OnInit, OnDestroy {

  // Page Data
  user: any;
  devices: any[] = [];
  keywordLists: any[] = [];

  menus = Menus;
  currentMenu: Menus = Menus.Settings;
  pageTitle = 'Create Session';
  forms = Forms;
  currentForm: Forms = null;
  displayText = '';

  // Session Data
  sessionName = '';
  byod = true;
  doa = true;
  features = true;
  selectedKeywordList: any = null;
  selectedDevices: any[] = [];
  folder = -1;
  folderPath = 'Home';
  folders: any[];

  constructor(private deviceService: DeviceService,
              private sessionService: SessionService,
              private router: Router,
              private authService: AuthService,
              private route: ActivatedRoute,
              private keywordService: KeywordService) { }

  ngOnInit() {
    this.user = this.authService.user;
    this.deviceService.getDevices(false, true, false, true).subscribe( devices => {
      this.devices = devices;
      this.selectedDevices = [];
      for (const device of devices) {
        // Add custom view fields to pods.
        device['selected'] = false;
        device['blinking'] = false;
      }
    });

    this.keywordService.getKeywordLists().subscribe(keywordLists => {
      this.keywordLists = keywordLists;
      for (const keywordList of this.keywordLists) {
        keywordList['keywordsText'] = keywordList.keywords.join(', ');
      }
    });
    this.sessionService.getFolders().subscribe(folders => {
      this.folders = folders;
      this.route.queryParams.subscribe(params => {
        const passedFolderId = +params['folder'];
        if (passedFolderId > -1) {
          this.setFolderLocation(passedFolderId, this.buildBreadcrumbs(passedFolderId));
        } else {
          this.setFolderLocation(passedFolderId, this.folderPath);
        }
      });
    });
    this.goToSettings();
  }

  ngOnDestroy() {
    const blinkingDevices = this.devices.filter(p => p.blinking === true);
    for (const device of blinkingDevices) {
      this.deviceService.blinkPod(device.id, 'stop').subscribe(() => { });
    }
  }

  setFolderLocation(folderId, pathString) {
    this.folder = folderId;
    this.folderPath = pathString;
    this.closeDialog();
  }
  receiveEmmitedFolder(e: any) {
    if (e === -1) {
      this.folder = null;
    } else {
    this.folder = e;
    }
    this.currentForm = null;
  }

  buildBreadcrumbs(folderId) {
    const breadcrumbs = [];
    let folder = this.folders.find(f => f.id === folderId);
    if (folder != null) {
      breadcrumbs.unshift(folder);
      while (folder.parent) {
        folder = this.folders.find(f => f.id === folder.parent);
        breadcrumbs.unshift(folder);
      }
    }
    if (breadcrumbs.length > 0) {
      const crumbnames = breadcrumbs.map(b => b.name);
      crumbnames.unshift('Home');
       return crumbnames.join('/');
      }
    }

  createSession() {
    if (!this.sessionName && this.sessionName.trim() === '') {
      this.openDialog(this.forms.Error, 'Invalid Session Name');
      this.currentMenu = this.menus.Settings;
    } else {
      const deviceIds = this.selectedDevices.map(d => d.id);
      const keywordListId = (this.selectedKeywordList) ? this.selectedKeywordList.id : null;
      this.sessionService.createNewSession(this.sessionName, deviceIds, keywordListId,
        this.byod, this.features, this.doa, this.folder).subscribe(s => {
        this.router.navigate(['sessions', s.id, 'overview']);
      }, error => {
        this.openDialog(this.forms.Error, error.json()['message']);
        this.goToSettings();
      });
    }
  }

  // ---------------------
  // Keyword Menu
  // ---------------------

  formatKeywordDate(date) {
    return formatDate(date);
  }

  // ---------------------
  // Device Menu
  // ---------------------

  deviceSelected(device: any) {
    if (!this.selectedDevices.includes(device)) {
      this.selectedDevices.push(device);
    } else {
      this.selectedDevices = this.selectedDevices.filter(d => d !== device);
    }
  }

  onClickSelectAll() {
    if (this.selectedDevices.length === this.devices.length) {
      this.selectedDevices = [];
    } else {
      this.selectedDevices = this.devices;
    }
  }

  blinkPod(e: any, device: any) {
    e.stopPropagation();
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

  // ---------------------
  // Navigation and Dialog
  // ---------------------

  goToKeywords() {
    this.currentMenu = this.menus.Keywords;
    this.pageTitle = 'Create Discussion: Keywords';
  }

  goToSettings() {
    this.currentMenu = this.menus.Settings;
    this.pageTitle = 'Create Discussion: Settings';
  }

  goToDevices() {
    this.currentMenu = this.menus.Devices;
    this.pageTitle = 'Create Discussion: Devices';
  }

  navigateToSessions() {
    this.router.navigate(['/sessions']);
  }

  navigateToKeywordLists() {
    this.router.navigate(['/keyword-lists/new']);
  }

  openDialog(form: Forms, text: string) {
    this.currentForm = form;
    this.displayText = text;
  }

  closeDialog() {
    this.currentForm = null;
  }
}
