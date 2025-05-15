from google.cloud import speech
from scipy.io.wavfile import read, write
from jiwer import wer
from pydub import AudioSegment
from pydub.utils import make_chunks
import io
import numpy as np


def data_to_bytes(file):
    with open(file, "rb") as wavfile:
        input_wav = wavfile.read()

    rate, data = read(io.BytesIO(input_wav))
    data0 = data[:, 0].astype(np.int16)
    write("file_name_byte.wav", rate, data)


def get_asr_transcribed_text(data):

    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=data)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        audio_channel_count = 1,
    )

    response = client.recognize(config=config, audio=audio)
    all_result = ''
    for result in response.results:
        all_result += result.alternatives[0].transcript
        # print("Transcript: {}".format(result.alternatives[0].transcript))
    return all_result.lower()


def make_audio_chunks(file):
    myAudio = AudioSegment.from_file(file)
    chunk_length_ms = 16000
    chunks = make_chunks(myAudio, chunk_length_ms)
    transcribed = ""
    for i, chunk in enumerate(chunks):
        text = get_asr_transcribed_text(chunk._data)
        transcribed += text
    return transcribed

'''
if __name__=="__main__":
    file = "2022_2.wav"
    hypothesis = make_audio_chunks(file)
    test_2022_2 = "hello hello bla bla bla and I think it is picking it is up banana you wanna go to the gym later to workout yeah yeah blob after we go to the gym can we go to the target yes we can go to the target after the gym hmm that is pretty cool yeah do you want to go to a place in pool i am going to beat you in pool yes i am wait make your voice sound emotional emotional say something emotional i lost my banana oh no i cant go to the gym okay okay so"
    word_error_rate = wer(test_2022_2, hypothesis)
    print(word_error_rate)
'''
