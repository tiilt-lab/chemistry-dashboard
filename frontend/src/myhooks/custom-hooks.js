import React from 'react';
import * as d3 from 'd3';

const useD3 =(renderChartFn, dependencies) => {
    const ref = React.useRef();

    React.useEffect(() => {
        renderChartFn(d3.select(ref.current));
        return () => {};
      }, dependencies);
    return ref;
}

const isLargeScreen = () => {
    return window.innerWidth >= 400;
}

const adjDim = (n) => {
    return isLargeScreen() ? n : (window.innerWidth * n / 400);
}

// Live theme flag: re-renders when the .dark class on <html> changes, so
// canvas/SVG charts (which resolve colors at draw time) can repaint on the
// theme toggle instead of keeping stale colors until navigation.
const useIsDark = () => {
    const get = () =>
        typeof document !== "undefined" &&
        document.documentElement.classList.contains("dark")
    const [dark, setDark] = React.useState(get)
    React.useEffect(() => {
        const observer = new MutationObserver(() => setDark(get()))
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ["class"],
        })
        return () => observer.disconnect()
    }, [])
    return dark
}

// parses topic models as they currently are
const unpackTopModels = (topModels) => {
    for (let i = 0; i < topModels.length; i++) {
      let split = topModels[i].summary.split("\n");
      if (split.length > 1) {
        topModels[i].summary = split[0];
        //but it's not just this. you have to go and select the topics that were selected
        //then interaction where you can print the data if it exists for each topic
        topModels[i].data = split[1];
      }
    }
    return topModels
}

export {useD3, isLargeScreen, adjDim, unpackTopModels, useIsDark}
