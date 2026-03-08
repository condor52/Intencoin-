from flask import Flask, request, jsonify
import requests
import uuid
import time
import hashlib
from threading import Timer
import sys

app = Flask(__name__)

# --- CONFIGURACIÓN PARA EL PAGO AUTOMÁTICO DE MINERÍA ---
# ¡IMPORTANTE! Este es el secreto que DEBE coincidir con el 'BRIDGE_SECRET' en tu Wallet (5020)
BRIDGE_SECRET = "dev-bridge-secret" 

# RECUERDA: Debes crear esta Wallet Address en el puerto 5020 primero y reemplazarla aquí.
MINER_WALLET_ADDR = "WALADDR-MINER-1000-AUTOMATIC" 

# URL para llamar al API de depósito en tu Wallet (Puerto 5020)
WALLET_BRIDGE_URL = "http://127.0.0.1:5020/api/bridge/deposit_new"
# -----------------------------------------------------------------

# 5 API slots for crypto connections
crypto_api_slots = [{"slot": i, "url": None, "status": "disabled"} for i in range(5)]

# Wallet (Solo para pruebas internas y no usado en el flujo de recompensa)
wallets = {}
blockchain = []
transactions = []

# Helper functions
def generate_wallet_address():
    # Usado para crear wallets de prueba, no es el flujo principal de la app
    return str(uuid.uuid4())

def create_genesis_block():
    return {
        "index": 1,
        "timestamp": time.time(),
        "transactions": [],
        "proof": 100,
        "previous_hash": "1",
    }

def create_block(proof, previous_hash, current_transactions):
    """Crea un nuevo bloque con las transacciones proporcionadas."""
    block = {
        "index": len(blockchain) + 1,
        "timestamp": time.time(),
        "transactions": current_transactions,
        "proof": proof,
        "previous_hash": previous_hash,
    }
    return block

def hash_block(block):
    # Asegúrate de ordenar el diccionario para tener hashes consistentes
    import json
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

def valid_proof(last_proof, proof):
    guess = f'{last_proof}{proof}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash[:4] == "0000"
    
def proof_of_work(last_proof):
    """Encuentra un número 'proof' tal que hash(last_proof + proof) contenga 4 ceros iniciales."""
    proof = 0
    while not valid_proof(last_proof, proof):
        proof += 1 
    return proof



# --- FUNCIÓN DE MINERÍA AUTOMÁTICA (AHORA CADA 5 MINUTOS) ---
def automated_mining():
    # 1. Pago de Recompensa (Llamada al Bridge API en Puerto 5020)
    reward_amount = 50 
    
    print(f"\n[MINERÍA AUTOMÁTICA] Iniciando proceso de minería. Recompensa: {reward_amount} INTEN")
    
    try:
        payload = {
            "wallet": MINER_WALLET_ADDR,
            "symbol": "INTEN",
            "amount": reward_amount,
            # Se usa 'bridge_secret' para autenticar la llamada con el puerto 5020
            "bridge_secret": BRIDGE_SECRET,
            "is_miner_reward": True 
        }
        
        # Intentar el pago de la recompensa a la Wallet (5020)
        response = requests.post(WALLET_BRIDGE_URL, json=payload, timeout=5)
        response.raise_for_status() 
        print(f"✅ Pago de minería enviado a Wallet (5020). Respuesta: {response.json()}")
    
    except requests.exceptions.RequestException as e:
        # En caso de fallo (ej: Wallet 5020 no está encendida), la recompensa no se distribuye
        print(f"❌ ERROR: Falló el pago de minería al Bridge API (5020): {e}. Recompensa no distribuida.")
        reward_amount = 0
        
    # 2. Registro de la Recompensa en la Blockchain (transacciones)
    miner_reward_record = {
        "sender": "system_mining",
        "receiver": MINER_WALLET_ADDR, 
        "amount": reward_amount,
        "symbol": "INTEN",
        "timestamp": time.time()
    }
    
    # 3. Minar el Bloque
    
    # Se añaden las transacciones pendientes (incluyendo la recompensa y cualquier notificación del 5020)
    current_transactions_to_mine = transactions.copy()
    current_transactions_to_mine.append(miner_reward_record)

    last_block = blockchain[-1] if blockchain else create_genesis_block()
    last_proof = last_block['proof']
    
    proof = proof_of_work(last_proof) 
    previous_hash = hash_block(last_block)
    
    block = create_block(proof, previous_hash, current_transactions_to_mine)
    
    # Limpiar el pool de transacciones (solo si la minería fue exitosa)
    transactions.clear() 
    blockchain.append(block)

    print(f"⛏️ Bloque minado con éxito! Índice: {block['index']}, TXs registradas: {len(block['transactions'])}, Recompensa: {reward_amount} INTEN")
    print(f"La próxima minería será en 5 minutos (Bloque {block['index'] + 1}).")

    # 4. Programar la próxima minería (cada 5 minutos = 300 segundos)
    # Importante: Esto usa Timer, que es no bloqueante y permite que Flask siga respondiendo.
    Timer(300, automated_mining).start()


# --- RUTAS FLASK ---


