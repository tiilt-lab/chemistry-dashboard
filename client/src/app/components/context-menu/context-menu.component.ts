import { Component, ViewChild, ElementRef, HostListener } from '@angular/core';

@Component({
  selector: 'app-context-menu',
  templateUrl: './context-menu.component.html',
  styleUrls: ['./context-menu.component.scss']
})
export class ContextMenuComponent {

  isOpen = false;
  constructor(private elementRef: ElementRef) { }

  toggle(state: boolean = null) {
    if (state == null) {
      this.isOpen = !this.isOpen;
    } else {
      this.isOpen = state;
    }
  }

  @HostListener('window:click', ['$event.target'])
  onClick(targetElement) {
    const clickedInside = this.elementRef.nativeElement.contains(targetElement);
    if (!clickedInside && this.isOpen) {
      this.isOpen = false;
    }
  }
}
