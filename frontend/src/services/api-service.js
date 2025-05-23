//import { Observable } from 'rxjs';
export class ApiService {
    getWSSProtocol() {
        return window.location.protocol === "https:" ? "wss:" : "ws:"
    }

    getEndpoint() {
        return window.location.protocol + "//" + window.location.host + "/"
    }

    getVideoServerEndpoint() {
    //   return (
    //     "http://129.105.44.121:8080/"
    //   );
    return (
      "https://video.tiilt-blinc.com"
    );

  }

  getAudioWebsocketEndpoint() {
    return (
      this.getWSSProtocol() +
      "//" +
      // window.location.host.split(":")[0] +
      window.location.host +
      "/audio_socket"
    );
  }

    getVideoWebsocketEndpoint() {
    //   return (
    //     "ws://129.105.44.121:8080/video_socket"
    //   );
    return (
      "wss://video.tiilt-blinc.com/video_socket"
    );
  }

   _generateHeaders(headers,data) {
    let h = {}
    if(!(data instanceof FormData)){
      h =  {
        "Content-Type": "application/json",
        "Accept": "application/json"
      };
    }

        let key = '';
        let val ='';
      for (const property in headers) {
        if (headers.hasOwnProperty(property)) {
          key = (typeof property === 'string')? property : JSON.stringify(property)
          val = (typeof headers[property] === 'string')? headers[property] : JSON.stringify(headers[property])
          h[key] = val;
         // h[property] = headers[property];
        }
      }
      return h;
    }

    get(apipath, headers) {
        return fetch(this.getEndpoint() + apipath, {
            method: "GET", // *GET, POST, PUT, DELETE, etc.
            mode: "cors", // no-cors, *cors, same-origin
            //cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
            credentials: "include", // include, *same-origin, omit
            headers: this._generateHeaders(headers),
            redirect: "follow", // manual, *follow, error
            //referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
        })
    }

    delete(apipath, headers) {
        return fetch(this.getEndpoint() + apipath, {
            method: "DELETE", // *GET, POST, PUT, DELETE, etc.
            mode: "cors", // no-cors, *cors, same-origin
            //cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
            credentials: "include", // include, *same-origin, omit
            headers: this._generateHeaders(headers),
            redirect: "follow", // manual, *follow, error
            //referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
        })
    }

    post(apipath, data, headers) {
        return fetch(this.getEndpoint() + apipath, {
            method: "POST", // *GET, POST, PUT, DELETE, etc.
            mode: "cors", // no-cors, *cors, same-origin
            //cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
            credentials: "include", // include, *same-origin, omit
            headers: this._generateHeaders(headers, data),
            redirect: "follow", // manual, *follow, error
            //referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
            body: JSON.stringify(data), // body data type must match "Content-Type" header
        })
    }

    postFiles(apipath, data) {
        return fetch(this.getEndpoint() + apipath, {
            method: "POST", // *GET, POST, PUT, DELETE, etc.
            mode: "cors", // no-cors, *cors, same-origin
            //cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
            credentials: "include", // include, *same-origin, omit
            headers: this._generateHeaders({}, data),
            redirect: "follow", // manual, *follow, error
            //referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
            body: data, // body data type must match "Content-Type" header
        })
    }

    put(apipath, data, headers) {
        return fetch(this.getEndpoint() + apipath, {
            method: "PUT", // *GET, POST, PUT, DELETE, etc.
            mode: "cors", // no-cors, *cors, same-origin
            //cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
            credentials: "include", // include, *same-origin, omit
            headers: this._generateHeaders(headers, data),
            redirect: "follow", // manual, *follow, error
            //referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
            body: JSON.stringify(data), // body data type must match "Content-Type" header
        })
    }

    patch(apipath, data, headers) {
        return fetch(this.getEndpoint() + apipath, {
            method: "PATCH", // *GET, POST, PUT, DELETE, etc.
            mode: "cors", // no-cors, *cors, same-origin
            //cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
            credentials: "include", // include, *same-origin, omit
            headers: this._generateHeaders(headers, data),
            redirect: "follow", // manual, *follow, error
            //referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
            body: JSON.stringify(data), // body data type must match "Content-Type" header
        })
    }

    httpRequestCall(apipath, type, data) {
        // Default options are marked with *
        let fetchcall = undefined
        if (type === "POST") {
            fetchcall = this.post(apipath, data, {})
        } else if (type === "PUT") {
            fetchcall = this.put(apipath, data, {})
        } else if (type === "GET") {
            fetchcall = this.get(apipath, {})
        } else if (type === "DELETE") {
            fetchcall = this.delete(apipath, {})
        } else if (type === "PATCH") {
            fetchcall = this.patch(apipath, data, {})
        }
        return fetchcall
    }

    httpRequestCallWithHeader(apipath, type, data, headers) {
        // Default options are marked with *
        let fetchcall = undefined
        if (type === "POST") {
            fetchcall = this.post(apipath, data, headers)
        } else if (type === "PUT") {
            fetchcall = this.put(apipath, data, headers)
        } else if (type === "GET") {
            fetchcall = this.get(apipath, headers)
        } else if (type === "DELETE") {
            fetchcall = this.delete(apipath, headers)
        } else if (type === "PATCH") {
            fetchcall = this.patch(apipath, data, headers)
        }
        return fetchcall
    }
}
