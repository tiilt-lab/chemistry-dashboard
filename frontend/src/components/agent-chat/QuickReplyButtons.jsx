/**
 * Quick Reply Buttons Component
 *
 * Versatile component for displaying clickable suggestion buttons.
 * Used for:
 * - Welcome/starter suggestions
 * - Follow-up questions
 * - Clarification options
 * - Fallback examples
 */

import React from 'react';
import styles from './QuickReplyButtons.module.css';

/**
 * Types of quick reply buttons with different styling
 */
export const QuickReplyType = {
    STARTER: 'starter',      // Initial suggestions on empty chat
    FOLLOW_UP: 'follow_up',  // Follow-up questions after response
    CLARIFICATION: 'clarification', // Options when clarifying
    FALLBACK: 'fallback',    // Example questions on error
};

const QuickReplyButtons = ({
    suggestions,
    onSelect,
    type = QuickReplyType.FOLLOW_UP,
    label = null,
    disabled = false,
    autoSubmit = false,  // If true, clicking submits immediately
}) => {
    if (!suggestions || suggestions.length === 0) {
        return null;
    }

    const handleClick = (suggestion) => {
        if (disabled) return;
        onSelect(suggestion, autoSubmit);
    };

    // Get label based on type if not provided
    const displayLabel = label || getDefaultLabel(type);

    // Get container class based on type
    const containerClass = `${styles.container} ${styles[type] || ''}`;

    return (
        <div className={containerClass}>
            {displayLabel && (
                <span className={styles.label}>{displayLabel}</span>
            )}
            <div className={styles.buttons}>
                {suggestions.map((suggestion, index) => (
                    <button
                        key={index}
                        className={`${styles.button} ${disabled ? styles.disabled : ''}`}
                        onClick={() => handleClick(suggestion)}
                        disabled={disabled}
                        title={suggestion}
                    >
                        {truncateSuggestion(suggestion)}
                    </button>
                ))}
            </div>
        </div>
    );
};

/**
 * Get default label based on type
 */
function getDefaultLabel(type) {
    switch (type) {
        case QuickReplyType.STARTER:
            return 'Try asking:';
        case QuickReplyType.FOLLOW_UP:
            return 'Follow up:';
        case QuickReplyType.CLARIFICATION:
            return 'Choose one:';
        case QuickReplyType.FALLBACK:
            return 'Or try:';
        default:
            return null;
    }
}

/**
 * Truncate long suggestions for button display
 */
function truncateSuggestion(suggestion, maxLength = 50) {
    if (suggestion.length <= maxLength) {
        return suggestion;
    }
    return suggestion.substring(0, maxLength - 3) + '...';
}

export default QuickReplyButtons;
