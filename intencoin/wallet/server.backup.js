require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const initSqlJs = require('sql.js');
let db;
let __dbReady = (async () => {
  const SQL = await initSqlJs();
  db = new SQL.Database();
  console.log("✅ SQLite (sql.js) listo");
  return true;
})();
async function waitDb(){ if(!db) await __dbReady; }
let db;
(async () => {
  const SQL = await initSqlJs();
  db = new SQL.Database();
  console.log('✅ SQLite (sql.js) inicializado en memoria');
})();

const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'change_me';
const ADMIN_API_KEY = process.env.ADMIN_API_KEY || 'admin_key';
const SITE_TITLE = process.env.SITE_TITLE || 'INTENCOIN';
const DB_FILE = process.env.DATABASE_FILE || './db.sqlite';

const app = express();
app.use(cors());
app.use(bodyParser.json());

// === DB init
// TODO: move to initSchema -> db.prepare(`
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE,
  name TEXT,
  password_hash TEXT,
  account_no TEXT,
  balance REAL DEFAULT 0,
  created_at INTEGER
)`).run();

// TODO: move to initSchema -> db.prepare(`
CREATE TABLE IF NOT EXISTS transactions (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  type TEXT,
  amount REAL,
  balance_after REAL,
  note TEXT,
  created_at INTEGER
)`).run();

// TODO: move to initSchema -> db.prepare(`
CREATE TABLE IF NOT EXISTS wallets (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  account_index INTEGER,
  deposit_address TEXT,
  created_at INTEGER
)`).run();

// === helpers
function sign(uid, email) { return jwt.sign({ uid, email }, JWT_SECRET, { expiresIn: '7d' }); }
function auth(req,res,next){
  const a = req.headers.authorization || '';
  if (!a.startsWith('Bearer ')) return res.status(401).json({ error: 'unauthorized' });
  try { req.user = jwt.verify(a.slice(7), JWT_SECRET); return next(); }
  catch(e){ return res.status(401).json({ error:'unauthorized' }); }
}

// === HTML (UNA SOLA PÁGINA)
const HTML = `<!doctype html>
<html><head>
<meta charset="utf-8">
<title>${SITE_TITLE}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root{--bg:#0f1220;--card:#151a38;--line:#232a61;--muted:#9aa0d0;--ink:#eaf0ff}
  body{font-family:system-ui,Segoe UI,Arial;margin:0;background:var(--bg);color:#fff}
  header{display:flex;gap:16px;align-items:center;padding:16px 20px;background:#141834;border-bottom:1px solid #222757}
  .logo{width:56px;height:56px;border:2px dashed #2f3560;border-radius:12px;display:flex;align-items:center;justify-content:center;color:#9aa0d0}
  main{max-width:960px;margin:20px auto;padding:0 16px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin:12px 0}
  input,button{padding:10px;border-radius:10px;border:1px solid #2a3369;background:#0f1330;color:var(--ink)}
  button{cursor:pointer}
  .row{display:flex;gap:8px;flex-wrap:wrap}
  .muted{color:var(--muted)}
  pre{white-space:pre-wrap}
  .ok{color:#7CFC7C}.err{color:#ff8989}
</style>
</head>
<body>
<header>
  <div class="logo">IC</div>
  <div>
    <div style="font-size:20px;font-weight:700">${SITE_TITLE}</div>
    <div class="muted">Unified UI (HTML + Server)</div>
  </div>
</header>
<main>
  <div class="card">
    <h3>Register</h3>
    <div class="row">
      <input id="r_name" placeholder="Name (optional)">
      <input id="r_email" placeholder="Email">
      <input id="r_pass" type="password" placeholder="Password">
      <button id="btn_reg">Create</button>
    </div>
    <div id="r_out" class="muted"></div>
  </div>

  <div class="card">
    <h3>Login</h3>
    <div class="row">
      <input id="l_email" placeholder="Email">
      <input id="l_pass" type="password" placeholder="Password">
      <button id="btn_login">Login</button>
      <button id="btn_logout">Logout</button>
    </div>
    <div id="l_out" class="muted"></div>
  </div>

  <div class="card">
    <h3>Account</h3>
    <div class="row">
      <button id="btn_balance">Balance</button>
      <span id="bal" class="muted"></span>
    </div>
    <div class="row" style="margin-top:8px">
      <button id="btn_wallet">Create Wallet Address</button>
      <span id="addr" class="muted"></span>
    </div>
    <div class="row" style="margin-top:8px">
      <input id="to_email" placeholder="Send to (email)">
      <input id="amt" placeholder="Amount">
      <button id="btn_transfer">Transfer</button>
    </div>
    <div class="row" style="margin-top:8px">
      <input id="ext" placeholder="External address">
      <input id="wamt" placeholder="Amount">
      <button id="btn_withdraw">Withdraw</button>
    </div>
    <div id="a_out" class="muted" style="margin-top:6px"></div>
  </div>

  <div class="card">
    <h3>Transactions</h3>
    <button id="btn_txs">Refresh</button>
    <pre id="txs"></pre>
  </div>
</main>

<script>
const $ = (id)=>document.getElementById(id);
function setMsg(id, data, ok){ $(id).innerHTML = '<span class="'+(ok?'ok':'err')+'">'+(typeof data==='string'?data:JSON.stringify(data,null,2))+'</span>'; }

function tokenGet(){ return localStorage.getItem('token')||null; }
function tokenSet(t){ if(t){ localStorage.setItem('token', t); } }
function tokenClear(){ localStorage.removeItem('token'); }

async function api(path, method='GET', body=null, needAuth=false){
  const headers = {'Content-Type':'application/json'};
  if(needAuth){
    const t = tokenGet();
    if(!t) return { error:'unauthorized', hint:'no token in localStorage' };
    headers['Authorization'] = 'Bearer '+t;
  }
  let res, txt;
  try{
    res = await fetch(path, {method, headers, body: body?JSON.stringify(body):null});
    txt = await res.text();
  }catch(e){
    return { error:'network', detail:String(e) };
  }
  try { return JSON.parse(txt); } catch(e){ return { error:'non-json', status:res && res.status, text:txt }; }
}

// UI handlers
$('btn_reg').onclick = async ()=>{
  const out = await api('/auth/register','POST',{
    name: $('r_name').value, email: $('r_email').value, password: $('r_pass').value
  }, false);
  setMsg('r_out', out, !out.error);
  if(out && out.token) tokenSet(out.token);
};

$('btn_login').onclick = async ()=>{
  const out = await api('/auth/login','POST',{
    email: $('l_email').value, password: $('l_pass').value
  }, false);
  setMsg('l_out', out, !out.error);
  if(out && out.token) tokenSet(out.token);
};

$('btn_logout').onclick = ()=>{
  tokenClear();
  setMsg('l_out', 'Logged out (token cleared)', true);
};

$('btn_balance').onclick = async ()=>{
  const out = await api('/api/balance','GET',null,true);
  $('bal').textContent = JSON.stringify(out);
  if(out && out.error) setMsg('a_out', out, false);
};

$('btn_wallet').onclick = async ()=>{
  const out = await api('/api/wallet/create','POST',{},true);
  $('addr').textContent = JSON.stringify(out);
  if(out && out.error) setMsg('a_out', out, false);
};

$('btn_transfer').onclick = async ()=>{
  const out = await api('/api/transfer','POST',{
    toEmail: $('to_email').value, amount: parseFloat($('amt').value||'0')
  }, true);
  setMsg('a_out', out, !out.error);
};

$('btn_withdraw').onclick = async ()=>{
  const out = await api('/api/withdraw-request','POST',{
    external_address: $('ext').value, amount: parseFloat($('wamt').value||'0')
  }, true);
  setMsg('a_out', out, !out.error);
};

$('btn_txs').onclick = async ()=>{
  const out = await api('/api/transactions','GET',null,true);
  $('txs').textContent = JSON.stringify(out,null,2);
  if(out && out.error) setMsg('a_out', out, false);
};

// Pequeño ping de balance al abrir si hay token
if(tokenGet()){ $('btn_balance').click(); }
</script>
</body></html>`;

// === RUTAS
app.get('/', (req,res)=> res.status(200).send(HTML));

// Auth
app.post('/auth/register', async (req,res)=>{
  const { email, password, name } = req.body || {};
  if(!email || !password) return res.status(400).json({ error:'email/password' });
  const exists = db.prepare('SELECT id FROM users WHERE email=?').get(String(email).toLowerCase());
  if(exists) return res.status(400).json({ error:'exists' });
  const id = uuidv4();
  const hash = await bcrypt.hash(password, 10);
  const acc = `INTEN-${id.slice(0,8).toUpperCase()}`;
  db.prepare('INSERT INTO users (id,email,name,password_hash,account_no,created_at) VALUES (?,?,?,?,?,?)')
    .run(id, String(email).toLowerCase(), name||null, hash, acc, Date.now());
  return res.json({ ok:true, token:sign(id,String(email).toLowerCase()), id, email:String(email).toLowerCase(), account_no:acc, site:SITE_TITLE });
});

app.post('/auth/login', async (req,res)=>{
  const { email, password } = req.body || {};
  const row = db.prepare('SELECT * FROM users WHERE email=?').get(String(email||'').toLowerCase());
  if(!row) return res.status(400).json({ error:'invalid' });
  const ok  = await bcrypt.compare(String(password||''), row.password_hash||'');
  if(!ok)   return res.status(400).json({ error:'invalid' });
  return res.json({ ok:true, token:sign(row.id,row.email), id:row.id, email:row.email, account_no:row.account_no, balance:row.balance });
});

// Protected
app.get('/api/balance', auth, (req,res)=>{
  const u = db.prepare('SELECT id,email,account_no,COALESCE(balance,0) balance FROM users WHERE id=?').get(req.user.uid);
  if(!u) return res.status(404).json({ error:'not found' });
  // address “virtual” (string aleatorio estable por usuario)
  const address = Buffer.from(u.id).toString('base64url').slice(0,23);
  return res.json({ ok:true, balance:u.balance||0, account_no:u.account_no, address });
});

app.post('/api/wallet/create', auth, (req,res)=>{
  // Marcador sencillo: no creamos chain real; devolvemos address estable a partir del uid (similar a balance)
  const u = db.prepare('SELECT id FROM users WHERE id=?').get(req.user.uid);
  if(!u) return res.status(404).json({ error:'user' });
  const deposit_address = Buffer.from(u.id + '::deposit').toString('base64url').slice(0,23);
  const w = { id: uuidv4(), user_id: u.id, account_index: Date.now()%100000, deposit_address, created_at: Date.now() };
  try {
    db.prepare('INSERT INTO wallets (id,user_id,account_index,deposit_address,created_at) VALUES (?,?,?,?,?)')
      .run(w.id, w.user_id, w.account_index, w.deposit_address, w.created_at);
  } catch(_) { /* idempotente */ }
  return res.json({ ok:true, wallet_id:w.id, account_index:w.account_index, deposit_address });
});

app.get('/api/transactions', auth, (req,res)=>{
  const txs = db.prepare('SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 200').all(req.user.uid);
  return res.json({ ok:true, transactions: txs });
});

app.post('/api/transfer', auth, (req,res)=>{
  const { toEmail, amount } = req.body || {};
  const a = parseFloat(amount||0);
  if(!toEmail || !(a>0)) return res.status(400).json({ error:'params' });
  const s = db.prepare('SELECT * FROM users WHERE id=?').get(req.user.uid);
  const r = db.prepare('SELECT * FROM users WHERE email=?').get(String(toEmail).toLowerCase());
  if(!s || !r) return res.status(404).json({ error:'user' });
  if((s.balance||0) < a) return res.status(400).json({ error:'insufficient' });

  const ns = +((s.balance||0) - a).toFixed(6);
  const nr = +((r.balance||0) + a).toFixed(6);
  db.prepare('UPDATE users SET balance=? WHERE id=?').run(ns, s.id);
  db.prepare('UPDATE users SET balance=? WHERE id=?').run(nr, r.id);
  db.prepare('INSERT INTO transactions (id,user_id,type,amount,balance_after,note,created_at) VALUES (?,?,?,?,?,?,?)')
    .run(uuidv4(), s.id, 'transfer', -a, ns, `to ${r.email}`, Date.now());
  db.prepare('INSERT INTO transactions (id,user_id,type,amount,balance_after,note,created_at) VALUES (?,?,?,?,?,?,?)')
    .run(uuidv4(), r.id, 'transfer',  a, nr, `from ${s.email}`, Date.now());
  return res.json({ ok:true, from:{ balance:ns }, to:{ balance:nr } });
});

app.post('/api/withdraw-request', auth, (req,res)=>{
  const { external_address, amount } = req.body || {};
  const a = parseFloat(amount||0);
  if(!external_address || !(a>0)) return res.status(400).json({ error:'params' });
  const u = db.prepare('SELECT * FROM users WHERE id=?').get(req.user.uid);
  if(!u) return res.status(404).json({ error:'user' });
  if((u.balance||0) < a) return res.status(400).json({ error:'insufficient' });
  const nb = +((u.balance||0) - a).toFixed(6);
  db.prepare('UPDATE users SET balance=? WHERE id=?').run(nb, u.id);
  db.prepare('INSERT INTO transactions (id,user_id,type,amount,balance_after,note,created_at) VALUES (?,?,?,?,?,?,?)')
    .run(uuidv4(), u.id, 'withdraw', -a, nb, `to ${external_address}`, Date.now());
  return res.json({ ok:true, balance: nb });
});

// === Admin credit (para fondear por email)
app.post('/admin/credit', (req,res)=>{
  if(req.headers['x-admin-key'] !== ADMIN_API_KEY) return res.status(403).json({ error:'forbidden' });
  const { email, amount, note } = req.body || {};
  const a = parseFloat(amount||0);
  if(!email || !(a>0)) return res.status(400).json({ error:'params' });
  const u = db.prepare('SELECT * FROM users WHERE email=?').get(String(email).toLowerCase());
  if(!u) return res.status(404).json({ error:'not found' });
  const nb = +((u.balance||0) + a).toFixed(6);
  db.prepare('UPDATE users SET balance=? WHERE id=?').run(nb, u.id);
  db.prepare('INSERT INTO transactions (id,user_id,type,amount,balance_after,note,created_at) VALUES (?,?,?,?,?,?,?)')
    .run(uuidv4(), u.id, 'credit', a, nb, note||'admin credit', Date.now());
  return res.json({ ok:true, balance: nb });
});

function startServer(){ app.listen(PORT, ()=> console.log('INTEN unified wallet listening on', PORT)); }


(async()=>{ await waitDb(); startServer(); })().catch(e=>{ console.error('Fatal init error:', e); process.exit(1); });
