import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { SessionService } from '../services/session.service';
import 'rxjs/add/operator/finally';
import {Location} from '@angular/common';

enum Forms {
  RenameSession = 1,
  RenameFolder,
  DeleteSession,
  DeleteFolder,
  NewFolder,
  Loading,
  MoveSession,
  MoveFolder
}

@Component({
  selector: 'app-sessions',
  templateUrl: './sessions.component.html',
  styleUrls: ['./sessions.component.scss']
})
export class SessionsComponent implements OnInit {

  forms = Forms;
  currentForm: Forms = null;
  sessions: any[] = [];
  folders: any [] = [];
  displayedFolders: any [] = [];
  displayedSessions: any [] = [];
  selectableFolders: any[] = [];
  selectedSession: any;
  selectedFolder: any;
  isLoading = true;
  showAlert = false;
  alertMessage: string;
  breadcrumbs: any[] = [];
  currentFolder: any;
  folderPath: string;

  constructor(private router: Router,
              private sessionService: SessionService,
              private route: ActivatedRoute,
              private location: Location
              ) { }

  ngOnInit() {
    this.sessionService.getSessions().subscribe(sessions => {
      this.sessions = sessions;

      this.sessionService.getFolders().subscribe(folders => {
        this.folders = folders;
        console.log(folders, 'folders ...')
        this.route.queryParams.subscribe(params => {
          const folder = params['folder'];
          this.displayFolder(parseInt(folder, 10));
        });
      });
    });
    this.isLoading = false;
  }

  navigateToHomescreen() {
    this.router.navigate(['homescreen']);
  }

  newRecording() {
    this.router.navigate(['/sessions/new'], {queryParams: {folder: this.currentFolder}});
  }

  goToSession(session) {
    this.router.navigate(['/sessions/' + session.id]);
  }

  // ----------
  // Folders
  // ----------

  displayFolder(folderId?) {
    if (!folderId) {
      this.displayedFolders = this.folders.filter(f => f.parent == null);
      this.displayedSessions = this.sessions.filter(s => s.folder == null);
      this.breadcrumbs = [];
      this.currentFolder = undefined;
      const url = '/sessions';
      this.location.replaceState(url);
    } else {
      this.displayedFolders = this.folders.filter(x => x.parent === folderId);
      this.displayedSessions = this.sessions.filter(s => s.folder === folderId);
      this.currentFolder = folderId;
      this.buildBreadcrumbs(folderId);
      const url = '/sessions/?folder=' + folderId;
      this.location.replaceState(url);
    }
  }

  buildBreadcrumbs(folderId) {
    this.breadcrumbs = [];
    let folder = this.folders.find(f => f.id === folderId);
    if (folder != null) {
      this.breadcrumbs.unshift(folder);
      while (folder.parent) {
        folder = this.folders.find(f => f.id === folder.parent);
        this.breadcrumbs.unshift(folder);
      }
    }
  }

  buildBreadcrumbString() {
    if (this.breadcrumbs.length > 0) {
      const crumbnames = this.breadcrumbs.map(b => b.name);
      crumbnames.unshift('Home');
      this.folderPath = crumbnames.join('/');
    }
  }

  goBackToPrevious() {
    if (this.breadcrumbs.length > 1) {
      this.displayFolder(this.breadcrumbs[this.breadcrumbs.length - 2].id);
    } else {
      this.displayFolder();
    }
  }

  addFolder(newName: string, locationId: number) {
    if (!newName) {
      this.showAlert = true;
      this.alertMessage = 'Please enter folder name';
      this.closeDialog();
    } else {
      this.sessionService.addFolder(newName, locationId).finally(() => {
        this.closeDialog();
      }).subscribe(folder => {
        this.folders.push(folder);
        if (locationId) {
          this.displayFolder(folder.parent);
        } else {
          this.displayFolder();
        }
      }, error => {
        this.showAlert = true;
        this.alertMessage = error.json()['message'];
      });
    }
  }

  changeFolderName(newName: string) {
    this.currentForm = this.forms.Loading;
    const folderId = this.selectedFolder.id;
    this.sessionService.updateFolder(folderId, null, newName).finally(() => {
      this.closeDialog();
    }).subscribe(folder => {
      const folderIndex = this.folders.findIndex(s => s.id === folder.id);
      this.folders[folderIndex] = folder;
      this.displayFolder(folder.parent);
    }, error => {
      this.showAlert = true;
      this.alertMessage = error.json()['message'];
    });
  }

