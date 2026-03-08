# -*- coding: utf-8 -*-
"""
blockchain_5001.py
Nodo Blockchain de Intencoin en el puerto 5001.

- Recibe notificaciones de la Wallet (5020) en /api/miner/notify
- Guarda transacciones pendientes en memoria
- Mina bloques automáticamente cada 300 segundos (5 minutos)
- Después de minar un bloque, envía recompensa a cada wallet que participó
  usando /api/bridge/deposit_new del servidor 5020
- Expone /get_blockchain y /get_transactions (evita 404 en tus pruebas)
"""

from flask import Flask, request, jsonify
import time
import hashlib
import uuid
import threading
import requests
import os

# ==============================
# CONFIGURACIÓN
# ==============================

app = Flask(__name__)

# Debe coincidir con BRIDGE_SECRET del wallet 5020
BRIDGE_SECRET = os.environ.get("BRIDGE_SECRET", "dev-bridge-secret")

# URL del bridge de la wallet (5020)
WALLET_BRIDGE_URL = os.environ.get(
    "WALLET_BRIDGE_URL",
    "http://127.0.0.1:5021/api/bridge/deposit_new"
)

# Intervalo de minería automática (segundos) -> 300 = 5 minutos
MINING_INTERVAL = int(os.environ.get("MINING_INTERVAL", "300"))

# Recompensa por wallet en cada bloque (INTEN)
MINING_REWARD_PER_WALLET = float(os.environ.get("MINING_REWARD", "20.0"))

# Símbolo principal de la cadena
CHAIN_SYMBOL = "INTEN"

# ==============================
# ESTRUCTURAS DE DATOS
# ==============================

blockchain = []         # Lista de bloques
transactions = []       # Transacciones pendientes (pool)


# ==============================
# FUNCIONES DE BLOCKCHAIN
# ==============================

def create_genesis_block():
    """Crea el bloque génesis."""
    return {
        "index": 1,
        "timestamp": time.time(),
        "transactions": [],
        "proof": 100,
        "previous_hash": "GENESIS"
    }


def hash_block(block):
    """Calcula el hash SHA-256 de un bloque."""
    encoded_block = str(block).encode()
    return hashlib.sha256(encoded_block).hexdigest()


def valid_proof(last_proof, proof):
    """
    Condición de Proof-of-Work:
    hash(last_proof + proof) debe comenzar con '0000'.
    """
    guess = f"{last_proof}{proof}".encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash.startswith("0000")


def proof_of_work(last_proof):
    """Algoritmo simple de PoW."""
    proof = 0
    while not valid_proof(last_proof, proof):
        proof += 1
    return proof


def create_block(proof, previous_hash, txs):
    """
    Crea un nuevo bloque con las transacciones txs y lo devuelve.
    (NO modifica blockchain aquí, solo construye el dict del bloque)
    """
    block = {
        "index": len(blockchain) + 1,
        "timestamp": time.time(),
        "transactions": txs,
        "proof": proof,
        "previous_hash": previous_hash
    }
    return block


# ==============================
# LÓGICA DE RECOMPENSAS
# ==============================

def send_reward_to_wallet(wallet_addr, amount):
    """
    Envía la recompensa de minería a una wallet real en el servidor 5020
    usando /api/bridge/deposit_new.

    Usa is_miner_reward=True para que 5020 NO notifique de vuelta a 5001.
    """
    payload = {
        "wallet": wallet_addr,
        "symbol": CHAIN_SYMBOL,
        "amount": float(amount),
        "bridge_secret": BRIDGE_SECRET,
        "is_miner_reward": True  # evita loop de notificaciones
    }

    try:
        r = requests.post(WALLET_BRIDGE_URL, json=payload, timeout=5)
        r.raise_for_status()
        print(f"✅ Recompensa enviada a {wallet_addr}: {amount} {CHAIN_SYMBOL}. Respuesta 5020: {r.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR al enviar recompensa a {wallet_addr}: {e}")
        return False


def mine_once(auto=False):
    """
    Función principal de minado:
    - Toma todas las transacciones pendientes
    - Calcula PoW
    - Envía recompensa a cada wallet participante
    - Crea y agrega el bloque a la cadena
    """
    global transactions, blockchain

    if not transactions:
        if auto:
            print("[MINER] No hay transacciones pendientes. Se omite este ciclo.")
        else:
            print("[MINER] No hay transacciones para minar.")
        return None

    # Copiar y limpiar pool de transacciones
    tx_pool = transactions.copy()
    transactions = []

    # Determinar wallets a recompensar (todas las que aparezcan como receiver)
    wallets_to_reward = set()
    for tx in tx_pool:
        recv = tx.get("receiver")
        if recv:
            wallets_to_reward.add(recv)

    # Enviar recompensa a cada wallet a través del bridge 5020
    reward_txs = []
    for w in wallets_to_reward:
        success = send_reward_to_wallet(w, MINING_REWARD_PER_WALLET)
        reward_txs.append({
            "sender": "mining_system",
            "receiver": w,
            "amount": MINING_REWARD_PER_WALLET if success else 0.0,
            "symbol": CHAIN_SYMBOL,
            "timestamp": time.time(),
            "reward_ok": success
        })

    # Preparar datos de PoW
    last_block = blockchain[-1] if blockchain else create_genesis_block()
    if not blockchain:
        blockchain.append(last_block)

    last_proof = last_block["proof"]
    proof = proof_of_work(last_proof)
    previous_hash = hash_block(last_block)

    # El bloque tendrá las transacciones originales + las recompensas
    full_txs = tx_pool + reward_txs
    new_block = create_block(proof, previous_hash, full_txs)
    blockchain.append(new_block)

    print(
        f"⛏️ Bloque minado (auto={auto}) | Índice: {new_block['index']}, "
        f"TXs: {len(full_txs)}, Wallets recompensadas: {len(wallets_to_reward)}"
    )

    return new_block


