import { mode } from 'd3';
import { stringToDate } from '../globals';

export class RaterModel {
  // Server Fields
  id;
  sessionid;
  sessiondeviceid;
  speakerid;
  speakertag;
  raterid;
  dashboardtype;
  evaluationCategory;
  completed;
  creation_date;

  
  static fromJson(json) {
    const model = new RaterModel();
    model.id = json['id'];
    model.sessionid = json['sessionid'];
    model.sessiondeviceid = json['sessiondeviceid'];
    model.speakerid = json['speakerid'];
    model.speakertag = json['speakertag'];
    model.raterid = json['raterid'];
    model.dashboardtype = json['type'];
    model.evaluationCategory = json['evaluation_category'];
    model.completed = json['completed'];
    model.creation_date = stringToDate(json['creation_date']);
    return model;
  }

  // Converts JSON to UserModel[]
  static fromJsonList(jsonArray) {
    const raterList = [];
    for (const el of jsonArray) {
      raterList.push(RaterModel.fromJson(el));
    }
    return raterList;
  }
}
