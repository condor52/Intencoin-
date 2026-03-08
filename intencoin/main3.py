import hashlib
import json
from time import time
from uuid import uuid4
import requests
from flask import Flask, jsonify, request
import os
import threading

# --- CONFIGURACIÓN ---
MINER_SECRET = os.environ.get("MINER_SECRET", "dev-miner-secret")
MINING_REWARD = 20.0
WALLET_APP_URL = os.environ.get("WALLET_APP_URL", "http://127.0.0.1:5020")
MINING_INTERVAL_SECONDS = 300 # Minado automático cada 5 minutos
# --- FIN CONFIGURACIÓN ---

class Blockchain:
    def __init__(self):
        self.chain = []
        # El pool de transacciones pendientes para el próximo bloque
        self.transactions = []
        self.nodes = set()
        # Crear el bloque Génesis
        self.new_block(proof=100, previous_hash='GENESIS')

    def register_node(self, address):
        """Añade un nuevo nodo a la lista de nodos"""
        parsed_url = requests.utils.urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """Determina si una cadena de bloques dada es válida"""
        # ... (código para valid_chain no modificado)
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            last_block = chain[current_index - 1]
            # Verificar el hash
            if block['previous_hash'] != self.hash(last_block):
                return False
            # Verificar la Prueba de Trabajo
            if not self.valid_proof(last_block['proof'], block['proof'], self.hash(last_block)):
                return False
            current_index += 1
        return True

    def resolve_conflicts(self):
        # ... (código para resolve_conflicts no modificado)
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbours:
            try:
                response = requests.get(f'http://{node}/get_blockchain')
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['blockchain']

                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
            except requests.exceptions.ConnectionError:
                print(f"Error de conexión con el nodo: {node}")
                continue

        if new_chain:
            self.chain = new_chain
            return True
        return False

    def new_block(self, proof, previous_hash=None):
        """
        Crea un nuevo bloque y lo añade a la cadena.
        Las transacciones pendientes son incluidas aquí.
        """
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        
        # Limpiar la lista de transacciones después de incluirlas en el bloque
        self.transactions = [] 
        self.chain.append(block)
        return block

    def new_transaction(self, sender, receiver, amount, symbol="INTEN"):
        """Añade una nueva transacción al pool de minería (self.transactions)"""
        # Se asegura de que 'amount' sea float antes de añadir
        try:
            amount = float(amount)
        except ValueError:
            print("ERROR: El monto de la transacción no es un número válido.")
            return None

        self.transactions.append({
            'sender': sender,
            'receiver': receiver,
            'amount': amount,
            'symbol': symbol,
            'timestamp': time()
        })
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """Crea un hash SHA-256 de un bloque"""
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """Implementación simple del Algoritmo de Prueba de Trabajo"""
        proof = 0
        # Incluir el hash del último bloque para hacerlo más robusto
        last_hash = self.hash(self.last_block)
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """Valida la Prueba: ¿El hash(última_prueba, prueba, último_hash) contiene 4 ceros iniciales?"""
        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        # Dificultad: 4 ceros iniciales
        return guess_hash[:4] == "0000"

    def send_reward(self, receiver_address, amount=MINING_REWARD):
        """
        Notifica a la Wallet App (5020) que debe acreditar la recompensa de minería.
        """
        reward_tx_url = f'{WALLET_APP_URL}/api/bridge/deposit_new'
        reward_data = {
            'wallet': receiver_address,
            'symbol': 'INTEN',
            'amount': amount,
            'bridge_secret': MINER_SECRET, 
            'is_miner_reward': True 
        }
        
        try:
            response = requests.post(reward_tx_url, json=reward_data, timeout=5)
            if response.status_code == 200:
                print(f"✅ Recompensa de {amount} INTEN enviada a {receiver_address} (Puerto 5020).")
                return {"reward_ok": True}
            else:
                print(f"❌ ERROR: Wallet 5020 respondió con código {response.status_code} al enviar recompensa.")
                return {"reward_ok": False, "status": response.status_code}
        except requests.exceptions.ConnectionError:
            print(f"❌ ERROR: No se pudo conectar con Wallet 5020 para enviar recompensa. Verifique que 5020 esté corriendo.")
            return {"reward_ok": False, "status": "Connection Error"}

# =========================================================================
# FLASK APP Y ENDPOINTS
# =========================================================================

app = Flask(__name__)
node_identifier = str(uuid4()).replace('-', '')
blockchain = Blockchain()

