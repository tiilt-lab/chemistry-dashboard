import { stringToDate } from '../globals';

export class StudentModel {
  // Server Fields
  id;
  // The old sign-up form's first and last name (records from before
  // 2026-10-14); newer records carry the labels below instead.
  lastname;
  firstname;
  username;
  // What pages show: the old names when a record has them, else the username.
  name;
  // The group (table) and team (or role) typed when enrolling.
  group_name;
  team_name;
  biometric_captured;
  creation_date;

  
  static fromJson(json) {
    const model = new StudentModel();
    model.id = json['id'];
    model.lastname = json['lastname'];
    model.firstname = json['firstname'];
    model.username = json['username']
    model.name = json['name'] || json['username']
    model.group_name = json['group_name'] || null
    model.team_name = json['team_name'] || null
    model.biometric_captured = json['biometric_captured']
    model.creation_date = stringToDate(json['creation_date']);
    return model;
  }

  // Converts JSON to UserModel[]
  static fromJsonList(jsonArray) {
    const studentList = [];
    for (const el of jsonArray) {
      studentList.push(StudentModel.fromJson(el));
    }
    return studentList;
  }
}
