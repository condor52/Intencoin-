
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import time
import hashlib
import uuid
from threading import Timer
import requests


import requests



# Database API URL
DATABASE_API_URL = "http://your-database-api-url:5001/api"  # Replace with your database API URL

# Function to send blockchain data
def send_blockchain_to_db():
    try:
        response = requests.post(f"{DATABASE_API_URL}/store_blockchain", json={"blockchain": blockchain})
        print(f"Blockchain sent to database. Response: {response.json()}")
    except Exception as e:
        print(f"Error sending blockchain to database: {e}")

# Function to send wallets data
def send_wallets_to_db():
    try:
        response = requests.post(f"{DATABASE_API_URL}/store_wallets", json={"wallets": wallets})
        print(f"Wallets sent to database. Response: {response.json()}")
    except Exception as e:
        print(f"Error sending wallets to database: {e}")

# Function to send transactions data
def send_transactions_to_db():
    try:
        response = requests.post(f"{DATABASE_API_URL}/store_transactions", json={"transactions": transactions})
        print(f"Transactions sent to database. Response: {response.json()}")
    except Exception as e:
        print(f"Error sending transactions to database: {e}")


# Initialize Flask App
app = Flask('app')

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Admin credentials
admin_credentials = {"username": "admin", "password": "admin123"}

# Cryptocurrency data
total_supply = 500000000000  # 500 Billion Intencoins
crypto_price = 0.0  # Price to be set by admin
enabled_apis = list(range(10))  # Automatically enable all 10 API slots
partner_apis = [None] * 10  # 10 API slots for external systems

# Wallets and Transactions
wallets = {}  # Store wallets with balances
transactions = []  # Store pending transactions
blockchain = []  # Store the blockchain (blocks of transactions)


from threading import Timer
import requests

# Replace with your database API URL
DATABASE_API_URL = "http://your-database-api-url:5001/api"

def periodic_sync():
    """Periodically send data to the storage database."""
    try:
        # Send blockchain
        requests.post(f"{DATABASE_API_URL}/store_blockchain", json={"blockchain": blockchain})
        # Send wallets
        requests.post(f"{DATABASE_API_URL}/store_wallets", json={"wallets": wallets})
        # Send transactions
        requests.post(f"{DATABASE_API_URL}/store_transactions", json={"transactions": transactions})
        print("Periodic data sync completed.")
    except Exception as e:
        print(f"Error syncing data: {e}")

    # Schedule the next sync in 5 minutes
    Timer(300, periodic_sync).start()







# Helper Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_wallet_address():
    return str(uuid.uuid4())

def create_genesis_block():
    return {
        'index': 1,
        'timestamp': time.time(),
        'transactions': [],
        'proof': 100,
        'previous_hash': '1'
    }

def create_block(proof, previous_hash):
    block = {
        'index': len(blockchain) + 1,
        'timestamp': time.time(),
        'transactions': transactions.copy(),
        'proof': proof,
        'previous_hash': previous_hash
    }
    transactions.clear()
    return block

def hash_block(block):
    encoded_block = str(block).encode()
    return hashlib.sha256(encoded_block).hexdigest()

def proof_of_work(last_proof):
    proof = 0
    while not valid_proof(last_proof, proof):
        proof += 1
    return proof

def valid_proof(last_proof, proof):
    guess = f'{last_proof}{proof}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash[:4] == "0000"

# Periodic API Calls
def call_active_apis():
    for api_id in enabled_apis:
        api_url = partner_apis[api_id]
        if api_url:
            try:
                response = requests.get(api_url)
                print(f"API {api_id} Response: {response.status_code}")
            except Exception as e:
                print(f"Error calling API {api_id}: {e}")
    Timer(3600, call_active_apis).start()

# Flask Routes
@app.route('/')
def hello_world():
    return "Welcome to Intencoin Cryptocurrency!"



@app.route('/get_blockchain', methods=['GET'])
def get_blockchain():
    """Fetch the current blockchain."""
    return jsonify({"blockchain": blockchain}), 200

@app.route('/get_wallets', methods=['GET'])
def get_wallets():
    """Fetch the current wallets."""
    return jsonify({"wallets": wallets}), 200

@app.route('/get_transactions', methods=['GET'])
def get_transactions():
    """Fetch the current transactions."""
    return jsonify({"transactions": transactions}), 200



