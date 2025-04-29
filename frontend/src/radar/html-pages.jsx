import { useD3, adjDim } from "../myhooks/custom-hooks";
import React from "react";
import * as d3 from "d3";
import style from "./radar.module.css";

function RadarPage(props) {
  //basic config
  const width = adjDim(340);
  const height = adjDim(200);
  const margin = adjDim(10);
  const radius = (height - margin * 2) / 2;

  // const data = [props.showFeatures.filter(sf => sf['clicked']).map(sf => props.features[sf['value']])];

  let data = props.features;
  for (let i = 0; i < data.length; i++) {
    if (!props.showFeatures[i]["clicked"]) {
      data[i]["value"] = 0;
    }
  }
  data = [data];

  const ref = useD3(
    (svg) => {
      //d3 code to return regardless
      svg.selectAll("*").remove();

      const containerWidth = width - margin * 2;
      const containerHeight = height - margin * 2;

      if (!(props.valSum && data.length)) {
        return;
      }

      const container = svg
        .append("g")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .attr(
          "transform",
          `translate(${width / 2 + margin}, ${height / 2 + margin})`
        );


      //specific config
      let axesDomain = data[0].map((d) => d.axis);
      let axisCircles = Math.ceil(props.maxValue * 10);
      let graphMax = axisCircles / 10;
      let axesLength = data[0].length;
      let angleSlice = (Math.PI * 2) / axesLength;
      let axisLabelFactor = 1.12;
      let format = d3.format("d");
      //plotting
      let rScale = d3.scaleLinear().domain([0, graphMax]).range([0, radius]);
      let radarLine = d3
        .lineRadial()
        .curve(d3["curveCardinalClosed"])
        .radius((d) => rScale(d))
        .angle((d, i) => i * angleSlice);
      let color = d3.scaleOrdinal().range(["#EDC951", "#CC333F", "#00A0B0"]);
      let device = (d) => ["Only one person for now"][d];

      //d3 radar chart code

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

      const plots = container
        .append("g")
        .selectAll("g")
        .data(data)
        .join("g")
        .attr("data-name", (d, i) => device(i))
        .attr("fill", "none")
        .attr("stroke", "steelblue");

      plots
        .append("path")
        .attr("d", (d) => radarLine(d.map((v) => v.value)))
        .attr("fill", (d, i) => color(i))
        .attr("fill-opacity", 0.1)
        .attr("stroke", (d, i) => color(i))
        .attr("stroke-width", 2);
    },
    [data]
  );

  return (
    <div
      className="relative w-sm h-min"
    >
      <svg ref={ref} width={width} height={height + margin * 2}></svg>
    </div>
  );
}

export { RadarPage };
