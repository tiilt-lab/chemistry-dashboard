export class ApiService {
    getWSSProtocol() {
        return window.location.protocol === "https:" ? "wss:" : "ws:"
    }

    getEndpoint() {
        return window.location.protocol + "//" + window.location.host + "/"
    }

    getVideoServerEndpoint() {
    return window.location.host;
  }

  getAudioWebsocketEndpoint() {
    return (
      this.getWSSProtocol() +
      "//" +
      window.location.host +
      "/audio_socket"
    );
  }

    getVideoWebsocketEndpoint() {
    return (
         this.getWSSProtocol() +
      "//" + this.getVideoServerEndpoint() +"/video_socket"
    );

  }

  getAudioPosthocWebsocketEndpoint() {
    return this.getWSSProtocol() + "//" + window.location.host + "/audio_posthoc_socket";
  }

  getVideoPosthocWebsocketEndpoint() {
    return this.getWSSProtocol() + "//" + window.location.host + "/video_posthoc_socket";
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
        }
      }
      return h;
    }

    // Single fetch wrapper — every verb helper below delegates here.
    // FormData bodies are sent raw (and _generateHeaders skips the JSON
    // content type for them); everything else is JSON-encoded.
    _request(method, apipath, data, headers) {
        const options = {
            method,
            mode: "cors",
            credentials: "include",
            // API responses reflect mutable server state; never let the browser
            // serve a stale cached copy. Without this, a GET re-fetched right
            // after a mutation (e.g. the students list after a merge) could
            // return the pre-mutation body, so the page never updated.
            cache: "no-store",
            headers: this._generateHeaders(headers || {}, data),
            redirect: "follow",
        }
        if (data !== undefined && method !== "GET" && method !== "DELETE") {
            options.body = data instanceof FormData ? data : JSON.stringify(data)
        }
        return fetch(this.getEndpoint() + apipath, options)
    }

    get(apipath, headers) {
        return this._request("GET", apipath, undefined, headers)
    }

    delete(apipath, headers) {
        return this._request("DELETE", apipath, undefined, headers)
    }

    post(apipath, data, headers) {
        return this._request("POST", apipath, data, headers)
    }

    postFiles(apipath, data) {
        return this._request("POST", apipath, data, {})
    }

    put(apipath, data, headers) {
        return this._request("PUT", apipath, data, headers)
    }

    httpRequestCall(apipath, type, data) {
        return this.httpRequestCallWithHeader(apipath, type, data, {})
    }

    httpRequestCallWithHeader(apipath, type, data, headers) {
        if (type === "GET" || type === "DELETE") {
            return this._request(type, apipath, undefined, headers)
        }
        if (type === "POST" || type === "PUT") {
            return this._request(type, apipath, data, headers)
        }
        return undefined
    }
}