# Admin Dashboard
@app.route('/admin_area', methods=['GET', 'POST'])
def admin_area():
    global total_supply, crypto_price, enabled_apis, partner_apis

    if request.method == 'POST':
        if 'logo' in request.files:
            file = request.files['logo']
            if file and allowed_file(file.filename):
                filename = 'intencoin_logo.' + file.filename.rsplit('.', 1)[1].lower()
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                return jsonify({"message": "Logo uploaded successfully!", "file_path": file_path}), 200

        if 'supply' in request.form:
            new_supply = request.form['supply']
            if new_supply.isdigit() and int(new_supply) <= 500000000000:
                total_supply = int(new_supply)
                return jsonify({"message": f"Total supply updated to {new_supply} Intencoins."}), 200
            else:
                return jsonify({"error": "Invalid supply value. Maximum is 500 billion."}), 400

        if 'price' in request.form:
            new_price = request.form['price']
            try:
                crypto_price = float(new_price)
                return jsonify({"message": f"Cryptocurrency price set to ${crypto_price}."}), 200
            except ValueError:
                return jsonify({"error": "Invalid price value."}), 400

        if 'enable_api' in request.form:
            api_id = int(request.form['enable_api'])
            if 0 <= api_id < len(partner_apis):
                enabled_apis.append(api_id)
                return jsonify({"message": f"API slot {api_id} enabled."}), 200
        if 'disable_api' in request.form:
            api_id = int(request.form['disable_api'])
            if api_id in enabled_apis:
                enabled_apis.remove(api_id)
                return jsonify({"message": f"API slot {api_id} disabled."}), 200

        if 'api_slot' in request.form and 'api_url' in request.form:
            api_slot = int(request.form['api_slot'])
            api_url = request.form['api_url']
            if 0 <= api_slot < len(partner_apis):
                partner_apis[api_slot] = api_url
                return jsonify({"message": f"API added to slot {api_slot}: {api_url}"}), 200

    return render_template(
        'admin_area.html',
        total_supply=total_supply,
        crypto_price=crypto_price,
        enabled_apis=enabled_apis,
        partner_apis=partner_apis,
        wallets=wallets,
        transactions=transactions,
        blockchain=blockchain
    )




@app.route('/create_wallet', methods=['POST'])
def create_wallet():
    user_id = request.json.get("user_id")
    if user_id in wallets:
        return jsonify({"error": "Wallet already exists for this user."}), 400
    wallet_address = generate_wallet_address()
    wallets[user_id] = {"address": wallet_address, "balance": 0}
    return jsonify({"message": "Wallet created successfully.", "wallet_address": wallet_address}), 200


@app.route('/transaction', methods=['POST'])
def make_transaction():
    sender_id = request.json.get("sender_id")
    sender_address = request.json.get("sender_address")
    receiver_id = request.json.get("receiver_id")
    receiver_address = request.json.get("receiver_address")
    amount = request.json.get("amount")

    # Handle system funds distribution (e.g., cryptocurrency minting)
    if sender_id == "system" and sender_address == "crypto-system":
        if receiver_id not in wallets or wallets[receiver_id]["address"] != receiver_address:
            return jsonify({"error": "Invalid receiver."}), 400

        # Add amount directly to the receiver's wallet
        wallets[receiver_id]["balance"] += amount
        transaction_record = {
            "sender_id": sender_id,
            "sender_address": sender_address,
            "receiver_id": receiver_id,
            "receiver_address": receiver_address,
            "amount": amount,
            "timestamp": time.time()
        }
        transactions.append(transaction_record)
        return jsonify({"message": "System transaction successful.", "transaction": transaction_record}), 200
    else:
        # Validate sender and receiver IDs for normal transactions
        if sender_id not in wallets or receiver_id not in wallets:
            return jsonify({"error": "Invalid sender or receiver ID."}), 400
        if wallets[sender_id]["address"] != sender_address or wallets[receiver_id]["address"] != receiver_address:
            return jsonify({"error": "Wallet address mismatch."}), 400
        if wallets[sender_id]["balance"] < amount:
            return jsonify({"error": "Insufficient balance."}), 400

        # Deduct balance from sender and add to receiver
        wallets[sender_id]["balance"] -= amount
        wallets[receiver_id]["balance"] += amount

        transaction_record = {
            "sender_id": sender_id,
            "sender_address": sender_address,
            "receiver_id": receiver_id,
            "receiver_address": receiver_address,
            "amount": amount,
            "timestamp": time.time()
        }
        transactions.append(transaction_record)
        return jsonify({"message": "Transaction successful.", "transaction": transaction_record}), 200





