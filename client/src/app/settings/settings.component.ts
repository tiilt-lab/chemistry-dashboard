import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { DeviceService } from '../services/device.service';
import 'rxjs/add/operator/finally';

enum Forms {
  ChangePassword = 1,
  ViewUsers,
  AddUser,
  Loading,
  DeleteUser,
  ConfirmDeleteUser,
  LockUser,
  UnlockUser,
  UserRole,
  ResetUser,
  ServerLogs,
  DeviceLogs,
  DeleteServerLogs,
  DeleteDeviceLogs,
  Status,
  AllowAPI,
  RevokeAPI
}

@Component({
  selector: 'app-settings',
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss']
})
export class SettingsComponent implements OnInit {

  constructor(private router: Router,
              private authService: AuthService,
              private deviceService: DeviceService) { }
  forms = Forms;
  user: any; // The currently logged in user.
  users: any;
  userToDelete: any;
  devices: any;
  currentForm: Forms = null;
  statusTitle = '';
  status = '';

  ngOnInit() {
    this.user = this.authService.user;
  }

  navigateToHomescreen() {
    this.router.navigate(['homescreen']);
  }

  openDialog(newForm: Forms, loadUsers= false, loadDevices= false) {
    if (loadUsers) {
      this.currentForm = this.forms.Loading;
      this.authService.getUsers().subscribe(users => {
        this.users = users.filter(u => u.id !== this.user.id);
        this.currentForm = newForm;
      });
    } else if (loadDevices) {
      this.currentForm = this.forms.Loading;
      this.deviceService.getDevices(false, true, null, true).subscribe(devices => {
        this.devices = devices;
        this.currentForm = newForm;
      });
    } else {
      this.currentForm = newForm;
    }
  }

  closeDialog() {
    this.status = null;
    this.currentForm = null;
  }

  changePassword(password, newPassword, confirmPassword) {
    this.authService.changePassword(password, newPassword, confirmPassword).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(response => {
      this.statusTitle = 'Password Changed';
      this.status = 'Your password has been changed successfully.';
    }, error => {
      this.status = error.json()['message'];
    });
  }

  createUser(email, role) {
    this.authService.createUser(email, role).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(response => {
      this.statusTitle = 'User Created';
      this.status = 'User has been given the password...\n' + response['password'];
    }, error => {
      this.statusTitle = 'Failed to Create User';
      this.status = error.json()['message'];
    });
  }

  confirmDeleteUser(userId: number) {
    userId = +userId;
    this.userToDelete = this.users.find(u => u.id === userId);
    this.currentForm = this.forms.ConfirmDeleteUser;
  }

  deleteSelectedUser() {
    this.authService.deleteUser(this.userToDelete.id).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(response => {
      this.statusTitle = 'User Deleted';
      this.status = this.userToDelete.email + ' has been deleted.';
    }, error => {
      this.statusTitle = 'Failed to Delete User';
      this.status = this.userToDelete.email + ' could not be deleted.';
    });
  }

  lockUser(userId: number) {
    userId = +userId;
    this.authService.lockUser(userId).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(e => {
      const user = this.users.find(u => u.id === userId);
      this.statusTitle = 'User Locked';
      this.status = user.email + ' has been locked out.';
    }, error => {
      const user = this.users.find(u => u.id === userId);
      this.statusTitle = 'Failed to Lock User';
      this.status = user.email + ' could not be locked out.';
    });
  }

  unlockUser(userId: number) {
    userId = +userId;
    this.authService.unlockUser(userId).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(e => {
      const user = this.users.find(u => u.id === userId);
      this.statusTitle = 'User Unlocked';
      this.status = user.email + ' has been unlocked and can now login.';
    }, error => {
      const user = this.users.find(u => u.id === userId);
      this.statusTitle = 'Failed to Unlock User';
      this.status = user.email + ' could not be unlocked.';
    });
  }

  changeUserRole(userId: number, role: string) {
    userId = +userId;
    this.authService.changeUserRole(userId, role).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(e => {
      const user = this.users.find(u => u.id === userId);
      this.statusTitle = 'User Role Updated';
      this.status = user.email + '\'s role is now "' + role + '".';
    }, error => {
      const user = this.users.find(u => u.id === userId);
      this.statusTitle = 'Failed to Update Role';
      this.status = user.email + '\'s role could not be updated.';
    });
  }

  resetUserPassword(userId: number) {
    userId = +userId;
    this.authService.resetUserPassword(userId).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(e => {
      const user = this.users.find(u => u.id === userId);
      this.statusTitle = 'User\'s Password Reset';
      this.status = user.email + '\s new password is...\n' + e['password'];
    }, error => {
      const user = this.users.find(u => u.id === userId);
      this.statusTitle = 'Failed to Reset User\'s Password';
      this.status = user.email + '\'s password could not be reset.';
    });
  }

  downloadServerLogs(type) {
    this.currentForm = this.forms.Loading;
    this.authService.getServerLogs(type).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(success => {
      this.statusTitle = 'Logs Downloaded';
      this.status = 'The logs have been downloaded successfully.';
    }, error => {
      this.statusTitle = 'Logs Download Failed';
      this.status = 'The logs failed to download.  Please try again later.';
    });
  }

  downloadDeviceLogs(deviceId) {
    deviceId = +deviceId;
    this.currentForm = this.forms.Loading;
    this.authService.getDeviceLogs(deviceId).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(success => {
      this.statusTitle = 'Logs Downloaded';
      this.status = 'The logs have been downloaded successfully.';
    }, error => {
        this.statusTitle = 'Logs Download Failed';
        this.status = 'The logs failed to download.  Please try again later.';
    });
  }

  deleteServerLogs(type) {
    this.currentForm = this.forms.Loading;
    this.authService.deleteServerLogs(type).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(success => {
      this.statusTitle = 'Logs Deleted';
      this.status = 'The logs have been deleted successfully.';
    }, error => {
      this.statusTitle = 'Logs Failed to Delete';
      this.status = 'The logs failed to delete.  Please try again later.';
    });
  }

  deleteDeviceLogs(deviceId: number) {
    deviceId = +deviceId;
    this.currentForm = this.forms.Loading;
    this.authService.deleteDeviceLogs(deviceId).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(success => {
      this.statusTitle = 'Logs Deleted';
      this.status = 'The logs have been deleted successfully.';
    }, error => {
      this.statusTitle = 'Logs Failed to Delete';
      this.status = 'The logs failed to delete.  Please try again later.';
    });
  }

  allowAPIAccess(userId: number) {
    userId = +userId;
    this.currentForm = this.forms.Loading;
    this.authService.allowAPIAccess(userId).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(data => {
      const user = this.users.find(u => u.id === userId);
      this.statusTitle = 'User Updated';
      this.status = user.email + ' can now access the API publicly...\n\nClient ID: \n'
                    + data['api_client']['client_id'] + '\n\nClient Secret: \n' + data['client_secret'];
    }, error => {
      this.statusTitle = 'Failed to Update User';
      this.status = 'Failed to grant API access to user.';
    });
  }

  revokeAPIAccess(userId: number) {
    userId = +userId;
    this.currentForm = this.forms.Loading;
    this.authService.revokeAPIAccess(userId).finally(() => {
      this.currentForm = this.forms.Status;
    }).subscribe(data => {
      const user = this.users.find(u => u.id === userId);
      this.statusTitle = 'User Updated';
      this.status = user.email + ' can no longer access the API publicly.';
    }, error => {
      this.statusTitle = 'Failed to Update User';
      this.status = 'Failed to revoke API access.';
    });
  }
}
