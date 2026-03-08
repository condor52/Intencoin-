/* === INTEN Wallet Frontend Glue === */
const $ = (id)=>document.getElementById(id);

// Persist token between refreshes
let TOKEN = localStorage.getItem('INTEN_TOKEN') || null;

// Show/hide dashboard
function showDashboard(auth) {
  const dash = document.querySelector('[data-dashboard]');
  if (!dash) return;
  dash.style.display = auth ? 'block' : 'none';
}

// Generic API helper (adds Authorization automatically if TOKEN)
async function api(path, method='GET', body=null) {
  const h = {'Content-Type':'application/json'};
  if (TOKEN) h['Authorization'] = 'Bearer ' + TOKEN;
  const r = await fetch(path, {method, headers:h, body: body ? JSON.stringify(body) : null});
  const txt = await r.text();
  let json = {};
  try { json = JSON.parse(txt); } catch { json = {error:'non-json', status:r.status, text:txt}; }
  if (!r.ok) throw json;
  return json;
}

// Register
async function register(){
  try{
    const out = await api('/auth/register','POST',{
      name: $('#r_name').value,
      email: $('#r_email').value,
      password: $('#r_pass').value
    });
    $('#r_out').innerText = JSON.stringify(out,null,2);
    if (out.token) {
      TOKEN = out.token;
      localStorage.setItem('INTEN_TOKEN', TOKEN);
      showDashboard(true);
      await balance();
    }
  }catch(err){ $('#r_out').innerText = JSON.stringify(err,null,2); }
}

// Login
async function login(){
  try{
    const out = await api('/auth/login','POST',{
      email: $('#l_email').value,
      password: $('#l_pass').value
    });
    $('#l_out').innerText = JSON.stringify(out,null,2);
    if (out.token) {
      TOKEN = out.token;
      localStorage.setItem('INTEN_TOKEN', TOKEN);
      showDashboard(true);
      await balance(); // refresh immediately
    }
  }catch(err){ $('#l_out').innerText = JSON.stringify(err,null,2); }
}

// Logout
function logout(){
  TOKEN = null;
  localStorage.removeItem('INTEN_TOKEN');
  showDashboard(false);
  $('#bal').innerText = '';
  $('#addr').innerText = '';
  $('#a_out').innerText = '';
  $('#txs').innerText = '';
}

// Balance (GET /api/balance)
async function balance(){
  try{
    const out = await api('/api/balance','GET');
    $('#bal').innerText = JSON.stringify(out,null,2);
  }catch(err){ $('#bal').innerText = JSON.stringify(err,null,2); }
}

// Create Wallet/Address (POST /api/wallet/create)
async function createWallet(){
  try{
    const out = await api('/api/wallet/create','POST',{});
    $('#addr').innerText = JSON.stringify(out,null,2);
    await balance();
  }catch(err){ $('#addr').innerText = JSON.stringify(err,null,2); }
}

// Transfer by email (POST /api/transfer {toEmail, amount})
async function transfer(){
  try{
    const toEmail = $('#to_email').value.trim();
    const amount = parseFloat($('#amt').value||'0');
    const out = await api('/api/transfer','POST',{ toEmail, amount });
    $('#a_out').innerText = JSON.stringify(out,null,2);
    await balance();
  }catch(err){ $('#a_out').innerText = JSON.stringify(err,null,2); }
}

// Withdraw to external address (Python) (POST /api/withdraw-request)
async function withdraw(){
  try{
    const external_address = $('#ext').value.trim();
    const amount = parseFloat($('#wamt').value||'0');
    const out = await api('/api/withdraw-request','POST',{ external_address, amount });
    $('#a_out').innerText = JSON.stringify(out,null,2);
    await balance();
  }catch(err){ $('#a_out').innerText = JSON.stringify(err,null,2); }
}

// Transactions (GET /api/transactions)
async function tx(){
  try{
    const out = await api('/api/transactions','GET');
    $('#txs').innerText = JSON.stringify(out,null,2);
  }catch(err){ $('#txs').innerText = JSON.stringify(err,null,2); }
}

// Currency conversion (POST /api/convert {to})
async function convertTo(sym){
  try{
    const out = await api('/api/convert','POST',{ to: sym });
    $('#a_out').innerText = JSON.stringify(out,null,2);
    await balance();
  }catch(err){ $('#a_out').innerText = JSON.stringify(err,null,2); }
}

// On load: show/hide dashboard based on token
document.addEventListener('DOMContentLoaded', ()=>{
  showDashboard(!!TOKEN);
});
