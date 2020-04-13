import { Component, Input, Output, EventEmitter } from '@angular/core';

@Component({
    selector: 'app-header',
    templateUrl: './header.component.html',
    styleUrls: ['./header.component.scss']
})
export class HeaderComponent {
    @Input('title') title: string;
    @Input('leftText') leftText: any[];
    @Input('rightText') rightText: any[];
    @Input('rightEnabled') rightEnabled = true;
    @Output() rightTextClick: EventEmitter<any> = new EventEmitter();
    @Output() backClick: EventEmitter<any> = new EventEmitter();

    constructor() { }

    backClicked() {
        this.backClick.emit();
    }

    rightTextClicked() {
        if (this.rightEnabled) {
            this.rightTextClick.emit();
        }
    }
}
