
from flask import Flask, request, jsonify
import requests
import uuid
import time
import hashlib
from threading import Timer
import json
import logging

app = Flask(__name__)
# Configura el nivel de logging para que los mensajes de INFO y superiores sean visibles.
logging.basicConfig(level=logging.INFO)

# --- CONFIGURACIÓN PARA EL PAGO AUTOMÁTICO DE MINERÍA ---
# ¡CLAVE! ESTE VALOR DEBE COINCIDIR EXACTAMENTE con el SECRETO configurado en tu Wallet (5021)
BRIDGE_SECRET = os.environ.get("BRIDGE_SECRE>
 

# Recompensa por cada Wallet registrada en el set 'known_wallets'.
REWARD_PER_WALLET = 5 

# URL para llamar al API de depósito en tu Wallet (Puerto 5021, CORREGIDO)
WALLET_BRIDGE_URL = "http://127.0.0.1:5021/api/bridge/deposit_new"

MINING_INTERVAL_SECONDS = 300 # 5 minutos
# -----------------------------------------------------------------

# Set para almacenar las direcciones de Wallets que participan/notifican transacciones.
known_wallets = set() 
crypto_api_slots = [{"slot": i, "url": None, "status": "disabled"} for i in range(5)]

# Blockchain Data
wallets = {}
blockchain = []
transactions = [] # Pool de transacciones pendientes

# --- Helper functions ---

def create_genesis_block():
    """Crea el bloque inicial de la cadena."""
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
    """Genera el hash SHA-256 de un bloque."""
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

def valid_proof(last_proof, proof):
    """Verifica si la prueba de trabajo es correcta (4 ceros iniciales)."""
    guess = f'{last_proof}{proof}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash[:4] == "0000"
    
def proof_of_work(last_proof):
    """Algoritmo de Prueba de Trabajo simple."""
    proof = 0
    while not valid_proof(last_proof, proof):
        proof += 1 
    return proof


# --- FUNCIÓN DE MINERÍA AUTOMÁTICA (DISTRIBUYE RECOMPENSA Y MINA) ---
def automated_mining():
    global known_wallets
    global transactions

    total_reward_paid = 0
    reward_records = []
    
    print(f"\n[MINERÍA AUTOMÁTICA] Iniciando proceso de minería. Wallets participantes: {len(known_wallets)}")
    
    # 1. Pago de Recompensa a TODOS los participantes (a través del Wallet 5021)
    # ESTO SE EJECUTA CADA 5 MINUTOS, HAYA O NO TRANSACCIONES.
    if known_wallets:
        for wallet_addr in list(known_wallets):
            try:
                # Envío de la recompensa individual
                payload = {
                    "wallet": wallet_addr,
                    "symbol": "INTEN", 
                    "amount": REWARD_PER_WALLET,
                    "bridge_secret": WALLET_APP_SECRET, # BRIDGE_SECRET
                }
                
                response = requests.post(WALLET_BRIDGE_URL, json=payload, timeout=5)
                response.raise_for_status() # Lanza excepción si el código es 4xx o 5xx

                # Si el pago fue exitoso (200/201), registramos la transacción para el bloque
                reward_records.append({
                    "sender": "system_mining_reward",
                    "receiver": wallet_addr, 
                    "amount": REWARD_PER_WALLET,
                    "symbol": "INTEN",
                    "timestamp": time.time()
                })
                total_reward_paid += REWARD_PER_WALLET
                
            except requests.exceptions.HTTPError as http_err:
                # Captura el error 401 (Unauthorized) aquí
                print(f"❌ ERROR HTTP ({http_err.response.status_code}): Falló el pago de {wallet_addr}. El servidor 5021 rechazó la clave secreta. Recompensa no pagada.")
            except requests.exceptions.RequestException as e:
                print(f"❌ ERROR CONEXIÓN: Falló la comunicación con el Wallet (5021). Recompensa no pagada.")
                
        print(f"✅ Recompensa distribuida a {len(reward_records)} Wallets. Total Pagado: {total_reward_paid} INTEN")
    else:
        print("⚠️ No hay Wallets conocidas para distribuir la recompensa. Pool vacío.")


    # 2. Minar el Bloque (registrando la prueba de trabajo y las transacciones)
    
    # El bloque se mina siempre, registrando las recompensas pagadas (si las hay) y las transacciones pendientes.
    current_transactions_to_mine = transactions.copy()
    current_transactions_to_mine.extend(reward_records) 
    
    last_block = blockchain[-1] if blockchain else create_genesis_block()
    last_proof = last_block['proof']
    
    proof = proof_of_work(last_proof) 
    previous_hash = hash_block(last_block)
    
    block = create_block(proof, previous_hash, current_transactions_to_mine)
    
    # Limpiar el pool de transacciones pendientes y registrar el nuevo bloque
    transactions.clear() 
    blockchain.append(block)

    print(f"⛏️ Bloque minado con éxito! Índice: {block['index']}, TXs registradas: {len(block['transactions'])}, Recompensa Total: {total_reward_paid} INTEN")
    print(f"La próxima minería será en {int(MINING_INTERVAL_SECONDS/60)} minutos (Bloque {block['index'] + 1}).")

    # 3. Programar la próxima minería
    Timer(MINING_INTERVAL_SECONDS, automated_mining).start()


# --- RUTAS FLASK ---


@app.route('/')
def home():
    return jsonify({"message": "Welcome to the blockchain API - Miner 5001"}), 200

@app.route('/blockchain', methods=['GET'])
def get_blockchain():
    return jsonify({"blockchain": blockchain, "length": len(blockchain), "pending_transactions": len(transactions), "known_wallets": list(known_wallets)}), 200

# 🔑 RUTA CLAVE: Notificación desde el puerto 5021
@app.post("/api/miner/notify") 
def api_miner_notify():
    data = request.get_json(force=True)
    secret = data.get("secret")
    
    # 1. Validación de Secreto
    if secret != WALLET_APP_SECRET: 
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    
    # 2. Extracción de datos
    wallet = data.get("wallet")
    amount = float(data.get("amount", 0))
    symbol = data.get("symbol")
    
    if not wallet or not amount or not symbol:
         return jsonify({"ok": False, "error": "missing data (wallet, amount, symbol)"}), 400

    # PASO CLAVE: Registramos la wallet en nuestro set de participantes
    global known_wallets
    known_wallets.add(wallet)
    
    # 3. Registra la transacción en la cola para ser minada
    new_deposit_transaction = {
        'sender': 'bridge_system_deposit' if amount > 0 else 'bridge_system_withdrawal',
        'receiver': wallet if amount > 0 else 'bridge_system_withdrawal',
        'amount': abs(amount),
        'symbol': symbol,
        'timestamp': time.time()
    }
    
    transactions.append(new_deposit_transaction) 
    
    print(f"✔️ Notificación recibida: {new_deposit_transaction['amount']} {symbol} a {wallet}. Añadida a cola de minería. Total Wallets Conocidas: {len(known_wallets)}")
    return jsonify({"ok": True, "message": f"Notification received and transaction added to pool for block {len(blockchain) + 1}"})


@app.route('/generate_new_apikey', methods=['POST'])
def generate_new_apikey():
    new_key = str(uuid.uuid4())
    return jsonify({
        "message": "API Key generada exitosamente. Asegúrate de guardar esta clave en un lugar seguro.",
        "api_key": new_key,
        "note": "Esta clave puede ser necesaria para la comunicación entre nodos (Bridge/Minero)."
    }), 201

@app.route('/crypto/apis', methods=['GET', 'POST'])
def manage_crypto_apis():
    if request.method == 'POST':
        slot_id = int(request.json.get('slot_id', -1))
        action = request.json.get('action')
        url = request.json.get('url')
        if 0 <= slot_id < 5:
            if action == "add":
                crypto_api_slots[slot_id]["url"] = url
                crypto_api_slots[slot_id]["status"] = "enabled"
                return jsonify({"message": f"API added to slot {slot_id}", "url": url}), 200
            elif action == "remove":
                crypto_api_slots[slot_id]["url"] = None
                crypto_api_slots[slot_id]["status"] = "disabled"
                return jsonify({"message": f"API removed from slot {slot_id}"}), 200
        return jsonify({"error": "Invalid slot or action"}), 400
    return jsonify({"crypto_api_slots": crypto_api_slots}), 200

@app.route('/create_wallet', methods=['POST'])
def create_wallet():
    user_id = request.json.get("user_id")
    if not user_id:
        return jsonify({"error": "User ID is required."}), 400
    if user_id in wallets:
        return jsonify({"error": "Wallet already exists for this user."}), 400
    wallet_address = str(uuid.uuid4())
    wallets[user_id] = {"address": wallet_address, "balance": 0}  
    return jsonify({
        "message": "Wallet created successfully (on Miner's internal ledger). Use 5021 for the official Wallet.",
        "wallet_address": wallet_address,
        "balance": 0,
    }), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'receiver', 'amount', 'symbol']
    if not all(k in values for k in required):
        return 'Missing values in payload (sender, receiver, amount, symbol)', 400
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

