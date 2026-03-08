
# -*- coding: utf-8 -*-
# ESTA ES LA PRIMERA LÍNEA. Garantiza que Python lea los caracteres en español (¡, ¿, ñ).

# app.py - Wallet prototype with wallet address generation
# INTEN active (internal ledger). External chains only if connectors configured.
# Wallet addresses generated per account. Balances kept per account (not per wallet).




from __future__ import annotations
import os, json, uuid, time
from typing import Dict, Any, Optional
from flask import Flask, request, session, redirect, url_for, render_template_string, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from jinja2 import DictLoader

import requests # ⬅️ AÑADIR ESTA LÍNEA
from requests.auth import HTTPBasicAuth




APP_SECRET = os.environ.get("WALLET_SECRET", "dev-bridge-secret")
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
SUPPORTED = ["INTEN", "BTC", "ETH", "XLM", "XRP", "LTC"]
DEFAULT_RATES = {
    "INTEN": 0.50,
    "BTC":   65000.0,
    "ETH":   3000.0,
    "XLM":   0.10,
    "XRP":   0.55,
    "LTC":   80.0,
}

MARKET_RATES = {
    "INTEN": 0.50,
    "BTC":   65000.0,
    "ETH":   3000.0,
    "XLM":   0.10,
    "XRP":   0.55,
    "LTC":   80.0,
}

# --- Configuración en tu script de backend (Reemplaza la sección existente) ---

# 1. Definición de credenciales
# Estas deben coincidir con tu archivo ~/.bitcoin/bitcoin.conf
RPC_USER = "INTEN" 
RPC_PASSWORD = "INTENCOIN" 
RPC_HOST = "127.0.0.1"
RPC_PORT = 8332

# 2. Construcción de la URL (Usada por tu función call_rpc)
# La URL base sin la ruta de la billetera.
RPC_BASE_URL = f"http://{RPC_HOST}:{RPC_PORT}" 
# Nota: La autenticación se maneja en el request.post.


# Conectores externos (usan la misma configuración RPC para Bitcoin)
# Esto es para que el BTCDriver y otras funciones sepan qué usar.
BTC_RPC_URL  = RPC_BASE_URL
BTC_RPC_USER = RPC_USER
BTC_RPC_PASS = RPC_PASSWORD

ETH_RPC      = os.environ.get("ETH_RPC")
XLM_HORIZON  = os.environ.get("XLM_HORIZON")
XRP_RPC      = os.environ.get("XRP_RPC")
LTC_RPC      = os.environ.get("LTC_RPC")



# Conectores externos (en el futuro puedes usarlos para RPC reales)
BTC_RPC      = os.environ.get("BTC_RPC")
ETH_RPC      = os.environ.get("ETH_RPC")
XLM_HORIZON  = os.environ.get("XLM_HORIZON")
XRP_RPC      = os.environ.get("XRP_RPC")
LTC_RPC      = os.environ.get("LTC_RPC")



# --- EN EL SCRIPT DEL PUERTO 5020 (wallet7.py) ---

# [Otras configuraciones aquí]

# 🔑 CONFIGURACIÓN NECESARIA PARA NOTIFICAR AL MINERO (PUERTO 5001)
MINER_NOTIFY_URL = "http://127.0.0.1:5001/api/miner/notify" 
# -------------------------------------------------------------

# [El resto de tu código...]




app = Flask(__name__)
app.secret_key = APP_SECRET

# Funci\u00f3n para realizar llamadas RPC al nodo Bitcoin Core (Línea ~69)
def call_rpc(method: str, params: list = [], wallet_name: str | None = None) -> Any:
    """Env\u00eda comandos RPC al nodo Bitcoin Core y devuelve el resultado, manejando errores -35."""
    
    # 1. Determinar la URL (Global o Específica de Billetera)
    url_to_use = f"{RPC_BASE_URL}/wallet/{wallet_name}" if wallet_name else RPC_BASE_URL
    
    headers = {'content-type': 'application/json'}
    payload = json.dumps({
        "method": method,
        "params": params,
        "jsonrpc": "1.0", 
        "id": "rpc_call_id"
    })
    
    try:
        response = requests.post(
            url_to_use, 
            data=payload, 
            headers=headers,
            # Aquí se usa el USER y PASSWORD definidos arriba:
            auth=HTTPBasicAuth(RPC_USER, RPC_PASSWORD), 
            timeout=30 
        )
        
        data = response.json()
        
        # Manejo de error específico de Bitcoin Core
        if data.get("error"):
             error_message = data["error"].get("message", "Unknown RPC Error")
             error_code = data["error"].get("code", 0)

             # *** CORRECCIÓN CRÍTICA: Manejar -35 y mensaje "already loaded" como éxito ***
             is_already_loaded_error = (method == "loadwallet" and 
                                        (error_code == -35 or "already loaded" in error_message.lower()))
             
             if is_already_loaded_error:
                 # print(f"[RPC] '{wallet_name}' ya estaba cargada (C\u00f3digo {error_code}). Tratado como \u00e9xito.")
                 return {"name": wallet_name} # Devuelve éxito para que el flujo continúe
             
             # Si no es un error de "ya cargada", lanza el error RPC
             raise RuntimeError(f"BTC RPC Error (Code {error_code}): {error_message}")
        
        # Si no hubo error RPC, verificamos el estado HTTP (e.g., para 404/500 puros)
        response.raise_for_status()
             
        return data["result"] 

    except Exception as e:
        # print(f"RPC Error calling {method} (Wallet: {wallet_name}): {e}")
        raise # Vuelve a lanzar la excepción




# ---------------- Persistence ----------------
def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return {"users": {}, "accounts": {}, "ledger": [], "rates": DEFAULT_RATES.copy()}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state: Dict[str, Any]):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)

STATE = load_state()

# ---------------- Utilities ----------------
def gen_wallet_address(acct_id: str) -> str:
    # Example address format: WALADDR-WAL-XXXX-1a2b3c4d
    return f"WALADDR-{acct_id}-{uuid.uuid4().hex[:8]}".upper()

def find_account_by_wallet(wallet_addr: str) -> Optional[Dict[str, Any]]:
    for a in STATE["accounts"].values():
        if wallet_addr in a.get("wallet_addresses", []):
            return a
    return None



