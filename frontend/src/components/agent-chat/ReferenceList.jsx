/**
 * Reference List Component
 *
 * Displays a grouped list of citations at the end of a message.
 * Each reference is clickable to show the citation popover.
 */

import React from 'react';
import styles from './ReferenceList.module.css';

// Type display names
const TYPE_NAMES = {
    transcript: 'Transcript Quotes',
    concept: 'Concepts',
    '7c': '7C Dimensions',
    cluster: 'Theme Clusters',
    session: 'Session Overviews',
    speaker: 'Speaker Profiles'
};

/**
 * Group citations by type.
 */
const groupByType = (citations) => {
    const grouped = {};
    citations.forEach(cite => {
        const type = cite.citationType || 'transcript';
        if (!grouped[type]) {
            grouped[type] = [];
        }
        grouped[type].push(cite);
    });
    return grouped;
};

const ReferenceList = ({ citations, onCitationClick }) => {
    if (!citations || citations.length === 0) {
        return null;
    }

    const grouped = groupByType(citations);

    return (
        <div className={styles.referenceList}>
            {/* Header */}
            <div className={styles.header}>
                <span className={styles.title}>References ({citations.length})</span>
            </div>

            {/* Grouped references */}
            <div className={styles.groups}>
                {Object.entries(grouped).map(([type, cites]) => (
                    <ReferenceGroup
                        key={type}
                        type={type}
                        citations={cites}
                        onCitationClick={onCitationClick}
                    />
                ))}
            </div>
        </div>
    );
};

/**
 * A group of references of the same type.
 */
const ReferenceGroup = ({ type, citations, onCitationClick }) => {
    const typeName = TYPE_NAMES[type] || 'References';

    return (
        <div className={styles.group}>
            <div className={styles.groupHeader}>
                <span className={styles.groupName}>{typeName}</span>
                <span className={styles.groupCount}>{citations.length}</span>
            </div>
            <div className={styles.items}>
                {citations.map((cite, idx) => (
                    <ReferenceItem
                        key={cite.id || idx}
                        citation={cite}
                        onCitationClick={onCitationClick}
                    />
                ))}
            </div>
        </div>
    );
};

/**
 * A single reference item.
 */
const ReferenceItem = ({ citation, onCitationClick }) => {
    const handleClick = (e) => {
        if (onCitationClick) {
            onCitationClick(citation, e);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && onCitationClick) {
            onCitationClick(citation, e);
        }
    };

    const citationType = citation.citationType || 'transcript';

    return (
        <div
            className={`${styles.item} ${styles[`item_${citationType}`] || ''}`}
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            role="button"
            tabIndex={0}
            title="Click to view details"
        >
            <span className={styles.refId}>[{citation.id}]</span>
            <span className={styles.refText}>
                {citation.referenceText || citation.inlineText}
            </span>
        </div>
    );
};

export default ReferenceList;
