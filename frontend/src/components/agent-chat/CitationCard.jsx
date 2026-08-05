/**
 * Citation Card Component
 *
 * Displays a clickable citation with artifact information.
 */

import React from 'react';
import styles from './CitationCard.module.css';

const CitationCard = ({ citation, sessionDeviceId }) => {
    // Determine icon based on artifact type
    const getIcon = (type) => {
        switch (type) {
            case 'transcript':
                return '📝';
            case 'concept_map':
            case 'concept_graph':
                return '🗺️';
            case 'seven_c':
                return '📊';
            case 'concept_cluster':
                return '🏷️';
            case 'search_result':
                return '🔍';
            default:
                return '📎';
        }
    };

    // Format artifact type for display
    const formatType = (type) => {
        switch (type) {
            case 'transcript':
                return 'Transcript';
            case 'concept_map':
                return 'Concept Map';
            case 'concept_graph':
                return 'Concept Graph';
            case 'seven_c':
                return '7C Analysis';
            case 'concept_cluster':
                return 'Theme Cluster';
            case 'search_result':
                return 'Search Result';
            default:
                return type || 'Citation';
        }
    };

    // Format session reference
    const sessionRef = citation.session_device_id
        ? `Session ${citation.session_device_id}`
        : citation.artifact_id || '';

    // Truncate excerpt
    const excerpt = citation.excerpt
        ? citation.excerpt.length > 100
            ? citation.excerpt.substring(0, 100) + '...'
            : citation.excerpt
        : null;

    const handleClick = () => {
        // In the future, this could open the artifact in a modal or navigate to it
        console.log('Citation clicked:', citation);
    };

    return (
        <div className={styles.card} onClick={handleClick} role="button" tabIndex={0}>
            <div className={styles.header}>
                <span className={styles.icon}>{getIcon(citation.artifact_type)}</span>
                <span className={styles.type}>{formatType(citation.artifact_type)}</span>
                {sessionRef && <span className={styles.session}>{sessionRef}</span>}
            </div>
            {excerpt && (
                <div className={styles.excerpt}>
                    "{excerpt}"
                </div>
            )}
        </div>
    );
};

export default CitationCard;