def _credit_by_wallet(wallet_addr: str, symbol: str, amount: float) -> Optional[str]:
    """
    Buscar la cuenta por wallet y acreditar monto.
    Devuelve account_id o None.
    """
    # 1. Buscar la cuenta
    acct = find_account_by_wallet(wallet_addr)
    
    if not acct:
        # Si la wallet no existe (CAUSA PRINCIPAL DEL 400), retorna None
        return None
    
    # Asume que SUPPORTED está definido globalmente en 5020
    if symbol not in SUPPORTED or amount <= 0:
        return None
        
    # 2. Asegurarse de que la clave 'balances' exista e inicializar
    if "balances" not in acct:
        acct["balances"] = {}
        
    if symbol not in acct["balances"]:
        acct["balances"][symbol] = 0.0

    # 3. Acreditar el monto
    acct["balances"][symbol] += float(amount)
    
    # 4. Registrar en el Ledger y guardar el estado (asumiendo add_ledger y save_state existen)
    add_ledger({
        "type": "bridge_deposit",
        "symbol": symbol,
        "to": acct["account_id"],
        "wallet": wallet_addr,
        "amount": float(amount),
    })
    
    save_state(STATE)
    
    return acct["account_id"]







# ---------------- Domain ----------------
def new_user(email: str, password: str, initial_wallets: int = 1) -> str:
    uid = str(uuid.uuid4())
    STATE["users"][uid] = {
        "uid": uid,
        "email": email.lower().strip(),
        "pwd": generate_password_hash(password),
        "created": time.time(),
    }
    acct_id = "WAL-" + uid.split("-")[0].upper()
    wallet_addresses = []
    for _ in range(max(1, initial_wallets)):
        wallet_addresses.append(gen_wallet_address(acct_id))
    STATE["accounts"][acct_id] = {
        "account_id": acct_id,
        "owner": uid,
        "balances": {c: 0.0 for c in SUPPORTED},
        "wallet_addresses": wallet_addresses,
        "created": time.time(),
    }
    save_state(STATE)
    return uid

def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    email = email.lower().strip()
    for u in STATE["users"].values():
        if u["email"] == email:
            return u
    return None

def user_accounts(uid: str):
    return [a for a in STATE["accounts"].values() if a["owner"] == uid]

def add_ledger(entry: Dict[str, Any]):
    entry["ts"] = time.time()
    STATE["ledger"].append(entry)
    save_state(STATE)

# ---------------- FX ----------------
def get_rates() -> Dict[str, float]:
    for c in SUPPORTED:
        if c not in STATE["rates"]:
            STATE["rates"][c] = DEFAULT_RATES[c]
    return STATE["rates"]

def set_rates(new_rates: Dict[str, float]):
    for k, v in new_rates.items():
        if k in SUPPORTED:
            STATE["rates"][k] = float(v)
    save_state(STATE)


# L\u00ednea ~209
# ---------------- Domain ----------------
def new_user(email: str, password: str, initial_wallets: int = 1) -> str:
    uid = str(uuid.uuid4())
    STATE["users"][uid] = {
        "uid": uid,
        "email": email.lower().strip(),
        "pwd": generate_password_hash(password),
        "created": time.time(),
    }
    acct_id = "WAL-" + uid.split("-")[0].upper()
    wallet_addresses = []
    for _ in range(max(1, initial_wallets)):
        wallet_addresses.append(gen_wallet_address(acct_id))
    STATE["accounts"][acct_id] = {
        "account_id": acct_id,
        "owner": uid,
        "balances": {c: 0.0 for c in SUPPORTED},
        "wallet_addresses": wallet_addresses,
        "external_btc_address": None, # <--- Inicializaci\u00f3n correcta de BTC
        "created": time.time(),
    }
    save_state(STATE)
    return uid









# FUNCIÓN DE REGISTRO DE USUARIO
def register_new_user(username, password):
    # 1. Crear nuevo usuario en tu DB
    # (El c\u00f3digo para crear un nuevo usuario real ir\u00eda aqu\u00ed)
    
    # 2. Generar Direcci\u00f3n Bitcoin Core para el usuario
    # El label (etiqueta) ayuda a rastrear los dep\u00f3sitos en tu nodo
    try:
        bitcoin_address_result = call_rpc("getnewaddress", [username, "bech32"]) # "bech32" para formato moderno (SegWit)
        new_btc_address = bitcoin_address_result
    except Exception as e:
        print(f"Error en register_new_user al generar BTC Adre: {e}")
        new_btc_address = "Error al generar BTC Adre"
        
    # 3. Guardar la nueva_btc_address y la nueva_inten_address en la base de datos del usuario
    # (El c\u00f3digo para guardar ir\u00eda aqu\u00ed)

    return new_btc_address






# ---------------- Drivers (INTEN + redes externas) ----------------
class ChainDriver:
    symbol: str = ""
    def is_configured(self) -> bool:
        return False
    def validate_address(self, address: str) -> bool:
        return bool(address and len(address) >= 4)
    def send(self, from_account: Dict[str, Any], to_address: str, amount: float) -> str:
        raise RuntimeError(f"connector for {self.symbol} not configured")



class IntencoinDriver(ChainDriver):
    symbol = "INTEN"

    def is_configured(self) -> bool:
        # Por ahora siempre configurado; luego aquí puedes chequear tu nodo real
        return True

    def send(self, from_account: Dict[str, Any], to_address: str, amount: float) -> str:
        # envío externo de INTEN
        print(f"[INTEN] Sending {amount} INTEN to {to_address} from {from_account['account_id']}")
        return f"INTEN-TX-{uuid.uuid4().hex[:12]}"



