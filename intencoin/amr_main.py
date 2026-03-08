from flask import Flask, request, jsonify
import requests
import uuid
import time
import hashlib
from threading import Timer

app = Flask(__name__)

# 5 API slots for crypto connections
crypto_api_slots = [{"slot": i, "url": None, "status": "disabled"} for i in range(5)]

# Wallet and blockchain data
wallets = {}
blockchain = []
transactions = []

# Helper functions
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

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the blockchain API"}), 200

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
    wallets[user_id] = {"address": wallet_address, "balance": 50}  # Mining reward
    reward_transaction = {
        "sender": "Mining Reward",
        "receiver": user_id,
        "amount": 50,
        "timestamp": time.time(),
    }
    transactions.append(reward_transaction)
    mine_block()

    return jsonify({
        "message": "Wallet created successfully.",
        "wallet_address": wallet_address,
        "balance": 50,
    }), 200

@app.route('/transaction', methods=['POST'])
def make_transaction():
    sender_id = request.json.get("sender_id")
    receiver_id = request.json.get("receiver_id")
    amount = request.json.get("amount")

    if sender_id not in wallets or receiver_id not in wallets:
        return jsonify({"error": "Invalid sender or receiver ID."}), 400
    if wallets[sender_id]["balance"] < amount:
        return jsonify({"error": "Insufficient balance."}), 400

    wallets[sender_id]["balance"] -= amount
    wallets[receiver_id]["balance"] += amount
    transaction_record = {
        "sender": sender_id,
        "receiver": receiver_id,
        "amount": amount,
        "timestamp": time.time(),
    }
    transactions.append(transaction_record)
    return jsonify({"message": "Transaction successful.", "transaction": transaction_record}), 200

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
    last_block = blockchain[-1] if blockchain else create_genesis_block()
    proof = 0
    while not valid_proof(last_block["proof"], proof):
        proof += 1
    previous_hash = hash_block(last_block)
    block = {
        "index": len(blockchain) + 1,
        "timestamp": time.time(),
        "transactions": transactions.copy(),
        "proof": proof,
        "previous_hash": previous_hash,
    }
    transactions.clear()
    blockchain.append(block)
    return block

def hash_block(block):
    encoded_block = str(block).encode()
    return hashlib.sha256(encoded_block).hexdigest()

def valid_proof(last_proof, proof):
    guess = f'{last_proof}{proof}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash[:4] == "0000"


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
    blockchain.append(create_genesis_block())
    app.run(host="0.0.0.0", port=5000)







0

0

0
