import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ActiveSessionService } from '../services/active-session.service';

@Component({
  selector: 'app-session-manager',
  templateUrl: './session-manager.component.html',
  styleUrls: ['./session-manager.component.scss']
})
export class SessionManagerComponent implements OnInit, OnDestroy {

  constructor(private router: Router,
              private route: ActivatedRoute,
              public activeSessionService: ActiveSessionService) { }

  ngOnInit() {
    this.route.params.subscribe(params => {
      const sessionId = params['sessionId'];
      this.activeSessionService.initialize(sessionId);
    });
  }

  ngOnDestroy() {
    this.activeSessionService.close();
  }
}
