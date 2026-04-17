let currentKana = null;
let streamer = null;
let isRecording = false;

const charEl    = document.getElementById('kana-char');
const typeEl    = document.getElementById('kana-type');
const promptEl  = document.getElementById('kana-prompt');
const transcriptEl = document.getElementById('transcript');
const feedbackEl   = document.getElementById('feedback');
const speakBtn     = document.getElementById('speak-btn');

async function loadNextKana() {
  feedbackEl.textContent = '';
  feedbackEl.className = 'feedback';
  transcriptEl.textContent = '';
  speakBtn.disabled = false;
  speakBtn.textContent = '🎤 SPEAK';

  const res = await fetch('/api/kana/next');
  const data = await res.json();

  if (data.done) {
    charEl.textContent = '✓';
    typeEl.textContent = '';
    promptEl.textContent = 'All done for today!';
    speakBtn.disabled = true;
    return;
  }

  currentKana = data;
  charEl.textContent = data.character;
  typeEl.textContent = data.kana_type === 'hiragana' ? 'Hiragana' : 'Katakana';
  promptEl.textContent = 'Say the sound!';
}

async function startRecording() {
  if (isRecording || !currentKana) return;
  isRecording = true;
  speakBtn.textContent = '🔴 Listening…';
  transcriptEl.textContent = '';

  const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  streamer = new AudioStreamer(`${wsProto}//${location.host}/ws/stt`);

  try {
    await streamer.start(
      (partial) => { transcriptEl.textContent = partial; },
      (text) => { handleFinal(text); }
    );
  } catch (err) {
    console.error('Recording error:', err);
    feedbackEl.textContent = 'Mic error — check permissions';
    feedbackEl.className = 'feedback incorrect';
    isRecording = false;
    speakBtn.textContent = '🎤 SPEAK';
  }
}

async function stopRecording() {
  if (!isRecording) return;
  isRecording = false;
  speakBtn.textContent = '🎤 SPEAK';
  if (streamer) {
    await streamer.stop();
    streamer = null;
  }
}

async function handleFinal(text) {
  transcriptEl.textContent = text;

  const res = await fetch('/api/kana/answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kana_id: currentKana.id, transcript: text }),
  });
  const result = await res.json();

  if (result.correct) {
    feedbackEl.textContent = `✓  "${result.expected}"`;
    feedbackEl.className = 'feedback correct';
  } else {
    feedbackEl.textContent = `✗  Expected: "${result.expected}"`;
    feedbackEl.className = 'feedback incorrect';
  }

  setTimeout(loadNextKana, 1600);
}

speakBtn.addEventListener('pointerdown', startRecording);
speakBtn.addEventListener('pointerup', stopRecording);
speakBtn.addEventListener('pointerleave', stopRecording);

document.addEventListener('DOMContentLoaded', loadNextKana);
