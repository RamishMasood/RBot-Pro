// RBot Pro Multi-Exchange Analysis UI - JavaScript Client

// Explicit WebSocket connection with proper configuration
const socket = io(window.location.origin, {
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 10,
    transports: ['websocket', 'polling']
});

let lineCount = 0;
let startTime = null;
let timerInterval = null;
let isRunning = false;
let signalsCount = 0;

// ===== WebSocket Event Handlers =====

socket.on('connect', () => {
    console.log('✓ Connected to server');
    updateStatus('Connected', 'connected');
    addTerminalLine('✓ Connected to RBot Pro server', 'success');
});

socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
    updateStatus('Connection Error', 'error');
    addTerminalLine(`✗ Connection error: ${error}`, 'error');
});

socket.on('disconnect', () => {
    console.log('✗ Disconnected from server');
    updateStatus('Disconnected', 'error');
    addTerminalLine('✗ Disconnected from server', 'error');
});

socket.on('output', (data) => {
    if (data.data) {
        const lines = data.data.split('\n');
        lines.forEach(line => {
            if (line.trim()) {
                addTerminalLine(line);
            }
        });
    }
});

socket.on('status', (data) => {
    if (data.status === 'started') {
        isRunning = true;
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;
        updateStatus('Running', 'running');
        startTimer();
    } else if (data.status === 'completed') {
        isRunning = false;
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        updateStatus('Complete', 'connected');
        stopTimer();
        addTerminalLine('✓ Analysis completed', 'success');
    } else if (data.status === 'stopped') {
        isRunning = false;
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        updateStatus('Stopped', 'error');
        stopTimer();
        addTerminalLine('⏹ Analysis stopped', 'warning');
    } else if (data.status === 'error') {
        isRunning = false;
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        updateStatus('Error', 'error');
        stopTimer();
    }
});

socket.on('clear', () => {
    document.getElementById('terminal').innerHTML = '';
    document.getElementById('signalsBox').innerHTML = '<div class="terminal-line" id="noSignalsMsg"><span class="line-prefix">#</span><span class="line-text" style="color: #666;">Signals found during the current run will appear here...</span></div>';
    lineCount = 0;
    signalsCount = 0;
    document.getElementById('signalsCount').innerText = '0 Found';
    updateLineCount();
});

socket.on('config_updated', (config) => {
    console.log('Config updated:', config);
});

socket.on('trade_signal', (trade) => {
    console.log('💸 SIGNAL FOUND:', trade);
    addTradeSignal(trade);
});

socket.on('market_status', (data) => {
    updateMarketStatus(data);
});

// ===== Terminal Functions =====

function addTerminalLine(text, type = 'normal') {
    const terminal = document.getElementById('terminal');
    const line = document.createElement('div');
    const classes = ['terminal-line'];

    // Detect line type by content
    if (!type || type === 'normal') {
        if (text.includes('ERROR') || text.includes('Error') || text.includes('❌')) type = 'error';
        else if (text.includes('TRADE FOUND') || text.includes('✓') || text.includes('✅')) type = 'success';
        else if (text.includes('⚠') || text.includes('warning')) type = 'warning';
        else if (text.includes('===') && (text.includes('TRADE') || text.includes('HIGH'))) type = 'trade';
    }

    if (type) classes.push(type);
    line.className = classes.join(' ');

    const prefix = document.createElement('span');
    prefix.className = 'line-prefix';
    prefix.textContent = '$';

    const textSpan = document.createElement('span');
    textSpan.className = 'line-text';
    textSpan.textContent = text;

    line.appendChild(prefix);
    line.appendChild(textSpan);
    terminal.appendChild(line);

    lineCount++;
    updateLineCount();
    terminal.scrollTop = terminal.scrollHeight;
}

