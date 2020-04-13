import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { KeywordService } from '../services/keyword.service';
import { formatDate } from '../globals';

@Component({
  selector: 'app-manage-keyword-lists',
  templateUrl: './manage-keyword-lists.component.html',
  styleUrls: ['./manage-keyword-lists.component.scss']
})
export class ManageKeywordListsComponent implements OnInit {

  constructor(private router: Router,
              private keywordService: KeywordService) { }

  deleteDialogIsOpen = false;
  keywordListToDelete: any;
  keywordLists: any[];
  formatDate = formatDate; // Allows the HTML to invoke the function.

  ngOnInit() {
    this.keywordService.getKeywordLists().subscribe(keywordLists => {
      this.keywordLists = keywordLists;
      for (const keywordList of this.keywordLists) {
        keywordList['keywordsText'] = keywordList.keywords.join(', ');
      }
    });
  }

  openNewKeywordList() {
    this.router.navigate(['/keyword-lists/new']);
  }

  keywordListClicked(keywordList) {
    this.router.navigate(['/keyword-lists/' + keywordList.id]);
  }

  navigateToHomeScreen() {
    this.router.navigate(['/homescreen']);
  }

  closeDeleteDialog() {
    this.deleteDialogIsOpen = false;
  }

  // Open confirmation dialog.
  deleteKeywordList(keywordList) {
    this.keywordListToDelete = keywordList;
    this.deleteDialogIsOpen = true;
  }

  // Deletes a keyword list.  Called from confirmation dialog.
  confirmDeleteKeywordList() {
    this.keywordService.deleteKeywordList(this.keywordListToDelete.id).subscribe(result => {
        this.keywordLists = this.keywordLists.filter(kl => kl.id !== this.keywordListToDelete.id);
        this.keywordListToDelete = null;
        this.closeDeleteDialog();
      },
      err => {
        console.log('Failed to delete keyword list.');
        this.closeDeleteDialog();
      }
    );
  }

  formatKeywords(keywords) {
    if (keywords) {
      return keywords.map(k => k.keyword).join(', ');
    }
    return '';
  }
}
