const fetch = (...args)=>import('node-fetch').then(({default:fetch})=>fetch(...args));
const bitcoin = require('bitcoinjs-lib');
const { deriveAddress } = require('../wallet');

function deriveBtcAddress(idx){
  const seed = process.env.ADMIN_WALLET_SEED;
  if(!seed) throw new Error('ADMIN_WALLET_SEED missing');
  const out = deriveAddress(seed, idx, 0, 0);
  return { address: out.address, path: out.path };
}

async function sendBtc(to, amountBtc){
  const url = `http://${process.env.BTC_RPC_HOST}:${process.env.BTC_RPC_PORT}`;
  const body = { jsonrpc: "1.0", id: "sendtoaddress", method: "sendtoaddress", params: [to, amountBtc] };
  const auth = Buffer.from(`${process.env.BTC_RPC_USER}:${process.env.BTC_RPC_PASS}`).toString('base64');
  const r = await fetch(url, {
    method:'POST',
    headers:{ 'Content-Type':'application/json', 'Authorization':`Basic ${auth}` },
    body: JSON.stringify(body)
  });
  const j = await r.json();
  if (j.error) throw new Error(j.error.message || 'btc rpc error');
  return j.result;
}

module.exports = { deriveBtcAddress, sendBtc };
