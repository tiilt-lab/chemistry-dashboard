"""Gaze-LLE attention/gaze model (open SOTA, Meta 2024).

Drop-in successor to the 2020 GazeFollow ModelSpatial, selected via
[videoprocessing] attention_model=gazelle. Subclasses AttentionDetection so
the object-of-focus geometry, attention-level tracking and the batching
dataset are reused unchanged; only the transform and the gaze inference are
replaced. Gaze-LLE predicts from DINOv2 features of the full frame plus a
normalized head box — no face crop or head-position channel needed, so those
batch tensors are simply ignored.

Validated standalone on a real pod frame: 0.41s/frame batch-of-1, in-frame
probability 0.95, plausible gaze target. Weights via torch.hub (fkryan/gazelle
+ facebookresearch/dinov2 backbone pinned to a py3.9-compatible revision in
the hub cache).
"""

import logging
import numpy as np
import torch

from .attention_tracking import AttentionDetection


class GazeLLEAttentionDetection(AttentionDetection):
    def __init__(self):
        super().__init__()
        # Gaze-LLE outputs 64x64 heatmaps, same as ModelSpatial, so the
        # downstream argmax/scale math is unchanged.
        self._hub_transform = None
        # inout is a 0..1 in-frame probability (1 = looking inside the frame).
        self.inout_threshold = 0.5

    def init_model(self, batch_size):
        self.batch_size = batch_size
        model, transform = torch.hub.load('fkryan/gazelle', 'gazelle_dinov2_vitb14_inout')
        self.model = model.cuda().to(self.device).eval()
        self._hub_transform = transform
        self.transform = self._wrapped_transform
        logging.info("Gaze-LLE attention model loaded (dinov2_vitb14_inout)")

    def _wrapped_transform(self, pil_image):
        # AttentionFlow applies self.transform to BOTH the full frame and the
        # face crop; Gaze-LLE only consumes the frame, but the face tensor
        # must still stack in the DataLoader, so transform it the same way.
        return self._hub_transform(pil_image)

    def get_batched_facial_data(self, person_detail, frames):
        out = super().get_batched_facial_data(person_detail, frames)
        val_img, val_face, val_head_channel, headbox, imsize, frame_id, time_stamp = out
        # Stash normalized head boxes for compute_gaze_direction (the pipeline
        # does not pass them there). One scheduler thread per batch.
        boxes = []
        for i in range(len(headbox)):
            x1, y1, x2, y2 = [float(v) for v in headbox[i]]
            w, h = float(imsize[i][0]), float(imsize[i][1])
            boxes.append((x1 / w, y1 / h, x2 / w, y2 / h))
        self._pending_bboxes = boxes
        return out

    def compute_gaze_direction(self, val_img, val_face, val_head_channel):
        with torch.no_grad():
            images = val_img.cuda().to(self.device)
            bboxes = [[b] for b in self._pending_bboxes[:len(images)]]
            out = self.model({"images": images, "bboxes": bboxes})
        heatmaps = [out["heatmap"][i][0] for i in range(len(images))]
        inouts = [out["inout"][i][0] for i in range(len(images))]
        return heatmaps, None, inouts

    def get_gaze_direction_point(self, val_gaze_heatmap_pred, val_inout_pred, imsize):
        with torch.no_grad():
            heatmap = val_gaze_heatmap_pred.cpu().numpy()
            inout = float(val_inout_pred)
            width, height = int(imsize[0]), int(imsize[1])
            if inout < self.inout_threshold:
                return None, None  # looking outside the frame
            flat_index = int(np.argmax(heatmap))
            gy, gx = divmod(flat_index, heatmap.shape[1])
            return (int((gx / heatmap.shape[1]) * width),
                    int((gy / heatmap.shape[0]) * height))
