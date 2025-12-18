
document.addEventListener('DOMContentLoaded', () => {
    const chatViewport = document.getElementById('chat-viewport');
    const messageList = document.getElementById('message-list');
    const welcomeScreen = document.getElementById('welcome-screen');
    const queryInput = document.getElementById('query-input');
    const sendButton = document.getElementById('send-btn');
    const clearButton = document.getElementById('clear-btn');
    const greetingEl = document.getElementById('greeting');

    // Settings Elements
    const settingsToggle = document.getElementById('settings-toggle');
    const settingsPanel = document.getElementById('settings-panel');
    const checkAuto = document.getElementById('check-auto');
    const manualDomainsContainer = document.getElementById('manual-domains');

    // Sliders
    const sliderBills = document.getElementById('slider-bills');
    const valBills = document.getElementById('val-bills');
    const sliderOrders = document.getElementById('slider-orders');
    const valOrders = document.getElementById('val-orders');
    const sliderOpinions = document.getElementById('slider-opinions');
    const valOpinions = document.getElementById('val-opinions');

    // Settings State
    let settingsOpen = false;
    let isFollowUp = false;

    // Toggle Settings
    settingsToggle.addEventListener('click', () => {
        settingsOpen = !settingsOpen;
        settingsPanel.classList.toggle('open', settingsOpen);
        settingsToggle.classList.toggle('active', settingsOpen);
    });

    // Slider Updates
    function connectSlider(slider, display) {
        slider.addEventListener('input', () => {
            display.textContent = slider.value;
        });
    }
    connectSlider(sliderBills, valBills);
    connectSlider(sliderOrders, valOrders);
    connectSlider(sliderOpinions, valOpinions);

    // Domain toggling logic
    checkAuto.addEventListener('change', () => {
        if (checkAuto.checked) {
            manualDomainsContainer.classList.remove('active');
            // Uncheck all manual to avoid confusion? Or just visually disable?
            // Let's visually disable as handled by CSS pointer-events
        } else {
            manualDomainsContainer.classList.add('active');
        }
    });

    // Helper to get selected domains
    function getSelectedDomains() {
        if (checkAuto.checked) return ""; // Empty string triggers auto logic in backend

        const checkboxes = manualDomainsContainer.querySelectorAll('input[type="checkbox"]:checked');
        const domains = Array.from(checkboxes).map(cb => cb.dataset.domain);
        return domains.join(",");
    }

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

        // PII Check
        const piiWarning = checkPII(query);
        if (piiWarning) {
            // Show simple alert for now, could be a toast in future
            alert("⚠️ Privacy Warning: " + piiWarning);
            return;
        }

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

        // Collect Settings
        const k_bills = parseInt(sliderBills.value);
        const k_orders = parseInt(sliderOrders.value);
        const k_opinions = parseInt(sliderOpinions.value);
        const selectedDomains = getSelectedDomains();

        // Show thinking process
        const steps = ["Analyzing query intent...", "Retrieving legal documents...", "Verifying citations..."];
        const thinkingId = await showThinkingProcess(steps);

        // Simulate step progress while waiting for backend (since we can't stream real status yet)
        let stepInterval = setInterval(() => {
            const currentStep = document.querySelector(`#${thinkingId} .active`);
            if (currentStep) {
                const index = parseInt(currentStep.id.split('-step-')[1]);
                if (index < steps.length - 1) {
                    updateThinkingStep(thinkingId, index, 'completed');
                }
            }
        }, 1500);

        try {
            // Determine tool to call
            const toolName = isFollowUp ? "follow_up" : "search";

            // Build arguments
            const args = {
                query: query,
                k_bills: k_bills,
                k_orders: k_orders,
                k_opinions: k_opinions,
                domains: selectedDomains
            };

            const response = await fetch('/api/mcp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: toolName,
                    arguments: args
                })
            });

            const data = await response.json();

            // Clear interval and remove thinking
            clearInterval(stepInterval);
            removeThinkingProcess(thinkingId);

            if (data.error) {
                await typeMessage('ai', `**Error:** ${data.error}`);
            } else if (data.content && data.content[0] && data.content[0].text) {
                const rawText = data.content[0].text;
                let parsed = null;
                try {
                    parsed = JSON.parse(rawText);
                } catch (e) {
                    // Not JSON, fallback to raw text
                }

                if (parsed && parsed.thinking) {
                    // Render thinking details first
                    renderThinkingDetails(parsed.thinking);
                    // Render answer
                    await typeMessage('ai', parsed.answer, query, parsed.sources);
                } else {
                    // Legacy/fallback
                    await typeMessage('ai', rawText, query);
                }

                // Mark conversation as active for next time
                isFollowUp = true;
            } else if (typeof data === 'string') {
                await typeMessage('ai', data, query);
                // Mark conversation as active for next time
                isFollowUp = true;

            } else if (data.answer) {
                // Handle direct JSON response from my new backend structure
                if (data.thinking) {
                    renderThinkingDetails(data.thinking);
                }
                await typeMessage('ai', data.answer, query, data.sources);
                isFollowUp = true;
            } else {
                await typeMessage('ai', "I'm not sure how to interpret that response.");
                console.log('Unexpected response:', data);
            }

        } catch (error) {
            clearInterval(stepInterval);
            removeThinkingProcess(thinkingId);
            await typeMessage('ai', `**Connection Error:** ${error.message}`);
        } finally {
            queryInput.disabled = false;
            sendButton.disabled = false;
            queryInput.focus();
            scrollToBottom();
        }
    }

    async function typeMessage(role, text, query = null, sources = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        if (sources && sources.length > 0) {
            messageDiv.dataset.sources = JSON.stringify(sources);
        }

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

        // Add Feedback UI if query is present (meaning it's a response to a query)
        if (query) {
            addFeedbackControls(content, query, text);
        }

        scrollToBottom();
    }

    function addFeedbackControls(container, query, response) {
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'feedback-actions';

        const upBtn = document.createElement('button');
        upBtn.className = 'feedback-btn';
        upBtn.innerHTML = '👍';
        upBtn.title = 'Helpful';

        const downBtn = document.createElement('button');
        downBtn.className = 'feedback-btn';
        downBtn.innerHTML = '👎';
        downBtn.title = 'Not helpful';

        feedbackDiv.appendChild(upBtn);
        feedbackDiv.appendChild(downBtn);
        container.appendChild(feedbackDiv);

        let hasVoted = false;

        const handleVote = async (type) => {
            if (hasVoted) return; // Prevent double voting for simplicity or allow change? Let's allow change visually but maybe just send update.

            // Visual update
            if (type === 'good') {
                upBtn.classList.add('active', 'good');
                downBtn.classList.remove('active', 'bad');
            } else {
                downBtn.classList.add('active', 'bad');
                upBtn.classList.remove('active', 'good');
            }

            // Send to backend
            try {
                await fetch('/api/mcp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: "update_user_evaluation",
                        arguments: {
                            query: query,
                            response: response,
                            evaluation: type
                        }
                    })
                });
            } catch (e) {
                console.error("Failed to send evaluation:", e);
            }

            // Show feedback form if bad
            if (type === 'bad') {
                showFeedbackForm(container, query, response);
            }
        };

        upBtn.addEventListener('click', () => handleVote('good'));
        downBtn.addEventListener('click', () => handleVote('bad'));
    }

    function showFeedbackForm(container, query, response) {
        // Check if form already exists
        if (container.querySelector('.feedback-form')) return;

        const form = document.createElement('div');
        form.className = 'feedback-form';

        const textarea = document.createElement('textarea');
        textarea.className = 'feedback-textarea';
        textarea.placeholder = "Tell us more about what went wrong...";

        const submitBtn = document.createElement('button');
        submitBtn.className = 'feedback-submit';
        submitBtn.textContent = 'Submit Feedback';

        form.appendChild(textarea);
        form.appendChild(submitBtn);
        container.appendChild(form);
        scrollToBottom();

        submitBtn.addEventListener('click', async () => {
            const feedback = textarea.value.trim();
            if (!feedback) return;

            submitBtn.textContent = 'Sending...';
            submitBtn.disabled = true;

            try {
                await fetch('/api/mcp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: "update_user_feedback",
                        arguments: {
                            query: query,
                            response: response,
                            feedback: feedback
                        }
                    })
                });

                form.innerHTML = '<div style="color: #4ade80; margin-top: 0.5rem; font-size: 0.9rem;">Thank you for your feedback!</div>';
            } catch (e) {
                console.error("Failed to send feedback:", e);
                submitBtn.textContent = 'Error. Try again.';
                submitBtn.disabled = false;
            }
        });
    }

    // PII Guardrail
    function checkPII(text) {
        // Regex patterns for common US PII
        const ssnPattern = /\b\d{3}[-.]?\d{2}[-.]?\d{4}\b/;
        const phonePattern = /\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/;
        const emailPattern = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/;

        if (ssnPattern.test(text)) return "It looks like you entered a Social Security Number. For your privacy, please remove it.";
        if (phonePattern.test(text)) return "It looks like you entered a phone number. For your privacy, please remove it.";
        if (emailPattern.test(text)) return "It looks like you entered an email address. For your privacy, please remove it.";

        return null;
    }

    // Thinking Process Visualization
    async function showThinkingProcess(steps) {
        const id = 'thinking-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = 'message ai';

        let stepsHtml = steps.map((step, index) =>
            `<div class="thinking-step ${index === 0 ? 'active' : ''}" id="${id}-step-${index}">
                <div class="step-icon">
                    ${index === 0 ? getSpinnerIcon() : '⚪'}
                </div>
                <span>${step}</span>
            </div>`
        ).join('');

        div.innerHTML = `
            <div class="avatar">✨</div>
            <div class="message-content" style="padding: 1rem;">
                <div class="thinking-process">
                    ${stepsHtml}
                </div>
            </div>
        `;
        messageList.appendChild(div);
        scrollToBottom();
        return id;
    }

    async function updateThinkingStep(id, stepIndex, status) {
        const stepEl = document.getElementById(`${id}-step-${stepIndex}`);
        if (!stepEl) return;

        const iconEl = stepEl.querySelector('.step-icon');

        if (status === 'completed') {
            stepEl.classList.remove('active');
            stepEl.classList.add('completed');
            iconEl.innerHTML = '✅';

            // Activate next step if exists
            const nextStep = document.getElementById(`${id}-step-${stepIndex + 1}`);
            if (nextStep) {
                nextStep.classList.add('active');
                nextStep.querySelector('.step-icon').innerHTML = getSpinnerIcon();
            }
        }
    }

    function getSpinnerIcon() {
        return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>`;
    }

    function removeThinkingProcess(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function addLoadingIndicator() {
        // Fallback or deprecated - replaced by showThinkingProcess
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
        const scrollHeight = chatViewport.scrollHeight;
        const currentScroll = chatViewport.scrollTop + chatViewport.clientHeight;

        // Only auto-scroll if user is already near bottom or it's a new message
        chatViewport.scrollTo({
            top: scrollHeight,
            behavior: 'smooth'
        });
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
        // New lines to <br> (only if not inside pre tags)
        html = html.replace(/\n/g, '<br>');

        // Citations [1] -> <span ...>[1]</span>
        // Check for sources only if we really want to be strict, but simple regex is fine
        html = html.replace(/\[(\d+)\]/g, '<span class="citation-link" data-index="$1">[$1]</span>');

        return html;
    }

    function renderThinkingDetails(thinking) {
        const { domains, context, cached } = thinking;
        const messageList = document.getElementById('message-list');

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai thinking-message';

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = '🧠';

        const msgContent = document.createElement('div');
        msgContent.className = 'message-content';

        const details = document.createElement('details');
        details.className = 'thinking-details';

        const summary = document.createElement('summary');
        summary.textContent = 'View Thinking Process';
        details.appendChild(summary);

        const content = document.createElement('div');
        content.className = 'thinking-content';

        // Metadata
        const metaDiv = document.createElement('div');
        metaDiv.className = 'thinking-meta';
        metaDiv.innerHTML = `
            <div style="margin-bottom: 4px;"><strong>Domains:</strong> ${domains ? domains.join(', ') : 'N/A'}</div>
            <div><strong>Cached:</strong> ${cached ? '✅ Yes' : '❌ No'}</div>
        `;
        content.appendChild(metaDiv);

        // Context
        if (context) {
            const contextHeader = document.createElement('div');
            contextHeader.innerHTML = '<strong>Context Used:</strong>';
            contextHeader.style.marginTop = '0.5rem';
            content.appendChild(contextHeader);

            const pre = document.createElement('pre');
            pre.className = 'thinking-context-block';
            pre.textContent = context;
            content.appendChild(pre);
        }

        details.appendChild(content);
        msgContent.appendChild(details);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(msgContent);

        messageList.appendChild(messageDiv);
        scrollToBottom();
    }

    // Tooltip Logic
    const tooltip = document.createElement('div');
    tooltip.className = 'citation-tooltip';
    document.body.appendChild(tooltip);

    let activeTooltipTarget = null;

    messageList.addEventListener('mouseover', (e) => {
        if (e.target.classList.contains('citation-link')) {
            const link = e.target;
            const index = parseInt(link.dataset.index);
            const messageDiv = link.closest('.message');

            if (messageDiv && messageDiv.dataset.sources) {
                try {
                    const sources = JSON.parse(messageDiv.dataset.sources);
                    // Adjust for 1-based index
                    const source = sources[index - 1];
                    if (source) {
                        showTooltip(link, source);
                    }
                } catch (err) {
                    console.error("Error parsing sources", err);
                }
            }
        }
    });

    messageList.addEventListener('mouseout', (e) => {
        if (e.target.classList.contains('citation-link')) {
            hideTooltip();
        }
    });

    function showTooltip(target, sourceData) {
        activeTooltipTarget = target;

        // Extract useful info from sourceData
        // Need to replicate format_context logic or just use what's available
        const chunk = sourceData.chunk || {};
        let title = "Source";
        let meta = "";
        let body = "";
        let url = null;

        if (chunk.congress) {
            title = `Bill: ${chunk.title || 'Unknown'}`;
            meta = `${chunk.congress}th Congress, H.R. ${chunk.number}`;
            body = chunk.latestAction?.text || "No action text";
        } else if (chunk.order_number) {
            title = `Executive Order: ${chunk.title || 'Unknown'}`;
            meta = chunk.signing_date || "";
            body = chunk.chunk_text?.text || "";
        } else if (chunk.resource_uri) { // Supreme Court
            title = "Supreme Court Decision";
            meta = chunk.date_created || "";
            body = chunk.text || "";
            url = chunk.absolute_url;
        } else if (chunk.body) { // News
            title = chunk.title || "News Article";
            meta = chunk.date || "";
            body = chunk.body || "";
            url = sourceData.uri; // NewsClient.py uses 'uri' if available
        } else {
            body = JSON.stringify(chunk).slice(0, 100) + "...";
        }

        // Truncate body
        if (body.length > 150) body = body.slice(0, 150) + "...";

        let html = `<strong>${title}</strong><br>`;
        if (meta) html += `<span style="opacity:0.8; font-size:0.85em;">${meta}</span><br>`;
        html += `<div style="margin-top:4px; font-size:0.9em; line-height:1.4;">${body}</div>`;
        if (url) {
            html += `<a href="${url}" target="_blank" style="display:block; margin-top:6px; color:#60a5fa; font-size:0.85em;">Open Link ↗</a>`;
        }

        tooltip.innerHTML = html;
        tooltip.style.display = 'block';

        // Position logic
        const rect = target.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();

        let top = rect.top - tooltipRect.height - 10;
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);

        // Keep in bounds
        if (left < 10) left = 10;
        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }
        if (top < 10) {
            top = rect.bottom + 10; // Flip to bottom if no space on top
        }

        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;
    }

    function hideTooltip() {
        tooltip.style.display = 'none';
        activeTooltipTarget = null;
    }
});
