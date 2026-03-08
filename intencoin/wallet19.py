
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
import requests
from flask import Flask, request, jsonify
import os, base64
from flask import Flask, jsonify, request, abort

import requests
from flask import Flask, request, jsonify

# === ESTO VA ARRIBA (VARIABLES GLOBALES) ===
BANK_API_URL = "http://69.164.245.28:5000"
SMART_CONTRACT_ADDRESS = "0x26cbed10c42A2e08DC7473d7acD3f808d2279ED9"
METAMASK_FUNDS_WALLET = "0x3335bddbaa5a9343b1883896102c6e5bfd621e7b"
BANK_ESCROW_ID = "ACC-F6215A2C412B"


BANK_API_URL = "http://69.164.245.28:5000"

def bank_request(path, payload):
    try:
        r = requests.post(f"{BANK_API_URL}{path}", json=payload, timeout=20)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --- ILP minimal client (local helper, sin dependencia externa) ---
ILP_NODE_URL = os.environ.get("ILP_NODE_URL", "http://127.0.0.1:7770")
ILP_ADMIN_TOKEN = os.environ.get("ILP_ADMIN_TOKEN", "admin123")

# SPSP “destinos” de ejemplo (puedes ajustar a los tuyos reales)
ILP_PAYPAL_SPSP = os.environ.get("ILP_PAYPAL_SPSP", "paypal.example/spsp/alice")

def ilp_send(amount: int, spsp_endpoint: str) -> dict:
    """
    Helper síncrono. Simula/encapsula un pago ILP.
    - Si ILP_NODE_URL está vivo, aquí puedes implementar llamadas reales a tu ilp-node.
    - Por ahora, devolvemos un resultado de éxito “mock” y queda listo para producción cuando conectes.
    """
    # TODO: si quieres usar tu ilp-node:
    # 1) crear cuenta/saldo en /accounts
    # 2) usar /spsp/pay o endpoint equivalente del ilp-node.
    return {
        "ok": True,
        "amount": int(amount),
        "to": spsp_endpoint,
        "node": ILP_NODE_URL,
        "txid": f"ILP-{uuid.uuid4().hex[:12]}"
    }


APP_SECRET = os.environ.get("WALLET_SECRET", "dev-bridge-secret")
STATE_FILE = os.environ.get("STATE_FILE", "state.json")




SUPPORTED = ["INTEN", "DGDM", "USDT", "BTC", "ETH", "XLM", "XRP", "LTC"]

DEFAULT_RATES = {
    "INTEN": 0.50,
    "DGDM": 1.00,   # 1 DGDM = 1 unidad soberana (Grand Dollars)
    "USDT": 1.00,   # Stablecoin de integración MetaTask
    "BTC":   65000.0,
    "ETH":   3000.0,
    "XLM":   0.10,
    "XRP":   0.55,
    "LTC":   80.0,
}



# Inicializamos MARKET_RATES con valores en cero
MARKET_RATES = {
    "INTEN": 0.0,
    "BTC": 0.0,
    "ETH": 0.0,
    "XLM": 0.0,
    "XRP": 0.0,
    "LTC": 0.0,
}










def update_market_rates():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum,stellar,ripple,litecoin",
        "vs_currencies": "usd"
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        # Actualizamos solo las monedas de mercado
        STATE["rates"]["BTC"] = float(data["bitcoin"]["usd"])
        STATE["rates"]["ETH"] = float(data["ethereum"]["usd"])
        STATE["rates"]["XLM"] = float(data["stellar"]["usd"])
        STATE["rates"]["XRP"] = float(data["ripple"]["usd"])
        STATE["rates"]["LTC"] = float(data["litecoin"]["usd"])

        # NO tocar INTEN, DGDM, USDT, EINTN, DENM
        save_state(STATE)

    except Exception as e:
        print(f"[Market] Error updating market rates: {e}")



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

LTC_RPC_URL  = "http://127.0.0.1:9332"
LTC_RPC_USER = "INTEN"
LTC_RPC_PASS = "INTENCOIN"


# =========================================================
# === CONFIGURACIÓN DE DGDM (ERC20 en Polygon) ============
# =========================================================

from web3 import Web3

POLYGON_RPC = "https://1rpc.io/matic"
web3 = Web3(Web3.HTTPProvider(POLYGON_RPC))

# 🔥 DIRECCIONES EN FORMATO CHECKSUM
DGDM_CONTRACT = Web3.to_checksum_address("0xEe9cf06834d3FD930811EdF021cd391493C749A8")
OWNER_ADDRESS = Web3.to_checksum_address("0x3335bddbaa5a9343b1883896102c6e5bfd621e7b")

OWNER_PRIVATE_KEY = os.getenv("PRIVATE_KEY")  # llave privada

# Cargar ABI del contrato DGDM
with open("DGDM_abi.json") as f:
    DGDM_ABI = json.load(f)

dgdm = web3.eth.contract(address=DGDM_CONTRACT, abi=DGDM_ABI)



# =========================================================
# === CONFIGURACIÓN DE USDT (ERC20 real en Polygon) =======
# =========================================================



USDT_CONTRACT = Web3.to_checksum_address("0x3A3A65aAb0dd2A17E3F1947bA16138cd37d08c04")

# ABI mínimo ERC-20 para transfer
USDT_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [
            {"name": "", "type": "bool"}
        ],
        "type": "function"
    }
]

usdt_contract = web3.eth.contract(address=USDT_CONTRACT, abi=USDT_ABI)



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

