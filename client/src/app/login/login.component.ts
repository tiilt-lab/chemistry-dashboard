import { Component, OnInit, HostListener, ViewChild, ElementRef } from '@angular/core';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent implements OnInit {

  @ViewChild('username') txtUsername: ElementRef;
  @ViewChild('password') txtPassword: ElementRef;

  loginErrorText = null;
  showLoginDialog = false;

  constructor(private router: Router,
              private authService: AuthService) { }

  ngOnInit() {
    this.authService.me().subscribe(response => {
      this.router.navigate(['homescreen']);
    }, error => {});
  }

  login() {
    if (this.txtUsername.nativeElement.value.trim() === '') {
      this.loginErrorText = 'Please enter your username or email.';
      this.txtUsername.nativeElement.focus();
      this.showLoginDialog = true;
    } else if (this.txtPassword.nativeElement.value.trim() === '') {
      this.loginErrorText = 'Please enter your password.';
      this.txtPassword.nativeElement.focus();
      this.showLoginDialog = true;
    } else {
      this.authService.login(this.txtUsername.nativeElement.value, this.txtPassword.nativeElement.value).subscribe(e => {
        this.router.navigate(['homescreen']);
      },
      error => {
        if (error.status === 429) {
          this.loginErrorText = 'You are attempting to login too frequently.  Please try again later.';
        } else {
          this.loginErrorText = error.json()['message'];
        }
        this.showLoginDialog = true;
      });
    }
  }

  @HostListener('document:keyup.enter', ['$event'])
  onKeydownHandler(event: KeyboardEvent) {
    if (event.keyCode === 13 && this.showLoginDialog) {
      this.closeDialog();
    } else if (event.keyCode === 13) {
      this.login();
    }
  }

  closeDialog() {
    this.showLoginDialog = false;
  }

  navigateBack() {
    this.router.navigate(['']);
  }
}
