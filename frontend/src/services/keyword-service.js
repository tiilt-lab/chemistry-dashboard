import { ApiService } from "./api-service";
import { KeywordListModel } from "../models/keyword-list";
import { KeywordListItemModel } from "../models/keyword-list-item";
import "rxjs/add/operator/map";

export class KeywordService {
   api = new ApiService() 

  getKeywordList(keywordListID){
    return this.api.httpRequestCall("api/v1/keyword_lists/" + keywordListID,'GET',{});
  }

  getKeywordLists() {
    return this.api.httpRequestCall("api/v1/keyword_lists",'GET',{});
  }

  getTopics(){
    return this.api.httpRequestCall("api/v1/topics",'GET',{});
  }

  createKeywordList(name, keywords) {
    const body = {
      name: name,
      keywords: keywords,
    };
    return this.api.httpRequestCall("api/v1/keyword_lists",'POST', body);
  }

  updateKeywordList(keywordListID,name,keywords ) {
    const body = {
      name: name,
      keywords: keywords,
    };
    return this.api
      .httpRequestCall("api/v1/keyword_lists/" + keywordListID, 'PUT',body);
  }

  deleteKeywordList(keywordListID) {
    return this.api
      .httpRequestCall("api/v1/keyword_lists/" + keywordListID,'DELETE',{});
  }

  getKeywordListItems(keywordListID) {
    return this.api.httpRequestCall("api/v1/keyword_lists/" + keywordListID + "/keywords",'GET',{});
  }
}
