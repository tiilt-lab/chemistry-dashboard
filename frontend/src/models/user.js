import { stringToDate } from '../globals';

export class UserModel {
  // Server Fields
  id;
  email;
  role;
  creation_date;
  last_login;
  locked;
  change_password;
  api_access;

  get isAdmin() {
    return this.role === 'admin';
  }

  get isSuper() {
    return this.role === 'super';
  }

  static fromJson(json) {
    const model = new UserModel();
    model.id = json['id'];
    model.email = json['email'];
    model.role = json['role'];
    model.creation_date = stringToDate(json['creation_date']);
    model.last_login = stringToDate(json['last_login']);
    model.locked = json['locked'];
    model.change_password = json['change_password'];
    model.api_access = json['api_access'];
    return model;
  }

  // Converts JSON to UserModel[]
  static fromJsonList(jsonArray) {
    const userList = [];
    for (const el of jsonArray) {
      userList.push(UserModel.fromJson(el));
    }
    return userList;
  }
}