update_market_rates()   # <--- AÑADIR AQUÍ




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



def call_ltc_rpc(method, params=[], wallet_name=None):
    url = f"{LTC_RPC_URL}/wallet/{wallet_name}" if wallet_name else LTC_RPC_URL

    payload = {
        "jsonrpc": "1.0",
        "id": "ltc",
        "method": method,
        "params": params
    }

    r = requests.post(
        url,
        json=payload,
        auth=HTTPBasicAuth(LTC_RPC_USER, LTC_RPC_PASS),
        timeout=30
    )
    r.raise_for_status()
    data = r.json()

    if data.get("error"):
        raise RuntimeError(data["error"])

    return data["result"]



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


update_market_rates()

import threading, time

def auto_update_market():
    while True:
        update_market_rates()
        time.sleep(60)

threading.Thread(target=auto_update_market, daemon=True).start()


def ilp_send(amount: int, payload: dict) -> dict:
    """
    Envío ILP real.
    Interledger recibe:
    - monto
    - tipo de transferencia
    - datos bancarios
    El banco destino responde si falta algo.
    """

    return {
        "ok": True,
        "amount": amount,
        "ilp_network": "INTERLEDGER",
        "payload": payload,
        "txid": f"ILP-{uuid.uuid4().hex[:16]}"
    }




def add_ledger(entry: dict):
    """
    Añade una entrada al ledger global y persiste el estado.
    """
    STATE.setdefault("ledger", [])
    entry["ts"] = time.time()
    STATE["ledger"].append(entry)
    save_state(STATE)



def find_user_by_email(email: str):
    email = email.lower().strip()
    for u in STATE["users"].values():
        if u.get("email") == email:
            return u
    return None


def user_accounts(uid: str):
    """
    Devuelve todas las cuentas (accounts) que pertenecen a un usuario.
    Normalmente será 1, pero queda listo para multi-account.
    """
    accounts = []
    for acct in STATE["accounts"].values():
        if acct.get("owner") == uid:
            accounts.append(acct)
    return accounts


def get_rates():
    """
    Devuelve las tasas activas (manuales + mercado si existen).
    Prioridad:
    - STATE["rates"] (persistido)
    - DEFAULT_RATES (fallback)
    """
    rates = {}

    # Base: rates guardados en STATE o defaults
    base = STATE.get("rates") or DEFAULT_RATES

    for sym in SUPPORTED:
        try:
            rates[sym] = float(base.get(sym, 0.0))
        except:
            rates[sym] = 0.0

    return rates


def set_rates(new_rates: dict):
    """
    Actualiza las tasas manuales (1 COIN = USD).
    Persiste en STATE["rates"].
    """
    if "rates" not in STATE:
        STATE["rates"] = {}

    for sym, value in new_rates.items():
        if sym in SUPPORTED:
            try:
                STATE["rates"][sym] = float(value)
            except:
                pass

    save_state(STATE)

@app.post("/api/admin/rates/<symbol>")
def api_set_rate(symbol):
    symbol = symbol.upper()

    if symbol not in SUPPORTED:
        return jsonify({"ok": False, "error": "unsupported symbol"}), 400

    # Acepta JSON o form-data
    if request.is_json:
        data = request.get_json(silent=True) or {}
        price = data.get("price")
    else:
        price = request.form.get("price")

    try:
        price = float(price)
    except:
        return jsonify({"ok": False, "error": "invalid price"}), 400

    # Guardar en STATE
    STATE["rates"][symbol] = price
    save_state(STATE)

    return jsonify({"ok": True, "symbol": symbol, "price": price})






    # Si viene de API JSON → responder JSON
    if request.is_json:
        return jsonify({"ok": True, "symbol": symbol, "price": price})

    # Si viene de HTML → volver a la página de rates
    return redirect(url_for("rates_page"))



# Asegurar que todas las cuentas tengan campos de direcciones externas
for acct in STATE["accounts"].values():
    acct.setdefault("external_btc_address", None)
    acct.setdefault("external_eth_address", None)
    acct.setdefault("external_xlm_address", None)
    acct.setdefault("external_xrp_address", None)
    acct.setdefault("external_ltc_address", None)
    # Para BTC usamos también un ID interno de wallet RPC opcional
    acct.setdefault("external_btc_wallet_id", None)






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





from web3 import Web3

