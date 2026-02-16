#!/usr/bin/env node
// api-server.js — Family Hub local API server
// Receives JSON data, saves to files, syncs to GitHub
// Usage: node api-server.js

const http = require('http');
const fs   = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const PORT      = 4747;
const DATA_DIR  = path.join(__dirname, 'data');
const SYNC_SH   = path.join(__dirname, 'sync_data.sh');
const ARGOS_KEY = "argos-secret-2026"; // Simple authentication key

const ALLOWED = {
  'acoes':         'acoes.json',
  'acoes_pessoas': 'acoes_pessoas.json',
  'acoes_imoveis': 'acoes_imoveis.json',
  'compras':       'compras.json',
  'lancamentos':   'lancamentos.json',
  'receitas':      'receitas.json',
  'viagem':        'viagem.json',
};

function cors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Argos-Key');
}

function ok(res, body) {
  cors(res);
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(body));
}

function err(res, code, msg) {
  cors(res);
  res.writeHead(code, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: msg }));
}

function runSync() {
  try {
    if (fs.existsSync(SYNC_SH)) {
      execSync(`bash "${SYNC_SH}"`, { timeout: 30000 });
      return true;
    }
    return false;
  } catch (e) {
    console.error('Sync error:', e.message);
    return false;
  }
}

const server = http.createServer((req, res) => {
  cors(res);

  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  const url = req.url.split('?')[0];

  // Auth Check for POST
  if (req.method === 'POST') {
    const key = req.headers['x-argos-key'];
    if (key !== ARGOS_KEY) {
      return err(res, 401, 'Unauthorized');
    }
  }

  // GET /ping — health check
  if (req.method === 'GET' && url === '/ping') {
    return ok(res, { ok: true, port: PORT });
  }

  // POST /sync-granular
  if (req.method === 'POST' && url === '/sync-granular') {
    let body = '';
    req.on('data', d => body += d);
    req.on('end', () => {
      try {
        const payload = JSON.parse(body);
        const { type, id, data } = payload;
        
        const filename = ALLOWED[type];
        if (!filename) return err(res, 400, `Type '${type}' not allowed`);

        const filePath = path.join(DATA_DIR, filename);
        let currentData = [];
        
        if (fs.existsSync(filePath)) {
          currentData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        }

        if (data && data._deleted) {
          // Deletion
          currentData = currentData.filter(item => item.id !== id);
        } else {
          // Apply granular update (patch)
          const index = currentData.findIndex(item => item.id === id);
          if (index !== -1) {
            currentData[index] = { ...currentData[index], ...data };
          } else {
            currentData.push({ id, ...data });
          }
        }

        fs.writeFileSync(filePath, JSON.stringify(currentData, null, 2), 'utf8');
        const synced = runSync();
        
        return ok(res, { success: true, synced });
      } catch (e) {
        return err(res, 400, 'Invalid JSON or Error: ' + e.message);
      }
    });
    return;
  }

  // POST /save/:dataset (legacy/bulk support)
  if (req.method === 'POST' && url.startsWith('/save/')) {
    const dataset = url.replace('/save/', '').replace(/\//g, '');
    const filename = ALLOWED[dataset];
    if (!filename) return err(res, 400, `Dataset '${dataset}' not allowed`);

    let body = '';
    req.on('data', d => body += d);
    req.on('end', () => {
      try {
        const data = JSON.parse(body);
        const filePath = path.join(DATA_DIR, filename);
        fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
        const synced = runSync();
        return ok(res, { saved: true, synced });
      } catch (e) {
        return err(res, 400, 'Invalid JSON: ' + e.message);
      }
    });
    return;
  }

  err(res, 404, 'Not found');
});

// Listen on all interfaces so it's accessible from LAN
server.listen(PORT, '0.0.0.0', () => {
  console.log(`✅ Family Hub API running on http://0.0.0.0:${PORT}`);
});

server.on('error', e => {
  if (e.code === 'EADDRINUSE') {
    console.error(`❌ Port ${PORT} already in use.`);
  } else {
    console.error('Server error:', e);
  }
  process.exit(1);
});