  moveFolder(newFolderId) {
    this.sessionService.updateFolder(this.selectedFolder.id, newFolderId, null).finally(() => {
      this.closeDialog();
    }).subscribe(updatedFolder => {
      const index = this.folders.findIndex(f => f.id === updatedFolder.id);
      this.folders[index] = updatedFolder;
      this.displayFolder(updatedFolder.parent);
    }, error => {
      this.showAlert = true;
      this.alertMessage = (error.json()['message']);
    });
  }

  deleteFolder() {
    this.currentForm = this.forms.Loading;
    const folderId = this.selectedFolder.id;
    const parentId = this.selectedFolder.parent;
    this.sessionService.deleteFolder(folderId).finally(() => {
      this.closeDialog();
    }).subscribe(() => {
      const foldersToRemove = [folderId];
      const children = this.folders.filter(f => f.parent === folderId);
      while (children.length > 0) {
        const child = children.pop();
        foldersToRemove.push(child.id);
        this.folders.filter(f => f.parent === child.id).forEach(f => children.push(f));
      }
      this.folders = this.folders.filter(f => foldersToRemove.indexOf(f.id) === -1);
      this.sessions = this.sessions.filter(s => foldersToRemove.indexOf(s.folder) === -1);
      if (parentId) {
        this.displayFolder(parentId);
      } else {
        this.displayFolder();
      }
    }, error => {
      this.showAlert = true;
      this.alertMessage = error.json()['message'];
    });
  }

  // ----------
  // Sessions
  // ----------

  endSession(session: any) {
    this.currentForm = this.forms.Loading;
    const sessionId = session.id;
    this.selectedSession = null;
    this.sessionService.endSession(sessionId).finally(() => {
      this.closeDialog();
    }).subscribe(endedSession => {
      const sessionIndex = this.sessions.findIndex(s => s.id === endedSession.id);
      this.sessions[sessionIndex] = endedSession;
      this.displayFolder(endedSession.folder);
    },
      error => {
        this.showAlert = true;
        this.alertMessage = error.json()['message'];
    });
  }

  changeSessionName(newName: string) {
    this.currentForm = this.forms.Loading;
    const sessionId = this.selectedSession.id;
    this.sessionService.updateSession(sessionId, newName).subscribe(session => {
      const sessionIndex = this.sessions.findIndex(s => s.id === session.id);
      if (sessionIndex > -1) {
        this.sessions[sessionIndex] = session;
    this.displayFolder(session.folder);
      }
    }, error => {
      this.showAlert = true;
      this.alertMessage = error.json()['message'];
    });
    this.closeDialog();
  }

  moveSession(newParentId) {
    this.sessionService.updateSessionFolder(this.selectedSession.id, newParentId).finally(() => {
      this.closeDialog();
    }).subscribe(updatedSession => {
      const index = this.sessions.findIndex(s => s.id === updatedSession.id);
      this.sessions[index] = updatedSession;
      this.displayFolder(updatedSession.folder);
    }, error => {
      this.showAlert = true;
      this.alertMessage = error.json()['message'];
    });
  }

  deleteSession() {
    this.currentForm = this.forms.Loading;
    const sessionId = this.selectedSession.id;
    this.sessionService.deleteSession(sessionId).finally(() => {
      this.closeDialog();
    }).subscribe(() => {
      const parent = this.folders.find(f => f.id === this.selectedSession.folder);
      this.sessions = this.sessions.filter(s => s.id !== sessionId);
      if (parent) {
        this.displayFolder(parent.id);
      } else {
        this.displayFolder();
      }
    }, error => {
      this.showAlert = true;
      this.alertMessage = error.json()['message'];
    });
  }

  // ----------
  // Dialogs
  // ----------

  openSessionDialog(newForm: any, selectedSession?: any) {
    this.currentForm = newForm;
    this.selectedSession = selectedSession;
    if (this.currentForm === Forms.MoveSession) {
      this.selectableFolders = this.folders;
    }
  }

  openFolderDialog(newForm: any, selectedFolder?: any) {
    this.currentForm = newForm;
    this.selectedFolder = selectedFolder;
    if (this.currentForm === Forms.MoveFolder) {
      this.selectableFolders = this.folders.filter(f => f.parent !== this.selectedFolder.id && f.id !== this.selectedFolder.id);
    }
  }

  closeDialog() {
    this.currentForm = null;
    this.selectedSession = null;
    this.selectedFolder = null;
  }

  closeAlert() {
    this.showAlert = false;
  }

  printdebug(tempVar){
    console.log(tempVar, 'debugging ...');

  }
}
