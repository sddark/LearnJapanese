let ws = null;
let sessionId = null;
let isRecording = false;
let streamer = null;
let showEnglish = true;
let audioChunks = [];
let audioCtx = null;

const thread      = document.getElementById('chat-thread');
const statusEl    = document.getElementById('chat-status');
const transcriptEl = document.getElementById('chat-transcript');
const speakBtn    = document.getElementById('chat-speak-btn');
const toggleBtn   = document.getElementById('toggle-english');

function setStatus(text) {
  statusEl.textContent = text;
}

function scrollThread() {
  thread.scrollTop = thread.scrollHeight;
}

function addAiBubble(japanese, english, turnId, targetWord) {
  const bubble = document.createElement('div');
  bubble.className = 'bubble bubble-ai';
  bubble.dataset.turn = turnId;
  const highlighted = targetWord
    ? japanese.replace(targetWord, `<mark class="target-word">${targetWord}</mark>`)
    : japanese;
  bubble.innerHTML = `
    <div class="bubble-japanese">${highlighted}</div>
    <div class="bubble-english ${showEnglish ? '' : 'hidden'}">${english}</div>
  `;
  thread.insertBefore(bubble, statusEl);
  scrollThread();
  return bubble;
}

function addUserBubble(text) {
  const bubble = document.createElement('div');
  bubble.className = 'bubble bubble-user';
  bubble.textContent = text || '…';
  thread.insertBefore(bubble, statusEl);
  scrollThread();
  return bubble;
}

function markBubble(bubble, correct, correction) {
  bubble.classList.add(correct ? 'bubble-correct' : 'bubble-incorrect');
  if (!correct && correction) {
    const hint = document.createElement('div');
    hint.className = 'bubble-correction';
    hint.textContent = `→ ${correction}`;
    bubble.appendChild(hint);
  }
}

async function playAudioChunks() {
  if (!audioChunks.length) return;
  const blob = new Blob(audioChunks, { type: 'audio/wav' });
  audioChunks = [];
  const url = URL.createObjectURL(blob);
  return new Promise(resolve => {
    const audio = new Audio(url);
    audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
    audio.onerror = () => { URL.revokeObjectURL(url); resolve(); };
    audio.play().catch(resolve);
  });
}

async function startSession() {
  try {
    const data = await API.post('/api/conversation/start', { topic: 'daily life' });
    sessionId = data.session_id;
  } catch (e) {
    setStatus('Failed to start session');
    return;
  }

  const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${wsProto}//${location.host}/ws/conversation`);
  ws.binaryType = 'arraybuffer';

  ws.onopen = () => {
    ws.send(JSON.stringify({ session_id: sessionId }));
  };

  let currentUserBubble = null;

  ws.onmessage = async (event) => {
    if (event.data instanceof ArrayBuffer) {
      audioChunks.push(new Uint8Array(event.data));
      return;
    }

    const msg = JSON.parse(event.data);

    switch (msg.type) {
      case 'ready':
        setStatus('Connected — waiting for first turn…');
        break;

      case 'ai_text':
        setStatus('AI is speaking…');
        addAiBubble(msg.japanese, msg.english, msg.turn, msg.target_word);
        break;

      case 'audio_start':
        audioChunks = [];
        break;

      case 'audio_done':
        await playAudioChunks();
        break;

      case 'listen':
        setStatus('Say the highlighted word — hold SPEAK');
        speakBtn.disabled = false;
        transcriptEl.textContent = '';
        currentUserBubble = null;
        break;

      case 'transcript':
        if (!currentUserBubble) {
          currentUserBubble = addUserBubble(msg.text);
        } else {
          currentUserBubble.textContent = msg.text;
        }
        transcriptEl.textContent = '';
        setStatus('Evaluating…');
        break;

      case 'evaluation':
        speakBtn.disabled = true;
        if (currentUserBubble) {
          markBubble(currentUserBubble, msg.correct, msg.correction);
        }
        setStatus(msg.correct ? '✓ Correct!' : '✗ Try again next time');
        break;

      case 'error':
        setStatus(`Error: ${msg.message}`);
        break;

      case 'done':
        setStatus('Session complete!');
        speakBtn.disabled = true;
        break;
    }
  };

  ws.onclose = () => setStatus('Disconnected');
  ws.onerror = () => setStatus('Connection error');
}

async function startRecording() {
  if (isRecording || !ws) return;
  isRecording = true;
  speakBtn.textContent = '🔴 Listening…';
  transcriptEl.textContent = '';
  currentUserBubble = null;

  streamer = new AudioStreamer(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/stt`);
  try {
    await streamer.start(
      partial => { transcriptEl.textContent = partial; },
      text    => { transcriptEl.textContent = text; }
    );
  } catch (_) {
    // STT unavailable — stay in recording state so user can release manually
    speakBtn.textContent = '🔴 Release to submit';
    streamer = null;
  }
}

async function stopRecording() {
  if (!isRecording || !ws) return;
  isRecording = false;
  speakBtn.textContent = '🎤 SPEAK';
  speakBtn.disabled = true;

  let transcript = transcriptEl.textContent;
  if (streamer) {
    await streamer.stop();
    streamer = null;
  }

  ws.send(JSON.stringify({ type: 'stop_listen', text: transcript }));
}

speakBtn.addEventListener('pointerdown', startRecording);
speakBtn.addEventListener('pointerup',   stopRecording);
speakBtn.addEventListener('pointerleave', stopRecording);

toggleBtn.addEventListener('click', () => {
  showEnglish = !showEnglish;
  toggleBtn.classList.toggle('active', showEnglish);
  document.querySelectorAll('.bubble-english').forEach(el => {
    el.classList.toggle('hidden', !showEnglish);
  });
});

document.addEventListener('DOMContentLoaded', startSession);