function addTradeSignal(trade) {
    const signalsBox = document.getElementById('signalsBox');
    const noMsg = document.getElementById('noSignalsMsg');
    if (noMsg) noMsg.style.display = 'none';

    // Normalize symbol (e.g., remove underscores from MEXC symbols like BTC_USDT)
    const cleanSymbol = trade.symbol.replace(/_/g, '').toUpperCase();

    // Generate a unique ID for the 'Master Signal' (Symbol + Direction)
    // This ensures that multiple strategies firing on the same coin deduplicate visually in real-time.
    const signalId = `signal-${cleanSymbol}-${trade.type}`.replace(/[^a-zA-Z0-9-]/g, '');
    let card = document.getElementById(signalId);
    let isUpdate = !!card;

    if (!isUpdate) {
        card = document.createElement('div');
        card.id = signalId;
        card.dataset.agreeingStrategies = JSON.stringify([trade.strategy]);
        signalsCount++;
        document.getElementById('signalsCount').innerText = `${signalsCount} Found`;
    } else {
        // Build agreement list incrementally during live scan
        let existing = JSON.parse(card.dataset.agreeingStrategies || '[]');

        // Strategy label with timeframe for better detail
        const currentStratLabel = `${trade.strategy} (${trade.timeframe || '?'})`;

        // If the backend sends a full list (post-processing), use it. Otherwise append.
        if (trade.agreeing_strategies && trade.agreeing_strategies.length > 0) {
            existing = trade.agreeing_strategies;
        } else if (!existing.includes(currentStratLabel) && !existing.includes(trade.strategy)) {
            // Check if we already have it in either simple or TF-enriched form
            existing.push(currentStratLabel);
        }
        card.dataset.agreeingStrategies = JSON.stringify(existing);
    }

    // Get final agreement list for this render
    const agreeingStrategies = JSON.parse(card.dataset.agreeingStrategies);
    const agreementCount = trade.agreement_count || agreeingStrategies.length;

    card.className = `trade-card ${trade.type.toLowerCase()}`;

    // Simplified color mapping for UI
    const typeColor = trade.type === 'LONG' ? '#00ff88' : '#ff4444';
    const exchangeName = trade.exchange || 'N/A';

    // Exchange badge color mapping
    const exchangeColors = {
        'MEXC': '#00b897',
        'Binance': '#f0b90b',
        'Bitget': '#00f0ff',
        'Bybit': '#f7931a',
        'OKX': '#ffffff',
        'KuCoin': '#23af91',
        'GateIO': '#2354e6',
        'HTX': '#2b71d6'
    };
    const exchangeColor = exchangeColors[exchangeName] || '#888';

    // Store trade data as a data attribute so the copy button can access it
    const tradeDataEncoded = encodeURIComponent(JSON.stringify(trade));

    // Signal quality badge colors
    const qualityStyles = {
        'ELITE': { bg: '#ffd70022', color: '#ffd700', border: '#ffd70055', icon: '🏆', label: 'ELITE' },
        'STRONG': { bg: '#00ff8822', color: '#00ff88', border: '#00ff8855', icon: '💪', label: 'STRONG' },
        'STANDARD': { bg: '#00d4ff22', color: '#00d4ff', border: '#00d4ff55', icon: '📊', label: 'STANDARD' }
    };
    const quality = qualityStyles[trade.signal_quality] || qualityStyles['STANDARD'];

    // Agreement badge (Now an interactive button)
    const agreementHtml = agreementCount > 1
        ? `<button onclick="event.stopPropagation(); showAgreementDetails('${signalId}')" style="background: #00ff8822; color: #00ff88; border: 1px solid #00ff8855; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; margin-left: 6px; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.background='#00ff8833'" onmouseout="this.style.background='#00ff8822'">✅ ${agreementCount} agree</button>`
        : '';

    // Conflict warning
    const conflictHtml = trade.conflict_warning
        ? `<div style="background: #ff444422; border: 1px solid #ff444455; border-radius: 6px; padding: 6px 10px; margin-top: 8px; font-size: 0.8em; color: #ff8888;">${trade.conflict_warning}</div>`
        : '';

    // Confidence boost info
    const boostHtml = (trade.original_confidence && trade.original_confidence !== trade.confidence_score)
        ? `<span style="color: #00ff88; font-size: 0.75em; margin-left: 5px;">↑ ${trade.original_confidence}→${trade.confidence_score}</span>`
        : '';

    card.innerHTML = `
        <div class="trade-header">
            <span class="exchange-badge" style="background: ${exchangeColor}22; color: ${exchangeColor}; border: 1px solid ${exchangeColor}55;">${exchangeName}</span>
            <span style="background: ${quality.bg}; color: ${quality.color}; border: 1px solid ${quality.border}; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold;">${quality.icon} ${quality.label}</span>
            <span style="font-weight: bold; color: #aaa;">[${trade.strategy}]</span>
            <span style="color: #666; font-size: 0.85em; font-weight: normal; margin-left: 5px;">(${trade.timeframe})</span>
            <span style="font-weight: bold; color: #fff; margin-left: 8px;">${trade.symbol}</span>
            <span style="font-weight: bold; color: ${typeColor}; margin-left: 8px;">${trade.type}</span>${agreementHtml}
            <span style="color: #666; font-size: 0.8em; margin-left: auto; margin-right: 15px;">🕒 ${trade.timestamp || 'Just now'}</span>
            <span style="color: #00d4ff; font-size: 0.9em; margin-right: 10px;">${trade.confidence_score}/10${boostHtml}</span>
            <button class="copy-btn" data-trade="${tradeDataEncoded}" onclick="copyTradeFromBtn(this)" title="Copy Signal">
                📋
            </button>
        </div>
        <div class="trade-body">
            <div>
                <span class="trade-label">Price (${trade.entry_type})</span>
                <span class="trade-val">$${trade.entry.toFixed(6)}</span>
            </div>
            <div>
                <span class="trade-label">Stop Loss</span>
                <span class="trade-val" style="color:#ff8888;">$${trade.sl.toFixed(6)}</span>
            </div>
            <div>
                <span class="trade-label">Target</span>
                <span class="trade-val" style="color:#00ff88;">$${trade.tp1.toFixed(6)}</span>
            </div>
            <div class="trade-details">
                <div style="display: flex; gap: 20px; font-size: 0.85em; margin-bottom: 8px;">
                    <span>R/R: <b style="color:#fff;">${trade.risk_reward}:1</b></span>
                    <span>Expected: <b style="color:#fff;">${trade.expected_time}</b></span>
                    <span>Exchange: <b style="color:${exchangeColor};">${exchangeName}</b></span>
                </div>
                <div style="font-size: 0.85em; color: #bbb;">
                    <b style="color: #888;">REASON:</b> ${trade.reason}
                </div>
                <div style="font-size: 0.85em; color: #999; margin-top: 5px; font-style: italic;">
                    ${trade.indicators}
                </div>${conflictHtml}
                <button class="view-analysis-btn" data-trade="${tradeDataEncoded}" onclick="openAnalysisChart(this)">
                    🔍 View Analysis Chart
                </button>
            </div>
        </div>
    `;

    if (!isUpdate) {
        signalsBox.prepend(card);
        // Play alert sound only for NEW signals to avoid spam on updates
        playAlertSound('trade');
    }
}

