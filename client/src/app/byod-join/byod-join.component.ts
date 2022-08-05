import { Component, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { SessionService } from '../services/session.service';
import { ApiService } from '../services/api.service';

enum Forms {
  NavGuard = 1,
  JoinError,
  ClosedSession,
  Connecting
}

@Component({
  selector: 'app-byod-join',
  templateUrl: './byod-join.component.html',
  styleUrls: ['./byod-join.component.scss']
})
export class ByodJoinComponent implements OnDestroy {

  // Audio connection data
  ws: any;
  connected = false;
  authenticated = false;
  streamReference: any;
  audioContext: any;
  processor: any;
  source: any;
  ending = false;
  reconnectCounter = 0;

  // Session data
  sessionDevice: any;
  session: any;
  key: any;

  POD_COLOR = '#FF6655';
  GLOW_COLOR = '#ffc3bd';

  forms = Forms;
  currentForm: any = null;
  displayText: string = null;
  pageTitle = 'Join Discussion';

  constructor(private sessionService: SessionService,
              private apiService: ApiService,
              private router: Router) { }

  ngOnDestroy() {
    this.disconnect(true);
  }

  // Verifies the users connection input and that the user
  // has a microphone accessible to the browser.
  verifyInputAndAudio(name: any, passcode: any) {
    if (name == null || name.trim().length === 0) {
      name = 'User Device';
    }
    try {
      if (navigator.mediaDevices != null) {
        navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        .then(stream => {
          stream.getAudioTracks().forEach(track => track.stop());
          this.requestAccessKey(name, passcode);
        }, error => {
          this.displayText = 'Failed to get user audio source.';
          this.currentForm = this.forms.JoinError;
          this.disconnect(true);
        });
      } else {
        this.displayText = 'No media devices detected.';
        this.currentForm = this.forms.JoinError;
        this.disconnect(true);
      }
    } catch (ex) {
      this.displayText = 'Failed to get user audio source.';
      this.currentForm = this.forms.JoinError;
      this.disconnect(true);
    }
  }

  // Requests session access from the server.
  requestAccessKey(name, passcode) {
    this.ending = false;
    this.currentForm = this.forms.Connecting;
    this.sessionService.joinByodSession(name, passcode).subscribe(response => {
      this.session = response.session;
      this.sessionDevice = response.session_device;
      this.key = response.key;
      this.handleStream();
    }, error => {
      this.displayText = error.json()['message'];
      this.currentForm = this.forms.JoinError;
      this.disconnect(true);
    });
  }

  // Creates stream with the users audio input.
  handleStream() {
    navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    .then(stream => {
      this.streamReference = stream;
      this.audioContext = new ((<any>window).AudioContext || (<any>window).webkitAudioContext)();
      this.source = this.audioContext.createMediaStreamSource(stream);
      this.processor = this.audioContext.createScriptProcessor(16384, 1, 1);

      this.source.connect(this.processor);
      this.processor.connect(this.audioContext.destination);

      this.processor.onaudioprocess = e => {

        if (this.connected && this.authenticated) {
          const data = e.inputBuffer.getChannelData(0);
          this.ws.send(data.buffer);
        }
      };

      this.connect();
    }, error => {
      this.displayText = 'Failed to get user audio source.';
      this.currentForm = this.forms.JoinError;
      this.disconnect(true);
    });
  }

  // Connects to websocket server.
  connect() {
    this.ws = new WebSocket(this.apiService.getWebsocketEndpoint());
    this.ws.binaryType = 'arraybuffer';

    this.ws.onopen = e => {
      console.log('[Connected]');
      this.connected = true;
      this.pageTitle = this.sessionDevice.name;
      this.reconnectCounter = 0;
      this.requestStart();
    };

    this.ws.onmessage = e => {
      const message = JSON.parse(e.data);
      if (message['type'] === 'start') {
        this.authenticated = true;
        this.closeDialog();
      } else if (message['type'] === 'error') {
        this.disconnect(true);
        this.displayText = 'The connection to the session has been closed by the server.';
        this.currentForm = this.forms.ClosedSession;
      } else if (message['type'] === 'end') {
        this.disconnect(true);
        this.displayText = 'The session has been closed by the owner.';
        this.currentForm = this.forms.ClosedSession;
      }
    };

    this.ws.onclose = e => {
      console.log('[Disconnected]');
      if (!this.ending) {
        if (this.reconnectCounter < 5) {
          this.currentForm = this.forms.Connecting;
          this.reconnectCounter++;
          this.disconnect();
          setTimeout(() => {
            this.handleStream();
          }, 1000);
        } else {
          this.displayText = 'Connection to the session has been lost.';
          this.currentForm = this.forms.ClosedSession;
          this.disconnect(true);
        }
      }
    };
  }

  // Disconnects from websocket server and audio stream.
  disconnect(permanent: boolean = false) {
    if (permanent) {
      this.ending = true;
    }
    this.connected = false;
    this.authenticated = false;
    this.pageTitle = 'Join Session';
    if (this.processor != null) {
      this.processor.onaudioprocess = null;
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.source != null) {
      this.source.disconnect();
      this.source = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    if (this.streamReference != null) {
      this.streamReference.getAudioTracks().forEach(track => track.stop());
      this.streamReference = null;
    }
    if (this.ws != null) {
      this.ws.close();
      this.ws = null;
    }
  }

  // Begin capturing and sending client audio.
  requestStart() {
    if (this.ws === null) {
      return;
    }
    const context = new ((<any>window).AudioContext || (<any>window).webkitAudioContext)();
    console.log(context, 'context ....')
    const message = {
      'type': 'start',
      'key': this.key,
      'start_time': 0.0,
      'sample_rate': context.sampleRate,
      'encoding': 'pcm_f32le',
      'channels': 1
    };
    context.close();
    this.ws.send(JSON.stringify(message));
  }

  requestHelp() {
    this.sessionDevice.button_pressed = !this.sessionDevice.button_pressed;
    this.sessionService.setDeviceButton(this.sessionDevice.id, this.sessionDevice.button_pressed, this.key).subscribe();
  }

  navigateToLogin(confirmed: boolean = false) {
    if (!confirmed && this.connected) {
      this.currentForm = this.forms.NavGuard;
    } else {
      this.router.navigate(['']);
    }
  }

  closeDialog() {
    this.currentForm = null;
  }

  converToUpperCase(inputField: any) {
    inputField.value = inputField.value.toUpperCase();
  }
}
