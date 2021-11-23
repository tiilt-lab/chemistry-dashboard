import { Injectable } from "@angular/core";
import { ApiService } from "./api.service";
import { Observable } from "rxjs/Observable";

@Injectable()
export class FileUploadService {
  constructor(private api: ApiService) {}

  uploadFile(url, formData): Observable<any> {
    return this.api.post(url, formData, {}, true).map((response) => {
      return response.json();
    });
  }

  getTopics(): Observable<any> {
    return this.api.get("api/v1/topics").map((response) => {
      return response.json();
    });
  }
}