// Global Sound Controller
let audioCtx = null;
function playAlertSound(type = 'trade') {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    if (type === 'trade') {
        osc.frequency.setValueAtTime(660, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(880, audioCtx.currentTime + 0.1);
        gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.4);
        osc.start(); osc.stop(audioCtx.currentTime + 0.4);
    }
}

function copyTradeFromBtn(btn) {
    try {
        const trade = JSON.parse(decodeURIComponent(btn.getAttribute('data-trade')));
        const action = trade.type === 'LONG' ? '🚀 BUY' : '🔻 SELL';
        const exchangeName = trade.exchange || 'N/A';

        // Helper to format numbers safely
        const f = (val) => {
            const n = parseFloat(val);
            return isNaN(n) ? '0.000000' : n.toFixed(6);
        };

        const text = `🔥 * [${trade.strategy}] TRADE ALERT *
━━━━━━━━━━━━━━━━━━━━
🏢 * Exchange:* ${exchangeName}
 * Signal:* ${action} ${trade.symbol} (${trade.timeframe})
📍 * Entry:* $${f(trade.entry)} (${trade.entry_type})
🛑 * SL:* $${f(trade.sl)}
🎯 * TP:* $${f(trade.tp1)}
💎 * R / R:* ${trade.risk_reward}: 1
⏱ * Expected:* ${trade.expected_time}
🔍 * Reason:* ${trade.reason}
━━━━━━━━━━━━━━━━━━━━
* RBot Pro 🤖 — World's Most Accurate AI Analysis Bot!* 🏆
    * Supported: MEXC • Binance • Bitget • Bybit • OKX • KuCoin • Gate.io • HTX * `;

        navigator.clipboard.writeText(text).then(() => {
            const originalText = btn.innerText;
            btn.innerText = '✅';
            btn.style.color = '#00ff88';
            setTimeout(() => {
                btn.innerText = '📋';
                btn.style.color = '';
            }, 2000);
        }).catch(err => {
            console.warn('Clipboard API failed, trying fallback...', err);
            // Fallback: use a temporary textarea for copying
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                btn.innerText = '✅';
                btn.style.color = '#00ff88';
            } catch (e) {
                console.error('Fallback copy failed:', e);
                alert('Copy failed. Please copy manually from the terminal.');
            }
            document.body.removeChild(textarea);
            setTimeout(() => {
                btn.innerText = '📋';
                btn.style.color = '';
            }, 2000);
        });
    } catch (e) {
        console.error('Failed to copy trade:', e);
        alert('Failed to copy trade signal: ' + e.message);
    }
}

// ===== Control Functions =====

function getSelectedExchanges() {
    return Array.from(document.querySelectorAll('#exchangeList input[type="checkbox"]:checked'))
        .map(cb => cb.value);
}

function selectAllExchanges() {
    document.querySelectorAll('#exchangeList input[type="checkbox"]').forEach(cb => cb.checked = true);
    updateExchangeCount();
}

function deselectAllExchanges() {
    document.querySelectorAll('#exchangeList input[type="checkbox"]').forEach(cb => cb.checked = false);
    updateExchangeCount();
}

function updateExchangeCount() {
    const count = getSelectedExchanges().length;
    const countEl = document.getElementById('selectedExchangesCount');
    const displayEl = document.getElementById('selectedExchangesDisplay');
    if (countEl) countEl.textContent = count;
    if (displayEl) displayEl.textContent = count;

    // Also save to server config
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exchanges: getSelectedExchanges() })
    });
}

function startAnalysis() {
    const exchanges = getSelectedExchanges();
    const symbols = getSelectedSymbols();
    const indicators = getSelectedIndicators();
    const timeframes = getSelectedTimeframes();
    const confidence = parseInt(document.getElementById('confidenceSlider').value);

    if (exchanges.length === 0) {
        alert('Please select at least one exchange');
        return;
    }

    if (symbols.length === 0) {
        alert('Please select at least one cryptocurrency');
        return;
    }

    if (indicators.length === 0) {
        alert('Please select at least one indicator');
        return;
    }

    if (timeframes.length === 0) {
        alert('Please select at least one timeframe');
        return;
    }

    addTerminalLine(`🚀 Starting analysis on ${exchanges.join(', ')} with ${symbols.length} coins, ${indicators.length} indicators, and ${timeframes.length} timeframes`, 'success');

    // Clear previous signals for new run
    document.getElementById('signalsCount').innerText = '0 Found';
    signalsCount = 0;
    const signalsBox = document.getElementById('signalsBox');
    signalsBox.innerHTML = '<div class="terminal-line" id="noSignalsMsg"><span class="line-prefix">#</span><span class="line-text" style="color: #666;">Signals found during the current run will appear here...</span></div>';

    // Save exchanges to config first
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exchanges: exchanges })
    });

    socket.emit('start_analysis', {
        symbols: symbols,
        indicators: indicators,
        timeframes: timeframes,
        min_confidence: confidence,
        exchanges: exchanges
    });
}

