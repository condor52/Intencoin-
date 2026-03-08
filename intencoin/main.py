
from flask import Flask, request, jsonify
import requests
import uuid
import time
import hashlib
from threading import Timer
import requests
import time
from threading import Thread 





app = Flask(__name__)

# --- CONFIGURACIÓN PARA EL PAGO AUTOMÁTICO DE MINERÍA ---
# ¡IMPORTANTE! Este es el secreto que DEBE coincidir con el 'BRIDGE_SECRET' en tu Wallet (5020)
BRIDGE_SECRET = "dev-bridge-secret" 

# Esta debe ser una dirección de Wallet REAL en tu sistema 5020.
# USA ESTA DIRECCIÓN TEMPORAL HASTA QUE CREES UNA EN EL PUERTO 5020.
MINER_WALLET_ADDR = "WALADDR-MINER-1000-AUTOMATIC" 

# URL para llamar al API de depósito en tu Wallet (Puerto 5020)
WALLET_BRIDGE_URL = "http://127.0.0.1:5020/api/bridge/deposit_new"
# -----------------------------------------------------------------

# 5 API slots for crypto connections
crypto_api_slots = [{"slot": i, "url": None, "status": "disabled"} for i in range(5)]

# Wallet and blockchain data
wallets = {}
blockchain = []
transactions = []





# Helper functions

def process_reward_payment(target_wallet, deposit_amount, bridge_secret):
    """
    Lógica de pago de recompensa. Se ejecuta en un hilo separado (thread).
    """
    print(f"⛏️ Iniciando proceso de recompensa en hilo separado para {target_wallet}...")
    
    # Necesitas asegurar que estas variables globales estén definidas en el 5001
    global transactions, BRIDGE_SECRET, WALLET_BRIDGE_URL, MINER_WALLET_ADDR
    
    REWARD_AMOUNT = 50 

    # 1. Crear el registro de recompensa en la blockchain (5001)
    reward_transaction = {
        "sender": MINER_WALLET_ADDR,  
        "receiver": target_wallet,    
        "amount": REWARD_AMOUNT,
        "symbol": "INTEN",
        "timestamp": time.time()
    }
    transactions.append(reward_transaction)

    # 2. Pagar la recompensa al 5020
    try:
        payload = {
            "wallet": target_wallet, 
            "symbol": "INTEN",
            "amount": REWARD_AMOUNT,
            "secret": BRIDGE_SECRET  
        }
        
        # Llamada de vuelta al 5020 (al puerto que está esperando la respuesta)
        response = requests.post(WALLET_BRIDGE_URL, json=payload, timeout=5)
        response.raise_for_status() 
        print(f"✅ Recompensa de {REWARD_AMOUNT} INTEN acreditada en Wallet (5020). Resp: {response.json()}")

    except requests.exceptions.RequestException as e:
        # Si falla el pago, se revierte la transacción.
        transactions.pop() 
        print(f"❌ ERROR: Falló el PAGO de recompensa a {target_wallet}: {e}. Transacción cancelada.")





def generate_wallet_address():
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
    encoded_block = str(block).encode()
    return hashlib.sha256(encoded_block).hexdigest()

def valid_proof(last_proof, proof):
    guess = f'{last_proof}{proof}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash[:4] == "0000"

# --- FUNCIÓN DE MINERÍA AUTOMÁTICA (NUEVA) ---

def proof_of_work(last_proof):
    proof = 0
    while not valid_proof(last_proof, proof):
        proof += 1
    return proof
# --- FUNCIÓN proof_of_work CORREGIDA ---
def proof_of_work(last_proof):
    """Simple algoritmo de Prueba de Trabajo: Encuentra un número 'proof' tal que
    hash(last_proof + proof) contenga 4 ceros iniciales."""
    proof = 0
    while not valid_proof(last_proof, proof):
        proof += 1 # <-- ¡CORRECCIÓN! Debes sumar 1.
    return proof



# --- FUNCIÓN DE MINERÍA AUTOMÁTICA (REVISADA) ---
def automated_mining():
    # 1. Pago de Recompensa (Llamada al Bridge API en Puerto 5020)
    reward_amount = 50 
    
    try:
        payload = {
            "wallet": MINER_WALLET_ADDR,
            "symbol": "INTEN",
            "amount": reward_amount,
            # ✅ CORRECCIÓN 2: Asegura que el secret se envía con la clave correcta.
            # También añadimos una bandera para que el 5020 sepa que no debe notificar de vuelta.
            "bridge_secret": BRIDGE_SECRET,
            "is_miner_reward": True # <-- Nueva bandera
        }
        # Llama al endpoint /api/bridge/deposit_new en el puerto 5020
        response = requests.post(WALLET_BRIDGE_URL, json=payload, timeout=5)
        response.raise_for_status() 
        print(f"✅ Pago de minería enviado a Wallet (5020). Respuesta: {response.json()}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Falló el pago de minería al Bridge API (5020): {e}. Recompensa no distribuida.")
        reward_amount = 0
        
    # 2. Registro de la Recompensa en la Blockchain (transacciones)
    miner_reward_record = {
        "sender": "system_mining",
        "receiver": MINER_WALLET_ADDR, 
        "amount": reward_amount,
        "timestamp": time.time()
    }
    transactions.append(miner_reward_record)

    # 3. Minar el Bloque (usando las transacciones actuales, incluyendo la recompensa y el depósito notificado)
    last_block = blockchain[-1] if blockchain else create_genesis_block()
    last_proof = last_block['proof']
    
    proof = proof_of_work(last_proof) 
    previous_hash = hash_block(last_block)
    
    block = create_block(proof, previous_hash, transactions.copy())
    
    transactions.clear() 
    blockchain.append(block)

    print(f"⛏️ Bloque minado con éxito! Índice: {block['index']}, TXs registradas: {len(block['transactions'])}, Recompensa: {reward_amount} INTEN")

    # 4. Programar la próxima minería (cada 15 minutos = 900 segundos)
    Timer(900, automated_mining).start()








