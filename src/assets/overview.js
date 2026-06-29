/**
 * AI Overview — Client-side Logic
 *
 * Handles streaming AI responses from the /ai-stream endpoint,
 * incremental markdown rendering, citation linking, source cards,
 * and conversational follow-up.
 */
(async () => {
    const CONFIG = __AI_CONFIG__;

    const box = document.getElementById("ai-overview-box");
    const answerContainer = document.getElementById("ai-answer");
    const skeleton = document.getElementById("ai-skeleton");
    const actions = document.getElementById("ai-actions");
    const sourcesContainer = document.getElementById("ai-sources-container");
    const chatHistory = document.getElementById("ai-chat-history");
    const followupForm = document.getElementById("ai-followup-form");
    const followupInput = document.getElementById("ai-followup-input");
    
    if (!box || !answerContainer) return;

    let isStreaming = false;
    let currentContext = CONFIG.context;
    let conversationHistory = "";
    let currentQuery = CONFIG.query;

    // ── Utilities ───────────────────────────────────────────────────
    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    // ── Simple Markdown & Citation Parser ───────────────────────────
    function renderMarkdownAndCitations(text) {
        // Step 1: Extract fenced code blocks BEFORE escaping, so their content
        // is preserved verbatim. We replace them with placeholders and re-inject later.
        const codeBlocks = [];
        text = text.replace(/```([^\n]*)\n([\s\S]*?)```/g, (match, lang, code) => {
            const placeholder = `%%CODEBLOCK_${codeBlocks.length}%%`;
            const escapedCode = escapeHtml(code.replace(/\n$/, "")); // trim trailing newline
            const langLabel = lang.trim() ? `<span class="ai-code-lang">${escapeHtml(lang.trim())}</span>` : "";
            const copyBtn = `<button class="ai-code-copy" onclick="navigator.clipboard.writeText(this.parentElement.querySelector('code').textContent).then(()=>{this.textContent='✅';setTimeout(()=>this.textContent='Copy',1500)})">Copy</button>`;
            codeBlocks.push(
                `<div class="ai-code-block">${langLabel}${copyBtn}<pre><code class="language-${escapeHtml(lang || "text")}">${escapedCode}</code></pre></div>`
            );
            return placeholder;
        });

        // Step 2: Escape remaining HTML
        let html = escapeHtml(text);

        // Step 3: Inline formatting (bold, italic, inline code, headings)
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        html = html.replace(/`(.*?)`/g, '<code>$1</code>');
        
        // Headings
        html = html.replace(/^(#{1,6})\s+(.*)$/gm, (match, hashes, text) => `<h${hashes.length}>${text}</h${hashes.length}>`);

        // Blockquotes (matching &gt; because of escapeHtml, and allowing leading spaces)
        html = html.replace(/^[ \t]*&gt;\s+(.*)$/gm, '<blockquote class="ai-blockquote">$1</blockquote>');

        // Tables
        html = html.replace(/^\|(.+)\|[ \t]*$/gm, (m, content) => {
            if (content.includes('---')) return '<!--SEP-->';
            return '<tr><td>' + content.split('|').map(c => c.trim()).join('</td><td>') + '</td></tr>';
        });
        html = html.replace(/(<tr><td>.*<\/td><\/tr>(?:\n(?:<!--SEP-->\n)?<tr><td>.*<\/td><\/tr>)*)/g, '<div class="ai-table-wrapper"><table>$1</table></div>');
        html = html.replace(/<table>\s*<tr>(.*?)<\/tr>\s*<!--SEP-->\s*/g, '<table><thead><tr>$1</tr></thead><tbody>');
        html = html.replace(/<thead><tr>(.*?)<\/tr><\/thead>/g, (m, p1) => `<thead><tr>${p1.replace(/<td>/g, '<th>').replace(/<\/td>/g, '</th>')}</tr></thead>`);
        html = html.replace(/<\/table><\/div>/g, '</tbody></table></div>'); // Close tbody

        // Numbered lists
        html = html.replace(/^(\d+)\.\s+(.*)$/gm, '<li value="$1">$2</li>');
        html = html.replace(/(<li value="\d+">[^]*?<\/li>(?:\n<li value="\d+">[^]*?<\/li>)*)/g, '<ol>$1</ol>');

        // Bullet lists
        html = html.replace(/^[-*]\s+(.*)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>(?:\n<li>.*<\/li>)*)/g, '<ul>$1</ul>');

        // Clean up newlines inside block elements so they don't get <br/>
        html = html.replace(/(<table[^>]*>[\s\S]*?<\/table>)/g, m => m.replace(/\n/g, ''));
        html = html.replace(/(<ul[^>]*>[\s\S]*?<\/ul>)/g, m => m.replace(/\n/g, ''));
        html = html.replace(/(<ol[^>]*>[\s\S]*?<\/ol>)/g, m => m.replace(/\n/g, ''));
        html = html.replace(/(<blockquote[^>]*>[\s\S]*?<\/blockquote>)/g, m => m.replace(/\n/g, '<br/>'));

        // Paragraphs / Newlines
        html = html.replace(/\n\n+/g, '</p><p>').replace(/\n/g, '<br/>');
        if (!html.startsWith('<p>') && !html.startsWith('<ul') && !html.startsWith('<ol') && !html.startsWith('<h') && !html.startsWith('<div')) {
            html = '<p>' + html + '</p>';
        }
        html = html.replace(/<p>\s*<\/p>/g, '');

        // Step 4: Re-inject code blocks
        codeBlocks.forEach((block, i) => {
            html = html.replace(`%%CODEBLOCK_${i}%%`, block);
        });

        // Step 5: Citations — [1], [2,3], etc.
        const re = /\[(\d{1,2}(?:\s*,\s*\d{1,2})*)\]/g;
        html = html.replace(re, (match, p1) => {
            let links = [];
            for (const n of p1.split(/\s*,\s*/)) {
                const idx = parseInt(n.trim());
                if (idx >= 1 && idx <= CONFIG.urls.length && CONFIG.urls[idx - 1]) {
                    const url = CONFIG.urls[idx - 1];
                    let domain = "";
                    try { domain = new URL(url).hostname.replace("www.", ""); } catch(e){}
                    links.push(`<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="ai-citation" title="${escapeHtml(domain)}">[${escapeHtml(n.trim())}]</a>`);
                } else {
                    links.push(`[${escapeHtml(n.trim())}]`);
                }
            }
            return links.join('');
        });

        return html;
    }

    function renderSourceCards() {
        sourcesContainer.innerHTML = "";
        if (!CONFIG.urls || CONFIG.urls.length === 0) return;

        const seenUrls = new Set();

        CONFIG.urls.forEach((url, i) => {
            if (!url || seenUrls.has(url)) return;
            seenUrls.add(url);
            
            try {
                const urlObj = new URL(url);
                const domain = urlObj.hostname.replace("www.", "");
                const favicon = `https://icons.duckduckgo.com/ip3/${encodeURIComponent(domain)}.ico`;

                const card = document.createElement("a");
                card.className = "ai-source-card";
                card.href = url;
                card.target = "_blank";
                card.rel = "noopener noreferrer";

                // Build card content safely with DOM APIs
                const refSpan = document.createElement("span");
                refSpan.className = "ai-source-ref";
                refSpan.textContent = `[${i + 1}]`;

                const img = document.createElement("img");
                img.src = favicon;
                img.className = "ai-source-icon";
                img.alt = domain;
                img.onerror = function() { this.style.display = 'none'; };

                const domainSpan = document.createElement("span");
                domainSpan.className = "ai-source-domain";
                domainSpan.textContent = domain;

                card.appendChild(refSpan);
                card.appendChild(img);
                card.appendChild(domainSpan);
                sourcesContainer.appendChild(card);
            } catch(e) {}
        });
    }

    // ── Stream Handler ──────────────────────────────────────────────
    async function startStream(queryToAsk, isFollowup = false) {
        if (isStreaming) return;
        isStreaming = true;

        try {
            box.style.display = "block";
            const wrapper = box.parentElement ? box.parentElement.closest(".answer") : null;
            if (wrapper) wrapper.style.display = "";

            actions.style.visibility = "hidden";
            followupForm.style.display = "none";
            sourcesContainer.innerHTML = "";
            answerContainer.innerHTML = "";
            
            // Show the user's query bubble (safe — uses textContent)
            const currentQueryEl = document.getElementById("ai-current-query");
            if (currentQueryEl) currentQueryEl.textContent = queryToAsk;

            // Fast Path: If SearXNG provided a direct answer or infobox, use it immediately
            if (!isFollowup && CONFIG.fastAnswer) {
                if (skeleton) skeleton.style.display = "none";
                answerContainer.innerHTML = renderMarkdownAndCitations(CONFIG.fastAnswer);
                conversationHistory += `\nUser: ${queryToAsk}\nAI: ${CONFIG.fastAnswer}\n`;
                actions.style.visibility = "visible";
                renderSourceCards();
                followupForm.style.display = "flex";
                isStreaming = false;
                return;
            }

            if (skeleton) skeleton.style.display = "flex";

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 60000);

            const endpoint = isFollowup ? "/ai-followup" : "/ai-stream";
            
            const reqBody = {
                q: queryToAsk,
                orig_q: CONFIG.query,
                lang: CONFIG.lang,
                tk: CONFIG.token,
                prev_answer: conversationHistory
            };

            const res = await fetch(CONFIG.scriptRoot + endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(reqBody),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (skeleton) skeleton.style.display = "none";

            if (!res.ok) {
                const errSpan = document.createElement("span");
                errSpan.className = "ai-error";
                errSpan.textContent = `⚠️ Error: ${res.statusText}`;
                answerContainer.appendChild(errSpan);
                return;
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();

            let streamBuffer = "";
            let collectedResponse = "";
            let isThinking = false;
            let thoughtHtml = "";
            let lastRenderTime = 0;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                if (!chunk) continue;

                streamBuffer += chunk;

                // Handle <think> blocks (Qwen/DeepSeek reasoning)
                if (streamBuffer.includes("<think>")) {
                    isThinking = true;
                    streamBuffer = streamBuffer.replace("<think>", "");
                }
                if (streamBuffer.includes("</think>")) {
                    isThinking = false;
                    const parts = streamBuffer.split("</think>");
                    thoughtHtml += parts[0];
                    streamBuffer = parts[1] || "";
                }

                if (isThinking) {
                    thoughtHtml += streamBuffer;
                    streamBuffer = "";
                } else {
                    collectedResponse += streamBuffer;
                    streamBuffer = "";
                }

                // Throttle DOM updates to prevent CPU starvation and scroll jank
                const now = Date.now();
                if (now - lastRenderTime > 50) {
                    lastRenderTime = now;
                    let finalHtml = "";
                    if (thoughtHtml) {
                        finalHtml += `<details class="ai-reasoning"><summary>Thought Process</summary><div class="ai-thought-content">${escapeHtml(thoughtHtml)}</div></details>`;
                    }
                    finalHtml += renderMarkdownAndCitations(collectedResponse);
                    finalHtml += '<span class="ai-cursor"></span>';
                    
                    answerContainer.innerHTML = finalHtml;
                }
            }

            // Final render without cursor
            let finalHtml = "";
            if (thoughtHtml) {
                finalHtml += `<details class="ai-reasoning"><summary>Thought Process</summary><div class="ai-thought-content">${escapeHtml(thoughtHtml)}</div></details>`;
            }
            finalHtml += renderMarkdownAndCitations(collectedResponse);
            answerContainer.innerHTML = finalHtml;

            // Update conversation history
            conversationHistory += `\nUser: ${queryToAsk}\nAI: ${collectedResponse}\n`;

            // Show UI elements
            actions.style.visibility = "visible";
            renderSourceCards();
            followupForm.style.display = "flex";

        } catch (e) {
            console.error("[AI Overview] Stream error:", e);
            if (skeleton) skeleton.style.display = "none";
            const errSpan = document.createElement("span");
            errSpan.className = "ai-error";
            errSpan.textContent = e.name === "AbortError" ? "⚠️ Connection timed out." : "⚠️ An error occurred.";
            answerContainer.appendChild(errSpan);
        } finally {
            isStreaming = false;
        }
    }

    // ── Event Listeners ─────────────────────────────────────────────
    
    // Copy button
    document.getElementById("ai-copy-btn").addEventListener("click", (e) => {
        const text = answerContainer.innerText.replace("Thought Process", "").trim();
        navigator.clipboard.writeText(text).then(() => {
            const btn = e.currentTarget;
            const origHtml = btn.innerHTML;
            btn.innerHTML = '✅ Copied';
            setTimeout(() => btn.innerHTML = origHtml, 2000);
        });
    });

    // Regenerate button
    document.getElementById("ai-regen-btn").addEventListener("click", () => {
        startStream(CONFIG.query, false);
    });

    // Follow-up form
    followupForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const followQuery = followupInput.value.trim();
        if (!followQuery || isStreaming) return;
        
        followupInput.value = "";
        
        // Move current answer to history UI (safe — uses textContent for user query)
        const turnDiv = document.createElement("div");
        turnDiv.className = "ai-chat-turn";

        const queryBubble = document.createElement("div");
        queryBubble.className = "ai-user-query";
        queryBubble.textContent = currentQuery;

        const responseDiv = document.createElement("div");
        responseDiv.className = "ai-bot-response";

        const ansClone = document.createElement("div");
        ansClone.className = "ai-answer";
        ansClone.innerHTML = answerContainer.innerHTML;

        const srcClone = document.createElement("div");
        srcClone.className = "ai-sources-container";
        srcClone.style.borderTop = "none";
        srcClone.style.paddingTop = "0";
        srcClone.innerHTML = sourcesContainer.innerHTML;

        responseDiv.appendChild(ansClone);
        responseDiv.appendChild(srcClone);
        turnDiv.appendChild(queryBubble);
        turnDiv.appendChild(responseDiv);
        chatHistory.appendChild(turnDiv);
        
        // Update current query tracking
        currentQuery = followQuery;
        
        // Start new stream
        startStream(followQuery, true);
    });

    // ── Auto-start ──────────────────────────────────────────────────
    startStream(CONFIG.query, false);
})();
