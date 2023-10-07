import { ApiService } from "./api-service";

export class TopicModelService {
   api = new ApiService()

  saveTopicModel(name, summary) {
    const body = {
      name: name,
      summary: summary
    };
    return this.api.httpRequestCall("api/v1/topics",'POST', body);
  }

  getTopicModel() {
    return this.api.httpRequestCall("api/v1/topics",'GET',{});
  }

  getTopicModels() {
    return this.api.httpRequestCall('api/v1/topic_models','GET',{})
  }

  deleteTopicModel(topicModelID){
    return this.api.httpRequestCall("api/v1/topic_models/"+topicModelID,'DELETE',{});
  }
}
