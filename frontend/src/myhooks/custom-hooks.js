import { useEffect, useState } from "react";
import {ApiService} from '../services/api.service';

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

export {useLogin}