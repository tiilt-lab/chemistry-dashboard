import { ApiService } from "./api-service";

export class FileUploadService {
  api = new ApiService()

  uploadFile(url, formData){
    return this.api.postFiles(url, formData);
  }
}
