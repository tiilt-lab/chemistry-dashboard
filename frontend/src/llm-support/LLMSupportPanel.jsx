import React, { useState, useMemo } from 'react';
import { adjDim } from '../myhooks/custom-hooks';
import style from './llm-support.module.css';

function LLMSupportPanel(props) {
  const [analysis, setAnalysis] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [taskType, setTaskType] = useState('summary');
  const [usage, setUsage] = useState(null);

  // Calculate current metrics averages
  const currentMetrics = useMemo(() => {
    if (!props.transcripts || props.transcripts.length === 0) return null;
    
    const sums = props.transcripts.reduce((acc, t) => ({
      emotional: acc.emotional + (parseInt(t.emotional_tone_value) || 0),
      analytic: acc.analytic + (parseInt(t.analytic_thinking_value) || 0),
      clout: acc.clout + (parseInt(t.clout_value) || 0),
      authenticity: acc.authenticity + (parseInt(t.authenticity_value) || 0),
      certainty: acc.certainty + (parseInt(t.certainty_value) || 0),
      count: acc.count + 1
    }), { emotional: 0, analytic: 0, clout: 0, authenticity: 0, certainty: 0, count: 0 });
    
    if (sums.count === 0) return null;
    
    return {
      emotional: Math.round(sums.emotional / sums.count),
      analytic: Math.round(sums.analytic / sums.count),
      clout: Math.round(sums.clout / sums.count),
      authenticity: Math.round(sums.authenticity / sums.count),
      certainty: Math.round(sums.certainty / sums.count)
    };
  }, [props.transcripts]);

  // Prepare multi-session data if available
  const prepareMultiSessionData = () => {
    if (!props.multiSeries || props.multiSeries.length < 2) return null;
    
    return props.multiSeries.map(series => {
      const transcripts = series.transcripts || [];
      if (transcripts.length === 0) {
        return {
          name: series.label,
          metrics: null
        };
      }
      
      const sums = transcripts.reduce((acc, t) => ({
        emotional: acc.emotional + (parseInt(t.emotional_tone_value) || 0),
        analytic: acc.analytic + (parseInt(t.analytic_thinking_value) || 0),
        clout: acc.clout + (parseInt(t.clout_value) || 0),
        authenticity: acc.authenticity + (parseInt(t.authenticity_value) || 0),
        certainty: acc.certainty + (parseInt(t.certainty_value) || 0),
        count: acc.count + 1
      }), { emotional: 0, analytic: 0, clout: 0, authenticity: 0, certainty: 0, count: 0 });
      
      return {
        name: series.label,
        metrics: {
          emotional: Math.round(sums.emotional / sums.count),
          analytic: Math.round(sums.analytic / sums.count),
          clout: Math.round(sums.clout / sums.count),
          authenticity: Math.round(sums.authenticity / sums.count),
          certainty: Math.round(sums.certainty / sums.count)
        }
      };
    });
  };

  const generateAnalysis = async () => {
    setLoading(true);
    setError('');
    setAnalysis('');
    
    try {
    
      // Prepare request data based on task type
    const sessionLength = props.session?.length || 0;
    const isFullRange = props.startTime <= 0.01 && 
                       props.endTime >= (sessionLength - 0.01);
    
    // Update requestData to include range info
    let requestData = {
      metrics: currentMetrics,
      transcripts: props.transcripts || [],
      sessionInfo: {
        name: props.sessionDevice?.name || 'Current Session',
        id: props.sessionDevice?.id
      },
      timeRange: {
        start: props.startTime,
        end: props.endTime,
        isFullRange: isFullRange,  
        totalLength: sessionLength  
      }
    };
      
      // Add multi-session data for comparison if available
      if (taskType === 'comparison' && props.multiSeries) {
        requestData.multiSessions = prepareMultiSessionData();
      }
      
      // Call backend API
      const response = await fetch('/api/v1/llm/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          taskType,
          data: requestData
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        setAnalysis(result.result);
        setUsage(result.usage);
      } else {
        setError(result.error || 'Failed to generate analysis');
      }
    } catch (err) {
      console.error('Error generating analysis:', err);
      setError('Failed to connect to analysis service');
    } finally {
      setLoading(false);
    }
  };

  const clearAnalysis = () => {
    setAnalysis('');
    setError('');
    setUsage(null);
  };

  // Check if we have enough data
  const hasData = props.transcripts && props.transcripts.length > 0;
  const hasMultipleSession = props.multiSeries && props.multiSeries.length > 1;

  return (
    <div className={style.llmPanel}>
      {/* Task Selection */}
      <div className={style.controls}>
        <select
          className={style.taskSelect}
          value={taskType}
          onChange={(e) => setTaskType(e.target.value)}
          disabled={loading}
          style={{
            padding: adjDim(6) + 'px',
            marginRight: adjDim(10) + 'px',
            borderRadius: adjDim(4) + 'px',
            border: '1px solid #ddd',
            fontSize: adjDim(14) + 'px'
          }}
        >
          <option value="summary">Summary</option>
          <option value="metrics">Metrics Analysis</option>
          <option value="themes">Extract Themes</option>
          {hasMultipleSession && (
            <option value="comparison">Compare Sessions</option>
          )}
        </select>
        
        <button
          className={style.generateBtn}
          onClick={generateAnalysis}
          disabled={loading || !hasData}
          style={{
            padding: `${adjDim(6)}px ${adjDim(12)}px`,
            marginRight: adjDim(8) + 'px',
            borderRadius: adjDim(4) + 'px',
            border: 'none',
            background: loading || !hasData ? '#ccc' : '#0173B2',
            color: 'white',
            fontSize: adjDim(14) + 'px',
            cursor: loading || !hasData ? 'default' : 'pointer'
          }}
        >
          {loading ? 'Analyzing...' : 'Generate Analysis'}
        </button>
        
        {analysis && (
          <button
            className={style.clearBtn}
            onClick={clearAnalysis}
            style={{
              padding: `${adjDim(6)}px ${adjDim(12)}px`,
              borderRadius: adjDim(4) + 'px',
              border: '1px solid #ddd',
              background: 'white',
              fontSize: adjDim(14) + 'px',
              cursor: 'pointer'
            }}
          >
            Clear
          </button>
        )}
      </div>

      {/* Status Messages */}
      {!hasData && (
        <div className={style.noData} style={{
          padding: adjDim(12) + 'px',
          color: '#666',
          fontSize: adjDim(13) + 'px'
        }}>
          No transcript data available for analysis
        </div>
      )}

      {/* Loading Indicator */}
      {loading && (
        <div className={style.loading} style={{
          padding: adjDim(20) + 'px',
          textAlign: 'center',
          color: '#666',
          fontSize: adjDim(13) + 'px'
        }}>
          <div className={style.spinner} style={{
            border: '3px solid #f3f3f3',
            borderTop: '3px solid #0173B2',
            borderRadius: '50%',
            width: adjDim(30) + 'px',
            height: adjDim(30) + 'px',
            margin: '0 auto ' + adjDim(10) + 'px',
            animation: 'spin 1s linear infinite'
          }} />
          Generating analysis...
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className={style.error} style={{
          padding: adjDim(12) + 'px',
          marginTop: adjDim(10) + 'px',
          background: '#fee',
          border: '1px solid #fcc',
          borderRadius: adjDim(4) + 'px',
          color: '#c00',
          fontSize: adjDim(13) + 'px'
        }}>
          {error}
        </div>
      )}

      {/* Analysis Result */}
      {analysis && (
        <div className={style.analysisResult} style={{
          marginTop: adjDim(12) + 'px',
          padding: adjDim(12) + 'px',
          background: '#f9f9f9',
          border: '1px solid #e0e0e0',
          borderRadius: adjDim(4) + 'px',
          fontSize: adjDim(13) + 'px',
          lineHeight: '1.5',
          whiteSpace: 'pre-wrap'
        }}>
          {analysis}
        </div>
      )}

      {/* Usage Info */}
      {usage && (
        <div className={style.usage} style={{
          marginTop: adjDim(8) + 'px',
          padding: adjDim(6) + 'px',
          fontSize: adjDim(11) + 'px',
          color: '#999',
          textAlign: 'right'
        }}>
          Tokens used: {usage.total_tokens || 0}
        </div>
      )}

      {/* Add CSS animation */}
      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export { LLMSupportPanel };