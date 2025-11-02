import { stringToDate } from '../globals';

export class StudentModel {
  // Server Fields
  id;
  lastname;
  firstname;
  username;
  biometric_captured;
  creation_date;

  
  static fromJson(json) {
    const model = new StudentModel();
    model.id = json['id'];
    model.lastname = json['lastname'];
    model.firstname = json['firstname'];
    model.username = json['username']
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
