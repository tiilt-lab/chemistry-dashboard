import React, { useState, useEffect } from 'react';
import style from './speaker-panel.module.css';

function SpeakerPanel({ nodes, onSpeakerSelect, selectedSpeakers }) {
  const [speakers, setSpeakers] = useState([]);
  const [speakerStats, setSpeakerStats] = useState({});

  // Extract unique speakers and calculate stats
  useEffect(() => {
    if (!nodes || nodes.length === 0) return;

    const speakerMap = {};
    const typeCountMap = {};

    nodes.forEach(node => {
      const speakerId = node.speaker_id || 'Unknown';

      if (!speakerMap[speakerId]) {
        speakerMap[speakerId] = {
          id: speakerId,
          name: node.speaker_alias || (speakerId === 'Unknown' ? 'Unknown' : `Speaker ${speakerId}`),
          nodeCount: 0,
          types: {}
        };
      }

      speakerMap[speakerId].nodeCount++;
      
      // Count node types per speaker
      const nodeType = node.type || node.node_type || 'concept';
      if (!speakerMap[speakerId].types[nodeType]) {
        speakerMap[speakerId].types[nodeType] = 0;
      }
      speakerMap[speakerId].types[nodeType]++;
    });

    // Convert to array and sort by contribution
    const speakerList = Object.values(speakerMap).sort((a, b) => b.nodeCount - a.nodeCount);
    
    setSpeakers(speakerList);
    setSpeakerStats(speakerMap);
  }, [nodes]);

  const getTypeColor = (type) => {
    const colors = {
      question: '#e74c3c',
      idea: '#3498db',
      example: '#27ae60',
      problem: '#c0392b',
      solution: '#16a085',
      goal: '#2980b9',
      elaboration: '#34495e'
    };
    return colors[type] || '#95a5a6';
  };

  const getSpeakerColor = (speakerId) => {
    const colors = ['#3498db', '#e74c3c', '#27ae60', '#f39c12', '#9b59b6', '#1abc9c'];
    const index = parseInt(speakerId) || 0;
    return colors[index % colors.length];
  };

  const handleSpeakerClick = (speakerId) => {
    const newSelected = new Set(selectedSpeakers || []);
    if (newSelected.has(speakerId)) {
      newSelected.delete(speakerId);
    } else {
      newSelected.add(speakerId);
    }
    onSpeakerSelect(Array.from(newSelected));
  };

  const selectAll = () => {
    onSpeakerSelect(speakers.map(s => s.id));
  };

  const clearAll = () => {
    onSpeakerSelect([]);
  };

  const totalNodes = nodes ? nodes.length : 0;

  return (
    <div className={style.speakerPanel}>
      <div className={style.header}>
        <h3>Speaker Contributions</h3>
        <div className={style.controls}>
          <button onClick={selectAll} className={style.smallBtn}>All</button>
          <button onClick={clearAll} className={style.smallBtn}>None</button>
        </div>
      </div>

      <div className={style.speakerList}>
        {speakers.map(speaker => {
          const isSelected = selectedSpeakers && selectedSpeakers.includes(speaker.id);
          const percentage = totalNodes > 0 ? Math.round((speaker.nodeCount / totalNodes) * 100) : 0;
          
          return (
            <div
              key={speaker.id}
              className={`${style.speakerCard} ${isSelected ? style.selected : ''}`}
              onClick={() => handleSpeakerClick(speaker.id)}
              style={{
                borderLeft: `4px solid ${getSpeakerColor(speaker.id)}`,
                backgroundColor: isSelected ? `${getSpeakerColor(speaker.id)}15` : 'transparent'
              }}
            >
              <div className={style.speakerHeader}>
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => {}}
                  className={style.checkbox}
                />
                <span className={style.speakerName}>{speaker.name}</span>
                <span className={style.nodeCount}>{speaker.nodeCount}</span>
              </div>
              
              <div className={style.stats}>
                <div className={style.percentage}>
                  <div 
                    className={style.percentageBar}
                    style={{
                      width: `${percentage}%`,
                      backgroundColor: getSpeakerColor(speaker.id)
                    }}
                  />
                  <span className={style.percentageText}>{percentage}%</span>
                </div>
                
                <div className={style.typeBreakdown}>
                  {Object.entries(speaker.types).slice(0, 3).map(([type, count]) => (
                    <span 
                      key={type} 
                      className={style.typeTag}
                      style={{ backgroundColor: getTypeColor(type) }}
                    >
                      {type}: {count}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {speakers.length === 0 && (
        <div className={style.noData}>
          No speaker data available
        </div>
      )}
    </div>
  );
}

export { SpeakerPanel };