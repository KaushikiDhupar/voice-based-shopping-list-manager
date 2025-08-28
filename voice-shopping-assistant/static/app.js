
const state = {
  recognizing: false,
  recognition: null,
  lang: 'en-US'
};

function initSpeech() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    document.getElementById('status').textContent = 'Speech recognition not supported. Type commands instead.';
    return;
  }
  state.recognition = new SpeechRecognition();
  state.recognition.lang = state.lang;
  state.recognition.interimResults = true;
  state.recognition.continuous = false;

  state.recognition.onstart = () => {
    state.recognizing = true;
    document.getElementById('mic').disabled = true;
    document.getElementById('status').textContent = 'Listening...';
  };
  state.recognition.onresult = (e) => {
    let transcript = '';
    for (let i = e.resultIndex; i < e.results.length; ++i) {
      transcript += e.results[i][0].transcript;
    }
    document.getElementById('transcript').value = transcript.trim();
  };
  state.recognition.onerror = () => {
    document.getElementById('status').textContent = 'Speech error. Try again.';
  };
  state.recognition.onend = async () => {
    state.recognizing = false;
    document.getElementById('mic').disabled = false;
    document.getElementById('status').textContent = 'Processing...';
    const text = document.getElementById('transcript').value;
    if (text) await sendCommand(text);
    document.getElementById('status').textContent = 'Ready.';
  };
}

async function refreshList() {
  const res = await fetch('/api/list');
  const data = await res.json();
  const ul = document.getElementById('list');
  ul.innerHTML = '';
  data.items.forEach(it => {
    const li = document.createElement('li');
    li.className = 'list-item';
    li.innerHTML = `
      <div>
        <div><strong>${it.item}</strong> <span class="kv">(${it.category || 'uncategorized'})</span></div>
        <div class="kv">added ${new Date(it.created_at).toLocaleString()}</div>
      </div>
      <div>x${it.quantity}</div>
      <button class="btn" data-id="${it.id}">Remove</button>
    `;
    li.querySelector('button').onclick = async () => {
      await fetch('/api/remove', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id: it.id})});
      refreshList();
    };
    ul.appendChild(li);
  });
}

async function getSuggestions() {
  const res = await fetch('/api/suggest');
  const data = await res.json();
  const ul = document.getElementById('suggestions');
  ul.innerHTML = '';
  data.suggestions.forEach(s => {
    const li = document.createElement('li');
    li.className = 'list-item';
    li.innerHTML = `
      <div><strong>${s.item}</strong> <span class="kv">${s.reason}</span></div>
      <div class="kv">${s.category}</div>
      <button class="btn">Add</button>
    `;
    li.querySelector('button').onclick = async () => {
      await fetch('/api/add', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({item: s.item, quantity: 1})});
      refreshList();
    };
    ul.appendChild(li);
  });
}

async function sendCommand(text) {
  const res = await fetch('/api/parse', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text, lang: state.lang})});
  const data = await res.json();
  const toast = document.getElementById('toast');
  toast.textContent = data.message;
  toast.className = 'toast';
  await refreshList();
}

document.addEventListener('DOMContentLoaded', () => {
  initSpeech();
  refreshList();
  getSuggestions();

  document.getElementById('mic').addEventListener('click', () => {
    if (state.recognition) state.recognition.start();
  });

  document.getElementById('lang').addEventListener('change', (e) => {
    state.lang = e.target.value;
    if (state.recognition) state.recognition.lang = state.lang;
  });

  document.getElementById('commandForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = document.getElementById('transcript').value;
    if (!text) return;
    await sendCommand(text);
    document.getElementById('transcript').value = '';
  });

  document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = document.getElementById('q').value;
    const brand = document.getElementById('brand').value;
    const max = document.getElementById('max').value;
    const res = await fetch('/api/search?' + new URLSearchParams({q, brand, max}));
    const data = await res.json();
    const ul = document.getElementById('searchResults');
    ul.innerHTML = '';
    data.results.forEach(r => {
      const li = document.createElement('li');
      li.className = 'list-item';
      li.innerHTML = `<div><strong>${r.name}</strong> <span class="kv">${r.brand}</span></div><div>$${r.price.toFixed(2)}</div><button class="btn">Add</button>`;
      li.querySelector('button').onclick = async () => {
        await fetch('/api/add', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({item: r.name, quantity: 1})});
        refreshList();
      };
      ul.appendChild(li);
    });
  });
});
