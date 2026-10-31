/**
 * MITS AI Assistant — frontend logic
 * ------------------------------------
 * Pure vanilla JS, no framework, no build step.
 *
 * Critical design rules for the "only 2 answers" bug:
 *   1. `isLoading` is ALWAYS reset in a `finally` block — an exception can
 *      never permanently disable the send button.
 *   2. The send button's disabled state is driven solely by `isLoading`.
 *   3. The textarea is never left in a disabled state after an error.
 *   4. Each request is completely independent — no shared mutable state
 *      between calls (no reused fetch objects, no retained promise chains).
 */

'use strict';

/* ── DOM refs ── */
const homeScreen     = document.getElementById('home-screen');
const chatScreen     = document.getElementById('chat-screen');
const chatMessages   = document.getElementById('chat-messages');
const chatInput      = document.getElementById('chat-input');
const sendBtn        = document.getElementById('send-btn');
const newChatBtn     = document.getElementById('new-chat-btn');
const themeBtn       = document.getElementById('theme-btn');
const recentList     = document.getElementById('recent-list');
const themeIcon      = document.getElementById('theme-icon');

/* ── App state ── */
let isLoading  = false;   // tracks whether a request is in-flight
let theme      = 'light'; // 'light' | 'dark'
let chatHistory = [];     // array of { role: 'user'|'ai', text, sources? }

/* ── Recent chats (localStorage) ── */
const STORAGE_KEY = 'mits_recent_chats';

function loadRecent() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveRecent(items) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 12)));
  } catch { /* storage quota — silently ignore */ }
}

function addRecentChat(title) {
  const items = loadRecent();
  // deduplicate by title
  const filtered = items.filter(i => i.title !== title);
  filtered.unshift({ title, ts: Date.now() });
  saveRecent(filtered);
  renderRecent();
}

function renderRecent() {
  const items = loadRecent();
  recentList.innerHTML = '';

  const icons = ['🎓', '👤', '💰', '📋', '📅', '🏫', '💼', '📚', '🔍', '📊'];

  items.forEach((item, idx) => {
    const li = document.createElement('li');
    li.className = 'recent-item';
    li.innerHTML = `
      <span class="recent-item-icon">${icons[idx % icons.length]}</span>
      <span>${escapeHtml(item.title)}</span>
    `;
    li.addEventListener('click', () => {
      // clicking a recent item sends the same question again
      startChat(item.title);
    });
    recentList.appendChild(li);
  });
}

