from pydub import AudioSegment
from pydub.utils import make_chunks

def make_audio_chunks(audio):
    myAudio = AudioSegment.from_file(audio)
    chunk_length_ms = 16000
    chunks = make_chunks(myAudio, chunk_length_ms)
    for i, chunk in enumerate(chunks):
        chunk_name = "2022_2_chunk{0}.wav".format(i)
        print("exporting " + chunk_name)
        chunk.export(chunk_name, format="wav")

if __name__=="__main__":
    audio = "file_name.wav"
    make_audio_chunks(audio)

