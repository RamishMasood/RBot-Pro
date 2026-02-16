// RBot Pro Multi-Exchange Analysis UI - JavaScript Client

// Detect environment to handle Vercel's lack of WebSocket support
const isVercelEnvironment = typeof window.IS_VERCEL !== 'undefined' ? window.IS_VERCEL : window.location.hostname.includes('vercel.app');

const socket = io(window.location.origin, {
    reconnection: true,
    reconnectionDelay: isVercelEnvironment ? 1500 : 1000,
    reconnectionDelayMax: isVercelEnvironment ? 7000 : 5000,
    reconnectionAttempts: Infinity,
    transports: isVercelEnvironment ? ['polling'] : ['polling', 'websocket'],
    upgrade: !isVercelEnvironment,
    rememberUpgrade: false,
    timeout: isVercelEnvironment ? 30000 : 20000,
    closeOnBeforeunload: false
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

    if (window.wasDisconnected) {
        if (!isVercelEnvironment) {
            addTerminalLine('✓ Reconnected to RBot Pro server', 'success');
        }
        window.wasDisconnected = false;
    }
});

socket.on('connect_error', (error) => {
    console.warn('Connection/Polling Warning:', error.message);
    if (!isVercelEnvironment) {
        updateStatus('Connecting...', 'warning');
    }
});

