# blinc.puthipiroj.com instance (glamdring-vm-1)

Second Discussion Capture instance running from `/home/vlj9405/code/chemistry-dashboard`,
alongside the existing `video.tiilt-blinc.com` instance (`/home/tde3218/chemistry-dashboard`,
ports 5000/9000/9001/9003).

## Port and isolation map

| Component            | Existing instance | This instance | Set via                          |
|----------------------|-------------------|---------------|----------------------------------|
| Flask/SocketIO       | 5000              | 5001          | `DC_PORT` env                    |
| Audio processor WS   | 9000              | 9010          | `DC_AUDIO_WS_PORT` env           |
| Device WS            | 9001              | 9011          | `DC_DEVICE_WS_PORT` env          |
| Video processor WS   | 9003              | 9013          | `DC_VIDEO_WS_PORT` env           |
| MySQL database       | discussion_capture| discussion_capture_vlj | `src/server/config.ini` |
| Redis db             | 0                 | 1             | all three `config.ini` files     |
| Runtime file storage | /var/lib          | /home/vlj9405/blinc-data | `config.ini` root_dir |

The processors' HTTP callbacks point at `127.0.0.1:5001` (this instance's Flask server).
The `redis_db` in `src/audio_processing/config.ini` and `src/video_processing/config.ini`
MUST match `src/server/config.ini` — the server writes session auth keys there and the
audio processor reads them directly.

## One-time setup

1. **DNS**: create an A record `blinc.puthipiroj.com -> 129.105.44.121` at the DNS
   provider for puthipiroj.com. Verify with `dig +short blinc.puthipiroj.com`.

2. **Python env**: one unified venv (`src/venv-unified`) runs every component
   (server, audio/video live + post-hoc, ASR worker). Build it per
   [`src/requirements-unified.README.md`](../../../src/requirements-unified.txt):
   ```
   <python3.13> -m venv src/venv-unified
   src/venv-unified/bin/pip install -r src/requirements-unified.txt
   ```
   Also download the model assets (Google News vectors, gaze/emotion checkpoints,
   Google Cloud ASR key at `src/audio_processing/asr_connectors/google-cloud-key.json`)
   per the repo README.

3. **Database** (`discussion_capture_vlj` already exists):
   ```
   cd src/server && venv/bin/flask --app discussion_capture db upgrade
   ```

4. **Frontend build**:
   ```
   cd frontend && npm install && npm run build
   ```

5. **systemd units**:
   ```
   sudo cp blinc-*.service /lib/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now blinc-discussion-capture blinc-audio-processor blinc-video-processor
   ```

6. **nginx**: see the note at the top of `nginx-blinc.puthipiroj.com.conf` —
   the main nginx.conf on this box does not include sites-enabled/, so the block
   must be added to the `http {}` context (or an include line added). Then:
   ```
   sudo nginx -t && sudo systemctl reload nginx
   ```

7. **TLS** (after DNS resolves; required for BYOD mic/camera capture):
   ```
   sudo certbot --nginx -d blinc.puthipiroj.com
   ```

8. **First user**:
   ```
   cd src/server && venv/bin/python create_user.py
   ```

## Dev mode (no nginx)

`frontend/vite.config.js` proxies `/api` and `/socket.io` to `localhost:5001`, so:
```
DC_PORT=5001 DC_DEVICE_WS_PORT=9011 src/server/venv/bin/python src/server/discussion_capture.py
cd frontend && npm start   # http://localhost:3000
```