@app.route('/')
def home():
    return jsonify({"message": "Welcome to the blockchain API - Miner 5001"}), 200

# La creación de wallets no es responsabilidad directa del Minero.
# Se deja para compatibilidad, pero la lógica principal de cuentas está en 5020.
@app.route('/create_wallet', methods=['POST'])
def create_wallet():
    user_id = request.json.get("user_id")
    if not user_id:
        return jsonify({"error": "User ID is required."}), 400
    if user_id in wallets:
        return jsonify({"error": "Wallet already exists for this user."}), 400

    wallet_address = generate_wallet_address()
    wallets[user_id] = {"address": wallet_address, "balance": 0}  
    
    return jsonify({
        "message": "Wallet created successfully (on Miner's internal ledger). Use 5020 for the official Wallet.",
        "wallet_address": wallet_address,
        "balance": 0,
    }), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'receiver', 'amount', 'symbol']
    if not all(k in values for k in required):
        return 'Missing values in payload (sender, receiver, amount, symbol)', 400
    
    # Añadimos la transacción a la cola
    transaction_data = {
        'sender': values['sender'],
        'receiver': values['receiver'],
        'amount': values['amount'],
        'symbol': values.get('symbol', 'INTEN'), 
        'timestamp': time.time()
    }
    transactions.append(transaction_data) 

    response = {'message': f"Transaction ({transaction_data['symbol']}) will be added to Block {len(blockchain) + 1}. TXs pending: {len(transactions)}"}
    return jsonify(response), 201


@app.route('/blockchain', methods=['GET'])
def get_blockchain():
    return jsonify({"blockchain": blockchain, "length": len(blockchain), "pending_transactions": len(transactions)}), 200


@app.route('/mine', methods=['POST'])
def mine_block():
    """Permite minar un bloque manualmente fuera del temporizador automático."""
    
    # 1. la recompensa del minero (solo para el registro en la blockchain)
    # NOTA: EL PAGO REAL AL PUERTO 5020 OCURRE EN 'automated_mining()'
    miner_reward_record = {
        "sender": "Manual Mining Reward",
        "receiver": "Manual Miner", 
        "amount": 50,
        "symbol": "INTEN",
        "timestamp": time.time()
    }
    
    last_block = blockchain[-1] if blockchain else create_genesis_block()
    last_proof = last_block["proof"]
    
    proof = proof_of_work(last_proof)

    previous_hash = hash_block(last_block)

    # Copiar transacciones pendientes y añadir la recompensa manual
    transactions_to_mine = transactions.copy()
    transactions_to_mine.append(miner_reward_record)
    
    block = create_block(proof, previous_hash, transactions_to_mine)

    transactions.clear()
    blockchain.append(block)
    return jsonify({"message": "Block mined successfully manually!", "block": block})


# 🔑 RUTA CLAVE: Notificación desde el puerto 5020 (Cuando hay un depósito o retiro)
@app.post("/api/miner/notify") 
def api_miner_notify():
    data = request.get_json(force=True)
    secret = data.get("secret")
    
    # 1. Validación de Secreto
    if secret != BRIDGE_SECRET: 
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    
    # 2. Lógica para añadir la transacción al pool de transacciones pendientes
    wallet = data.get("wallet")
    amount = float(data.get("amount", 0))
    symbol = data.get("symbol")
    
    if not wallet or not amount or not symbol:
         return jsonify({"ok": False, "error": "missing data (wallet, amount, symbol)"}), 400

    # Registra la transacción de depósito/retiro en la cola del Minero para ser confirmada
    new_deposit_transaction = {
        'sender': 'bridge_system_deposit' if amount > 0 else 'bridge_system_withdrawal',
        'receiver': wallet if amount > 0 else 'bridge_system_withdrawal', # Si es retiro, el receptor es el sistema
        'amount': abs(amount),
        'symbol': symbol,
        'timestamp': time.time()
    }
    
    transactions.append(new_deposit_transaction) 
    
    print(f"✔️ Notificación de depósito/retiro recibida: {new_deposit_transaction['amount']} {symbol} a {wallet}. Añadida a cola de minería. TXs pendientes: {len(transactions)}")
    return jsonify({"ok": True, "message": f"Notification received and transaction added to pool for block {len(blockchain) + 1}"})


# --- INICIO DEL SERVIDOR ---
if __name__ == "__main__":
    # Inicializa el bloque Génesis si no existe
    if not blockchain:
        blockchain.append(create_genesis_block())
    
    # ¡INICIA EL PROCESO DE MINERÍA AUTOMÁTICA (5 MINUTOS)!
    print("---------------------------------------------------------------------")
    print(f"Minero INTENcoin iniciado.")
    print(f"Recompensa de minería: 50 INTEN. Intervalo: 5 minutos.")
    print(f"Wallet de Recompensa: {MINER_WALLET_ADDR}")
    print("---------------------------------------------------------------------")
    
    # Usamos Timer para iniciar el primer ciclo sin bloquear el servidor web.
    Timer(5, automated_mining).start() 
    
    # Tu criptomoneda corre en el puerto 5001
    app.run(host="0.0.0.0", port=5001)