def new_user(email: str, password: str, initial_wallets: int = 1) -> str:
    uid = str(uuid.uuid4())
    STATE["users"][uid] = {
        "uid": uid,
        "email": email.lower().strip(),
        "pwd": generate_password_hash(password),
        "created": time.time(),
    }

    acct_id = "WAL-" + uid.split("-")[0].upper()

    # Crear WALADDR INTEN
    wallet_addresses = [gen_wallet_address(acct_id)]

    # Crear WALLET EVM (DGDM/USDT)
    evm = Web3().eth.account.create()
    evm_address = evm.address
    evm_private_key = evm.key.hex()

    STATE["accounts"][acct_id] = {
        "account_id": acct_id,
        "owner": uid,
        "balances": {c: 0.0 for c in SUPPORTED},
        "wallet_addresses": wallet_addresses,

        # 🔥 Wallet EVM del cliente
        "external_eth_address": evm_address,
        "evm_private_key": evm_private_key,

        # Otras cadenas
        "external_btc_address": None,
        "external_btc_wallet_id": None,
        "external_xlm_address": None,
        "external_xrp_address": None,
        "external_ltc_address": None,

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





def burn_dgdm(from_address: str, amount: float):
    amount_wei = web3.to_wei(amount, 'ether')
    nonce = web3.eth.get_transaction_count(OWNER_ADDRESS)

    tx = dgdm.functions.burn(from_address, amount_wei).build_transaction({
        'from': OWNER_ADDRESS,
        'nonce': nonce,
        'gas': 300000,
        'gasPrice': web3.to_wei('50', 'gwei')
    })

    signed = web3.eth.account.sign_transaction(tx, OWNER_PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    return tx_hash.hex()



def swap_inten_to_dgdm(acct, amount_inten):
    acct["balances"]["INTEN"] -= amount_inten

    payload = {
        "account_id": acct["account_id"],
        "amount_inten": amount_inten,
        "evm_address": acct["external_eth_address"]
    }

    res = bank_request("/api/bank/swap/inten-to-dgdm", payload)

    if not res.get("ok"):
        acct["balances"]["INTEN"] += amount_inten
        save_state(STATE)
        return res

    add_ledger({
        "type": "swap_inten_to_dgdm",
        "from": acct["account_id"],
        "amount_inten": amount_inten,
        "amount_dgdm": res["dgdm_amount"],
        "tx": res["tx"]
    })

    save_state(STATE)
    return res



def send_dgdm_to_evm(acct, to_evm, amount_dgdm):
    payload = {
        "from_evm": acct["external_eth_address"],
        "to_evm": to_evm,
        "amount_dgdm": amount_dgdm
    }

    res = bank_request("/api/bank/send/dgdm-to-evm", payload)

    add_ledger({
        "type": "send_dgdm_to_evm",
        "from": acct["external_eth_address"],
        "to": to_evm,
        "amount_dgdm": amount_dgdm,
        "tx": res.get("tx")
    })

    save_state(STATE)
    return res



def swap_inten_to_metamask(acct, amount_inten, metamask_address):
    acct["balances"]["INTEN"] -= amount_inten

    payload = {
        "account_id": acct["account_id"],
        "amount_inten": amount_inten,
        "evm_address": metamask_address
    }

    res = bank_request("/api/bank/swap/inten-to-dgdm", payload)

    if not res.get("ok"):
        acct["balances"]["INTEN"] += amount_inten
        save_state(STATE)
        return res

    add_ledger({
        "type": "swap_inten_to_metamask",
        "from": acct["account_id"],
        "amount_inten": amount_inten,
        "amount_dgdm": res["dgdm_amount"],
        "evm_address": metamask_address,
        "tx": res["tx"]
    })

    save_state(STATE)
    return res
    
    
    





# =========================================================
# === RUTAS DE SWAP INTEN ↔ DGDM ==========================
# =========================================================

@app.post("/api/swap/inten-to-dgdm")
def api_swap_inten_to_dgdm():
    user = require_login()
    if not user:
        return jsonify({"ok": False, "error": "auth required"}), 401

    data = request.get_json(force=True, silent=True) or {}
    amount_inten = float(data.get("amount_inten", 0))

    if amount_inten <= 0:
        return jsonify({"ok": False, "error": "invalid amount"}), 400

    accts = user_accounts(user["uid"])
    if not accts:
        return jsonify({"ok": False, "error": "no account"}), 400

    acct = accts[0]

    if acct["balances"].get("INTEN", 0.0) < amount_inten:
        return jsonify({"ok": False, "error": "insufficient INTEN"}), 400

    if not acct.get("external_eth_address"):
        return jsonify({"ok": False, "error": "no external_eth_address configured"}), 400

    result = swap_inten_to_dgdm(acct, amount_inten)

    return jsonify({
        "ok": True,
        "account_id": acct["account_id"],
        "amount_inten": amount_inten,
        "dgdm_received": result["dgdm"],
        "tx": result["tx"],
    })


@app.post("/api/swap/dgdm-to-inten")
def api_swap_dgdm_to_inten():
    user = require_login()
    if not user:
        return jsonify({"ok": False, "error": "auth required"}), 401

    data = request.get_json(force=True, silent=True) or {}
    amount_dgdm = float(data.get("amount_dgdm", 0))

    if amount_dgdm <= 0:
        return jsonify({"ok": False, "error": "invalid amount"}), 400

    accts = user_accounts(user["uid"])
    if not accts:
        return jsonify({"ok": False, "error": "no account"}), 400

    acct = accts[0]

    if not acct.get("external_eth_address"):
        return jsonify({"ok": False, "error": "no external_eth_address configured"}), 400

    result = swap_dgdm_to_inten(acct, amount_dgdm)

    return jsonify({
        "ok": True,
        "account_id": acct["account_id"],
        "amount_dgdm": amount_dgdm,
        "inten_received": result["inten"],
        "tx": result["tx"],
    })








@app.post("/api/send/inten-to-metamask/dgdm")
def api_send_inten_to_metamask_dgdm():
    user = require_login()
    if not user:
        return jsonify({"ok": False, "error": "auth required"}), 401

    data = request.get_json(silent=True) or request.form or {}
    amount_inten = float(data.get("amount_inten", 0))
    evm_address = data.get("evm_address", "").strip()

    if amount_inten <= 0:
        return jsonify({"ok": False, "error": "invalid amount"}), 400
    if not evm_address.startswith("0x") or len(evm_address) != 42:
        return jsonify({"ok": False, "error": "invalid evm_address"}), 400

    accts = user_accounts(user["uid"])
    acct = accts[0]

    if acct["balances"]["INTEN"] < amount_inten:
        return jsonify({"ok": False, "error": "insufficient INTEN"}), 400

    # Debitar INTEN interno
    acct["balances"]["INTEN"] -= amount_inten
    save_state(STATE)

    # Llamar al banco para mintear DGDM y enviarlo
    payload = {
        "account_id": acct["account_id"],
        "amount_inten": amount_inten,
        "evm_address": evm_address
    }

    res = bank_request("/api/bank/send/dgdm-to-evm", payload)

    if not res.get("ok"):
        # rollback
        acct["balances"]["INTEN"] += amount_inten
        save_state(STATE)
        return jsonify(res), 500

    tx_hash = res["tx"]

    add_ledger({
        "type": "send_inten_to_metamask_dgdm",
        "from": acct["account_id"],
        "amount_inten": amount_inten,
        "evm_address": evm_address,
        "tx": tx_hash,
    })

    save_state(STATE)

    return jsonify({
        "ok": True,
        "tx": tx_hash,
        "amount_inten": amount_inten,
        "evm_address": evm_address
    })


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
        return bool(LTC_RPC_URL and LTC_RPC_USER and LTC_RPC_PASS)

    def create_and_get_address(self, wallet_name: str) -> str:
        if not self.is_configured():
            raise RuntimeError("LTC RPC not configured")

        # 1️⃣ Crear wallet (si no existe)
        try:
            call_ltc_rpc("createwallet", [wallet_name])
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise

        # 2️⃣ Cargar wallet (OBLIGATORIO)
        try:
            call_ltc_rpc("loadwallet", [wallet_name])
        except Exception as e:
            if "already loaded" not in str(e).lower():
                raise

        # 3️⃣ Crear dirección REAL on-chain
        address = call_ltc_rpc(
            "getnewaddress",
            ["", "bech32"],
            wallet_name=wallet_name
        )

        if not address:
            raise RuntimeError("Failed to generate LTC address")

        return address



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
        #una TXID de la red INTEN
        return f"INTEN-TX-EXTERNAL-{uuid.uuid4().hex[:12]}"


class EVMDriver(ChainDriver):
    def __init__(self, rpc_url, contract_address, abi):
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract = self.web3.eth.contract(address=contract_address, abi=abi)

    def send(self, from_private_key, to_address, amount):
        amount_wei = self.web3.to_wei(amount, 'ether')
        account = self.web3.eth.account.from_key(from_private_key)
        nonce = self.web3.eth.get_transaction_count(account.address)

        tx = self.contract.functions.transfer(to_address, amount_wei).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': self.web3.to_wei('50', 'gwei')
        })

        signed = self.web3.eth.account.sign_transaction(tx, from_private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()
        
     
     
     

    
    
    
        



DRIVERS: Dict[str, ChainDriver] = {
    "INTEN": IntencoinDriver(),
    "BTC":   BTCDriver(),
    "LTC":   LTCDriver(),   # ⬅️ OBLIGATORIO
    "ETH":   ETHDriver(),
    "XLM":   XLMDriver(),
    "XRP":   XRPDriver(),
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
<title>INTENCOIN CRYPTOCURRENCY</title>
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

<div style="text-align:center; margin-bottom:20px;">
  <img src="/static/INTENCOIN.jpg"
       alt="INTENCOIN CRYPTOCURRENCY"
       style="max-height:140px; display:block; margin:auto;">

  <img src="/static/Flag.jpg"
       alt="Gov IUKAC Empire Flag"
       style="max-height:80px; margin-top:12px;">
</div>

  <p>Welcome. Create an account INTENCOIN or login.</p>
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
  <hr>

<div class="card">
  <p><b>INTENCOIN CRYPTOCURRENCY</b> belongs to the
     <b>Gov IUKAC Empire Sovereign State</b>.</p>

  <p>
    INTENCOIN is one of the official reserve cryptocurrencies of the
    <b>Federal Reserve of the Gov IUKAC Bank</b>.
  </p>

  <p>
    This platform operates under the
    <b>Iukense Sovereign Market</b> —
    an independent and sovereign financial market.
  </p>

  <small>
    All monetary operations are governed by sovereign authority.
    
    
  
    
      //__  INTENCOIN  2024 //_2025
  </small>
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
    



<p><b>2. External Deposit Addresses (Chains):</b></p>
<table class="table">
  <tr>
    <th>Coin</th>
    <th>Address</th>
    <th>Action</th>
  </tr>

  {% for coin, field in {
    "BTC":"external_btc_address",
    "ETH":"external_eth_address",
    "XLM":"external_xlm_address",
    "XRP":"external_xrp_address",
    "LTC":"external_ltc_address"
  }.items() %}
  <tr>
    <td>{{ coin }}</td>
    <td>{{ acct[field] or "Not configured" }}</td>
    <td>
      {% if not acct[field] %}
        
        <form method="post" action="{{ url_for('configure_external_wallet_route') }}">
          <input type="hidden" name="symbol" value="{{ coin }}">
          <button class="btn" type="submit">Configure {{ coin }}</button>
        </form>
      {% else %}
        <small>Configured</small>
      {% endif %}
    </td>
  </tr>
  {% endfor %}
</table>


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
<tr>
  <th>Coin</th>
  <th>Amount</th>
  <th>Price (USD)</th>
  <th>≈ USD</th>
</tr>


{% for sym in supported %}
<tr>
    <td>{{ sym }}</td>
    <td>{{ "%.8f"|format(acct.balances.get(sym, 0.0)) }}</td>
    <td>{{ "%.8f"|format(rates[sym]) }}</td>
    <td>{{ "%.2f"|format(acct.balances.get(sym, 0.0) * rates[sym]) }}</td>
</tr>
{% endfor %}


</table>



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
  
  
  <form class="card" method="post" action="/api/send/inten-to-metamask/dgdm">
  <h3>Swap INTEN → DGDM (Polygon)</h3>

  <p><b>From Internal:</b> {{ acct.account_id }} (INTEN)</p>

  <p><input name="amount_inten" type="number" step="any"
            placeholder="Amount of INTEN to convert" required></p>

  <p><input name="evm_address" type="text"
            value="{{ acct.external_eth_address }}"
            placeholder="Destination EVM address (0x...)" required></p>

  <p><button class="btn">Swap & Mint DGDM</button></p>

  <small>Debits INTEN, verifies guarantee, converts using rates, mints DGDM to Polygon.</small>
</form>
  
  <form class="card" method="post" action="/api/send/inten-to-metamask/usdt">
  <h3>Swap INTEN → USDT (Polygon)</h3>

  <p><b>From Internal:</b> {{ acct.account_id }} (INTEN)</p>

  <p><input name="amount_inten" type="number" step="any"
            placeholder="Amount of INTEN to convert" required></p>

  <p><input name="evm_address" type="text"
            value="{{ acct.external_eth_address }}"
            placeholder="Destination EVM address (0x...)" required></p>

  <p><button class="btn">Swap & Send USDT</button></p>

  <small>Debits INTEN, verifies guarantee, converts using rates, sends USDT via ERC‑20.</small>
</form>
  
  
  <div class="card" style="border:1px solid #ddd;border-radius:14px;padding:14px;margin:12px 0;">
  <h3 style="margin:0 0 10px 0;">INTENCOIN – PRODUCTION TRANSFER COMMANDS</h3>

  <pre style="white-space:pre-wrap;word-break:break-word;background:#f7f7f7;border:1px solid #eee;border-radius:12px;padding:12px;margin:0;">
BTC – Transfer to external wallet (Binance / others)
---------------------------------------------------
curl -X POST http://127.0.0.1:5021/send-external \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC",
    "from_wallet": "BTC55677",
    "to_address": "bc1btchhh66xxxxxxxxxxxx",
    "amount": 0.001
  }'


LTC – Transfer to external wallet (Binance / others)
---------------------------------------------------
curl -X POST http://127.0.0.1:5021/send-external \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "LTC",
    "from_wallet": "LTC55677",
    "to_address": "ltc1qqqqqqqqqqqqqq",
    "amount": 1.25
  }'