# --- RUTAS FLASK ---




@app.route('/')
def home():
    return jsonify({"message": "Welcome to the blockchain API"}), 200



# --- RUTA CORREGIDA ---
@app.route('/generate_new_apikey', methods=['POST'])
def generate_new_apikey():
    """Genera una nueva clave de API única y la devuelve."""
    
    # Se utiliza uuid4 para generar una cadena única.
    new_key = str(uuid.uuid4())

    # Aquí puedes añadir lógica para almacenar new_key asociada a un nodo o servicio.
    # Por ahora, solo la devolvemos.

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

    wallet_address = generate_wallet_address()
    wallets[user_id] = {"address": wallet_address, "balance": 0}  # Se inicia en 0. La minería paga aparte.
    
    # No se llama a mine_block aquí, ya que la minería es automática o manual.
    # El balance inicial puede ser 0 o una recompensa de bienvenida que se registre en las transacciones.

    return jsonify({
        "message": "Wallet created successfully.",
        "wallet_address": wallet_address,
        "balance": 0,
    }), 200





@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    
    # 1. Validar campos requeridos
    required = ['sender', 'receiver', 'amount']
    if not all(k in values for k in required):
        return 'Missing values in payload', 400

    # 2. Asignar valores
    sender = values['sender']
    receiver = values['receiver']
    amount = values['amount']
    
    # Añadimos 'symbol' con un valor por defecto (INTEN) si no se proporciona, 
    # para ser compatible con BTC y otras monedas.
    symbol = values.get('symbol', 'INTEN') 

    # 3. Registrar la transacción
    transaction_data = {
        'sender': sender,
        'receiver': receiver,
        'amount': amount,
        'symbol': symbol,
        'timestamp': time.time() # Si tienes 'time' importado, si no, omite.
    }
    
    # Asegúrate de que esta lista 'transactions' sea la que el minero usa.
    transactions.append(transaction_data) 

    response = {'message': f'Transaction ({symbol}) will be added to Block {len(blockchain) + 1}'}
    return jsonify(response), 201



@app.route('/blockchain', methods=['GET'])
def get_blockchain():
    return jsonify({"blockchain": blockchain, "length": len(blockchain)}), 200

@app.route('/say')
def say():
    return jsonify({"message": "Hello from say endpoint"}), 200

@app.route('/mine', methods=['POST'])
def mine_block():
    if not transactions:
        return {"message": "No transactions to mine."}
    
    # 1. la recompensa del minero (solo para el registro en la blockchain)
    # NOTA: EL PAGO REAL AL PUERTO 5020 OCURRE EN 'automated_mining()'
    miner_reward_record = {
        "sender": "Manual Mining Reward",
        "receiver": "Manual Miner", 
        "amount": 50,
        "timestamp": time.time()
    }
    transactions.append(miner_reward_record)
    
    last_block = blockchain[-1] if blockchain else create_genesis_block()
    last_proof = last_block["proof"]
    
    proof = proof_of_work(last_proof)

    previous_hash = hash_block(last_block)
    
    block = create_block(proof, previous_hash, transactions.copy())

    transactions.clear()
    blockchain.append(block)
    return jsonify({"message": "Block mined successfully!", "block": block})





# 🔑 RUTA CLAVE: Notificación desde el puerto 5020
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
    
    # ✅ CORRECCIÓN CLAVE 3: Registra la transacción de depósito en la cola del Minero
    new_deposit_transaction = {
        'sender': 'bridge_system_deposit',
        'receiver': wallet, # <-- La wallet del usuario que depositó
        'amount': amount,
        'symbol': symbol,
        'timestamp': time.time()
    }
    
    # Añadimos esta nueva transacción a la cola para ser minada
    transactions.append(new_deposit_transaction) 
    
    print(f"✔️ Notificación de depósito recibida: {amount} {symbol} a {wallet}. Añadida a cola de minería. Total TXs pendientes: {len(transactions)}")
    return jsonify({"ok": True, "message": f"Notification received and transaction added to pool for block {len(blockchain) + 1}"})





# Necesario para que tú puedas verificar el historial
@app.get("/api/ledger") 
def api_ledger():
    # [Devuelve los datos de tu blockchain o ledger]
    return jsonify({"ok": True, "ledger": "..."}) 




# --- INICIO DEL SERVIDOR ---
if __name__ == "__main__":
    blockchain.append(create_genesis_block())
    
    # ¡INICIA EL PROCESO DE MINERÍA AUTOMÁTICA!
    automated_mining() 
    

    # Tu criptomoneda corre en el puerto 5000
    app.run(host="0.0.0.0", port=5001)













