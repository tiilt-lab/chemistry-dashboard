# Imports the Google Cloud client library


from google.cloud import speech
import os


def run_quickstart() -> speech.RecognizeResponse:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/var/lib/chemistry-dashboard/audio_processing/asr_connectors/google-cloud-key.json'

    #print(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))
    # Instantiates a client
    client = speech.SpeechClient()
    print(client)
    use_client_cert = os.getenv("GOOGLE_APPLICATION_CREDENTIALS","true")
    #print(use_client_cert)

    # The name of the audio file to transcribe
    gcs_uri = "gs://cloud-samples-data/speech/brooklyn_bridge.raw"

    audio = speech.RecognitionAudio(uri=gcs_uri)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
    )

    # Detects speech in the audio file
    response = client.recognize(config=config, audio=audio)

    for result in response.results:
        print(f"Transcript: {result.alternatives[0].transcript}")

run_quickstart()