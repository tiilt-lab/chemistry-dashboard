import React, { useState, useEffect } from 'react';
import styles from './dimension-schema-editor.module.css';

/**
 * DimensionSchemaEditor — Two-column Active / Inactive pool with batch confirm
 *
 * Active column:   dimensions currently on in this session.  Click → pending deactivate.
 * Inactive column: dimensions in the pool but off.           Click → pending activate.
 *
 * Changes are applied only when the user clicks "Confirm".
 * "Remove from pool" (✕ icon) permanently deletes from the pool immediately.
 *
 * Props:
 *   onClose          — close the modal
 *   onSchemaChange   — callback after pool changes
 *   sessionDeviceId  — current session (for activate/deactivate)
 *   onSessionChange  — callback after per-session changes
 */
const DimensionSchemaEditor = ({ onClose, onSchemaChange, sessionDeviceId, onSessionChange }) => {
    const [pool, setPool] = useState(null);
    const [sessionDims, setSessionDims] = useState(null);   // confirmed truth from server
    const [pendingDims, setPendingDims] = useState(null);   // user's pending selection (Set | null)
    const [error, setError] = useState(null);
    const [isAddingDim, setIsAddingDim] = useState(false);
    const [newDim, setNewDim] = useState({ key: '', name: '', description: '', indicators: '', scoring_criteria: '', color: 'rgba(150, 150, 150, 0.35)' });
    const [isSaving, setIsSaving] = useState(false);
    const [removingDim, setRemovingDim] = useState(null);   // dim key being permanently removed
    const [isApplying, setIsApplying] = useState(false);

    useEffect(() => {
        fetchPool();
        if (sessionDeviceId) fetchSessionDims();
    }, [sessionDeviceId]); // eslint-disable-line react-hooks/exhaustive-deps

    // Initialise pendingDims from sessionDims on first load
    useEffect(() => {
        if (sessionDims !== null && pendingDims === null) {
            setPendingDims(new Set(sessionDims));
        }
    }, [sessionDims, pendingDims]);

    const fetchPool = async () => {
        try {
            const res = await fetch('/api/v1/dimension-schemas/default');
            if (res.ok) { const data = await res.json(); setPool(data.dimensions || []); }
            else setError('Failed to load dimension pool');
        } catch (_) { setError('Failed to load dimension pool'); }
    };

    const fetchSessionDims = async () => {
        if (!sessionDeviceId) return null;
        try {
            const res = await fetch(`/api/v1/seven-cs/results/${sessionDeviceId}`);
            if (res.ok) {
                const data = await res.json();
                const dims = data.summary ? Object.keys(data.summary) : null;
                setSessionDims(dims);
                return dims;
            }
        } catch (_) {}
        return null;
    };

    const slugify = (str) => str.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');

    const handleNameChange = (val) => {
        const updated = { ...newDim, name: val };
        if (!newDim.key || newDim.key === slugify(newDim.name)) updated.key = slugify(val);
        setNewDim(updated);
    };

    const addToPool = async () => {
        if (!newDim.key || !newDim.name) { setError('Name and key are required'); return; }
        setIsSaving(true);
        setError(null);
        try {
            const body = {
                key: newDim.key,
                name: newDim.name,
                description: newDim.description,
                indicators: newDim.indicators ? newDim.indicators.split(',').map(s => s.trim()).filter(Boolean) : [],
                scoring_criteria: newDim.scoring_criteria,
                color: newDim.color,
            };
            const res = await fetch('/api/v1/dimension-pool/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (res.ok) {
                setNewDim({ key: '', name: '', description: '', indicators: '', scoring_criteria: '', color: 'rgba(150, 150, 150, 0.35)' });
                setIsAddingDim(false);
                await fetchPool();
                if (onSchemaChange) onSchemaChange();
            } else {
                const data = await res.json();
                setError(data.error || 'Failed to add dimension');
            }
        } catch (_) { setError('Failed to add dimension'); }
        finally { setIsSaving(false); }
    };

    const removeFromPool = async (dimKey, e) => {
        e.stopPropagation();
        if (!window.confirm(`Remove "${dimKey}" from the pool permanently? This also removes it from ALL sessions.`)) return;
        setRemovingDim(dimKey);
        setError(null);
        try {
            const res = await fetch('/api/v1/dimension-pool/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: dimKey }),
            });
            if (res.ok) {
                setPendingDims(prev => { if (!prev) return prev; const next = new Set(prev); next.delete(dimKey); return next; });
                await fetchPool();
                if (sessionDeviceId) await fetchSessionDims();
                if (onSchemaChange) onSchemaChange();
                if (onSessionChange) onSessionChange();
            } else {
                const data = await res.json();
                setError(data.error || 'Failed to remove dimension');
            }
        } catch (_) { setError('Failed to remove dimension'); }
        finally { setRemovingDim(null); }
    };

    const toggleDimPending = (dimKey) => {
        setPendingDims(prev => {
            const next = new Set(prev);
            if (next.has(dimKey)) next.delete(dimKey);
            else next.add(dimKey);
            return next;
        });
    };

    const applyChanges = async () => {
        if (!sessionDeviceId || !pendingDims || !sessionDims) return;
        setIsApplying(true);
        setError(null);
        const currentSet = new Set(sessionDims);
        const toActivate = [...pendingDims].filter(k => !currentSet.has(k));
        const toDeactivate = [...currentSet].filter(k => !pendingDims.has(k));
        try {
            for (const k of toActivate) {
                const res = await fetch(`/api/v1/seven-cs/results/${sessionDeviceId}/activate`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dimension: k }),
                });
                if (!res.ok) { const d = await res.json(); throw new Error(d.error || 'Failed to activate'); }
            }
            for (const k of toDeactivate) {
                const res = await fetch(`/api/v1/seven-cs/results/${sessionDeviceId}/deactivate`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dimension: k }),
                });
                if (!res.ok) { const d = await res.json(); throw new Error(d.error || 'Failed to deactivate'); }
            }
            const newDims = await fetchSessionDims();  // refreshes sessionDims state
            setPendingDims(new Set(newDims || []));     // sync pendingDims to confirmed state
            if (onSessionChange) onSessionChange();
        } catch (e) {
            setError(e.message || 'Failed to apply changes');
        } finally {
            setIsApplying(false);
        }
    };

    const resetPending = () => setPendingDims(sessionDims ? new Set(sessionDims) : new Set());

    const isPendingActive = (dimKey) => pendingDims ? pendingDims.has(dimKey) : (sessionDims && sessionDims.includes(dimKey));
    const hasAnalysis = sessionDims !== null;
    const hasPendingChanges = pendingDims !== null && sessionDims !== null && (
        [...pendingDims].some(k => !sessionDims.includes(k)) ||
        sessionDims.some(k => !pendingDims.has(k))
    );

    // Split pool by pending selection for the two-column layout
    const activeDims   = (pool || []).filter(d => isPendingActive(d.key));
    const inactiveDims = (pool || []).filter(d => !isPendingActive(d.key));

    const renderDimCard = (dim, isActive) => {
        const removing = removingDim === dim.key;
        const dotColor = (dim.color || 'rgba(150,150,150,0.35)').replace('0.35', '1');
        const indicators = Array.isArray(dim.indicators) ? dim.indicators : [];

        return (
            <div
                key={dim.key}
                className={`${styles.dimCard} ${isActive ? styles.dimCardActive : styles.dimCardInactive} ${(removing || isApplying) ? styles.dimCardLoading : ''}`}
                onClick={() => !removing && !isApplying && hasAnalysis && toggleDimPending(dim.key)}
                title={hasAnalysis ? (isActive ? 'Click to deactivate' : 'Click to activate') : ''}
            >
                <div className={styles.dimCardHeader}>
                    <span className={styles.dimColorDot} style={{ backgroundColor: dotColor }} />
                    <span className={styles.dimCardName}>{dim.name}</span>
                    <button
                        className={styles.removeBtn}
                        onClick={e => removeFromPool(dim.key, e)}
                        disabled={removing || isApplying}
                        title="Remove from pool permanently"
                    >
                        ✕
                    </button>
                </div>
                {indicators.length > 0 && (
                    <div className={styles.dimIndicators}>
                        {indicators.map(ind => (
                            <span key={ind} className={styles.dimIndicatorChip}>{ind}</span>
                        ))}
                    </div>
                )}
                {dim.description && (
                    <p className={styles.dimCardDesc}>{dim.description}</p>
                )}
            </div>
        );
    };

    return (
        <div className={styles.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
            <div className={styles.container}>
                <div className={styles.header}>
                    <h2>Dimension Pool</h2>
                    <button className={styles.closeBtn} onClick={onClose}>✕</button>
                </div>

                {error && <div className={styles.error}>{error}</div>}

                {pool === null ? (
                    <div className={styles.placeholder}>Loading…</div>
                ) : (
                    <>
                        {hasAnalysis ? (
                            /* ── Two-column layout when session has an analysis ── */
                            <div className={styles.twoColLayout}>
                                <div className={styles.poolColumn}>
                                    <div className={styles.columnHeader}>
                                        <span className={styles.columnDot} style={{ background: '#22c55e' }} />
                                        Active
                                        <span className={styles.columnCount}>{activeDims.length}</span>
                                    </div>
                                    {activeDims.length === 0 ? (
                                        <div className={styles.emptyCol}>No active dimensions</div>
                                    ) : (
                                        activeDims.map(d => renderDimCard(d, true))
                                    )}
                                </div>

                                <div className={styles.poolColumn}>
                                    <div className={styles.columnHeader}>
                                        <span className={styles.columnDot} style={{ background: '#94a3b8' }} />
                                        Inactive
                                        <span className={styles.columnCount}>{inactiveDims.length}</span>
                                    </div>
                                    {inactiveDims.length === 0 ? (
                                        <div className={styles.emptyCol}>All dimensions active</div>
                                    ) : (
                                        inactiveDims.map(d => renderDimCard(d, false))
                                    )}
                                </div>
                            </div>
                        ) : (
                            /* ── Single-column fallback when no analysis yet ── */
                            <div className={styles.poolList}>
                                {pool.length === 0 ? (
                                    <div className={styles.placeholder}>No dimensions in pool.</div>
                                ) : (
                                    pool.map(dim => {
                                        const indicators = Array.isArray(dim.indicators) ? dim.indicators : [];
                                        return (
                                            <div key={dim.key} className={styles.dimCard}>
                                                <div className={styles.dimCardHeader}>
                                                    <span
                                                        className={styles.dimColorDot}
                                                        style={{ backgroundColor: (dim.color || 'rgba(150,150,150,0.35)').replace('0.35', '1') }}
                                                    />
                                                    <span className={styles.dimCardName}>{dim.name}</span>
                                                    <button
                                                        className={styles.removeBtn}
                                                        onClick={e => removeFromPool(dim.key, e)}
                                                        title="Remove from pool"
                                                    >
                                                        ✕
                                                    </button>
                                                </div>
                                                {indicators.length > 0 && (
                                                    <div className={styles.dimIndicators}>
                                                        {indicators.map(ind => (
                                                            <span key={ind} className={styles.dimIndicatorChip}>{ind}</span>
                                                        ))}
                                                    </div>
                                                )}
                                                {dim.description && <p className={styles.dimCardDesc}>{dim.description}</p>}
                                            </div>
                                        );
                                    })
                                )}
                                <p className={styles.noAnalysisNote}>
                                    Run an analysis first to activate/deactivate dimensions for this session.
                                </p>
                            </div>
                        )}

                        {/* ── Pending changes bar ── */}
                        {hasPendingChanges && (
                            <div className={styles.pendingBar}>
                                <span className={styles.pendingLabel}>Unsaved changes</span>
                                <div className={styles.pendingActions}>
                                    <button className={styles.resetBtn} onClick={resetPending} disabled={isApplying}>
                                        Reset
                                    </button>
                                    <button className={styles.applyBtn} onClick={applyChanges} disabled={isApplying}>
                                        {isApplying ? 'Applying…' : 'Confirm'}
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* ── Add dimension form ── */}
                        <div className={styles.addSection}>
                            {isAddingDim ? (
                                <div className={styles.addForm}>
                                    <h3>Add New Dimension to Pool</h3>
                                    <div className={styles.addFormGrid}>
                                        <div className={styles.formRowFull}>
                                            <label>Name</label>
                                            <input type="text" value={newDim.name} onChange={e => handleNameChange(e.target.value)} className={styles.input} placeholder="e.g. Creativity" />
                                            {newDim.key && (
                                                <span className={styles.keyChip}>
                                                    ID: {newDim.key}
                                                    <button className={styles.keyEditBtn} onClick={() => {
                                                        const custom = window.prompt('Edit dimension ID:', newDim.key);
                                                        if (custom !== null) setNewDim({ ...newDim, key: custom.toLowerCase().replace(/[^a-z0-9]+/g, '_') });
                                                    }}>edit</button>
                                                </span>
                                            )}
                                        </div>
                                        <div className={styles.formRowFull}>
                                            <label>Definition</label>
                                            <textarea value={newDim.description} onChange={e => setNewDim({ ...newDim, description: e.target.value })} className={styles.textarea} rows={2} placeholder="What does this dimension measure?" />
                                        </div>
                                        <div className={styles.formRowFull}>
                                            <label>Indicators <span className={styles.optionalLabel}>(optional, comma-separated)</span></label>
                                            <input type="text" value={newDim.indicators} onChange={e => setNewDim({ ...newDim, indicators: e.target.value })} className={styles.input} placeholder="e.g. novel ideas, divergent thinking" />
                                        </div>
                                        <div className={styles.formRowFull}>
                                            <label>Scoring Criteria <span className={styles.optionalLabel}>(optional)</span></label>
                                            <textarea value={newDim.scoring_criteria} onChange={e => setNewDim({ ...newDim, scoring_criteria: e.target.value })} className={styles.textarea} rows={2} placeholder="How should this dimension be scored?" />
                                        </div>
                                    </div>
                                    <div className={styles.addFormActions}>
                                        <button onClick={addToPool} disabled={isSaving} className={styles.saveBtn}>
                                            {isSaving ? 'Adding…' : 'Add to Pool'}
                                        </button>
                                        <button onClick={() => { setIsAddingDim(false); setError(null); }} className={styles.cancelBtn}>
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <button onClick={() => setIsAddingDim(true)} className={styles.addDimBtn}>
                                    + Add New Dimension
                                </button>
                            )}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default DimensionSchemaEditor;
