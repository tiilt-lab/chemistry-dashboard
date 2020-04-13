import { Component } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-landing-page',
  templateUrl: './landing-page.component.html',
  styleUrls: ['./landing-page.component.scss']
})
export class LandingPageComponent {

  constructor(private router: Router) { }

  timeOfDay = this.updateTime();

  goToLogin() {
    this.router.navigate(['login']);
  }

  goToJoin() {
    this.router.navigate(['join']);
  }

  updateTime() {
    const today = new Date();
    const curHr = today.getHours();

    if (curHr < 12) {
      return 'morning';
    } else if (curHr < 18) {
      return 'afternoon';
    } else {
      return 'evening';
    }
  }
}