@app.route('/send_to_external', methods=['POST'])
def send_to_external():
    sender_id = request.json.get("sender_id")
    sender_address = request.json.get("sender_address")
    external_address = request.json.get("external_address")
    amount = request.json.get("amount")
    external_currency = request.json.get("external_currency")

    # List of supported cryptocurrencies
    supported_currencies = ["Bitcoin", "Ethereum", "Litecoin", "Dogecoin"]

    # Validate sender details
    if sender_id not in wallets or wallets[sender_id]["address"] != sender_address:
        return jsonify({"error": "Invalid sender details."}), 400

    # Validate currency
    if external_currency not in supported_currencies:
        return jsonify({"error": f"Unsupported external currency. Supported: {', '.join(supported_currencies)}"}), 400

    # Check sender balance
    if wallets[sender_id]["balance"] < amount:
        return jsonify({"error": "Insufficient balance."}), 400

    # Deduct balance from sender
    wallets[sender_id]["balance"] -= amount

    # Record transaction for external address
    transaction_record = {
        "sender_id": sender_id,
        "sender_address": sender_address,
        "external_address": external_address,
        "amount": amount,
        "external_currency": external_currency,
        "timestamp": time.time()
    }
    transactions.append(transaction_record)

    return jsonify({"message": "Transaction to external address successful.", "transaction": transaction_record}), 200



@app.route("/wallet/deposit-inten", methods=["POST"])
def wallet_deposit_inten():
    """
    Desde la CRIPTOMONEDA → depositar INTEN en la WALLET Flask.

    Body JSON (pedido que TÚ envías como banco/admin):
    {
      "wallet": "WALADDR-...",
      "amount": 1000
    }
    """
    data = request.get_json(force=True) or {}

    wallet_addr = (data.get("wallet") or "").strip()
    try:
        amount = float(data.get("amount", 0))
    except:
        amount = 0.0

    if not wallet_addr or amount <= 0:
        return jsonify({"ok": False, "error": "wallet/amount invalid"}), 400

    payload = {
        "wallet": wallet_addr,
        "amount": amount,
        "secret": CRYPTO_INTEN_SECRET,
    }

    try:
        r = requests.post(
            f"{WALLET_BASE}/api/bridge/deposit-inten-from-crypto",
            json=payload,
            timeout=15,
        )
    except Exception as e:
        return jsonify({"ok": False, "error": f"wallet unreachable: {e}"}), 502

    try:
        data_wallet = r.json()
    except Exception:
        return jsonify({"ok": False, "error": "invalid response from wallet"}), 502

    return jsonify({
        "ok": True,
        "wallet_status": r.status_code,
        "wallet_response": data_wallet,
    })







# Other Flask routes and logic
@app.route('/mine', methods=['POST'])
def mine_block():
    if not transactions:
        return jsonify({"message": "No transactions to mine."}), 400

    # Reward the miner
    miner_reward = {
        "sender_id": "system",
        "sender_address": "crypto-system",
        "receiver_id": "miner",
        "receiver_address": "miner_wallet_address",  # Replace with actual miner wallet
        "amount": 50,  # Reward amount
        "timestamp": time.time()
    }
    transactions.append(miner_reward)

    # Proceed with mining
    last_block = blockchain[-1] if blockchain else create_genesis_block()
    last_proof = last_block['proof']
    proof = proof_of_work(last_proof)
    previous_hash = hash_block(last_block)
    block = create_block(proof, previous_hash)
    blockchain.append(block)

    return jsonify({"message": "Block mined successfully!", "block": block}), 200


# Automated mining function with dynamic rewards
from threading import Timer

def automated_mining():
    miner_wallet = "miner_wallet_address"  # Replace with an actual miner wallet address

    # Determine the reward based on the number of blocks mined
    reward_amount = 20 if len(blockchain) < 1000 else 50  # Adjust reward dynamically

    # Reward the miner
    miner_reward = {
        "sender_id": "system",
        "sender_address": "crypto-system",
        "receiver_id": "miner",
        "receiver_address": miner_wallet,
        "amount": reward_amount,
        "timestamp": time.time()
    }
    transactions.append(miner_reward)

    # Mine the block
    last_block = blockchain[-1] if blockchain else create_genesis_block()
    last_proof = last_block['proof']
    proof = proof_of_work(last_proof)
    previous_hash = hash_block(last_block)
    block = create_block(proof, previous_hash)
    blockchain.append(block)

    print(f"Block mined successfully! Block index: {block['index']}, Reward: {reward_amount} Intencoins")

    # Schedule next mining (every  5 minutes = 300 seconds)
    Timer(300, automated_mining).start()




