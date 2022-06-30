import { Component, OnInit, Input } from '@angular/core';

@Component({
  selector: 'app-section-box',
  templateUrl: './section-box.component.html',
  styleUrls: ['./section-box.component.scss']
})
export class SectionBoxComponent implements OnInit {

  @Input('heading') heading: string;
  @Input('maxHeight') maxHeight: number = null;

  constructor() { }

  ngOnInit() {
  }

}
