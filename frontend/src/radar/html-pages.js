import * as d3 from "d3";

function RadarPage(props){
   //////////fields before code
   //configuration
   if (!props.features.length) { 
     return;
   }
   //console.log(props.features);
   let axesDomain = props.features[0].map(d => d.axis);
   let width = 1152;
   let height = 600;
   let margin = 30;
   let axisCircles = Math.ceil(props.maxValue * 10);
   let graphMax = axisCircles / 10;
   let axesLength =  props.features[0].length;
   let angleSlice = Math.PI * 2 / axesLength;
   let radius = 270;
   let axisLabelFactor = 1.12;
   let dotRadius = 4;
   let format = d3.format("d");
   //plotting
   let rScale = d3.scaleLinear()
      .domain([0, graphMax])
      .range([0, radius]);
   let radarLine = d3.lineRadial()
      .curve(d3["curveCardinalClosed"])
      .radius(d => rScale(d))
      .angle((d, i) => i * angleSlice);
   let color = d3.scaleOrdinal()
      .range(["#EDC951","#CC333F","#00A0B0"]);
   let device = d => ["Only one person for now"][d];
      
   ////////d3 radar chart code
   const svg = d3.select("body")
                 .append("svg")
                 .attr("width", width)
                 .attr("height", height+(margin*2));
   
   console.log(svg);
   
   const containerWidth = width-(margin*2);
   const containerHeight = height-(margin*2);

   const container = svg.append('g')
      .attr("width", containerWidth)
      .attr("height", containerHeight)
      .attr('transform', `translate(${(width/2)+margin}, ${(height/2)+margin})`);
      
   var axisGrid = container.append("g")
      .attr("class", "axisWrapper");

   axisGrid.selectAll(".levels")
	   .data(d3.range(1,(axisCircles+1)).reverse())
	   .enter()
      .append("circle")
      .attr("class", "gridCircle")
      .attr("r", (d, i) => radius/axisCircles*d)
      .style("fill", "#CDCDCD")
      .style("stroke", "#CDCDCD")
      .style("fill-opacity", 0.1);
   
   axisGrid.selectAll('.axisLabel')
      .data(d3.range(1, axisCircles + 1).reverse())
      .join('text')
        .attr('class', 'axisLabel')
        .attr('x', 4)
        .attr('y', d => (-d * radius) / axisCircles)
        .attr('dy', '0.4em')
        .style('font-size', '10px')
        .attr('fill', '#737373')
        .text(d => format(10 * d));

   const axis = axisGrid.selectAll(".axis")
      .data(axesDomain)
      .enter()
      .append("g")
      .attr("class", "axis");
      
   axis.append("line")
	.attr("x1", 0)
	.attr("y1", 0)
	.attr("x2", (d, i) => rScale(graphMax*1.1) * Math.cos(angleSlice*i - Math.PI/2))
	.attr("y2", (d, i) => rScale(graphMax*1.1) * Math.sin(angleSlice*i - Math.PI/2))
	.attr("class", "line")
	.style("stroke", "white")
	.style("stroke-width", "2px");

   axis.append("text")
      .attr("class", "legend")
      .style("font-size", "11px")
      .attr("text-anchor", "middle")
      .attr("font-family", "monospace")
      .attr("dy", "0.35em")
      .attr("x", (d, i) => rScale(graphMax * axisLabelFactor) * Math.cos(angleSlice*i - Math.PI/2))
      .attr("y", (d, i) => rScale(graphMax * axisLabelFactor) * Math.sin(angleSlice*i - Math.PI/2))
      .text(d => d);
   
   const plots = container.append('g')
      .selectAll('g')
      .data(props.features)
      .join('g')
        .attr("data-name", (d, i) => device(i))
        .attr("fill", "none")
        .attr("stroke", "steelblue");

   plots.append('path')
      .attr("d", d => radarLine(d.map(v => v.value)))
      .attr("fill", (d, i) => color(i))
      .attr("fill-opacity", 0.1)
      .attr("stroke", (d, i) => color(i))
      .attr("stroke-width", 2);
      
   console.log("Making it here");
   
   //return 1;
      
   return svg.node();
   
   //return svg;
}   

export {RadarPage}
