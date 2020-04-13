import { stringToDate } from '../globals';

export class UserModel {
  // Server Fields
  id: number;
  email: string;
  role: string;
  creation_date: Date;
  last_login: Date;
  locked: boolean;
  change_password: boolean;
  api_access: boolean;

  get isAdmin(): boolean {
    return this.role === 'admin';
  }

  get isSuper(): boolean {
    return this.role === 'super';
  }

  static fromJson(json): UserModel {
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
  static fromJsonList(jsonArray: any): UserModel[] {
    const userList = [];
    for (const el of jsonArray) {
      userList.push(UserModel.fromJson(el));
    }
    return userList;
  }
}
