# BLINC frontend

The dashboard, the BYOD join page and the profile-creation flow: a React 18
app built with Vite, Tailwind, rxjs and socket.io-client. The production
nginx serves the built `frontend/build/` directly; the Flask API lives at
`/api` and `/socket.io` on the same origin (see the repository README).

Node 24 (the version CI uses). `npm ci` installs the pinned dependencies.

## Scripts

| Command             | What it does                                                        |
| ------------------- | ------------------------------------------------------------------- |
| `npm start`         | Dev server on <http://localhost:3000>, proxying `/api` and `/socket.io` to the API (`DC_API_TARGET`, default `http://localhost:5001`) |
| `npm run build`     | Production build into `build/`; on the server, rebuilding is deploying |
| `npm run lint`      | eslint over `.js` and `.jsx` (CI gates on errors and ratchets warnings) |
| `npm run lint:strict` | Same, with `react-hooks/exhaustive-deps` as an error              |
| `npm run typecheck` | `tsc --noEmit` over the converted `.ts` files                       |
| `npm test`          | vitest, the `*.test.js` files beside the code                       |
| `npm run svgr`      | Regenerate `src/Icons/` from `src/assets/img`                       |

To talk to an API started by hand on another port:

```bash
DC_API_TARGET=http://localhost:5091 npm start
```

## Layout

```
src/routes/            page routing, role guards, app shell
src/services/          REST and socket clients (one module per API area)
src/sessions/          session list and session manager
src/pods-overview/     live overview of a session's pods
src/pod-details/       one pod: transcript, metrics, video
src/components/        shared panels (transcripts, video analytics, coding, post-hoc trigger, ...)
src/byod-join/         the student join/record page (/join)
src/profile-creation/  voice and face enrollment (/signup)
src/coding-schemes/    coding-scheme library and editor
src/student-dashboard/ anonymous student results (/student/dashboard)
src/expert-rating/     rater flow (/expert/rating)
public/audio-sender-processor.js  the AudioWorklet that streams microphone PCM
```
