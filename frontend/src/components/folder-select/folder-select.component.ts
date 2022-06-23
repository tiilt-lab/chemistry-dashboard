import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-folder-select',
  templateUrl: './folder-select.component.html',
  styleUrls: ['./folder-select.component.scss']
})
export class FolderSelectComponent implements OnInit {
  @Input('folders')
  set folders(value: any[]) {
    if (value != null) {
      this._folders = value;
      this.displayFolder();
    }
  }
  @Output() itemSelected = new EventEmitter<any>();

  get folder(): number {
    return this.selectedFolder;
  }

  get breadcrumb(): string {
    const crumbnames = this.breadcrumbs.map(b => b.name);
    if (this.selectedFolder !== -1) {
      const currentFolder = this._folders.find(f => f.id === this.selectedFolder);
      crumbnames.push(currentFolder.name);
    }
    crumbnames.unshift('Home');
    return crumbnames.join('/');
  }

  _folders: any[];
  visibleFolders: any[] = [];
  selectedFolder: any;
  breadcrumbs: any [] = [];
  recentFolder: any;

  constructor(private route: ActivatedRoute) {}

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.recentFolder = this._folders.find(f => f.id === (parseInt(params['folder'], 10)));
      if (this.recentFolder) {
        this.displayFolder(this.recentFolder.parent);
      }
    });
  }

  displayFolder(folderId?) {
    if (!folderId || folderId === undefined) {
      this.visibleFolders = this._folders.filter(f => f.parent == null);
      this.breadcrumbs = [];
    } else {
      this.visibleFolders = this._folders.filter(x => x.parent === folderId);
      this.breadcrumbs = [];
      let folder = this._folders.find(f => f.id === folderId);
      this.breadcrumbs.unshift(folder);
      while (folder.parent) {
        folder = this._folders.find(f => f.id === folder.parent);
        this.breadcrumbs.unshift(folder);
      }
    }
  }

  hasChildren(folder) {
    const children = this._folders.filter(x => x.parent === folder.id);
    return children.length > 0;
  }

  setSelectedFolder(id) {
    this.selectedFolder = id;
  }
}
