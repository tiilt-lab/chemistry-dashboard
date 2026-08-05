/**
 * Citation Popover Component
 *
 * Displays artifact preview when a citation is clicked.
 * Uses React Portal to render above all other content.
 *
 * Features:
 * - Click outside to close
 * - Escape key to close
 * - Smart positioning to stay in viewport
 * - Type-specific preview content
 */

import React, { useRef, useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import styles from './CitationPopover.module.css';

// Type display names (no icons - removed per user request)
const TYPE_NAMES = {
    transcript: 'Transcript Quote',
    concept: 'Concept',
    '7c': '7C Dimension',
    cluster: 'Theme Cluster',
    session: 'Session Overview',
    speaker: 'Speaker Profile'
};

const CitationPopover = ({ citation, position, onClose }) => {
    const popoverRef = useRef(null);
    const [popoverStyle, setPopoverStyle] = useState({});

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (popoverRef.current && !popoverRef.current.contains(event.target)) {
                onClose();
            }
        };

        // Use mousedown for earlier detection
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [onClose]);

    // Close on Escape key
    useEffect(() => {
        const handleEscape = (event) => {
            if (event.key === 'Escape') {
                onClose();
            }
        };

        document.addEventListener('keydown', handleEscape);
        return () => document.removeEventListener('keydown', handleEscape);
    }, [onClose]);

    // Calculate position to stay in viewport
    useEffect(() => {
        if (!popoverRef.current || !position) return;

        const rect = popoverRef.current.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        let left = position.x + 10;
        let top = position.y + 10;

        // Adjust if too close to right edge
        if (left + rect.width + 20 > viewportWidth) {
            left = viewportWidth - rect.width - 20;
        }

        // Adjust if too close to bottom
        if (top + rect.height + 20 > viewportHeight) {
            top = position.y - rect.height - 10;
        }

        // Ensure not off-screen left/top
        left = Math.max(10, left);
        top = Math.max(10, top);

        setPopoverStyle({ left, top });
    }, [position]);

    if (!citation) return null;

    const citationType = citation.citationType || 'transcript';
    const typeName = TYPE_NAMES[citationType] || 'Reference';
    const preview = citation.preview || {};
    const artifactRef = citation.artifactRef || {};

    // Render using portal
    return ReactDOM.createPortal(
        <div
            ref={popoverRef}
            className={styles.popover}
            style={popoverStyle}
            role="dialog"
            aria-label={`${typeName} preview`}
        >
            {/* Header */}
            <div className={styles.header}>
                <span className={styles.title}>{preview.title || typeName}</span>
                <button
                    className={styles.closeBtn}
                    onClick={onClose}
                    aria-label="Close popover"
                >
                    ×
                </button>
            </div>

            {/* Content */}
            <div className={styles.content}>
                {renderPreviewContent(citationType, citation)}
            </div>

            {/* Footer with type badge */}
            <div className={styles.footer}>
                <span className={`${styles.typeBadge} ${styles[citationType]}`}>
                    {typeName}
                </span>
                {artifactRef.sessionId && (
                    <span className={styles.sessionBadge}>
                        Session {artifactRef.sessionId}
                    </span>
                )}
            </div>
        </div>,
        document.body
    );
};

/**
 * Render preview content based on citation type.
 */
