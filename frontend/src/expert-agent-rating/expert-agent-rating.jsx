import { useState, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import styles from './expert-agent-rating.module.css';

// Extract plain text from React children (strings, nested elements)
const extractText = (children) => {
  if (typeof children === 'string') return children;
  if (Array.isArray(children)) return children.map(extractText).join('');
  if (children?.props?.children) return extractText(children.props.children);
  return '';
};

// Check if text looks like a transcript quote
// Starts with " and ends with " possibly followed by punctuation and/or a timestamp like (14:15)
const isQuotedText = (text) => {
  const trimmed = text.trim();
  if (trimmed.length < 30) return false;
  if (!/^[""\u201C]/.test(trimmed)) return false;
  // Match closing quote, optional punctuation, optional timestamp
  return /[""\u201D][.?!,;:)]*(\s*\(\d{1,3}:\d{2}\))?$/.test(trimmed);
};

// Style timestamps like [05:59] or (14:15) in text nodes
const styleTimestamps = (text) => {
  if (typeof text !== 'string') return text;
  const parts = text.split(/(\[\d{1,3}:\d{2}\]|\(\d{1,3}:\d{2}\))/g);
  if (parts.length === 1) return text;
  return parts.map((part, i) =>
    /^[\[\(]\d{1,3}:\d{2}[\]\)]$/.test(part)
      ? <span key={i} className={styles.timestamp}>{part}</span>
      : part
  );
};

// Recursively apply timestamp styling to children
const withInlineStyles = (children) => {
  if (typeof children === 'string') return styleTimestamps(children);
  if (Array.isArray(children)) return children.map((c, i) => typeof c === 'string' ? <span key={i}>{styleTimestamps(c)}</span> : c);
  return children;
};

// Custom markdown components to normalize quote styling
const markdownComponents = {
  // Render long italic quotes (e.g. *"transcript text..."*) as blockquotes
  em: ({ children }) => {
    const text = extractText(children);
    if (isQuotedText(text)) {
      return <blockquote className={styles.inlineQuote}><p>{children}</p></blockquote>;
    }
    return <em>{children}</em>;
  },
  // Render list items that are just quoted text in quote style
  li: ({ children }) => {
    const text = extractText(children);
    if (isQuotedText(text)) {
      return <li className={styles.quotedListItem}>{withInlineStyles(children)}</li>;
    }
    return <li>{withInlineStyles(children)}</li>;
  },
  // Apply timestamp styling in paragraphs
  p: ({ children }) => {
    return <p>{withInlineStyles(children)}</p>;
  }
};

// Rating dimensions with descriptions
const DIMENSIONS = [
  { key: 'accuracy', name: 'Accuracy', description: 'The response is factually correct' },
  { key: 'relevance', name: 'Relevance', description: 'The response addresses the question asked' },
  { key: 'groundedness', name: 'Groundedness', description: 'The response is supported by evidence from the data' },
  { key: 'analytical_depth', name: 'Analytical Depth', description: 'The response provides meaningful insight and/or considers multiple viewpoints where appropriate' },
  { key: 'helpfulness', name: 'Helpfulness', description: 'This response would be useful and actionable' },
];

