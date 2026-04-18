function pct(n, total) {
  return total > 0 ? Math.round((n / total) * 100) : 0;
}

function setBar(id, value, total) {
  const el = document.getElementById(id);
  if (!el) return;
  const p = pct(value, total);
  el.style.width = p + '%';
  el.style.minWidth = value > 0 ? '6px' : '0';
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

async function loadProgress() {
  try {
    const [words, kana, due, streak] = await Promise.all([
      API.get('/api/progress/words'),
      API.get('/api/progress/kana'),
      API.get('/api/progress/due'),
      API.get('/api/progress/streak'),
    ]);

    // Words — N5
    const n5 = words['N5'] || { unknown: 0, learning: 0, known: 0, total: 0 };
    setText('n5-known',    `${n5.known} / ${n5.total}`);
    setText('n5-learning', `${n5.learning} learning`);
    setBar('n5-known-bar',    n5.known,    n5.total);
    setBar('n5-learning-bar', n5.learning, n5.total);

    // Kana
    const hira = kana['hiragana'] || { known: 0, learning: 0, total: 46 };
    const kata = kana['katakana'] || { known: 0, learning: 0, total: 46 };
    setText('hira-count', `${hira.known} / ${hira.total}`);
    setText('kata-count', `${kata.known} / ${kata.total}`);
    setBar('hira-known-bar',    hira.known,    hira.total);
    setBar('hira-learning-bar', hira.learning, hira.total);
    setBar('kata-known-bar',    kata.known,    kata.total);
    setBar('kata-learning-bar', kata.learning, kata.total);

    // Due today
    setText('words-due', due.words);
    setText('kana-due',  due.kana);

    // Streak
    setText('streak-count', streak.streak);

  } catch (e) {
    console.error('Progress load failed', e);
  }
}

document.addEventListener('DOMContentLoaded', loadProgress);
