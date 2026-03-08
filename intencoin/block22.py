
# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import time, threading, hashlib, json, requests
from datetime import datetime

app = Flask(__name__)

# ================================
# CONFIG
# ================================
BRIDGE_SECRET = "dev-bridge-secret"         # Debe ser EXACTAMENTE el mismo de la Wallet
WALLET_URL = "http://127.0.0.1:5021/api/bridge/deposit"
MINING_INTERVAL = 300  # 5 minutos

# ================================
# ESTADO EN MEMORIA
# ================================
wallets = set()          # Lista de wallets registradas
pending_txs = []         # Lista de transacciones pendientes
blockchain = []          # Cadena de bloques

# ================================
# HERRAMIENTAS
# ================================
def hash_block(block):
    return hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()

def create_block(transactions, reward_amount):
    block = {
        "index": len(blockchain) + 1,
        "timestamp": time.time(),
        "transactions": transactions,
        "reward": reward_amount,
        "previous_hash": hash_block(blockchain[-1]) if blockchain else "GENESIS"
    }
    blockchain.append(block)
    return block

# ================================
# PAGO REAL A LA WALLET
# ================================
def pay_wallet(wallet_addr, amount):
    payload = {
        "wallet": wallet_addr,
        "symbol": "INTEN",
        "amount": amount,
        "secret": BRIDGE_SECRET
    }
    try:
        r = requests.post(WALLET_URL, json=payload, timeout=5)
        print(f"[PAY] Pago enviado a {wallet_addr}: {amount} INTEN → Respuesta: {r.text}")
    except Exception as e:
        print(f"[PAY] ERROR enviando pago a wallet {wallet_addr}: {e}")

# ================================
# MINAR BLOQUE
# ================================
def mine(auto=False):
    global pending_txs

    has_tx = len(pending_txs) > 0

    if has_tx:
        reward = 50
        print("[MINER] Minado por transacción → recompensa 50 por wallet")
    else:
        reward = 20
        print("[MINER] Minado automático → recompensa 20 por wallet")

    txs = pending_txs.copy()
    pending_txs = []

    for w in wallets:
        pay_wallet(w, reward)

    block = create_block(txs, reward)

    print(f"[BLOCK] Bloque {block['index']} minado | TXs: {len(txs)} | Wallets: {len(wallets)} | Reward: {reward}")

# ================================
# MINADO AUTOMÁTICO
# ================================
def auto_miner():
    while True:
        time.sleep(MINING_INTERVAL)
        try:
            mine(auto=True)
        except Exception as e:
            print("[AUTO-MINER] Error:", e)

threading.Thread(target=auto_miner, daemon=True).start()

# ================================
# API → RECIBIR NOTIFICACION
# ================================
@app.post("/api/notify_deposit")
def notify_deposit():
    data = request.get_json(force=True)

    if data.get("secret") != BRIDGE_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    wallet = data.get("wallet")
    amount = data.get("amount", 0)

    if not wallet:
        return jsonify({"error": "invalid wallet"}), 400

    wallets.add(wallet)

    tx = {
        "wallet": wallet,
        "amount": amount,
        "timestamp": datetime.utcnow().isoformat()
    }
    pending_txs.append(tx)

    print(f"✔️ Notificación recibida de {wallet}: {amount} INTEN → Total TX pendientes: {len(pending_txs)}")

    # Minado inmediato por llegada de transacción
    mine(auto=False)

    return jsonify({"ok": True})

# ================================
# MAIN
# ================================
if __name__ == "__main__":
    print("[RUN] Minero escuchando en 0.0.0.0:5001 …")
    app.run(host="0.0.0.0", port=5003)





