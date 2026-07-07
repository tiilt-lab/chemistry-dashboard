import logging
import threading
try:
    import moviepy.editor as mp  # moviepy 1.x
except ImportError:
    import moviepy as mp  # moviepy 2.x dropped the .editor module
import  cv2
import numpy as np
import json
import os
from facial_recognition_backend import get_face_backend

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
        embeddings = []
        student_embedding = {}
        face_backend = get_face_backend()

        # Coached recordings run up to 60s now (previously 10s). Encoding
        # every frame at 5fps with jitters takes minutes on CPU, so sample at
        # most MAX_FRAMES frames spread across the whole clip — head turns
        # from every part of the script still contribute.
        MAX_FRAMES = 40
        vidclip = mp.VideoFileClip(video_file+'.'+mediaExt)
        duration = float(vidclip.duration or 0)
        fps = 2 if duration <= 0 else min(2.0, MAX_FRAMES / max(duration, 1.0))
        frames = list(vidclip.iter_frames(fps=max(fps, 0.5), dtype="uint8"))
        if len(frames) > MAX_FRAMES:
            step = len(frames) / MAX_FRAMES
            frames = [frames[int(i * step)] for i in range(MAX_FRAMES)]
        for frame in frames:
            # Detect face locations in the frame
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_backend.locate(frame)

            # Face embeddings for each detected face (backend-specific dimension)
            encodings = face_backend.encode(frame, face_locations, num_jitters=2)

            if len(encodings) > 0:
                embeddings.append(encodings[0])  # Take first detected face

        if len(embeddings) == 0:
            self.send_json({'type': 'error', 'message': "No face could be captured — please record again with your face visible and better lighting."})
            return

        # Compute average embedding
        avg_embedding = np.mean(embeddings, axis=0)
        student_embedding[currAlias] = avg_embedding
        np.save(facial_biometric_file+".npy", student_embedding)

        logging.info('video biometrics saved (%d face samples)', len(embeddings))
        self.send_json({'type': 'saved', 'message': "Biometric data captured successfully"})
