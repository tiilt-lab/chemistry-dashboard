import { Component, HostListener, OnInit, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-dialog',
  templateUrl: './dialog.component.html',
  styleUrls: ['./dialog.component.scss']
})
export class DialogComponent implements OnInit {

  @Output() closeDialog: EventEmitter<any> = new EventEmitter();

  @HostListener('document:keydown', ['$event'])
  public handleKeyboardEvent(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      event.stopPropagation();
      this.closeDialogEvent();
    }
  }
  constructor() { }

  ngOnInit() {
  }

  closeDialogEvent() {
    this.closeDialog.emit();
  }
}
