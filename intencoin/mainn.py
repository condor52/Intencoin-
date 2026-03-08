





from flask import Flask, jsonify
import time
import threading
import uuid
import hashlib # ← NECESARIO
import json # ← NECESARIO


app = Flask(__name__)

# Blockchain simplificada
blockchain = []
transactions = []

# Función para crear el bloque génesis
def create_genesis_block():
    return {
        "index": 1,
        "timestamp": time.time(),
        "transactions": [],
        "proof": 100,
        "previous_hash": "1",
    }

# Función para crear un nuevo bloque
def create_block(proof, previous_hash, transactions):
    block = {
        "index": len(blockchain) + 1,
        "timestamp": time.time(),
        "transactions": transactions,
        "proof": proof,
        "previous_hash": previous_hash,
    }
    return block

# Función para minar un nuevo bloque
def mine_block():
    last_block = blockchain[-1] if blockchain else create_genesis_block()
    last_proof = last_block['proof']
    proof = proof_of_work(last_proof)
    previous_hash = hash_block(last_block)
    block = create_block(proof, previous_hash, transactions)
    
    # Recompensa fija de 20 IntenCoins
    reward_transaction = {
        "sender": "system",
        "receiver": "miner",
        "amount": 20,
    }
    block["transactions"].append(reward_transaction)
    
    # Añadir el bloque a la cadena y limpiar transacciones pendientes
    blockchain.append(block)
    transactions.clear()
    print(f"Bloque minado: {block['index']} con recompensa de 20 IntenCoins")

# Prueba de trabajo simple (proof of work)
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

# Función de minería automática cada 5 minutos
def automated_mining():
    mine_block()
    threading.Timer(300, automated_mining).start()  # 300 segundos = 5 minutos

# Ruta para minar manualmente
@app.route('/mine', methods=['POST'])
def manual_mine():
    mine_block()
    return jsonify({"message": "Bloque minado manualmente"}), 200

if __name__ == '__main__':
    # Inicializar la blockchain con el bloque génesis
    blockchain.append(create_genesis_block())
    # Iniciar la minería automática
    automated_mining()
    app.run(host='0.0.0.0', port=5002)