function stopAnalysis() {
    socket.emit('stop_analysis');
    addTerminalLine('⏹ Stop requested — terminating all processes...', 'warning');
    // Immediately update UI state so user sees feedback
    isRunning = false;
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
    updateStatus('Stopping...', 'error');
    stopTimer();
}

function clearTerminal() {
    socket.emit('clear_output');
}

function updateStatus(text, status) {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');

    indicator.className = 'status-indicator';
    indicator.classList.add(status);
    statusText.textContent = text;

    const infoSpan = document.querySelector('.terminal-info');
    if (infoSpan) infoSpan.textContent = text;
}

function updateLineCount() {
    document.getElementById('lineCount').textContent = lineCount;
}

// ===== Configuration Functions =====

function getSelectedSymbols() {
    return Array.from(document.querySelectorAll('#symbolList input[type="checkbox"]:checked'))
        .map(cb => cb.value);
}

function getSelectedIndicators() {
    return Array.from(document.querySelectorAll('#indicatorList input:checked'))
        .map(cb => cb.value);
}

function selectAllSymbols() {
    // Only select/deselect visible (non-hidden) symbols
    document.querySelectorAll('#symbolList label').forEach(label => {
        if (label.style.display !== 'none') {
            label.querySelector('input[type="checkbox"]').checked = true;
        }
    });
    updateSymbolCount();
}

function deselectAllSymbols() {
    document.querySelectorAll('#symbolList input[type="checkbox"]').forEach(cb => cb.checked = false);
    updateSymbolCount();
}

function searchSymbols(query) {
    const q = query.toUpperCase().trim();
    document.querySelectorAll('#symbolList label').forEach(label => {
        const cb = label.querySelector('input[type="checkbox"]');
        if (!cb) return;
        const val = cb.value.toUpperCase();
        const text = label.textContent.toUpperCase();
        label.style.display = (q === '' || val.includes(q) || text.includes(q)) ? '' : 'none';
    });
}

function addCustomCoin() {
    const input = document.getElementById('addCoinInput');
    let coinName = input.value.trim().toUpperCase();
    if (!coinName) {
        alert('Please enter a coin name (e.g. NMRUSDT)');
        return;
    }
    // Auto-append USDT if not present
    if (!coinName.endsWith('USDT')) {
        coinName += 'USDT';
    }
    // Check if already exists
    const existing = document.querySelector(`#symbolList input[value = "${coinName}"]`);
    if (existing) {
        existing.checked = true;
        addTerminalLine(`✓ ${coinName} already exists and has been selected`, 'success');
        input.value = '';
        updateSymbolCount();
        return;
    }
    // Add the new coin to the list
    const symbolList = document.getElementById('symbolList');
    const label = document.createElement('label');
    label.style.animation = 'fadeIn 0.3s ease';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = coinName;
    checkbox.checked = true;
    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(coinName));
    symbolList.appendChild(label);
    input.value = '';
    updateSymbolCount();
    addTerminalLine(`✓ ${coinName} added and ready for analysis`, 'success');
}

function selectAllIndicators() {
    document.querySelectorAll('#indicatorList input').forEach(cb => cb.checked = true);
    updateIndicatorCount();
}

function deselectAllIndicators() {
    document.querySelectorAll('#indicatorList input').forEach(cb => cb.checked = false);
    updateIndicatorCount();
}

function updateSymbolCount() {
    const count = getSelectedSymbols().length;
    document.getElementById('selectedCoinsCount').textContent = count;
    // Also save to server config
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: getSelectedSymbols() })
    });
}

function updateIndicatorCount() {
    const count = getSelectedIndicators().length;
    document.getElementById('selectedIndicatorsCount').textContent = count;
    // Also save to server config
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ indicators: getSelectedIndicators() })
    });
}

function getSelectedTimeframes() {
    return Array.from(document.querySelectorAll('#timeframeList input:checked'))
        .map(cb => cb.value);
}

function selectAllTimeframes() {
    document.querySelectorAll('#timeframeList input').forEach(cb => cb.checked = true);
    updateTimeframeCount();
}

function deselectAllTimeframes() {
    document.querySelectorAll('#timeframeList input').forEach(cb => cb.checked = false);
    updateTimeframeCount();
}

function updateTimeframeCount() {
    const count = getSelectedTimeframes().length;
    // Also save to server config
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timeframes: getSelectedTimeframes() })
    });
}

function loadAvailableCoins() {
    addTerminalLine('📡 Loading top 100 coins from EACH selected exchange...', 'info');
    fetch('/api/available-coins')
        .then(r => r.json())
        .then(data => {
            const symbolList = document.getElementById('symbolList');
            symbolList.innerHTML = '';
            data.coins.forEach(coin => {
                const label = document.createElement('label');
                const input = document.createElement('input');
                input.type = 'checkbox';
                input.value = coin;
                input.checked = true;
                label.appendChild(input);
                label.appendChild(document.createTextNode(coin));
                symbolList.appendChild(label);
            });
            updateSymbolCount();
            addTerminalLine(`✓ Loaded ${data.coins.length} unique coins from all selected exchanges`, 'success');
        })
        .catch(err => addTerminalLine(`✗ Failed to load coins: ${err} `, 'error'));
}

