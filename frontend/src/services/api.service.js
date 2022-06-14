
import { Observable } from 'rxjs';

export class ApiService {
  getWSSProtocol() {
    return window.location.protocol === "https:" ? "wss:" : "ws:";
  }

  getEndpoint() {
    return (
      window.location.protocol + "//" + window.location.host.split(":")[0] + "/"
    );
  }

  getWebsocketEndpoint() {
    return (
      this.getWSSProtocol() +
      "//" +
      window.location.host.split(":")[0] +
      "/audio_socket"
    );
  }

  httpRequestCall(apipath, type, data, tomodel) {
    // Default options are marked with *
    return new Observable((subscriber) => {
      //const controller = new AbortController();
      fetch(this.getEndpoint() + apipath, {
        method: type, // *GET, POST, PUT, DELETE, etc.
        mode: 'cors', // no-cors, *cors, same-origin
        //cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
        credentials: 'include', // include, *same-origin, omit
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
          //   // 'Content-Type': 'application/x-www-form-urlencoded',
        },
        redirect: 'follow', // manual, *follow, error
        //referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
        body: JSON.stringify(data) // body data type must match "Content-Type" header
      }).then(
          (response) => { 
          if(response.status === 200){
            subscriber.next(response);
            subscriber.complete();
          }else{
            subscriber.error(response)
          }
        },
        (apiError) =>{ 
            apiError.status = 600
            subscriber.error(apiError)}
          )
    })
  }

  httpRequestCallV2(apipath, type, data, tomodel, setError, setValue) {
    // Default options are marked with *
    const controller = new AbortController();
    fetch(this.getEndpoint() + apipath, {
      method: type, // *GET, POST, PUT, DELETE, etc.
      mode: 'same-origin', // no-cors, *cors, same-origin
      //cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
      //credentials: 'include', // include, *same-origin, omit
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
        //   // 'Content-Type': 'application/x-www-form-urlencoded',
      },
      //redirect: 'follow', // manual, *follow, error
      //referrerPolicy: 'origin-when-cross-origin', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
      body: JSON.stringify(data) // body data type must match "Content-Type" header
    })
      .then((response) => { return response.json() })
      .then((dataFromApi) => {
        //if (tomodel) {
        //  setValue(UserModel.fromJson(dataFromApi));
       //} else {
          setValue(dataFromApi);
       // }
      })
      .catch((apiError) => setError(apiError))
    return () => controller.abort()
  }
}