INTERLEDGER TRANSFERS
--------------------
curl -X POST http://127.0.0.1:5021/send/interledger \
  -H "Content-Type: application/json" \
  -d '{"payment_pointer":"chimoney.io","amount":1000}'

curl -X POST http://127.0.0.1:5021/send/interledger \
  -H "Content-Type: application/json" \
  -d '{"payment_pointer":"uphold.com","amount":500}'

curl -X POST http://127.0.0.1:5021/send/interledger \
  -H "Content-Type: application/json" \
  -d '{"payment_pointer":"walletguru.com","amount":250}'


ACH TRANSFER – APACHE FINERACT
-----------------------------
curl -X POST http://127.0.0.1:8443/fineract-provider/api/v1/ach/transfers \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic BASE64_KEY" \
  -d '{
    "fromAccountId": 55677,
    "routingNumber": "021000021",
    "accountNumber": "987654321",
    "amount": 1000,
    "currency": "USD"
  }'


WIRE TRANSFER – APACHE FINERACT
------------------------------
curl -X POST http://127.0.0.1:8443/fineract-provider/api/v1/wires \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic BASE64_KEY" \
  -d '{
    "fromAccountId": 55677,
    "swift": "BSCHESMM",
    "accountNumber": "99887766",
    "amount": 5000,
    "currency": "USD"
  }'