def auto_miner_loop():
    """
    Bucle de minería automática.
    Cada MINING_INTERVAL segundos intenta minar si hay transacciones pendientes.
    """
    print(f"[AUTO-MINER] Iniciado. Intervalo: {MINING_INTERVAL} segundos.")
    while True:
        time.sleep(MINING_INTERVAL)
        try:
            if transactions:
                print(f"[AUTO-MINER] Hay {len(transactions)} transacciones pendientes. Minando...")
                mine_once(auto=True)
            else:
                print("[AUTO-MINER] Sin transacciones pendientes en este ciclo.")
        except Exception as e:
            print(f"[AUTO-MINER] Error durante minado automático: {e}")


# ==============================
# RUTAS HTTP (API)
# ==============================

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "ok": True,
        "message": "Intencoin Blockchain Node (5001)",
        "blocks": len(blockchain),
        "pending_transactions": len(transactions),
        "endpoints": {
            "get_blockchain": "/get_blockchain",
            "get_transactions": "/get_transactions",
            "new_transaction": "/transactions/new",
            "mine_now": "/mine",
            "miner_notify": "/api/miner/notify",
        }
    })


@app.route("/get_blockchain", methods=["GET"])
def get_blockchain():
    """Devuelve la cadena completa (para evitar 404 en tus pruebas)."""
    return jsonify({
        "ok": True,
        "length": len(blockchain),
        "blockchain": blockchain
    }), 200


@app.route("/get_transactions", methods=["GET"])
def get_transactions():
    """Devuelve las transacciones pendientes (pool)."""
    return jsonify({
        "ok": True,
        "pending": len(transactions),
        "transactions": transactions
    }), 200


@app.route("/transactions/new", methods=["POST"])
def new_transaction():
    """
    Crea una nueva transacción manualmente.

    JSON esperado:
    {
      "sender": "id_origen",
      "receiver": "wallet_destino",
      "amount": 123.45,
      "symbol": "INTEN"   # opcional, default INTEN
    }
    """
    data = request.get_json(force=True) or {}
    required = ["sender", "receiver", "amount"]
    if not all(k in data for k in required):
        return jsonify({"ok": False, "error": "missing fields"}), 400

    try:
        amount = float(data.get("amount", 0))
    except ValueError:
        amount = 0.0

    if amount <= 0:
        return jsonify({"ok": False, "error": "amount must be > 0"}), 400

    tx = {
        "sender": data["sender"],
        "receiver": data["receiver"],
        "amount": amount,
        "symbol": data.get("symbol", CHAIN_SYMBOL),
        "timestamp": time.time()
    }
    transactions.append(tx)

    return jsonify({
        "ok": True,
        "message": "Transaction added to pool",
        "pool_size": len(transactions)
    }), 201


@app.route("/mine", methods=["POST"])
def mine_block():
    """
    Fuerza minado manual (además del automático).
    """
    new_block = mine_once(auto=False)
    if not new_block:
        return jsonify({"ok": False, "error": "no transactions to mine"}), 400

    return jsonify({
        "ok": True,
        "message": "Block mined successfully",
        "block": new_block
    }), 200


@app.route("/api/miner/notify", methods=["POST"])
def api_miner_notify():
    """
    Endpoint llamado por la wallet 5020 (MINER_NOTIFY_URL)
    cuando se acredita un depósito INTEN en una wallet.

    JSON (desde 5020):
    {
      "wallet": "WALADDR-...",
      "amount": 5000.0,
      "symbol": "INTEN",
      "secret": "BRIDGE_SECRET"
    }
    """
    data = request.get_json(force=True) or {}
    secret = data.get("secret")

    if secret != BRIDGE_SECRET:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    wallet = (data.get("wallet") or "").strip()
    symbol = (data.get("symbol") or CHAIN_SYMBOL).strip()
    try:
        amount = float(data.get("amount", 0))
    except ValueError:
        amount = 0.0

    if not wallet or amount <= 0:
        return jsonify({"ok": False, "error": "wallet/amount invalid"}), 400

    tx = {
        "sender": "bridge_system_deposit",
        "receiver": wallet,
        "amount": amount,
        "symbol": symbol,
        "timestamp": time.time()
    }
    transactions.append(tx)

    print(
        f"✔️ Notificación de depósito recibida: {amount} {symbol} "
        f"a {wallet}. Añadida a cola de minería. Total TXs pendientes: {len(transactions)}"
    )

    return jsonify({
        "ok": True,
        "message": "Notification received and transaction added to pool",
        "pending": len(transactions)
    }), 200


# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    # Crear bloque génesis si la cadena está vacía
    if not blockchain:
        genesis = create_genesis_block()
        blockchain.append(genesis)
        print(f"[INIT] Bloque génesis creado. Hash: {hash_block(genesis)}")

    # Lanzar minero automático en un hilo en segundo plano
    miner_thread = threading.Thread(target=auto_miner_loop, daemon=True)
    miner_thread.start()

    # Ejecutar servidor Flask en puerto 5001
    port = int(os.environ.get("PORT", "5004"))
    print(f"[RUN] Blockchain node escuchando en 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)







