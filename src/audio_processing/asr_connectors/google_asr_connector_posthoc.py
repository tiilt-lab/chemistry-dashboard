from .google_asr_connector import GoogleASR as _GoogleASR


class GoogleASR(_GoogleASR):
    """Posthoc variant of the Google ASR connector.

    Identical to the live connector except: the caller supplies the shared
    STOP sentinel, and queue reads block (replaying a recording — there is
    no shutdown-polling need). Kept as its own module so the posthoc
    server's import path is unchanged.
    """

    def __init__(self, audio_queue, transcript_queue, config, mediatype, interval, STOP_SIGNAL):
        super().__init__(audio_queue, transcript_queue, config, mediatype,
                         interval, STOP_SIGNAL, blocking_get=True)
