import { ApiService } from "./api-service";

export class FileUploadService {
  api = new ApiService()

  uploadFile(url, formData){
    return this.api.httpRequestCall(url,'POST', formData);
  }

  getTopics() {
    return this.api.httpRequestCall("api/v1/topics",'GET',{});
  }
}
