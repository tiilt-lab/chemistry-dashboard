"""A pod's clock on the session timeline.

The audio service stamps every utterance as ``config.start_offset`` (set when
the pod's start message arrives: seconds since the session clock began) plus
the utterance's position in the audio received, counted in samples. Nothing
else ever checked that clock against real time, and three things move it:

* audio that begins after the start message (the microphone prompt, the
  group pressing Start a little later) -- those seconds never arrive as
  samples, so the pod's stamps run early by the gap for the whole session;
* a stalled capture (a throttled tab, a busy laptop) sends fewer samples
  than real time passes, so the stamps drift early;
* a network hiccup holds frames back and delivers them in a burst: real
  time runs ahead for a while and the burst catches up, so nothing should
  move.

Group 1 on 2026-10-16 ran 18 s apart from its partner laptop for half an
hour, then 5 s; the coding merge could not pair the two transcripts.

ClockAnchor sees every audio frame's arrival time and the audio seconds
received so far and decides when ``start_offset`` must move: at the first
frame, by however late it came; and later, by a drift that has stayed past
RE_ANCHOR_THRESHOLD for RE_ANCHOR_SUSTAIN seconds (a hiccup that catches up
within that time moves nothing). Audio running ahead of real time is only
corrected back as far as earlier corrections went: a backlog the client
replays after a reconnect is audio from the past and belongs where its
samples put it. Pure: no Twisted, no Redis, so the rules are unit-testable.
"""

LATE_START_MIN = 0.5        # s: a first frame later than this moves the anchor
RE_ANCHOR_THRESHOLD = 1.0   # s: drift past this, sustained, is a stall rather than jitter
RE_ANCHOR_SUSTAIN = 8.0     # s: how long the drift must hold before the clock moves


class ClockAnchor(object):
    def __init__(self, started_at):
        # Wall-clock seconds (time.time()) when the start message arrived:
        # the moment start_offset was computed for.
        self.started_at = float(started_at)
        self.first_frame_at = None
        self.late_start = 0.0     # s the first frame came after the start message
        self.corrected = 0.0      # s added to start_offset by re-anchoring so far
        self.drift = 0.0          # s audio currently lags real time (negative: leads)
        self._over_since = None   # when the drift last crossed the threshold ...
        self._over_sign = 0       # ... and in which direction

    def first_frame(self, now):
        """Seconds to add to start_offset: the first audio frame arrived this
        long after the start message (0 when within LATE_START_MIN)."""
        self.first_frame_at = float(now)
        late = max(0.0, self.first_frame_at - self.started_at)
        if late < LATE_START_MIN:
            return 0.0
        self.late_start = late
        return late

    def frame(self, audio_seconds, now):
        """Seconds to add to start_offset after this frame, usually 0.
        ``audio_seconds``: audio received so far, this frame included."""
        if self.first_frame_at is None:
            return 0.0
        wall = float(now) - self.first_frame_at
        self.drift = wall - float(audio_seconds) - self.corrected
        behind = self.drift > RE_ANCHOR_THRESHOLD
        ahead = self.drift < -RE_ANCHOR_THRESHOLD and self.corrected > 0.0
        if not (behind or ahead):
            self._over_since = None
            return 0.0
        sign = 1 if behind else -1
        if self._over_since is None or sign != self._over_sign:
            self._over_since, self._over_sign = float(now), sign
            return 0.0
        if float(now) - self._over_since < RE_ANCHOR_SUSTAIN:
            return 0.0
        delta = self.drift if behind else max(self.drift, -self.corrected)
        self.corrected += delta
        self.drift -= delta
        self._over_since = None
        return delta

    def snapshot(self):
        """What the Devices tab shows for this pod (live_presence.set_clock)."""
        return {"drift": round(self.drift, 1), "corrected": round(self.corrected, 1),
                "late_start": round(self.late_start, 1)}
