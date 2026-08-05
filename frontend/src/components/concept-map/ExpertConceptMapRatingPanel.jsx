import { useState, useCallback } from 'react';
import styles from './expert-concept-map-rating-panel.module.css';

const DIMENSIONS = [
  { key: 'node_accuracy', name: 'Node Accuracy', description: 'The concepts accurately reflect ideas from the discussion' },
  { key: 'relationship_validity', name: 'Relationship Validity', description: 'The connections between concepts are meaningful and supported' },
  { key: 'completeness', name: 'Completeness', description: 'Important ideas from the discussion are captured' },
  { key: 'granularity', name: 'Granularity', description: 'The level of detail is appropriate, not too broad, not too fragmented' },
  { key: 'usefulness', name: 'Usefulness', description: 'This map would help a learner or educator understand the discussion' },
];

function ExpertConceptMapRatingPanel({ sessionDeviceId }) {
  const [expertId, setExpertId] = useState('');
  const [isLoaded, setIsLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('draft');
  const [lastSaved, setLastSaved] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');
  const [ratings, setRatings] = useState(() => {
    const initial = {};
    DIMENSIONS.forEach(d => { initial[d.key] = null; });
    return initial;
  });
  const [comment, setComment] = useState('');

  const loadRating = useCallback(async () => {
    if (!expertId.trim() || !sessionDeviceId) return;

    setIsLoading(true);
    try {
      const response = await fetch(
        `/api/v1/expert-concept-map-ratings/${sessionDeviceId}?expert_id=${encodeURIComponent(expertId)}`
      );
      const data = await response.json();

      if (data.exists) {
        setRatings(data.rating.ratings);
        setComment(data.rating.comment || '');
        setStatus(data.rating.status);
        setLastSaved(data.rating.updated_at);
        setSaveMessage('Existing rating loaded');
      } else {
        const empty = {};
        DIMENSIONS.forEach(d => { empty[d.key] = null; });
        setRatings(empty);
        setComment('');
        setStatus('draft');
        setLastSaved(null);
        setSaveMessage('New rating — ready to start');
      }
      setIsLoaded(true);
    } catch (error) {
      console.error('Error loading rating:', error);
      setSaveMessage('Error loading rating');
    } finally {
      setIsLoading(false);
    }
  }, [expertId, sessionDeviceId]);

  const saveDraft = async () => {
    if (!expertId.trim()) { setSaveMessage('Please enter an Expert ID first'); return; }
    setIsLoading(true);
    try {
      const response = await fetch(`/api/v1/expert-concept-map-ratings/${sessionDeviceId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expert_id: expertId, ratings, comment, status: 'draft' }),
      });
      const data = await response.json();
      if (response.ok) {
        setLastSaved(data.rating.updated_at);
        setStatus('draft');
        setSaveMessage('Draft saved successfully');
      } else {
        setSaveMessage(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error('Error saving draft:', error);
      setSaveMessage('Error saving draft');
    } finally {
      setIsLoading(false);
    }
  };

  const submitRating = async () => {
    if (!expertId.trim()) { setSaveMessage('Please enter an Expert ID first'); return; }
    const missing = DIMENSIONS.filter(d => !ratings[d.key]);
    if (missing.length > 0) {
      setSaveMessage(`Please rate: ${missing.map(d => d.name).join(', ')}`);
      return;
    }
    setIsLoading(true);
    try {
      const response = await fetch(`/api/v1/expert-concept-map-ratings/${sessionDeviceId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expert_id: expertId, ratings, comment, status: 'submitted' }),
      });
      const data = await response.json();
      if (response.ok) {
        setLastSaved(data.rating.updated_at);
        setStatus('submitted');
        setSaveMessage('Rating submitted successfully!');
      } else {
        setSaveMessage(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error('Error submitting rating:', error);
      setSaveMessage('Error submitting rating');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTimestamp = (isoString) => {
    if (!isoString) return '';
    return new Date(isoString).toLocaleString();
  };

  const isSubmitted = status === 'submitted';

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3>Expert Concept Map Rating</h3>
        {isSubmitted && <span className={styles.submittedBadge}>Submitted</span>}
      </div>

      {/* Expert ID */}
      <div className={styles.expertIdSection}>
        <label htmlFor="cmExpertId">Expert ID:</label>
        <div className={styles.expertIdRow}>
          <input
            type="text"
            id="cmExpertId"
            value={expertId}
            onChange={(e) => setExpertId(e.target.value)}
            placeholder="e.g., expert_marcelo"
            disabled={isLoaded && isSubmitted}
            className={styles.expertIdInput}
          />
          {!isLoaded ? (
            <button onClick={loadRating} disabled={isLoading || !expertId.trim()} className={styles.loadButton}>
              {isLoading ? 'Loading...' : 'Load / Start'}
            </button>
          ) : (
            <button onClick={() => { setIsLoaded(false); setExpertId(''); setSaveMessage(''); }} className={styles.changeButton}>
              Change
            </button>
          )}
        </div>
      </div>

      {/* Rating form */}
      {isLoaded && (
        <>
          <div className={styles.dimensionList}>
            {DIMENSIONS.map((dim) => (
              <div key={dim.key} className={styles.dimensionBox}>
                <div className={styles.dimensionHeader}>
                  <span className={styles.dimensionName}>{dim.name}</span>
                </div>
                <p className={styles.dimensionDesc}>{dim.description}</p>
                <div className={styles.likertGroup}>
                  {[1, 2, 3, 4, 5].map((val) => (
                    <label key={val} className={`${styles.likertOption} ${ratings[dim.key] === val ? styles.likertSelected : ''}`}>
                      <input
                        type="radio"
                        name={dim.key}
                        value={val}
                        checked={ratings[dim.key] === val}
                        onChange={() => { setRatings(prev => ({ ...prev, [dim.key]: val })); setSaveMessage(''); }}
                        disabled={isSubmitted}
                        className={styles.likertRadio}
                      />
                      <span className={styles.likertLabel}>{val}</span>
                    </label>
                  ))}
                  <span className={styles.likertScale}>
                    <span>Strongly Disagree</span>
                    <span>Strongly Agree</span>
                  </span>
                </div>
              </div>
            ))}

            {/* Comment - always shown */}
            <div className={styles.dimensionBox}>
              <div className={styles.dimensionHeader}>
                <span className={styles.dimensionName}>Comment</span>
              </div>
              <p className={styles.dimensionDesc}>Any issues or observations?</p>
              <textarea
                value={comment}
                onChange={(e) => { setComment(e.target.value); setSaveMessage(''); }}
                disabled={isSubmitted}
                placeholder="Optional comments..."
                rows={3}
                className={styles.textarea}
              />
            </div>
          </div>

          {/* Actions */}
          <div className={styles.actions}>
            {!isSubmitted && (
              <>
                <button onClick={saveDraft} disabled={isLoading} className={styles.draftButton}>
                  {isLoading ? 'Saving...' : 'Save Draft'}
                </button>
                <button onClick={submitRating} disabled={isLoading} className={styles.submitButton}>
                  {isLoading ? 'Submitting...' : 'Submit'}
                </button>
              </>
            )}
          </div>

          {/* Status */}
          <div className={styles.statusSection}>
            {saveMessage && <p className={styles.saveMessage}>{saveMessage}</p>}
            {lastSaved && <p className={styles.lastSaved}>Last saved: {formatTimestamp(lastSaved)}</p>}
          </div>
        </>
      )}

      {!isLoaded && (
        <p className={styles.instructions}>
          Enter your Expert ID to load existing rating or start a new one.
        </p>
      )}
    </div>
  );
}

export { ExpertConceptMapRatingPanel };
