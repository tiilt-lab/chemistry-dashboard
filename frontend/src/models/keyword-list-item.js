export class KeywordListItemModel {
  // Server Fields
  keyword_list_id;
  keyword;

  static fromJson(json){
    const model = new KeywordListItemModel();
    model.keyword_list_id = json['keyword_list_id'];
    model.keyword = json['keyword'];
    return model;
  }

  // Converts JSON to KeywordListItemModel[]
  static fromJsonList(jsonArray){
    const keywordListItems = [];
    for (const el of jsonArray) {
      keywordListItems.push(KeywordListItemModel.fromJson(el));
    }
    return keywordListItems;
  }
}
