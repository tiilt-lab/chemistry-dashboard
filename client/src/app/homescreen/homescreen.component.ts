import { Component, OnInit } from "@angular/core";
import { Router } from "@angular/router";
import { AuthService } from "../services/auth.service";

@Component({
  selector: "app-homescreen",
  templateUrl: "./homescreen.component.html",
  styleUrls: ["./homescreen.component.scss"]
})
export class HomescreenComponent implements OnInit {
  timeOfDay = "";

  constructor(public router: Router, private authService: AuthService) {}

  ngOnInit() {
    this.updateTime();
  }

  updateTime() {
    const today = new Date();
    const curHr = today.getHours();

    if (curHr < 12) {
      this.timeOfDay = "morning";
    } else if (curHr < 18) {
      this.timeOfDay = "afternoon";
    } else {
      this.timeOfDay = "evening";
    }
  }

  navigateToHelp() {
    window.open(
      window.location.protocol +
        "//" +
        window.location.hostname +
        "/help/Default.htm"
    );
  }

  navigateToSettings() {
    this.router.navigate(["settings"]);
  }

  logout() {
    this.authService.logout().subscribe(
      result => {
        this.router.navigate(["login"]);
      },
      error => {
        this.router.navigate(["login"]);
      }
    );
  }
}
