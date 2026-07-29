"""PAGE gaze target estimation (Ye et al., arXiv 2607.04860, July 2026).

Claimed successor to Gaze-LLE — human-level on GazeFollow/VAT/ChildPlay in the
authors' own evaluation, not yet independently verified. Selectable per
post-hoc run via the trigger UI's "Attention / gaze" selector (id
'page-vith+'); the deployment default stays Gaze-LLE.

The released checkpoints are self-contained HuggingFace models (safetensors
include the DINOv3 backbone; structure loads via trust_remote_code) — see
vendor/PaGE/scripts/inference.py, which this adapter mirrors. Install:

    hf download Octopus1/page-vithplus --local-dir pretrained_models/page-vithplus

(needs HF_TOKEN; ~several GB). Subclasses the Gaze-LLE adapter so the
64x64-heatmap argmax, in/out threshold, and object-of-focus geometry are
reused unchanged; only model loading and the forward pass differ. PAGE's HF
processor does its own preprocessing from PIL images, so the pipeline's
batched tensors are ignored and inference runs per head from the stashed
frames — slower than Gaze-LLE, acceptable for an experimental re-analysis.
"""

import logging
import os

import numpy as np
import torch

from .gazelle_attention import GazeLLEAttentionDetection

_CHECKPOINT_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', '..', 'pretrained_models', 'page-vithplus'))

_INSTALL_HINT = (
    "PAGE ViT-H+ is not installed on this deployment. To enable it: "
    "1) hf download Octopus1/page-vithplus --local-dir "
    "pretrained_models/page-vithplus (needs HF_TOKEN); "
    "2) ensure `transformers` and `safetensors` are installed in the video "
    "service venv. Then re-run. Falling back is deliberate-only — pick "
    "Gaze-LLE in the selector to proceed without PAGE."
)


class PageAttentionDetection(GazeLLEAttentionDetection):

    def init_model(self, batch_size):
        self.batch_size = batch_size
        if not os.path.isdir(_CHECKPOINT_DIR):
            raise RuntimeError(
                "PAGE checkpoint directory missing ({0}). {1}".format(
                    _CHECKPOINT_DIR, _INSTALL_HINT))
        try:
            from transformers import AutoModel, AutoImageProcessor
        except ImportError as e:
            raise RuntimeError(
                "transformers is not available in the video service "
                "environment. {0}".format(_INSTALL_HINT)) from e
        self.model = (AutoModel.from_pretrained(
            _CHECKPOINT_DIR, trust_remote_code=True)
            .eval().to(self.device))
        self.processor = AutoImageProcessor.from_pretrained(
            _CHECKPOINT_DIR, trust_remote_code=True)
        # The pipeline's DataLoader still stacks frame/face tensors; PAGE
        # ignores them (its HF processor consumes PIL directly), but the
        # transform must exist for the batching dataset to run.
        from torchvision import transforms
        self.transform = transforms.Compose(
            [transforms.Resize((448, 448)), transforms.ToTensor()])
        logging.info("PAGE attention model loaded (ViT-H+) from %s",
                     _CHECKPOINT_DIR)

    def get_batched_facial_data(self, person_detail, frames):
        out = super().get_batched_facial_data(person_detail, frames)
        _, _, _, headbox, imsize, frame_ids, _ = out
        # Stash the raw scenes + head boxes in dataset order; the tensors the
        # base pipeline hands to compute_gaze_direction are ignored for PAGE.
        pending = []
        for i in range(len(headbox)):
            frame = frames[int(frame_ids[i])]
            x1, y1, x2, y2 = [float(v) for v in headbox[i]]
            w, h = float(imsize[i][0]), float(imsize[i][1])
            pixel_bbox = (max(0, int(x1)), max(0, int(y1)),
                          min(int(w), int(x2)), min(int(h), int(y2)))
            pending.append((frame, pixel_bbox,
                            (x1 / w, y1 / h, x2 / w, y2 / h)))
        self._pending_pages = pending
        return out

    @staticmethod
    def _to_device(obj, device):
        if isinstance(obj, torch.Tensor):
            return obj.to(device)
        if isinstance(obj, dict):
            return {k: PageAttentionDetection._to_device(v, device)
                    for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            moved = [PageAttentionDetection._to_device(v, device) for v in obj]
            return type(obj)(moved) if isinstance(obj, tuple) else moved
        return obj

    def compute_gaze_direction(self, val_img, val_face, val_head_channel):
        from PIL import Image
        heatmaps, inouts = [], []
        with torch.inference_mode():
            for frame, pixel_bbox, norm_bbox in self._pending_pages[:len(val_img)]:
                scene = Image.fromarray(frame)
                left, top, right, bottom = pixel_bbox
                if right <= left or bottom <= top:
                    heatmaps.append(torch.zeros(64, 64))
                    inouts.append(0.0)
                    continue
                inputs = self.processor(
                    scene,
                    head_crops=[scene.crop((left, top, right, bottom))],
                    bboxes=[[norm_bbox]])
                inputs = self._to_device(inputs, self.device)
                out = self.model(inputs)
                hm = out["heatmap"][0]
                hm = (hm.detach().float() if isinstance(hm, torch.Tensor)
                      else torch.as_tensor(np.asarray(hm), dtype=torch.float32))
                heatmaps.append(hm.squeeze())
                io_p = out["inout"][0]
                io_p = (float(io_p.detach().float().squeeze())
                        if isinstance(io_p, torch.Tensor)
                        else float(np.asarray(io_p).squeeze()))
                inouts.append(io_p)
        # Same contract as Gaze-LLE: (heatmaps, attmaps, inout probabilities);
        # get_gaze_direction_point is inherited unchanged.
        return heatmaps, None, inouts
