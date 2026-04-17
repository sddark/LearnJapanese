/**
 * AudioStreamer: captures mic via AudioWorklet, streams 16kHz PCM over WebSocket.
 * Usage:
 *   const s = new AudioStreamer(wsUrl);
 *   await s.start(onPartial, onFinal);
 *   await s.stop();  // flushes final result then closes
 */
class AudioStreamer {
  constructor(wsUrl) {
    this._wsUrl = wsUrl;
    this._ws = null;
    this._context = null;
    this._worklet = null;
    this._source = null;
    this._stream = null;
  }

  async start(onPartial, onFinal) {
    this._stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    this._context = new AudioContext();
    await this._context.audioWorklet.addModule('/js/pcm-processor.js');

    this._source = this._context.createMediaStreamSource(this._stream);
    this._worklet = new AudioWorkletNode(this._context, 'pcm-processor');
    this._source.connect(this._worklet);

    await new Promise((resolve, reject) => {
      this._ws = new WebSocket(this._wsUrl);
      this._ws.binaryType = 'arraybuffer';
      this._ws.onopen = resolve;
      this._ws.onerror = reject;
    });

    this._worklet.port.onmessage = (e) => {
      if (this._ws.readyState === WebSocket.OPEN) {
        this._ws.send(e.data);
      }
    };

    this._ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'partial') {
        onPartial(msg.text);
      } else if (msg.type === 'final') {
        onFinal(msg.text, msg.confidence ?? 0);
      }
    };
  }

  async stop() {
    // Stop sending audio
    if (this._worklet) {
      this._worklet.port.onmessage = null;
      this._worklet.disconnect();
    }
    if (this._source) this._source.disconnect();
    if (this._stream) this._stream.getTracks().forEach(t => t.stop());

    // Flush final result
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._ws.send('STOP');
      await new Promise(resolve => {
        const orig = this._ws.onmessage;
        this._ws.onmessage = (e) => {
          if (orig) orig(e);
          this._ws.close();
          resolve();
        };
        // Safety timeout
        setTimeout(() => { this._ws?.close(); resolve(); }, 3000);
      });
    }

    if (this._context) await this._context.close();
    this._ws = null;
    this._context = null;
    this._worklet = null;
    this._source = null;
    this._stream = null;
  }
}