class BTCDriver(ChainDriver):
    symbol = "BTC"

    def is_configured(self) -> bool:
        return bool(BTC_RPC_URL and BTC_RPC_USER and BTC_RPC_PASS)

    def validate_address(self, address: str) -> bool:
        # Validación mínima. Bitcoin Core tiene su propia validación al enviar.
        return bool(address and len(address) >= 20)

    # FUNCIÓN CLAVE: Crear y cargar la billetera RPC para el cliente
    def create_and_get_address(self, wallet_name: str) -> str:
        if not self.is_configured():
            return "Error: Conector BTC no configurado"
            
        # --- Parte 1: Intentar crear la billetera (con claves por defecto) ---
        try:
            # CORRECCIÓN: Quitamos el 'True' (blank=True) para que se creen claves.
            # Los parámetros por defecto de createwallet aseguran que se cree una wallet con claves.
            call_rpc("createwallet", [wallet_name], wallet_name=None) 
            # print(f"[BTC] Creada billetera RPC: {wallet_name}")
        except RuntimeError as e:
            # Capturar errores que indican que el archivo ya existe en disco
            if "Wallet already exists" in str(e):
                # print(f"[BTC] Wallet ya existe en disco.")
                pass
            else:
                return f"Error al crear BTC Wallet: {e}"
        
        # --- Parte 2: Forzar la carga ---
        try:
            # Esto resuelve el 500 si ya estaba cargada gracias a la Corrección 1 en call_rpc.
            call_rpc("loadwallet", [wallet_name], wallet_name=None)
            # print(f"[BTC] Carga de billetera RPC confirmada: {wallet_name}")
        except Exception as load_e:
             # Si no se puede cargar por un motivo NO relacionado con '-35'
             return f"Error al cargar BTC Wallet: {load_e}"


        # --- Parte 3: Obtener la dirección ---
        try:
            # Generar la dirección para la wallet ya cargada.
            btc_address = call_rpc("getnewaddress", ["", "bech32"], wallet_name=wallet_name)
            return btc_address if btc_address else "Error al obtener dirección (getnewaddress falló)"
        except Exception as e:
            return f"Error al obtener dirección de {wallet_name}: {e}"
        
    def send(self, from_account: Dict[str, Any], to_address: str, amount: float) -> str:
        # Usamos el account_id como nombre de la billetera de origen RPC
        wallet_name = from_account.get("external_btc_wallet_id", from_account["account_id"])

        if not self.is_configured():
            raise RuntimeError("BTC RPC not configured")

        txid = call_rpc("sendtoaddress", [to_address, float(amount)], wallet_name=wallet_name)

        if txid:
            # print(f"REAL BTC SEND: Sent {amount} BTC from {wallet_name} to {to_address}, txid={txid}")
            return txid
        else:
            raise RuntimeError("BTC RPC call failed during send.")






# ... (Otros Drivers sin cambios) ...




class ETHDriver(ChainDriver):
    symbol = "ETH"
    def is_configured(self) -> bool:
        return True
    def validate_address(self, address: str) -> bool:
        return address.startswith("0x") and len(address) == 42
    def send(self, from_account: Dict[str, Any], to_address: str, amount: float) -> str:
        return f"INTEN-ETH-TX-{uuid.uuid4().hex[:12]}"

class XLMDriver(ChainDriver):
    symbol = "XLM"
    def is_configured(self) -> bool:
        return True
    def validate_address(self, address: str) -> bool:
        return address.startswith("G") and len(address) >= 30
    def send(self, from_account: Dict[str, Any], to_address: str, amount: float) -> str:
        return f"INTEN-XLM-TX-{uuid.uuid4().hex[:12]}"

class XRPDriver(ChainDriver):
    symbol = "XRP"
    def is_configured(self) -> bool:
        return True
    def validate_address(self, address: str) -> bool:
        return address.startswith("r") and len(address) >= 25
    def send(self, from_account: Dict[str, Any], to_address: str, amount: float) -> str:
        return f"INTEN-XRP-TX-{uuid.uuid4().hex[:12]}"

class LTCDriver(ChainDriver):
    symbol = "LTC"
    def is_configured(self) -> bool:
        return True
    def validate_address(self, address: str) -> bool:
        return address.startswith("L") or address.startswith("M") or address.startswith("ltc1")
    def send(self, from_account: Dict[str, Any], to_address: str, amount: float) -> str:
        return f"INTEN-LTC-TX-{uuid.uuid4().hex[:12]}"


class IntencoinDriver(ChainDriver):
    symbol = "INTEN"

    def is_configured(self) -> bool:
        # Siempre configurado para simular que la red INTEN existe
        return True
        
    def validate_address(self, address: str) -> bool:
        # Una validación dummy para INTEN
        return bool(address and len(address) > 10)

    def send(self, from_account: Dict[str, Any], to_address: str, amount: float) -> str:
        """Envío de INTEN Coin puro. (Asumido como envío externo a su propia cadena)."""
        print(f"[INTEN] Sending {amount} INTEN to external address {to_address} from {from_account['account_id']}")
        # Simula una TXID de la red INTEN
        return f"INTEN-TX-EXTERNAL-{uuid.uuid4().hex[:12]}"




DRIVERS: Dict[str, ChainDriver] = {
    "INTEN": IntencoinDriver(),
    "BTC":   BTCDriver(),
    "ETH":   ETHDriver(),
    "XLM":   XLMDriver(),
    "XRP":   XRPDriver(),
    "LTC":   LTCDriver(),
}




# ---------------- Auth ----------------
def require_login():
    uid = session.get("uid")
    if not uid or uid not in STATE["users"]:
        return None
    return STATE["users"][uid]

# ---------------- Templates ----------------
BASE_HTML = """
<!doctype html>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Wallet Demo</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,sans-serif;margin:2rem;}
.card{border:1px solid #ddd;border-radius:16px;padding:1rem;margin:0 0 1rem 0;}
.row{display:flex;gap:1rem;flex-wrap:wrap}
.btn{display:inline-block;padding:.6rem 1rem;border-radius:10px;border:1px solid #888;text-decoration:none}
input,select{padding:.5rem;border-radius:8px;border:1px solid #bbb}
.table{border-collapse:collapse;width:100%}
.table th,.table td{border:1px solid #eee;padding:.5rem;text-align:left}
small{color:#555}
</style>
<div class=card>
  <h2>{{ title }}</h2>
  {% block body %}{% endblock %}
</div>
"""

