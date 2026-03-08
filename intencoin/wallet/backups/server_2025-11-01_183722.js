const express = require('express');
const fs = require('fs');
const path = require('path');
const { randomUUID } = require('crypto');

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// --------- Config ----------
const PORT = process.env.PORT || 3000;
const DEPOSIT_SECRET = process.env.DEPOSIT_SHARED_SECRET || process.env.DEPOSIT_SECRET || 'letmein';
const PYTHON_RECEIVE_URL = process.env.PYTHON_RECEIVE_URL || 'http://127.0.0.1:8083/public_receive';

// --------- Archivos de datos ----------
const DATA_DIR = path.join(__dirname, 'data');
const USERS = path.join(DATA_DIR, 'users.json');
const ADDRS = path.join(DATA_DIR, 'addresses.json');
const TXS   = path.join(DATA_DIR, 'transactions.json');

function ensureFiles() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  if (!fs.existsSync(USERS)) fs.writeFileSync(USERS, JSON.stringify({}, null, 2));
  if (!fs.existsSync(ADDRS)) fs.writeFileSync(ADDRS, JSON.stringify({}, null, 2));
  if (!fs.existsSync(TXS))   fs.writeFileSync(TXS,   JSON.stringify([], null, 2));
}
function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8') || (p===TXS?'[]':'{}')); }
  catch { return p===TXS ? [] : {}; }
}
function writeJson(p, v) { fs.writeFileSync(p, JSON.stringify(v, null, 2)); }

ensureFiles();

// --------- Estáticos (/ y /index.html) ----------
app.use(express.static(path.join(__dirname, 'static')));
app.get('/', (req, res) => res.sendFile(path.join(__dirname, 'static', 'index.html')));

// --------- API pública ----------

// 1) Registrar/afiliar una dirección pública a un usuario
app.post('/public/register_address', (req, res) => {
  try {
    ensureFiles();
    const { user_id, account_no, email, address } = req.body || {};
    if (!user_id || !address) return res.status(400).json({ error: 'params' });

    const users = readJson(USERS);
    const amap  = readJson(ADDRS);

    if (!users[user_id]) {
      users[user_id] = {
        id: user_id,
        email: (email||'').toLowerCase(),
        account_no: account_no || user_id,
        balance: Number(users[user_id]?.balance || 0)
      };
    }
    amap[address] = user_id;

    writeJson(USERS, users);
    writeJson(ADDRS, amap);

    return res.json({
      ok: true,
      user_id,
      address,
      account_no: users[user_id].account_no,
      balance: users[user_id].balance || 0
    });
  } catch (e) {
    console.error('public/register_address error:', e);
    return res.status(500).json({ error: 'server', detail: String(e) });
  }
});

// 2) Consultar balance por address
app.get('/public/balance', (req, res) => {
  try {
    ensureFiles();
    const address = (req.query.address || '').toString().trim();
    if (!address) return res.status(400).json({ error: 'address missing' });

    const users = readJson(USERS);
    const amap  = readJson(ADDRS);
    const uid = amap[address];
    if (!uid || !users[uid]) return res.status(404).json({ error: 'address not found' });

    const u = users[uid];
    return res.json({ address, account_no: u.account_no || uid, balance: Number(u.balance || 0) });
  } catch (e) {
    console.error('public/balance error:', e);
    return res.status(500).json({ error: 'server', detail: String(e) });
  }
});

// 3) Depósito (webhook entrante) — requiere secreto
app.post('/public/deposit', (req, res) => {
  try {
    ensureFiles();
    const secretHeader = (req.headers['x-deposit-secret'] || '').toString();
    if (secretHeader !== DEPOSIT_SECRET) return res.status(403).json({ error: 'forbidden' });

    const { address, amount, note } = req.body || {};
    const a = Number(amount || 0);
    if (!address || !(a > 0)) return res.status(400).json({ error: 'params' });

    const users = readJson(USERS);
    const amap  = readJson(ADDRS);
    const txs   = readJson(TXS);

    const uid = amap[address];
    if (!uid || !users[uid]) return res.status(404).json({ error: 'address not found' });

    users[uid].balance = Number(users[uid].balance || 0) + a;
    const id = randomUUID(), now = Date.now();
    txs.push({ id, user_id: uid, type: 'deposit', amount: a, balance_after: users[uid].balance, note: note || 'deposit', created_at: now });

    writeJson(USERS, users);
    writeJson(TXS, txs);

    return res.json({ ok: true, address, balance: users[uid].balance, tx_id: id });
  } catch (e) {
    console.error('public/deposit error:', e);
    return res.status(500).json({ error: 'server', detail: String(e) });
  }
});

// 4) Retiro (salida hacia Python) — requiere secreto
app.post('/public/withdraw', async (req, res) => {
  try {
    ensureFiles();
    const secretHeader = (req.headers['x-deposit-secret'] || '').toString();
    if (secretHeader !== DEPOSIT_SECRET) return res.status(403).json({ error: 'forbidden' });

    const { address, amount, to, note } = req.body || {};
    const a = Number(amount || 0);
    if (!address || !(a > 0)) return res.status(400).json({ error: 'params' });

    const users = readJson(USERS);
    const amap  = readJson(ADDRS);
    const txs   = readJson(TXS);

    const uid = amap[address];
    if (!uid || !users[uid]) return res.status(404).json({ error: 'address not found' });

    const bal = Number(users[uid].balance || 0);
    if (bal < a) return res.status(400).json({ error: 'insufficient' });

    const newBal = +(bal - a).toFixed(6);
    users[uid].balance = newBal;

    const id = randomUUID(), now = Date.now();
    txs.push({
      id, user_id: uid, type: 'withdraw', amount: -a,
      balance_after: newBal, note: `to ${to||'external'}${note ? ' - '+note : ''}`, created_at: now
    });

    // Persistir descuento antes de reenviar
    writeJson(USERS, users);
    writeJson(TXS, txs);

    // Reenviar a Python (best-effort)
    try {
      const resp = await fetch(PYTHON_RECEIVE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: to, amount: a, note: note || 'from Node' })
      });
      const txt = await resp.text();
      console.log('[WITHDRAW] node->py', resp.status, txt);
    } catch (e) {
      console.error('[WITHDRAW] node->py ERROR', e);
    }

    return res.json({ ok: true, address, balance: newBal, tx_id: id });
  } catch (e) {
    console.error('public/withdraw error:', e);
    return res.status(500).json({ error: 'server', detail: String(e) });
  }
});

// (Opcional) Stubs usados en pruebas
app.get('/get_balance', (req,res)=> res.json({ balance: 4477 }));
app.post('/convert', (req,res)=> res.json({ rate: 0.5 }));

// --------- Listen único ----------
app.listen(PORT, () => console.log('INTEN Wallet listening on', PORT));