const renderPreviewContent = (type, citation) => {
    const preview = citation.preview || {};
    const metadata = preview.metadata || {};
    const artifactRef = citation.artifactRef || {};

    switch (type) {
        case 'transcript':
            return (
                <div className={styles.transcriptPreview}>
                    {artifactRef.speaker && (
                        <div className={styles.speaker}>
                            <span className={styles.speakerName}>{artifactRef.speaker}</span>
                        </div>
                    )}
                    {preview.content && (
                        <blockquote className={styles.quote}>
                            "{preview.content}"
                        </blockquote>
                    )}
                    <div className={styles.meta}>
                        {metadata.wordCount > 0 && (
                            <span>{metadata.wordCount} words</span>
                        )}
                        {metadata.timestamp && (
                            <span>{formatTimestamp(metadata.timestamp)}</span>
                        )}
                    </div>
                </div>
            );

        case 'concept':
            return (
                <div className={styles.conceptPreview}>
                    {metadata.conceptType && (
                        <span className={`${styles.conceptType} ${styles[metadata.conceptType]}`}>
                            {metadata.conceptType}
                        </span>
                    )}
                    <div className={styles.conceptText}>
                        {preview.content || citation.inlineText}
                    </div>
                    <div className={styles.meta}>
                        {metadata.speaker && (
                            <span>{metadata.speaker}</span>
                        )}
                        {metadata.connections > 0 && (
                            <span>{metadata.connections} connections</span>
                        )}
                    </div>
                </div>
            );

        case '7c':
            return (
                <div className={styles.sevenCPreview}>
                    <div className={styles.dimensionHeader}>
                        <span className={styles.dimensionName}>
                            {metadata.dimension || artifactRef.dimension || 'Dimension'}
                        </span>
                        <div
                            className={styles.scoreCircle}
                            style={getScoreStyle(metadata.score)}
                        >
                            {metadata.score || 0}
                        </div>
                    </div>
                    {preview.content && (
                        <div className={styles.explanation}>
                            {preview.content}
                        </div>
                    )}
                    {metadata.explanation && (
                        <div className={styles.evidence}>
                            <strong>Evidence:</strong> {metadata.explanation}
                        </div>
                    )}
                </div>
            );

        case 'cluster':
            return (
                <div className={styles.clusterPreview}>
                    <div className={styles.clusterName}>
                        {preview.title || preview.content || 'Theme Cluster'}
                    </div>
                    {metadata.keyConcepts && metadata.keyConcepts.length > 0 && (
                        <div className={styles.keyConcepts}>
                            <strong>Key concepts:</strong>
                            <ul>
                                {metadata.keyConcepts.slice(0, 5).map((concept, i) => (
                                    <li key={i}>{concept}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                    {metadata.clusterSize > 0 && (
                        <div className={styles.meta}>
                            <span>{metadata.clusterSize} related concepts</span>
                        </div>
                    )}
                </div>
            );

        case 'session':
            return (
                <div className={styles.sessionPreview}>
                    <div className={styles.sessionTitle}>
                        Session {artifactRef.sessionId} Overview
                    </div>
                    {preview.content && (
                        <div className={styles.sessionSummary}>
                            {preview.content}
                        </div>
                    )}
                    {metadata.participants && metadata.participants.length > 0 && (
                        <div className={styles.participants}>
                            <strong>Participants:</strong> {metadata.participants.join(', ')}
                        </div>
                    )}
                    {metadata.duration && (
                        <div className={styles.meta}>
                            <span>Duration: {formatDuration(metadata.duration)}</span>
                        </div>
                    )}
                </div>
            );

        case 'speaker':
            return (
                <div className={styles.speakerPreview}>
                    <div className={styles.speakerHeader}>
                        <span className={styles.speakerName}>
                            {artifactRef.speaker || preview.title || 'Speaker'}
                        </span>
                    </div>
                    {preview.content && (
                        <div className={styles.speakerBio}>
                            {preview.content}
                        </div>
                    )}
                    <div className={styles.meta}>
                        {metadata.sessionCount > 0 && (
                            <span>{metadata.sessionCount} sessions</span>
                        )}
                        {metadata.utteranceCount > 0 && (
                            <span>{metadata.utteranceCount} utterances</span>
                        )}
                    </div>
                </div>
            );

        default:
            return (
                <div className={styles.defaultPreview}>
                    {preview.content || citation.referenceText || citation.inlineText}
                </div>
            );
    }
};

/**
 * Format timestamp to readable time.
 */
const formatTimestamp = (seconds) => {
    if (!seconds && seconds !== 0) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
};

/**
 * Format duration in seconds to readable string.
 */
const formatDuration = (seconds) => {
    if (!seconds) return '';
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
        return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
};

/**
 * Get score color style based on value.
 */
const getScoreStyle = (score) => {
    if (!score && score !== 0) return {};
    const hue = Math.round((score / 100) * 120); // 0 = red, 120 = green
    return {
        backgroundColor: `hsl(${hue}, 70%, 50%)`,
        color: score > 50 ? '#fff' : '#000'
    };
};

export default CitationPopover;
