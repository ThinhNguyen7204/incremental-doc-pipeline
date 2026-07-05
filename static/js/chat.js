document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('chatForm');
  const input = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');
  const chatFeed = document.getElementById('chatFeed');

  // Auto-resize textarea
  input.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    if (this.value.trim() === '') {
      this.style.height = 'auto';
    }
  });

  // Handle Enter key (Shift+Enter for new line)
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event('submit'));
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message) return;

    // Reset input
    input.value = '';
    input.style.height = 'auto';
    input.focus();
    sendBtn.disabled = true;

    // Add user message
    addUserMessage(message);

    // Add loading state
    const loadingId = 'loading-' + Date.now();
    addLoadingBotMessage(loadingId);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });

      const data = await response.json();
      removeLoadingMessage(loadingId);

      if (!response.ok) {
        addBotMessage("Sorry, I encountered an error: " + (data.error || "Unknown error"), []);
      } else {
        addBotMessage(data.answer, data.citations);
      }
    } catch (err) {
      removeLoadingMessage(loadingId);
      addBotMessage("Sorry, I couldn't reach the server.", []);
    } finally {
      sendBtn.disabled = false;
    }
  });

  function getCurrentTimeStr() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function addUserMessage(text) {
    const row = document.createElement('article');
    row.className = 'message-row user-message';
    row.innerHTML = `
      <div class="bubble user-bubble">${escapeHTML(text)}</div>
      <div class="message-footer user-footer"><span class="timestamp">${getCurrentTimeStr()}</span></div>
    `;
    chatFeed.appendChild(row);
    scrollToBottom();
  }

  function addLoadingBotMessage(id) {
    const row = document.createElement('article');
    row.className = 'message-row bot-message';
    row.id = id;
    row.innerHTML = `
      <div class="mini-bot" aria-hidden="true">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-bot-icon lucide-bot"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
      </div>
      <div class="typing-indicator"><span></span><span></span><span></span></div>
    `;
    chatFeed.appendChild(row);
    scrollToBottom();
  }

  function removeLoadingMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function addBotMessage(text, citations) {
    const row = document.createElement('article');
    row.className = 'message-row bot-message';

    // Format text basic markdown (links, bold, bullets)
    let formattedText = escapeHTML(text);
    
    // Remove Article URL lines from the text body since we show them as nice links below
    formattedText = formattedText.replace(/^.*Article URL:.*$/gim, '');

    // Bold (**text**)
    formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Bullet points (both - and *)
    formattedText = formattedText.replace(/^[-*]\s+(.*)$/gm, '<li>$1</li>');
    formattedText = formattedText.replace(/(<li>.*<\/li>)/s, match => `<ul>${match}</ul>`);

    // Italic (*text*) - now safe since bullet points * are converted to <li>
    formattedText = formattedText.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Code
    formattedText = formattedText.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Markdown Links
    formattedText = formattedText.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // Raw URLs (auto link)
    formattedText = formattedText.replace(/(^|[^="'])(https?:\/\/[^\s<]+)/g, '$1<a href="$2" target="_blank" rel="noopener noreferrer">$2</a>');

    // Quotes to Bold
    formattedText = formattedText.replace(/&quot;(.*?)&quot;/g, '<strong>$1</strong>');

    // Paragraphs
    formattedText = formattedText.split('\n\n').filter(p => p.trim()).map(p => {
      if(p.startsWith('<ul>')) return p;
      return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    }).join('');

    let citationsHTML = '';
    if (citations && citations.length > 0) {
      const links = citations.map(c => `<a href="${escapeHTML(c.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(c.label)}</a>`).join('<br>');
      citationsHTML = `<div class="citations-text"><p>For more details: ${links}</p></div>`;
    }

    row.innerHTML = `
      <div class="mini-bot" aria-hidden="true">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-bot-icon lucide-bot"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
      </div>
      <div class="status-steps">
        <div class="status-step" style="opacity: 0; animation: fadeIn 0.3s ease-out 0s forwards;">
          <div class="status-icon check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg></div>
          <span>Searched articles</span>
        </div>
        <div class="status-step" style="opacity: 0; animation: fadeIn 0.3s ease-out 0.4s forwards;">
          <div class="status-icon check"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg></div>
          <span>Read article</span>
        </div>
      </div>
      <div class="bubble bot-bubble" style="opacity: 0; animation: fadeIn 0.3s ease-out 0.8s forwards;">
        ${formattedText}
        ${citationsHTML}
        <div class="message-footer bot-footer">
          <button class="feedback-btn" aria-label="Thumbs up">
            <svg viewBox="0 0 24 24"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>
          </button>
          <button class="feedback-btn" aria-label="Thumbs down">
            <svg viewBox="0 0 24 24"><path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"/></svg>
          </button>
          <span class="timestamp">${getCurrentTimeStr()}</span>
        </div>
      </div>
    `;

    chatFeed.appendChild(row);
    scrollToBottom();
  }

  function scrollToBottom() {
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }

  function escapeHTML(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