# --- LÓGICA DE MINADO (SIN CONDICIÓN DE TRANSACCIONES) ---
@app.route('/mine', methods=['POST'])
def mine():
    # Minamos SIEMPRE para mantener la producción constante (Bloques Vacíos permitidos).

    # 1. Ejecutar el algoritmo de Prueba de Trabajo para el próximo bloque
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # 2. Asignar Recompensa (Se hace ANTES de crear el bloque)
    MINER_ADDRESS_FOR_REWARD = "WALADDR-MINER-1A2B3C4D" 
    reward_status = blockchain.send_reward(MINER_ADDRESS_FOR_REWARD, MINING_REWARD)
    
    # 3. Crear el nuevo Bloque (incluye TXs pendientes, o solo la recompensa si el pool estaba vacío)
    new_block = blockchain.new_block(proof, blockchain.hash(last_block))
    
    response = {
        'message': "⛏️ Nuevo Bloque Forzado Minado (Bloques Vacíos permitidos)",
        'index': new_block['index'],
        # Usamos new_block['transactions'] para mostrar las TX de usuario que se incluyeron
        'transactions_in_block': new_block['transactions'], 
        'proof': new_block['proof'],
        'previous_hash': new_block['previous_hash'],
        'reward_status': reward_status
    }
    return jsonify(response), 200

# --- LÓGICA DE MINADO AUTOMÁTICO ---
def auto_miner_task():
    """Tarea que llama a /mine cada MINING_INTERVAL_SECONDS."""
    with app.app_context():
        try:
            # Llama al endpoint /mine que ahora está garantizado que minará
            response = requests.post(f'http://127.0.0.1:5001/mine')
            if response.status_code == 200:
                result = response.json()
                # Mostramos si el bloque se minó y cuántas TXs contenía
                print(f"\n--- [AUTO-MINER] Bloque {result['index']} minado. TXs incluidas: {len(result['transactions_in_block'])} ---\n")
            else:
                 print(f"\n--- [AUTO-MINER] ERROR al minar: {response.text} ---\n")
        except requests.exceptions.ConnectionError:
            pass
        
    threading.Timer(MINING_INTERVAL_SECONDS, auto_miner_task).start()

# Iniciar el Minero Automático si se ejecuta como el nodo 5001
if __name__ == '__main__':
    threading.Timer(MINING_INTERVAL_SECONDS, auto_miner_task).start()
    app.run(host='127.0.0.1', port=5001)

# --- ENDPOINT PARA RECIBIR NOTIFICACIONES DE TX (Desde Wallet 5020) ---
@app.route('/api/miner/notify', methods=['POST'])
def notify_miner():
    values = request.get_json()
    required = ['sender', 'receiver', 'amount', 'symbol', 'secret']
    
    if not all(k in values for k in required):
        return jsonify({"message": "Faltan valores requeridos para la TX."}), 400

    # 1. VERIFICACIÓN DEL SECRETO
    if values['secret'] != MINER_SECRET:
        print(f"❌ ERROR: Intento de notificación de TX con secreto incorrecto desde {request.remote_addr}")
        return jsonify({"message": "Acceso no autorizado (Secreto de Minero incorrecto)."}), 401

    # 2. AÑADIR AL POOL
    # new_transaction ahora incluye validación de float
    index = blockchain.new_transaction(
        values['sender'],
        values['receiver'],
        values['amount'],
        values['symbol']
    )
    
    if index is None: # Si falló la validación del monto
        return jsonify({"message": "Monto de transacción inválido."}), 400

    print(f"✅ Transacción válida recibida y añadida al Pool. Se minará en el Bloque {index}.")

    return jsonify({
        'message': f'Transacción añadida al Pool. Se incluirá en el Bloque {index}',
        'ok': True
    }), 200

# --- ENDPOINTS DE CONSULTA ---
@app.route('/get_blockchain', methods=['GET'])
def full_chain():
    response = {
        'blockchain': blockchain.chain,
        'length': len(blockchain.chain),
        'ok': True
    }
    return jsonify(response), 200

@app.route('/get_transactions', methods=['GET'])
def get_transactions():
    response = {
        'transactions': blockchain.transactions,
        'pending': len(blockchain.transactions),
        'ok': True
    }
    return jsonify(response), 200

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Nuestra cadena fue reemplazada',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Nuestra cadena es autoritaria',
            'chain': blockchain.chain
        }

    return jsonify(response), 200




# Dentro de la sección de CONFIGURACIÓN:
# ...
WALLET_APP_URL = os.environ.get("WALLET_APP_URL", "http://127.0.0.1:5020")
# ...

# Al final del archivo, en el bloque de inicio:
if __name__ == '__main__':
    # ... (código de inicio del hilo de minería automática)
    
    # Esta línea asegura que la aplicación Flask se ejecuta en el puerto 5001
    app.run(host='127.0.0.1', port=5001) 




