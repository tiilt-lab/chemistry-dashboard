import { Component, OnInit, ViewChildren, QueryList, ElementRef } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { KeywordService } from '../services/keyword.service';
import { KeywordListItemModel } from '../models/keyword-list-item';
import { KeywordListModel } from '../models/keyword-list';

@Component({
  selector: 'app-keyword-list-items',
  templateUrl: './keyword-list-items.component.html',
  styleUrls: ['./keyword-list-items.component.scss']
})
export class KeywordListItemsComponent implements OnInit {
  keywordListID: any;
  keywordList: any;
  keywordListItems: any[];
  validName = true;
  newPressed = false;

  @ViewChildren('keywordInput') set newInput(inputs: QueryList<ElementRef>) {
    if (inputs) {
      if (this.newPressed) {
        setTimeout(() => {
          inputs.last.nativeElement.focus();
          this.newPressed = false;
        }, 0);
      }
    }
  }

  constructor(private router: Router,
              private route: ActivatedRoute,
              private keywordService: KeywordService) { }

  ngOnInit() {
    this.route.params.subscribe(params => {
      const url = this.router.url;
      this.keywordListID = params['keyword-list-id'];
      if (!isNaN(this.keywordListID)) {
        this.keywordService.getKeywordList(this.keywordListID).subscribe(result => {
          this.keywordList = result;
          this.keywordListItems = [];
          for (const keyword of this.keywordList.keywords) {
            this.keywordListItems.push({'keyword': keyword});
          }
        });
      } else {
        this.keywordListID = -1; // -1 denotes that list is new
        this.keywordList = new KeywordListModel();
        this.keywordList.name = null;
        this.keywordList.id = -1;
        this.keywordListItems = [];
      }
    });
  }

  saveKeywordList() {
    if (!this.isValid) {
      return;
    }
    const keywords = this.keywordListItems.filter(item => item.keyword != null).map(item => item.keyword);
    if (this.keywordListID === -1) {
      this.keywordService.createKeywordList(this.keywordList.name, keywords).subscribe(response => {
        this.goBackToKeywordLists();
      }, error => {
        alert(error.json()['message']);
      });
    } else {
      this.keywordService.updateKeywordList(this.keywordListID, this.keywordList.name, keywords).subscribe(response => {
        this.goBackToKeywordLists();
      }, error => {
        alert(error.json()['message']);
      });
    }
  }

  addNewKeyword() {
    const emptyItems = this.keywordListItems.filter(item => !item.keyword);
    for (const emptyItem of emptyItems) {
      this.removeKeyword(emptyItem);
    }
    this.newPressed = true;
    this.keywordListItems.push(new KeywordListItemModel());
   
  }

  removeKeyword(item) {
    this.keywordListItems = this.keywordListItems.filter(k => k !== item);
  }

  checkName(event: any) {
    // TBD: Set name rules.
    this.validName = true;
    if (this.validName) {
      if (event.which === 13) { // Enter
        this.addNewKeyword();
      }
    }
  }

  checkKeyword(keyword: any, event: any) {
    if (!keyword.keyword) {
      return;
    }
    const new_keyword = keyword.keyword.trim().toLowerCase();
    if (new_keyword.length === 0) {
      keyword.error = 'Your keyword is empty.';
    } else if (!new_keyword.match('^[A-Za-z0-9\']+$')) {
      keyword.error = 'Your keyword contains one or more invalid characters. Please only use alphabets and numbers.'
                    + ' Spaces and special characters are not allowed.';
    } else if (this.keywordListItems.find(k => k.keyword === keyword.keyword && k !== keyword)) {
      keyword.error = 'Your list already contains that keyword.';
    } else {
      keyword.error = null;
    }
    if (!keyword.error) {
      if (event.which === 13) { // Enter
        this.addNewKeyword();
      }
    }
  }

  trackByFn(index, item) {
    return item.value;
  }

  get isValid(): boolean {
    if (this.keywordList && this.keywordListItems && this.keywordListItems.length !== 0) {
      return (this.validName && this.keywordListItems.filter(k => k.error != null).length === 0
      && this.keywordListItems.filter(k => k.keyword && k.keyword.length !== 0).length > 0);
    }
    return false;
  }

  goBackToKeywordLists() {
    this.router.navigate(['/keyword-lists']);
  }
}
