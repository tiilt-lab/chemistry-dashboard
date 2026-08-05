import React, { useState, useEffect } from 'react';
import './rag-search.css';
import ReactMarkdown from 'react-markdown';

// Session storage keys for state persistence
const STORAGE_KEY = 'ragSearchState';

function RagSearchComponent() {
  // Initialize state from sessionStorage for persistence across navigation
  const [query, setQuery] = useState(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved).query || '' : '';
    } catch { return ''; }
  });
  const [results, setResults] = useState(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved).results || null : null;
    } catch { return null; }
  });
  const [loading, setLoading] = useState(false);
  const [searchType, setSearchType] = useState('all');
  const [manualInsights, setManualInsights] = useState(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved).manualInsights || null : null;
    } catch { return null; }
  });
  const [loadingManualInsights, setLoadingManualInsights] = useState(false);

  // Save state to sessionStorage when it changes
  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
        query,
        results,
        manualInsights
      }));
    } catch (e) {
      console.warn('Failed to save search state:', e);
    }
  }, [query, results, manualInsights]);

  // Quick action examples
  const quickActions = [
    { label: 'Compare Sessions', query: 'Compare discussion on nuclear fusion and discussion on country music' },
    { label: 'High Communication', query: 'sessions with high communication quality' },
    { label: 'Speaker Styles', query: 'How did Julia articulate her opinions?' },
    { label: 'Why Patterns?', query: 'why do some discussions have higher engagement?' }
  ];

  const handleSearch = async (searchQuery = query) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setManualInsights(null); // Clear manual insights on new search

    try {
      const response = await fetch('/api/v1/rag/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery,
          granularity: 'auto',  // Always use auto - let backend decide
          filter_to_user: searchType === 'my_sessions'
        })
      });

      const data = await response.json();
      console.log('Search response:', data);
      setResults(data);
    } catch (error) {
      console.error('Search failed:', error);
      setResults({
        query_type: 'error',
        error: 'Search failed. Please try again.'
      });
    }
    setLoading(false);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const generateManualInsights = async () => {
    setLoadingManualInsights(true);

    try {
      // Combine all result types for the insights endpoint
      // Priority: chunks > sessions > speakers
      const allResults = results.results || results.session_results || results.speaker_results || [];

      const response = await fetch('/api/v1/rag/insights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: results.query,
          search_results: {
            query: results.query,
            results: allResults,
            session_results: results.session_results,
            speaker_results: results.speaker_results,
            total_found: results.total_found
          }
        })
      });

      const data = await response.json();
      setManualInsights(data.insights);
    } catch (error) {
      console.error('Insights error:', error);
      setManualInsights('Failed to generate insights. Please try again.');
    }

    setLoadingManualInsights(false);
  };

  // Determine which insights to show: auto-generated or manual
  const displayedInsights = results?.insights || manualInsights;
  const hasChunkResults = results?.results && results.results.length > 0;
  const hasSessionResults = results?.session_results && results.session_results.length > 0;
  const hasSpeakerResults = results?.speaker_results && results.speaker_results.length > 0;
  const hasResults = hasChunkResults || hasSessionResults || hasSpeakerResults;
  const showInsightsButton = hasResults && !results?.insights && !displayedInsights;

  return (
    <div className="rag-search-container">
      <div className="search-header">
        <h2>Discover Insights</h2>
        <p>Ask questions about discussion patterns and insights</p>
      </div>

      <div className="search-box">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Ask anything about your discussions..."
          className="search-input"
        />
        <button 
          onClick={() => handleSearch()} 
          disabled={loading}
          className="search-button"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      <div className="search-filters">
        <div className="filter-group">
          <span className="filter-label">Search in:</span>
          <label>
            <input
              type="radio"
              value="all"
              checked={searchType === 'all'}
              onChange={(e) => setSearchType(e.target.value)}
            />
            All Sessions
          </label>
          <label>
            <input
              type="radio"
              value="my_sessions"
              checked={searchType === 'my_sessions'}
              onChange={(e) => setSearchType(e.target.value)}
            />
            My Sessions Only
          </label>
        </div>

      </div>

      <div className="quick-actions">
        <span>Try: </span>
        {quickActions.map((action, idx) => (
          <button
            key={idx}
            onClick={() => {
              setQuery(action.query);
              handleSearch(action.query);
            }}
            className="quick-action-btn"
          >
            {action.label}
          </button>
        ))}
      </div>

      {results && (
        <div className="search-results">
          {/* Error State */}
          {results.query_type === 'error' && (
            <div className="error">
              {results.error}
              {results.example && <p className="error-example">Example: {results.example}</p>}
            </div>
          )}

          {/* Insights Display - auto-generated or manual */}
          {displayedInsights && (
            <div className="insights-section">
              <h3>
                {results.insights ? 'AI Insights' : 'Generated Insights'}
              </h3>
              <div className="insights-box">
                <ReactMarkdown>{displayedInsights}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* Search Level Indicator */}
          {results.search_level && (
            <div className="search-level-indicator">
              Searched: {results.search_level === 'chunks' ? 'Specific Moments' :
                        results.search_level === 'sessions' ? 'Discussion Patterns' : 'Both Levels'}
              {results.filters_applied && Object.keys(results.filters_applied).length > 0 && (
                <span className="filters-applied"> | Filters: {Object.keys(results.filters_applied).join(', ')}</span>
              )}
            </div>
          )}

          {/* Results with Manual Insights Button */}
          {hasResults && (
            <>
              <h3>
                {displayedInsights ? 'Supporting Evidence' : 'Results'} ({results.total_found})
              </h3>

              {/* Show button only if no insights exist yet */}
              {showInsightsButton && (
                <button
                  onClick={generateManualInsights}
                  disabled={loadingManualInsights}
                  className="insight-button"
                >
                  {loadingManualInsights ? 'Generating...' : 'Generate AI Insights'}
                </button>
              )}

              {/* Session-Level Results (NEW) */}
              {hasSessionResults && (
                <div className="session-results-section">
                  <h4>Discussion Patterns ({results.session_results.length} sessions)</h4>
                  {results.session_results.map((result, idx) => (
                    <div key={idx} className="session-result-item">
                      <div className="result-header">
                        <span className="session-badge">
                          Session {result.session_device_id || result.metadata?.session_device_id}
                        </span>
                        {/* Ultra RAG hybrid score indicator */}
                        {result.hybrid_score > 0 && (
                          <span className="relevance-badge" title={`Metric: ${(result.metric_score * 100).toFixed(0)}% | Semantic: ${(result.semantic_score * 100).toFixed(0)}%`}>
                            {(result.hybrid_score * 100).toFixed(0)}% match
                          </span>
                        )}
                        <span className="discourse-badge">
                          {result.metadata?.discourse_type || 'Discussion'}
                        </span>
                        {result.metadata?.has_concept_map && (
                          <span className="feature-badge concept-map">Concept Map</span>
                        )}
                        {result.metadata?.has_seven_cs && (
                          <span className="feature-badge seven-cs">7C Analysis</span>
                        )}
                      </div>

                      {/* Structural Metrics */}
                      <div className="session-metrics">
                        <span className="metric-item">
                          <span className="metric-label">Concepts:</span>
                          <span className="metric-value">{result.metadata?.node_count || 0}</span>
                        </span>
                        <span className="metric-item">
                          <span className="metric-label">Clusters:</span>
                          <span className="metric-value">{result.metadata?.cluster_count || 0}</span>
                        </span>
                        <span className="metric-item">
                          <span className="metric-label">Questions:</span>
                          <span className="metric-value">{((result.metadata?.question_ratio || 0) * 100).toFixed(0)}%</span>
                        </span>
                        {result.metadata?.communication_score > 0 && (
                          <span className="metric-item">
                            <span className="metric-label">Communication:</span>
                            <span className="metric-value">{result.metadata?.communication_score}/100</span>
                          </span>
                        )}
                      </div>

                      {/* Argumentation Metrics (from backend enrichment) */}
                      {result.argumentation?.has_concept_map && (
                        <div className="session-argumentation">
                          <span className="metric-item">
                            <span className="metric-label">Debate Score:</span>
                            <span className="metric-value debate-score">{result.argumentation.debate_score}</span>
                          </span>
                          <span className="metric-item">
                            <span className="metric-label">Reasoning:</span>
                            <span className="metric-value">{result.argumentation.reasoning_depth}</span>
                          </span>
                          <span className="metric-item">
                            <span className="metric-label">Challenges:</span>
                            <span className="metric-value">{result.argumentation.challenge_count}</span>
                          </span>
                        </div>
                      )}

                      {/* Evolution Metrics (from backend enrichment) */}
                      {result.evolution?.has_evolution && (
                        <div className="session-evolution">
                          <span className="metric-item">
                            <span className="metric-label">Analytic Δ:</span>
                            <span className={`metric-value ${result.evolution.analytic_evolution > 0 ? 'positive' : 'negative'}`}>
                              {result.evolution.analytic_evolution > 0 ? '+' : ''}{result.evolution.analytic_evolution}
                            </span>
                          </span>
                          <span className="metric-item">
                            <span className="metric-label">Tone Δ:</span>
                            <span className={`metric-value ${result.evolution.tone_evolution > 0 ? 'positive' : 'negative'}`}>
                              {result.evolution.tone_evolution > 0 ? '+' : ''}{result.evolution.tone_evolution}
                            </span>
                          </span>
                        </div>
                      )}

                      {/* Preview Text */}
                      {result.text_preview && (
                        <div className="result-text session-preview">
                          {result.text_preview.substring(0, 250)}...
                        </div>
                      )}

                      {/* Cluster Themes */}
                      {result.metadata?.cluster_names && Array.isArray(result.metadata.cluster_names) && result.metadata.cluster_names.length > 0 && (
                        <div className="cluster-themes">
                          <span className="themes-label">Themes: </span>
                          {result.metadata.cluster_names.slice(0, 3).map((name, i) => (
                            <span key={i} className="theme-tag">{name}</span>
                          ))}
                        </div>
                      )}

                      <a
                        href={`/sessions/${result.metadata?.session_id}/pods/${result.session_device_id || result.metadata?.session_device_id}`}
                        className="view-link"
                      >
                        View Session →
                      </a>
                    </div>
                  ))}
                </div>
              )}

              {/* Chunk-Level Results (Original) */}
              {hasChunkResults && (
                <div className="chunk-results-section">
                  {hasSessionResults && <h4>Specific Moments ({results.results.length})</h4>}
                  {results.results.map((result, idx) => (
                    <div key={idx} className="result-item">
                      <div className="result-header">
                        <span className="session-badge">
                          Session {result.metadata?.session_device_id}
                        </span>
                        <span className="time-badge">
                          {formatTime(result.metadata?.start_time)} - {formatTime(result.metadata?.end_time)}
                        </span>
                        <span className="speakers-badge">
                          {result.metadata?.speaker_count || 0} speakers
                        </span>
                      </div>

                      <div className="result-text">
                        {(result.text || result.text_preview || '').substring(0, 300)}...
                      </div>

                      <div className="result-metrics">
                        <span className="metric-item">
                          <span className="metric-label">Tone:</span>
                          <span className="metric-value">{result.metadata?.avg_emotional_tone?.toFixed(0) || 0}</span>
                        </span>
                        <span className="metric-item">
                          <span className="metric-label">Analytic:</span>
                          <span className="metric-value">{result.metadata?.avg_analytic_thinking?.toFixed(0) || 0}</span>
                        </span>
                        <span className="metric-item">
                          <span className="metric-label">Clout:</span>
                          <span className="metric-value">{result.metadata?.avg_clout?.toFixed(0) || 0}</span>
                        </span>
                        <span className="metric-item">
                          <span className="metric-label">Authenticity:</span>
                          <span className="metric-value">{result.metadata?.avg_authenticity?.toFixed(0) || 0}</span>
                        </span>
                        <span className="metric-item">
                          <span className="metric-label">Certainty:</span>
                          <span className="metric-value">{result.metadata?.avg_certainty?.toFixed(0) || 0}</span>
                        </span>
                      </div>

                      <a
                        href={`/transcripts/device/${result.metadata?.session_device_id}?highlight_time=${result.metadata?.start_time || 0}`}
                        className="view-link"
                      >
                        View in context →
                      </a>
                    </div>
                  ))}
                </div>
              )}

              {/* Speaker Results */}
              {hasSpeakerResults && (
                <div className="speaker-results-section">
                  <h4>Speaker Profiles ({results.speaker_results.length})</h4>
                  {results.speaker_results.map((result, idx) => (
                    <div key={idx} className="speaker-result-item">
                      <div className="result-header">
                        <span className="speaker-badge">
                          {result.metadata?.speaker_name || result.speaker_name || 'Speaker'}
                        </span>
                        <span className="session-badge">
                          Session {result.metadata?.session_device_id || result.session_device_id}
                        </span>
                      </div>

                      <div className="speaker-metrics">
                        {result.metadata?.total_turns > 0 && (
                          <span className="metric-item">
                            <span className="metric-label">Speaking Turns:</span>
                            <span className="metric-value">{result.metadata.total_turns}</span>
                          </span>
                        )}
                        {result.metadata?.avg_turn_length > 0 && (
                          <span className="metric-item">
                            <span className="metric-label">Avg Turn Length:</span>
                            <span className="metric-value">{result.metadata.avg_turn_length.toFixed(0)} words</span>
                          </span>
                        )}
                        {result.metadata?.question_ratio > 0 && (
                          <span className="metric-item">
                            <span className="metric-label">Questions:</span>
                            <span className="metric-value">{(result.metadata.question_ratio * 100).toFixed(0)}%</span>
                          </span>
                        )}
                      </div>

                      {result.text && (
                        <div className="result-text speaker-profile">
                          {result.text.substring(0, 300)}...
                        </div>
                      )}

                      <a
                        href={`/transcripts/device/${result.metadata?.session_device_id || result.session_device_id}`}
                        className="view-link"
                      >
                        View Session →
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* Speaker Comparison Results */}
          {results.speaker_comparison && Object.keys(results.speaker_comparison).length > 0 && (
            <>
              <h3>Speaker Comparison</h3>
              <div className="comparison-grid speaker-comparison">
                {Object.entries(results.speaker_comparison).map(([name, profile]) => (
                  <div key={name} className="comparison-card speaker-card">
                    <h4>{profile.alias || name}</h4>
                    <div className="speaker-stats">
                      <p><strong>Sessions:</strong> {profile.session_count || 0}</p>
                      <p><strong>Total Turns:</strong> {profile.total_turns || 0}</p>
                      <p><strong>Questions:</strong> {profile.question_count || 0} ({((profile.question_ratio || 0) * 100).toFixed(0)}%)</p>
                      <p><strong>Avg Turn Length:</strong> {(profile.avg_turn_length || 0).toFixed(0)} words</p>
                    </div>
                    <div className="speaker-liwc">
                      <h5>Communication Style</h5>
                      <MetricRow label="Clout" value={profile.avg_clout} />
                      <MetricRow label="Analytic" value={profile.avg_analytic} />
                      <MetricRow label="Tone" value={profile.avg_tone} />
                      <MetricRow label="Authenticity" value={profile.avg_authenticity} />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Similar Sessions Results */}
          {results.similar?.similar_sessions && results.similar.similar_sessions.length > 0 && (
            <div className="similar-results-section">
              <h3>Similar Sessions</h3>
              <p className="similar-reference">
                Finding sessions similar to Session {results.similar.reference_session_device_id}
              </p>
              {results.similar.similar_sessions.map((result, idx) => (
                <div key={idx} className="session-result-item">
                  <div className="result-header">
                    <span className="session-badge">
                      Session {result.session_device_id}
                    </span>
                    <span className="similarity-badge">
                      {((1 - result.distance) * 100).toFixed(0)}% similar
                    </span>
                    <span className="discourse-badge">
                      {result.metadata?.discourse_type || 'Discussion'}
                    </span>
                  </div>
                  <div className="session-metrics">
                    <span className="metric-item">
                      <span className="metric-label">Concepts:</span>
                      <span className="metric-value">{result.metadata?.node_count || 0}</span>
                    </span>
                    <span className="metric-item">
                      <span className="metric-label">Clusters:</span>
                      <span className="metric-value">{result.metadata?.cluster_count || 0}</span>
                    </span>
                    {result.metadata?.communication_score > 0 && (
                      <span className="metric-item">
                        <span className="metric-label">Communication:</span>
                        <span className="metric-value">{result.metadata?.communication_score}/100</span>
                      </span>
                    )}
                  </div>
                  {result.metadata?.cluster_names && Array.isArray(result.metadata.cluster_names) && (
                    <div className="cluster-themes">
                      <span className="themes-label">Themes: </span>
                      {result.metadata.cluster_names.slice(0, 3).map((name, i) => (
                        <span key={i} className="theme-tag">{name}</span>
                      ))}
                    </div>
                  )}
                  <a
                    href={`/sessions/${result.metadata?.session_id}/pods/${result.session_device_id}`}
                    className="view-link"
                  >
                    View Session →
                  </a>
                </div>
              ))}
            </div>
          )}

          {/* No Results */}
          {results.query_type !== 'error' && !hasResults &&
           !results.comparison && !results.timeline &&
           !(results.similar?.similar_sessions?.length > 0) &&
           !(results.speaker_comparison && Object.keys(results.speaker_comparison).length > 0) && (
            <div className="no-results">
              <p>No results found for your query.</p>
              <p>Try rephrasing or using different keywords.</p>
            </div>
          )}

          {/* Comparative Analysis */}
          {results.comparison && Object.keys(results.comparison).length > 0 && (
            <>
              <h3>Session Comparison</h3>
              <div className="comparison-grid">
                {Object.entries(results.comparison).map(([label, data]) => (
                  <div key={label} className="comparison-card">
                    <h4>{label}</h4>
                    {data.text_preview && (
                      <p className="comparison-preview">{data.text_preview.substring(0, 150)}...</p>
                    )}
                    <div className="comparison-metrics">
                      <h5>7C Quality Scores</h5>
                      <MetricRow label="Communication" value={data.metrics?.communication_score} />
                      <MetricRow label="Constructive" value={data.metrics?.constructive_score} />
                      <MetricRow label="Contribution" value={data.metrics?.contribution_score} />
                      <MetricRow label="Climate" value={data.metrics?.climate_score} />
                      <MetricRow label="Conflict Resolution" value={data.metrics?.conflict_score} />
                    </div>
                    {data.argumentation?.has_concept_map && (
                      <div className="comparison-argumentation">
                        <h5>Argumentation</h5>
                        <p><strong>Debate Score:</strong> {data.argumentation.debate_score}</p>
                        <p><strong>Reasoning Depth:</strong> {data.argumentation.reasoning_depth}</p>
                        <p><strong>Challenges:</strong> {data.argumentation.challenge_count}</p>
                      </div>
                    )}
                    {data.evolution?.has_evolution && (
                      <div className="comparison-evolution">
                        <h5>Evolution Over Time</h5>
                        <p><strong>Analytic:</strong> {data.evolution.analytic_evolution > 0 ? '+' : ''}{data.evolution.analytic_evolution}</p>
                        <p><strong>Tone:</strong> {data.evolution.tone_evolution > 0 ? '+' : ''}{data.evolution.tone_evolution}</p>
                      </div>
                    )}
                    <div className="comparison-stats">
                      <p><strong>Transcripts:</strong> {data.total_chunks}</p>
                      <p><strong>Speakers:</strong> {data.unique_speakers}</p>
                      <p><strong>Type:</strong> {data.discourse_type}</p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Timeline */}
          {results.timeline && (
            <>
              <h3>Timeline Analysis</h3>
              <div className="timeline-summary">
                <p><strong>Duration:</strong> {Math.floor(results.summary?.total_duration / 60)} minutes</p>
                <p><strong>Data Points:</strong> {results.summary?.total_chunks}</p>
              </div>
              <div className="timeline-chart">
                {results.timeline.slice(0, 20).map((point, idx) => (
                  <div key={idx} className="timeline-point">
                    <span className="timeline-time">{formatTime(point.time)}</span>
                    <div className="timeline-metrics">
                      <span>Tone: {point.metrics.emotional_tone.toFixed(0)}</span>
                      <span>Analytic: {point.metrics.analytic_thinking.toFixed(0)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// Helper component for metric rows in comparison
function MetricRow({ label, value }) {
  const safeValue = value ?? 0;
  return (
    <div className="metric-row">
      <span className="metric-label">{label}:</span>
      <div className="metric-bar">
        <div className="metric-fill" style={{width: `${safeValue}%`}}></div>
        <span className="metric-value">{safeValue.toFixed(0)}</span>
      </div>
    </div>
  );
}

export { RagSearchComponent };