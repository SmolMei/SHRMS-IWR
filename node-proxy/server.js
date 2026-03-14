/**
 * IWR Node.js Proxy (Option B)
 *
 * Sits between Smart-HRMS and the Python FastAPI service.
 * Smart-HRMS calls this proxy on port 3000; this proxy forwards
 * requests to the Python IWR API on port 8000, attaching the API key.
 *
 * Usage:
 *   cd node-proxy && npm install && npm run dev
 *
 * Required env vars (copy .env.example → .env in node-proxy/):
 *   IWR_API_URL    - base URL of the Python API  (default: http://127.0.0.1:8000)
 *   IWR_API_KEY    - secret key for the Python API
 *   PROXY_PORT     - port this proxy listens on   (default: 3000)
 */

require('dotenv').config();
const express = require('express');
const axios   = require('axios');

const app = express();
app.use(express.json());

const IWR_API_URL = process.env.IWR_API_URL || 'http://127.0.0.1:8000';
const IWR_API_KEY = process.env.IWR_API_KEY;
const PORT        = process.env.PROXY_PORT  || 3000;

if (!IWR_API_KEY) {
  console.error('ERROR: IWR_API_KEY is not set. Copy .env.example to .env and fill it in.');
  process.exit(1);
}

// Shared headers attached to every request forwarded to the Python API
const iwr_headers = {
  'Content-Type': 'application/json',
  'X-API-Key': IWR_API_KEY,
};

// ── Health ──────────────────────────────────────────────────────────────────
// Checks both this proxy AND the Python API are alive.
app.get('/api/health', async (req, res) => {
  try {
    const { data } = await axios.get(`${IWR_API_URL}/api/health`);
    res.json({ proxy: 'ok', iwr: data });
  } catch (err) {
    res.status(502).json({ proxy: 'ok', iwr: 'unreachable', error: err.message });
  }
});

// ── IPCR routing ─────────────────────────────────────────────────────────────
app.post('/api/ipcr/route', async (req, res) => {
  try {
    const { data } = await axios.post(`${IWR_API_URL}/api/ipcr/route`, req.body, { headers: iwr_headers });
    res.json(data);
  } catch (err) {
    forwardError(err, res);
  }
});

// ── Leave routing ─────────────────────────────────────────────────────────────
app.post('/api/leave/route', async (req, res) => {
  try {
    const { data } = await axios.post(`${IWR_API_URL}/api/leave/route`, req.body, { headers: iwr_headers });
    res.json(data);
  } catch (err) {
    forwardError(err, res);
  }
});

// ── Error helper ─────────────────────────────────────────────────────────────
function forwardError(err, res) {
  if (err.response) {
    // Python API returned an error (e.g. 422 validation, 403 auth)
    res.status(err.response.status).json(err.response.data);
  } else {
    // Network error — Python API is down
    res.status(502).json({ error: 'IWR Python API is unreachable', detail: err.message });
  }
}

app.listen(PORT, () => {
  console.log(`IWR Node proxy running on http://localhost:${PORT}`);
  console.log(`Forwarding to Python IWR API at ${IWR_API_URL}`);
});
