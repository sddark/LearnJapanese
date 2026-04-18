let currentWord = null;
let isRecording = false;
let streamer = null;

const emojiEl      = document.getElementById('quiz-emoji');
const meaningEl    = document.getElementById('quiz-meaning');
const choiceGrid   = document.getElementById('choice-grid');
const speakArea    = document.getElementById('speak-area');
const transcriptEl = document.getElementById('quiz-transcript');
const feedbackEl   = document.getElementById('quiz-feedback');
const speakBtn     = document.getElementById('quiz-speak-btn');
const skipBtn      = document.getElementById('quiz-skip-btn');
const showBtn      = document.getElementById('quiz-show-btn');
const doneMsg      = document.getElementById('quiz-done');

async function loadNextWord() {
  feedbackEl.textContent = '';
  feedbackEl.className = 'feedback';
  transcriptEl.textContent = '';
  choiceGrid.innerHTML = '';
  choiceGrid.style.display = 'none';
  speakArea.style.display = 'none';
  doneMsg.style.display = 'none';
  skipBtn.disabled = false;
  showBtn.style.display = '';

  let data;
  try {
    data = await API.get('/api/quiz/next');
  } catch (e) {
    feedbackEl.textContent = 'Error loading word';
    feedbackEl.className = 'feedback incorrect';
    return;
  }

  if (data.done) {
    emojiEl.textContent = '🎉';
    meaningEl.textContent = '';
    doneMsg.style.display = 'block';
    skipBtn.disabled = true;
    showBtn.style.display = 'none';
    return;
  }

  currentWord = data;
  emojiEl.textContent = data.emoji || '📝';
  meaningEl.textContent = data.meaning;

  if (data.mode === 'choice') {
    renderChoices(data.choices);
  } else {
    speakArea.style.display = 'flex';
    speakBtn.disabled = false;
    speakBtn.textContent = '🎤 SPEAK';
  }
}

function renderChoices(choices) {
  choiceGrid.style.display = 'grid';
  choices.forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'choice-btn';
    btn.textContent = opt.word;
    btn.addEventListener('click', () => handleChoice(opt.id === currentWord.id, btn));
    choiceGrid.appendChild(btn);
  });
}

async function handleChoice(correct, clickedBtn) {
  Array.from(choiceGrid.children).forEach(b => b.disabled = true);

  // Highlight correct answer
  Array.from(choiceGrid.children).forEach(b => {
    if (b.textContent === currentWord.word) b.classList.add('correct');
  });
  if (!correct) clickedBtn.classList.add('incorrect');

  try {
    await API.post('/api/quiz/answer', { word_id: currentWord.id, correct });
  } catch (_) {}

  if (correct) {
    feedbackEl.textContent = `✓  ${currentWord.reading}`;
    feedbackEl.className = 'feedback correct';
  } else {
    feedbackEl.textContent = `✗  ${currentWord.word}  ${currentWord.reading}`;
    feedbackEl.className = 'feedback incorrect';
  }

  setTimeout(loadNextWord, 1800);
}

async function startRecording() {
  if (isRecording || !currentWord) return;
  isRecording = true;
  speakBtn.textContent = '🔴 Listening…';
  transcriptEl.textContent = '';

  const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  streamer = new AudioStreamer(`${wsProto}//${location.host}/ws/stt`);

  try {
    await streamer.start(
      partial => { transcriptEl.textContent = partial; },
      text    => { handleFinalTranscript(text); }
    );
  } catch (err) {
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

async function handleFinalTranscript(text) {
  transcriptEl.textContent = text;
  let result;
  try {
    result = await API.post('/api/quiz/answer', { word_id: currentWord.id, correct: false, transcript: text });
  } catch (_) { return; }

  if (result.correct) {
    feedbackEl.textContent = `✓  ${currentWord.reading}`;
    feedbackEl.className = 'feedback correct';
  } else {
    feedbackEl.textContent = `✗  ${currentWord.word}  ${currentWord.reading}`;
    feedbackEl.className = 'feedback incorrect';
  }
  setTimeout(loadNextWord, 1800);
}

speakBtn.addEventListener('pointerdown', startRecording);
speakBtn.addEventListener('pointerup',   stopRecording);
speakBtn.addEventListener('pointerleave', stopRecording);

skipBtn.addEventListener('click', async () => {
  if (!currentWord) return;
  try { await API.post('/api/quiz/answer', { word_id: currentWord.id, correct: false }); } catch (_) {}
  loadNextWord();
});

showBtn.addEventListener('click', () => {
  feedbackEl.textContent = `${currentWord.word}  ${currentWord.reading}  (${currentWord.romaji})`;
  feedbackEl.className = 'feedback';
  showBtn.style.display = 'none';
});

document.addEventListener('DOMContentLoaded', loadNextWord);
