export class FolderModel {
    // Server Fields
    id;
    name;
    owner_id;
    creation_date;
    parent;
    // Sent to admins and supers, who see every account's folders: the owner's
    // email and whether it is the caller's own. Only a super may change one
    // they do not own.
    owner;
    owned;

    static fromJson(json) {
        const model = new FolderModel();
        model.id = json['id'];
        model.name = json['name'];
        model.creation_date = new Date(json['creation_date']);
        model.parent = json['parent'];
        model.owner = json['owner'] != null ? json['owner'] : null;
        model.owned = json['owned'] !== false;
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
