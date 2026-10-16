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

The browser also reports, in its start message, how many seconds of audio
it has queued and is about to replay (its pre-Start buffer, or what it held
through a reconnect), and start_offset is reduced by that much so the
replay lands in the past where it belongs. On 2026-10-16 that promise was
broken for three of six groups: the frames of the replay arrived while the
service was still setting the stream up and were discarded, so the clock
had been moved back by up to 196 s for audio that never counted. Groups
2, 4 and 6 ran 260, 108 and 191 s apart from their partner laptops.

ClockAnchor sees every audio frame's arrival time and the audio seconds
received so far and decides when ``start_offset`` must move: at the first
frame, by however late it came; by every second of audio the service had to
discard before it was ready (promised in the report, never counted); and
later, by a drift that has stayed past RE_ANCHOR_THRESHOLD for
RE_ANCHOR_SUSTAIN seconds once the replay has settled (a hiccup that
catches up within that time moves nothing). The reported backlog is the
expected lead of audio over real time, so after the replay the audio should
run exactly that far ahead; a sustained shortfall or excess is corrected in
either direction. Pure: no Twisted, no Redis, so the rules are
unit-testable.
"""

LATE_START_MIN = 0.5        # s: a first frame later than this moves the anchor
RE_ANCHOR_THRESHOLD = 1.0   # s: drift past this, sustained, is a stall rather than jitter
RE_ANCHOR_SUSTAIN = 8.0     # s: how long the drift must hold before the clock moves
SETTLE_MIN_SECONDS = 5.0    # s: no drift judgement before this much real time has passed ...
SETTLE_WINDOW = 5.0         # s: ... or while the audio lead still grew by more than
SETTLE_LEAD_GROWTH = 1.0    # s over the last SETTLE_WINDOW (a replay still arriving)


class ClockAnchor(object):
    def __init__(self, started_at, reported_backlog=0.0):
        # Wall-clock seconds (time.time()) when the start message arrived:
        # the moment start_offset was computed for. ``reported_backlog``: the
        # seconds of queued audio the browser said it would replay, already
        # taken off start_offset, so the audio is expected to lead real time
        # by that much once the replay is in.
        self.started_at = float(started_at)
        self.expected_lead = max(0.0, float(reported_backlog or 0.0))
        self.first_frame_at = None
        self.late_start = 0.0     # s the first frame came after the start message
        self.discarded = 0.0      # s of audio the service dropped before it was ready
        self.corrected = 0.0      # s added to start_offset by re-anchoring so far
        self.drift = 0.0          # s audio currently lags where it should be (negative: leads)
        self._over_since = None   # when the drift last crossed the threshold ...
        self._over_sign = 0       # ... and in which direction
        self._leads = []          # recent (now, lead) samples for the settle check

    def first_frame(self, now):
        """Seconds to add to start_offset: the first audio frame arrived this
        long after the start message (0 when within LATE_START_MIN)."""
        self.first_frame_at = float(now)
        late = max(0.0, self.first_frame_at - self.started_at)
        if late < LATE_START_MIN:
            return 0.0
        self.late_start = late
        return late

    def discard(self, audio_seconds):
        """Seconds to add to start_offset: the service received, but could not
        count, this much audio (it arrived before the stream was ready). The
        browser's report promised it, so the clock had been moved back for
        it already."""
        if audio_seconds <= 0:
            return 0.0
        self.discarded += float(audio_seconds)
        self.expected_lead = max(0.0, self.expected_lead - float(audio_seconds))
        return float(audio_seconds)

    def _settled(self, now, lead):
        # No judgement while a replay may still be arriving: within the first
        # seconds, or while the lead over real time still grows quickly.
        self._leads.append((float(now), lead))
        cutoff = float(now) - SETTLE_WINDOW
        while len(self._leads) > 1 and self._leads[1][0] <= cutoff:
            self._leads.pop(0)
        if float(now) - self.first_frame_at < SETTLE_MIN_SECONDS:
            return False
        return lead - self._leads[0][1] <= SETTLE_LEAD_GROWTH

    def frame(self, audio_seconds, now):
        """Seconds to add to start_offset after this frame, usually 0.
        ``audio_seconds``: audio received so far, this frame included."""
        if self.first_frame_at is None:
            return 0.0
        wall = float(now) - self.first_frame_at
        lead = float(audio_seconds) - wall
        # Where the audio should be: leading real time by the backlog the
        # browser promised (less whatever had to be discarded), plus any
        # earlier correction.
        self.drift = self.expected_lead - lead - self.corrected
        if not self._settled(now, lead):
            self._over_since = None
            return 0.0
        behind = self.drift > RE_ANCHOR_THRESHOLD
        ahead = self.drift < -RE_ANCHOR_THRESHOLD
        if not (behind or ahead):
            self._over_since = None
            return 0.0
        sign = 1 if behind else -1
        if self._over_since is None or sign != self._over_sign:
            self._over_since, self._over_sign = float(now), sign
            return 0.0
        if float(now) - self._over_since < RE_ANCHOR_SUSTAIN:
            return 0.0
        delta = self.drift
        self.corrected += delta
        self.drift = 0.0
        self._over_since = None
        return delta

    def snapshot(self):
        """What the Devices tab shows for this pod (live_presence.set_clock)."""
        return {"drift": round(self.drift, 1), "corrected": round(self.corrected, 1),
                "late_start": round(self.late_start, 1), "discarded": round(self.discarded, 1)}