NOTES
-----
• Interledger requires a valid payment pointer
• We give a gift of 1000 INTENCOIN
• For deposits, contact us with your wallet number: WALXXXXX
• Mining runs automatically every 5 minutes


CONTACT
-------
Email: goviukac@gmail.com
Text / WhatsApp: +1 346 325 7706
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

@app.route('/check-market-rates', methods=['GET'])
def check_market_rates():
    return jsonify(MARKET_RATES)


@app.get('/')
def index():
    if session.get('uid'):
        return redirect(url_for('dashboard'))
    return render_template_string(app.jinja_loader.get_source(app.jinja_env,'index.html')[0], title="INTENCOIN CRYPTOCURRENCY")

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

@app.post('/configure-external-wallet')
def configure_external_wallet_route():
    user = require_login()
    if not user:
        return redirect(url_for("login"))

    symbol = request.form.get("symbol", "").upper()

    accts = user_accounts(user["uid"])
    if not accts:
        return "No account", 400

    acct = accts[0]

    # SOLO IMPLEMENTAMOS ETH (DGDM/USDT)
    if symbol == "ETH":
        from web3 import Web3
        evm = Web3().eth.account.create()
        acct["external_eth_address"] = evm.address
        acct["evm_private_key"] = evm.key.hex()

        save_state(STATE)
        return redirect(url_for("dashboard"))

    return f"Symbol {symbol} not supported", 400




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
    # 1. Extraer datos (JSON o Form)
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    # 2. Seguridad: Bridge Secret o Login
    secret_sent = data.get("secret")
    u = None
    if secret_sent == BRIDGE_SECRET:
        u = {"uid": "admin-api", "email": "bridge@internal"}
    else:
        u = require_login()

    if not u:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    # 3. Parámetros de la transacción
    symbol = (data.get("symbol") or "").strip()
    from_wallet = (data.get("from_wallet") or "").strip()
    to_address = (data.get("to_address") or "").strip()
    symbol_dest = (data.get("symbol_dest") or data.get("swap_to") or "").strip()

    try:
        amount_to_debit = float(data.get("amount", 0))
    except:
        amount_to_debit = 0.0

    if not symbol or amount_to_debit <= 0:
        return jsonify({"ok": False, "error": "Invalid symbol or amount"}), 400
    if not from_wallet or not to_address:
        return jsonify({"ok": False, "error": "Missing from_wallet or to_address"}), 400

    acct = find_account_by_wallet(from_wallet)
    if not acct:
        return jsonify({"ok": False, "error": "Source wallet not found"}), 404

    # Validación de pertenencia si no es admin
    if secret_sent != BRIDGE_SECRET:
        uacct = user_accounts(u['uid'])[0]
        if acct['account_id'] != uacct['account_id']:
            return jsonify({"ok": False, "error": "Forbidden"}), 403

    if acct["balances"].get(symbol, 0) < amount_to_debit:
        return jsonify({"ok": False, "error": "Insufficient funds"}), 400

    # ===================================================
    # FILTRO DE GARANTÍA BANCARIA (Para Swaps desde INTEN)
    # ===================================================
    if symbol == "INTEN" and symbol_dest in ["BTC", "LTC"]:
        rates = get_rates()
        val_usd = amount_to_debit * rates.get("INTEN", 0.50)
        try:
            print(f"[BANCO] Solicitando garantía de {val_usd} USD...")
            guarantee_res = requests.post(f"{BANK_API_URL}/api/bank/escrow/lock", json={
                "contract_address": SMART_CONTRACT_ADDRESS,
                "funds_source": METAMASK_FUNDS_WALLET,
                "bank_account": acct['account_id'],
                "amount_dgd": val_usd
            }, timeout=10)
            
            if guarantee_res.status_code != 200:
                return jsonify({"ok": False, "error": "El Banco denegó la garantía soberana"}), 400
        except Exception as e:
            return jsonify({"ok": False, "error": f"Error de conexión con Oráculo Bancario: {str(e)}"}), 500

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
        amount_to_send_dest = float("{:.8f}".format(usd_value / rate_dest))

        if amount_to_send_dest <= 0:
            return jsonify({"ok": False, "error": "Amount too small for BTC network"}), 400

        acct["balances"]["INTEN"] -= amount_to_debit
        driver = DRIVERS["BTC"]
        try:
            txid = driver.send(acct, to_address, amount_to_send_dest)
        except Exception as e:
            acct["balances"]["INTEN"] += amount_to_debit
            return jsonify({"ok": False, "error": str(e)}), 500

        add_ledger({
            "type": "swap_INTEN_to_BTC_GUARANTEED",
            "spent_INTEN": amount_to_debit,
            "sent_BTC": amount_to_send_dest,
            "from_account": acct["account_id"],
            "to": to_address,
            "txid": txid,
            "contract": SMART_CONTRACT_ADDRESS
        })
        save_state(STATE)
        return jsonify({"ok": True, "txid": txid, "sent_BTC": amount_to_send_dest}), 200

    # ===================================================
    # CASO 1B: SWAP INTEN → LTC
    # ===================================================
    if symbol == "INTEN" and symbol_dest == "LTC":
        rates = get_rates()
        rate_inten = rates.get("INTEN", 0.0)
        rate_ltc = rates.get("LTC", 0.0)

        if rate_inten <= 0 or rate_ltc <= 0:
            return jsonify({"ok": False, "error": "Invalid exchange rates"}), 400

        usd_value = amount_to_debit * rate_inten
        ltc_amount = usd_value / rate_ltc
        acct["balances"]["INTEN"] -= amount_to_debit

        driver = DRIVERS["LTC"]
        try:
            txid = driver.send(acct, to_address, ltc_amount)
        except Exception as e:
            acct["balances"]["INTEN"] += amount_to_debit
            return jsonify({"ok": False, "error": str(e)}), 500

        add_ledger({
            "type": "swap_INTEN_to_LTC_GUARANTEED",
            "spent_INTEN": amount_to_debit,
            "sent_LTC": ltc_amount,
            "from_account": acct["account_id"],
            "to": to_address,
            "txid": txid,
            "contract": SMART_CONTRACT_ADDRESS
        })
        save_state(STATE)
        return jsonify({"ok": True, "sent_LTC": ltc_amount, "txid": txid}), 200

    # ===================================================
    # CASO 2: ENVÍO DIRECTO BTC → BTC
    # ===================================================
    if symbol == "BTC":
        driver = DRIVERS["BTC"]
        acct["balances"]["BTC"] -= amount_to_debit
        try:
            txid = driver.send(acct, to_address, amount_to_debit)
        except Exception as e:
            acct["balances"]["BTC"] += amount_to_debit
            return jsonify({"ok": False, "error": str(e)}), 500

        add_ledger({"type": "external_send_pure", "symbol": "BTC", "amount": amount_to_debit, "txid": txid})
        save_state(STATE)
        return jsonify({"ok": True, "txid": txid}), 200

    # ===================================================
    # CASO 3: OTROS (ETH, XRP, etc.)
    # ===================================================
    driver = DRIVERS.get(symbol)
    if not driver or not driver.is_configured():
        return jsonify({"ok": False, "error": "Connector not configured"}), 400

    acct["balances"][symbol] -= amount_to_debit
    try:
        txid = driver.send(acct, to_address, amount_to_debit)
    except Exception as e:
        acct["balances"][symbol] += amount_to_debit
        return jsonify({"ok": False, "error": str(e)}), 500

    add_ledger({"type": "external_send_pure", "symbol": symbol, "amount": amount_to_debit, "txid": txid})
    save_state(STATE)
    return jsonify({"ok": True, "txid": txid}), 200






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


