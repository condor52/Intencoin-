
from flask import Flask, request, jsonify
import time
import uuid

app = Flask(__name__)

# Simple blockchain data structures
blockchain = []
transactions = []

# Function to create a new block
def create_block(proof, previous_hash, txs):
    block = {
        'index': len(blockchain) + 1,
        'timestamp': time.time(),
        'transactions': txs,
        'proof': proof,
        'previous_hash': previous_hash
    }
    return block

# Function to create a new transaction
def create_transaction(sender, receiver, amount, symbol):
    tx = {
        'sender': sender,
        'receiver': receiver,
        'amount': amount,
        'symbol': symbol,
        'timestamp': time.time()
    }
    return tx

# Proof of work function (simple example)
def proof_of_work(last_proof):
    proof = 0
    while not valid_proof(last_proof, proof):
        proof += 1
    return proof

def valid_proof(last_proof, proof):
    guess = f'{last_proof}{proof}'.encode()
    guess_hash = hashlib.sha256(guess).hexdigest()
    return guess_hash[:4] == "0000"

# Add the genesis block
def create_genesis_block():
    return create_block(proof=100, previous_hash='1', txs=[])

blockchain.append(create_genesis_block())

# Simple wallet crediting logic
wallet_balances = {}

def credit_wallet(wallet, amount, symbol):
    if wallet not in wallet_balances:
        wallet_balances[wallet] = {}
    if symbol not in wallet_balances[wallet]:
        wallet_balances[wallet][symbol] = 0
    wallet_balances[wallet][symbol] += amount
    print(f"Credited {amount} {symbol} to {wallet}")

# Endpoint to receive notification from the wallet
@app.route('/api/miner/notify', methods=['POST'])
def api_miner_notify():
    data = request.get_json(force=True)
    wallet = data.get('wallet')
    amount = float(data.get('amount', 0))
    symbol = data.get('symbol', 'INTEN')
    
    if not wallet or amount <= 0:
        return jsonify({'ok': False, 'error': 'Invalid wallet or amount'}), 400
    
    # Credit the wallet with the amount
    credit_wallet(wallet, amount, symbol)
    
    # Add the transaction to the current block transactions
    transactions.append(create_transaction('mining_reward', wallet, amount, symbol))
    
    return jsonify({'ok': True, 'message': 'Reward credited to wallet'}), 200

# Endpoint to mine a new block (if needed)
@app.route('/mine', methods=['POST'])
def mine_block():
    last_block = blockchain[-1]
    last_proof = last_block['proof']
    proof = proof_of_work(last_proof)
    previous_hash = hash_block(last_block)
    
    block = create_block(proof, previous_hash, transactions.copy())
    transactions.clear()
    blockchain.append(block)
    
    return jsonify({'message': 'New block mined', 'block': block}), 200

# Utility function to hash a block
import hashlib
import json

def hash_block(block):
    encoded_block = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(encoded_block).hexdigest()

# Run the app on port 5001
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)







