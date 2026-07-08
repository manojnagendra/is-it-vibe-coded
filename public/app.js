// Client-side Application Logic: Vibe Coding Detector

document.addEventListener("DOMContentLoaded", () => {
    // API Base URL
    const API_BASE = "";

    // DOM Elements
    const urlInput = document.getElementById("url-input");
    const btnScan = document.getElementById("btn-scan");
    const btnManualOpen = document.getElementById("btn-manual-open");
    const scanTerminal = document.getElementById("scan-terminal");
    const terminalBody = document.getElementById("terminal-body");
    const resultDashboard = document.getElementById("result-dashboard");
    
    // Result elements
    const scoreNum = document.getElementById("score-num");
    const progressRingBar = document.getElementById("progress-ring-bar");
    const gradeBadge = document.getElementById("grade-badge");
    const targetTitle = document.getElementById("target-title");
    const targetLink = document.getElementById("target-link");
    const verdictText = document.getElementById("verdict-text");
    
    // Detail elements
    const metricTailwindVal = document.getElementById("metric-tailwind-val");
    const metricTailwindBar = document.getElementById("metric-tailwind-bar");
    const metricLucideVal = document.getElementById("metric-lucide-val");
    const metricLucideBar = document.getElementById("metric-lucide-bar");
    const metricShadcnVal = document.getElementById("metric-shadcn-val");
    const metricFrameworkVal = document.getElementById("metric-framework-val");
    const metricBuilderVal = document.getElementById("metric-builder-val");
    const metricSpeedVal = document.getElementById("metric-speed-val");
    
    // Vote elements
    const voteVibePct = document.getElementById("vote-vibe-pct");
    const voteVibeBar = document.getElementById("vote-vibe-bar");
    const voteHandPct = document.getElementById("vote-hand-pct");
    const voteHandBar = document.getElementById("vote-hand-bar");
    const voteVibeCount = document.getElementById("vote-vibe-count");
    const voteHandCount = document.getElementById("vote-hand-count");
    const btnVoteVibe = document.getElementById("btn-vote-vibe");
    const btnVoteHand = document.getElementById("btn-vote-hand");
    
    // Comments elements
    const commentsList = document.getElementById("comments-list");
    const commentForm = document.getElementById("comment-form");
    const commentAuthor = document.getElementById("comment-author");
    const commentText = document.getElementById("comment-text");
    
    // History elements
    const historyList = document.getElementById("history-list");
    const historySearch = document.getElementById("history-search");
    
    // Modal elements
    const manualModal = document.getElementById("manual-modal");
    const btnManualClose = document.getElementById("btn-manual-close");
    const btnManualCancel = document.getElementById("btn-manual-cancel");
    const manualAuditForm = document.getElementById("manual-audit-form");

    // Application State
    let activeAudit = null;
    let allAudits = [];
    let localVotes = JSON.parse(localStorage.getItem("vibecoded_votes") || "{}");

    // Initialize Page
    loadRegistry();

    // 1. REGISTRY / HISTORY HANDLING
    async function loadRegistry() {
        try {
            const response = await fetch(`${API_BASE}/api/history`);
            if (!response.ok) throw new Error("Failed to fetch history");
            allAudits = await response.ok ? await response.json() : [];
            renderRegistry(allAudits);
        } catch (err) {
            console.error("Error loading registry:", err);
            historyList.innerHTML = `<div class="loader-history" style="color: var(--color-rose)">Offline. Run python server.</div>`;
        }
    }

    function renderRegistry(audits) {
        if (audits.length === 0) {
            historyList.innerHTML = `<div class="loader-history">No audits registered yet.</div>`;
            return;
        }

        historyList.innerHTML = "";
        audits.forEach(audit => {
            const item = document.createElement("div");
            item.className = "history-item";
            item.setAttribute("data-id", audit.id);
            
            // Determine score class color
            let scoreClass = "vibe-mid";
            if (audit.score >= 90) scoreClass = "vibe-high";
            else if (audit.score >= 75) scoreClass = "vibe-mid";
            else if (audit.score >= 40) scoreClass = "vibe-low";
            else scoreClass = "vibe-artisan";

            // Extract display URL / name
            const displayName = audit.name || audit.url.replace(/https?:\/\//, "");

            item.innerHTML = `
                <div class="history-item-left">
                    <h4>${displayName}</h4>
                    <span>${audit.url || "Manual Profile"}</span>
                </div>
                <div class="history-item-right">
                    <span class="mini-score ${scoreClass}">${audit.score}%</span>
                    <span class="mini-indicator ${scoreClass}"></span>
                </div>
            `;
            
            item.addEventListener("click", () => {
                displayAuditResults(audit);
                resultDashboard.scrollIntoView({ behavior: "smooth" });
            });
            
            historyList.appendChild(item);
        });
    }

    // Filter registry search
    historySearch.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        const filtered = allAudits.filter(audit => {
            const nameMatch = (audit.name || "").toLowerCase().includes(query);
            const urlMatch = (audit.url || "").toLowerCase().includes(query);
            const gradeMatch = (audit.grade || "").toLowerCase().includes(query);
            return nameMatch || urlMatch || gradeMatch;
        });
        renderRegistry(filtered);
    });

    // Reset registry button
    const btnClearHistory = document.getElementById("btn-clear-history");
    if (btnClearHistory) {
        btnClearHistory.addEventListener("click", async () => {
            if (confirm("⚠️ Are you sure you want to reset the live audit registry? This will delete all user comments, votes, and scanned profiles, reverting back to the clean baseline seed.")) {
                try {
                    btnClearHistory.textContent = "⌛ Resetting...";
                    btnClearHistory.disabled = true;
                    const res = await fetch(`${API_BASE}/api/clear`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" }
                    });
                    if (res.ok) {
                        const data = await res.json();
                        allAudits = data;
                        historySearch.value = "";
                        renderRegistry(allAudits);
                        if (allAudits.length > 0) {
                            displayAuditResults(allAudits[0]);
                        }
                    } else {
                        alert("Failed to reset registry.");
                    }
                } catch (err) {
                    console.error("Error clearing registry:", err);
                    alert("Error resetting registry.");
                } finally {
                    btnClearHistory.textContent = "⚠️ Reset";
                    btnClearHistory.disabled = false;
                }
            }
        });
    }

    // 2. AUDIT SCANNERS (DEEP SCAN & MANUAL SCAN)
    btnScan.addEventListener("click", () => {
        const input = urlInput.value.trim();
        if (!input) {
            alert("Please enter a URL or Application Name.");
            urlInput.focus();
            return;
        }
        runDeepScan(input);
    });

    urlInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            btnScan.click();
        }
    });

    async function runDeepScan(target) {
        // Clear and show terminal
        scanTerminal.classList.remove("hidden");
        terminalBody.innerHTML = "";
        btnScan.disabled = true;
        resultDashboard.classList.add("hidden");

        const domain = target.replace(/https?:\/\/(www\.)?/, "");

        // Terminal Log animation steps
        const logs = [
            { text: `📡 Initializing vibe-analyzer on: ${target}...`, class: "info", delay: 300 },
            { text: `🔍 Resolving DNS records for: ${domain}...`, class: "info", delay: 500 },
            { text: `🔗 Fetching index file and headers...`, class: "info", delay: 400 },
            { text: `🧠 Parsing HTML DOM components (loaded 345KB)...`, class: "", delay: 600 },
            { text: `🎨 CSS Footprint Audit: Checking for Tailwind CSS declarations...`, class: "", delay: 500 },
            { text: `🧱 Inspecting layout elements for Shadcn UI structures...`, class: "", delay: 400 },
            { text: `✨ Detecting Lucide React and linear icon packs...`, class: "", delay: 500 },
            { text: `📝 Executing NLP copy engine: Scanning for LLM placeholder clichés...`, class: "", delay: 600 },
            { text: `🔮 Running final heuristic weighting & compilation...`, class: "info", delay: 450 }
        ];

        let logIdx = 0;
        
        async function runLogQueue() {
            if (logIdx < logs.length) {
                const log = logs[logIdx];
                appendTerminalLine(log.text, log.class);
                logIdx++;
                setTimeout(runLogQueue, log.delay);
            } else {
                // Done log animations, fetch actual data from backend
                try {
                    appendTerminalLine("🚀 Dispatching audit payload request to python server...", "info");
                    
                    const response = await fetch(`${API_BASE}/api/audit`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ url: target, name: "" })
                    });
                    
                    if (!response.ok) {
                        throw new Error("Audit engine response error.");
                    }
                    
                    const report = await response.json();
                    
                    if (report.warning) {
                        appendTerminalLine(`⚠️ SCRAPE WARNING: ${report.warning}`, "warning");
                    }
                    
                    appendTerminalLine(`✅ Success! Vibe Index compiled: ${report.score}% (${report.grade})`, "success");
                    
                    setTimeout(() => {
                        displayAuditResults(report);
                        btnScan.disabled = false;
                        // Reload history registry
                        loadRegistry();
                    }, 500);

                } catch (err) {
                    appendTerminalLine(`❌ ERROR: Could not complete scrap loop. Details: ${err.message}`, "warning");
                    appendTerminalLine("💡 Suggestion: Start the Python server using 'python3 server.py' or check server terminal output.", "info");
                    btnScan.disabled = false;
                }
            }
        }

        runLogQueue();
    }

    function appendTerminalLine(text, className = "") {
        const line = document.createElement("div");
        line.className = `terminal-line ${className}`;
        line.innerHTML = `<span class="prefix">&gt;</span> <span class="content">${text}</span>`;
        terminalBody.appendChild(line);
        terminalBody.scrollTop = terminalBody.scrollHeight;
    }

    // 3. DISPLAY SCAN RESULTS
    function displayAuditResults(report) {
        activeAudit = report;

        // Populate elements
        scoreNum.innerText = report.score;
        targetTitle.innerText = report.name || "Audited Site";
        
        // Handle URL links
        if (report.url && report.url.startsWith("http")) {
            targetLink.innerText = report.url.replace(/https?:\/\//, "") + " ↗";
            targetLink.href = report.url;
            targetLink.classList.remove("hidden");
        } else {
            targetLink.classList.add("hidden");
        }
        
        verdictText.innerText = report.verdict;

        // Circular progress ring setup
        // R = 70. Perimeter = 439.82
        const r = 70;
        const perimeter = 2 * Math.PI * r;
        const offset = perimeter - (perimeter * report.score / 100);
        progressRingBar.style.strokeDashoffset = offset;

        // Set grade badge and score visual colors
        gradeBadge.className = "badge";
        
        let strokeColor = "url(#gradient-vibe)";
        
        if (report.score >= 90) {
            gradeBadge.classList.add("badge-vibe-high");
            gradeBadge.innerText = report.grade;
        } else if (report.score >= 75) {
            gradeBadge.classList.add("badge-vibe-mid");
            gradeBadge.innerText = report.grade;
        } else if (report.score >= 40) {
            gradeBadge.classList.add("badge-vibe-low");
            gradeBadge.innerText = report.grade;
        } else {
            gradeBadge.classList.add("badge-vibe-artisan");
            gradeBadge.innerText = report.grade;
        }

        // Metrics Breakdown
        const analysis = report.analysis || {};
        
        metricTailwindVal.innerText = `${analysis.tailwind_density || 0}%`;
        metricTailwindBar.style.width = `${analysis.tailwind_density || 0}%`;
        
        metricLucideVal.innerText = `${analysis.lucide_density || 0}%`;
        metricLucideBar.style.width = `${analysis.lucide_density || 0}%`;
        
        metricShadcnVal.innerText = analysis.radix_shadcn_presence ? "DETECTED" : "NONE DETECTED";
        metricShadcnVal.className = analysis.radix_shadcn_presence ? "metric-value font-accent" : "metric-value font-accent";
        metricShadcnVal.style.color = analysis.radix_shadcn_presence ? "var(--color-pink)" : "var(--text-muted)";
        
        metricFrameworkVal.innerText = analysis.framework || "Unknown";
        metricBuilderVal.innerText = analysis.builder_sig || "None";
        metricSpeedVal.innerText = analysis.speed_indicator || "Standard Speed";

        // Voting bars render
        updateVoteBars(report);

        // Render Comments List
        renderComments(report.comments || []);

        // Show Dashboard
        resultDashboard.classList.remove("hidden");
    }

    // 4. VOTING ENGINE
    async function castVote(voteType) {
        if (!activeAudit) return;
        
        // Optimistic UI updates - save locally first
        localVotes[activeAudit.id] = voteType;
        localStorage.setItem("vibecoded_votes", JSON.stringify(localVotes));
        
        // Instant screen update
        updateVoteBars(activeAudit);
        
        try {
            const response = await fetch(`${API_BASE}/api/vote`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: activeAudit.id, vote: voteType })
            });

            if (!response.ok) throw new Error("Vote failed");
            
            const updatedReport = await response.json();
            activeAudit = updatedReport;
            updateVoteBars(updatedReport);
            
            // Reload history to refresh values
            loadRegistry();
        } catch (err) {
            console.error("Error voting:", err);
            // Non-blocking catch: UI is already updated locally.
        }
    }

    function updateVoteBars(report) {
        let votesVibe = report.votes_vibe || 0;
        let votesHand = report.votes_hand || 0;
        
        // Inject local vote to count if server cache is empty/unsynced
        const myVote = localVotes[report.id];
        if (myVote === "vibe" && votesVibe === 0) votesVibe = 1;
        if (myVote === "hand" && votesHand === 0) votesHand = 1;
        
        const total = votesVibe + votesHand;
        
        let vibePct = 50;
        let handPct = 50;

        if (total > 0) {
            vibePct = Math.round((votesVibe / total) * 100);
            handPct = 100 - vibePct;
        }

        voteVibePct.innerText = `${vibePct}%`;
        voteVibeBar.style.width = `${vibePct}%`;
        
        voteHandPct.innerText = `${handPct}%`;
        voteHandBar.style.width = `${handPct}%`;

        // Toggle buttons state
        btnVoteVibe.classList.remove("voted");
        btnVoteHand.classList.remove("voted");
        btnVoteVibe.disabled = false;
        btnVoteHand.disabled = false;

        if (myVote === "vibe") {
            btnVoteVibe.classList.add("voted");
            btnVoteVibe.disabled = true;
            btnVoteHand.disabled = true;
            btnVoteVibe.innerHTML = `🔥 Vibe Coded (Voted: +<span id="vote-vibe-count">${votesVibe}</span>)`;
            btnVoteHand.innerHTML = `🛠️ Hand Crafted (+<span id="vote-hand-count">${votesHand}</span>)`;
        } else if (myVote === "hand") {
            btnVoteHand.classList.add("voted");
            btnVoteVibe.disabled = true;
            btnVoteHand.disabled = true;
            btnVoteVibe.innerHTML = `🔥 Vibe Coded (+<span id="vote-vibe-count">${votesVibe}</span>)`;
            btnVoteHand.innerHTML = `🛠️ Hand Crafted (Voted: +<span id="vote-hand-count">${votesHand}</span>)`;
        } else {
            btnVoteVibe.innerHTML = `🔥 Vibe Coded (+<span id="vote-vibe-count">${votesVibe}</span>)`;
            btnVoteHand.innerHTML = `🛠️ Hand Crafted (+<span id="vote-hand-count">${votesHand}</span>)`;
        }
    }

    btnVoteVibe.addEventListener("click", () => castVote("vibe"));
    btnVoteHand.addEventListener("click", () => castVote("hand"));

    // 5. COMMENTS ENGINE
    function renderComments(comments) {
        if (comments.length === 0) {
            commentsList.innerHTML = `<div class="loader-history" style="padding: 10px 0;">No developer notes posted yet. Add yours below!</div>`;
            return;
        }

        commentsList.innerHTML = "";
        comments.forEach(comment => {
            const dateObj = new Date(comment.date);
            const dateStr = dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute:'2-digit' });
            
            const item = document.createElement("div");
            item.className = "comment-item";
            item.innerHTML = `
                <div class="comment-meta">
                    <span class="author">@${comment.author}</span>
                    <span class="date">${dateStr}</span>
                </div>
                <div class="comment-text">${escapeHTML(comment.text)}</div>
            `;
            commentsList.appendChild(item);
        });
        
        commentsList.scrollTop = commentsList.scrollHeight;
    }

    commentForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!activeAudit) return;

        const author = commentAuthor.value.trim();
        const text = commentText.value.trim();

        if (!text) return;

        try {
            const response = await fetch(`${API_BASE}/api/comment`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: activeAudit.id, author, text })
            });

            if (!response.ok) throw new Error("Comment post failed");
            
            const updatedReport = await response.json();
            activeAudit = updatedReport;
            renderComments(updatedReport.comments || []);
            
            commentText.value = ""; // clear message
            loadRegistry();
        } catch (err) {
            console.error("Error adding note:", err);
            alert("Failed to submit note. Is python server active?");
        }
    });

    // 6. MANUAL AUDIT WIZARD MODAL
    btnManualOpen.addEventListener("click", () => {
        manualModal.classList.remove("hidden");
        document.body.style.overflow = "hidden"; // disable scrolling
    });

    function closeManualModal() {
        manualModal.classList.add("hidden");
        document.body.style.overflow = ""; // enable scrolling
        manualAuditForm.reset();
    }

    btnManualClose.addEventListener("click", closeManualModal);
    btnManualCancel.addEventListener("click", closeManualModal);
    
    // Close modal clicking overlay
    manualModal.addEventListener("click", (e) => {
        if (e.target === manualModal) {
            closeManualModal();
        }
    });

    manualAuditForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const manualName = document.getElementById("manual-name").value.trim();
        const isTailwind = document.querySelector('input[name="tailwind"]:checked').value === "yes";
        const isLucide = document.getElementById("check-lucide").checked;
        const isShadcn = document.getElementById("check-shadcn").checked;
        const isCliche = document.getElementById("check-cliche").checked;
        const isBroken = document.getElementById("check-broken").checked;
        const isNoAnalytics = document.getElementById("check-no-analytics").checked;
        const speed = document.querySelector('select[name="speed"]').value;

        const answers = {
            tailwind: isTailwind,
            lucide: isLucide,
            shadcn: isShadcn,
            cliche: isCliche,
            broken_links: isBroken,
            no_analytics: isNoAnalytics,
            speed: speed
        };

        // Trigger manual audit compilation
        try {
            // Close modal
            closeManualModal();
            
            // Show terminal scan log mock
            scanTerminal.classList.remove("hidden");
            terminalBody.innerHTML = "";
            btnScan.disabled = true;
            resultDashboard.classList.add("hidden");

            appendTerminalLine("📋 Initializing Manual Audit Diagnostics Questionnaire...", "info");
            setTimeout(() => appendTerminalLine(`📝 Mapping answers for profile: "${manualName}"`, ""), 400);
            setTimeout(() => appendTerminalLine(`🎨 Input Styling Flag: ${isTailwind ? 'Tailwind Framework' : 'Bespoke Separate CSS'}`, ""), 800);
            setTimeout(() => appendTerminalLine(`🧱 Structuring Component Blueprint Weighting...`, ""), 1200);
            setTimeout(() => appendTerminalLine(`⏳ Speed parameters registered: ${speed}`, "info"), 1600);
            
            setTimeout(async () => {
                try {
                    const response = await fetch(`${API_BASE}/api/audit`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            url: "",
                            name: manualName,
                            manual: true,
                            answers: answers
                        })
                    });

                    if (!response.ok) throw new Error("Manual compile failed");
                    
                    const report = await response.json();
                    
                    appendTerminalLine("✅ Compiled manual vibe metrics profile!", "success");
                    
                    setTimeout(() => {
                        displayAuditResults(report);
                        btnScan.disabled = false;
                        loadRegistry();
                    }, 500);

                } catch (err) {
                    appendTerminalLine(`❌ ERROR: Could not compile manual metrics. ${err.message}`, "warning");
                    btnScan.disabled = false;
                }
            }, 2000);

        } catch (err) {
            console.error("Error running manual audit:", err);
            btnScan.disabled = false;
        }
    });

    // Helper: Escape script tags in comments
    function escapeHTML(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
