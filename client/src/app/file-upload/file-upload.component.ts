import { Component, OnInit, EventEmitter } from "@angular/core";
import { AuthService } from "../services/auth.service";
import { FileUploadService } from "../services/file-upload.service";
import { FormBuilder, FormGroup } from "@angular/forms";
import { ActivatedRoute, Router } from "@angular/router";

@Component({
  selector: "app-file-upload",
  templateUrl: "./file-upload.component.html",
  styleUrls: ["./file-upload.component.scss"],
})
export class FileUploadComponent implements OnInit {
  user: any;
  selectedFile: File = null;
  uploadForm: FormGroup;
  myFiles: any = [];

  constructor(
    private authService: AuthService,
    private fileUploadService: FileUploadService,
    private formBuilder: FormBuilder,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  topics: any[];

  ngOnInit() {
    if (this.authService.user) {
      this.user = this.authService.user;
      console.log("Current User: ", this.user);
    }
    this.uploadForm = this.formBuilder.group({
      fileUpload: [""],
    });
  }

  onFileSelect(event) {
    if (event.target.files.length > 0) {
      for (var i = 0; i < event.target.files.length; i++) {
        const file = event.target.files[i];
        // this.uploadForm.get("fileUpload").setValue(file);
        this.myFiles.push(file);
      }
    }
  }

  navigateToHomescreen() {
    this.router.navigate(["homescreen"]);
  }

  createTopicModel() {
    this.fileUploadService.getTopics().subscribe((topics) => {
      this.topics = topics;
      for (const topic of this.topics) {
        console.log("Topic: ", topic);
      }
    });
  }

  onSubmit() {
    const formData = new FormData();
    for (var i = 0; i < this.myFiles.length; i++) {
      console.log("My files: ", this.myFiles[i]);
      formData.append("fileUpload[]", this.myFiles[i], this.myFiles[i].name);
    }
    console.log("formData: ", formData.get("fileUpload[]"));
    const URL = `api/v1/uploads/${this.user.id}`;
    this.fileUploadService.uploadFile(URL, formData).subscribe((result) => {
      console.log(result);
    });
  }
}