function updateConfidence(value) {
    document.getElementById('confidenceValue').textContent = value;
    // Also save to server config for auto-run consistency
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ min_confidence: parseInt(value) })
    });
}

function toggleAutoRun() {
    const enabled = document.getElementById('autoRunToggle').checked;
    document.getElementById('autoRunOptions').style.display = enabled ? 'block' : 'none';

    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            auto_run: enabled,
            symbols: getSelectedSymbols(),
            indicators: getSelectedIndicators(),
            timeframes: getSelectedTimeframes(),
            exchanges: getSelectedExchanges(),
            min_confidence: parseInt(document.getElementById('confidenceSlider').value)
        })
    });

    if (enabled) {
        addTerminalLine('🤖 Auto-run enabled', 'warning');
    } else {
        addTerminalLine('🤖 Auto-run disabled', 'warning');
    }
}

function updateAutoRunInterval() {
    const interval = parseInt(document.getElementById('autoRunInterval').value);
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_run_interval: interval })
    });
    addTerminalLine(`✓ Auto - run interval set to ${interval} seconds`, 'success');
}

// ===== Timer Functions =====

function startTimer() {
    startTime = Date.now();
    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const hours = Math.floor(elapsed / 3600);
        const minutes = Math.floor((elapsed % 3600) / 60);
        const seconds = elapsed % 60;

        const timeString =
            String(hours).padStart(2, '0') + ':' +
            String(minutes).padStart(2, '0') + ':' +
            String(seconds).padStart(2, '0');

        document.getElementById('elapsedTime').textContent = timeString;
    }, 1000);
}

function stopTimer() {
    if (timerInterval) clearInterval(timerInterval);
}

// ===== Event Listeners =====

// Risk Profile Sync
function updateRiskProfile() {
    const profile = document.getElementById('riskProfile').value;
    const minConf = profile === 'conservative' ? 9 : (profile === 'moderate' ? 7 : 5);

    // Sync slider too for visual consistency
    document.getElementById('confidenceSlider').value = minConf;
    document.getElementById('confidenceVal').innerText = `${minConf}/10`;

    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ risk_profile: profile, min_confidence: minConf })
    });
}

// Telegram Config Sync
function updateTelegramConfig() {
    const token = document.getElementById('tgToken').value;
    const chatId = document.getElementById('tgChatId').value;

    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telegram_token: token, telegram_chat_id: chatId })
    });
}

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
    // Update counts on checkbox changes
    document.addEventListener('change', (e) => {
        if (e.target.closest('#symbolList')) updateSymbolCount();
        if (e.target.closest('#indicatorList')) updateIndicatorCount();
        if (e.target.closest('#exchangeList')) updateExchangeCount();
        if (e.target.closest('#timeframeList')) updateTimeframeCount();
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter' && !isRunning) startAnalysis();
        if (e.ctrlKey && e.key === 'l') {
            e.preventDefault();
            clearTerminal();
        }
    });

    // Initial setup
    updateSymbolCount();
    updateIndicatorCount();
    updateExchangeCount();
    addTerminalLine('RBot Pro ready. Select exchanges and click START ANALYSIS or press Ctrl+Enter', 'success');
    addTerminalLine('Use Ctrl+L to clear output', 'info');
});

// ===== Analysis Chart Functions =====

let activeChart = null;

function closeAnalysisModal() {
    document.getElementById('analysisModal').style.display = 'none';
    if (activeChart) {
        activeChart.remove();
        activeChart = null;
    }
}

