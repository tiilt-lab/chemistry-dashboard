import style from "./features.module.css";
import { DialogBox } from "../dialog/dialog-component";
import questIcon from "../assets/img/question.svg";
import { adjDim } from "../myhooks/custom-hooks";
import React, { useMemo, useState, useEffect, useRef } from "react";

function FeaturePage(props) {
  // Only show device picker for Group mode with multi-session (unless hidden by parent)
  const showDevicePicker = props.isMulti && props.mode === 'Group' && !props.hideSessionPicker;

  // Check if we're in multi-session mode (for data processing, separate from UI)
  const isMultiSessionMode = props.isMulti && props.mode === 'Group';

  // === selection state (pending before Apply) - only for multi-session ===
  // Note: appliedIds is used for data filtering regardless of whether picker is shown
  const appliedIds = useMemo(
    () => (isMultiSessionMode && Array.isArray(props.selectedDeviceIds) ? props.selectedDeviceIds.map(String) : []),
    [props.selectedDeviceIds, isMultiSessionMode]
  );
  const options = useMemo(
    () => (isMultiSessionMode && Array.isArray(props.deviceOptions) ? props.deviceOptions.map(o => ({ id: String(o.id), label: o.label })) : []),
    [props.deviceOptions, isMultiSessionMode]
  );
  const [isOpen, setIsOpen] = useState(false);
  const [pendingIds, setPendingIds] = useState(appliedIds);
  useEffect(() => setPendingIds(appliedIds), [appliedIds.join(",")]);

  const togglerRef = useRef(null);
  const panelRef = useRef(null);

  // close on outside click
  useEffect(() => {
    if (!showDevicePicker) return;
    function onDocClick(e) {
      if (!isOpen) return;
      const t = e.target;
      if (t && (t === togglerRef.current || togglerRef.current?.contains(t))) return;
      if (t && (t === panelRef.current || panelRef.current?.contains(t))) return;
      setIsOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [isOpen, showDevicePicker]);

  const toggleId = (id) => {
    const sid = String(id);
    const currentPairId = props.currentSessionDeviceId;

    // Prevent unchecking current session-device
    if (sid === currentPairId && pendingIds.includes(sid)) {
      return;
    }

    const s = new Set(pendingIds);
    if (s.has(sid)) s.delete(sid); else s.add(sid);
    setPendingIds(Array.from(s));
  };
  const applySelection = () => {
    if (typeof props.onDeviceSelectionChange === "function") props.onDeviceSelectionChange(pendingIds);
    setIsOpen(false);
  };
  const removeChip = (id) => {
    const currentPairId = props.currentSessionDeviceId;
    // Prevent removing current session-device
    if (String(id) === currentPairId) return;

    const next = appliedIds.filter(x => x !== String(id));
    if (typeof props.onDeviceSelectionChange === "function") props.onDeviceSelectionChange(next);
  };
  const selectedOptions = useMemo(() => {
    if (!showDevicePicker) return [];
    const map = new Map(options.map(o => [o.id, o.label]));
    return appliedIds.map(id => ({ id, label: map.get(id) ?? id }));
  }, [appliedIds, options, showDevicePicker]);

  // === aggregation helpers ===
  const multiActive = isMultiSessionMode && Array.isArray(props.features);

  const aggAverage = (feature) => {
    if (!multiActive || !Array.isArray(feature.series)) return Math.round(feature.average ?? 0);
    const sel = feature.series.filter(s => appliedIds.includes(String(s.deviceId)));
    if (sel.length === 0) return 0;
    const mean = sel.reduce((acc, s) => acc + (s.average ?? 0), 0) / sel.length;
    return Math.round(mean);
  };

  const aggTrend = (feature) => {
    if (!multiActive || !Array.isArray(feature.series)) return feature.trend ?? 0;
    const sel = feature.series.filter(s => appliedIds.includes(String(s.deviceId)));
    if (sel.length === 0) return 0;
    const avgMean = sel.reduce((acc, s) => acc + (s.average ?? 0), 0) / sel.length;
    const lastMean = sel.reduce((acc, s) => acc + (s.last ?? 0), 0) / sel.length;
    if (lastMean > avgMean) return 1;
    if (lastMean < avgMean) return -1;
    return 0;
  };

  // === ONE overlaid time-axis mini-plot per metric ===
  // Colorblind-friendly palette (using Okabe-Ito colors)
  const palette = ["#0173B2", "#DE8F05", "#029E73", "#CC78BC", "#ECE133", "#56B4E9", "#949494", "#F0E442"];

  const OverlayPlot = ({ feature }) => {
    // Use multi-session style if we're in multi-session mode (even with single selection)
    if (!multiActive || !Array.isArray(feature.series)) {
      // Fallback for non-multi mode (Individual/Comparison views)
      const vals = Array.isArray(feature.values) ? feature.values : [];
      if (!vals.length) return <div className={style["no-data-span"]} style={{ width: adjDim(74) + "px" }} />;
      return (
        <svg viewBox="0 -0.5 74 39.5" className={style.svg} style={{ width: adjDim(74) + "px" }}>
          <path
            d={feature.path}
            fill="none"
            className={feature.trend >= 0 ? style.positive : feature.trend === -1 ? style.negative : ""}
          />
        </svg>
      );
    }

    // Multi-session style (always use when in Group mode, even with 1 selection)
    const sel = feature.series.filter(s => appliedIds.includes(String(s.deviceId)));
    if (sel.length === 0) return <div className={style["no-data-span"]} style={{ width: adjDim(120) + "px" }} />;

    return (
      <svg viewBox="0 0 120 36" className={style.svg} style={{ width: adjDim(120) + "px", height: adjDim(36) + "px" }}>
        {sel.map((s, i) => (
          <path key={s.deviceId} d={pathFrom(s.values)} fill="none" stroke={palette[i % palette.length]} strokeWidth="1.5" />
        ))}
      </svg>
    );
  };

  // simple polyline generator (0..100 to 36px tall)
  function pathFrom(values) {
    const W = 120, H = 36;
    const n = values.length;
    if (!n) return "";
    const safe = values.map(v => Math.max(0, Math.min(100, Number(v) || 0)));
    const x = (i) => (n === 1 ? W : (i * (W / (n - 1))));
    const y = (v) => H - v * (H / 100);
    let d = `M ${x(0)} ${y(safe[0])}`;
    for (let i = 1; i < n; i++) d += ` L ${x(i)} ${y(safe[i])}`;
    return d;
  }

  // === dropdown (chips + list; Apply at TOP; no Cancel) ===
  const DevicePicker = () => (
    <div className="small-section" style={{ marginBottom: adjDim(8) + "px" }}>
      {/* chips of applied selection */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: adjDim(8) + "px", marginBottom: adjDim(8) + "px" }}>
        {selectedOptions.length === 0 ? (
          <span style={{ opacity: 0.7 }}>Current session</span>
        ) : (
          selectedOptions.map(opt => (
            <span
              key={opt.id}
              style={{
                display: "inline-flex", alignItems: "center", gap: adjDim(6) + "px",
                padding: `${adjDim(4)}px ${adjDim(8)}px`, borderRadius: adjDim(12) + "px", background: "var(--chip-bg, #eef)"
              }}
            >
              {opt.label}
              <button
                aria-label={`remove ${opt.label}`}
                onClick={() => removeChip(opt.id)}
                style={{ border: "none", background: "transparent", cursor: "pointer", fontWeight: 700, lineHeight: 1 }}
              >
                ×
              </button>
            </span>
          ))
        )}
      </div>

      {/* trigger */}
      <div style={{ position: "relative" }}>
        <button
          ref={togglerRef}
          className="dropdown"
          style={{
            width: "90%",
            textAlign: "left",
            paddingLeft: adjDim(12) + "px",
            color: "#666"
          }}
          onClick={() => setIsOpen(v => !v)}
        >
          Include more sessions
        </button>

        {isOpen && (
          <div
            ref={panelRef}
            style={{
              position: "absolute", zIndex: 10, top: "100%", left: 0,
              width: "90%",
              background: "white", border: "1px solid #ddd", borderRadius: 8, marginTop: 6, padding: 8,
              maxHeight: 280, overflowY: "auto", boxShadow: "0 4px 12px rgba(0,0,0,0.1)"
            }}
          >
            {/* Apply on top */}
            <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
              <button className="option-button" onClick={applySelection}>Apply</button>
            </div>

            {options.length === 0 && <div style={{ padding: 8, opacity: 0.7 }}>No devices available</div>}

            {options.map(opt => {
              const checked = pendingIds.includes(opt.id);
              const currentPairId = props.currentSessionDeviceId;
              const isCurrentSession = opt.id === currentPairId;

              return (
                <label key={opt.id} style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 8px",
                  cursor: isCurrentSession ? "default" : "pointer",
                  opacity: isCurrentSession ? 0.8 : 1
                }}>
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

  return (
    <>
      {showDevicePicker && <DevicePicker />}

      <div className="small-section">
        {/* Shared legend for multi-session mode (hidden when rendered externally) */}
        {!props.hideLegend && multiActive && Array.isArray(props.features) && props.features.length > 0 && (() => {
          const firstFeature = props.features.find(f => Array.isArray(f?.series));
          if (!firstFeature) return null;
          const sel = firstFeature.series.filter(s => appliedIds.includes(String(s.deviceId)));
          if (sel.length <= 1) return null;
          return (
            <div style={{
              display: "flex",
              flexWrap: "wrap",
              gap: adjDim(12) + "px",
              marginBottom: adjDim(12) + "px",
              padding: adjDim(8) + "px",
              background: "#f8fafc",
              borderRadius: adjDim(6) + "px",
              border: "1px solid #e2e8f0"
            }}>
              {sel.map((s, i) => (
                <span key={s.deviceId} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: adjDim(11) + "px", color: "#475569" }}>
                  <span style={{ width: 14, height: 3, background: palette[i % palette.length], display: "inline-block", borderRadius: 2 }} />
                  {s.deviceLabel}
                </span>
              ))}
            </div>
          );
        })()}

        <table className={style["features-table"]}>
          <thead>
            <tr>
              <th className={style["desc-header"]} style={{ width: adjDim(multiActive ? 150 : 186) + "px" }}>Classifier</th>
              <th className={style["score-header"]} style={{ width: adjDim(multiActive ? 140 : 59) + "px", textAlign: "center" }}>Score</th>
              <th className={style["graph-header"]} style={{ width: multiActive ? adjDim(120) + "px" : adjDim(74) + "px" }}>
                Graph
              </th>
            </tr>
          </thead>

          {Array.isArray(props.features) && props.features.length > 0 && (
            <tbody>
              {props.showFeatures
                .filter(sf => sf["clicked"])
                .map(sf => props.features[sf["value"]])
                .filter(Boolean)
                .map((feature, idx) => {
                  const avg = multiActive ? aggAverage(feature) : Math.round(feature.average);
                  const trend = multiActive ? aggTrend(feature) : feature.trend;

                  return (
                    <tr key={idx}>
                      <td>
                        <img alt="quest" onClick={() => props.getInfo(feature.name)} className={style["info-button"]} src={questIcon} />
                        {feature.name}
                      </td>

                      {/* Score column */}
                      <td className={style.score}>
                        <div style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
                          <div className={style.number} style={{ fontSize: adjDim(22) + "px" }}>{avg}</div>
                          <div
                            className={
                              trend === 1 ? `${style["direction-indicator"]} ${style.positive}`
                                : trend === 0 ? `${style["direction-indicator"]} ${style.neutral}`
                                : `${style["direction-indicator"]} ${style.negative}`
                            }
                          />
                        </div>
                        {multiActive && Array.isArray(feature.series) && (
                          <div style={{ marginTop: adjDim(6) + "px", lineHeight: 1.4 }}>
                            {feature.series
                              .filter(s => appliedIds.includes(String(s.deviceId)))
                              .map((s, i) => (
                                <div key={s.deviceId} style={{
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  gap: 4,
                                  fontSize: adjDim(10) + "px",
                                  color: "#64748b",
                                  marginBottom: 2
                                }}>
                                  <span style={{
                                    width: 8,
                                    height: 2,
                                    background: palette[i % palette.length],
                                    display: "inline-block",
                                    borderRadius: 1,
                                    flexShrink: 0
                                  }} />
                                  <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                    {s.deviceLabel}: {Math.round(s.average)}
                                  </span>
                                </div>
                              ))}
                          </div>
                        )}
                      </td>

                      <td><OverlayPlot feature={feature} /></td>
                    </tr>
                  );
                })}
            </tbody>
          )}
        </table>
      </div>

      {/* Feature info dialog */}
      <DialogBox
        itsclass={"add-dialog"}
        heading={props.featureHeader}
        message={props.featureDescription}
        show={props.showFeatureDialog}
        closedialog={props.closeDialog}
      />
    </>
  );
}

export { FeaturePage };
