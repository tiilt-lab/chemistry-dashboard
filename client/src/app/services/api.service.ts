import { Injectable } from '@angular/core';
import { Http, Headers, Response, RequestMethod, Request, URLSearchParams } from '@angular/http';
import { Router } from '@angular/router';
import { Observable } from 'rxjs/Observable';

@Injectable()
export class ApiService {

  constructor(private http: Http,
              private router: Router) {}

  private getWSSProtocol(): string {
    return (window.location.protocol === 'https:') ? 'wss:' : 'ws:';
  }

  getEndpoint(): string {
    return window.location.protocol  + '//' + window.location.host.split(':')[0] + '/';
  }

  getWebsocketEndpoint(): string {
    return this.getWSSProtocol() + '//' + window.location.host.split(':')[0] + '/audio_socket';
  }

  get(endpoint: string, queryParams: Object = {}, useAccessToken = true, headers?: Object,
      url: string = this.getEndpoint(), withCredentials = false): Observable<Response> {
    return this._request(RequestMethod.Get, endpoint, {}, queryParams, useAccessToken, headers, url, withCredentials);
  }

  put(endpoint: string, body: Object, queryParams: Object = {}, useAccessToken = true, headers?: Object,
      url: string = this.getEndpoint(), withCredentials = false): Observable<Response> {
    return this._request(RequestMethod.Put, endpoint, body, queryParams, useAccessToken, headers, url, withCredentials);
  }

  post(endpoint: string, body: Object, queryParams: Object = {}, useAccessToken = true, headers?: Object,
       url: string = this.getEndpoint(), withCredentials = false): Observable<Response> {
    return this._request(RequestMethod.Post, endpoint, body, queryParams, useAccessToken, headers, url, withCredentials);
  }

  delete(endpoint: string, queryParams: Object = {}, useAccessToken = true, headers?: Object,
         url: string = this.getEndpoint(), withCredentials = false): Observable<Response> {
    return this._request(RequestMethod.Delete, endpoint, {}, queryParams, useAccessToken, headers, url, withCredentials);
  }

  private _request(method: RequestMethod, endpoint: string, body: Object, queryParams: Object, useAccessToken: boolean,
                   headers: Object, url: string, withCredentials: boolean): Observable<Response> {
    return Observable.create( obs => {
      this.http.request(new Request({
        'method': method,
        'url': url + endpoint,
        'body': body,
        'search': this._generateQueryParams(queryParams),
        'headers': this._generateHeaders(useAccessToken, headers),
        'withCredentials': withCredentials
      })).subscribe(response => {
        obs.next(response);
        obs.complete();
      }, error => {
        if (error.status === 401) {
          this.router.navigateByUrl('/login');
        }
        obs.error(error);
      });
    });
  }

  private _generateQueryParams(queryParams): URLSearchParams {
    const params: URLSearchParams = new URLSearchParams();
    for (const property in queryParams) {
      if (queryParams.hasOwnProperty(property)) {
        params.set(property, queryParams[property]);
      }
    }

    return params;
  }

  private _generateHeaders(useAccessToken: boolean, headers?: Object): Headers {
    const h = {
      'Content-Type': 'application/json'
    };

    for (const property in headers) {
      if (headers.hasOwnProperty(property)) {
        h[property] = headers[property];
      }
    }

    return new Headers(h);
  }
}