async function openAnalysisChart(btn) {
    let trade;
    try {
        trade = JSON.parse(decodeURIComponent(btn.getAttribute('data-trade')));
    } catch (e) {
        console.error("Failed to parse trade data:", e);
        return;
    }

    const modal = document.getElementById('analysisModal');
    const overlay = document.getElementById('chartOverlay');
    const chartContainer = document.getElementById('chartContainer');

    // Setup Modal Initial State
    modal.style.display = 'block';
    overlay.style.display = 'flex';
    document.getElementById('modalTitle').innerText = `📊 ${trade.symbol} Analysis - ${trade.exchange}`;
    document.getElementById('modalSubtitle').innerText = `${trade.strategy} | TF: ${trade.timeframe} | ${trade.type}`;
    document.getElementById('modalReason').innerText = trade.reason || "";
    chartContainer.innerHTML = '';
    document.getElementById('modalTradeKey').innerHTML = '';

    const modalCopyBtn = document.getElementById('modalCopyBtn');
    modalCopyBtn.onclick = () => copyTradeFromBtn(btn);

    try {
        // Fetch historical candles
        const candles = await fetchCandles(trade.exchange, trade.symbol, trade.timeframe);
        if (!candles || candles.length === 0) throw new Error("No pricing data found for " + trade.symbol);

        overlay.style.display = 'none';

        // Initialize Chart
        if (typeof LightweightCharts === 'undefined') {
            throw new Error("TradingView Library not found");
        }

        const chart = LightweightCharts.createChart(chartContainer, {
            layout: {
                background: { color: '#0a0a0a' },
                textColor: '#d1d4dc',
            },
            grid: {
                vertLines: { color: '#111' },
                horzLines: { color: '#111' },
            },
            rightPriceScale: {
                borderColor: '#333',
                visible: true,
                autoScale: true,
            },
            timeScale: {
                borderColor: '#333',
                timeVisible: true,
            },
        });
        activeChart = chart;

        // Create Series
        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#00ff88',
            downColor: '#ff4444',
            borderVisible: false,
            wickUpColor: '#00ff88',
            wickDownColor: '#ff4444',
        });

        candlestickSeries.setData(candles);

        // Lines Colors
        const entryColor = '#f0b90b';
        const slColor = '#ff4444';
        const tpColor = '#00ff88';

        // Add Price Lines
        candlestickSeries.createPriceLine({
            price: trade.entry,
            color: entryColor,
            lineWidth: 2,
            lineStyle: 0,
            axisLabelVisible: true,
            title: 'ENTRY',
        });

        candlestickSeries.createPriceLine({
            price: trade.sl,
            color: slColor,
            lineWidth: 2,
            lineStyle: 1,
            axisLabelVisible: true,
            title: 'STOP LOSS',
        });

        candlestickSeries.createPriceLine({
            price: trade.tp1,
            color: tpColor,
            lineWidth: 2,
            lineStyle: 1,
            axisLabelVisible: true,
            title: 'TARGET 1',
        });


        // Add Key items
        addModalKey(`${trade.type} Signal`, trade.type === 'LONG' ? tpColor : slColor);
        addModalKey(`R/R ${trade.risk_reward}:1`, '#00d4ff');
        addModalKey(`Conf: ${trade.confidence_score}/10`, '#fff');

        // Handle Resize - Critical for proper rendering
        const resizeChart = () => {
            const w = chartContainer.clientWidth;
            const h = chartContainer.clientHeight;
            if (w && h && chart) chart.resize(w, h);
        };

        window.addEventListener('resize', resizeChart);

        // Initial resize & fit 
        setTimeout(() => {
            resizeChart();
            if (chart) chart.timeScale().fitContent();
        }, 150);

    } catch (err) {
        console.error('Chart UI error:', err);
        overlay.innerHTML = `<div style="text-align:center;"><span style="color: #ff4444; display:block; margin-bottom:10px;">✗ ${err.name}: ${err.message}</span>
            <p style="font-size:0.8em; color:#888;">Ensure TradingView script is loaded and you have internet access.</p>
            <button class="btn btn-mini" style="margin-top:10px" onclick="closeAnalysisModal()">Close</button></div>`;
    }
}

