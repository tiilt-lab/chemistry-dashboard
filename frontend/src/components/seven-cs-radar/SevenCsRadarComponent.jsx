import React, { useEffect, useState, useMemo } from 'react';
import * as d3 from 'd3';
import { useD3, adjDim } from '../../myhooks/custom-hooks';
import styles from './seven-cs-radar.module.css';

// 7C Framework colors - matching SevenCsPanel
const SEVEN_CS_CONFIG = {
  climate: { name: 'Climate', color: '#FFB74D', shortName: 'Climate' },
  communication: { name: 'Communication', color: '#64B5F6', shortName: 'Comms' },
  contribution: { name: 'Contribution', color: '#CDDC39', shortName: 'Contrib' },  // Lime
  conflict: { name: 'Conflict', color: '#EF5350', shortName: 'Conflict' },
  constructive: { name: 'Constructive', color: '#26C6DA', shortName: 'Construct' },
  context: { name: 'Context', color: '#66BB6A', shortName: 'Context' },
  compatibility: { name: 'Compatibility', color: '#BA68C8', shortName: 'Compat' }
};

const DIMENSION_ORDER = ['climate', 'communication', 'contribution', 'conflict', 'constructive', 'context', 'compatibility'];

function SevenCsRadarComponent({ sessionDeviceId, multiSeries, selectedDeviceIds, mode }) {
  const [analysisData, setAnalysisData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Multi-session color palette
  const palette = ["#0173B2", "#DE8F05", "#029E73", "#CC78BC", "#ECE133", "#56B4E9", "#949494", "#F0E442"];

  // Check if we're in multi-session mode
  const isMultiMode = mode === 'Group' && Array.isArray(multiSeries) && multiSeries.length > 0;

  // Fetch 7C analysis data
  useEffect(() => {
    if (!sessionDeviceId && !isMultiMode) return;

    const fetchData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        if (isMultiMode && selectedDeviceIds?.length > 0) {
          // Multi-session: fetch for each selected device
          const results = await Promise.all(
            selectedDeviceIds.map(async (pairId) => {
              const [, deviceId] = pairId.split(':');
              try {
                const response = await fetch(`/api/v1/seven-cs/results/${deviceId}`);
                const data = await response.json();
                if (response.ok && data.status !== 'not_analyzed') {
                  return { pairId, data };
                }
                return { pairId, data: null };
              } catch {
                return { pairId, data: null };
              }
            })
          );
          setAnalysisData(results);
        } else {
          // Single session
          const response = await fetch(`/api/v1/seven-cs/results/${sessionDeviceId}`);
          const data = await response.json();
          if (response.ok && data.status !== 'not_analyzed') {
            setAnalysisData([{ pairId: 'current', data }]);
          } else {
            setAnalysisData(null);
          }
        }
      } catch (err) {
        console.error('[7C Radar] Error fetching data:', err);
        setError('Failed to load 7C analysis');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [sessionDeviceId, isMultiMode, selectedDeviceIds]);

  // Process data for radar chart
  const radarData = useMemo(() => {
    if (!analysisData) return [];

    return analysisData
      .filter(item => item.data !== null)
      .map((item, index) => {
        const summary = item.data.summary || {};
        const data = DIMENSION_ORDER.map(dim => ({
          axis: SEVEN_CS_CONFIG[dim].shortName,
          fullName: SEVEN_CS_CONFIG[dim].name,
          value: (summary[dim]?.score || 0) / 100, // Normalize to 0-1
          dimColor: SEVEN_CS_CONFIG[dim].color
        }));

        // Get label from multiSeries if available
        let label = 'Current Session';
        if (isMultiMode && multiSeries) {
          const match = multiSeries.find(s => s.id === item.pairId);
          if (match) label = match.label;
        }

        return {
          pairId: item.pairId,
          label,
          color: palette[index % palette.length],
          data,
          hasData: data.some(d => d.value > 0)
        };
      });
  }, [analysisData, isMultiMode, multiSeries]);

  // D3 radar chart rendering - match LIWC radar size
  const width = adjDim(340);
  // In multi-mode, add more height for legend (16px per session)
  const legendHeight = isMultiMode ? adjDim(16 * Math.max(radarData.length, 2) + 10) : 0;
  const baseHeight = adjDim(200);
  const topPadding = adjDim(15);  // Extra space for top label (Climate)
  const height = baseHeight + legendHeight;
  const margin = adjDim(10);
  const radius = (baseHeight - margin * 2) / 2;

  const ref = useD3(
    (svg) => {
      svg.selectAll("*").remove();

      const containerWidth = width - margin * 2;
      const containerHeight = height - margin * 2;

      const hasData = radarData.length > 0 && radarData.some(d => d.hasData);
      const axesDomain = DIMENSION_ORDER.map(d => SEVEN_CS_CONFIG[d].name);  // Full dimension names
      const axesLength = axesDomain.length;
      const angleSlice = (Math.PI * 2) / axesLength;

      const container = svg
        .append("g")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .attr("transform", `translate(${width / 2 + margin}, ${(baseHeight) / 2 + margin + topPadding})`);

      // Config
      const axisCircles = 5;
      const graphMax = 1;
      const axisLabelFactor = 1.12;  // Match LIWC radar

      // Scales
      const rScale = d3.scaleLinear().domain([0, graphMax]).range([0, radius]);
      const radarLine = d3
        .lineRadial()
        .curve(d3.curveCardinalClosed)
        .radius(d => rScale(d.value))
        .angle((d, i) => i * angleSlice);

      // Background gradient
      const defs = svg.append("defs");
      const gradient = defs.append("radialGradient")
        .attr("id", "radarGradient")
        .attr("cx", "50%")
        .attr("cy", "50%")
        .attr("r", "50%");
      gradient.append("stop").attr("offset", "0%").attr("stop-color", "#f8fafc");
      gradient.append("stop").attr("offset", "100%").attr("stop-color", "#e2e8f0");

      // Background circle
      container.append("circle")
        .attr("cx", 0)
        .attr("cy", 0)
        .attr("r", radius)
        .attr("fill", "url(#radarGradient)")
        .attr("opacity", 0.5);

      // Grid circles
      const axisGrid = container.append("g").attr("class", "axisWrapper");

      axisGrid
        .selectAll(".levels")
        .data(d3.range(1, axisCircles + 1).reverse())
        .enter()
        .append("circle")
        .attr("class", "gridCircle")
        .attr("r", d => (radius / axisCircles) * d)
        .style("fill", "none")
        .style("stroke", "#cbd5e1")
        .style("stroke-width", 1)
        .style("stroke-dasharray", "3,3")
        .style("opacity", 0.7);

      // Grid labels (percentages)
      axisGrid
        .selectAll(".axisLabel")
        .data(d3.range(1, axisCircles + 1).reverse())
        .join("text")
        .attr("class", "axisLabel")
        .attr("x", 4)
        .attr("y", d => (-d * radius) / axisCircles)
        .attr("dy", "0.4em")
        .style("font-size", "9px")
        .style("font-family", "system-ui, sans-serif")
        .attr("fill", "#94a3b8")
        .text(d => `${d * 20}`);

      // Axes
      const axis = axisGrid
        .selectAll(".axis")
        .data(axesDomain)
        .enter()
        .append("g")
        .attr("class", "axis");

      axis
        .append("line")
        .attr("x1", 0)
        .attr("y1", 0)
        .attr("x2", (d, i) => rScale(graphMax * 1.05) * Math.cos(angleSlice * i - Math.PI / 2))
        .attr("y2", (d, i) => rScale(graphMax * 1.05) * Math.sin(angleSlice * i - Math.PI / 2))
        .style("stroke", "#e2e8f0")
        .style("stroke-width", "1.5px");

      // Axis labels - plain text like LIWC radar
      axis
        .append("text")
        .attr("class", "legend")
        .style("font-size", "11px")
        .style("font-weight", "600")
        .attr("text-anchor", "middle")
        .attr("font-family", "system-ui, sans-serif")
        .attr("dy", "0.35em")
        .attr("x", (d, i) => rScale(graphMax * axisLabelFactor) * Math.cos(angleSlice * i - Math.PI / 2))
        .attr("y", (d, i) => rScale(graphMax * axisLabelFactor) * Math.sin(angleSlice * i - Math.PI / 2))
        .style("fill", "#475569")
        .text((d) => d);

      // No data message
      if (!hasData) {
        container
          .append("text")
          .attr("x", 0)
          .attr("y", 0)
          .attr("text-anchor", "middle")
          .style("font-size", "12px")
          .style("fill", "#94a3b8")
          .style("font-family", "system-ui, sans-serif")
          .text("No 7C analysis available");
        return;
      }

      // Plot polygons for each session
      const plots = container
        .append("g")
        .selectAll("g")
        .data(radarData)
        .join("g")
        .attr("data-name", d => d.label)
        .attr("fill", "none");

      // Add glow filter for polygons
      const filter = defs.append("filter")
        .attr("id", "glow")
        .attr("x", "-50%")
        .attr("y", "-50%")
        .attr("width", "200%")
        .attr("height", "200%");
      filter.append("feGaussianBlur")
        .attr("stdDeviation", "2")
        .attr("result", "coloredBlur");
      const feMerge = filter.append("feMerge");
      feMerge.append("feMergeNode").attr("in", "coloredBlur");
      feMerge.append("feMergeNode").attr("in", "SourceGraphic");

      plots
        .append("path")
        .attr("d", d => radarLine(d.data))
        .attr("fill", d => d.color)
        .attr("fill-opacity", isMultiMode ? 0.12 : 0.2)
        .attr("stroke", d => d.color)
        .attr("stroke-width", 2.5)
        .attr("filter", "url(#glow)")
        .style("transition", "all 0.3s ease");

      // Dots on vertices
      plots
        .selectAll("circle")
        .data(d => d.data.map(point => ({ ...point, color: d.color })))
        .enter()
        .append("circle")
        .attr("r", 4)
        .attr("cx", (d, i) => rScale(d.value) * Math.cos(angleSlice * i - Math.PI / 2))
        .attr("cy", (d, i) => rScale(d.value) * Math.sin(angleSlice * i - Math.PI / 2))
        .style("fill", d => d.color)
        .style("stroke", "#fff")
        .style("stroke-width", 1.5)
        .style("filter", "url(#glow)");

      // Legend for multi-mode
      if (isMultiMode && radarData.length > 0) {
        const legend = svg
          .append("g")
          .attr("class", "legend")
          .attr("transform", `translate(${margin}, ${height - legendHeight + topPadding + 15})`);

        const legendItems = legend
          .selectAll(".legendItem")
          .data(radarData)
          .enter()
          .append("g")
          .attr("class", "legendItem")
          .attr("transform", (d, i) => {
            // Single column layout to fit long session names
            const yPos = i * adjDim(16);
            return `translate(0, ${yPos})`;
          });

        legendItems
          .append("rect")
          .attr("x", 0)
          .attr("y", -4)
          .attr("width", 12)
          .attr("height", 12)
          .attr("rx", 3)
          .style("fill", d => d.color)
          .style("opacity", 0.8);

        legendItems
          .append("text")
          .attr("x", 16)
          .attr("y", 2)
          .attr("dy", "0.1em")
          .style("font-size", "10px")
          .style("font-family", "system-ui, sans-serif")
          .style("fill", "#64748b")
          .text(d => d.label);  // Full session name, no truncation
      }
    },
    [radarData, isMultiMode]
  );

  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <span>Loading 7C analysis...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>{error}</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <svg ref={ref} width={width} height={height + margin * 2 + topPadding}></svg>
      {!radarData.length && !isLoading && (
        <div className={styles.noData}>
          <p>Run 7C Analysis to see results here</p>
        </div>
      )}
    </div>
  );
}

export { SevenCsRadarComponent };
