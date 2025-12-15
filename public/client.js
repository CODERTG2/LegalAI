
document.addEventListener('DOMContentLoaded', () => {
    const chatViewport = document.getElementById('chat-viewport');
    const messageList = document.getElementById('message-list');
    const welcomeScreen = document.getElementById('welcome-screen');
    const queryInput = document.getElementById('query-input');
    const sendButton = document.getElementById('send-btn');
    const clearButton = document.getElementById('clear-btn');
    const greetingEl = document.getElementById('greeting');

    // State tracking
    let isFollowUp = false;

    // Dynamic Greeting
    const hour = new Date().getHours();
    if (hour < 12) greetingEl.textContent = "Good morning";
    else if (hour < 18) greetingEl.textContent = "Good afternoon";
    else greetingEl.textContent = "Good evening";

    // Auto-focus input
    queryInput.focus();

    // Global helper for suggestion cards
    window.setInput = (text) => {
        queryInput.value = text;
        queryInput.focus();
        handleSearch();
    };

    // Handle Enter key
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSearch();
        }
    });

    sendButton.addEventListener('click', handleSearch);

    clearButton.addEventListener('click', resetChat);

    async function resetChat() {
        // Clear backend history
        try {
            await fetch('/api/mcp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: "clean_history", arguments: {} })
            });
        } catch (e) {
            console.error("Failed to clear history:", e);
        }

        // Reset frontend state
        isFollowUp = false;
        messageList.innerHTML = '';
        messageList.style.display = 'none';
        welcomeScreen.style.display = 'flex';
        clearButton.style.display = 'none';
        queryInput.value = '';
        queryInput.focus();
    }

    async function handleSearch() {
        const query = queryInput.value.trim();
        if (!query) return;

        // UI Transition: Hide welcome, show chat
        if (welcomeScreen.style.display !== 'none') {
            welcomeScreen.style.display = 'none';
            messageList.style.display = 'flex';
            clearButton.style.display = 'block';
        }

        // Add user message
        typeMessage('user', query);
        queryInput.value = '';
        queryInput.disabled = true;
        sendButton.disabled = true;

        // Show loading state
        const loadingId = addLoadingIndicator();
        scrollToBottom();

        try {
            // Determine tool to call
            const toolName = isFollowUp ? "follow_up" : "search";

            const response = await fetch('/api/mcp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: toolName,
                    arguments: { query: query }
                })
            });

            const data = await response.json();

            // Remove loading indicator
            removeLoadingIndicator(loadingId);

            if (data.error) {
                await typeMessage('ai', `**Error:** ${data.error}`);
            } else if (data.content && data.content[0] && data.content[0].text) {
                await typeMessage('ai', data.content[0].text);
                // Mark conversation as active for next time
                isFollowUp = true;
            } else if (typeof data === 'string') {
                await typeMessage('ai', data);
                // Mark conversation as active for next time
                isFollowUp = true;
            } else {
                await typeMessage('ai', "I'm not sure how to interpret that response.");
                console.log('Unexpected response:', data);
            }

        } catch (error) {
            removeLoadingIndicator(loadingId);
            await typeMessage('ai', `**Connection Error:** ${error.message}`);
        } finally {
            queryInput.disabled = false;
            sendButton.disabled = false;
            queryInput.focus();
            scrollToBottom();
        }
    }

    async function typeMessage(role, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        // Use generic friendly icons
        avatar.textContent = role === 'user' ? '👤' : '✨';

        const content = document.createElement('div');
        content.className = 'message-content';

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        messageList.appendChild(messageDiv);

        if (role === 'user') {
            content.innerHTML = formatMarkdown(text);
            scrollToBottom();
            return;
        }

        // Typing effect for AI
        const chunks = text.split(/(\s+)/); // Keep delimiters to preserve spacing
        let currentText = '';

        for (const chunk of chunks) {
            currentText += chunk;
            content.innerHTML = formatMarkdown(currentText);
            scrollToBottom();

            // Add delay only for non-empty text to simulate typing
            if (chunk.trim().length > 0) {
                await new Promise(r => setTimeout(r, 50));
            }
        }
        // Ensure final render matches exactly
        content.innerHTML = formatMarkdown(text);
        scrollToBottom();
    }

    function addLoadingIndicator() {
        const id = 'loading-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = 'message ai';
        div.innerHTML = `
            <div class="avatar">✨</div>
            <div class="message-content" style="padding: 1rem;">
                <div class="typing-dots">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
            </div>
        `;
        messageList.appendChild(div);
        return id;
    }

    function removeLoadingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        chatViewport.scrollTop = chatViewport.scrollHeight;
    }

    function formatMarkdown(text) {
        if (!text) return '';

        let html = text.replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Italic
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Code blocks
        html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Links [text](url)
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

        // Lists
        html = html.replace(/^\s*-\s+(.*)/gim, '<ul><li>$1</li></ul>');
        html = html.replace(/<\/ul>\s*<ul>/g, ''); // Join adjacent lists

        // New lines to <br> (only if not inside pre tags)
        html = html.replace(/\n/g, '<br>');

        return html;
    }
});
