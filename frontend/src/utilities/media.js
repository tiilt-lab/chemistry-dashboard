// Polyfill navigator.mediaDevices.getUserMedia for legacy browsers.
// Previously duplicated verbatim in the join page and the enrollment page,
// each followed by a no-op enumerateDevices() loop kept alive for a
// commented-out console.log.
export function ensureGetUserMedia() {
    if (navigator.mediaDevices !== undefined) return
    navigator.mediaDevices = {}
    navigator.mediaDevices.getUserMedia = function (constraintObj) {
        const getUserMedia =
            navigator.webkitGetUserMedia || navigator.mozGetUserMedia
        if (!getUserMedia) {
            return Promise.reject(
                new Error("getUserMedia is not implemented in this browser"),
            )
        }
        return new Promise(function (resolve, reject) {
            getUserMedia.call(navigator, constraintObj, resolve, reject)
        })
    }
}
