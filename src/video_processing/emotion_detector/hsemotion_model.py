"""HSEmotion facial-expression model (open source, AffectNet-trained).

Drop-in alternative to EmotionDetectionModelV1 (ResMaskingNet / FER-2013,
2019). HSEmotion (Savchenko) is an EfficientNet-B2 trained on AffectNet-8 —
substantially more accurate than FER-2013-era models — run through ONNX
Runtime so it needs no torch checkpoint unpickling. Selected via the
[videoprocessing] emotion_model=hsemotion config key.

Emits the same lowercase label vocabulary the dashboard already stores;
AffectNet's extra classes map onto the nearest existing label (anger->angry,
contempt->serious).
"""

import logging
import cv2

_AFFECTNET_TO_DASHBOARD = {
    "Anger": "angry",
    "Contempt": "serious",
    "Disgust": "disgust",
    "Fear": "fear",
    "Happiness": "happy",
    "Neutral": "neutral",
    "Sadness": "sad",
    "Surprise": "surprise",
}


class EmotionDetectionModelV2:
    def __init__(self, model_name="enet_b2_8"):
        self.model_name = model_name
        self.recognizer = None

    def load_model(self):
        from hsemotion_onnx.facial_emotions import HSEmotionRecognizer
        self.recognizer = HSEmotionRecognizer(model_name=self.model_name)
        print('HSEmotion model {0} loaded successfully.'.format(self.model_name))

    def predict_facial_emotion(self, image):
        try:
            if self.recognizer is None:
                self.load_model()
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            emotion, _scores = self.recognizer.predict_emotions(rgb, logits=False)
            return _AFFECTNET_TO_DASHBOARD.get(emotion, emotion.lower())
        except Exception as e:
            logging.info('EmotionDetectionModelV2: exception while predicting facial emotion: {0}'.format(e))

    def set_persistent_variables(self, persons_emotions_detected):
        self.persons_emotions_detected = persons_emotions_detected

    def predict_facial_emotion_for_all_participants(self, frames, faces, crop_face_from_fame_with_bbox):
        for alias, person_detail in faces:
            for face_detail_by_frame in person_detail:
                frame_index, alias, bbox, time_stamp = face_detail_by_frame
                try:
                    face = crop_face_from_fame_with_bbox(frames[frame_index], bbox, "xyxy", False, 0.0, False)
                    emotion_name = self.predict_facial_emotion(face)
                    if alias in self.persons_emotions_detected:
                        self.persons_emotions_detected[alias].append([time_stamp, emotion_name])
                    else:
                        self.persons_emotions_detected[alias] = [[time_stamp, emotion_name]]
                except Exception as e:
                    logging.info('EmotionDetectionModelV2: exception for {0} in frame {1}: {2}'.format(alias, frame_index, e))

    def predict_facial_emotion_for_single_participant(self, image, bbox, alias, frame_index, crop_face_from_fame_with_bbox):
        try:
            face = crop_face_from_fame_with_bbox(image, bbox, "xyxy", False, 0.0, False)
            return self.predict_facial_emotion(face)
        except Exception as e:
            logging.info('EmotionDetectionModelV2: exception for {0} in frame {1}: {2}'.format(alias, frame_index, e))
