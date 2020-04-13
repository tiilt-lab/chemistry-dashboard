import { KeywordUsageModel } from './keyword-usage';

export class TranscriptModel {
  // Server Fields
  id: number;
  session_device_id: number;
  start_time: number;
  length: number;
  question: boolean;
  transcript: string;
  word_count: number;
  direction: number;
  emotional_tone_value: number;
  analytic_thinking_value: number;
  clout_value: number;
  authenticity_value: number;
  certainty_value: number;
  keywords: any[];
  speaker_tag: string;

  static fromJson(json): TranscriptModel {
    const model = new TranscriptModel();
    model.id = json['id'];
    model.session_device_id = json['session_device_id'];
    model.start_time = json['start_time'];
    model.length = json['length'];
    model.question = json['question'];
    model.transcript = json['transcript'];
    model.word_count = json['word_count'];
    model.direction = json['direction'];
    model.emotional_tone_value = json['emotional_tone_value'];
    model.analytic_thinking_value = json['analytic_thinking_value'];
    model.clout_value = json['clout_value'];
    model.authenticity_value = json['authenticity_value'];
    model.certainty_value = json['certainty_value'];
    model.speaker_tag = json['speaker_tag'];
    model.keywords = KeywordUsageModel.fromJsonList(json['keywords']);
    model.keywords.forEach(k => k.transcript_id = model.id);
    return model;
  }

  // Converts JSON to TranscriptModel[]
  static fromJsonList(jsonArray: any): TranscriptModel[] {
    const transcripts = [];
    for (const el of jsonArray) {
      transcripts.push(TranscriptModel.fromJson(el));
    }
    return transcripts;
  }

  static tracker( index: number, transcript: TranscriptModel ): number {
    return transcript.id;
  }
}
