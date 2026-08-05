import React, { useState, useEffect, useMemo, useRef } from 'react';
import { adjDim } from '../../myhooks/custom-hooks';
import styles from './infographics-comparison.module.css';

function SessionSelectorComponent({ deviceOptions, selectedDeviceIds, onDeviceSelectionChange, currentSessionDeviceId }) {
  // Convert to string arrays for comparison
  const appliedIds = useMemo(
    () => (Array.isArray(selectedDeviceIds) ? selectedDeviceIds.map(String) : []),
    [selectedDeviceIds]
  );

  const options = useMemo(
    () => (Array.isArray(deviceOptions) ? deviceOptions.map(o => ({ id: String(o.id), label: o.label })) : []),
    [deviceOptions]
  );

  const [isOpen, setIsOpen] = useState(false);
  const [pendingIds, setPendingIds] = useState(appliedIds);

  // Sync pending with applied when applied changes
  useEffect(() => setPendingIds(appliedIds), [appliedIds.join(",")]);

  const togglerRef = useRef(null);
  const panelRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    function onDocClick(e) {
      if (!isOpen) return;
      const t = e.target;
      if (t && (t === togglerRef.current || togglerRef.current?.contains(t))) return;
      if (t && (t === panelRef.current || panelRef.current?.contains(t))) return;
      setIsOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [isOpen]);

  const toggleId = (id) => {
    const sid = String(id);
    const currentPairId = String(currentSessionDeviceId);

    // Prevent unchecking current session-device
    if (sid === currentPairId && pendingIds.includes(sid)) {
      return;
    }

    const s = new Set(pendingIds);
    if (s.has(sid)) s.delete(sid); else s.add(sid);
    setPendingIds(Array.from(s));
  };

  const applySelection = () => {
    if (typeof onDeviceSelectionChange === "function") {
      onDeviceSelectionChange(pendingIds);
    }
    setIsOpen(false);
  };

  const removeChip = (id) => {
    const currentPairId = String(currentSessionDeviceId);
    // Prevent removing current session-device
    if (String(id) === currentPairId) return;

    const next = appliedIds.filter(x => x !== String(id));
    if (typeof onDeviceSelectionChange === "function") {
      onDeviceSelectionChange(next);
    }
  };

  const selectedOptions = useMemo(() => {
    const map = new Map(options.map(o => [o.id, o.label]));
    return appliedIds.map(id => ({ id, label: map.get(id) ?? id }));
  }, [appliedIds, options]);

  return (
    <div className={styles.selectorContainer}>
      {/* Chips of applied selection */}
      <div className={styles.selectorChips}>
        {selectedOptions.length === 0 ? (
          <span className={styles.selectorPlaceholder}>Current session</span>
        ) : (
          selectedOptions.map(opt => {
            const isCurrent = opt.id === String(currentSessionDeviceId);
            return (
              <span
                key={opt.id}
                className={`${styles.selectorChip} ${isCurrent ? styles.selectorChipCurrent : ''}`}
              >
                {opt.label}
                {!isCurrent && (
                  <button
                    aria-label={`remove ${opt.label}`}
                    onClick={() => removeChip(opt.id)}
                    className={styles.selectorChipRemove}
                  >
                    &times;
                  </button>
                )}
              </span>
            );
          })
        )}
      </div>

      {/* Trigger button */}
      <div className={styles.selectorDropdownWrapper}>
        <button
          ref={togglerRef}
          className={styles.selectorTrigger}
          onClick={() => setIsOpen(v => !v)}
        >
          Include more sessions
        </button>

        {isOpen && (
          <div ref={panelRef} className={styles.selectorPanel}>
            {/* Apply button at top */}
            <div className={styles.selectorApplyRow}>
              <button className={styles.selectorApplyBtn} onClick={applySelection}>
                Apply
              </button>
            </div>

            {options.length === 0 && (
              <div className={styles.selectorNoOptions}>No devices available</div>
            )}

            {options.map(opt => {
              const checked = pendingIds.includes(opt.id);
              const currentPairId = String(currentSessionDeviceId);
              const isCurrentSession = opt.id === currentPairId;

              return (
                <label
                  key={opt.id}
                  className={`${styles.selectorOption} ${isCurrentSession ? styles.selectorOptionCurrent : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleId(opt.id)}
                    disabled={isCurrentSession && checked}
                  />
                  <span>{opt.label} {isCurrentSession && "(current)"}</span>
                </label>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export { SessionSelectorComponent };
