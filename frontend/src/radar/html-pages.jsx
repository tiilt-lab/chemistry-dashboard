import { useD3, adjDim } from "../myhooks/custom-hooks";
import React from "react";
import * as d3 from "d3";
import style from "./radar.module.css";

function RadarPage(props) {
  // Basic config
  const width = adjDim(340);
  const height = adjDim(200);
  const margin = adjDim(10);
  const radius = (height - margin * 2) / 2;

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

      // Check if we have data to display
      const hasData = processedData.length > 0 && processedData.some(d => d.totalSum > 0);

      // Use default axes if no data available
      const defaultAxes = ["Emotional", "Analytical", "Clout", "Authenticity", "Certainty"];
      const axesDomain = processedData[0]?.data.map((d) => d.axis) || defaultAxes;

      const container = svg
        .append("g")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .attr(
          "transform",
          `translate(${width / 2 + margin}, ${height / 2 + margin})`
        );

      // Specific config - use defaults when no data
      let axisCircles = hasData ? (Math.ceil(props.maxValue * 10) || 4) : 4;
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

      // Show "no data" message in center if no data, but keep the grid visible
      if (!hasData) {
        container
          .append("text")
          .attr("x", 0)
          .attr("y", 0)
          .attr("text-anchor", "middle")
          .style("font-size", "11px")
          .style("fill", "#999")
          .text("No data in selected range");
      }

      // Plot polygons for each device (only if we have data)
      if (!hasData) return;

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


