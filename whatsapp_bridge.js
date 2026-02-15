const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const QRCode = require('qrcode');
const axios = require('axios');

// Configuration
const FLASK_SERVER_URL = 'http://localhost:5000/api/whatsapp/message';
const QR_API_URL = 'http://localhost:5000/api/whatsapp/qr';

const fs = require('fs');

// Auto-detect Chrome Path
let chromePath = undefined;
const possiblePaths = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'.replace('Program Files', 'Program Files (x86)') // Fallback
];

for (const path of possiblePaths) {
    if (fs.existsSync(path)) {
        chromePath = path;
        console.log(`✅ Found System Chrome: ${chromePath}`);
        break;
    }
}

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        executablePath: chromePath, // Use system Chrome if found
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ],
        headless: true
    }
});

console.log('🚀 Starting RBot WhatsApp Bridge...');

client.on('qr', async (qr) => {
    // 1. Show in terminal
    qrcode.generate(qr, { small: true });
    console.log('📸 Scan the QR code above to link WhatsApp.');

    // 2. Generate Base64 for the Web UI
    try {
        const qrBase64 = await QRCode.toDataURL(qr);
        await axios.post(QR_API_URL, {
            qr: qrBase64,
            status: 'SCAN_REQUIRED'
        });
    } catch (err) {
        console.error('❌ Failed to send QR to Flask:', err.message);
    }
});

client.on('authenticated', () => {
    console.log('✅ WhatsApp Authenticated!');
    axios.post(QR_API_URL, { status: 'INITIALIZING' }).catch(() => { });
});

client.on('auth_failure', msg => {
    console.error('❌ WhatsApp Authentication failure', msg);
    axios.post(QR_API_URL, { status: 'ERROR', message: msg }).catch(() => { });
});

client.on('ready', () => {
    console.log('✅ WhatsApp Client is READY!');
    axios.post(QR_API_URL, { status: 'READY' }).catch(() => { });
});

client.on('disconnected', (reason) => {
    console.log('❌ WhatsApp Disconnected:', reason);
    axios.post(QR_API_URL, { status: 'DISCONNECTED' }).catch(() => { });
});

client.on('message', async (msg) => {
    const text = msg.body.trim();
    if (!text.startsWith('/')) return;

    console.log(`📩 Received Command: ${text} from ${msg.from}`);

    try {
        // Forward command to Python Backend
        const response = await axios.post(FLASK_SERVER_URL, {
            text: text,
            from: msg.from,
            author: msg.author || msg.from,
            isGroup: msg.from.endsWith('@g.us'),
            messenger: 'whatsapp'
        });

        if (response.data && response.data.reply) {
            msg.reply(response.data.reply);
        }
    } catch (err) {
        console.error('❌ Backend Error:', err.message);
        // Don't spam reply on network errors unless it's a command
        if (text.startsWith('/')) {
            msg.reply('⚠ Error communicating with bot engine.');
        }
    }
});

// Endpoint for Python to send messages OUT (Alerts/Trades)
const express = require('express');
const app = express();
app.use(express.json());

app.post('/send', async (req, res) => {
    const { to, message } = req.body;
    if (!to || !message) return res.status(400).send('Missing params');

    try {
        await client.sendMessage(to, message);
        res.send({ success: true });
    } catch (err) {
        console.error(`❌ Failed to send message to ${to}:`, err.message);
        res.status(500).send({ error: err.message });
    }
});

const PORT = 3001;
app.listen(PORT, () => {
    console.log(`🌐 WhatsApp Web Bridge listening on port ${PORT}`);
});

// Global crash protection for initialize
try {
    client.initialize();
} catch (e) {
    console.error('❌ CRITICAL: Failed to initialize WhatsApp client:', e);
    axios.post(QR_API_URL, { status: 'ERROR', message: e.message }).catch(() => { });
}
