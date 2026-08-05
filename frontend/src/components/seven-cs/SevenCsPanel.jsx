import React, { useState, useEffect, useCallback, useRef } from 'react';
import styles from './seven-cs.module.css';
import DimensionSchemaEditor from '../dimension-schema/DimensionSchemaEditor';

// Gradient track: fills left of thumb through red→orange→yellow→green, right stays gray
const getSliderBackground = (score) => {
    if (score === 0) return 'linear-gradient(to right, #374151 0%, #374151 100%)';
    let gradientPart;
    if (score <= 40) {
        gradientPart = `#ef4444 0%, #f97316 ${score}%`;
    } else if (score <= 70) {
        gradientPart = `#ef4444 0%, #f97316 40%, #eab308 ${score}%`;
    } else {
        gradientPart = `#ef4444 0%, #f97316 40%, #eab308 70%, #22c55e ${score}%`;
    }
    return `linear-gradient(to right, ${gradientPart}, #374151 ${score}%, #374151 100%)`;
};

const SevenCsPanel = ({ sessionDeviceId, sessionName, deviceName, singleColumn = false, transcriptOpen = false }) => {
    const [analysisData, setAnalysisData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedDimension, setSelectedDimension] = useState(null);
    const [error, setError] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [schemas, setSchemas] = useState([]);
    const [selectedSchemaId, setSelectedSchemaId] = useState(null);
    const [showSchemaEditor, setShowSchemaEditor] = useState(false);
    const [poolDimensions, setPoolDimensions] = useState(null);

    // Card-level score edit (slider inline on the card)
    const [editingCardDim, setEditingCardDim] = useState(null); // dimension key
    const [cardScoreValue, setCardScoreValue] = useState(0);
    const [isSavingCard, setIsSavingCard] = useState(false);

    // Modal unified edit mode (score + explanation + evidence simultaneously)
    const [isModalEditMode, setIsModalEditMode] = useState(false);
    const [modalEditValues, setModalEditValues] = useState({ score: 0, explanation: '', evidence: [] });
    const [isSavingModal, setIsSavingModal] = useState(false);

    // Inline edit mode (used when transcript is open)
    const [inlineEditDim, setInlineEditDim] = useState(null);
    const [inlineEditValues, setInlineEditValues] = useState({ score: 0, explanation: '', evidence: [] });
    const [isSavingInline, setIsSavingInline] = useState(false);

    const explanationRef = useRef(null);
    const inlineExplanationRef = useRef(null);

    // Default 7C fallback for display
    const DEFAULT_SEVEN_CS = {
        climate:       { name: 'Climate',       description: 'Emotional safety, respect, and comfort in group interactions',      color: 'rgba(255, 183, 77, 0.35)' },
        communication: { name: 'Communication', description: 'Quality and effectiveness of information exchange',                  color: 'rgba(100, 181, 246, 0.35)' },
        compatibility: { name: 'Compatibility', description: 'How well group members\' working styles complement each other',      color: 'rgba(186, 104, 200, 0.35)' },
        conflict:      { name: 'Conflict',      description: 'Approaches to handling disagreements and contentious situations',   color: 'rgba(239, 83, 80, 0.35)' },
        context:       { name: 'Context',       description: 'Environmental factors and situational awareness',                   color: 'rgba(102, 187, 106, 0.35)' },
        contribution:  { name: 'Contribution',  description: 'Individual participation and effort balance',                       color: 'rgba(205, 220, 57, 0.35)' },
        constructive:  { name: 'Constructive',  description: 'Goal achievement and mutual benefit',                               color: 'rgba(38, 198, 218, 0.35)' },
    };

    const getDimConfig = (dimKey) => {
        if (poolDimensions) {
            const poolDim = poolDimensions.find(d => d.key === dimKey);
            if (poolDim) return { name: poolDim.name, description: poolDim.description || '', color: poolDim.color || 'rgba(150, 150, 150, 0.35)' };
        }
        if (analysisData?.schema?.dimensions) {
            const schemaDim = analysisData.schema.dimensions.find(d => d.key === dimKey);
            if (schemaDim) return { name: schemaDim.name, description: schemaDim.description || '', color: schemaDim.color || 'rgba(150, 150, 150, 0.35)' };
        }
        if (DEFAULT_SEVEN_CS[dimKey]) return DEFAULT_SEVEN_CS[dimKey];
        return { name: dimKey.charAt(0).toUpperCase() + dimKey.slice(1), description: '', color: 'rgba(150, 150, 150, 0.35)' };
    };

    const editedDimensions = analysisData?.edited_dimensions || {};
    const isEdited = (dimKey) => dimKey in editedDimensions;
    const activeDimensions = analysisData?.summary ? Object.keys(analysisData.summary) : [];

    useEffect(() => {
        if (sessionDeviceId) fetchAnalysisResults();
        fetchSchemas();
        fetchPool();
    }, [sessionDeviceId]); // eslint-disable-line react-hooks/exhaustive-deps

    // Auto-focus explanation textarea when entering modal edit mode
    useEffect(() => {
        if (isModalEditMode && explanationRef.current) {
            explanationRef.current.focus();
        }
    }, [isModalEditMode]);

    // Auto-focus explanation textarea when entering inline edit mode
    useEffect(() => {
        if (inlineEditDim && inlineExplanationRef.current) {
            inlineExplanationRef.current.focus();
        }
    }, [inlineEditDim]);

    // Discard inline edit when transcript closes
    useEffect(() => {
        if (!transcriptOpen && inlineEditDim) {
            setInlineEditDim(null);
        }
    }, [transcriptOpen]); // eslint-disable-line react-hooks/exhaustive-deps

    const fetchSchemas = async () => {
        try {
            const res = await fetch('/api/v1/dimension-schemas');
            if (res.ok) { const data = await res.json(); setSchemas(data); }
        } catch (_) {}
    };

    const fetchPool = async () => {
        try {
            const res = await fetch('/api/v1/dimension-schemas/default');
            if (res.ok) { const data = await res.json(); setPoolDimensions(data.dimensions || []); }
        } catch (_) {}
    };

    const fetchAnalysisResults = async () => {
        if (!sessionDeviceId) return;
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`/api/v1/seven-cs/results/${sessionDeviceId}`);
            const data = await response.json();
            if (response.ok) {
                setAnalysisData(data.status === 'not_analyzed' ? null : data);
            } else {
                setError(data.error || 'Failed to fetch analysis results');
            }
        } catch (_) {
            setError('Failed to connect to server');
        } finally {
            setIsLoading(false);
        }
    };

    const triggerAnalysis = async (schemaId) => {
        if (!sessionDeviceId) return;
        setIsAnalyzing(true);
        setError(null);
        const body = schemaId ? { schema_id: schemaId } : {};
        try {
            const response = await fetch(`/api/v1/seven-cs/analyze/${sessionDeviceId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await response.json();
            if (response.ok) { pollForResults(); }
            else { setError(data.error || 'Failed to start analysis'); setIsAnalyzing(false); }
        } catch (_) {
            setError('Failed to connect to server');
            setIsAnalyzing(false);
        }
    };

    const pollForResults = async () => {
        const maxAttempts = 60;
        let attempts = 0;
        const poll = async () => {
            if (attempts >= maxAttempts) { setError('Analysis timed out. Please try again.'); setIsAnalyzing(false); return; }
            try {
                const response = await fetch(`/api/v1/seven-cs/status/${sessionDeviceId}`);
                const data = await response.json();
                if (data.status === 'completed') { await fetchAnalysisResults(); setIsAnalyzing(false); }
                else if (data.status === 'failed') { setError('Analysis failed. Please try again.'); setIsAnalyzing(false); }
                else { attempts++; setTimeout(poll, 5000); }
            } catch (_) { attempts++; setTimeout(poll, 5000); }
        };
        poll();
    };

    const handleDimensionClick = useCallback((dimension) => {
        if (editingCardDim) return;
        setSelectedDimension(dimension === selectedDimension ? null : dimension);
        setIsModalEditMode(false);
    }, [selectedDimension, editingCardDim]);

    const getScoreColor = (score) => {
        if (score >= 75) return '#4CAF50';
        if (score >= 50) return '#FF9800';
        return '#F44336';
    };

    // ─── Card score edit ───────────────────────────────────────────────────────

    const startCardEdit = (dimension, score, e) => {
        e.stopPropagation();
        setEditingCardDim(dimension);
        setCardScoreValue(score);
    };

    const saveCardScore = async (e) => {
        if (e) e.stopPropagation();
        if (!editingCardDim) return;
        setIsSavingCard(true);
        try {
            const response = await fetch(`/api/v1/seven-cs/results/${sessionDeviceId}/edit`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dimension: editingCardDim, field: 'score', value: cardScoreValue }),
            });
            if (response.ok) {
                await fetchAnalysisResults();
                setEditingCardDim(null);
            }
        } catch (err) {
            console.error('Error saving card score:', err);
        } finally {
            setIsSavingCard(false);
        }
    };

    // ─── Modal unified edit mode ───────────────────────────────────────────────

    const enterModalEditMode = (e) => {
        if (e) e.stopPropagation();
        const dimKey = selectedDimension;
        const dimData = analysisData?.summary?.[dimKey];
        if (!dimData) return;

        if (transcriptOpen) {
            // Redirect to inline edit: close modal, open edit in card
            const values = {
                score: dimData.score ?? 0,
                explanation: dimData.explanation ?? '',
                evidence: Array.isArray(dimData.evidence) ? [...dimData.evidence] : [],
            };
            setSelectedDimension(null);
            setIsModalEditMode(false);
            setInlineEditDim(dimKey);
            setInlineEditValues(values);
        } else {
            setModalEditValues({
                score: dimData.score ?? 0,
                explanation: dimData.explanation ?? '',
                evidence: Array.isArray(dimData.evidence) ? [...dimData.evidence] : [],
            });
            setIsModalEditMode(true);
        }
    };

    const cancelModalEdit = (e) => {
        if (e) e.stopPropagation();
        setIsModalEditMode(false);
    };

    const saveModalEdits = async (e) => {
        if (e) e.stopPropagation();
        if (!selectedDimension || !analysisData) return;

        const dimData = analysisData.summary[selectedDimension];
        const { score, explanation, evidence } = modalEditValues;

        // Normalise evidence: split textarea lines if it's a string (shouldn't be, but guard)
        const newEvidence = (Array.isArray(evidence) ? evidence : evidence.split('\n'))
            .map(l => l.trim())
            .filter(Boolean);

        const changes = [];
        if (score !== dimData.score) changes.push({ field: 'score', value: score });
        if (explanation !== (dimData.explanation ?? '')) changes.push({ field: 'explanation', value: explanation });
        if (JSON.stringify(newEvidence) !== JSON.stringify(dimData.evidence || []))
            changes.push({ field: 'evidence', value: newEvidence });

        if (changes.length === 0) { setIsModalEditMode(false); return; }

        setIsSavingModal(true);
        try {
            for (const { field, value } of changes) {
                await fetch(`/api/v1/seven-cs/results/${sessionDeviceId}/edit`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dimension: selectedDimension, field, value }),
                });
            }
            await fetchAnalysisResults();
            setIsModalEditMode(false);
        } catch (err) {
            console.error('Error saving modal edits:', err);
        } finally {
            setIsSavingModal(false);
        }
    };

    const resetDimension = async (dimension, e) => {
        if (e) e.stopPropagation();
        try {
            const response = await fetch(`/api/v1/seven-cs/results/${sessionDeviceId}/reset/${dimension}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (response.ok) {
                await fetchAnalysisResults();
                setIsModalEditMode(false);
            }
        } catch (err) {
            console.error('Error resetting dimension:', err);
        }
    };

    // ─── Inline edit save / cancel ─────────────────────────────────────────────

    const cancelInlineEdit = () => {
        setInlineEditDim(null);
    };

    const saveInlineEdits = async () => {
        if (!inlineEditDim || !analysisData) return;
        const dimData = analysisData.summary[inlineEditDim];
        const { score, explanation, evidence } = inlineEditValues;

        const newEvidence = (Array.isArray(evidence) ? evidence : evidence.split('\n'))
            .map(l => l.trim())
            .filter(Boolean);

        const changes = [];
        if (score !== dimData.score) changes.push({ field: 'score', value: score });
        if (explanation !== (dimData.explanation ?? '')) changes.push({ field: 'explanation', value: explanation });
        if (JSON.stringify(newEvidence) !== JSON.stringify(dimData.evidence || []))
            changes.push({ field: 'evidence', value: newEvidence });

        if (changes.length === 0) { setInlineEditDim(null); return; }

        setIsSavingInline(true);
        try {
            for (const { field, value } of changes) {
                await fetch(`/api/v1/seven-cs/results/${sessionDeviceId}/edit`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dimension: inlineEditDim, field, value }),
                });
            }
            await fetchAnalysisResults();
            setInlineEditDim(null);
        } catch (err) {
            console.error('Error saving inline edits:', err);
        } finally {
            setIsSavingInline(false);
        }
    };

    // ─── Render helpers ────────────────────────────────────────────────────────

    const renderDimensionCard = (dimension, data) => {
        const config = getDimConfig(dimension);
        const isNullData = data === null;
        const score = data?.score ?? 0;
        const count = analysisData?.counts?.[dimension] || 0;
        const isSelected = selectedDimension === dimension;
        const dimIsEdited = isEdited(dimension);
        const isEditingThisCard = editingCardDim === dimension;
        const isInlineEditing = inlineEditDim === dimension;

        return (
            <div
                key={dimension}
                className={`${styles.dimensionCard} ${isSelected ? styles.selected : ''} ${isNullData ? styles.pendingCard : ''} ${isInlineEditing ? styles.inlineEditingCard : ''}`}
                onClick={() => !isNullData && !isInlineEditing && handleDimensionClick(dimension)}
                style={{ borderLeftColor: config.color }}
            >
                <div className={styles.cardHeader}>
                    <div className={styles.cardTitle}>
                        <h3>{config.name}</h3>
                        {dimIsEdited && <span className={styles.editedBadge}>edited</span>}
                        {isNullData && <span className={styles.pendingBadge}>needs regeneration</span>}
                    </div>
                    {!isNullData && !isInlineEditing && count > 0 && (
                        <span className={styles.segmentCount}>{count} segments</span>
                    )}
                </div>

                {isInlineEditing ? (
                    /* ── Inline full edit (transcript open) ── */
                    <div className={styles.inlineEditBody} onClick={e => e.stopPropagation()}>
                        <div className={styles.modalEditSection}>
                            <label className={styles.editFieldLabel}>Score</label>
                            <div className={styles.sliderRow}>
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={inlineEditValues.score}
                                    onChange={e => setInlineEditValues(v => ({ ...v, score: Number(e.target.value) }))}
                                    className={styles.scoreSlider}
                                    style={{ background: getSliderBackground(inlineEditValues.score) }}
                                />
                                <span className={styles.sliderValue}>{inlineEditValues.score}</span>
                            </div>
                        </div>

                        <div className={styles.modalEditSection}>
                            <label className={styles.editFieldLabel}>Analysis</label>
                            <textarea
                                ref={inlineExplanationRef}
                                value={inlineEditValues.explanation}
                                onChange={e => setInlineEditValues(v => ({ ...v, explanation: e.target.value }))}
                                className={styles.editTextarea}
                                rows={4}
                            />
                        </div>

                        <div className={styles.modalEditSection}>
                            <label className={styles.editFieldLabel}>Key Evidence</label>
                            <textarea
                                value={Array.isArray(inlineEditValues.evidence) ? inlineEditValues.evidence.join('\n') : ''}
                                onChange={e => setInlineEditValues(v => ({ ...v, evidence: e.target.value.split('\n') }))}
                                className={styles.editTextarea}
                                rows={3}
                                placeholder="One evidence item per line"
                            />
                        </div>

                        <div className={styles.inlineEditActions}>
                            <button className={styles.editConfirm} onClick={saveInlineEdits} disabled={isSavingInline}>
                                {isSavingInline ? 'Saving…' : 'Save'}
                            </button>
                            <button className={styles.editCancel} onClick={cancelInlineEdit}>
                                Cancel
                            </button>
                        </div>
                    </div>
                ) : isNullData ? (
                    <p className={styles.explanation} style={{ color: '#94a3b8', fontStyle: 'italic' }}>
                        Dimension activated. Run Re-analyze to generate assessment.
                    </p>
                ) : isEditingThisCard ? (
                    /* ── Card slider edit ── */
                    <div className={styles.cardSliderWrap} onClick={e => e.stopPropagation()}>
                        <div className={styles.sliderRow}>
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={cardScoreValue}
                                onChange={e => setCardScoreValue(Number(e.target.value))}
                                className={styles.scoreSlider}
                                style={{ background: getSliderBackground(cardScoreValue) }}
                            />
                            <span className={styles.sliderValue}>{cardScoreValue}</span>
                        </div>
                        <div className={styles.sliderActions}>
                            <button className={styles.editConfirm} onClick={saveCardScore} disabled={isSavingCard}>
                                {isSavingCard ? '…' : 'OK'}
                            </button>
                            <button className={styles.editCancel} onClick={e => { e.stopPropagation(); setEditingCardDim(null); }}>
                                Cancel
                            </button>
                        </div>
                    </div>
                ) : (
                    <>
                        <div className={styles.scoreSection}>
                            <div
                                className={styles.scoreCircle}
                                style={{ borderColor: getScoreColor(score), cursor: 'pointer' }}
                                onClick={e => startCardEdit(dimension, score, e)}
                                title="Click to edit score"
                            >
                                <span className={styles.scoreValue}>{score}</span>
                                <span className={styles.scoreLabel}>/100</span>
                            </div>
                            <div className={styles.scoreBar}>
                                <div
                                    className={styles.scoreProgress}
                                    style={{ width: `${score}%`, backgroundColor: getScoreColor(score) }}
                                />
                            </div>
                        </div>
                        {data?.explanation && (
                            <p className={styles.explanation}>
                                {data.explanation.length > 150
                                    ? data.explanation.substring(0, 150).replace(/\s+\S*$/, '') + '…'
                                    : data.explanation}
                            </p>
                        )}
                    </>
                )}
            </div>
        );
    };

    const renderEvidenceModal = () => {
        if (!selectedDimension || !analysisData) return null;

        const segments = analysisData.segments?.filter(s => s.dimension === selectedDimension) || [];
        const dimensionData = analysisData.summary?.[selectedDimension];
        const config = getDimConfig(selectedDimension);
        const dimIsEdited = isEdited(selectedDimension);

        const handleBackdropClick = (e) => {
            if (e.target === e.currentTarget) {
                setSelectedDimension(null);
                setIsModalEditMode(false);
            }
        };

        return (
            <div className={styles.modalOverlay} onClick={handleBackdropClick}>
                <div className={styles.modalContainer}>
                    {/* ── Header ── */}
                    <div className={styles.modalHeader}>
                        <div className={styles.modalTitle}>
                            <span
                                className={styles.modalDimensionBadge}
                                style={{ backgroundColor: config.color.replace('0.35', '1') }}
                            />
                            <h3>
                                {config.name}
                                {!isModalEditMode && (
                                    <span className={styles.modalScoreStatic}>
                                        &nbsp;{dimensionData?.score ?? 0}/100
                                    </span>
                                )}
                            </h3>
                            {dimIsEdited && <span className={styles.editedBadge}>edited</span>}
                        </div>
                        <div className={styles.modalHeaderActions}>
                            {dimIsEdited && !isModalEditMode && (
                                <button
                                    className={styles.resetButton}
                                    onClick={e => resetDimension(selectedDimension, e)}
                                >
                                    Reset to AI original
                                </button>
                            )}
                            {!isModalEditMode && (
                                <button className={styles.editButton} onClick={enterModalEditMode}>
                                    Edit
                                </button>
                            )}
                            <button
                                className={styles.modalCloseButton}
                                onClick={() => { setSelectedDimension(null); setIsModalEditMode(false); }}
                            >
                                ✕
                            </button>
                        </div>
                    </div>

                    {/* ── Body ── */}
                    <div className={styles.modalContent}>
                        {isModalEditMode ? (
                            /* ── Edit mode: all three fields at once ── */
                            <>
                                <div className={styles.modalEditSection}>
                                    <label className={styles.editFieldLabel}>Score</label>
                                    <div className={styles.sliderRow}>
                                        <input
                                            type="range"
                                            min="0"
                                            max="100"
                                            value={modalEditValues.score}
                                            onChange={e => setModalEditValues(v => ({ ...v, score: Number(e.target.value) }))}
                                            className={styles.scoreSlider}
                                            style={{ background: getSliderBackground(modalEditValues.score) }}
                                        />
                                        <span className={styles.sliderValue}>{modalEditValues.score}</span>
                                    </div>
                                </div>

                                <div className={styles.modalEditSection}>
                                    <label className={styles.editFieldLabel}>Analysis</label>
                                    <textarea
                                        ref={explanationRef}
                                        value={modalEditValues.explanation}
                                        onChange={e => setModalEditValues(v => ({ ...v, explanation: e.target.value }))}
                                        className={styles.editTextarea}
                                        rows={6}
                                    />
                                </div>

                                <div className={styles.modalEditSection}>
                                    <label className={styles.editFieldLabel}>Key Evidence</label>
                                    <textarea
                                        value={Array.isArray(modalEditValues.evidence) ? modalEditValues.evidence.join('\n') : ''}
                                        onChange={e => setModalEditValues(v => ({ ...v, evidence: e.target.value.split('\n') }))}
                                        className={styles.editTextarea}
                                        rows={5}
                                        placeholder="One evidence item per line"
                                    />
                                </div>

                                <div className={styles.modalEditBar}>
                                    <button className={styles.editConfirm} onClick={saveModalEdits} disabled={isSavingModal}>
                                        {isSavingModal ? 'Saving…' : 'Save'}
                                    </button>
                                    <button className={styles.editCancel} onClick={cancelModalEdit}>
                                        Cancel
                                    </button>
                                </div>
                            </>
                        ) : (
                            /* ── View mode ── */
                            <>
                                <div className={styles.modalExplanation}>
                                    <h4>Analysis</h4>
                                    <p>{dimensionData?.explanation || 'No explanation available.'}</p>
                                </div>

                                <div className={styles.modalEvidence}>
                                    <h4>Key Evidence</h4>
                                    <ul className={styles.modalEvidenceList}>
                                        {dimensionData?.evidence && dimensionData.evidence.length > 0 ? (
                                            dimensionData.evidence.map((item, idx) => (
                                                <li key={idx}>{item}</li>
                                            ))
                                        ) : (
                                            <li className={styles.noEvidence}>No evidence items.</li>
                                        )}
                                    </ul>
                                </div>

                                {segments.length > 0 && (
                                    <div className={styles.modalSegments}>
                                        <h4>Illustrative Segments</h4>
                                        {segments.map((segment, idx) => (
                                            <div
                                                key={idx}
                                                className={styles.modalSegment}
                                                style={{ borderLeftColor: config.color.replace('0.35', '0.8') }}
                                            >
                                                <div className={styles.modalSegmentMeta}>
                                                    <span className={styles.modalTimestamp}>
                                                        {formatTimestamp(segment.start_time)}
                                                    </span>
                                                    {segment.speaker_tag && (
                                                        <span className={styles.modalSpeaker}>{segment.speaker_tag}</span>
                                                    )}
                                                    {segment.confidence && (
                                                        <span className={styles.modalConfidence}>
                                                            {Math.round(segment.confidence * 100)}% confident
                                                        </span>
                                                    )}
                                                </div>
                                                <div className={styles.modalSegmentText}>
                                                    "{segment.text_snippet}"
                                                </div>
                                                {segment.coding_reason && (
                                                    <div className={styles.modalCodingReason}>
                                                        {segment.coding_reason}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    const formatTimestamp = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    // ─── Top-level render states ───────────────────────────────────────────────

    if (isLoading) {
        return (
            <div className={styles.container}>
                <div className={styles.loading}>
                    <div className={styles.spinner} />
                    <p>Loading analysis…</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className={styles.container}>
                <div className={styles.error}>
                    <p>{error}</p>
                    <button onClick={fetchAnalysisResults} className={styles.retryButton}>Retry</button>
                </div>
            </div>
        );
    }

    if (!analysisData || analysisData.status === 'not_analyzed') {
        return (
            <div className={styles.container}>
                <div className={styles.noAnalysis}>
                    <h3>No Collaboration Assessment Available</h3>
                    <p>Click below to analyze this session</p>
                    {schemas.length > 1 && (
                        <select
                            className={styles.schemaSelect}
                            value={selectedSchemaId || ''}
                            onChange={e => setSelectedSchemaId(e.target.value ? parseInt(e.target.value) : null)}
                            style={{ marginBottom: 12 }}
                        >
                            {schemas.map(s => (
                                <option key={s.id} value={s.id}>
                                    {s.schema_name}{s.is_default ? ' (default)' : ''}
                                </option>
                            ))}
                        </select>
                    )}
                    <button
                        onClick={() => triggerAnalysis(selectedSchemaId)}
                        disabled={isAnalyzing}
                        className={styles.analyzeButton}
                    >
                        {isAnalyzing ? 'Analyzing…' : 'Run Analysis'}
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div className={styles.headerInfo}>
                    <h2>Collaboration Assessment</h2>
                </div>
                <div className={styles.headerActions}>
                    {schemas.length > 1 && (
                        <select
                            className={styles.schemaSelect}
                            value={selectedSchemaId || analysisData?.metadata?.schema_id || ''}
                            onChange={e => setSelectedSchemaId(e.target.value ? parseInt(e.target.value) : null)}
                        >
                            {schemas.map(s => (
                                <option key={s.id} value={s.id}>
                                    {s.schema_name}{s.is_default ? ' (default)' : ''}
                                </option>
                            ))}
                        </select>
                    )}
                    <button
                        onClick={() => triggerAnalysis(selectedSchemaId)}
                        disabled={isAnalyzing}
                        className={styles.updateButton}
                    >
                        {isAnalyzing ? 'Analyzing…' : 'Re-analyze'}
                    </button>
                    <button onClick={() => setShowSchemaEditor(true)} className={styles.schemaEditorBtn}>
                        Dimensions
                    </button>
                </div>
            </div>

            <div className={`${styles.dimensionGrid} ${singleColumn ? styles.dimensionGridSingleCol : ''}`}>
                {activeDimensions.map(dimension =>
                    renderDimensionCard(dimension, analysisData?.summary?.[dimension])
                )}
            </div>

            {selectedDimension && renderEvidenceModal()}

            {showSchemaEditor && (
                <DimensionSchemaEditor
                    onClose={() => setShowSchemaEditor(false)}
                    onSchemaChange={() => { fetchSchemas(); fetchPool(); }}
                    sessionDeviceId={sessionDeviceId}
                    onSessionChange={() => fetchAnalysisResults()}
                />
            )}
        </div>
    );
};

export default SevenCsPanel;
