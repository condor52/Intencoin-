from flask import Flask, request, jsonify

# Inicialización de Flask en el puerto 5001
app = Flask(__name__)

# --- ALMACENAMIENTO DE DATOS EN MEMORIA ---
# Estos diccionarios y listas actuarán como tu "base de datos"
data_storage = {
    "blockchain": [],  # Datos de la Criptomoneda (5000)
    "wallets": {},     # Datos de la Wallet (5020)
    "transactions": [] # Transacciones pendientes de ambas apps
}
# ----------------------------------------

@app.route('/')
def home():
    return jsonify({"message": "Database API is running on port 5001."}), 200

# ====================================================================
# RUTAS PARA ALMACENAR DATOS (POST)
# ====================================================================

@app.route('/api/store_blockchain', methods=['POST'])
def store_blockchain():
    """Guarda la cadena de bloques (Blockchain) enviada por el Puerto 5000."""
    try:
        data = request.json.get("blockchain")
        if data is None:
            return jsonify({"error": "Missing 'blockchain' data"}), 400
        data_storage["blockchain"] = data
        return jsonify({"message": "Blockchain data stored successfully."}), 200
    except Exception as e:
        return jsonify({"error": f"Error storing blockchain: {e}"}), 500

@app.route('/api/store_wallets', methods=['POST'])
def store_wallets():
    """Guarda los datos de las wallets enviados por el Puerto 5020."""
    try:
        data = request.json.get("wallets")
        if data is None:
            return jsonify({"error": "Missing 'wallets' data"}), 400
        data_storage["wallets"] = data
        return jsonify({"message": "Wallets data stored successfully."}), 200
    except Exception as e:
        return jsonify({"error": f"Error storing wallets: {e}"}), 500

@app.route('/api/store_transactions', methods=['POST'])
def store_transactions():
    """Guarda las transacciones pendientes (de ambos sistemas)."""
    try:
        data = request.json.get("transactions")
        if data is None:
            return jsonify({"error": "Missing 'transactions' data"}), 400
        data_storage["transactions"] = data
        return jsonify({"message": "Transactions data stored successfully."}), 200
    except Exception as e:
        return jsonify({"error": f"Error storing transactions: {e}"}), 500


# ====================================================================
# RUTAS PARA RECUPERAR DATOS (GET)
# ====================================================================

@app.route('/api/get_all_data', methods=['GET'])
def get_all_data():
    """Devuelve todo el almacenamiento actual (para diagnóstico)."""
    return jsonify(data_storage), 200

# ====================================================================

if __name__ == "__main__":
    # La base de datos debe correr en el puerto 5001
    app.run(host="0.0.0.0", port=5002)




0