async function fetchCandles(exchange, symbol, timeframe) {
    const tfMap = { '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1h', '4h': '4h', '1d': '1d' };
    const tf = tfMap[timeframe] || '1h';

    // Normalize symbol
    const cleanSymbol = symbol.replace('_', '').replace('-', '').toUpperCase();
    const exch = exchange ? exchange.toUpperCase() : 'BINANCE';

    // Use local proxy to avoid CORS issues with browser fetch
    const url = `/api/proxy/klines?symbol=${cleanSymbol}&interval=${tf}&limit=200&exchange=${exch}`;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Proxy API returned ${response.status}`);
        const data = await response.json();
        return parseKlines(data);
    } catch (e) {
        console.error(`Fetch klines failed via proxy for ${cleanSymbol}:`, e);
        return [];
    }
}

function parseKlines(data) {
    if (!Array.isArray(data)) return [];
    return data.map(d => ({
        time: d[0] / 1000,
        open: parseFloat(d[1]),
        high: parseFloat(d[2]),
        low: parseFloat(d[3]),
        close: parseFloat(d[4])
    }));
}

function addModalKey(label, color) {
    const key = document.getElementById('modalTradeKey');
    const item = document.createElement('div');
    item.className = 'key-item';
    item.style.display = 'flex';
    item.style.alignItems = 'center';
    item.style.gap = '8px';
    item.innerHTML = `<span style="width: 12px; height: 12px; background: ${color}; border-radius: 2px;"></span><span style="color: #ccc;">${label}</span>`;
    key.appendChild(item);
}

function plotAnalysisData(chart, series, data, candles, trade) {
    if (!data) data = {};
    const reason = (trade.reason || "").toUpperCase();

    // 1. Draw Fair Value Gaps (FVG)
    if (data.fvg) {
        const color = data.fvg.type === 'BULLISH' ? 'rgba(0, 255, 136, 0.2)' : 'rgba(255, 68, 68, 0.2)';
        const borderColor = data.fvg.type === 'BULLISH' ? '#00ff88' : '#ff4444';

        series.createPriceLine({
            price: data.fvg.top,
            color: borderColor,
            lineWidth: 1,
            lineStyle: 1, // Dotted
            title: 'FVG TOP',
        });
        series.createPriceLine({
            price: data.fvg.bottom,
            color: borderColor,
            lineWidth: 1,
            lineStyle: 1, // Dotted
            title: 'FVG BTM',
        });
        addModalKey(`FVG (${data.fvg.type})`, color);
    }

    // 2. Mitigation Block (MB)
    if (data.mitigation_block) {
        series.createPriceLine({
            price: data.mitigation_block.level,
            color: '#00d4ff',
            lineWidth: 2,
            lineStyle: 0, // Solid
            axisLabelVisible: true,
            title: 'MB LEVEL',
        });
        addModalKey('Mitigation Block', '#00d4ff');
    }

    // 3. ICT Phase Visualization
    if (data.ict_phase) {
        const color = data.ict_phase === 'ACCUMULATION' ? '#00ff88' : '#ff4444';
        series.createPriceLine({
            price: data.price_level,
            color: color,
            lineWidth: 2,
            lineStyle: 0, // Solid
            axisLabelVisible: true,
            title: `ICT ${data.ict_phase}`,
        });
        addModalKey(`ICT ${data.ict_phase}`, color);
    }

    // 4. UT Bot Stop Level
    if (data.ut_stop) {
        series.createPriceLine({
            price: data.ut_stop,
            color: '#ffaa00',
            lineWidth: 1,
            lineStyle: 2, // Dashed
            axisLabelVisible: true,
            title: 'UT STOP',
        });
        addModalKey('UT Bot Stop', '#ffaa00');
    }

    // 5. Harmonic Level
    if (data.harmonic_level) {
        series.createPriceLine({
            price: data.fib_level,
            color: '#ff00ff',
            lineWidth: 1,
            lineStyle: 1, // Dotted
            axisLabelVisible: true,
            title: `FIB ${data.harmonic_level}`,
        });
        addModalKey(`Fib ${data.harmonic_level}`, '#ff00ff');
    }

    // 6. Keltner Channels (Heuristic or Data)
    if (data.keltner_upper) {
        series.createPriceLine({ price: data.keltner_upper, color: 'rgba(255,255,255,0.1)', lineWidth: 1, lineStyle: 1, title: 'KC UPPER' });
        series.createPriceLine({ price: data.keltner_lower, color: 'rgba(255,255,255,0.1)', lineWidth: 1, lineStyle: 1, title: 'KC LOWER' });
        addModalKey('Keltner Channels', 'rgba(255,255,255,0.3)');
    }

    // 8. PSAR Scalp
    if (data.psar) {
        series.createPriceLine({ price: data.psar, color: '#ff00ff', lineWidth: 1, lineStyle: 2, title: 'PSAR' });
        addModalKey('PSAR', '#ff00ff');
    }

    // 9. TEMA Level
    if (data.tema) {
        series.createPriceLine({ price: data.tema, color: '#00d4ff', lineWidth: 1, lineStyle: 0, title: 'TEMA' });
        addModalKey('TEMA', '#00d4ff');
    }

    // 10. KAMA Level
    if (data.kama) {
        series.createPriceLine({ price: data.kama, color: '#ffaa00', lineWidth: 1, lineStyle: 0, title: 'KAMA' });
        addModalKey('KAMA', '#ffaa00');
    }

    // 11. Chandelier Exit
    if (data.chandelier_long) {
        series.createPriceLine({ price: data.chandelier_long, color: '#00ff88', lineWidth: 1, lineStyle: 1, title: 'CHANDELIER' });
        addModalKey('Chandelier Exit', '#00ff88');
    }

    // 12. ZLSMA
    if (data.zlsma) {
        series.createPriceLine({ price: data.zlsma, color: '#f0b90b', lineWidth: 1, lineStyle: 0, title: 'ZLSMA' });
        addModalKey('ZLSMA', '#f0b90b');
    }

    // 13. Momentum Indicators (RSI, UO, VFI labels)
    if (data.rsi !== undefined || data.uo !== undefined || data.vfi !== undefined) {
        let label = "";
        if (data.rsi !== undefined) label += `RSI:${data.rsi.toFixed(0)} `;
        if (data.uo !== undefined) label += `UO:${data.uo.toFixed(0)} `;
        if (data.vfi !== undefined) label += `VFI:${data.vfi.toFixed(2)}`;
        addModalKey(label.trim(), '#888');
    }

    // 7. Mark the Signal Candle & Confluences (Markers)
    if (candles && candles.length > 0) {
        const lastCandle = candles[candles.length - 1];
        const markers = [
            {
                time: lastCandle.time,
                position: 'aboveBar',
                color: '#f0b90b',
                shape: 'arrowDown',
                text: 'SIGNAL',
            }
        ];

        // Squeeze Release
        if (data.squeeze === 'OFF' || reason.includes('SQUEEZE') || reason.includes('SQZ')) {
            markers.push({
                time: lastCandle.time,
                position: 'belowBar',
                color: '#00ff88',
                shape: 'circle',
                text: 'SQZ BRK',
            });
            addModalKey('Squeeze Release', '#00ff88');
        }

        // ADX / Momentum
        if (reason.includes('ADX') || reason.includes('MOMENTUM') || reason.includes('MOM:')) {
            markers.push({
                time: lastCandle.time,
                position: 'belowBar',
                color: '#00d4ff',
                shape: 'arrowUp',
                text: 'MOM',
            });
            addModalKey('Momentum Confirmed', '#00d4ff');
        }

        // Trend Alignment
        if (reason.includes('TREND') || reason.includes('ALIGNMENT')) {
            markers.push({
                time: lastCandle.time,
                position: trade.type === 'LONG' ? 'belowBar' : 'aboveBar',
                color: trade.type === 'LONG' ? '#00ff88' : '#ff4444',
                shape: trade.type === 'LONG' ? 'arrowUp' : 'arrowDown',
                text: 'TREND',
            });
            addModalKey('Trend Alignment', trade.type === 'LONG' ? '#00ff88' : '#ff4444');
        }

        series.setMarkers(markers);
    }
}

// Keyboard listener for modals
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeAnalysisModal();
        closeAgreementModal();
    }
});

// ===== Agreement Details Popup =====

window.showAgreementDetails = function (signalId) {
    console.log("Opening agreement details for:", signalId);
    const card = document.getElementById(signalId);
    if (!card) {
        console.error("Card not found for signalId:", signalId);
        return;
    }

    let strategies = [];
    try {
        strategies = JSON.parse(card.dataset.agreeingStrategies || '[]');
    } catch (e) {
        console.error("Error parsing strategies:", e);
    }

    const symbol = signalId.replace('signal-', '').split('-')[0].toUpperCase();

    const titleEl = document.getElementById('agreementTitle');
    const subtitleEl = document.getElementById('agreementSubtitle');
    const modal = document.getElementById('agreementModal');
    const list = document.getElementById('agreementList');

    if (!modal || !list) {
        console.error("Agreement modal or list container not found!");
        return;
    }

    titleEl.innerText = `🤝 ${symbol} Confluence`;
    subtitleEl.innerText = `${strategies.length} Strategies Aligning`;

    list.innerHTML = '';

    if (strategies.length === 0) {
        list.innerHTML = '<div style="color: #666; padding: 10px;">No specific strategies recorded yet.</div>';
    } else {
        strategies.forEach((strat, index) => {
            const item = document.createElement('div');
            item.style.padding = '12px';
            item.style.marginBottom = '8px';
            item.style.background = 'rgba(255,255,255,0.03)';
            item.style.borderLeft = '3px solid #00ff88';
            item.style.borderRadius = '0 4px 4px 0';
            item.style.fontSize = '0.9em';
            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold; color: #fff;">${strat}</span>
                    <span style="font-size: 0.8em; color: #00ff88;">✅ Active</span>
                </div>
            `;
            list.appendChild(item);
        });
    }

    modal.style.display = 'block';
    console.log("Agreement modal displayed");
};

