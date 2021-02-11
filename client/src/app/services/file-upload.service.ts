import { Injectable } from "@angular/core";
import { ApiService } from "./api.service";
import { Observable } from "rxjs/Observable";

@Injectable()
export class FileUploadService {
  constructor(private api: ApiService) {}

  uploadFile(url, file): Observable<any> {
    // console.log("formData to upload " + formData.get("file"));
    // const body = {
    //   formData: formData,
    // };
    console.log("This is the file: ", file);
    const formData = new FormData();
    formData.append("fileUpload", file, file.name);
    console.log(typeof formData);
    console.log("This is the formData: ", formData.get("fileUpload"));
    // const body = { formData: formData };

    return this.api.post(url, formData, {}, true).map((response) => {
      return response.json();
    });
  }

  updateFiles(): Observable<any>{
    return this.api.get('api/v1/uploads/update_files').map(response => {
      return response.json();
    });
  }

  getTopics(): Observable<any> {
    return this.api.get('api/v1/topics').map(response => {
      return response.json();
    });
  }


}