# --- EN EL SCRIPT DEL PUERTO 8083 (proxy.py o similar) ---

# --- CONFIGURACIÓN GLOBAL (Debe ir al inicio del script del Puerto 8083) ---
WALLET_BRIDGE_URL = "http://127.0.0.1:5021/api/bridge/deposit_new" 

@app.route('/api/transfer_to_wallet', methods=['POST'])
def transfer_to_wallet():
    """
    Ruta para transferir INTEN desde la red externa al Wallet Bridge (5020).
    Actúa como un proxy de depósito.
    """
    try:
        # Usamos request.get_json() en lugar de request.json para mejor manejo de errores.
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400

    wallet_addr = data.get("wallet")
    
    # Manejo seguro de 'amount' y 'bridge_secret'
    try:
        amount = float(data.get("amount", 0))
    except ValueError:
        return jsonify({"error": "Amount must be a valid number"}), 400
        
    bridge_secret = data.get("bridge_secret") 
    
    # 1. Validación básica (deberías añadir más aquí)
    if not wallet_addr or amount <= 0 or not bridge_secret:
        return jsonify({"error": "Missing wallet address, valid amount, or bridge secret"}), 400
        
    # Lógica de "retiro" de Intencoin (aquí se verificaría el saldo y se debitaría)
    # ...

    # 3. Llamada al API de Bridge del Wallet Bridge (Puerto 5020)
    
    # *** CONSTRUCCIÓN DEL PAYLOAD PARA EL 5020 (Debe coincidir con lo que 5020 espera) ***
    payload = {
        "wallet": wallet_addr,
        "symbol": "INTEN",  # <--- Agregamos el symbol
        "amount": amount,
        # La clave es 'bridge_secret' y el valor es lo que recibimos del curl
        "bridge_secret": bridge_secret 
    }                                                                                         
    
    try:
        # Se asume que WALLET_BRIDGE_URL = "http://127.0.0.1:5020/api/bridge/deposit_new"
        response = requests.post(WALLET_BRIDGE_URL, json=payload, timeout=5)
        response.raise_for_status() # Lanza una excepción si la respuesta es 4xx o 5xx
        
        # Si llega aquí, la transferencia al 5020 fue exitosa.
        # ... (registro de la transacción)
        
        return jsonify({
            "message": "INTEN transferido y acreditado en el Wallet Bridge.",
            "wallet_response": response.json(),
            "amount": amount,
            "target_wallet": wallet_addr
        }), 200
                                                 
    except requests.exceptions.RequestException as e:
        # Captura cualquier error de conexión o HTTP (como 401 UNAUTHORIZED o 500)
        return jsonify({"error": f"Failed to connect to wallet bridge: {e}"}), 500









if __name__ == "__main__":
    blockchain.append(create_genesis_block())
    call_active_apis()  # Initialize APIs if applicable
    automated_mining()  # Start the mining process






@app.route('/restore_data', methods=['POST'])
def restore_data():
    """Restore blockchain, wallets, and transactions."""
    global blockchain, wallets, transactions
    data = request.json
    blockchain = data.get("blockchain", [])
    wallets = data.get("wallets", {})
    transactions = data.get("transactions", [])
    return jsonify({"message": "Data restored successfully."}), 200


# Colócala cerca de las otras rutas de la aplicación Flask
@app.route('/generate_new_apikey', methods=['POST'])
def generate_new_apikey():
    """Genera una nueva clave de API única y la devuelve."""
    # Se utiliza uuid4 para generar una cadena única que puede servir como clave API
    new_key = str(uuid.uuid4())
    
    # Aquí puedes añadir lógica para almacenar new_key y asociarla a un usuario/servicio
    # Por ahora, solo la devolvemos.
    
    return jsonify({
        "message": "API Key generada exitosamente.",
        "api_key": new_key,
        "note": "Asegúrate de guardar esta clave; no se mostrará de nuevo."
    }), 201 




if __name__ == "__main__":
    blockchain.append(create_genesis_block())  # Initialize the genesis block
    periodic_sync()  # Start periodic data sync to the database
    automated_mining()  # Start the automated mining process
    app.run(host='0.0.0.0', port=8083)  # Run the Flask app