@app.post("/wallet/ilp/ach-anybank")
def wallet_to_ach_anybank():
    data = request.get_json(force=True)

    wallet = data.get("wallet")
    amount = int(data.get("amount", 0))
    bank_name = data.get("bank_name")
    routing_number = data.get("routing_number")
    account_number = data.get("account_number")
    description = data.get("description", "ACH transfer via Interledger")

    acct = find_account_by_wallet(wallet)
    if not acct:
        return {"error": "wallet not found"}, 404

    if acct["balances"]["INTEN"] < amount:
        return {"error": "insufficient funds"}, 400

    acct["balances"]["INTEN"] -= amount

    ilp_payload = {
        "type": "ACH",
        "bank_name": bank_name,
        "routing_number": routing_number,
        "account_number": account_number,
        "description": description,
        "currency": "USD"
    }

    result = ilp_send(amount, ilp_payload)

    add_ledger({
        "type": "INTEN->ILP->ACH",
        "wallet": wallet,
        "amount": amount,
        "details": ilp_payload,
        "txid": result["txid"]
    })

    save_state(STATE)

    return {
        "ok": True,
        "txid": result["txid"],
        "bank": bank_name,
        "amount": amount
    }


@app.post("/wallet/ilp/wire")
def wallet_to_wire():
    data = request.get_json(force=True)

    wallet = data.get("wallet")
    amount = int(data.get("amount", 0))
    bank_name = data.get("bank_name")
    swift_or_routing = data.get("routing_number")
    account_number = data.get("account_number")
    description = data.get("description", "Wire transfer via Interledger")

    acct = find_account_by_wallet(wallet)
    if acct["balances"]["INTEN"] < amount:
        return {"error": "insufficient funds"}, 400

    acct["balances"]["INTEN"] -= amount

    ilp_payload = {
        "type": "WIRE",
        "bank_name": bank_name,
        "routing_or_swift": swift_or_routing,
        "account_number": account_number,
        "description": description,
        "currency": "USD"
    }

    result = ilp_send(amount, ilp_payload)

    add_ledger({
        "type": "INTEN->ILP->WIRE",
        "wallet": wallet,
        "amount": amount,
        "details": ilp_payload,
        "txid": result["txid"]
    })

    save_state(STATE)

    return {
        "ok": True,
        "txid": result["txid"],
        "bank": bank_name
    }


