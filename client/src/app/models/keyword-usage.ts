export class KeywordUsageModel {
  // Server Fields
  id: number;
  transcript_id: number;
  word: string;
  keyword: string;
  similarity: number;

  static fromJson(json): KeywordUsageModel {
    const model = new KeywordUsageModel();
    model.id = json['id'];
    model.transcript_id = json['transcript_id'];
    model.word = json['word'];
    model.keyword = json['keyword'];
    model.similarity = +((1.0 - json['similarity']) * 100).toFixed(2);
    return model;
  }

  // Converts JSON to KeywordUsageModel[]
  static fromJsonList(jsonArray: any): KeywordUsageModel[] {
    const keywordUsages = [];
    for (const el of jsonArray) {
      keywordUsages.push(KeywordUsageModel.fromJson(el));
    }
    return keywordUsages;
  }
}
