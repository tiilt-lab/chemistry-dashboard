import * as d3 from "d3";
import { useEffect, useState, useMemo } from 'react';
import { RadarPage } from './html-pages';
import underscore from 'underscore';

function AppRadarComponent(props) {
  const [features, setFeatures] = useState([]);
  const [maxValue, setMaxValue] = useState(0);
  const [valSum, setValSum] = useState(0);
  
  // Check if we're in multi-session mode
  const isMultiMode = props.mode === 'Group' && 
                      Array.isArray(props.multiSeries) && 
                      props.multiSeries.length > 0;

  // Same color palette as Features component
  const palette = ["#0173B2", "#DE8F05", "#029E73", "#CC78BC", "#ECE133", "#56B4E9", "#949494", "#F0E442"];

  // Normalize to devices array
  const devices = useMemo(() => {
    if (!isMultiMode) {
      // Single session mode - use transcripts directly
      return [{ 
        id: "current", 
        label: "Current", 
        transcripts: props.transcripts || [] 
      }];
    }
    
    // Multi-session mode - use multiSeries
    const src = props.multiSeries;
    if (src && src.length) {
      return src.map((d) => ({
        id: String(d.id),
        label: d.label ?? String(d.id),
        transcripts: Array.isArray(d.transcripts) ? d.transcripts : [],
      }));
    }
    
    return [];
  }, [props.multiSeries, props.transcripts, isMultiMode]);

  // Filter devices to only selected ones (for multi-mode)
  const selectedDevices = useMemo(() => {
    if (!isMultiMode || !props.selectedDeviceIds) {
      return devices;
    }
    return devices.filter(d => props.selectedDeviceIds.includes(d.id));
  }, [devices, props.selectedDeviceIds, isMultiMode]);

  useEffect(() => {
    updateGraphs();
  }, [selectedDevices, props.radarTrigger, props.start, props.end, props.showFeatures]);
  
  const updateGraphs = () => {
    if (!selectedDevices || !selectedDevices.length) {
      setFeatures([]);
      setMaxValue(0);
      setValSum(0);
      return;
    }

    // Calculate radar data for each selected device
    const allDeviceFeatures = selectedDevices.map((device, deviceIndex) => {
      const raddata = device.transcripts || [];
      let analytical_sum = 0;
      let authenticity_sum = 0;
      let certainty_sum = 0;
      let clout_sum = 0;
      let emotional_sum = 0;
      
      for (const i in raddata) {
        // Check time range
        //if (!props.start || !props.end || 
           // (props.start <= raddata[i].start_time && raddata[i].start_time <= props.end)) {
          analytical_sum += parseInt(raddata[i].analytic_thinking_value || 0);
          authenticity_sum += parseInt(raddata[i].authenticity_value || 0);
          certainty_sum += parseInt(raddata[i].certainty_value || 0);
          clout_sum += parseInt(raddata[i].clout_value || 0);
          emotional_sum += parseInt(raddata[i].emotional_tone_value || 0);
        //}
      }
      
      const total_sum = analytical_sum + authenticity_sum + 
                       certainty_sum + clout_sum + emotional_sum;
      
      if (total_sum === 0) {
        // No data for this device in time range
        return {
          deviceId: device.id,
          deviceLabel: device.label,
          color: palette[deviceIndex % palette.length],
          data: [
            {"axis": "Emotional", "value": 0},
            {"axis": "Analytical", "value": 0},
            {"axis": "Clout", "value": 0},
            {"axis": "Authenticity", "value": 0},
            {"axis": "Certainty", "value": 0}
          ],
          totalSum: 0
        };
      }
      
      return {
        deviceId: device.id,
        deviceLabel: device.label,
        color: palette[deviceIndex % palette.length],
        data: [
          {"axis": "Emotional", "value": Math.round(100*emotional_sum/total_sum)/100},
          {"axis": "Analytical", "value": Math.round(100*analytical_sum/total_sum)/100},
          {"axis": "Clout", "value": Math.round(100*clout_sum/total_sum)/100},
          {"axis": "Authenticity", "value": Math.round(100*authenticity_sum/total_sum)/100},
          {"axis": "Certainty", "value": Math.round(100*certainty_sum/total_sum)/100}
        ],
        totalSum: total_sum
      };
    });

    // Set features for all devices
    setFeatures(allDeviceFeatures);
    
    // Calculate max value across all devices
    const allValues = allDeviceFeatures.flatMap(f => f.data.map(d => d.value));
    setMaxValue(d3.max(allValues) || 0.4); // Default to 0.4 if no data
    
    // Sum of totals (for validation)
    const totalSum = allDeviceFeatures.reduce((sum, f) => sum + f.totalSum, 0);
    setValSum(totalSum);
  };
  
  return (
    <RadarPage
      features={features}
      maxValue={maxValue}
      valSum={valSum}
      showFeatures={props.showFeatures}
      isMulti={isMultiMode}
    />
  );
}

export { AppRadarComponent };