socket.on('disconnect', (reason) => {
    console.log('✗ Socket Disconnected:', reason);

    if (reason === 'io server disconnect') {
        socket.connect();
    }

    if (!window.wasDisconnected) {
        window.wasDisconnected = true;
        // Don't flip the UI immediately on Vercel to avoid flickering
        if (!isVercelEnvironment) {
            updateStatus('Reconnecting...', 'warning');
            addTerminalLine('✗ Connection lost. Reconnecting...', 'warning');
        }
    }
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
    updateTradeStats();
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

socket.on('tracking_update', (trades) => {
    updateTrackingUI(trades);
});

function updateTrackingUI(trades) {
    // Map to aggregate best status per signalId
    const aggregated = {};

    trades.forEach(trade => {
        const cleanSymbol = trade.symbol.replace(/_/g, '').toUpperCase();
        const exch = trade.exchange ? trade.exchange.toUpperCase().replace(/\./g, '') : 'BINANCE';
        const signalId = `signal-${exch}-${cleanSymbol}-${trade.type}`.replace(/[^a-zA-Z0-9-]/g, '');

        const status = trade.tracking_status || 'WAITING';
        const pnl = trade.pnl_pct || 0;
        const price = trade.current_price || trade.entry;

        if (!aggregated[signalId]) {
            aggregated[signalId] = { status, pnl, price, exchange: trade.exchange };
        } else {
            // Pick 'most advanced' status per card
            const priority = { 'TP_HIT': 4, 'SL_HIT': 3, 'RUNNING': 2, 'WAITING': 1 };
            if (priority[status] > priority[aggregated[signalId].status]) {
                aggregated[signalId].status = status;
                aggregated[signalId].pnl = pnl;
                aggregated[signalId].price = price;
            } else if (status === aggregated[signalId].status) {
                aggregated[signalId].price = price;
                aggregated[signalId].pnl = pnl;
            }
        }
    });

    Object.keys(aggregated).forEach(signalId => {
        const card = document.getElementById(signalId);
        if (!card) return;

        const trackingSection = card.querySelector('.tracking-area');
        if (!trackingSection) return;

        const { status, pnl, price, exchange } = aggregated[signalId];
        const pnlClass = pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
        const pnlSign = pnl >= 0 ? '+' : '';

        trackingSection.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="status-badge status-${status.toLowerCase()}">${status.replace('_', ' ')}</span>
                <div class="pnl-display ${pnlClass}">
                    ${pnlSign}${pnl.toFixed(2)}%
                </div>
            </div>
            <div class="live-price-box">
                LIVE PRICE (${exchange})
                <span class="live-price-val">$${price < 0.00001 ? price.toFixed(10) : (price < 0.01 ? price.toFixed(8) : (price < 1 ? price.toFixed(6) : price.toFixed(2)))}</span>
            </div>
        `;
    });

    // Refresh stats after UI updates
    updateTradeStats();
}

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

    // STRICTOR FILTER: Only show trades with R/R >= 2:1 as requested
    const rrValue = parseFloat(trade.risk_reward);
    if (!isNaN(rrValue) && rrValue < 2.0) {
        console.log(`⚠️ Hiding low R/R signal: ${trade.symbol} (${rrValue}:1)`);
        return;
    }

    // Normalize symbol and exchange for ID
    const cleanSymbol = trade.symbol.replace(/_/g, '').toUpperCase();
    const exch = trade.exchange ? trade.exchange.toUpperCase().replace(/\./g, '') : 'BINANCE';

    // Unique ID per Exchange + Symbol + Type
    const signalId = `signal-${exch}-${cleanSymbol}-${trade.type}`.replace(/[^a-zA-Z0-9-]/g, '');
    let card = document.getElementById(signalId);
    let isUpdate = !!card;

    if (!isUpdate) {
        card = document.createElement('div');
        card.id = signalId;
        card.dataset.agreeingStrategies = JSON.stringify([trade.strategy]);
        // Store complete trade object for modal access
        card.dataset.tradeData = JSON.stringify(trade);
        // Initialize strategy details array with first strategy
        const initialDetails = [{
            strategy: trade.strategy,
            timeframe: trade.timeframe || 'N/A',
            entry: trade.entry,
            sl: trade.sl,
            tp1: trade.tp1,
            confidence: trade.confidence_score || 0
        }];
        card.dataset.strategyDetails = JSON.stringify(initialDetails);
        signalsCount++;
        // Count update is now handled by filterSignalsByQuality()
    } else {
        // Build agreement list incrementally during live scan
        let existing = JSON.parse(card.dataset.agreeingStrategies || '[]');
        let existingDetails = JSON.parse(card.dataset.strategyDetails || '[]');

        // Strategy label with timeframe for better detail
        const currentStratLabel = `${trade.strategy} (${trade.timeframe || '?'})`;

        // If the backend sends a full list (post-processing), use it. Otherwise append.
        if (trade.agreeing_strategies && trade.agreeing_strategies.length > 0) {
            existing = trade.agreeing_strategies;
        } else if (!existing.includes(currentStratLabel) && !existing.includes(trade.strategy)) {
            // Check if we already have it in either simple or TF-enriched form
            existing.push(currentStratLabel);

            // CRITICAL: Add this strategy's details to the array
            const newDetail = {
                strategy: trade.strategy,
                timeframe: trade.timeframe || 'N/A',
                entry: trade.entry,
                sl: trade.sl,
                tp1: trade.tp1,
                confidence: trade.confidence_score || 0
            };
            existingDetails.push(newDetail);
        }
        card.dataset.agreeingStrategies = JSON.stringify(existing);
        card.dataset.strategyDetails = JSON.stringify(existingDetails);

        // CRITICAL: Update trade data if this is a final merged signal with details from backend
        if (trade.agreeing_strategies_details) {
            card.dataset.tradeData = JSON.stringify(trade);
            // Use backend details if available (they are post-processed and more accurate)
            card.dataset.strategyDetails = JSON.stringify(trade.agreeing_strategies_details);
        } else if (!card.dataset.tradeData) {
            // Store initial trade data if not already stored
            card.dataset.tradeData = JSON.stringify(trade);
        }
    }

    // Get final agreement list for this render
    const agreeingStrategies = JSON.parse(card.dataset.agreeingStrategies);
    const agreementCount = trade.agreement_count || agreeingStrategies.length;

    // Quality Upgrade Logic: Elite > Strong > Standard
    let finalQuality = trade.signal_quality || 'STANDARD';
    if (isUpdate) {
        const qualityPriority = { 'ELITE': 3, 'STRONG': 2, 'STANDARD': 1 };
        const currentClasses = Array.from(card.classList);
        const currentQualityClass = currentClasses.find(c => c.startsWith('quality-'));
        if (currentQualityClass) {
            const currentQ = currentQualityClass.split('-')[1].toUpperCase();
            if (qualityPriority[currentQ] > qualityPriority[finalQuality]) {
                finalQuality = currentQ; // Keep the higher quality
            }
        }
    }

    card.className = `trade-card ${trade.type.toLowerCase()} quality-${finalQuality.toLowerCase()}`;

    // Check visibility against selected quality filters
    const selectedQualities = Array.from(document.querySelectorAll('#qualityList input:checked')).map(cb => cb.value);
    if (!selectedQualities.includes(finalQuality)) {
        card.style.display = 'none';
    } else {
        card.style.display = '';
    }

    // Simplified color mapping for UI
    const typeColor = trade.type === 'LONG' ? '#00ff88' : '#ff4444';
    const exchangeName = trade.exchange || 'N/A';

    // Exchange badge color mapping (Case-Insensitive)
    const exchangeColors = {
        'MEXC': '#00b897',
        'BINANCE': '#f0b90b',
        'BITGET': '#00f0ff',
        'BYBIT': '#f7931a',
        'OKX': '#ffffff',
        'KUCOIN': '#23af91',
        'GATEIO': '#2354e6',
        'HTX': '#2b71d6'
    };
    const exchangeColor = exchangeColors[exchangeName.toUpperCase()] || '#888';

    // Store trade data as a data attribute so the copy button can access it
    const tradeDataEncoded = encodeURIComponent(JSON.stringify(trade));

    // Signal quality badge colors
    const qualityStyles = {
        'ELITE': { bg: '#ffd70022', color: '#ffd700', border: '#ffd70055', icon: '🏆', label: 'ELITE' },
        'STRONG': { bg: '#00ff8822', color: '#00ff88', border: '#00ff8855', icon: '💪', label: 'STRONG' },
        'STANDARD': { bg: '#00d4ff22', color: '#00d4ff', border: '#00d4ff55', icon: '📊', label: 'STANDARD' }
    };
    const quality = qualityStyles[finalQuality] || qualityStyles['STANDARD'];

    // Agreement badge (Now an interactive button)
    const agreementHtml = agreementCount > 1
        ? `<button onclick="event.stopPropagation(); showAgreementDetails('${signalId}')" style="background: #00ff8822; color: #00ff88; border: 1px solid #00ff8855; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; margin-left: 6px; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.background='#00ff8833'" onmouseout="this.style.background='#00ff8822'">✅ ${agreementCount} agree</button>`
        : '';

    // Conflict warning
    const conflictHtml = trade.conflict_warning
        ? `<div style="background: #ff444422; border: 1px solid #ff444455; border-radius: 6px; padding: 6px 10px; margin-top: 8px; font-size: 0.8em; color: #ff8888;">⚠️ <b>CONFLICT:</b> ${trade.conflict_warning}</div>`
        : '';

    // Volatility/Market Warning
    const warningHtml = trade.warning
        ? `<div style="background: #ffaa0022; border: 1px solid #ffaa0055; border-radius: 6px; padding: 6px 10px; margin-top: 8px; font-size: 0.8em; color: #ffaa00;">🛡️ <b>RISK:</b> ${trade.warning}</div>`
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
                <span class="trade-val">$${trade.entry < 0.00001 ? trade.entry.toFixed(10) : (trade.entry < 0.01 ? trade.entry.toFixed(8) : trade.entry.toFixed(6))}</span>
            </div>
            <div>
                <span class="trade-label">Stop Loss</span>
                <span class="trade-val" style="color:#ff8888;">$${trade.sl < 0.00001 ? trade.sl.toFixed(10) : (trade.sl < 0.01 ? trade.sl.toFixed(8) : trade.sl.toFixed(6))}</span>
            </div>
            <div>
                <span class="trade-label">Target</span>
                <span class="trade-val" style="color:#00ff88;">$${trade.tp1 < 0.00001 ? trade.tp1.toFixed(10) : (trade.tp1 < 0.01 ? trade.tp1.toFixed(8) : trade.tp1.toFixed(6))}</span>
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
                </div>${conflictHtml}${warningHtml}
                <div class="tracking-area">
                    ${isUpdate ? (card.querySelector('.tracking-area') ? card.querySelector('.tracking-area').innerHTML : '') : `
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span class="status-badge status-waiting">WAITING TO ENTER</span>
                        <div class="pnl-display">0.00%</div>
                    </div>
                    `}
                </div>
                <button class="btn-mini btn-primary" onclick="executeManualTrade(this)" data-trade="${tradeDataEncoded}" style="margin-top:5px; width:100%; margin-bottom:5px; background: linear-gradient(90deg, #ff8800, #ff4400); border:none;">🚀 TRADE NOW (Real)</button>
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

    // Update filtering and count display
    filterSignalsByQuality();
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

        // Helper to format numbers safely (Max Precision)
        const f = (val) => {
            const n = parseFloat(val);
            if (isNaN(n)) return '0.000000';
            if (n < 0.00001) return n.toFixed(10);
            if (n < 0.01) return n.toFixed(8);
            if (n < 1) return n.toFixed(6);
            return n.toFixed(2);
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
    const strategies = getSelectedStrategies();
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

    if (strategies.length === 0) {
        alert('Please select at least one strategy');
        return;
    }

    if (timeframes.length === 0) {
        alert('Please select at least one timeframe');
        return;
    }

    socket.emit('output', { 'data': `🚀 Starting analysis on ${exchanges.join(', ')} with ${symbols.length} coins, ${indicators.length} indicators, ${strategies.length} strategies, and ${timeframes.length} timeframes\n` });

    // Clear previous signals for new run
    const countEl = document.getElementById('signalsCount');
    if (countEl) countEl.innerText = '0 Found';
    signalsCount = 0;
    const signalsBox = document.getElementById('signalsBox');
    if (signalsBox) {
        signalsBox.innerHTML = '<div class="terminal-line" id="noSignalsMsg"><span class="line-prefix">#</span><span class="line-text" style="color: #666;">Signals found during the current run will appear here...</span></div>';
    }

    // Save exchanges to config first
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exchanges: exchanges })
    });

    // Trigger analysis via REST API (More robust for Vercel/Serverless than socket.emit)
    const analysisData = {
        sid: socket.id, // CRITICAL: Pass SID so server knows where to emit
        symbols: symbols,
        indicators: indicators,
        strategies: strategies,
        timeframes: timeframes,
        min_confidence: confidence,
        exchanges: exchanges
    };

    fetch('/api/start-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(analysisData)
    }).then(r => r.json()).then(res => {
        if (res.status !== 'ok') {
            addTerminalLine(`❌ API Error: ${res.msg}`, 'error');
        }
    }).catch(err => {
        console.error('Failed to trigger analysis:', err);
        // Fallback to socket if API fails
        socket.emit('start_analysis', analysisData);
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
    const countEl = document.getElementById('selectedIndicatorsCount');
    if (countEl) countEl.textContent = count;
    // Also save to server config
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ indicators: getSelectedIndicators() })
    });
}

function getSelectedStrategies() {
    return Array.from(document.querySelectorAll('#strategyList input:checked'))
        .map(cb => cb.value);
}

function selectAllStrategies() {
    document.querySelectorAll('#strategyList input').forEach(cb => cb.checked = true);
    updateStrategyCount();
}

function deselectAllStrategies() {
    document.querySelectorAll('#strategyList input').forEach(cb => cb.checked = false);
    updateStrategyCount();
}

function updateStrategyCount() {
    const count = getSelectedStrategies().length;
    const countEl = document.getElementById('selectedStrategiesCount');
    if (countEl) countEl.textContent = count;
    // Also save to server config
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategies: getSelectedStrategies() })
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
            strategies: getSelectedStrategies(),
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

// ===== Signal Filtering =====
function filterSignalsByQuality() {
    const selectedQualities = Array.from(document.querySelectorAll('#qualityList input:checked')).map(cb => cb.value);
    const cards = document.querySelectorAll('.trade-card');
    let visibleCount = 0;

    cards.forEach(card => {
        let isVisible = false;
        if (card.classList.contains('quality-elite') && selectedQualities.includes('ELITE')) isVisible = true;
        if (card.classList.contains('quality-strong') && selectedQualities.includes('STRONG')) isVisible = true;
        if (card.classList.contains('quality-standard') && selectedQualities.includes('STANDARD')) isVisible = true;

        card.style.display = isVisible ? '' : 'none';
        if (isVisible) visibleCount++;
    });

    // Update count display to show filtered count
    const total = signalsCount;
    document.getElementById('signalsCount').innerText = `${visibleCount} Visible / ${total} Found`;

    updateTradeStats();
}

function updateTradeStats() {
    const cards = document.querySelectorAll('.trade-card');
    let tp = 0;
    let sl = 0;
    let running = 0;
    let waiting = 0;

    cards.forEach(card => {
        if (card.style.display === 'none') return; // Skip hidden cards based on filter

        const badge = card.querySelector('.status-badge');
        if (badge) {
            const text = badge.innerText.toUpperCase();
            if (text.includes('TP HIT')) tp++;
            else if (text.includes('SL HIT')) sl++;
            else if (text.includes('RUNNING')) running++;
            else if (text.includes('WAITING') || text === 'WAITING') waiting++;
            else waiting++; // Default fallback
        } else {
            waiting++; // Default if badge not rendered yet
        }
    });

    const statsEl = document.getElementById('signalStats');
    if (statsEl) {
        statsEl.innerHTML = `
            <span style="color:#00ff88; margin-right:15px">TP: ${tp}</span>
            <span style="color:#ff4444; margin-right:15px">SL: ${sl}</span>
            <span style="color:#00d4ff; margin-right:15px">RUNNING: ${running}</span>
            <span style="color:#aaa">WAITING: ${waiting}</span>
        `;
    }
}

// ===== Analysis Chart Functions =====

let activeChart = null;
let activeCandleSeries = null;
let activeUpdateInterval = null;
let isChartUpdating = false;

function closeAnalysisModal() {
    document.getElementById('analysisModal').style.display = 'none';
    if (activeUpdateInterval) {
        clearInterval(activeUpdateInterval);
        activeUpdateInterval = null;
    }
    if (activeChart) {
        activeChart.remove();
        activeChart = null;
    }
    activeCandleSeries = null;
    isChartUpdating = false;
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
    overlay.innerHTML = '<div class="loader"></div><span>Initializing Chart Data...</span>';
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
            priceFormat: {
                type: 'price',
                precision: trade.entry < 0.00001 ? 10 : (trade.entry < 0.01 ? 8 : (trade.entry < 1 ? 6 : 2)),
                minMove: trade.entry < 0.00001 ? 0.0000000001 : (trade.entry < 0.01 ? 0.00000001 : (trade.entry < 1 ? 0.000001 : 0.01)),
            },
        });
        activeCandleSeries = candlestickSeries;

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

            // Plot tactical data (indicators, markers, etc)
            plotAnalysisData(chart, candlestickSeries, trade.analysis_data, candles, trade);

            // Start Live Updates
            if (activeUpdateInterval) clearInterval(activeUpdateInterval);
            activeUpdateInterval = setInterval(async () => {
                if (isChartUpdating || !activeChart || !activeCandleSeries) return;
                isChartUpdating = true;
                try {
                    const newCandles = await fetchCandles(trade.exchange, trade.symbol, trade.timeframe);
                    if (newCandles && newCandles.length > 0 && activeCandleSeries) {
                        activeCandleSeries.setData(newCandles);
                    }
                } catch (e) {
                    console.warn("Live update failed:", e);
                } finally {
                    isChartUpdating = false;
                }
            }, 1000);
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
    const isLong = trade.type === 'LONG';
    const sigText = isLong ? 'BUY' : 'SELL';
    const sigColor = isLong ? '#00ff88' : '#ff4444';

    // Helper for adding lines (EMA, TEMA, etc)
    const addIndicatorLine = (lineData, color, title) => {
        if (!lineData || !Array.isArray(lineData)) return;
        const lineSeries = chart.addLineSeries({
            color: color,
            lineWidth: 2,
            title: title,
            priceFormat: {
                type: 'price',
                precision: 4,
                minMove: 0.0001,
            },
        });
        lineSeries.setData(lineData);
        addModalKey(title, color);
    };

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

    // 2b. Order Blocks (OB)
    if (data.order_blocks) {
        if (data.order_blocks.bullish_ob) {
            series.createPriceLine({
                price: data.order_blocks.bullish_ob.high,
                color: 'rgba(0, 255, 136, 0.4)',
                lineWidth: 1,
                lineStyle: 2,
                title: 'BULL OB',
            });
            addModalKey('Bullish Order Block', 'rgba(0, 255, 136, 0.6)');
        }
        if (data.order_blocks.bearish_ob) {
            series.createPriceLine({
                price: data.order_blocks.bearish_ob.low,
                color: 'rgba(255, 68, 68, 0.4)',
                lineWidth: 1,
                lineStyle: 2,
                title: 'BEAR OB',
            });
            addModalKey('Bearish Order Block', 'rgba(255, 68, 68, 0.6)');
        }
    }

    // 2c. Supply / Demand Zones
    if (data.sup_dem) {
        series.createPriceLine({
            price: data.sup_dem.level,
            color: data.sup_dem.type === 'SUPPLY' ? '#ffaa00' : '#00d4ff',
            lineWidth: 1,
            lineStyle: 3,
            title: data.sup_dem.type,
        });
        addModalKey(`${data.sup_dem.type} Zone`, data.sup_dem.type === 'SUPPLY' ? '#ffaa00' : '#00d4ff');
    }

    // 2d. Break of Structure (BOS)
    if (data.bos) {
        series.createPriceLine({
            price: data.bos.level,
            color: '#ffffff',
            lineWidth: 1,
            lineStyle: 1,
            title: data.bos.type,
        });
        addModalKey(data.bos.type, '#ffffff');
    }


    // 3. UT Bot Stop Level
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

    // 4. PSAR Series
    if (data.psar_series) {
        // PSAR is often dots, but line is okay for simplified view
        addIndicatorLine(data.psar_series, '#ff00ff', 'PSAR');
    } else if (data.psar) {
        series.createPriceLine({ price: data.psar, color: '#ff00ff', lineWidth: 1, lineStyle: 2, title: 'PSAR' });
        addModalKey('PSAR', '#ff00ff');
    }

    // 5. TEMA Series
    if (data.tema_series) {
        addIndicatorLine(data.tema_series, '#00d4ff', 'TEMA');
    } else if (data.tema) {
        series.createPriceLine({ price: data.tema, color: '#00d4ff', lineWidth: 1, lineStyle: 0, title: 'TEMA' });
        addModalKey('TEMA', '#00d4ff');
    }

    // 6. KAMA Series
    if (data.kama_series) {
        addIndicatorLine(data.kama_series, '#ffaa00', 'KAMA');
    } else if (data.kama) {
        series.createPriceLine({ price: data.kama, color: '#ffaa00', lineWidth: 1, lineStyle: 0, title: 'KAMA' });
        addModalKey('KAMA', '#ffaa00');
    }

    // 7. Chandelier Exit
    if (data.chandelier_series) {
        addIndicatorLine(data.chandelier_series, isLong ? '#00ff88' : '#ff4444', 'CHANDELIER');
    } else if (data.chandelier_long && isLong) {
        series.createPriceLine({ price: data.chandelier_long, color: '#00ff88', lineWidth: 1, lineStyle: 1, title: 'CHANDELIER' });
        addModalKey('Chandelier Exit', '#00ff88');
    } else if (data.chandelier_short && !isLong) {
        series.createPriceLine({ price: data.chandelier_short, color: '#ff4444', lineWidth: 1, lineStyle: 1, title: 'CHANDELIER' });
        addModalKey('Chandelier Exit', '#ff4444');
    }

    // 8. ZLSMA Series
    if (data.zlsma_series) {
        addIndicatorLine(data.zlsma_series, '#f0b90b', 'ZLSMA');
    } else if (data.zlsma) {
        series.createPriceLine({ price: data.zlsma, color: '#f0b90b', lineWidth: 1, lineStyle: 0, title: 'ZLSMA' });
        addModalKey('ZLSMA', '#f0b90b');
    }

    // 9. EMA 200 (Commonly requested context)
    if (data.ema200_series) {
        addIndicatorLine(data.ema200_series, 'rgba(255,255,255,0.3)', 'EMA 200');
    }

    // 10. Momentum & Advanced Metrics Labels (Tactical Info)
    if (data.rsi !== undefined || data.uo !== undefined || data.vfi !== undefined ||
        data.market_regime || data.wyckoff_phase || data.wyckoff ||
        data.zscore || data.mtf_bias || data.rvol || data.harmonic_pattern) {

        let label = "";

        // Elite 2026 Indicators
        if (data.mtf_bias) label += `BIAS:${data.mtf_bias} `;
        if (data.market_regime) label += `REGIME:${data.market_regime.regime || data.market_regime} `;

        const w_phase = data.wyckoff_phase?.phase || data.wyckoff || data.wyckoff_phase;
        if (w_phase && w_phase !== 'NEUTRAL' && w_phase !== 'UNKNOWN') {
            label += `WYCKOFF:${w_phase} `;
        }

        if (data.harmonic_pattern) label += `HARMONIC:${data.harmonic_pattern} `;
        if (data.rvol !== undefined) label += `RVOL:${typeof data.rvol === 'object' ? data.rvol.ratio : data.rvol}x `;

        // Standard technicals
        if (data.cumulative_delta !== undefined) label += `Δ:${data.cumulative_delta.toFixed(0)} `;
        if (data.zscore !== undefined) label += `Z:${data.zscore.toFixed(2)} `;
        if (data.rsi !== undefined) label += `RSI:${data.rsi.toFixed(0)} `;
        if (data.vfi !== undefined) label += `VFI:${data.vfi.toFixed(2)}`;

        if (label.trim()) {
            addModalKey(label.trim(), '#ddd');
        }
    }


    // 11. Mark the Signal Candle & Confluences (Markers)
    if (candles && candles.length > 0) {
        const lastCandle = candles[candles.length - 1];
        // Use exact candle time from signal if available, else fallback to latest
        const signalTime = trade.candle_time || lastCandle.time;

        const markers = [
            {
                time: signalTime,
                position: isLong ? 'belowBar' : 'aboveBar',
                color: sigColor,
                shape: isLong ? 'arrowUp' : 'arrowDown',
                text: sigText,
                size: 2
            }
        ];

        // Squeeze Release
        if (data.squeeze === 'OFF' || reason.includes('SQUEEZE') || reason.includes('SQZ')) {
            markers.push({
                time: signalTime,
                position: isLong ? 'belowBar' : 'aboveBar',
                color: '#00ff88',
                shape: 'circle',
                text: 'SQZ BRK',
            });
            addModalKey('Squeeze Release', '#00ff88');
        }

        // Trend Alignment
        if (reason.includes('TREND') || reason.includes('ALIGNMENT') || reason.includes('CONFLUENCE')) {
            markers.push({
                time: signalTime,
                position: isLong ? 'belowBar' : 'aboveBar',
                color: isLong ? '#00ff88' : '#ff4444',
                shape: isLong ? 'arrowUp' : 'arrowDown',
                text: 'TRND',
            });
            addModalKey('Trend Alignment', isLong ? '#00ff88' : '#ff4444');
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

    // Get Trade Data from the card's dataset (primary source)
    let trade = {};
    try {
        if (card.dataset.tradeData) {
            trade = JSON.parse(card.dataset.tradeData);
        } else {
            // Fallback: Try copy button
            const copyBtn = card.querySelector('.copy-btn');
            if (copyBtn && copyBtn.dataset.trade) {
                trade = JSON.parse(decodeURIComponent(copyBtn.dataset.trade));
            }
        }
    } catch (e) {
        console.error("Error parsing trade data:", e);
    }

    // Use detailed list if available
    // Priority: 1. Real-time incremental details (dataset.strategyDetails)
    //           2. Backend post-processed details (trade.agreeing_strategies_details)
    //           3. Simple string list (fallback)
    let strategies = [];

    try {
        // First try: Real-time incremental details built on frontend
        if (card.dataset.strategyDetails) {
            strategies = JSON.parse(card.dataset.strategyDetails);
        }
        // Second try: Backend post-processed details (if analysis completed)
        else if (trade.agreeing_strategies_details && Array.isArray(trade.agreeing_strategies_details)) {
            strategies = trade.agreeing_strategies_details;
        }
        // Fallback: Simple string list
        else {
            strategies = trade.agreeing_strategies || JSON.parse(card.dataset.agreeingStrategies || '[]');
        }
    } catch (e) {
        console.error("Error parsing strategies:", e);
        // Ultimate fallback
        strategies = [];
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

    titleEl.innerText = `🤝 ${trade.symbol || symbol} Confluence`;
    subtitleEl.innerText = `${strategies.length} Strategies Aligning`;

    list.innerHTML = '';

    // Helper for formatting prices
    const f = (val) => {
        const n = parseFloat(val);
        if (isNaN(n)) return '0.000000';
        if (n < 0.00001) return n.toFixed(10);
        if (n < 0.01) return n.toFixed(8);
        if (n < 1) return n.toFixed(6);
        return n.toFixed(2);
    };

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

            if (typeof strat === 'string') {
                // Legacy / Simple String View
                item.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: bold; color: #fff;">${strat}</span>
                        <span style="font-size: 0.8em; color: #00ff88;">✅ Active</span>
                    </div>
                `;
            } else {
                // Detailed Object View
                item.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span style="font-weight: bold; color: #fff; display:block;">${strat.strategy}</span>
                            <span style="font-size: 0.8em; color: #888;">${strat.timeframe} • Conf: <span style="color:#00d4ff">${strat.confidence}/10</span></span>
                        </div>
                        <div style="text-align: right; font-family: monospace; font-size: 0.9em; line-height: 1.4;">
                            <div style="color: #aaa;">Entry: <span style="color: #fff;">$${f(strat.entry)}</span></div>
                            <div style="color: #aaa;">TP: <span style="color: #00ff88;">$${f(strat.tp1)}</span></div>
                            <div style="color: #aaa;">SL: <span style="color: #ff4444;">$${f(strat.sl)}</span></div>
                        </div>
                    </div>
                `;
            }
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

// Global Event Delegation for Config Updates
document.addEventListener('change', (e) => {
    if (e.target.closest('#exchangeList')) updateExchangeCount();
    if (e.target.closest('#symbolList')) updateSymbolCount();
    if (e.target.closest('#indicatorList')) updateIndicatorCount();
    if (e.target.closest('#strategyList')) updateStrategyCount();
    if (e.target.closest('#timeframeList')) updateTimeframeCount();
});

// --- Auto Trader Logic ---

function openTraderConfig() {
    document.getElementById('traderModal').style.display = 'flex';
    fetchTraderStatus();
}

function closeTraderConfig() {
    document.getElementById('traderModal').style.display = 'none';
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    // Select specific button based on tab name
    const buttons = document.querySelectorAll('.tab-btn');
    if (tabName === 'keys') buttons[0].classList.add('active');
    if (tabName === 'risk') buttons[1].classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.add('active');
}

function saveKeys() {
    const exch = document.getElementById('keyExchangeSelect').value;
    const key = document.getElementById('apiKeyInput').value;
    const secret = document.getElementById('secretKeyInput').value;

    fetch('/api/trader/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exchange: exch, apiKey: key, secretKey: secret })
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'ok') {
                document.getElementById('keyStatus').innerText = '✅ Keys Saved & Connected!';
                document.getElementById('keyStatus').style.color = '#00ff88';
                fetchTraderStatus();
            } else {
                document.getElementById('keyStatus').innerText = '❌ Error: ' + data.msg;
                document.getElementById('keyStatus').style.color = '#ff4444';
            }
        })
        .catch(e => {
            document.getElementById('keyStatus').innerText = '❌ Network Error';
        });
}


function saveRiskSettings() {
    const type = document.getElementById('riskType').value;
    const value = document.getElementById('riskValue').value;
    const filters = [];
    if (document.getElementById('filterElite').checked) filters.push('ELITE');
    if (document.getElementById('filterStrong').checked) filters.push('STRONG');
    if (document.getElementById('filterStandard').checked) filters.push('STANDARD');

    const autoEnabled = document.getElementById('autoTradeToggle').checked;

    fetch('/api/trader/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            auto_trade_enabled: autoEnabled,
            risk_type: type,
            risk_value: value,
            filters: filters
        })
    })
        .then(r => r.json())
        .then(data => {
            const statusEl = document.getElementById('riskStatus');
            if (statusEl) {
                statusEl.innerText = '✅ Settings Saved!';
                setTimeout(() => statusEl.innerText = '', 3000);
            }
            updateTraderStatusUI(autoEnabled);
        });
}

function toggleAutoTrader() {
    saveRiskSettings(); // Save new toggle state
}

function fetchTraderStatus() {
    fetch('/api/trader/status')
        .then(r => r.json())
        .then(data => {
            document.getElementById('connectedList').innerText = data.connected_exchanges.join(', ') || 'None';
            document.getElementById('autoTradeToggle').checked = data.auto_trade_enabled;

            // Update Risk UI
            if (data.risk_settings) {
                document.getElementById('riskType').value = data.risk_settings.type;
                document.getElementById('riskValue').value = data.risk_settings.value;
            }

            // Update Filters
            if (data.filters) {
                document.getElementById('filterElite').checked = data.filters.includes('ELITE');
                document.getElementById('filterStrong').checked = data.filters.includes('STRONG');
                document.getElementById('filterStandard').checked = data.filters.includes('STANDARD');
            }

            updateTraderStatusUI(data.auto_trade_enabled);
        })
        .catch(e => console.log('Trader status fetch failed', e));
}

function updateTraderStatusUI(enabled) {
    const statusEl = document.getElementById('traderStatus');
    if (statusEl) {
        if (enabled) {
            statusEl.innerHTML = '<span style="color:#00ff88; font-weight:bold;">✅ AUTO-TRADING ACTIVE</span>';
        } else {
            statusEl.innerHTML = '<span style="color:#888;">⏸ PAUSED - Manual Only</span>';
        }
    }
}

function executeManualTrade(btn) {
    if (!confirm("⚠️ Are you sure you want to open a REAL trade?")) return;

    const trade = JSON.parse(decodeURIComponent(btn.getAttribute('data-trade')));
    const originalText = btn.innerText;
    btn.innerText = "⏳ Placing Order...";
    btn.disabled = true;

    fetch('/api/trader/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trade: trade })
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                btn.innerText = "✅ ORDER PLACED";
                btn.style.background = "#00ff88";
                btn.style.color = "#000";
                addTerminalLine(`✅ Manual Trade Executed: ${trade.symbol} | ID: ${data.order.id}`, 'success');
            } else {
                btn.innerText = "❌ FAILED";
                btn.style.background = "#ff4444";
                btn.disabled = false;
                addTerminalLine(`❌ Manual Trade Failed: ${data.msg}`, 'error');
                setTimeout(() => {
                    btn.innerText = originalText;
                    btn.style.background = "";
                    btn.style.color = "";
                }, 3000);
            }
        })
        .catch(e => {
            btn.innerText = "❌ NETWORK ERROR";
            btn.disabled = false;
            setTimeout(() => { btn.innerText = originalText; }, 3000);
        });
}

// Initial fetch
document.addEventListener('DOMContentLoaded', () => {
    fetchTraderStatus();
    checkWhatsAppStatus();
});

// ===== WhatsApp Bridge Logic =====

function openWhatsAppSetup() {
    document.getElementById('whatsappModal').style.display = 'block';
    checkWhatsAppStatus();
}

function closeWhatsAppSetup() {
    document.getElementById('whatsappModal').style.display = 'none';
}

function checkWhatsAppStatus() {
    // Show loading initially
    document.getElementById('wa-loading').style.display = 'block';
    document.getElementById('wa-qr-container').style.display = 'none';
    document.getElementById('wa-connected').style.display = 'none';
    document.getElementById('wa-error').style.display = 'none';

    fetch('/api/whatsapp/status')
        .then(r => r.json())
        .then(data => {
            updateWhatsAppUI(data.status, data.qr);
        })
        .catch(e => {
            console.error('WhatsApp status check failed', e);
            document.getElementById('wa-loading').style.display = 'none';
            document.getElementById('wa-error').style.display = 'block';
        });
}

function updateWhatsAppUI(status, qr = null) {
    document.getElementById('wa-loading').style.display = 'none';

    const sidebarStatus = document.getElementById('whatsappStatusSidebar');

    if (status === 'READY') {
        document.getElementById('wa-connected').style.display = 'block';
        document.getElementById('wa-qr-container').style.display = 'none';

        if (sidebarStatus) {
            sidebarStatus.innerHTML = '<span style="color:#25d366; font-weight:bold;">● Connected</span>';
        }

        // Load current config if available
        fetch('/api/config')
            .then(r => r.json())
            .then(config => {
                if (config.whatsapp_chat_id) {
                    document.getElementById('waChatId').value = config.whatsapp_chat_id;
                    document.getElementById('waChatId').style.color = '#fff';
                }
                if (config.whatsapp_quality) {
                    document.getElementById('waQualitySelect').value = config.whatsapp_quality;
                }
            });

    } else if (status === 'SCAN_REQUIRED' || qr) {
        document.getElementById('wa-qr-container').style.display = 'block';
        document.getElementById('wa-connected').style.display = 'none';

        if (qr) {
            const qrImg = document.getElementById('wa-qr-image');
            qrImg.innerHTML = `<img src="${qr}" style="width: 256px; height: 256px;">`;
        }

        if (sidebarStatus) {
            sidebarStatus.innerHTML = '<span style="color:#ffaa00;">● Scan Required</span>';
        }
    } else {
        document.getElementById('wa-loading').style.display = 'block';
        if (sidebarStatus) {
            sidebarStatus.innerHTML = '<span style="color:#888;">● Initializing...</span>';
        }
    }
}

function updateWhatsAppConfig() {
    const quality = document.getElementById('waQualitySelect').value;
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            whatsapp_quality: quality
        })
    });
}

function logoutWhatsApp() {
    if (!confirm('Are you sure you want to log out from WhatsApp? This will terminate the connection and clear all saved session data.')) return;

    // Show loading
    document.getElementById('wa-loading').style.display = 'block';
    document.getElementById('wa-connected').style.display = 'none';

    fetch('/api/whatsapp/logout', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'ok') {
                alert('WhatsApp successfully logged out. The bridge will restart shortly for a fresh scan.');
                checkWhatsAppStatus();
            } else {
                alert('Error logging out: ' + data.msg);
                checkWhatsAppStatus();
            }
        })
        .catch(e => {
            console.error('Logout failed', e);
            alert('Logout request failed. Please check server logs.');
            checkWhatsAppStatus();
        });
}

// Socket.IO Events for WhatsApp
socket.on('whatsapp_qr', (data) => {
    console.log('📱 WhatsApp QR Received');
    updateWhatsAppUI('SCAN_REQUIRED', data.qr);
});

socket.on('whatsapp_status', (data) => {
    console.log('📱 WhatsApp Status:', data.status);
    updateWhatsAppUI(data.status);

    // If it just became ready, update the chat ID input if we have one
    if (status === 'READY') {
        fetch('/api/config').then(r => r.json()).then(c => {
            if (c.whatsapp_chat_id) document.getElementById('waChatId').value = c.whatsapp_chat_id;
        });
    }
});

// Auto-Sync Chat ID from Server-side update
socket.on('config_updated', (config) => {
    if (config.whatsapp_chat_id) {
        const input = document.getElementById('waChatId');
        if (input) {
            input.value = config.whatsapp_chat_id;
            input.style.color = '#fff';
        }
    }
});
// --- Local Storage Logic for Sensitive Credentials (Privacy/Security) ---
function updateTelegramConfig() {
    const token = document.getElementById('tgToken').value;
    const chatId = document.getElementById('tgChatId').value;

    localStorage.setItem('rbot_tg_token', token);
    localStorage.setItem('rbot_tg_chat_id', chatId);

    socket.emit('update_config', {
        telegram_token: token,
        telegram_chat_id: chatId
    });
}

function updateWhatsAppConfig() {
    const chatId = document.getElementById('waChatId').value;
    const quality = document.getElementById('waQualitySelect').value;

    if (chatId) localStorage.setItem('rbot_wa_chat_id', chatId);
    localStorage.setItem('rbot_wa_quality', quality);

    socket.emit('update_config', {
        whatsapp_chat_id: chatId,
        whatsapp_quality: quality
    });
}

function syncCredentialsToServer() {
    // Collect all stored credentials
    const credentials = {
        telegram_token: localStorage.getItem('rbot_tg_token') || '',
        telegram_chat_id: localStorage.getItem('rbot_tg_chat_id') || '',
        whatsapp_chat_id: localStorage.getItem('rbot_wa_chat_id') || '',
        whatsapp_quality: localStorage.getItem('rbot_wa_quality') || 'ELITE',
        // Exchange keys are handled via specialized API but can be synced here too for memory-only persistence
        exchange_keys: JSON.parse(localStorage.getItem('rbot_exchange_keys') || '{}')
    };

    socket.emit('update_config', credentials);
    console.log("🔐 Credentials synced to bot memory from browser storage.");
}

// Load Config on Startup
document.addEventListener('DOMContentLoaded', () => {
    // Telegram
    const savedToken = localStorage.getItem('rbot_tg_token');
    const savedChatId = localStorage.getItem('rbot_tg_chat_id');
    if (savedToken) document.getElementById('tgToken').value = savedToken;
    if (savedChatId) document.getElementById('tgChatId').value = savedChatId;

    // WhatsApp
    const savedWaChatId = localStorage.getItem('rbot_wa_chat_id');
    const savedWaQuality = localStorage.getItem('rbot_wa_quality');
    if (savedWaChatId) document.getElementById('waChatId').value = savedWaChatId;
    if (savedWaQuality) document.getElementById('waQualitySelect').value = savedWaQuality;

    // Push everything to server when socket connects
    socket.on('connect', () => {
        syncCredentialsToServer();
    });

    // Handle updates from server (e.g. auto-synced WhatsApp ID)
    socket.on('config_updated', (newConfig) => {
        if (newConfig.whatsapp_chat_id) {
            localStorage.setItem('rbot_wa_chat_id', newConfig.whatsapp_chat_id);
            if (document.getElementById('waChatId')) {
                document.getElementById('waChatId').value = newConfig.whatsapp_chat_id;
            }
        }
    });
});
