"""YOLO11 object detector (open SOTA successor to the YOLOv4-P7 weights).

Selected via [videoprocessing] object_model=yolo11 in config.ini. Exposes a
single call that takes original BGR frames and returns per-frame detections as
[x1, y1, x2, y2, conf, cls_id] tensors in ORIGINAL frame coordinates plus the
class-name map — the same row layout the attention pipeline's combined_pred
consumes, but already scaled (callers must skip scale_coords for these rows).

Validated standalone on a real pod frame (6 persons, chair, laptop @ 2.3s cold
/ ~20ms warm on the RTX 8000). Person is class 0 in COCO, matching the
pipeline's convention of filtering persons out of the object stream.
"""

import logging
import torch


class Yolo11ObjectDetection:
    def __init__(self, weights="yolo11m.pt", conf=0.35):
        self.weights = weights
        self.conf = conf
        self.model = None
        self.names = {}

    def load(self):
        from ultralytics import YOLO
        self.model = YOLO(self.weights)
        self.names = dict(self.model.names)
        logging.info("YOLO11 object detector loaded (%s)", self.weights)

    def detect(self, frames_bgr):
        """frames_bgr: list of HxWx3 BGR numpy arrays (original size).

        Returns list of (N, 6) float tensors [x1, y1, x2, y2, conf, cls_id]
        in original frame coordinates.
        """
        if self.model is None:
            self.load()
        results = self.model(frames_bgr, conf=self.conf, verbose=False)
        detections = []
        for r in results:
            if r.boxes is None or len(r.boxes) == 0:
                detections.append(torch.zeros((0, 6)))
                continue
            xyxy = r.boxes.xyxy.cpu()
            conf = r.boxes.conf.cpu().unsqueeze(1)
            cls = r.boxes.cls.cpu().unsqueeze(1)
            detections.append(torch.cat((xyxy, conf, cls), dim=1))
        return detections
