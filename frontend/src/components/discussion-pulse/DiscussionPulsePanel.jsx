import React, { useState, useEffect, useRef } from 'react';
import style from './discussion-pulse.module.css';

/**
 * Discussion Pulse Panel - Lyrics-style scrollable feed of discussion summaries.
 * Shows periodic summaries with topics, auto-scrolls to latest during active sessions.
 */
function DiscussionPulsePanel({ sessionDeviceId, isSessionActive, isCollapsed, onToggleCollapse }) {
  const [pulses, setPulses] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollContainerRef = useRef(null);
  const lastPulseRef = useRef(null);

  // Load initial pulses
  useEffect(() => {
    if (!sessionDeviceId) return;

    setIsLoading(true);
    fetch(`/api/v1/discussion-pulse/${sessionDeviceId}`)
      .then(res => res.json())
      .then(data => {
        setPulses(data.pulses || []);
        setIsLoading(false);
      })
      .catch(err => {
        console.error('Error loading pulses:', err);
        setIsLoading(false);
      });
  }, [sessionDeviceId]);

  // Poll for new pulses during active session
  useEffect(() => {
    if (!sessionDeviceId || !isSessionActive) return;

    const pollInterval = setInterval(() => {
      const lastTime = pulses.length > 0
        ? pulses[pulses.length - 1].end_time
        : 0;

      fetch(`/api/v1/discussion-pulse/${sessionDeviceId}/poll?since=${lastTime}`)
        .then(res => res.json())
        .then(data => {
          if (data.pulses && data.pulses.length > 0) {
            setPulses(prev => [...prev, ...data.pulses]);
          }
        })
        .catch(err => console.error('Poll error:', err));
    }, 10000); // Poll every 10 seconds

    return () => clearInterval(pollInterval);
  }, [sessionDeviceId, isSessionActive, pulses]);

  // Auto-scroll to latest pulse
  useEffect(() => {
    if (autoScroll && lastPulseRef.current) {
      lastPulseRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [pulses, autoScroll]);

  // Handle manual scroll to disable auto-scroll
  const handleScroll = () => {
    if (!scrollContainerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    if (!isAtBottom && autoScroll) {
      setAutoScroll(false);
    } else if (isAtBottom && !autoScroll) {
      setAutoScroll(true);
    }
  };

  // Trigger manual pulse generation
  const handleGeneratePulse = () => {
    if (!sessionDeviceId) return;

    fetch(`/api/v1/discussion-pulse/${sessionDeviceId}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
      .then(res => res.json())
      .then(data => {
        if (data.pulse) {
          setPulses(prev => [...prev, data.pulse]);
        }
      })
      .catch(err => console.error('Generate error:', err));
  };

  if (isCollapsed) {
    return (
      <div className={style.collapsedPanel} onClick={onToggleCollapse}>
        <span className={style.collapsedIcon}>•••</span>
        <span className={style.collapsedLabel}>Discussion<br/>Pulse</span>
        {pulses.length > 0 && (
          <span className={style.badge}>{pulses.length}</span>
        )}
      </div>
    );
  }

  return (
    <div className={style.pulsePanel}>
      <div className={style.header}>
        <h3>Discussion Pulse</h3>
        <div className={style.controls}>
          {isSessionActive && (
            <button
              className={style.refreshBtn}
              onClick={handleGeneratePulse}
              title="Generate summary now"
            >
              +
            </button>
          )}
          <button
            className={style.collapseBtn}
            onClick={onToggleCollapse}
          >
            -
          </button>
        </div>
      </div>

      <div
        className={style.pulseList}
        ref={scrollContainerRef}
        onScroll={handleScroll}
      >
        {isLoading && (
          <div className={style.loading}>
            Loading discussion summaries...
          </div>
        )}

        {!isLoading && pulses.length === 0 && (
          <div className={style.empty}>
            <p>No summaries yet</p>
            <p className={style.hint}>
              Summaries appear as the discussion progresses
            </p>
          </div>
        )}

        {pulses.map((pulse, index) => {
          const isCurrent = index === pulses.length - 1;
          const isLast = index === pulses.length - 1;

          return (
            <div
              key={pulse.id || index}
              ref={isLast ? lastPulseRef : null}
              className={`${style.pulseCard} ${isCurrent ? style.currentPulse : style.pastPulse}`}
            >
              <div className={style.timeRange}>
                {pulse.time_range}
                {isCurrent && isSessionActive && (
                  <span className={style.currentBadge}>CURRENT</span>
                )}
              </div>

              <div className={style.summary}>
                {pulse.summary_text}
              </div>

              <div className={style.topics}>
                {(pulse.topics || []).map((topic, idx) => (
                  <span key={idx} className={style.topicTag}>
                    #{topic}
                  </span>
                ))}
              </div>

              {pulse.speaker_count > 0 && (
                <div className={style.metadata}>
                  {pulse.speaker_count} speaker{pulse.speaker_count !== 1 ? 's' : ''}
                  {pulse.transcript_count && (
                    <span> | {pulse.transcript_count} segments</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {!autoScroll && (
        <button
          className={style.scrollToBottom}
          onClick={() => {
            setAutoScroll(true);
            lastPulseRef.current?.scrollIntoView({ behavior: 'smooth' });
          }}
        >
          Scroll to latest
        </button>
      )}
    </div>
  );
}

export { DiscussionPulsePanel };
export default DiscussionPulsePanel;
