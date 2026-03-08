
from flask import Flask, request, jsonify
import requests
import threading
import time

app = Flask(__name__)

# Configuración del minero
MINER_NOTIFY_URL = "http://127.0.0.1:5020/api/notify_deposit"
BRIDGE_SECRET = "dev-bridge-secret"  # Debe coincidir con el secreto de la wallet

registered_wallets = {}
pending_txs = []

def mine_block():
    while True:
        time.sleep(300)  # Minar cada 5 minutos
        if registered_wallets:
            for wallet in registered_wallets:
                reward = 50  # Recompensa fija para simplificar
                reward_payload = {
                    "wallet": wallet,
                    "amount": reward,
                    "symbol": "INTEN",
                    "secret": BRIDGE_SECRET
                }
                try:
                    response = requests.post(MINER_NOTIFY_URL, json=reward_payload, timeout=5)
                    response.raise_for_status()
                    print(f"→ Recompensa enviada a {wallet}: {reward} INTEN")
                except Exception as e:
                    print(f"⚠️ Error al enviar recompensa a {wallet}: {e}")

            # Limpiar las transacciones pendientes después de minar
            pending_txs.clear()
        else:
            print("No hay wallets registradas, minando sin recompensas.")

@app.route("/api/notify_deposit", methods=["POST"])
def notify_deposit():
    data = request.get_json()
    wallet = data.get("wallet")
    amount = data.get("amount")
    symbol = data.get("symbol")
    secret = data.get("secret")

    if secret != BRIDGE_SECRET:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    if wallet not in registered_wallets:
        registered_wallets[wallet] = amount
        print(f"Wallet {wallet} registrada con saldo inicial de {amount} {symbol}.")

    pending_txs.append({
        "wallet": wallet,
        "amount": amount,
        "symbol": symbol
    })

    return jsonify({"ok": True, "message": "Notificación recibida"}), 200

mining_thread = threading.Thread(target=mine_block, daemon=True)
mining_thread.start()

if __name__ == "__main__":
    app.run(port=5004)