INDEX_HTML = """
{% extends 'base.html' %}
{% block body %}
  <p>Welcome. Create an account or login.</p>
  <div class=row>
    <form class=card method=post action="{{ url_for('register') }}">
      <h3>Register</h3>
      <p><input name=email placeholder="email" required></p>
      <p><input name=password type=password placeholder="password" required></p>
      <p><button class=btn>Create account</button></p>
    </form>
    <form class=card method=post action="{{ url_for('login') }}">
      <h3>Login</h3>
      <p><input name=email placeholder="email" required></p>
      <p><input name=password type=password placeholder="password" required></p>
      <p><button class=btn>Login</button></p>
    </form>
  </div>
{% endblock %}
"""



# Busca esta definici\u00f3n en tu archivo (probablemente est\u00e1 alrededor de la l\u00ednea 360-400)
DASH_HTML = """
{% extends 'base.html' %}
{% block body %}
  <p><b>User:</b> {{ user.email }} | <a class=btn href='{{ url_for('logout') }}'>Logout</a></p>

  <div class=card>
    <h3>Account: {{ acct.account_id }}</h3>
    
    <p><b>1. Internal Wallet Addresses (INTEN Ledger):</b></p>
    <ul>
      {% for w in acct.wallet_addresses %}
        <li>{{w}}</li>
      {% endfor %}
    </ul>
    
    <p><b>2. External Deposit Address (Bitcoin Core):</b></p>
    <ul>
        <li><b>BTC:</b> {{ acct.external_btc_address or "Not configured" }}</li>
    </ul>

    {# Bloque Condicional para Botones #}
    {% if not acct.external_btc_address %}
        <form method="post" action="{{ url_for('configure_btc_wallet') }}" style="display:inline;">
          <button class=btn type="submit">Configure BTC Deposit Wallet (RPC)</button>
          <small> (Requiere nodo Bitcoin Core)</small>
        </form>
    {% else %}
        <form method="post" action="{{ url_for('create_wallet') }}" style="display:inline;">
          <button class=btn type="submit">Create new internal wallet address (INTEN)</button>
        </form>
    {% endif %}

    
    <h3>Balances</h3>
    <table class=table>
      <tr><th>Coin</th><th>Amount</th><th>≈ USD</th></tr>
      {% for sym, amt in acct.balances.items() %}
        <tr><td>{{ sym }}</td><td>{{ '%.8f'|format(amt) }}</td><td>{{ '%.2f'|format(rates[sym]*amt) }}</td></tr>
      {% endfor %}
    </table>
    <small>Rates are manual for now. <a href='{{ url_for('rates_page') }}'>Edit rates</a></small>
  </div>

  <div class=row>
    
    <form class=card method=post action='{{ url_for('transfer_internal') }}'>
      <h3>Internal Transfer (INTEN/Ledger)</h3>
      <p><select name=symbol>{% for s in supported %}<option>{{s}}</option>{% endfor %}</select></p>
      <p><input name=to_account placeholder="Destination account (WAL-...)" ></p>
      <p><input name=to_wallet placeholder="OR destination wallet address (WALADDR-...)" ></p>
      <p><input name=amount type=number step=any placeholder="Amount" required></p>
      <p><button class=btn>Transfer</button></p>
      <small>Use either account ID or wallet address as destination.</small>
    </form>

    <form class=card method=post action='{{ url_for('send_external') }}'>
      <h3>Send External (INTEN -> BTC Swap)</h3>
      <p><b>From Internal:</b> <select name=symbol><option>INTEN</option></select></p>
      <p><b>To External:</b> <select name=symbol_dest>{% for s in supported %}{% if s != "INTEN" %}<option>{{s}}</option>{% endif %}{% endfor %}</select></p>
      <p><input name=from_wallet placeholder="Your wallet address (WALADDR-...)" required></p>
      <p><input name=to_address placeholder="Destination chain address" required></p>
      <p><input name=amount type=number step=any placeholder="Amount of INTEN to spend" required></p>
      <p><button class=btn>Swap & Send (INTEN -> BTC)</button></p>
      <small>Debits INTEN, converts to target coin value based on rates, sends target coin (e.g., BTC) via native chain.</small>
    </form>
  </div>

  <div class=card>
    <h3>Commands (cURL)</h3>
    <pre>
# Create new wallet address (POST)
POST {{ url_for('create_wallet', _external=True) }}

# Deposit INTEN (session required)
POST {{ url_for('api_deposit', _external=True) }}  JSON: {"symbol":"INTEN","amount":100}

# Internal transfer by wallet:
POST {{ url_for('api_transfer_internal', _external=True) }} JSON: {"to_wallet":"WALADDR-...","symbol":"INTEN","amount":1}

# Retiro/Swap (INTEN -> BTC):
POST {{ url_for('send_external', _external=True) }} JSON: {"symbol":"BTC", "from_wallet":"WALADDR-...", "to_address":"bc1...", "amount":1000} (1000 INTEN gastados)
    </pre>
  </div>

{% endblock %}
"""








RATES_HTML = """
{% extends 'base.html' %}
{% block body %}
  <form class=card method=post>
    <h3>Edit rates (1 COIN = USD) - Manual</h3>
    {% for s in supported %}
      <p>
        {{ s }}:
        <input
          name="{{ s }}"
          type="number"
          step="0.00000001"
          value="{{ '%.8f'|format(rates[s]) }}"
        >
      </p>
    {% endfor %}
    <p><button class=btn>Save</button> <a class=btn href='{{ url_for('dashboard') }}'>Back</a></p>
  </form>

  <div class=card>
    <h3>Market rates (read-only)</h3>
    <table class=table>
      <tr><th>Coin</th><th>Market USD</th></tr>
      {% for s in supported %}
        <tr><td>{{ s }}</td><td>{{ '%.8f'|format(market[s]) }}</td></tr>
      {% endfor %}
    </table>
    <small>These are external/market reference rates.</small>
  </div>
{% endblock %}
"""




RATES_HTML = """
{% extends 'base.html' %}
{% block body %}
  <form class=card method=post>
    <h3>Edit rates (1 COIN = USD) - Manual</h3>
    {% for s in supported %}
      <p>{{s}}: <input name="{{s}}" type=number step=any value="{{rates[s]}}"></p>
    {% endfor %}
    <p><button class=btn>Save</button> <a class=btn href='{{ url_for('dashboard') }}'>Back</a></p>
  </form>

  <div class=card>
    <h3>Market rates (read-only)</h3>
    <table class=table>
      <tr><th>Coin</th><th>Market USD</th></tr>
      {% for s in supported %}
        <tr><td>{{ s }}</td><td>{{ '%.6f'|format(market[s]) }}</td></tr>
      {% endfor %}
    </table>
    <small>These are external/market reference rates.</small>
  </div>
{% endblock %}
"""

