/**
 * Follow-Up Suggestions Component
 *
 * Displays clickable suggestion chips for follow-up questions.
 */

import React from 'react';
import styles from './FollowUpSuggestions.module.css';

const FollowUpSuggestions = ({ suggestions, onSelect }) => {
    if (!suggestions || suggestions.length === 0) {
        return null;
    }

    return (
        <div className={styles.container}>
            <span className={styles.label}>Follow up:</span>
            <div className={styles.suggestions}>
                {suggestions.map((suggestion, index) => (
                    <button
                        key={index}
                        className={styles.chip}
                        onClick={() => onSelect(suggestion)}
                    >
                        {suggestion}
                    </button>
                ))}
            </div>
        </div>
    );
};

export default FollowUpSuggestions;
