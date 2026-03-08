/**
 * WalletConnect v2 helper (Termux/Node 24)
 * - Fuerza WebSocket de 'ws' (tiene .on)
 * - Stub Worker con terminate()
 * - Resolver recursivo de exportaciones (default / named / nested)
 * - Soporta constructor o .init()
 */
import * as wsmod from 'ws';
const WSImpl = wsmod.WebSocket || wsmod.default;
globalThis.WebSocket = function(url, protocols){
  return new WSImpl(url, protocols, { perMessageDeflate:false });
};
if (typeof globalThis.Worker === 'undefined') {
  globalThis.Worker = class {
    constructor() {}
    postMessage(_) {}
    terminate() {}
    onmessage = null;
    onerror = null;
  };
}

const projectId = process.env.WC_PROJECT_ID || '74f092b235a8dd36deed736cfcd97d45';
const relayUrl  = process.env.WC_RELAY      || 'wss://relay.walletconnect.com';

let mod; 
try { mod = await import('@walletconnect/sign-client'); }
catch(e){ console.error('import error:', e?.message||e); process.exit(1); }

// -------- resolver recursivo --------
function* walk(obj, seen=new Set(), path='root'){
  if (!obj || typeof obj!=='object' && typeof obj!=='function') return;
  if (seen.has(obj)) return; seen.add(obj);
  yield { node: obj, path };
  for (const k of Object.keys(obj)) {
    try { yield* walk(obj[k], seen, path+'.'+k); } catch {}
  }
}
function findClient(mod){
  let ctor=null, staticInit=null, whereCtor='', whereInit='';
  for (const {node, path} of walk(mod)) {
    if (!ctor && typeof node === 'function') { ctor = node; whereCtor = path; }
    if (!staticInit && node && typeof node.init === 'function') { staticInit = node.init.bind(node); whereInit = path+'.init'; }
    if (ctor && staticInit) break;
  }
  return { ctor, staticInit, whereCtor, whereInit };
}

const { ctor, staticInit, whereCtor, whereInit } = findClient(mod);

// Namespaces (EVM mainnet)
const REQUIRED_NAMESPACES = {
  eip155: {
    methods: ['eth_sendTransaction','eth_signTransaction','eth_sign','personal_sign','eth_signTypedData'],
    chains:  ['eip155:1'],
    events:  ['chainChanged','accountsChanged']
  }
};
const metadata = {
  name: 'Mission Arreola DApp',
  description: 'Intencoin WC2 Connector',
  url: 'https://intencoin.local',
  icons: ['https://walletconnect.com/walletconnect-logo.png']
};

try {
  let client;
  if (staticInit) {
    // Encontramos API estática .init()
    client = await staticInit({ projectId, relayUrl, metadata });
    // console.debug('use init at', whereInit);
  } else if (ctor) {
    // Encontramos un constructor utilizable
    client = new ctor({ projectId, relayUrl, metadata });
    // console.debug('use ctor at', whereCtor);
  } else {
    console.error('No SignClient usable. keys =', Object.keys(mod||{}));
    process.exit(1);
  }

  const { uri/*, approval*/ } = await client.connect({ requiredNamespaces: REQUIRED_NAMESPACES });
  if (!uri) { console.error('No pairing URI generated'); process.exit(1); }

  console.log(JSON.stringify({ uri }));
  // Si quieres: const session = await approval(); console.log(JSON.stringify({approved:true, session},null,2));
} catch(e){
  console.error('WC helper error:', e?.message||e);
  process.exit(1);
}