app.jinja_loader = DictLoader({
    'base.html': BASE_HTML,
    'index.html': INDEX_HTML,
    'dash.html': DASH_HTML,
    'rates.html': RATES_HTML,
})

# ---------------- Routes ----------------
@app.get('/')
def index():
    if session.get('uid'):
        return redirect(url_for('dashboard'))
    return render_template_string(app.jinja_loader.get_source(app.jinja_env,'index.html')[0], title="Wallet Demo")

@app.post('/register')
def register():
    email = request.form.get('email','').strip()
    password = request.form.get('password','').strip()
    if not email or not password:
        abort(400)
    if find_user_by_email(email):
        return "User exists", 400
    uid = new_user(email, password, initial_wallets=1)
    session['uid'] = uid
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return redirect(url_for('index'))
    email = request.form.get('email','').strip()
    password = request.form.get('password','').strip()
    u = find_user_by_email(email)
    if not u or not check_password_hash(u['pwd'], password):
        return "Invalid credentials", 400
    session['uid'] = u['uid']
    return redirect(url_for('dashboard'))

@app.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.get('/dashboard')
def dashboard():
    u = require_login()
    if not u:
        return redirect(url_for('index'))
    accts = user_accounts(u['uid'])
    acct = accts[0]
    return render_template_string(
        app.jinja_loader.get_source(app.jinja_env,'dash.html')[0],
        title="Dashboard",
        user=u, acct=acct, rates=get_rates(), supported=SUPPORTED,
    )


# AÑADIDO: Ruta /configure-btc-wallet (Añadir cerca de @app.post('/create-wallet'))


@app.post('/configure-btc-wallet')
def configure_btc_wallet():
    u = require_login()
    if not u: 
        return jsonify({"error": "Unauthorized"}), 401
    
    acct = user_accounts(u['uid'])[0]

    if not acct.get('external_btc_address'):
        btc_driver = DRIVERS["BTC"]
        wallet_rpc_name = acct['account_id']
        
        if not btc_driver.is_configured():
            return jsonify({"error": "BTC connector not configured"}), 500
        
        try:
            new_btc_address = btc_driver.create_and_get_address(wallet_rpc_name)
            
            if new_btc_address and not new_btc_address.startswith("Error"):
                acct['external_btc_address'] = new_btc_address
                acct['external_btc_wallet_id'] = wallet_rpc_name
                add_ledger({"type": "btc_wallet_config", "account": acct['account_id'], "address": new_btc_address})
                save_state(STATE)
                return jsonify({"success": True, "btc_address": new_btc_address})
            else:
                return jsonify({"error": "Failed to create BTC wallet"}), 500

        except Exception as e:
            return jsonify({"error": f"Exception: {str(e)}"}), 500

    return jsonify({"error": "Wallet already configured"}), 400






