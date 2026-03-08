
# -*- coding: utf-8 -*-
# Blockchain INTEN – compatible con Wallet 5021

from flask import Flask, request, jsonify
import time, threading, hashlib, json, requests

app = Flask(__name__)

# ------------------------------
# CONFIG
# ------------------------------

# URL de la Wallet (5021)
WALLET_URL = "http://127.0.0.1:5021/api/bridge/deposit"
BRIDGE_SECRET = "dev-bridge-secret"   # Misma clave que usa la Wallet

MINING_INTERVAL = 300   # 5 minutos


# ------------------------------
# ESTADO DEL BLOCKCHAIN
# ------------------------------

blockchain = []
pending_txs = []       # Transacciones INTEN recibidas desde la wallet
registered_wallets = set()   # Wallets que deben recibir recompensa


# ------------------------------
# FUNCIONES BLOCKCHAIN
# ------------------------------

def create_genesis_block():
    return {
        "index": 1,
        "timestamp": time.time(),
        "transactions": [],
        "proof": 100,
        "previous_hash": "1"
    }

def hash_block(block):
    return hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()

def valid_proof(last_proof, proof):
    guess = f"{last_proof}{proof}".encode()
    return hashlib.sha256(guess).hexdigest()[:4] == "0000"

def proof_of_work(last_proof):
    proof = 0
    while not valid_proof(last_proof, proof):
        proof += 1
    return proof


# ------------------------------
# MANEJO DE RECOMPENSAS
# ------------------------------

def send_reward_to_wallet(wallet_addr, amount):
    payload = {
        "wallet": wallet_addr,
        "symbol": "INTEN",
        "amount": amount,
        "secret": BRIDGE_SECRET
    }

    try:
        r = requests.post(WALLET_URL, json=payload, timeout=5)
        print(f"   → Recompensa enviada a {wallet_addr}: {amount} INTEN | Respuesta {r.status_code}")
    except Exception as e:
        print(f"⚠️ ERROR enviando recompensa a {wallet_addr}: {e}")


# ------------------------------
# MINADO AUTOMÁTICO
# ------------------------------

def mine_block():
    global pending_txs

    last_block = blockchain[-1]
    last_proof = last_block["proof"]
    proof = proof_of_work(last_proof)
    previous_hash = hash_block(last_block)

    # Determinar recompensa
    if pending_txs:
        reward_amount = 50
    else:
        reward_amount = 20

    block = {
        "index": len(blockchain) + 1,
        "timestamp": time.time(),
        "transactions": list(pending_txs),
        "proof": proof,
        "previous_hash": previous_hash
    }

    blockchain.append(block)

    print("===========================================")
    print(f"[MINADO] Bloque {block['index']} generado")
    print(f"   TXS pendientes: {len(pending_txs)}")
    print(f"   Wallets registradas: {len(registered_wallets)}")
    print(f"   Recompensa por wallet: {reward_amount} INTEN")
    print("===========================================")

    # Enviar recompensa a cada wallet registrada
    for wal in registered_wallets:
        send_reward_to_wallet(wal, reward_amount)

    pending_txs = []


def automated_mining():
    mine_block()
    threading.Timer(MINING_INTERVAL, automated_mining).start()


# ------------------------------
# ENDPOINT: NOTIFICACIÓN DESDE WALLET (5021)
# ------------------------------

@app.post("/api/notify_deposit")
def notify_deposit():
    data = request.get_json(force=True)

    wallet = data.get("wallet")
    amount = float(data.get("amount", 0))
    symbol = data.get("symbol")
    secret = data.get("secret")

    if secret != BRIDGE_SECRET:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    if not wallet or amount <= 0 or symbol != "INTEN":
        return jsonify({"ok": False, "error": "invalid data"}), 400

    # Registrar wallet para recompensas futuras
    registered_wallets.add(wallet)

    # Registrar transacción para minado de 50 INTEN
    pending_txs.append({
        "wallet": wallet,
        "amount": amount,
        "timestamp": time.time()
    })

    print(f"✔️ Notificación recibida | TX de {amount} INTEN a {wallet}")
    print(f"   Wallets registradas: {len(registered_wallets)}")
    print(f"   TXs pendientes: {len(pending_txs)}")

    return jsonify({"ok": True})



@app.post("/api/miner/notify")
def miner_notify():
    data = request.get_json(force=True)

    # Validar secreto
    if data.get("secret") != BRIDGE_SECRET:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    wallet_addr = data.get("wallet")
    amount = float(data.get("amount", 0))

    if not wallet_addr or amount <= 0:
        return jsonify({"ok": False, "error": "invalid data"}), 400

    # Registrar la wallet si no existe
    if wallet_addr not in wallets:
        wallets[wallet_addr] = 0  # saldo inicial
        print(f"✔ Wallet nueva registrada en blockchain: {wallet_addr}")

    # Registrar la transacción pendiente para minería
    transactions.append({
        "wallet": wallet_addr,
        "amount": amount,
        "timestamp": time.time()
    })

    print(f"✔️ Notificación recibida: {amount} INTEN para {wallet_addr}.")
    print(f"➡ Total transacciones pendientes: {len(transactions)}")

    return jsonify({"ok": True, "registered_wallet": wallet_addr})











# ------------------------------
# MAIN
# ------------------------------

if __name__ == "__main__":
    blockchain.append(create_genesis_block())
    print("[RUN] Blockchain INTEN escuchando en puerto 5001")
    automated_mining()
    app.run(host="0.0.0.0", port=5003)




0

