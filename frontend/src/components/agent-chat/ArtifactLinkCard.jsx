/**
 * Artifact Link Card
 *
 * Compact card rendered below agent messages that links to the referenced
 * session's dashboard page. Shows session name + artifact type icon.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './ArtifactLinkCard.module.css';
import { logStudyAction } from '../../services/study-log-service';

const TYPE_CONFIG = {
  transcript: { label: 'Transcript' },
  concept_map: { label: 'Concept Map' },
  collaboration: { label: 'Assessment' },
};

const ArtifactLinkCard = ({ citation }) => {
  const navigate = useNavigate();

  const { type, session_id, discussion_id, session_name } = citation;
  const config = TYPE_CONFIG[type] || { label: type };

  const handleClick = () => {
    if (discussion_id) {
      const tab = type === 'concept_map' ? 'concept-map' : 'assessment';
      logStudyAction('artifact_card_click', { session_device_id: discussion_id, action_data: { type, tab } });
      const qs = type === 'transcript' ? '?transcript=open' : '';
      navigate(`/app/${discussion_id}/${tab}${qs}`);
    }
  };

  if (!discussion_id) return null;

  return (
    <button className={styles.card} onClick={handleClick} title={`Open ${config.label} for ${session_name}`}>
      <span className={styles.label}>
        <span className={styles.sessionName}>{session_name || `Session ${session_id}`}</span>
        <span className={styles.artifactType}>{config.label}</span>
      </span>
      <span className={styles.arrow}>&rarr;</span>
    </button>
  );
};

export default ArtifactLinkCard;
