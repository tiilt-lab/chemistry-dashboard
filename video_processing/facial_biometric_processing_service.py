import logging
import threading
import moviepy.editor as mp
import  cv2
import face_recognition
import numpy as np
import json
import os

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
        embeddings = []
        student_embedding = {}

        vidclip = mp.VideoFileClip(video_file+'.'+mediaExt)
        for frame in vidclip.iter_frames(fps=5, dtype="uint8"):
            # Detect face locations in the frame
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(frame)

            # Get 128-D face embeddings for each detected face
            encodings = face_recognition.face_encodings(frame, face_locations,num_jitters=2)
        
            if len(encodings) > 0:
                embeddings.append(encodings[0])  # Take first detected face

        if len(embeddings) == 0:
            self.send_json({'type': 'error', 'message': "Facial capuring failed, please record yourself again with better lighting"})

        # Compute average embedding
        avg_embedding = np.mean(embeddings, axis=0)
        student_embedding[currAlias] = avg_embedding
        np.save(facial_biometric_file+".npy", student_embedding)

        if os.path.isfile(video_file+'.'+mediaExt):
            os.remove(video_file+'.'+mediaExt)

        logging.info('video biometrics saved')
        self.send_json({'type': 'saved', 'message': "Biometric data captured successfully"})   

        return
