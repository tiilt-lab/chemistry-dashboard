/**
 * TranscriptPanel
 *
 * Inline panel (not a floating overlay) that sits in the transcript column
 * beside the assessment section. Speaker name is read from `speaker_tag`.
 */

import React, { useState, useEffect } from 'react';
import styles from './TranscriptDrawer.module.css';

const SPEAKER_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

const TranscriptPanel = ({ deviceId, onClose }) => {
    const [transcripts, setTranscripts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        if (!deviceId) return;
        setLoading(true);
        setError(null);
        fetch(`/api/v1/devices/${deviceId}/transcripts/client`)
            .then(res => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .then(data => {
                setTranscripts(
                    Array.isArray(data) ? data.sort((a, b) => a.start_time - b.start_time) : []
                );
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [deviceId]);

    const formatTime = (seconds) => {
        if (seconds == null) return '';
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${String(s).padStart(2, '0')}`;
    };

    const filtered = searchQuery.trim()
        ? transcripts.filter(t =>
            (t.transcript || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
            (t.speaker_tag || '').toLowerCase().includes(searchQuery.toLowerCase())
          )
        : transcripts;

    // Color by unique speaker_tag
    const speakerIndex = {};
    transcripts.forEach(t => {
        const name = t.speaker_tag || 'Unknown';
        if (!(name in speakerIndex)) speakerIndex[name] = Object.keys(speakerIndex).length;
    });
    const speakerColor = (name) => SPEAKER_COLORS[speakerIndex[name] % SPEAKER_COLORS.length];

    return (
        <div className={styles.panel}>
            <div className={styles.panelHeader}>
                <div className={styles.panelTitle}>
                    <span>Transcript</span>
                    {!loading && !error && (
                        <span className={styles.utteranceCount}>{transcripts.length} utterances</span>
                    )}
                </div>
                <input
                    className={styles.searchInput}
                    type="text"
                    placeholder="Search…"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                />
            </div>

            <div className={styles.panelBody}>
                {loading && <div className={styles.statusMsg}>Loading transcript…</div>}
                {error && <div className={styles.errorMsg}>Failed to load: {error}</div>}
                {!loading && !error && filtered.length === 0 && (
                    <div className={styles.statusMsg}>
                        {searchQuery ? 'No matching utterances' : 'No transcript available'}
                    </div>
                )}
                {!loading && !error && filtered.map((t, i) => {
                    const name = t.speaker_tag || 'Unknown';
                    const color = speakerColor(name);
                    return (
                        <div key={t.id || i} className={styles.utterance}>
                            <div className={styles.utteranceMeta}>
                                <span className={styles.speakerTag} style={{ borderLeftColor: color, color }}>
                                    {name}
                                </span>
                                {t.start_time != null && (
                                    <span className={styles.timestamp}>{formatTime(t.start_time)}</span>
                                )}
                            </div>
                            <p className={styles.utteranceText}>{t.transcript || ''}</p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default TranscriptPanel;
