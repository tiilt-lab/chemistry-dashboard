import { ApiService } from "./api-service";

export class TopicModelService {
   api = new ApiService() 

  createTopicModel(name, topics) {
    const body = {
      name: name,
      //might have to change this field name w other things
      keywords: topics,
    };
    return this.api.httpRequestCall("api/v1/topic_models",'POST', body);
  }
  
  getTopicModels() {
    return this.api.httpRequestCall("api/v1/topic_models",'GET',{});
  }
}
