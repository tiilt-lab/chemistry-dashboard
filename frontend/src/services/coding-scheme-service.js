import { ApiService } from "./api-service"

// Coding schemes (Library): the built-in ones and the caller's own. Every
// call resolves to { status, body } (body null when the response has none).
function parse(r) {
    return r.json().then(
        (body) => ({ status: r.status, body }),
        () => ({ status: r.status, body: null }),
    )
}

export class CodingSchemeService {
    api = new ApiService()

    list() {
        return this.api.httpRequestCall("api/v1/coding_schemes", "GET", {}).then(parse)
    }

    // ref: "builtin:<key>", "scheme:<id>" or a numeric id.
    get(ref) {
        return this.api.httpRequestCall("api/v1/coding_schemes/" + encodeURIComponent(String(ref)), "GET", {}).then(parse)
    }

    create(scheme) {
        return this.api.httpRequestCall("api/v1/coding_schemes", "POST", scheme).then(parse)
    }

    update(id, scheme) {
        return this.api.httpRequestCall("api/v1/coding_schemes/" + id, "PUT", scheme).then(parse)
    }

    delete(id) {
        return this.api.httpRequestCall("api/v1/coding_schemes/" + id, "DELETE", {}).then(parse)
    }

    validate(scheme) {
        return this.api.httpRequestCall("api/v1/coding_schemes/validate", "POST", scheme).then(parse)
    }
}
