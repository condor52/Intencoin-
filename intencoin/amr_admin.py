from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import uuid
import random

app = Flask(__name__)

# Data Storage
wallets = {}
cards = {}
api_key = None  # For generated API key
blockchain_connected = False  # Placeholder; assume connection can be verified
intencoin_price = 0.0
total_supply = 0

# Dashboard Template
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin AMR COIN  Dashboard</title>
</head>
<body>
    <h1>Admin Dashboard</h1>

    <h2>Blockchain Status</h2>
    <p>Status: {{ "Connected" if blockchain_connected else "Not Connected" }}</p>

    <h2>Intencoin Management</h2>
    <p>Current Price: ${{ intencoin_price }}</p>
    <p>Total Supply: {{ total_supply }}</p>
    <form method="POST" action="/admin/update_price">
        <label>Price ($):</label>
        <input type="number" step="0.01" name="price" required>
        <button type="submit">Update Price</button>
    </form>
    <form method="POST" action="/admin/update_supply">
        <label>Total Supply:</label>
        <input type="number" name="supply" required>
        <button type="submit">Update Supply</button>
    </form>

    <h2>Wallet and Mega Visa Management</h2>
    <a href="/wallets">Manage Wallets and Cards</a>

    <h2>API Key Management</h2>
    <p>Generated API Key: {{ api_key or "None" }}</p>
    <form method="POST" action="/generate_api_key">
        <button type="submit">Generate API Key</button>
    </form>
</body>
</html>
'''

# Wallet Template (Unchanged)
WALLET_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Wallet Management</title>
</head>
<body>
    <h1>Wallet Management</h1>
    <p>Blockchain Status: {{ "Connected" if blockchain_connected else "Not Connected" }}</p>
    <ul>
        {% for user_id, wallet in wallets.items() %}
        <li>
            <strong>{{ user_id }}</strong>: 
            Address: {{ wallet.address }}, 
            Balance: ${{ wallet.balance }}
        </li>
        {% endfor %}
    </ul>
    <form method="POST" action="/wallet/create">
        <label>User ID:</label>
        <input type="text" name="user_id" required>
        <button type="submit">Create Wallet</button>
    </form>

    <h2>Wallet Transactions</h2>
    <form method="POST" action="/wallet/send">
        <label>Sender ID:</label>
        <input type="text" name="sender" required>
        <label>Receiver Address:</label>
        <input type="text" name="receiver" required>
        <label>Amount:</label>
        <input type="number" step="0.01" name="amount" required>
        <button type="submit">Send Funds</button>
    </form>
    <h2>Receive Funds</h2>
    <form method="POST" action="/wallet/receive">
        <label>Receiver ID:</label>
        <input type="text" name="receiver" required>
        <label>Amount:</label>
        <input type="number" step="0.01" name="amount" required>
        <button type="submit">Receive Funds</button>
    </form>
    <a href="/">Back to Dashboard</a>
</body>
</html>
'''

@app.route('/')
def admin_dashboard():
    return render_template_string(DASHBOARD_HTML, blockchain_connected=blockchain_connected, intencoin_price=intencoin_price, total_supply=total_supply, api_key=api_key)

@app.route('/generate_api_key', methods=['POST'])
def generate_api_key():
    global api_key
    api_key = str(uuid.uuid4())
    return redirect('/')

# Wallet Management
@app.route('/wallets', methods=['GET'])
def manage_wallets():
    return render_template_string(WALLET_HTML, blockchain_connected=blockchain_connected, wallets=wallets, cards=cards)

@app.route('/wallet/create', methods=['POST'])
def create_wallet():
    user_id = request.form['user_id']
    if user_id not in wallets:
        wallets[user_id] = {"address": str(uuid.uuid4()), "balance": 0.0}
    return redirect('/wallets')
    

@app.route('/wallet/send', methods=['POST'])
def send_funds():
    sender = request.form['sender']
    receiver = request.form['receiver']
    amount = float(request.form['amount'])

    # Validate sender and receiver existence
    if sender not in wallets:
        return jsonify({"error": "Sender wallet not found"}), 400
    if receiver not in wallets:
        return jsonify({"error": "Receiver wallet not found"}), 400

    # Validate sender's balance
    if wallets[sender]['balance'] < amount:
        return jsonify({"error": "Insufficient funds"}), 400

    # Perform the transaction
    wallets[sender]['balance'] -= amount
    wallets[receiver]['balance'] += amount

    return jsonify({
        "message": "Transaction successful",
        "sender": sender,
        "receiver": receiver,
        "amount": amount
    })



@app.route('/wallet/receive', methods=['POST'])
def receive_funds():
    receiver = request.form['receiver']
    amount = float(request.form['amount'])

    # Validate receiver existence
    if receiver not in wallets:
        return jsonify({"error": "Receiver wallet not found"}), 400

    # Validate amount
    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    # Credit receiver's wallet
    wallets[receiver]['balance'] += amount

    return jsonify({
        "message": "Funds received",
        "receiver": receiver,
        "amount": amount
    })


# Intencoin Management (Unchanged)
@app.route('/admin/update_price', methods=['POST'])
def update_price():
    global intencoin_price
    intencoin_price = float(request.form['price'])
    return redirect('/')

@app.route('/admin/update_supply', methods=['POST'])
def update_supply():
    global total_supply
    total_supply = int(request.form['supply'])
    return redirect('/')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
















0


0

0

