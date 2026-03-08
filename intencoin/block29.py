from flask import Flask, request, jsonify
import requests
import uuid
import time
import hashlib
from threading import Timer
import json
import logging
import os 
from urllib.parse import urlparse # Para parsear URLs de nodos

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- CONFIGURACIÓN PARA EL PAGO AUTOMÁTICO DE MINERÍA ---
WALLET_APP_SECRET = os.environ.get('BRIDGE_SECRET', 'dev-bridge-secret')
REWARD_PER_WALLET = 5 
WALLET_BRIDGE_URL = "http://127.0.0.1:5021/api/bridge/deposit_new"
MINING_INTERVAL_SECONDS = 300 # 5 minutos
# -----------------------------------------------------------------

# NUEVOS ELEMENTOS PARA SINCRONIZACIÓN DE NODOS
known_wallets = set() 
peer_nodes = set() # Conjunto de otros nodos en la red (Ej: 5001)
crypto_api_slots = [{"slot": i, "url": None, "status": "disabled"} for i in range(5)]

# Blockchain Data
wallets = {}
blockchain = []
transactions = [] # Pool de transacciones pendientes

# --- Helper functions (funciones auxiliares) ---

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
    guess_hash = hashlib.sha256(guess)
    return guess_hash.hexdigest()[:4] == "0000"

# NUEVA FUNCIÓN: Verificar si una cadena es válida
def valid_chain(chain):
    """Determina si una cadena de bloques dada es válida."""
    last_block = chain[0]
    current_index = 1

    while current_index < len(chain):
        block = chain[current_index]
        print(f'{last_block}')
        print(f'{block}')
        print("\n-----------\n")
        # 1. Verificar que el hash del bloque anterior sea correcto
        if block['previous_hash'] != hash_block(last_block):
            return False
        
        # 2. Verificar la Prueba de Trabajo (PoW)
        if not valid_proof(last_block['proof'], block['proof']):
            return False

        last_block = block
        current_index += 1

    return True

# NUEVA FUNCIÓN: Algoritmo de Consenso
def resolve_conflicts():
    """
    Este es el algoritmo de Consenso: reemplaza nuestra cadena con la cadena
    más larga y válida en la red.
    """
    global blockchain
    
    network = peer_nodes
    max_length = len(blockchain)
    new_chain = None

    # Recorre todos los nodos vecinos
    for node in network:
        try:
            response = requests.get(f'http://{node}/blockchain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['blockchain']

                # Verifica si la cadena del vecino es más larga Y es válida
                if length > max_length and valid_chain(chain):
                    max_length = length
                    new_chain = chain
        except requests.exceptions.RequestException:
            logging.warning(f"No se pudo conectar con el nodo vecino: {node}")
            continue

    # Reemplaza la cadena si encontramos una nueva y más larga
    if new_chain:
        blockchain = new_chain
        return True

    return False

    
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
    global blockchain

    # Antes de minar, chequea si hay un conflicto y sincroniza con la cadena más larga.
    # Esto asegura que 5002 use el trabajo de 5001 (si es más largo).
    resolved = resolve_conflicts()
    if resolved:
        print("🔄 CADENA ACTUALIZADA: La cadena local fue reemplazada por una más larga de la red.")
        
    total_reward_paid = 0
    reward_records = []
    
    print(f"\n[MINERÍA AUTOMÁTICA - 5002] Iniciando proceso de minería. Wallets participantes: {len(known_wallets)}")
    
    # 1. Pago de Recompensa a TODOS los participantes (a través del Wallet 5021)
    if known_wallets:
        for wallet_addr in list(known_wallets):
            try:
                # Envío de la recompensa individual
                payload = {
                    "wallet": wallet_addr,
                    "symbol": "INTEN", 
                    "amount": REWARD_PER_WALLET,
                    "bridge_secret": WALLET_APP_SECRET, 
                }
                
                response = requests.post(WALLET_BRIDGE_URL, json=payload, timeout=5)
                response.raise_for_status() 

                reward_records.append({
                    "sender": "system_mining_reward",
                    "receiver": wallet_addr, 
                    "amount": REWARD_PER_WALLET,
                    "symbol": "INTEN",
                    "timestamp": time.time()
                })
                total_reward_paid += REWARD_PER_WALLET
                
            except requests.exceptions.HTTPError as http_err:
                print(f"❌ ERROR HTTP ({http_err.response.status_code}): Falló el pago de {wallet_addr}. El servidor 5021 rechazó la clave secreta. Recompensa no pagada. (Valor actual: '{WALLET_APP_SECRET}')")
            except requests.exceptions.RequestException as e:
                print(f"❌ ERROR CONEXIÓN: Falló la comunicación con el Wallet (5021). Recompensa no pagada.")
                
        print(f"✅ Recompensa distribuida a {len(reward_records)} Wallets. Total Pagado: {total_reward_paid} INTEN")
    else:
        print("⚠️ No hay Wallets conocidas para distribuir la recompensa. Pool vacío.")


    # 2. Minar el Bloque
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
    return jsonify({"message": "Welcome to the blockchain API - Miner 5002"}), 200

@app.route('/blockchain', methods=['GET'])
def get_blockchain():
    # Devuelve la cadena local del Minero 5002
    return jsonify({"blockchain": blockchain, "length": len(blockchain), "pending_transactions": len(transactions), "known_wallets": list(known_wallets), "peer_nodes": list(peer_nodes)}), 200


@app.post("/api/miner/notify") 
def api_miner_notify():
    data = request.get_json(force=True)
    secret = data.get("secret")
    
    if secret != WALLET_APP_SECRET: 
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    
    wallet = data.get("wallet")
    amount = float(data.get("amount", 0))
    symbol = data.get("symbol")
    
    if not wallet or not amount or not symbol:
         return jsonify({"ok": False, "error": "missing data (wallet, amount, symbol)"}), 400

    global known_wallets
    known_wallets.add(wallet)
    
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

# NUEVA RUTA: Para que los mineros se encuentren.
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return "Error: Por favor, especifique una lista válida de nodos.", 400

    for node in nodes:
        parsed_url = urlparse(node)
        # Solo necesitamos el netloc (ej: 127.0.0.1:5001)
        if parsed_url.netloc:
            peer_nodes.add(parsed_url.netloc)
        else:
            return f"Error: URL de nodo inválida: {node}", 400

    response = {
        'message': 'Nuevos nodos han sido añadidos',
        'total_nodes': list(peer_nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus_endpoint():
    replaced = resolve_conflicts()

    if replaced:
        response = {
            'message': 'Nuestra cadena fue reemplazada por la más larga y válida.',
            'new_chain': blockchain
        }
    else:
        response = {
            'message': 'Nuestra cadena es la autoritaria.',
            'chain': blockchain
        }

    return jsonify(response), 200

# --- Otras rutas (sin cambios) ---

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
    print(f"Minero INTENcoin (Puerto 5005) iniciado y listo para sincronizar.")
    print(f"Para que trabaje simultáneamente, debes registrar el nodo 5001 en este nodo (5005).")
    print("---------------------------------------------------------------------")
    
    Timer(5, automated_mining).start() 

if __name__ == "__main__":
    start_miner_timer()
    app.run(host="0.0.0.0", port=5005, use_reloader=False)




