const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, 'data');
const USERS_F = path.join(DATA_DIR, 'users.json');
const TXS_F   = path.join(DATA_DIR, 'transactions.json');
const ADDR_F  = path.join(DATA_DIR, 'addresses.json');

function load(file, fallback){
  try { return JSON.parse(fs.readFileSync(file,'utf8')); } catch(e){ return fallback; }
}
function save(file, obj){
  fs.mkdirSync(DATA_DIR, {recursive:true});
  fs.writeFileSync(file, JSON.stringify(obj, null, 2));
}

let users = load(USERS_F, {});          // key: id -> user
let txs   = load(TXS_F,   []);          // array
let addrs = load(ADDR_F,  {});          // key: address -> user_id

function persist(){ save(USERS_F, users); save(TXS_F, txs); save(ADDR_F, addrs); }

function uuid(){ return (global.crypto?.randomUUID?.() || require('crypto').randomUUID()); }

function findUserByEmail(email){
  return Object.values(users).find(u=> (u.email||'').toLowerCase() === (email||'').toLowerCase()) || null;
}
function findUserById(id){ return users[id] || null; }
function findUserByAccountNo(ac){ return Object.values(users).find(u=>u.account_no===ac) || null; }
function findUserByAddress(address){
  const uid = addrs[address] || Object.values(users).find(u=>u.deposit_address===address)?.id;
  return uid ? users[uid] || null : null;
}

function insertUser(u){
  users[u.id] = {...u, balance: Number(u.balance||0)};
  if (u.deposit_address) addrs[u.deposit_address] = u.id;
  persist();
}
function updateUserBalance(id, newBal){
  if (!users[id]) return;
  users[id].balance = Number(newBal);
  persist();
}
function setDepositAddress(id, address){
  if (!users[id]) return;
  users[id].deposit_address = address;
  addrs[address] = id;
  persist();
}
function insertTx(row){
  txs.push(row);
  persist();
}
function listTxByUser(user_id, limit=50, offset=0){
  const arr = txs.filter(t=>t.user_id===user_id).sort((a,b)=>b.created_at - a.created_at);
  return arr.slice(offset, offset+limit);
}

module.exports = {
  // minimal shim compatible with server.js usage: db.prepare(...).get/run/all
  prepare(sql){
    sql = (sql||'').trim();

    // SELECT * FROM users WHERE email=?
    if (/^SELECT\s+\*\s+FROM\s+users\s+WHERE\s+email\s*=\s*\?/i.test(sql)){
      return { get(email){ return findUserByEmail(email) || undefined; } };
    }

    // SELECT * FROM users WHERE id=?
    if (/^SELECT\s+\*\s+FROM\s+users\s+WHERE\s+id\s*=\s*\?/i.test(sql)){
      return { get(id){ return findUserById(id) || undefined; } };
    }

    // SELECT * FROM users WHERE deposit_address = ? OR address = ?
    if (/^SELECT\s+\*\s+FROM\s+users\s+WHERE\s+deposit_address\s*=\s*\?\s+OR\s+address\s*=\s*\?/i.test(sql)){
      return { get(a1, a2){ return findUserByAddress(a1) || findUserByAddress(a2) || undefined; } };
    }

    // SELECT * FROM addresses WHERE address=?
    if (/^SELECT\s+\*\s+FROM\s+addresses\s+WHERE\s+address\s*=\s*\?/i.test(sql)){
      return { get(address){ const uid = addrs[address]; return uid ? { address, user_id: uid } : undefined; } };
    }

    // SELECT id,email,account_no,deposit_address,balance FROM users
    if (/^SELECT\s+id,\s*email,\s*account_no,\s*deposit_address,\s*balance\s+FROM\s+users/i.test(sql)){
      return { all(){ return Object.values(users).map(u=>({
        id:u.id, email:u.email, account_no:u.account_no, deposit_address:u.deposit_address, balance:u.balance
      })); } };
    }

    // INSERT INTO users (id,email,password_hash,account_no,balance,created_at) VALUES (?,?,?,?,?,?)
    if (/^INSERT\s+INTO\s+users\s*\(/i.test(sql)){
      return { run(id,email,phash,acc,balance,created){
        insertUser({ id, email, password_hash:phash, account_no:acc, balance, created_at:created });
        return { changes:1 };
      }};
    }

    // UPDATE users SET balance=? WHERE id=?
    if (/^UPDATE\s+users\s+SET\s+balance\s*=\s*\?\s+WHERE\s+id\s*=\s*\?/i.test(sql)){
      return { run(balance,id){ updateUserBalance(id, balance); return { changes:1 }; } };
    }

    // INSERT INTO transactions (...)
    if (/^INSERT\s+INTO\s+transactions\s*\(/i.test(sql)){
      return { run(id,user_id,type,amount,balance_after,note,created_at){
        insertTx({ id, user_id, type, amount:Number(amount), balance_after:Number(balance_after), note, created_at });
        return { changes:1 };
      }};
    }

    // INSERT OR IGNORE INTO addresses(address,user_id) VALUES(?,?)
    if (/^INSERT\s+OR\s+IGNORE\s+INTO\s+addresses\s*\(/i.test(sql)){
      return { run(address, user_id){ if(!addrs[address]){ addrs[address]=user_id; persist(); } return { changes:1 }; } };
    }

    // custom helpers we may call from server.js patches
    if (/^__SET_DEPOSIT__/i.test(sql)){
      return { run(id,address){ setDepositAddress(id,address); return { changes:1 }; } };
    }

    // Transactions listing example
    if (/^SELECT\s+\*\s+FROM\s+transactions\s+WHERE\s+user_id\s*=\s*\?\s+ORDER BY/i.test(sql)){
      return { all(user_id,limit=50,offset=0){ return listTxByUser(user_id, limit, offset); } };
    }

    // default dummy
    return { get(){return undefined;}, run(){return {changes:0};}, all(){return [];} };
  },

  // convenience to create a random UUID if your server.js expects to import from db
  uuid
};
