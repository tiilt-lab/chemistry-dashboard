import { useEffect, useState } from "react";
import {ApiService} from '../services/api-service';
import React from 'react';
import * as d3 from 'd3';

function useLogin(apipath , type,data,tomodel){
    const [value,setValue] = useState();
    const [error,setError] = useState();

    useEffect(()=>{
        if(data!==null){
        new ApiService().httpRequestCallV2(apipath , type,data,tomodel,setError,setValue)
        }
    },[apipath , type,data,tomodel])

    return [error,value];
}

const useD3 = (renderChartFn, dependencies) => {
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

export {useLogin, useD3, isLargeScreen, adjDim, unpackTopModels}