@app.post('/recargar-wallet')
def recargar_wallet():
    u = require_login()
    if not u:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    data = request.get_json()
    account_number = data.get("intencoin_account")
    
    if not account_number:
        return jsonify({"ok": False, "error": "Missing account number"}), 400

    # Aquí usas las credenciales y llamas a tu función que se conecta a Bitcoin Core
    # Por ejemplo:
    try:
        btc_driver = DRIVERS["BTC"]
        result = btc_driver.reload_wallet(account_number)
        if result:
            return jsonify({"ok": True, "message": f"Wallet {account_number} reloaded successfully."})
        else:
            return jsonify({"ok": False, "error": "Failed to reload wallet"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500







@app.route('/rates', methods=['GET', 'POST'])
def rates_page():
    u = require_login()
    if not u:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Actualiza los rates manuales (1 COIN = USD)
        edits_raw = {s: request.form.get(s) for s in SUPPORTED}
        edits = {k: float(v) for k, v in edits_raw.items() if v not in (None, '')}
        set_rates(edits)
        return redirect(url_for('rates_page'))

    # Render con rates manuales y market rates de solo lectura
    return render_template_string(
        app.jinja_loader.get_source(app.jinja_env, 'rates.html')[0],
        title="Rates",
        rates=get_rates(),
        supported=SUPPORTED,
        market=MARKET_RATES,
    )
        

# Create wallet address (HTML)
@app.post('/create-wallet')
def create_wallet():
    u = require_login()
    if not u: return redirect(url_for('index'))
    acct = user_accounts(u['uid'])[0]
    new_addr = gen_wallet_address(acct['account_id'])
    acct.setdefault("wallet_addresses", []).append(new_addr)
    add_ledger({"type":"create_wallet","account":acct['account_id'],"wallet":new_addr})
    save_state(STATE)
    return redirect(url_for('dashboard'))

# ---------------- Actions ----------------
@app.post('/transfer-internal')
def transfer_internal():
    u = require_login()
    if not u: return redirect(url_for('index'))
    symbol = request.form.get('symbol')
    to_account = request.form.get('to_account','').strip() or None
    to_wallet = request.form.get('to_wallet','').strip() or None
    amount = float(request.form.get('amount','0') or 0)
    if symbol not in SUPPORTED or amount <= 0:
        return "Invalid request", 400
    src = user_accounts(u['uid'])[0]
    # resolve destination
    dst = None
    if to_account:
        dst = STATE['accounts'].get(to_account)
    elif to_wallet:
        dst = find_account_by_wallet(to_wallet)
    if not dst:
        return "Destination not found", 404
    if src['balances'][symbol] < amount:
        return "Insufficient funds", 400
    src['balances'][symbol] -= amount
    dst['balances'][symbol] += amount
    add_ledger({"type":"internal","symbol":symbol,"from":src['account_id'],"to": dst['account_id'],"amount":amount,"via_wallet": to_wallet})
    save_state(STATE)
    return redirect(url_for('dashboard'))




    
    # ... (Validación de wallet y usuario sin cambios) ...
    acct = find_account_by_wallet(from_wallet)
    if not acct: return "Source wallet not found", 404
    uacct = user_accounts(u['uid'])[0]
    if acct['account_id'] != uacct['account_id']:
        return "Source wallet does not belong to your account", 403
    
    # 2. VERIFICAR BALANCE DE INTEN
    if acct['balances']['INTEN'] < inten_amount_spent:
        return "Insufficient INTEN funds (needs INTEN).", 400
        
    # 3. CONVERSIÓN DE MONEDA (INTEN -> Destino)
    rates = get_rates()
    
    rate_inten = rates.get('INTEN', 0.0)
    rate_dest = rates.get(symbol_dest, 0.0)
    
    if rate_inten <= 0 or rate_dest <= 0:
        return f"Exchange rates for INTEN or {symbol_dest} are zero/invalid.", 400

    # Valor en USD: (INTEN gastado * Rate INTEN)
    usd_value = inten_amount_spent * rate_inten
    
    # Cantidad de destino a enviar: (Valor USD / Rate Destino)
    amount_to_send_dest = usd_value / rate_dest
    
    # 4. EJECUTAR EL ENVÍO Y EL DÉBITO
    driver = DRIVERS[symbol_dest]
    if not driver.is_configured():
        return f"Connector not configured for {symbol_dest}", 400
        
    # Debitar INTEN
    acct['balances']['INTEN'] -= inten_amount_spent
    
    # Enviar la moneda de destino (BTC, ETH, etc.)
    txid = driver.send(acct, to_address, amount_to_send_dest)
    
    # 5. REGISTRAR LEDGER
    add_ledger({
        "type": "external_swap",
        "spent": "INTEN", "spent_amount": inten_amount_spent,
        "sent": symbol_dest, "sent_amount": amount_to_send_dest,
        "from_account": acct['account_id'], "to": to_address, 
        "txid": txid
    })
    save_state(STATE)
    return redirect(url_for('dashboard'))





@app.post('/send-external')
def send_external():
    u = require_login()
    if not u:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    # Detectar si viene JSON o FORM desde HTML
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    # Leer variables compatibles con HTML y JSON
    symbol = (data.get("symbol") or "").strip()
    from_wallet = (data.get("from_wallet") or "").strip()
    to_address = (data.get("to_address") or "").strip()

    # Soportar ambos nombres symbol_dest y swap_to
    symbol_dest = (data.get("symbol_dest") or data.get("swap_to") or "").strip()

    try:
        amount_to_debit = float(data.get("amount", 0))
    except:
        amount_to_debit = 0.0

    if not symbol or amount_to_debit <= 0:
        return jsonify({"ok": False, "error": "Invalid symbol or amount"}), 400
    if not from_wallet or not to_address:
        return jsonify({"ok": False, "error": "Missing from_wallet or to_address"}), 400

    # Buscar la cuenta origen
    acct = find_account_by_wallet(from_wallet)
    if not acct:
        return jsonify({"ok": False, "error": "Source wallet not found"}), 404

    if acct["balances"].get(symbol, 0) < amount_to_debit:
        return jsonify({"ok": False, "error": "Insufficient funds"}), 400

    # ===================================================
    # CASO 1: SWAP INTEN → BTC
    # ===================================================
    if symbol == "INTEN" and symbol_dest == "BTC":

        rates = get_rates()
        rate_inten = rates.get("INTEN", 0.0)
        rate_dest = rates.get("BTC", 0.0)

        if rate_inten <= 0 or rate_dest <= 0:
            return jsonify({"ok": False, "error": "Invalid exchange rates"}), 400

        usd_value = amount_to_debit * rate_inten
        amount_to_send_dest = usd_value / rate_dest  # BTC calculado

        # Debitar INTEN
        acct["balances"]["INTEN"] -= amount_to_debit

        # Enviar BTC usando Bitcoin Core
        driver = DRIVERS["BTC"]

        try:
            txid = driver.send(acct, to_address, amount_to_send_dest)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

        add_ledger({
            "type": "swap_INTEN_to_BTC",
            "spent_INTEN": amount_to_debit,
            "sent_BTC": amount_to_send_dest,
            "from_account": acct["account_id"],
            "to": to_address,
            "txid": txid,
        })
        save_state(STATE)

        return jsonify({
            "ok": True,
            "type": "swap_INTEN_to_BTC",
            "spent_INTEN": amount_to_debit,
            "sent_BTC": amount_to_send_dest,
            "txid": txid,
            "to": to_address
        }), 200

    # ===================================================
    # CASO 2: ENVÍO DIRECTO BTC → BTC (Bitcoin Core)
    # ===================================================
    if symbol == "BTC":
        driver = DRIVERS["BTC"]
        acct["balances"]["BTC"] -= amount_to_debit

        try:
            txid = driver.send(acct, to_address, amount_to_debit)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

        add_ledger({
            "type": "external_send_pure",
            "symbol": "BTC",
            "amount": amount_to_debit,
            "from_account": acct["account_id"],
            "to": to_address,
            "txid": txid,
        })
        save_state(STATE)

        return jsonify({
            "ok": True,
            "type": "send_BTC_to_BTC",
            "amount": amount_to_debit,
            "txid": txid,
            "to": to_address
        }), 200

    # ===================================================
    # CASO 3: ENVÍO DIRECTO DE OTRAS CRIPTOS (ETH, XRP…)
    # ===================================================
    driver = DRIVERS.get(symbol)
    if not driver:
        return jsonify({"ok": False, "error": "Unsupported symbol"}), 400

    if not driver.is_configured():
        return jsonify({"ok": False, "error": f"Connector not configured for {symbol}"}), 400

    # Debitar
    acct["balances"][symbol] -= amount_to_debit

    try:
        txid = driver.send(acct, to_address, amount_to_debit)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    add_ledger({
        "type": "external_send_pure",
        "symbol": symbol,
        "amount": amount_to_debit,
        "from_account": acct["account_id"],
        "to": to_address,
        "txid": txid,
    })
    save_state(STATE)

    return jsonify({
        "ok": True,
        "type": f"send_{symbol}",
        "amount": amount_to_debit,
        "to": to_address,
        "txid": txid
    }), 200







@app.post('/pull')
def pull_action():
    u = require_login()
    if not u: return redirect(url_for('index'))
    symbol = request.form.get('symbol')
    add_ledger({"type":"pull","symbol":symbol,"account":user_accounts(u['uid'])[0]['account_id']})
    return redirect(url_for('dashboard'))

@app.post('/hook-a')
def extra_hook():
    u = require_login()
    if not u: return redirect(url_for('index'))
    add_ledger({"type":"hook-a","account":user_accounts(u['uid'])[0]['account_id']})
    return redirect(url_for('dashboard'))

@app.post('/hook-b')
def extra_hook_b():
    u = require_login()
    if not u: return redirect(url_for('index'))
    add_ledger({"type":"hook-b","account":user_accounts(u['uid'])[0]['account_id']})
    return redirect(url_for('dashboard'))

# ---------------- JSON APIs (commands) ----------------
@app.post('/api/create-wallet')
def api_create_wallet():
    u = require_login()
    if not u: return ("Unauthorized", 401)
    acct = user_accounts(u['uid'])[0]
    new_addr = gen_wallet_address(acct['account_id'])
    acct.setdefault("wallet_addresses", []).append(new_addr)
    add_ledger({"type":"create_wallet","account":acct['account_id'],"wallet":new_addr})
    return jsonify({"ok": True, "wallet": new_addr})

@app.post('/api/deposit')
def api_deposit():
    u = require_login()
    if not u: return ("Unauthorized", 401)
    data = request.get_json(force=True)
    symbol = data.get('symbol','INTEN')
    amount = float(data.get('amount',0))
    if symbol not in SUPPORTED or amount <= 0:
        return jsonify({"ok": False, "error":"invalid request"}), 400
    acct = user_accounts(u['uid'])[0]
    acct['balances'][symbol] += amount
    add_ledger({"type":"deposit","symbol":symbol,"to":acct['account_id'],"amount":amount,"note":"manual command"})
    save_state(STATE)
    return jsonify({"ok": True, "account": acct['account_id'], "symbol": symbol, "new_balance": acct['balances'][symbol]})

@app.post('/api/transfer-internal')
def api_transfer_internal():
    u = require_login()
    if not u: return ("Unauthorized", 401)
    data = request.get_json(force=True)
    to_account = data.get('to')
    to_wallet = data.get('to_wallet')
    symbol = data.get('symbol')
    amount = float(data.get('amount',0))
    if symbol not in SUPPORTED or amount <= 0:
        return jsonify({"ok": False, "error":"invalid request"}), 400
    src = user_accounts(u['uid'])[0]
    dst = None
    if to_account:
        dst = STATE['accounts'].get(to_account)
    elif to_wallet:
        dst = find_account_by_wallet(to_wallet)
    if not dst:
        return jsonify({"ok": False, "error":"unknown destination"}), 404
    if src['balances'][symbol] < amount:
        return jsonify({"ok": False, "error":"insufficient funds"}), 400
    src['balances'][symbol] -= amount
    dst['balances'][symbol] += amount
    add_ledger({"type":"internal","symbol":symbol,"from":src['account_id'],"to":dst['account_id'],"amount":amount,"via_wallet": to_wallet})
    save_state(STATE)
    return jsonify({"ok": True, "tx":"internal", "from": src['account_id'], "to": dst['account_id']})




# API general de comerciante: generar API key
@app.post("/api/generate-api-key")
def generate_api_key():
    api_key = str(uuid.uuid4())
    # Aquí podrías guardar este api_key asociado a un merchant, etc.
    return jsonify({"ok": True, "api_key": api_key})


# ---------- Bridge / API for external credits ----------

# Clave general (para depósitos genéricos: INTEN, BTC, ETH, etc.)
BRIDGE_SECRET = os.environ.get("BRIDGE_SECRET", "dev-bridge-secret")

# Clave especial SOLO para la criptomoneda de Intencoin
CRYPTO_INTEN_SECRET = os.environ.get("CRYPTO_INTEN_SECRET", "INTEN-BRIDGE-SECRET")


def _credit_by_wallet(wallet_addr: str, symbol: str, amount: float) -> Optional[str]:
    """
    Buscar la cuenta por wallet y acreditar monto.
    Devuelve account_id o None.
    """
    acct = find_account_by_wallet(wallet_addr)
    if not acct:
        return None
    if symbol not in SUPPORTED or amount <= 0:
        return None
    acct["balances"][symbol] += float(amount)
    add_ledger({
        "type": "bridge_deposit",
        "symbol": symbol,
        "to": acct["account_id"],
        "wallet": wallet_addr,
        "amount": float(amount),
    })
    save_state(STATE)
    return acct["account_id"]













@app.route('/api/rates', methods=['GET','POST'])
def api_rates():
    u = require_login()
    if not u: return ("Unauthorized", 401)
    if request.method == 'GET':
        return jsonify({"ok": True, "rates": get_rates()})
    data = request.get_json(force=True)
    set_rates({k: v for k, v in data.items() if k in SUPPORTED})
    return jsonify({"ok": True, "rates": get_rates()})


# ---------- Bridge / API for external credits ----------
BRIDGE_SECRET = os.environ.get("BRIDGE_SECRET", "dev-bridge-secret")

def _credit_by_wallet(wallet_addr: str, symbol: str, amount: float) -> Optional[str]:
    """Find account by wallet address and credit amount. Returns account_id or None."""
    acct = find_account_by_wallet(wallet_addr)
    if not acct:
        return None
    if symbol not in SUPPORTED or amount <= 0:
        return None
    acct["balances"][symbol] += float(amount)
    add_ledger({"type":"bridge_deposit","symbol":symbol,"to":acct["account_id"],"wallet":wallet_addr,"amount":float(amount)})
    save_state(STATE)
    return acct["account_id"]

@app.post("/api/bridge/deposit")
def api_bridge_deposit():
    """
    Body JSON:
    {
      "wallet": "WALADDR-...",
      "symbol": "INTEN",
      "amount": 25,
      "secret": "BRIDGE_SECRET"
    }
    """
    data = request.get_json(force=True)
    secret = data.get("secret")
    if secret != BRIDGE_SECRET:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    wallet_addr = (data.get("wallet") or "").strip()
    symbol = (data.get("symbol") or "INTEN").strip()
    try:
        amount = float(data.get("amount", 0))
    except:
        amount = 0.0

    acct_id = _credit_by_wallet(wallet_addr, symbol, amount)
    if not acct_id:
        return jsonify({"ok": False, "error":"invalid wallet/symbol/amount"}), 400
    return jsonify({"ok": True, "credited_account": acct_id, "symbol": symbol, "amount": amount})




@app.post("/api/bridge/deposit-inten-from-crypto")
def api_bridge_deposit_inten_from_crypto():
    """
    Deposito ESPECIAL para INTEN que viene desde la CRIPTOMONEDA.

    Body JSON:
    {
      "wallet": "WALADDR-...",
      "amount": 1000,
      "secret": "INTEN-BRIDGE-SECRET"
    }
    """
    data = request.get_json(force=True) or {}

    secret = data.get("secret")
    if secret != CRYPTO_INTEN_SECRET:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    wallet_addr = (data.get("wallet") or "").strip()
    try:
        amount = float(data.get("amount", 0))
    except:
        amount = 0.0

    if not wallet_addr or amount <= 0:
        return jsonify({"ok": False, "error": "wallet/amount invalid"}), 400

    # Aquí siempre es INTEN
    acct_id = _credit_by_wallet(wallet_addr, "INTEN", amount)
    if not acct_id:
        return jsonify({"ok": False, "error": "invalid wallet"}), 400

    return jsonify({
        "ok": True,
        "credited_account": acct_id,
        "symbol": "INTEN",
        "amount": amount
    })



@app.post("/api/bridge/deposit_new")
def api_bridge_deposit_new():
    """
    Endpoint para que un sistema externo (como el Minero 5001) deposite fondos.
    """
    data = request.get_json(force=True)
    
    # 1. Validación del Secreto
    secret = data.get("bridge_secret") 
    # Asume que BRIDGE_SECRET está definido globalmente en 5020
    if secret != BRIDGE_SECRET:
        return jsonify({"ok": False, "error": "unauthorized"}), 401 # Aquí podría estar fallando

    wallet_addr = (data.get("wallet") or "").strip()
    symbol = (data.get("symbol") or "INTEN").strip()
    
    try:
        amount = float(data.get("amount", 0))
    except ValueError:
        amount = 0.0

    # 2. Crédito del balance en el 5020
    acct_id = _credit_by_wallet(wallet_addr, symbol, amount)
    
    if not acct_id:
        # Esto devuelve el 400 BAD REQUEST si la wallet no existe.
        return jsonify({"ok": False, "error":"invalid wallet/symbol/amount"}), 400 

    # 3. Lógica de Notificación al Minero (5001)
    # Evita notificar si esta llamada viene del Minero pagándose a sí mismo (is_miner_reward: True)
    is_miner_reward = data.get("is_miner_reward", False) 
    
    if acct_id and symbol == "INTEN" and amount > 0 and not is_miner_reward:
        try:
            notify_payload = {
                "wallet": wallet_addr,
                "amount": amount,
                "symbol": symbol,
                "secret": BRIDGE_SECRET 
            }
            # Asume que MINER_NOTIFY_URL está definido globalmente en 5020
            r = requests.post(MINER_NOTIFY_URL, json=notify_payload, timeout=5)
            r.raise_for_status() 
        except requests.exceptions.RequestException:
            pass # Si falla la notificación, el depósito en 5020 ya está hecho.

    # 4. Respuesta final
    return jsonify({"ok": True, "credited_account": acct_id, "symbol": symbol, "amount": amount})










@app.get("/api/balance")
def api_balance():
    """
    Query:
      - ?wallet=WALADDR-...   -> balance de la cuenta dueña de esa wallet
      - ?account=WAL-...      -> balance por account_id
    """
    wallet_q = request.args.get("wallet")
    acct_q = request.args.get("account")
    acct = None
    if wallet_q:
        acct = find_account_by_wallet(wallet_q.strip())
    elif acct_q:
        acct = STATE["accounts"].get(acct_q.strip())
    if not acct:
        return jsonify({"ok": False, "error":"not found"}), 404
    return jsonify({"ok": True, "account": acct["account_id"], "balances": acct["balances"], "wallets": acct.get("wallet_addresses", [])})

@app.get("/api/ledger")
def api_ledger():
    """
    Query:
      - ?limit=50 (default 50)
    """
    try:
        limit = int(request.args.get("limit", 50))
    except:
        limit = 50
    return jsonify({"ok": True, "ledger": STATE["ledger"][-limit:]})


@app.get("/api/market-rates")
def api_market_rates():
    return jsonify({"ok": True, "market": MARKET_RATES})

@app.post("/api/market-rates")
def api_market_rates_update():
    # opcional: permitir actualizar MARKET_RATES manualmente
    u = require_login()
    if not u: return ("Unauthorized", 401)
    data = request.get_json(force=True)
    for k,v in (data or {}).items():
        if k in SUPPORTED:
            try:
                MARKET_RATES[k] = float(v)
            except:
                pass
    return jsonify({"ok": True, "market": MARKET_RATES})


    import uuid

@app.route('/api/generate-token', methods=['POST'])
def generate_token():
    u = require_login()
    if not u:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    token = str(uuid.uuid4())
    # Aquí puedes guardar el token en tu base de datos o en un estado, asociado al usuario o a la cuenta correspondiente.

    return jsonify({"ok": True, "token": token})

import uuid # Asegúrate de tener esto importado

# ... (otras funciones de tu script) ...

@app.route('/generate_new_apikey', methods=['POST'])
def generate_new_apikey():
    """Genera una nueva clave de API única y la devuelve."""
    # Se utiliza uuid4 para generar una cadena única que puede servir como clave API
    new_key = str(uuid.uuid4())
    
    # Devuelve la clave en formato JSON
    return jsonify({
        "message": "API Key generada exitosamente.",
        "api_key": new_key,
        "note": "Asegúrate de guardar esta clave; no se mostrará de nuevo."
    }), 201 

# ... (resto de tu código) ...







# ---------------- Main ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5021"))
    app.run(host="0.0.0.0", port=port, debug=True)
    