function ExpertAgentRating() {
  const [expertId, setExpertId] = useState('');
  const [isLoaded, setIsLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [queryGroups, setQueryGroups] = useState([]);
  const [currentGroupIndex, setCurrentGroupIndex] = useState(0);
  const [currentResponseIndex, setCurrentResponseIndex] = useState(0);
  const [ratings, setRatings] = useState({});
  const [comment, setComment] = useState('');
  const [progress, setProgress] = useState({ total: 0, rated: 0 });
  const [message, setMessage] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const initRatings = useCallback(() => {
    const initial = {};
    DIMENSIONS.forEach(d => { initial[d.key] = 0; });
    return initial;
  }, []);

  const loadResponses = useCallback(async () => {
    if (!expertId.trim()) return;

    setIsLoading(true);
    setMessage('');
    try {
      const response = await fetch(
        `/api/expert-agent-rating/responses?expert_id=${encodeURIComponent(expertId)}`
      );
      const data = await response.json();

      if (data.error) {
        setMessage(`Error: ${data.error}`);
        return;
      }

      if (data.responses.length === 0) {
        setMessage('No responses available for rating yet.');
        return;
      }

      // Group flat response list into query groups
      const groups = [];
      let i = 0;
      while (i < data.responses.length) {
        const resp = data.responses[i];
        if (resp.pair_size === 2 && resp.pair_label === 'Response A') {
          const respB = data.responses[i + 1];
          groups.push({
            query: resp.query,
            pair_id: resp.pair_id,
            responses: [resp, respB]
          });
          i += 2;
        } else {
          groups.push({
            query: resp.query,
            pair_id: resp.pair_id,
            responses: [resp]
          });
          i += 1;
        }
      }

      setQueryGroups(groups);

      const totalResponses = data.responses.length;
      const ratedCount = data.responses.filter(r => r.rated).length;
      setProgress({ total: totalResponses, rated: ratedCount });

      const firstUnrated = groups.findIndex(g => g.responses.some(r => !r.rated));
      setCurrentGroupIndex(firstUnrated >= 0 ? firstUnrated : 0);
      setCurrentResponseIndex(0);

      setRatings(initRatings());
      setComment('');
      setIsLoaded(true);
      setMessage(`Loaded ${groups.length} queries (${data.pair_count || 0} paired, ${data.single_count || 0} single). ${ratedCount} responses rated.`);
    } catch (error) {
      console.error('Error loading responses:', error);
      setMessage('Error loading responses');
    } finally {
      setIsLoading(false);
    }
  }, [expertId, initRatings]);

  const loadExistingRating = useCallback(async (responseId) => {
    try {
      const response = await fetch(
        `/api/expert-agent-rating/rating/${responseId}?expert_id=${encodeURIComponent(expertId)}`
      );
      const data = await response.json();

      if (data.rating) {
        setRatings(data.rating.ratings);
        setComment(data.rating.comment || '');
      } else {
        setRatings(initRatings());
        setComment('');
      }
    } catch (error) {
      console.error('Error loading existing rating:', error);
    }
  }, [expertId, initRatings]);

  useEffect(() => {
    if (isLoaded && queryGroups.length > 0) {
      const group = queryGroups[currentGroupIndex];
      if (group && group.responses[currentResponseIndex]) {
        loadExistingRating(group.responses[currentResponseIndex].id);
      }
    }
  }, [currentGroupIndex, currentResponseIndex, isLoaded, queryGroups, loadExistingRating]);

  const updateRating = (dimension, value) => {
    setRatings(prev => ({ ...prev, [dimension]: value }));
  };

  const submitRating = async () => {
    const missingRatings = DIMENSIONS.filter(d => !ratings[d.key] || ratings[d.key] < 1);
    if (missingRatings.length > 0) {
      setMessage('Please rate all dimensions (1-5)');
      return;
    }

    const group = queryGroups[currentGroupIndex];
    const currentResp = group.responses[currentResponseIndex];

    setIsSaving(true);
    try {
      const response = await fetch('/api/expert-agent-rating/ratings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          expert_id: expertId,
          response_id: currentResp.id,
          ...ratings,
          comment: comment
        })
      });

      const data = await response.json();
      if (response.ok) {
        setQueryGroups(prev => prev.map((g, gi) => {
          if (gi !== currentGroupIndex) return g;
          return {
            ...g,
            responses: g.responses.map((r, ri) =>
              ri === currentResponseIndex ? { ...r, rated: true } : r
            )
          };
        }));

        if (!currentResp.rated) {
          setProgress(prev => ({ ...prev, rated: prev.rated + 1 }));
        }

        setMessage('Rating saved!');

        // Advance: if pair and on Response A, go to B
        if (group.responses.length === 2 && currentResponseIndex === 0) {
          setTimeout(() => {
            setCurrentResponseIndex(1);
            setMessage('');
          }, 500);
        } else {
          // Move to next group with unrated responses
          setTimeout(() => {
            const nextGroup = queryGroups.findIndex((g, gi) =>
              gi > currentGroupIndex && g.responses.some(r => !r.rated)
            );
            if (nextGroup >= 0) {
              setCurrentGroupIndex(nextGroup);
              setCurrentResponseIndex(0);
              setMessage('');
            } else {
              setMessage('All responses rated! Thank you.');
            }
          }, 500);
        }
      } else {
        setMessage(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error('Error submitting rating:', error);
      setMessage('Error submitting rating');
    } finally {
      setIsSaving(false);
    }
  };

  const goToGroup = (index) => {
    if (index >= 0 && index < queryGroups.length) {
      setCurrentGroupIndex(index);
      setCurrentResponseIndex(0);
      setMessage('');
    }
  };

  const currentGroup = queryGroups[currentGroupIndex];
  const currentResp = currentGroup?.responses[currentResponseIndex];

  return (
    <div className={styles.container}>
      <div className={styles.innerContainer}>
        <header className={styles.header}>
          <h1>Agent Response Evaluation</h1>
        </header>

        {!isLoaded && (
          <div className={styles.expertSection}>
            <label htmlFor="expertId">Enter your Expert ID:</label>
            <div className={styles.expertRow}>
              <input
                type="text"
                id="expertId"
                value={expertId}
                onChange={(e) => setExpertId(e.target.value)}
                placeholder="e.g., expert_marcelo"
                className={styles.expertInput}
                onKeyDown={(e) => e.key === 'Enter' && loadResponses()}
              />
              <button
                onClick={loadResponses}
                disabled={isLoading || !expertId.trim()}
                className={styles.loadButton}
              >
                {isLoading ? 'Loading...' : 'Start'}
              </button>
            </div>
            {message && <p className={styles.message}>{message}</p>}
          </div>
        )}

        {isLoaded && currentGroup && currentResp && (
          <div className={styles.ratingInterface}>
            {/* Progress bar */}
            <div className={styles.progressSection}>
              <div className={styles.progressInfo}>
                <span>Query {currentGroupIndex + 1} of {queryGroups.length}</span>
                <span>{progress.rated} / {progress.total} responses rated</span>
              </div>
              <div className={styles.progressBar}>
                <div
                  className={styles.progressFill}
                  style={{ width: `${(progress.rated / progress.total) * 100}%` }}
                />
              </div>
            </div>

            {/* Query-level navigation */}
            <div className={styles.navigation}>
              <button
                onClick={() => goToGroup(currentGroupIndex - 1)}
                disabled={currentGroupIndex === 0}
                className={styles.navButton}
              >
                Prev Query
              </button>
              <div className={styles.responseIndicators}>
                {queryGroups.map((g, i) => {
                  const allRated = g.responses.every(r => r.rated);
                  const someRated = g.responses.some(r => r.rated);
                  return (
                    <button
                      key={i}
                      onClick={() => goToGroup(i)}
                      className={`${styles.indicator} ${i === currentGroupIndex ? styles.indicatorActive : ''} ${allRated ? styles.indicatorRated : someRated ? styles.indicatorPartial : ''}`}
                      title={`Query ${i + 1} (${g.responses.length === 2 ? 'paired' : 'single'})${allRated ? ' - all rated' : someRated ? ' - partially rated' : ''}`}
                    />
                  );
                })}
              </div>
              <button
                onClick={() => goToGroup(currentGroupIndex + 1)}
                disabled={currentGroupIndex === queryGroups.length - 1}
                className={styles.navButton}
              >
                Next Query
              </button>
            </div>

            <div className={styles.contentAndRating}>
              {/* Left: Query + Response */}
              <div className={styles.responseDisplay}>
                <div className={styles.queryBox}>
                  <h3>Query</h3>
                  <p>{currentGroup.query}</p>
                </div>

                {/* A/B sub-navigation for pairs */}
                {currentGroup.responses.length === 2 && (
                  <div className={styles.pairNav}>
                    {currentGroup.responses.map((r, ri) => (
                      <button
                        key={ri}
                        onClick={() => { setCurrentResponseIndex(ri); setMessage(''); }}
                        className={`${styles.pairNavButton} ${ri === currentResponseIndex ? styles.pairNavActive : ''} ${r.rated ? styles.pairNavRated : ''}`}
                      >
                        {r.pair_label}
                        {r.rated && ' \u2713'}
                      </button>
                    ))}
                  </div>
                )}

                <div className={styles.answerBox}>
                  <h3>{currentResp.pair_label || 'Response'}</h3>
                  <div className={styles.answerContent}>
                    <ReactMarkdown components={markdownComponents}>{currentResp.response}</ReactMarkdown>
                  </div>
                </div>
              </div>

              {/* Right: Sticky rating panel */}
              <div className={styles.ratingForm}>
                <h3>Rate this response</h3>
                <div className={styles.dimensionGrid}>
                  {DIMENSIONS.map((dim) => (
                    <div key={dim.key} className={styles.dimensionRow}>
                      <div className={styles.dimensionInfo}>
                        <span className={styles.dimensionName}>{dim.name}</span>
                        <span className={styles.dimensionDesc}>{dim.description}</span>
                      </div>
                      <div className={styles.likertScale}>
                        {[1, 2, 3, 4, 5].map((value) => (
                          <button
                            key={value}
                            onClick={() => updateRating(dim.key, value)}
                            className={`${styles.likertButton} ${ratings[dim.key] === value ? styles.likertSelected : ''}`}
                          >
                            {value}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>

                <div className={styles.commentSection}>
                  <label htmlFor="comment">Comments (optional)</label>
                  <textarea
                    id="comment"
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Any issues or observations..."
                    rows={3}
                    className={styles.commentInput}
                  />
                </div>

                <div className={styles.submitSection}>
                  <button
                    onClick={submitRating}
                    disabled={isSaving}
                    className={styles.submitButton}
                  >
                    {isSaving ? 'Saving...' : currentResp.rated ? 'Update Rating' : 'Submit Rating'}
                  </button>
                  {message && <span className={styles.submitMessage}>{message}</span>}
                </div>
              </div>
            </div>

            <div className={styles.footer}>
              <button
                onClick={() => {
                  setIsLoaded(false);
                  setQueryGroups([]);
                  setMessage('');
                }}
                className={styles.changeExpertButton}
              >
                Change Expert ID
              </button>
            </div>
          </div>
        )}

        {isLoaded && queryGroups.length === 0 && (
          <div className={styles.emptyState}>
            <p>No responses available for rating yet.</p>
            <button
              onClick={() => {
                setIsLoaded(false);
                setMessage('');
              }}
              className={styles.changeExpertButton}
            >
              Back
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export { ExpertAgentRating };
