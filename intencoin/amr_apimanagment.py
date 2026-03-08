



from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# API Slots Data
crypto_api_slots = [{"slot": i, "url": None, "status": "disabled"} for i in range(10)]
admin_api_slots = [{"slot": i, "url": None, "status": "disabled"} for i in range(5)]
external_api_slots = [{"slot": i, "url": None, "status": "disabled"} for i in range(5)]

# Admin Dashboard Template
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
</head>
<body>
    <h1>Admin Dashboard</h1>

    <h2>API Management</h2>
    <a href="/admin/apis">Manage APIs</a>
    <form method="POST" action="/admin/generate_api">
        <button type="submit">Generate API</button>
    </form>

    <h2>Upload Logo</h2>
    <form method="POST" action="/admin/upload_logo" enctype="multipart/form-data">
        <label>Description:</label>
        <input type="text" name="description">
        <input type="file" name="logo" required>
        <button type="submit">Upload Logo</button>
    </form>
</body>
</html>
'''

@app.route('/')
def admin_dashboard():
    return render_template_string(DASHBOARD_HTML)

# Generate API Button
@app.route('/admin/generate_api', methods=['POST'])
def generate_api():
    api_key = str(uuid.uuid4())
    return jsonify({"message": "API generated successfully!", "api_key": api_key})

# API Management Page
@app.route('/admin/apis', methods=['GET', 'POST'])
def manage_apis():
    api_html = '''
    <h1>API Management</h1>
    <h2>Cryptocurrency APIs</h2>
    <ul>
        {% for slot in crypto_api_slots %}
        <li>Slot {{ slot.slot }}: 
            <form method="POST" action="/admin/apis/edit/{{ slot.slot }}" style="display:inline;">
                <input type="text" name="url" value="{{ slot.url or '' }}" placeholder="Paste API URL">
                <button type="submit">Save</button>
            </form>
            <form method="POST" action="/admin/apis/toggle/{{ slot.slot }}" style="display:inline;">
                <button type="submit">{{ "Disable" if slot.status == "enabled" else "Enable" }}</button>
            </form>
        </li>
        {% endfor %}
    </ul>
    <h2>Admin APIs</h2>
    <ul>
        {% for slot in admin_api_slots %}
        <li>Slot {{ slot.slot }}: 
            <form method="POST" action="/admin/apis/edit_admin/{{ slot.slot }}" style="display:inline;">
                <input type="text" name="url" value="{{ slot.url or '' }}" placeholder="Paste API URL">
                <button type="submit">Save</button>
            </form>
            <form method="POST" action="/admin/apis/toggle_admin/{{ slot.slot }}" style="display:inline;">
                <button type="submit">{{ "Disable" if slot.status == "enabled" else "Enable" }}</button>
            </form>
        </li>
        {% endfor %}
    </ul>
    <h2>External APIs</h2>
    <ul>
        {% for slot in external_api_slots %}
        <li>Slot {{ slot.slot }}: 
            <form method="POST" action="/admin/apis/edit_external/{{ slot.slot }}" style="display:inline;">
                <input type="text" name="url" value="{{ slot.url or '' }}" placeholder="Paste API URL">
                <button type="submit">Save</button>
            </form>
            <form method="POST" action="/admin/apis/toggle_external/{{ slot.slot }}" style="display:inline;">
                <button type="submit">{{ "Disable" if slot.status == "enabled" else "Enable" }}</button>
            </form>
        </li>
        {% endfor %}
    </ul>
    <a href="/">Back to Dashboard</a>
    '''
    return render_template_string(api_html, crypto_api_slots=crypto_api_slots, admin_api_slots=admin_api_slots, external_api_slots=external_api_slots)

@app.route('/admin/apis/edit/<int:slot>', methods=['POST'])
def edit_crypto_api(slot):
    url = request.form['url']
    if 0 <= slot < len(crypto_api_slots):
        crypto_api_slots[slot]['url'] = url
        return redirect('/admin/apis')
    return "Invalid slot", 400

@app.route('/admin/apis/toggle/<int:slot>', methods=['POST'])
def toggle_crypto_api(slot):
    if 0 <= slot < len(crypto_api_slots):
        status = crypto_api_slots[slot]['status']
        crypto_api_slots[slot]['status'] = "disabled" if status == "enabled" else "enabled"
        return redirect('/admin/apis')
    return "Invalid slot", 400

@app.route('/admin/apis/edit_admin/<int:slot>', methods=['POST'])
def edit_admin_api(slot):
    url = request.form['url']
    if 0 <= slot < len(admin_api_slots):
        admin_api_slots[slot]['url'] = url
        return redirect('/admin/apis')
    return "Invalid slot", 400

@app.route('/admin/apis/toggle_admin/<int:slot>', methods=['POST'])
def toggle_admin_api(slot):
    if 0 <= slot < len(admin_api_slots):
        status = admin_api_slots[slot]['status']
        admin_api_slots[slot]['status'] = "disabled" if status == "enabled" else "enabled"
        return redirect('/admin/apis')
    return "Invalid slot", 400

@app.route('/admin/apis/edit_external/<int:slot>', methods=['POST'])
def edit_external_api(slot):
    url = request.form['url']
    if 0 <= slot < len(external_api_slots):
        external_api_slots[slot]['url'] = url
        return redirect('/admin/apis')
    return "Invalid slot", 400

@app.route('/admin/apis/toggle_external/<int:slot>', methods=['POST'])
def toggle_external_api(slot):
    if 0 <= slot < len(external_api_slots):
        status = external_api_slots[slot]['status']
        external_api_slots[slot]['status'] = "disabled" if status == "enabled" else "enabled"
        return redirect('/admin/apis')
    return "Invalid slot", 400

# Logo Upload
@app.route('/admin/upload_logo', methods=['POST'])
def upload_logo():
    description = request.form.get('description', '')
    if 'logo' in request.files:
        file = request.files['logo']
        if file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            return jsonify({"message": "Logo uploaded successfully.", "description": description, "file_path": file_path})
    return "Logo upload failed", 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)









0