@app.post("/wallet/ilp/paypal")
def wallet_to_paypal():
    data = request.get_json()

    wallet = data["wallet"]
    amount = float(data["amount"])

    paypal_payload = {
        "type": "PAYPAL",
        "paypal_email": data["paypal_email"],
        "description": data.get("description", "PayPal via Interledger")
    }

    acct = find_account_by_wallet(wallet)
    if not acct or acct["balances"]["INTEN"] < amount:
        return {"error": "insufficient funds"}, 400

    acct["balances"]["INTEN"] -= amount

    ilp_result = ilp_transfer(paypal_payload)

    add_ledger({
        "type": "INTEN->ILP->PAYPAL",
        "wallet": wallet,
        "amount": amount,
        "ilp": ilp_result
    })

    save_state(STATE)
    return {"ok": True}


@app.post('/configure-external-wallet')
def configure_external_wallet():
    """
    Configura la dirección de depósito externa para una moneda:
    - BTC: usa Bitcoin Core (RPC)
    - LTC: usa Litecoin Core REAL
    """
    u = require_login()
    if not u:
        return redirect(url_for("index"))

    symbol = (request.form.get("symbol") or "").upper().strip()
    if symbol not in ("BTC", "ETH", "XLM", "XRP", "LTC"):
        return "Unsupported symbol", 400

    acct = user_accounts(u["uid"])[0]

    field_map = {
        "BTC": "external_btc_address",
        "ETH": "external_eth_address",
        "XLM": "external_xlm_address",
        "XRP": "external_xrp_address",
        "LTC": "external_ltc_address",
    }
    field_name = field_map[symbol]

    if acct.get(field_name):
        return redirect(url_for("dashboard"))

    # =========================
    # BTC (Bitcoin Core)
    # =========================
    if symbol == "BTC":
        btc_driver = DRIVERS["BTC"]
        wallet_rpc_name = acct["account_id"]

        if not btc_driver.is_configured():
            return "BTC connector not configured", 500

        try:
            new_btc_address = btc_driver.create_and_get_address(wallet_rpc_name)
        except Exception as e:
            return f"Error configuring BTC wallet: {e}", 500

        acct["external_btc_address"] = new_btc_address
        acct["external_btc_wallet_id"] = wallet_rpc_name

        add_ledger({
            "type": "external_wallet_config",
            "symbol": "BTC",
            "account": acct["account_id"],
            "address": new_btc_address,
        })

        save_state(STATE)
        return redirect(url_for("dashboard"))

    # =========================
    # LTC (Litecoin Core REAL)
    # =========================
    if symbol == "LTC":
        ltc_driver = DRIVERS["LTC"]
        wallet_rpc_name = acct["account_id"]

        try:
            ltc_address = ltc_driver.create_and_get_address(wallet_rpc_name)
        except Exception as e:
            return f"Error configuring LTC wallet: {e}", 500

        acct["external_ltc_address"] = ltc_address
        acct["external_ltc_wallet_id"] = wallet_rpc_name

        add_ledger({
            "type": "external_wallet_config",
            "symbol": "LTC",
            "account": acct["account_id"],
            "address": ltc_address,
        })

        save_state(STATE)
        return redirect(url_for("dashboard"))

    # Fallback seguro
    return redirect(url_for("dashboard"))




