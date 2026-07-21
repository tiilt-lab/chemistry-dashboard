import logging
import threading
import time
try:
    import moviepy.editor as mp  # moviepy 1.x
except ImportError:
    import moviepy as mp  # moviepy 2.x dropped the .editor module
import  cv2
import numpy as np
import json
import os
from facial_recognition_backend import get_backend_by_name


def _sample_frames(video_path, max_frames):
    """RGB frames spread across the whole clip (head turns from every part of
    the recording contribute)."""
    vidclip = mp.VideoFileClip(video_path)
    duration = float(vidclip.duration or 0)
    fps = 2 if duration <= 0 else min(2.0, max_frames / max(duration, 1.0))
    frames = list(vidclip.iter_frames(fps=max(fps, 0.5), dtype="uint8"))
    if len(frames) > max_frames:
        step = len(frames) / max_frames
        frames = [frames[int(i * step)] for i in range(max_frames)]
    return [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in frames]


def build_face_embeddings(video_path, max_frames=40, dlib_frames=12):
    """Dual-backend enrollment embeddings from one clip. Pure + import-free of
    the websocket plumbing so it can be tested standalone.

    ArcFace (GPU, ~seconds) runs over ALL sampled frames and is the
    forward-looking gallery entry (.arc.npy — same convention the ASD path
    and gallery minting use). Dlib (CPU, the slow one) runs over a SUBSET
    with jitter off, only to keep the deployed 128-D live matcher working
    for this student until the whole gallery migrates. Returns
    (arc_vec_512 | None, dlib_vec_128 | None, timings_dict).
    """
    frames = _sample_frames(video_path, max_frames)
    timings = {"frames": len(frames)}

    t0 = time.time()
    arc = get_backend_by_name("insightface")
    arc_embs = []
    for frame in frames:
        encs = arc.encode(frame, arc.locate(frame))
        if encs:
            arc_embs.append(encs[0])
    arc_vec = None
    if arc_embs:
        v = np.mean(arc_embs, axis=0)
        arc_vec = (v / (np.linalg.norm(v) + 1e-9)).astype(np.float32)
    timings["arcface_s"] = round(time.time() - t0, 1)
    timings["arcface_faces"] = len(arc_embs)

    t0 = time.time()
    dlib = get_backend_by_name("dlib")
    # Prefer frames ArcFace saw a face in; jitters off — averaging a dozen
    # frames of a coached head-turn clip replaces what jitter augmentation
    # bought on single stills, at a fraction of the CPU time.
    subset = frames[:: max(1, len(frames) // dlib_frames)][:dlib_frames]
    dlib_embs = []
    for frame in subset:
        encs = dlib.encode(frame, dlib.locate(frame), num_jitters=1)
        if encs:
            dlib_embs.append(encs[0])
    dlib_vec = np.mean(dlib_embs, axis=0) if dlib_embs else None
    timings["dlib_s"] = round(time.time() - t0, 1)
    timings["dlib_faces"] = len(dlib_embs)
    return arc_vec, dlib_vec, timings

class FacialBiometricProcessor:
    def __init__(self,facial_biometric_file,video_file,mediaExt,currAlias):
        self.facial_biometric_file = facial_biometric_file
        self.video_file = video_file
        self.mediaExt = mediaExt
        self.currAlias = currAlias
        self.web_socket_connection = None

    def start(self):
        self.facial_embedding_pro_thread = threading.Thread(target=self.savefacialembedding,args=(self.facial_biometric_file,self.video_file,self.mediaExt,self.currAlias), name="FacialEmbeddingProcessor")
        self.facial_embedding_pro_thread.daemon = True
        self.facial_embedding_pro_thread.start()
        

    def add_websocket_connection(self,web_socket):
        self.web_socket_connection = web_socket

    def send_json(self, message):
        payload = json.dumps(message).encode('utf8')
        self.web_socket_connection.sendMessage(payload, isBinary = False)

    def savefacialembedding(self,facial_biometric_file,video_file,mediaExt,currAlias):
        # Runs on a daemon thread: any uncaught exception used to kill it
        # silently and the sign-up page waited on "Processing…" forever.
        try:
            self._savefacialembedding(facial_biometric_file, video_file, mediaExt, currAlias)
        except Exception as e:
            logging.warning('facial biometric processing failed: %s', e, exc_info=True)
            try:
                self.send_json({'type': 'error',
                                'message': 'Processing the video failed on the server. Please try again.'})
            except Exception:
                pass

    def _savefacialembedding(self,facial_biometric_file,video_file,mediaExt,currAlias):
        arc_vec, dlib_vec, timings = build_face_embeddings(
            video_file + '.' + mediaExt)
        logging.info('face embedding timings for %s: %s', currAlias, timings)

        if arc_vec is None and dlib_vec is None:
            self.send_json({'type': 'error', 'message': "No face could be captured — please record again with your face visible and better lighting."})
            return

        # ArcFace 512 — the forward-looking gallery entry (same .arc.npy
        # convention as the ASD identify path and gallery minting).
        if arc_vec is not None:
            np.save(facial_biometric_file + ".arc.npy", arc_vec)
        # dlib 128, legacy dict format — keeps the deployed live matcher
        # working for this student until the whole gallery migrates.
        if dlib_vec is not None:
            np.save(facial_biometric_file + ".npy", {currAlias: dlib_vec})

        logging.info('video biometrics saved (arc:%s dlib:%s)',
                     timings.get("arcface_faces"), timings.get("dlib_faces"))
        self.send_json({'type': 'saved', 'message': "Biometric data captured successfully"})
