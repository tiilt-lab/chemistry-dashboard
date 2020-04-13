import { stringToDate } from '../globals';

export class KeywordListModel {
  // Server Fields
  id: number;
  creation_date: Date;
  name: string;
  keywords: any[];

  static fromJson(json): KeywordListModel {
    const model = new KeywordListModel();
    model.id = json['id'];
    model.creation_date = stringToDate(json['creation_date']);
    model.name = json['name'];
    model.keywords = json['keywords'];
    return model;
  }

  // Converts JSON to KeywordListModel[]
  static fromJsonList(jsonArray: any): KeywordListModel[] {
    const keywordLists = [];
    for (const el of jsonArray) {
      keywordLists.push(KeywordListModel.fromJson(el));
    }
    return keywordLists;
  }
}
