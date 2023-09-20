import { stringToDate } from '../globals';

export class TopicModelModel {
  // Server Fields
  id;
  creation_date;
  name;
  summary;

  static fromJson(json){
    const model = new TopicModelModel();
    model.id = json['id'];
    model.creation_date = stringToDate(json['creation_date']);
    model.name = json['name'];
    model.summary = json['summary'];
    return model;
  }

  // Converts JSON to KeywordListModel[]
  static fromJsonList(jsonArray){
    const TopicModels = [];
    for (const el of jsonArray) {
      TopicModels.push(TopicModelModel.fromJson(el));
    }
    return TopicModels;
  }
}
