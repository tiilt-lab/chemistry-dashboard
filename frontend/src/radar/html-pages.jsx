import { useD3, adjDim } from "../myhooks/custom-hooks";
import React from "react";
import * as d3 from "d3";
import style from "./radar.module.css";

function RadarPage(props) {
  // Basic config
  const width = adjDim(340);
  const height = adjDim(props.isMulti ? 240 : 200); // More height for legend if multi
  const margin = adjDim(10);
  const legendHeight = props.isMulti ? adjDim(40) : 0;
  const radius = (height - margin * 2 - legendHeight) / 2;

  // Process data for rendering
  const processedData = props.features.map(deviceData => {
    let data = deviceData.data.map((d, i) => ({
      ...d,
      value: props.showFeatures[i]?.clicked ? d.value : 0
    }));
    return {
      ...deviceData,
      data: data
    };
  });

  const ref = useD3(
    (svg) => {
      // Clear previous render
      svg.selectAll("*").remove();

      const containerWidth = width - margin * 2;
      const containerHeight = height - margin * 2;

      if (!processedData.length) {
        // Show empty message
        const emptyText = svg
          .append("text")
          .attr("x", width / 2)
          .attr("y", height / 2)
          .attr("text-anchor", "middle")
          .style("font-size", "12px")
          .style("fill", "#999")
          .text("No data available");
        return;
      }
      
      // Check if all devices have zero data
      const hasData = processedData.some(d => d.totalSum > 0);
      if (!hasData) {
        const emptyText = svg
          .append("text")
          .attr("x", width / 2)
          .attr("y", height / 2)
          .attr("text-anchor", "middle")
          .style("font-size", "12px")
          .style("fill", "#999")
          .text("No data in selected time range");
        return;
      }

      const container = svg
        .append("g")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .attr(
          "transform",
          `translate(${width / 2 + margin}, ${height / 2 + margin - legendHeight/2})`
        );

      // Specific config
      let axesDomain = processedData[0]?.data.map((d) => d.axis) || [];
      let axisCircles = Math.ceil(props.maxValue * 10) || 1;
      let graphMax = axisCircles / 10;
      let axesLength = axesDomain.length;
      let angleSlice = (Math.PI * 2) / axesLength;
      let axisLabelFactor = 1.12;
      let format = d3.format("d");
      
      // Plotting scales
      let rScale = d3.scaleLinear().domain([0, graphMax]).range([0, radius]);
      let radarLine = d3
        .lineRadial()
        .curve(d3["curveCardinalClosed"])
        .radius((d) => rScale(d.value))
        .angle((d, i) => i * angleSlice);

      // Grid circles
      var axisGrid = container.append("g").attr("class", "axisWrapper");

      axisGrid
        .selectAll(".levels")
        .data(d3.range(1, axisCircles + 1).reverse())
        .enter()
        .append("circle")
        .attr("class", "gridCircle")
        .attr("r", (d, i) => (radius / axisCircles) * d)
        .style("fill", "#CDCDCD")
        .style("stroke", "#CDCDCD")
        .style("fill-opacity", 0.1);

      // Grid labels
      axisGrid
        .selectAll(".axisLabel")
        .data(d3.range(1, axisCircles + 1).reverse())
        .join("text")
        .attr("class", "axisLabel")
        .attr("x", 4)
        .attr("y", (d) => (-d * radius) / axisCircles)
        .attr("dy", "0.4em")
        .style("font-size", "10px")
        .attr("fill", "#737373")
        .text((d) => format(10 * d));

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
        .attr(
          "x2",
          (d, i) =>
            rScale(graphMax * 1.1) * Math.cos(angleSlice * i - Math.PI / 2)
        )
        .attr(
          "y2",
          (d, i) =>
            rScale(graphMax * 1.1) * Math.sin(angleSlice * i - Math.PI / 2)
        )
        .attr("class", "line")
        .style("stroke", "white")
        .style("stroke-width", "2px");

      axis
        .append("text")
        .attr("class", "legend")
        .style("font-size", "11px")
        .attr("text-anchor", "middle")
        .attr("font-family", "monospace")
        .attr("dy", "0.35em")
        .attr(
          "x",
          (d, i) =>
            rScale(graphMax * axisLabelFactor) *
            Math.cos(angleSlice * i - Math.PI / 2)
        )
        .attr(
          "y",
          (d, i) =>
            rScale(graphMax * axisLabelFactor) *
            Math.sin(angleSlice * i - Math.PI / 2)
        )
        .text((d) => d);

      // Plot polygons for each device
      const plots = container
        .append("g")
        .selectAll("g")
        .data(processedData)
        .join("g")
        .attr("data-name", (d) => d.deviceLabel)
        .attr("fill", "none");

      plots
        .append("path")
        .attr("d", (d) => radarLine(d.data))
        .attr("fill", (d) => d.color)
        .attr("fill-opacity", props.isMulti ? 0.15 : 0.2)
        .attr("stroke", (d) => d.color)
        .attr("stroke-width", 2);

      // Add dots on vertices for multi-mode
      if (props.isMulti) {
        plots
          .selectAll("circle")
          .data((d) => d.data.map(point => ({ ...point, color: d.color })))
          .enter()
          .append("circle")
          .attr("r", 3)
          .attr(
            "cx",
            (d, i) => rScale(d.value) * Math.cos(angleSlice * i - Math.PI / 2)
          )
          .attr(
            "cy",
            (d, i) => rScale(d.value) * Math.sin(angleSlice * i - Math.PI / 2)
          )
          .style("fill", (d) => d.color)
          .style("fill-opacity", 0.8);
      }

      // Legend for multi-mode
      if (props.isMulti && processedData.length > 0) {
        const legend = svg
          .append("g")
          .attr("class", "legend")
          .attr("transform", `translate(${margin}, ${height - legendHeight + 5})`);

        const legendItems = legend
          .selectAll(".legendItem")
          .data(processedData)
          .enter()
          .append("g")
          .attr("class", "legendItem")
          .attr("transform", (d, i) => {
            const itemsPerRow = 2;
            const col = i % itemsPerRow;
            const row = Math.floor(i / itemsPerRow);
            const xPos = col * (containerWidth / itemsPerRow);
            const yPos = row * adjDim(15);
            return `translate(${xPos}, ${yPos})`;
          });

        legendItems
          .append("rect")
          .attr("x", 0)
          .attr("y", 0)
          .attr("width", 10)
          .attr("height", 2)
          .style("fill", (d) => d.color);

        legendItems
          .append("text")
          .attr("x", 15)
          .attr("y", 1)
          .attr("dy", "0.35em")
          .style("font-size", adjDim(10) + "px")
          .style("fill", "#666")
          .text((d) => {
            // Truncate label if too long
            const maxChars = 25;
            return d.deviceLabel.length > maxChars 
              ? d.deviceLabel.substring(0, maxChars) + "..." 
              : d.deviceLabel;
          });
      }
    },
    [processedData, props.showFeatures]
  );

  return (
    <div className="relative small-section h-min">
      <svg ref={ref} width={width} height={height + margin * 2}></svg>
    </div>
  );
}

export { RadarPage };


