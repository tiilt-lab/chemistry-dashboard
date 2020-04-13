export class FolderModel {
    // Server Fields
    id: number;
    name: string;
    owner_id: number;
    creation_date: Date;
    parent: number;

    static fromJson(json): FolderModel {
        const model = new FolderModel();
        model.id = json['id'];
        model.name = json['name'];
        model.creation_date = new Date(json['creation_date']);
        model.parent = json['parent'];
        return model;
    }

    // Converts JSON to FolderModel[]
    static fromJsonList(jsonArray: any): FolderModel[] {
      const folders = [];
      for (const el of jsonArray) {
        folders.push(FolderModel.fromJson(el));
      }
        return folders;
    }
}
