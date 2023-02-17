import { ApiService } from "./api-service";

export class FileUploadService {
  api = new ApiService()

  uploadFile(url, formData){
    return this.api.postFiles(url, formData);
  }

  getTopics() {
    return this.api.httpRequestCall("api/v1/topics",'GET',{});
  }
}