window.closeAgreementModal = function () {
    document.getElementById('agreementModal').style.display = 'none';
};

// ===== Market Status Updates =====

function updateMarketStatus(data) {
    // 1. Update Sentinel Badge
    const badge = document.getElementById('sentimentBadge');
    if (badge) {
        let color = '#777';
        if (data.sentiment.includes('BULLISH')) color = '#00ff00';
        else if (data.sentiment.includes('BEARISH')) color = '#ff4444';

        badge.style.color = color;
        badge.style.borderColor = color;
        badge.innerHTML = `BTC SENTIMENT: ${data.sentiment}`;
    }

    // 2. Update Volatility Warning
    const warningBox = document.getElementById('marketWarning');
    if (warningBox) {
        if (data.volatility_warning) {
            warningBox.style.display = 'block';
            warningBox.innerText = data.volatility_warning;
        } else if (data.news_warning) {
            warningBox.style.display = 'block';
            warningBox.innerText = data.news_warning;
        } else {
            warningBox.style.display = 'none';
        }
    }

    // 3. Update News Feed
    const feedList = document.getElementById('newsFeedList');
    if (feedList && data.news_feed) {
        // Update header info with last sync time
        const info = document.querySelector('.news-wrapper .terminal-info');
        if (info) {
            const now = new Date();
            info.innerHTML = `Live Feed (last sync: ${now.toLocaleTimeString()})`;
        }
        feedList.innerHTML = '';
        data.news_feed.forEach(item => {
            const div = document.createElement('div');
            div.className = 'news-item';

            // Color based on sentiment
            let sentimentColor = '#888';
            if (item.sentiment === 'POSITIVE') sentimentColor = '#00ff88';
            if (item.sentiment === 'NEGATIVE') sentimentColor = '#ff4444';

            // Format Date
            let dateDisplay = item.pub_date;
            try {
                const d = new Date(item.pub_date);
                if (!isNaN(d.getTime())) {
                    dateDisplay = d.toLocaleString();
                }
            } catch (e) { }

            div.innerHTML = `
                <div style="margin-bottom: 2px;">
                    <a href="${item.link}" target="_blank" style="color: #ddd; text-decoration: none; font-weight: bold;">${item.title}</a>
                </div>
                <div style="font-size: 0.85em; display: flex; justify-content: space-between;">
                    <span style="color: #666;">🕒 ${dateDisplay}</span>
                    <span style="color: ${sentimentColor}; font-weight: bold;">[${item.sentiment}]</span>
                </div>
            `;
            // Add subtle separator
            div.style.borderBottom = '1px solid #333';
            div.style.padding = '8px 0';
            feedList.appendChild(div);
        });
    }
}
// Refresh News Manually
window.refreshNews = function () {
    const btn = document.getElementById('refreshNewsBtn');
    if (btn) {
        btn.innerHTML = '↻ Loading...';
        btn.disabled = true;
    }
    socket.emit('refresh_news');

    // Re-enable in 2 seconds (visual feedback)
    setTimeout(() => {
        if (btn) {
            btn.innerHTML = '↻ Refresh';
            btn.disabled = false;
        }
    }, 2000);
}
