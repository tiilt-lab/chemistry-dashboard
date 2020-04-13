import { stringToDate } from '../globals';

export class SessionModel {
  // Server Fields
  id: number;
  name: string;
  creation_date: Date;
  end_date: Date;
  passcode: string;
  keywords: string[];
  folder: number;

  // Client Fields
  local_start_date: Date;

  get recording(): boolean {
    return (this.end_date == null);
  }

  get length(): number {
    if (this.end_date != null) {
      return Math.floor((this.end_date.getTime() - this.creation_date.getTime()) / 1000);
    } else {
      return Math.floor((Date.now() - this.local_start_date.getTime()) / 1000);
    }
  }

  get title(): string {
    return (this.name == null) ? 'Session' : this.name;
  }

  get lengthFormatted(): string {
    const h = Math.floor(this.length / 60 / 60);
    const m = Math.floor((this.length - (h * 60 * 60)) / 60);
    const s = Math.floor(this.length - (m * 60) - (h * 60 * 60));
    let result = '';
    result += h.toString().padStart(2, '0') + ':';
    result += m.toString().padStart(2, '0') + ':';
    result += s.toString().padStart(2, '0');
    return result;
  }

  get formattedDate(): string {
    const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: 'numeric' };
    let dateString = this.creation_date.toLocaleDateString('en-US', options);
    dateString += ' (' + this.lengthFormatted + ')';
    return dateString;
  }

  static fromJson(json): SessionModel {
    const model = new SessionModel();
    model.id = json['id'];
    model.name = json['name'];
    model.creation_date = stringToDate(json['creation_date']);
    if (json['end_date'] != null) {
      model.end_date = stringToDate(json['end_date']);
    }
    model.local_start_date = new Date();
    model.local_start_date.setSeconds(model.local_start_date.getSeconds() - json['length']);
    model.passcode = json['passcode'];
    model.keywords = json['keywords'];
    model.folder = json['folder']
    return model;
  }

  // Converts JSON to SessionModel[]
  static fromJsonList(jsonArray: any): SessionModel[] {
    const sessions = [];
    for (const el of jsonArray) {
      sessions.push(SessionModel.fromJson(el));
    }
    return sessions;
  }
}
