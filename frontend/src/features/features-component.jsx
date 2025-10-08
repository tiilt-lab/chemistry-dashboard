import { useEffect, useMemo, useState } from "react";
import { FeaturePage } from "./html-pages";

function AppFeaturesComponent(props) {
  // Check if we're in multi-session Group mode
  const isMultiMode = props.mode === 'Group' && 
                      Array.isArray(props.multiSeries) && 
                      props.multiSeries.length > 0;

  // === ORIGINAL LOGIC FOR INDIVIDUAL/COMPARISON MODES ===
  const svgWidth = 74;
  const svgHeight = 39;
  const [singleFeatures, setSingleFeatures] = useState([]);
  const [featureDescription, setFeatureDescription] = useState(null);
  const [featureHeader, setFeatureHeader] = useState(null);
  const [showFeatureDialog, setShowFeatureDialog] = useState(false);

  // Original updateGraphs for single-transcript mode
  const updateGraphs = () => {
    const valueArrays = [
      { name: 'Emotional tone', values: [] },
      { name: 'Analytic thinking', values: [] },
      { name: 'Clout', values: [] },
      { name: 'Authenticity', values: [] },
      { name: 'Confusion', values: [] }
    ];
    
    props.transcripts.map(t => {
      valueArrays[0].values.push(t.emotional_tone_value);
      valueArrays[1].values.push(t.analytic_thinking_value);
      valueArrays[2].values.push(t.clout_value);
      valueArrays[3].values.push(t.authenticity_value);
      valueArrays[4].values.push(t.certainty_value);
    });
    
    for (const valueArray of valueArrays) {
      const length = valueArray.values.length;
      const average = valueArray.values.reduce((sum, current) => sum + current, 0) / ((length > 0) ? length : 1);
      const last = (length > 0) ? valueArray.values[length - 1] : 0;
      const trend = (last > average) ? 1 : (last === average) ? 0 : -1;
      let path = '';
      for (let i = 0; i < length; i++) {
        const xPos = Math.round(((i + 1) / length) * svgWidth);
        const yPos = svgHeight - Math.round((valueArray.values[i] / 100) * svgHeight);
        path += (i === 0) ? 'M' : 'L';
        path += `${xPos} ${yPos} `;
      }
      valueArray['average'] = average;
      valueArray['last'] = last;
      valueArray['trend'] = trend;
      valueArray['path'] = path;
    }
    setSingleFeatures(valueArrays);
  };

  useEffect(() => {
    if (!isMultiMode) {
      updateGraphs();
    }
  }, [props.transcripts, isMultiMode]);

  // === NEW MULTI-SESSION LOGIC FOR GROUP MODE ===
  const spec = useMemo(
    () => [
      { name: "Emotional tone", key: "emotional_tone_value" },
      { name: "Analytic thinking", key: "analytic_thinking_value" },
      { name: "Clout", key: "clout_value" },
      { name: "Authenticity", key: "authenticity_value" },
      { name: "Confusion", key: "certainty_value" },
    ],
    []
  );

  // Normalize to devices array (only for multi-mode)
  const devices = useMemo(() => {
    if (!isMultiMode) return [];
    
    const src = props.multiSeries;
    if (src && src.length) {
      return src.map((d) => ({
        id: String(d.id),
        label: d.label ?? String(d.id),
        transcripts: Array.isArray(d.transcripts) ? d.transcripts : [],
      }));
    }

    // fallback: single-session from transcripts
    const t = Array.isArray(props.transcripts) ? props.transcripts : [];
    return [{ id: "current", label: "Current session", transcripts: t }];
  }, [props.multiSeries, props.transcripts, isMultiMode]);

  // Compute features with per-device series (only for multi-mode)
  const multiFeatures = useMemo(() => {
    if (!isMultiMode) return [];
    
    const W = 120, H = 36;

    const pathFrom = (values) => {
      const n = values.length;
      if (!n) return "";
      const x = (i) => (n === 1 ? W : i * (W / (n - 1)));
      const y = (v) => H - Math.max(0, Math.min(100, Number(v) || 0)) * (H / 100);
      let d = `M ${x(0)} ${y(values[0])}`;
      for (let i = 1; i < n; i++) d += ` L ${x(i)} ${y(values[i])}`;
      return d;
    };

    const summarize = (arr) => {
      const n = arr.length || 1;
      const sum = arr.reduce((a, v) => a + (Number.isFinite(v) ? v : 0), 0);
      const avg = sum / n;
      const last = arr.length ? arr[arr.length - 1] : 0;
      const trend = last > avg ? 1 : last < avg ? -1 : 0;
      return { average: avg, last, trend };
    };

    return spec.map(({ name, key }) => {
      const series = devices.map((dev) => {
        const values = dev.transcripts.map((t) => Number(t?.[key] ?? 0));
        const { average, last, trend } = summarize(values);
        return {
          deviceId: dev.id,
          deviceLabel: dev.label,
          values,
          average,
          last,
          trend,
          path: pathFrom(values),
        };
      });

      // If only one device in series, still maintain series structure for consistent UI
      return { name, series };
    });
  }, [devices, spec, isMultiMode]);

  // Info dialog handlers
  const getInfo = (name) => {
    const map = {
      "Emotional tone": "Scores above 50 indicate positive tone; below 50 negative.",
      "Analytic thinking": "Scores above 50 indicate analytic thinking; below 50 narrative.",
      Clout: "Higher scores suggest confidence/leadership.",
      Authenticity: "Higher scores suggest more honesty/authenticity.",
      Confusion: "Your pipeline labels this 'certainty'. Higher = more certain.",
    };
    setFeatureDescription(map[name] || null);
    setFeatureHeader(name);
    setShowFeatureDialog(true);
  };
  
  const closeDialog = () => setShowFeatureDialog(false);

  // Choose features based on mode
  const features = isMultiMode ? multiFeatures : singleFeatures;
  const optionList = isMultiMode ? props.deviceOptions : undefined;
  const selectedIds = isMultiMode ? props.selectedDeviceIds : undefined;
  const selectionHandler = isMultiMode ? props.onDeviceSelectionChange : undefined;

  return (
    <FeaturePage
      features={features}
      showFeatures={props.showFeatures}
      deviceOptions={optionList}
      selectedDeviceIds={selectedIds}
      onDeviceSelectionChange={selectionHandler}
      currentSessionDeviceId={props.currentSessionDeviceId}
      featureHeader={featureHeader}
      featureDescription={featureDescription}
      showFeatureDialog={showFeatureDialog}
      closeDialog={closeDialog}
      isMulti={isMultiMode}
      getInfo={getInfo}
      mode={props.mode}
    />
  );
}

export { AppFeaturesComponent };