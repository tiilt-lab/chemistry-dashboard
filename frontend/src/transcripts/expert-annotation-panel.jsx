import { useState, useEffect, useCallback } from 'react';
import styles from './expert-annotation-panel.module.css';

// 7C dimension definitions
const DIMENSIONS = [
  { key: 'climate', name: 'Climate', description: 'The emotional and affective aspects of the collaboration', indicators: 'respect, comfort, tone, welcome, safe, listening' },
  { key: 'communication', name: 'Communication', description: 'The quantity and quality of information shared among group members', indicators: 'verbal, nonverbal, discussion, listening, sharing' },
  { key: 'compatibility', name: 'Compatibility', description: 'How well group members\' working styles complement each other', indicators: 'working style, equal distribution, complementary skills' },
  { key: 'conflict', name: 'Conflict', description: 'Approaches to handling disagreements and contentious situations', indicators: 'adapting, differences, confronting, mediator, resolution' },
  { key: 'context', name: 'Context', description: 'Environmental factors and situational awareness', indicators: 'privacy, setting, interest, group members' },
  { key: 'contribution', name: 'Contribution', description: 'Individual participation and effort balance', indicators: 'accountable, balance of work, engagement, effort' },
  { key: 'constructive', name: 'Constructive', description: 'Overall goals and the team\'s progress toward achieving them', indicators: 'goal, product, efficiency, learning, mutual benefit' },
];