@app.route('/mine', methods=['POST'])
def mine_block():
    """Permite minar un bloque manualmente fuera del temporizador automático."""
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
    transactions_to_mine = transactions.copy()
    transactions_to_mine.append(miner_reward_record)
    block = create_block(proof, previous_hash, transactions_to_mine)
    transactions.clear()
    blockchain.append(block)
    return jsonify({"message": "Block mined successfully manually!", "block": block})


# --- INICIO DEL SERVIDOR ---
def start_miner_timer():
    if not blockchain:
        blockchain.append(create_genesis_block())
    
    print("---------------------------------------------------------------------")
    print(f"Minero INTENcoin iniciado.")
    print(f"Recompensa por Wallet Conocida: {REWARD_PER_WALLET} INTEN. Intervalo: 5 minutos.")
    print(f"Secreto Bridge: {WALLET_APP_SECRET} (¡VERIFICAR EN 5021!)")
    print(f"URL de Pago del Wallet: {WALLET_BRIDGE_URL}")
    print("---------------------------------------------------------------------")
    
    # Inicia el proceso de minería en un hilo separado
    Timer(5, automated_mining).start() 

if __name__ == "__main__":
    # La inicialización se mueve a un hilo para evitar bloquear el servidor web.
    start_miner_timer()
    app.run(host="0.0.0.0", port=5001, use_reloader=False)












