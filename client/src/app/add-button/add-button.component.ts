import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'app-add-button',
  templateUrl: './add-button.component.html',
  styleUrls: ['./add-button.component.scss']
})
export class AddButtonComponent implements OnInit {
  @Input('isFocused') isFocused: boolean;
  @Input('isInvalid') isInvalid: boolean;
  isClicked = false;

  constructor() { }

  ngOnInit() {
  }
}
