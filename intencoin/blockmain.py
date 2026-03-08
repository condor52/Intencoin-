from flask import Flask, jsonify
import time
import threading
import uuid
import hashlib
import json

app = Flask(__name__)

# Datos en memoria
blockchain = []
transactions = []
wallets = {}

# Crear el bloque génesis
def create_genesis_block():
    return {
        "index": 1,
        "timestamp": time.time(),
        "transactions": [],
        "proof": 100,
        "previous_hash": "1",
    }

# Crear un nuevo bloque
def create_block(proof, previous_hash, transactions):
    block = {
        "index": len(blockchain) + 1,
        "timestamp": time.time(),
        "transactions": transactions,
        "proof": proof,
        "previous_hash": previous_hash,
    }
    return block

# Función para el algoritmo de prueba de trabajo
def proof_of_work(last_proof):
    proof = 0
    while not valid_proof(last_proof, proof):
        proof += 1
    return proof

def valid_proof(last_proof, proof):
    guess = f'{last_proof}{proof}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash[:4] == "0000"

def hash_block(block):
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

# Función de minería automática
def automated_mining():
    global transactions
    last_block = blockchain[-1] if blockchain else create_genesis_block()
    last_proof = last_block['proof']
    proof = proof_of_work(last_proof)
    previous_hash = hash_block(last_block)

    # Determinar la recompensa
    if transactions:
        reward_amount = 50 # Si hay transacciones
    else:
        reward_amount = 20 # Si no hay transacciones

    # Recompensa a todas las wallets
    reward_transactions = []
    for wallet_addr in wallets.keys():
        reward_transactions.append({
            "sender": "system",
            "receiver": wallet_addr,
            "amount": reward_amount
        })

    # Crear el bloque
    block = create_block(proof, previous_hash, transactions + reward_transactions)

    # Añadir el bloque a la cadena y limpiar las transacciones
    blockchain.append(block)
    transactions.clear()

    print(f"Bloque minado: {block['index']} con recompensa de {reward_amount} IntenCoins por wallet.")

    # Programar la próxima minería en 5 minutos
    threading.Timer(300, automated_mining).start()

# Ruta para minar manualmente (opcional)
@app.route('/mine', methods=['POST'])
def manual_mine():
    automated_mining() # Llama a la función de minería
    return jsonify({"message": "Bloque minado manualmente"}), 200

# Ruta para registrar una nueva wallet (por ejemplo)
@app.route('/register_wallet', methods=['POST'])
def register_wallet():
    wallet_id = str(uuid.uuid4())
    wallets[wallet_id] = {"balance": 0}
    return jsonify({"message": "Wallet registrada", "wallet_id": wallet_id}), 201

# Iniciar la blockchain con el bloque génesis
blockchain.append(create_genesis_block())

# Iniciar la minería automática
automated_mining()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)