function ExpertAnnotationPanel({ sessionDeviceId }) {
  const [expertId, setExpertId] = useState('');
  const [isLoaded, setIsLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('draft');
  const [lastSaved, setLastSaved] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');
  const [annotationData, setAnnotationData] = useState(() => {
    const initial = {};
    DIMENSIONS.forEach(d => {
      initial[d.key] = { score: '', analysis: '', evidence: '' };
    });
    return initial;
  });

  // Load existing annotation when expert ID is confirmed
  const loadAnnotation = useCallback(async () => {
    if (!expertId.trim() || !sessionDeviceId) return;

    setIsLoading(true);
    try {
      const response = await fetch(
        `/api/v1/expert-annotations/${sessionDeviceId}?expert_id=${encodeURIComponent(expertId)}`
      );
      const data = await response.json();

      if (data.exists) {
        setAnnotationData(data.annotation.annotation_data);
        setStatus(data.annotation.status);
        setLastSaved(data.annotation.updated_at);
        setSaveMessage('Existing annotation loaded');
      } else {
        // Initialize empty annotation
        const empty = {};
        DIMENSIONS.forEach(d => {
          empty[d.key] = { score: '', analysis: '', evidence: '' };
        });
        setAnnotationData(empty);
        setStatus('draft');
        setLastSaved(null);
        setSaveMessage('New annotation - ready to start');
      }
      setIsLoaded(true);
    } catch (error) {
      console.error('Error loading annotation:', error);
      setSaveMessage('Error loading annotation');
    } finally {
      setIsLoading(false);
    }
  }, [expertId, sessionDeviceId]);

  // Update a dimension field
  const updateDimension = (dimension, field, value) => {
    setAnnotationData(prev => ({
      ...prev,
      [dimension]: {
        ...prev[dimension],
        [field]: value
      }
    }));
    setSaveMessage(''); // Clear save message when editing
  };

  // Save draft
  const saveDraft = async () => {
    if (!expertId.trim()) {
      setSaveMessage('Please enter an Expert ID first');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`/api/v1/expert-annotations/${sessionDeviceId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          expert_id: expertId,
          annotation_data: annotationData,
          status: 'draft'
        })
      });

      const data = await response.json();
      if (response.ok) {
        setLastSaved(data.annotation.updated_at);
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

  // Submit final
  const submitAnnotation = async () => {
    if (!expertId.trim()) {
      setSaveMessage('Please enter an Expert ID first');
      return;
    }

    // Validate all dimensions have scores
    const missingScores = DIMENSIONS.filter(d => !annotationData[d.key]?.score);
    if (missingScores.length > 0) {
      setSaveMessage(`Please provide scores for: ${missingScores.map(d => d.name).join(', ')}`);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`/api/v1/expert-annotations/${sessionDeviceId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          expert_id: expertId,
          annotation_data: annotationData,
          status: 'submitted'
        })
      });

      const data = await response.json();
      if (response.ok) {
        setLastSaved(data.annotation.updated_at);
        setStatus('submitted');
        setSaveMessage('Annotation submitted successfully!');
      } else {
        setSaveMessage(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error('Error submitting annotation:', error);
      setSaveMessage('Error submitting annotation');
    } finally {
      setIsLoading(false);
    }
  };

  // Format timestamp
  const formatTimestamp = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3>Expert 7C Annotation</h3>
        {status === 'submitted' && <span className={styles.submittedBadge}>Submitted</span>}
      </div>

      {/* Expert ID input */}
      <div className={styles.expertIdSection}>
        <label htmlFor="expertId">Expert ID:</label>
        <div className={styles.expertIdRow}>
          <input
            type="text"
            id="expertId"
            value={expertId}
            onChange={(e) => setExpertId(e.target.value)}
            placeholder="e.g., expert_marcelo"
            disabled={isLoaded && status === 'submitted'}
            className={styles.expertIdInput}
          />
          {!isLoaded && (
            <button
              onClick={loadAnnotation}
              disabled={isLoading || !expertId.trim()}
              className={styles.loadButton}
            >
              {isLoading ? 'Loading...' : 'Load / Start'}
            </button>
          )}
          {isLoaded && (
            <button
              onClick={() => {
                setIsLoaded(false);
                setExpertId('');
                setSaveMessage('');
              }}
              className={styles.changeButton}
            >
              Change
            </button>
          )}
        </div>
      </div>

      {/* Annotation form */}
      {isLoaded && (
        <>
          <div className={styles.dimensionList}>
            {DIMENSIONS.map((dim) => (
              <div key={dim.key} className={styles.dimensionBox}>
                <div className={styles.dimensionHeader}>
                  <span className={styles.dimensionName}>{dim.name}</span>
                  <span className={styles.tooltip} title={`${dim.description}\nIndicators: ${dim.indicators}`}>
                    ?
                  </span>
                </div>

                <div className={styles.fieldGroup}>
                  <label>Score (0-100):</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={annotationData[dim.key]?.score || ''}
                    onChange={(e) => updateDimension(dim.key, 'score', e.target.value)}
                    disabled={status === 'submitted'}
                    className={styles.scoreInput}
                  />
                </div>

                <div className={styles.fieldGroup}>
                  <label>Analysis:</label>
                  <textarea
                    value={annotationData[dim.key]?.analysis || ''}
                    onChange={(e) => updateDimension(dim.key, 'analysis', e.target.value)}
                    disabled={status === 'submitted'}
                    placeholder="Your analysis of this dimension..."
                    rows={3}
                    className={styles.textarea}
                  />
                </div>

                <div className={styles.fieldGroup}>
                  <label>Key Evidence:</label>
                  <textarea
                    value={annotationData[dim.key]?.evidence || ''}
                    onChange={(e) => updateDimension(dim.key, 'evidence', e.target.value)}
                    disabled={status === 'submitted'}
                    placeholder="Evidence from the transcript..."
                    rows={2}
                    className={styles.textarea}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Save/Submit buttons */}
          <div className={styles.actions}>
            {status !== 'submitted' && (
              <>
                <button
                  onClick={saveDraft}
                  disabled={isLoading}
                  className={styles.draftButton}
                >
                  {isLoading ? 'Saving...' : 'Save Draft'}
                </button>
                <button
                  onClick={submitAnnotation}
                  disabled={isLoading}
                  className={styles.submitButton}
                >
                  {isLoading ? 'Submitting...' : 'Submit'}
                </button>
              </>
            )}
          </div>

          {/* Status messages */}
          <div className={styles.statusSection}>
            {saveMessage && (
              <p className={styles.saveMessage}>{saveMessage}</p>
            )}
            {lastSaved && (
              <p className={styles.lastSaved}>Last saved: {formatTimestamp(lastSaved)}</p>
            )}
          </div>
        </>
      )}

      {!isLoaded && (
        <p className={styles.instructions}>
          Enter your Expert ID to load existing annotation or start a new one.
        </p>
      )}
    </div>
  );
}

export { ExpertAnnotationPanel };
