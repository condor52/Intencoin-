
# miner_5001.py
# Servicio Blockchain/Minero (PUERTO 5001)
# - Recibe notificaciones de la wallet (5021) en /api/notify_deposit
# - Mina cada 5 minutos:
#     * si hubo transacciones pendientes en la ventana -> recompensa 50 INTEN por cada wallet pendiente
#     * si no hubo transacciones -> recompensa 20 INTEN a TODAS las wallets registradas
# - Paga la recompensa llamando a /api/bridge/deposit de la wallet (5021)

from flask import Flask, request, jsonify
import os, time, threading, uuid, hashlib, json
import requests

app = Flask(__name__)

# ======= CONFIG =======
WALLET_BRIDGE_DEPOSIT = os.environ.get("WALLET_BRIDGE_DEPOSIT", "http://127.0.0.1:5021/api/bridge/deposit")
BRIDGE_SECRET         = os.environ.get("BRIDGE_SECRET", "dev-bridge-secret")
MINE_INTERVAL_SEC     = int(os.environ.get("MINE_INTERVAL_SEC", "300"))  # 300 = 5 minutos

# ======= STATE (in-memory) =======
blockchain    = []
pending_txs   = []   # cada elemento: {"wallet": "...", "amount": float, "symbol": "INTEN", "ts": float}
registered_ws = set()  # wallets conocidas (las que recibieron algo alguna vez)

# ======= BLOCKCHAIN UTILS =======
def create_genesis_block():
    return {"index": 1, "timestamp": time.time(), "transactions": [], "proof": 100, "previous_hash": "1"}

def hash_block(block):
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

def valid_proof(last_proof, proof):
    guess = f"{last_proof}{proof}".encode()
    return hashlib.sha256(guess).hexdigest()[:4] == "0000"

def proof_of_work(last_proof):
    proof = 0
    while not valid_proof(last_proof, proof):
        proof += 1
    return proof

def create_block(proof, previous_hash, txs):
    block = {
        "index": len(blockchain) + 1,
        "timestamp": time.time(),
        "transactions": txs,
        "proof": proof,
        "previous_hash": previous_hash,
    }
    return block

# ======= REWARD / PAY =======
def _pay_reward_to_wallet(wallet_addr: str, amount: float):
    """Paga recompensa llamando al bridge de la wallet en 5021."""
    try:
        payload = {
            "wallet": wallet_addr,
            "symbol": "INTEN",
            "amount": amount,
            "secret": BRIDGE_SECRET
        }
        r = requests.post(WALLET_BRIDGE_DEPOSIT, json=payload, timeout=8)
        r.raise_for_status()
        return True, r.json()
    except Exception as e:
        return False, str(e)

# ======= MINER LOOP =======
def mine_once():
    # 1) Setup último bloque
    last_block = blockchain[-1] if blockchain else create_genesis_block()
    if not blockchain:
        blockchain.append(last_block)
    last_proof = last_block["proof"]

    # 2) PoW
    proof = proof_of_work(last_proof)
    prev_hash = hash_block(last_block)

    # 3) Decidir recompensa
    #    - Si hay txs pendientes: 50 INTEN por cada wallet en pending_txs
    #    - Si NO hay txs pendientes: 20 INTEN por cada wallet registrada (si no hay ninguna registrada aún, no paga a nadie)
    local_txs = []
    had_activity = len(pending_txs) > 0

    if had_activity:
        # Recompensa 50 INTEN por wallet con actividad
        wallets_to_reward = sorted({t["wallet"] for t in pending_txs})
        for w in wallets_to_reward:
            ok, info = _pay_reward_to_wallet(w, 50.0)
            local_txs.append({
                "type": "reward",
                "wallet": w,
                "amount": 50.0,
                "symbol": "INTEN",
                "bridge_ok": ok,
                "bridge_info": info,
            })
        # limpiar ventana de pendientes
        pending_txs.clear()
    else:
        # Sin actividad: 20 INTEN a TODAS las wallets registradas
        for w in sorted(registered_ws):
            ok, info = _pay_reward_to_wallet(w, 20.0)
            local_txs.append({
                "type": "idle_reward",
                "wallet": w,
                "amount": 20.0,
                "symbol": "INTEN",
                "bridge_ok": ok,
                "bridge_info": info,
            })

    # 4) Crear bloque con las "txs" de recompensa (registro contable del minero)
    block = create_block(proof, prev_hash, local_txs)
    blockchain.append(block)
    print(f"[MINER] Bloque {block['index']} minado | {'TX detectadas' if had_activity else 'sin TX'} | rewards: {len(local_txs)}")

def mining_loop():
    while True:
        try:
            mine_once()
        except Exception as e:
            print(f"[MINER] Error en mining_loop: {e}")
        time.sleep(MINE_INTERVAL_SEC)

# ======= API =======
@app.post("/api/notify_deposit")
def notify_deposit():
    """
    Llamado por la wallet (5021) cuando se acredita un depósito en /api/bridge/deposit_new.
    Body JSON:
    { "wallet": "WALADDR-...", "amount": 123.45, "symbol": "INTEN", "secret": "dev-bridge-secret" }
    """
    data = request.get_json(force=True) or {}
    if data.get("secret") != BRIDGE_SECRET:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    wallet = (data.get("wallet") or "").strip()
    symbol = (data.get("symbol") or "").strip()
    try:
        amount = float(data.get("amount", 0))
    except:
        amount = 0.0

    if not wallet or amount <= 0 or symbol != "INTEN":
        return jsonify({"ok": False, "error": "invalid payload"}), 400

    registered_ws.add(wallet)
    pending_txs.append({
        "wallet": wallet,
        "amount": amount,
        "symbol": symbol,
        "ts": time.time()
    })
    return jsonify({"ok": True, "queued": True})

@app.get("/api/chain")
def api_chain():
    return jsonify({"ok": True, "height": len(blockchain), "chain": blockchain[-10:]})

if __name__ == "__main__":
    # Génesis
    if not blockchain:
        blockchain.append(create_genesis_block())
    # Loop minero en hilo aparte
    t = threading.Thread(target=mining_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5003)





