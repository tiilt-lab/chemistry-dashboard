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

export {useLogin, useD3, isLargeScreen, adjDim}
