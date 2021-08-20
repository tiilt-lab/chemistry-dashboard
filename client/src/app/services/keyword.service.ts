import { Injectable } from "@angular/core";
import { ApiService } from "./api.service";
import { Observable } from "rxjs/Observable";
import { KeywordListModel } from "../models/keyword-list";
import { KeywordListItemModel } from "../models/keyword-list-item";
import "rxjs/add/operator/map";

@Injectable()
export class KeywordService {
  constructor(private api: ApiService) {}

  getKeywordList(keywordListID): Observable<any> {
    return this.api
      .get("api/v1/keyword_lists/" + keywordListID)
      .map((response) => {
        return KeywordListModel.fromJson(response.json());
      });
  }

  getKeywordLists(): Observable<any> {
    return this.api.get("api/v1/keyword_lists").map((response) => {
      return KeywordListModel.fromJsonList(response.json());
    });
  }

  getTopics(): Observable<any> {
    return this.api.get("api/v1/topics").map((response) => {
      return response.json();
    });
  }

  createKeywordList(name: string, keywords: any[]): Observable<any> {
    const body = {
      name: name,
      keywords: keywords,
    };
    return this.api.post("api/v1/keyword_lists", body).map((response) => {
      return KeywordListModel.fromJson(response.json());
    });
  }

  updateKeywordList(
    keywordListID: number,
    name: string,
    keywords: any[]
  ): Observable<any> {
    const body = {
      name: name,
      keywords: keywords,
    };
    return this.api
      .put("api/v1/keyword_lists/" + keywordListID, body)
      .map((response) => {
        return KeywordListModel.fromJson(response.json());
      });
  }

  deleteKeywordList(keywordListID: number): Observable<any> {
    return this.api
      .delete("api/v1/keyword_lists/" + keywordListID)
      .map((response) => {
        return response.json();
      });
  }

  getKeywordListItems(keywordListID: number): Observable<any> {
    return this.api
      .get("api/v1/keyword_lists/" + keywordListID + "/keywords")
      .map((response) => {
        return KeywordListItemModel.fromJsonList(response.json());
      });
  }
}
