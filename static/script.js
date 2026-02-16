// WebSocket connection and UI handling for RBot Pro Analysis UI

// Detect environment to handle Vercel's lack of WebSocket support
const isVercelEnv = typeof window.IS_VERCEL !== 'undefined' ? window.IS_VERCEL : window.location.hostname.includes('vercel.app');

const socket = io({
    reconnection: true,
    reconnectionDelay: isVercelEnv ? 1500 : 1000,
    reconnectionDelayMax: isVercelEnv ? 7000 : 5000,
    reconnectionAttempts: Infinity,
    transports: isVercelEnv ? ['polling'] : ['polling', 'websocket'],
    upgrade: !isVercelEnv,
    timeout: isVercelEnv ? 30000 : 20000,
    closeOnBeforeunload: false
});
let lineCount = 0;
let startTime = null;
let timerInterval = null;
let isAnalysisRunning = false;

// Connect event
socket.on('connect', function () {
    updateStatus('Connected', 'connected');
    console.log('Connected to server');
    window.wasDisconnectedEnv = false;
});

// Disconnect event
socket.on('disconnect', function (reason) {
    if (!window.wasDisconnectedEnv) {
        updateStatus('Reconnecting...', 'warning');
        console.log('Disconnected:', reason);
        window.wasDisconnectedEnv = true;
    }
});

socket.on('connect_error', (error) => {
    console.warn('Connection Warning:', error.message);
    if (!isVercelEnv) {
        updateStatus('Connecting...', 'warning');
    }
});

// Receive output
socket.on('output', function (data) {
    if (data.data) {
        addOutputLine(data.data);
    }
});

// Receive status updates
socket.on('status', function (data) {
    if (data.status === 'started') {
        isAnalysisRunning = true;
        document.getElementById('startBtn').disabled = true;
        updateStatus('Running Analysis', 'running');
        startTimer();
    } else if (data.status === 'completed') {
        isAnalysisRunning = false;
        document.getElementById('startBtn').disabled = false;
        updateStatus('Analysis Complete', 'connected');
        stopTimer();
        addOutputLine('✓ Analysis completed successfully\n');
    } else if (data.status === 'error') {
        isAnalysisRunning = false;
        document.getElementById('startBtn').disabled = false;
        updateStatus('Error', 'disconnected');
        stopTimer();
    }
});

// Clear output event
socket.on('clear', function () {
    const terminal = document.getElementById('terminal');
    terminal.innerHTML = '';
    lineCount = 0;
    document.getElementById('lineCount').textContent = '0';
});

// Add line to output
function addOutputLine(text) {
    const terminal = document.getElementById('terminal');

    // Split by newline and add each line
    const lines = text.split('\n');

    lines.forEach(line => {
        if (line.trim()) {
            const outputLine = document.createElement('div');
            outputLine.className = 'output-line';

            // Detect line type by content
            if (line.includes('ERROR') || line.includes('Error')) {
                outputLine.classList.add('error');
            } else if (line.includes('TRADE FOUND') || line.includes('✓') || line.includes('✅')) {
                outputLine.classList.add('success');
            } else if (line.includes('⚠') || line.includes('warning')) {
                outputLine.classList.add('warning');
            }

            const prompt = document.createElement('span');
            prompt.className = 'prompt';
            prompt.textContent = '$';

            const text_span = document.createElement('span');
            text_span.className = 'text';
            text_span.textContent = line;

            outputLine.appendChild(prompt);
            outputLine.appendChild(text_span);
            terminal.appendChild(outputLine);

            lineCount++;
        }
    });

    // Update line count
    document.getElementById('lineCount').textContent = lineCount;

    // Auto-scroll to bottom
    terminal.scrollTop = terminal.scrollHeight;
}

// Start analysis
function startAnalysis() {
    if (isAnalysisRunning) {
        addOutputLine('⚠ Analysis is already running!\n');
        return;
    }

    addOutputLine(`\n>>> Analysis started at ${new Date().toLocaleTimeString()}\n`);
    socket.emit('start_analysis');
}

// Clear output
function clearOutput() {
    socket.emit('clear_output');
    addOutputLine('>>> Output cleared\n');
}

// Update status indicator
function updateStatus(text, status) {
    const statusText = document.getElementById('statusText');
    const statusDot = document.querySelector('.status-dot');

    statusText.textContent = text;
    statusDot.className = 'status-dot ' + status;
}

// Timer functions
function startTimer() {
    startTime = Date.now();
    timerInterval = setInterval(updateTimer, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
    }
}

function updateTimer() {
    if (!startTime) return;

    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;

    const timeString =
        String(hours).padStart(2, '0') + ':' +
        String(minutes).padStart(2, '0') + ':' +
        String(seconds).padStart(2, '0');

    document.getElementById('elapsedTime').textContent = timeString;
}

// Keyboard shortcuts
document.addEventListener('keydown', function (event) {
    // Ctrl+Enter to start analysis
    if (event.ctrlKey && event.key === 'Enter') {
        startAnalysis();
    }
    // Ctrl+L to clear output
    if (event.ctrlKey && event.key === 'l') {
        event.preventDefault();
        clearOutput();
    }
});

// Initial message
document.addEventListener('DOMContentLoaded', function () {
    addOutputLine('>>> System ready. Press "Start Analysis" or Ctrl+Enter to begin\n');
    addOutputLine('>>> Use Ctrl+L to clear output\n');
});