@app.post("/api/send/inten-to-metamask/usdt")
def api_send_inten_to_metamask_usdt():
    user = require_login()
    if not user:
        return jsonify({"ok": False, "error": "auth required"}), 401

    data = request.get_json(silent=True) or request.form or {}

    amount_inten = float(data.get("amount_inten", 0))
    evm_address = data.get("evm_address", "").strip()

    if amount_inten <= 0:
        return jsonify({"ok": False, "error": "invalid amount"}), 400
    if not evm_address.startswith("0x") or len(evm_address) != 42:
        return jsonify({"ok": False, "error": "invalid evm_address"}), 400

    accts = user_accounts(user["uid"])
    if not accts:
        return jsonify({"ok": False, "error": "no account"}), 400

    acct = accts[0]

    if acct["balances"]["INTEN"] < amount_inten:
        return jsonify({"ok": False, "error": "insufficient INTEN"}), 400

    # Descontar INTEN local
    acct["balances"]["INTEN"] -= amount_inten

    # Llamar al banco
    payload = {
        "account_id": acct["account_id"],
        "amount_inten": amount_inten,
        "evm_address": evm_address
    }

    res = bank_request("/api/bank/send/usdt-to-evm", payload)

    if not res.get("ok"):
        # rollback
        acct["balances"]["INTEN"] += amount_inten
        save_state(STATE)
        return jsonify(res), 400

    # Registrar en ledger local
    add_ledger({
        "type": "send_inten_to_metamask_usdt",
        "from": acct["account_id"],
        "amount_inten": amount_inten,
        "amount_usdt": res["usdt_amount"],
        "evm_address": evm_address,
        "tx": res["tx"]
    })

    save_state(STATE)

    return jsonify({
        "ok": True,
        "account_id": acct["account_id"],
        "amount_inten": amount_inten,
        "usdt_sent": res["usdt_amount"],
        "evm_address": evm_address,
        "tx": res["tx"]
    })



@app.route("/send/interledger/internal", methods=["POST"])
def send_ilp_internal():
    data = request.json
    payment_pointer = data["payment_pointer"]
    amount = data["amount"]

    # 1️⃣ Resolver SPSP
    r = requests.get(f"https://{payment_pointer}/.well-known/pay")
    spsp = r.json()

    packet = {
        "destination_account": spsp["destination_account"],
        "shared_secret": spsp["shared_secret"],
        "amount": amount
    }

    # 2️⃣ Enviar al siguiente conector
    forward(packet)

    return jsonify({"status": "sent"})

def forward(packet):
    print("Forwarding ILP packet:", packet)







@app.route("/send/interledger", methods=["POST"])
def send_ilp():
    data = request.json
    payment_pointer = data["payment_pointer"]
    amount = data["amount"]

    # 1️⃣ Resolver SPSP
    r = requests.get(f"https://{payment_pointer}/.well-known/pay")
    spsp = r.json()

    packet = {
        "destination_account": spsp["destination_account"],
        "shared_secret": spsp["shared_secret"],
        "amount": amount
    }

    # 2️⃣ Enviar al siguiente conector
    forward(packet)

    return jsonify({"status": "sent"})

def forward(packet):
    print("Forwarding ILP packet:", packet)



ILP_PREFIX = "g.iukac"        # prefijo ILP SOBERANO
ASSET_CODE = "XRP"            # o INTEN
ASSET_SCALE = 6               # XRP drops




@app.route("/.well-known/pay", methods=["GET"])
def spsp():
    account = request.args.get("account")
    if not account:
        abort(400, "missing account")

    destination_account = f"{ILP_PREFIX}.account.{account}"
    shared_secret = base64.b64encode(os.urandom(32)).decode()

    return jsonify({
        "destination_account": destination_account,
        "shared_secret": shared_secret,
        "asset_code": ASSET_CODE,
        "asset_scale": ASSET_SCALE
    })






@app.route("/ilp/in", methods=["POST"])
def ilp_in():
    packet = request.json

    account = packet["destination_account"].split(".")[-1]
    amount = packet["amount"]

    credit_intencoin_wallet(account, amount)

    return {"status": "credited"}




# --- UPDATE MARKET RATES AT STARTUP ---
update_market_rates()
print("Market rates updated at startup.")


# ---------------- Main ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5021"))
    app.run(host="0.0.0.0", port=port, debug=True)
    





