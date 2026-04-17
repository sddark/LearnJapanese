/**
 * AudioWorklet processor: captures mic audio, downsamples to 16kHz,
 * converts to Int16, and posts binary frames to the main thread.
 * Vosk requires 16kHz 16-bit mono PCM.
 */
class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // sampleRate is a global in AudioWorklet scope
    this._ratio = sampleRate / 16000;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) return true;

    const chunk = input[0]; // Float32Array at native sample rate
    const outLen = Math.floor(chunk.length / this._ratio);
    if (outLen === 0) return true;

    const out = new Int16Array(outLen);
    for (let i = 0; i < outLen; i++) {
      const src = chunk[Math.floor(i * this._ratio)];
      // Clamp and convert float32 [-1,1] to int16
      out[i] = Math.max(-32768, Math.min(32767, src * 32767));
    }

    this.port.postMessage(out.buffer, [out.buffer]);
    return true;
  }
}

registerProcessor('pcm-processor', PCMProcessor);
