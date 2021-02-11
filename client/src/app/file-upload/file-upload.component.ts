import { Component, OnInit, EventEmitter } from "@angular/core";
import { AuthService } from "../services/auth.service";
import { FileUploadService } from "../services/file-upload.service";
import { Form, FormBuilder, FormGroup, FormArray, FormControl } from "@angular/forms";
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
  topics: any[];
  FileName: string = 'No file selected';
  filesData = [];
  fileForm: FormGroup;

  get filesFormArray() {
    return this.fileForm.controls.files as FormArray;
  }

  constructor(
    private authService: AuthService,
    private fileUploadService: FileUploadService,
    private formBuilder: FormBuilder,
    private route: ActivatedRoute,
    private router: Router
  ) {
    this.fileForm = this.formBuilder.group({
      files: new FormArray([])
    });
    this.updateFiles();
  }

  ngOnInit() {
    if (this.authService.user) {
      this.user = this.authService.user;
      console.log("Current User: ", this.user);
    }
    this.uploadForm = this.formBuilder.group({
      fileUpload: [""],
    });


    
  }

  // onFileSelected(event) {
  //   this.selectedFile = event.target.files[0];
  // }

  onFileSelect(event) {
    if (event.target.files.length > 0) {
      const file = event.target.files[0];
      this.uploadForm.get("fileUpload").setValue(file);
      this.FileName = file.name;
    }
  }

  navigateToHomescreen() {
    this.router.navigate(["homescreen"]);
  }

  onSubmit() {
    // let fd = new FormData();
    // fd.append("file", this.selectedFile);
    // const formData = new FormData();
    // formData.append("file", this.uploadForm.get("fileUpload").value);
    // console.log("THis is fd created on front-end: ", formData.get("file"));
    const URL = `api/v1/uploads/${this.user.id}`;
    this.fileUploadService
      .uploadFile(URL, this.uploadForm.get("fileUpload").value)
      .subscribe((result) => {
        console.log(result);
        window.location.reload();
      });
    
  }

  private addCheckboxes() {
    this.filesData.forEach(() => this.filesFormArray.push(new FormControl(false)));
  }

  updateFiles(){
    this.fileUploadService.updateFiles().subscribe(files => {
      //console.log("files:"+files);
      this.filesData = [];
      var iter = 0;
      for (const fileName of files) {
        //list here
        //console.log(fileName);
        this.filesData.push({
          id: iter,
          name: fileName
        })

        iter = iter + 1;
      };

      this.addCheckboxes();

      //incorporate topic modeling of selectedFilesIds
    });
  }

  createTopicModel(){
    this.fileUploadService.getTopics().subscribe(topics => {
      this.topics = topics;
      for (const topic of this.topics) {
        console.log("Topic: ",topic)
      }

      const selectedFileIds = this.fileForm.value.files
      .map((checked, i) => checked ? this.filesData[i].id : null)
      .filter(v => v !== null);

      console.log(selectedFileIds);
    });
  }

}

