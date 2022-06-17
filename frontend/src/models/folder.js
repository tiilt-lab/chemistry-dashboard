export class FolderModel {
    // Server Fields
    id;
    name;
    owner_id;
    creation_date;
    parent;

    static fromJson(json) {
        const model = new FolderModel();
        model.id = json['id'];
        model.name = json['name'];
        model.creation_date = new Date(json['creation_date']);
        model.parent = json['parent'];
        return model;
    }

    // Converts JSON to FolderModel[]
    static fromJsonList(jsonArray){
      const folders = [];
      for (const el of jsonArray) {
        folders.push(FolderModel.fromJson(el));
      }
        return folders;
    }
}