/* ── Theme ── */
function initTheme() {
  const stored = localStorage.getItem('mits_theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  theme = stored || (prefersDark ? 'dark' : 'light');
  applyTheme();
}

function applyTheme() {
  document.documentElement.setAttribute('data-theme', theme);
  themeIcon.textContent = theme === 'dark' ? '☀' : '☾';
}

function toggleTheme() {
  theme = theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('mits_theme', theme);
  applyTheme();
}

/* ── Helpers ── */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Auto-grow the textarea up to ~6 lines */
function autogrow() {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
}

/* ── View switching ── */
function showHome() {
  homeScreen.style.display = 'flex';
  chatScreen.classList.remove('active');
}

function showChat() {
  homeScreen.style.display = 'none';
  chatScreen.classList.add('active');
}

/* ── New chat ── */
function newChat() {
  // Clear conversation state
  chatHistory = [];
  chatMessages.innerHTML = '';
  chatInput.value = '';
  autogrow();
  setLoading(false); // always reset, in case a request was mid-flight
  showHome();
}

/* ── Loading state ── */
function setLoading(state) {
  isLoading = state;
  sendBtn.disabled = state;
  chatInput.disabled = state;
  if (state) {
    sendBtn.innerHTML = '<span class="btn-spinner">⟳</span>';
  } else {
    sendBtn.innerHTML = '↑';
  }
}

/* ── Safe Markdown rendering (dependency-free, XSS-safe) ── */

/**
 * Parse common Markdown into a sanitized DOM fragment.
 *
 * Safety model:
 *   1. All HTML entities in the raw text are escaped first (& → &amp;, < → &lt;,
 *      > → &gt;) so any <script> or other tags from the LLM become inert text.
 *   2. Markdown patterns (bold, lists, tables, headings, etc.) are converted
 *      to HTML strings using only tags from a fixed allowlist.
 *   3. The resulting HTML string is parsed by DOMParser (which does NOT execute
 *      scripts) and walked with an element/attribute allowlist sanitizer.
 *   4. The sanitized DOM nodes are returned for safe insertion via appendChild.
 *
 * No external libraries. No innerHTML on live DOM. No eval. No XSS surface.
 *
 * Supported: paragraphs, line breaks, bold, italic, inline code, code blocks,
 *           unordered/ordered lists, tables, headings (1-6), blockquotes,
 *           horizontal rules, links (safe protocols only).
 */
function renderMarkdown(md) {
  if (!md || typeof md !== 'string' || !md.trim()) return null;

  // Step 1 — normalize line endings & escape all HTML entities in raw text
  var raw = md.replace(/\r\n?/g, '\n')
              .replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;');

  // Step 2 — extract code blocks & inline code so they are not parsed as Markdown
  var codeBlocks = [];
  var inlineCodes = [];

  raw = raw.replace(/```(\w*)\n?([\s\S]*?)```/g, function (m, lang, code) {
    codeBlocks.push(code.replace(/\n$/, ''));
    return '\x00CB' + (codeBlocks.length - 1) + '\x00';
  });
  raw = raw.replace(/`([^`]+)`/g, function (m, code) {
    inlineCodes.push(code);
    return '\x00IC' + (inlineCodes.length - 1) + '\x00';
  });

  // Step 3 — block-level parsing
  var lines = raw.split('\n');
  var html = '';
  var i = 0;

  while (i < lines.length) {
    var line = lines[i];

    // Standalone code-block placeholder
    if (/^\x00CB\d+\x00$/.test(line)) {
      html += line + '\n';
      i++;
      continue;
    }

    // Blank line
    if (line.trim() === '') { i++; continue; }

    // Headings (# … ######)
    var hMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (hMatch) {
      var lvl = hMatch[1].length;
      html += '<h' + lvl + '>' + _mdInline(hMatch[2]) + '</h' + lvl + '>\n';
      i++;
      continue;
    }

    // Horizontal rule (only on its own line)
    if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      html += '<hr>\n';
      i++;
      continue;
    }

    // Blockquote (consecutive lines starting with >)
    if (/^>\s?/.test(line)) {
      var qLines = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        qLines.push(lines[i].replace(/^>\s?/, ''));
        i++;
      }
      html += '<blockquote>' + _mdInline(qLines.join('<br>')) + '</blockquote>\n';
      continue;
    }

    // Table — header row followed by a separator row (|---|---|)
    if (line.indexOf('|') !== -1 && i + 1 < lines.length &&
        /^\|?[\s:|-]+$/.test(lines[i + 1]) && lines[i + 1].indexOf('-') !== -1) {
      var tResult = _mdTable(lines, i);
      if (tResult) { html += tResult.html; i += tResult.consumed; continue; }
    }

    // Unordered list (-, *, +)
    if (/^\s*[-*+]\s+/.test(line)) {
      var uItems = [];
      while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
        uItems.push(lines[i].replace(/^\s*[-*+]\s+/, ''));
        i++;
      }
      html += '<ul>' + uItems.map(function (it) {
        return '<li>' + _mdInline(it) + '</li>';
      }).join('') + '</ul>\n';
      continue;
    }

    // Ordered list (1. 2. 3.)
    if (/^\s*\d+\.\s+/.test(line)) {
      var oItems = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        oItems.push(lines[i].replace(/^\s*\d+\.\s+/, ''));
        i++;
      }
      html += '<ol>' + oItems.map(function (it) {
        return '<li>' + _mdInline(it) + '</li>';
      }).join('') + '</ol>\n';
      continue;
    }

    // Paragraph — collect consecutive "plain" lines
    var pLines = [];
    while (i < lines.length && lines[i].trim() !== '' &&
           !/^(#{1,6})\s+/.test(lines[i]) &&
           !/^\s*[-*+]\s+/.test(lines[i]) &&
           !/^\s*\d+\.\s+/.test(lines[i]) &&
           !/^>\s?/.test(lines[i]) &&
           !/^\x00CB\d+\x00$/.test(lines[i]) &&
           !/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(lines[i]) &&
           !(lines[i].indexOf('|') !== -1 && i + 1 < lines.length &&
             /^\|?[\s:|-]+$/.test(lines[i + 1]) && lines[i + 1].indexOf('-') !== -1)) {
      pLines.push(lines[i]);
      i++;
    }
    if (pLines.length) {
      // Single newline within a paragraph → <br> for line break
      html += '<p>' + _mdInline(pLines.join('<br>')) + '</p>\n';
    }
  }

  // Step 4 — restore code blocks & inline code
  html = html.replace(/\x00CB(\d+)\x00/g, function (m, idx) {
    return '<pre><code>' + codeBlocks[parseInt(idx, 10)] + '</code></pre>';
  });
  html = html.replace(/\x00IC(\d+)\x00/g, function (m, idx) {
    return '<code>' + inlineCodes[parseInt(idx, 10)] + '</code>';
  });

  // Step 5 — sanitize via DOMParser + allowlist
  return _mdSanitize(html);
}

/** Inline Markdown: bold, italic, links. Operates on already-escaped text. */
function _mdInline(text) {
  // Bold — **text** or __text__
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/__([^_]+)__/g, '<strong>$1</strong>');
  // Italic — *text* or _text_ (after bold so ** is already consumed)
  // Lookbehind/ahead prevents matching inside words (e.g. file_name) and
  // requires no space right after the opening / before the closing delimiter.
  text = text.replace(/(?<![*\w])\*(?!\s)([^*]+?)(?<!\s)\*(?![*\w])/g, '<em>$1</em>');
  text = text.replace(/(?<![_\w])_(?!\s)([^_]+?)(?<!\s)_(?![_\w])/g, '<em>$1</em>');
  // Links — [text](url) only with safe protocols
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function (m, txt, url) {
    if (/^(https?:|mailto:)/i.test(url)) {
      return '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + txt + '</a>';
    }
    return txt;
  });
  return text;
}

/** Parse a Markdown table starting at lines[startIdx]. Returns { html, consumed }. */
function _mdTable(lines, startIdx) {
  var parseRow = function (line) {
    var cells = line.split('|');
    if (cells.length && cells[0].trim() === '') cells.shift();
    if (cells.length && cells[cells.length - 1].trim() === '') cells.pop();
    return cells.map(function (c) { return c.trim(); });
  };

  var headers = parseRow(lines[startIdx]);

  var html = '<div class="md-table"><table><thead><tr>';
  headers.forEach(function (h) { html += '<th>' + _mdInline(h) + '</th>'; });
  html += '</tr></thead><tbody>';

  var i = startIdx + 2; // skip header + separator
  while (i < lines.length && lines[i].trim() !== '' &&
         lines[i].indexOf('|') !== -1 &&
         !/^(#{1,6})\s+/.test(lines[i]) &&
         !/^\s*[-*+]\s+/.test(lines[i]) &&
         !/^\s*\d+\.\s+/.test(lines[i])) {
    var cells = parseRow(lines[i]);
    html += '<tr>';
    for (var j = 0; j < headers.length; j++) {
      html += '<td>' + _mdInline(cells[j] || '') + '</td>';
    }
    html += '</tr>';
    i++;
  }
  html += '</tbody></table></div>\n';
  return { html: html, consumed: i - startIdx };
}

/**
 * Parse an HTML string with DOMParser and sanitize with an allowlist.
 * Returns a DocumentFragment ready for safe appendChild insertion.
 */
function _mdSanitize(html) {
  var ALLOWED_TAGS = {
    p:1, br:1, strong:1, em:1, ul:1, ol:1, li:1,
    table:1, thead:1, tbody:1, tr:1, th:1, td:1,
    code:1, pre:1, h1:1, h2:1, h3:1, h4:1, h5:1, h6:1,
    blockquote:1, hr:1, a:1, span:1, div:1
  };
  var ALLOWED_ATTR = {
    a: { href:1, target:1, rel:1 },
    div: { class:1 }
  };

  var doc = new DOMParser().parseFromString(html, 'text/html');

  function walk(node) {
    var children = Array.prototype.slice.call(node.childNodes);
    for (var k = 0; k < children.length; k++) {
      var child = children[k];
      if (child.nodeType === 8) { // comment node — remove
        node.removeChild(child);
        continue;
      }
      if (child.nodeType === 1) { // element node
        var tag = child.tagName.toLowerCase();
        if (!ALLOWED_TAGS[tag]) {
          // Replace disallowed element with its text content (no HTML preserved)
          var replacement = document.createTextNode(child.textContent || '');
          node.replaceChild(replacement, child);
          continue;
        }
        // Strip non-allowed attributes
        var allowed = ALLOWED_ATTR[tag] || {};
        var attrs = Array.prototype.slice.call(child.attributes);
        for (var a = 0; a < attrs.length; a++) {
          var attrName = attrs[a].name.toLowerCase();
          var attrVal = attrs[a].value;
          if (!allowed[attrName]) {
            child.removeAttribute(attrs[a].name);
          } else if (attrName === 'href' && !/^(https?:|mailto:|#)/i.test(attrVal)) {
            child.removeAttribute(attrs[a].name);
          }
        }
        walk(child);
      }
    }
  }

  walk(doc.body);

  var frag = document.createDocumentFragment();
  while (doc.body.firstChild) {
    frag.appendChild(doc.body.firstChild);
  }
  return frag;
}

/* ── Append messages to chat ── */
function appendMessage(role, text, sources) {
  const isUser = role === 'user';

  const msgEl = document.createElement('div');
  msgEl.className = `message ${role}`;

  const avatarEl = document.createElement('div');
  avatarEl.className = 'msg-avatar';
  avatarEl.textContent = isUser ? 'U' : 'M';

  const bubbleEl = document.createElement('div');
  bubbleEl.className = 'msg-bubble';

  const senderEl = document.createElement('div');
  senderEl.className = 'msg-sender';
  senderEl.textContent = isUser ? 'You' : 'MITS AI';

  const textEl = document.createElement('div');
  textEl.className = 'msg-text';

  if (isUser) {
    textEl.textContent = text; // user input — always plain text, no XSS risk
  } else {
    // AI response — render Markdown safely (escaped + sanitized DOM, never innerHTML)
    var rendered = renderMarkdown(text);
    if (rendered && rendered.childNodes.length > 0) {
      textEl.appendChild(rendered);
    } else {
      textEl.textContent = text; // fallback to plain text
    }
  }

  bubbleEl.appendChild(senderEl);
  bubbleEl.appendChild(textEl);

  // Sources block (AI messages only)
  if (!isUser && sources && sources.length > 0) {
    const sourcesEl = document.createElement('div');
    sourcesEl.className = 'sources';

    const labelEl = document.createElement('div');
    labelEl.className = 'sources-label';
    labelEl.textContent = 'Sources';

    sourcesEl.appendChild(labelEl);

    // deduplicate source titles
    const seen = new Set();
    sources.forEach(src => {
      const title = src.title || src.source || 'MITS document';
      if (seen.has(title)) return;
      seen.add(title);

      const itemEl = document.createElement('div');
      itemEl.className = 'source-item';
      // show just the filename, not the full path
      const filename = title.split(/[\\/]/).pop();
      itemEl.textContent = filename;
      sourcesEl.appendChild(itemEl);
    });

    bubbleEl.appendChild(sourcesEl);
  }

  msgEl.appendChild(avatarEl);
  msgEl.appendChild(bubbleEl);
  chatMessages.appendChild(msgEl);

  // Scroll to the new message
  msgEl.scrollIntoView({ behavior: 'smooth', block: 'end' });

  return msgEl;
}

/** Show the animated "thinking" bubble; returns the element so it can be replaced. */
function appendThinking() {
  const msgEl = document.createElement('div');
  msgEl.className = 'message ai';
  msgEl.id = 'thinking-bubble';

  const avatarEl = document.createElement('div');
  avatarEl.className = 'msg-avatar';
  avatarEl.textContent = 'M';

  const bubbleEl = document.createElement('div');
  bubbleEl.className = 'msg-bubble';

  const textEl = document.createElement('div');
  textEl.className = 'msg-text';

  const thinkingEl = document.createElement('div');
  thinkingEl.className = 'thinking';
  thinkingEl.innerHTML = '<span></span><span></span><span></span>';

  textEl.appendChild(thinkingEl);
  bubbleEl.appendChild(textEl);
  msgEl.appendChild(avatarEl);
  msgEl.appendChild(bubbleEl);
  chatMessages.appendChild(msgEl);
  msgEl.scrollIntoView({ behavior: 'smooth', block: 'end' });

  return msgEl;
}

function removeThinking() {
  const el = document.getElementById('thinking-bubble');
  if (el) el.remove();
}

/* ── Core send function ── */
async function sendMessage(questionText) {
  const question = (questionText || chatInput.value).trim();
  if (!question || isLoading) return;

  // Switch to chat view if on home
  showChat();

  // Add user message to UI
  appendMessage('user', question);
  chatHistory.push({ role: 'user', text: question });

  // Clear input immediately
  chatInput.value = '';
  autogrow();

  // Track this question in recent list
  addRecentChat(question.length > 48 ? question.slice(0, 45) + '…' : question);

  // Show thinking indicator
  const thinkingEl = appendThinking();

  // Lock UI
  setLoading(true);

  try {
    const response = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    // Always remove thinking bubble regardless of success/failure
    removeThinking();

    if (!response.ok) {
      // Parse error detail from FastAPI if available
      let detail = `Server error (${response.status})`;
      try {
        const errBody = await response.json();
        detail = errBody.detail || detail;
      } catch { /* non-JSON error body — keep generic message */ }

      // Log for developer debugging
      console.error('[MITS AI] API error:', response.status, detail);

      // Show user-friendly error
      const errEl = appendMessage('ai', "I couldn't retrieve an answer right now. Please try again.");
      errEl.querySelector('.msg-text').classList.add('error');
      chatHistory.push({ role: 'ai', text: errEl.querySelector('.msg-text').textContent });
      return; // falls through to finally
    }

    const data = await response.json();

    // Validate response shape
    const answer = (data.answer || '').trim();
    const sources = Array.isArray(data.sources) ? data.sources : [];

    if (!answer) {
      appendMessage('ai', "I received an empty response. Please try rephrasing your question.");
      return;
    }

    appendMessage('ai', answer, sources);
    chatHistory.push({ role: 'ai', text: answer, sources });

  } catch (networkErr) {
    // Network failure (no connection, CORS, etc.)
    removeThinking();
    console.error('[MITS AI] Network error:', networkErr);

    const errEl = appendMessage('ai', "Network error — could not reach the server. Please check your connection and try again.");
    errEl.querySelector('.msg-text').classList.add('error');
    chatHistory.push({ role: 'ai', text: errEl.querySelector('.msg-text').textContent });

  } finally {
    // ── CRITICAL: always unlock UI, no matter what happened above ──
    setLoading(false);
    chatInput.focus();
  }
}

/* ── Start a chat from a suggestion card / recent item ── */
function startChat(question) {
  chatInput.value = question;
  sendMessage(question);
}

/* ── Event listeners ── */
sendBtn.addEventListener('click', () => sendMessage());

chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

chatInput.addEventListener('input', autogrow);

newChatBtn.addEventListener('click', newChat);

themeBtn.addEventListener('click', toggleTheme);

// Suggestion cards — delegate clicks on the grid
document.getElementById('cards-grid').addEventListener('click', e => {
  const card = e.target.closest('.card');
  if (!card) return;
  const question = card.dataset.question;
  if (question) startChat(question);
});

/* ── Init ── */
initTheme();
renderRecent();
chatInput.focus();
