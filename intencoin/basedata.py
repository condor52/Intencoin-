# firestore_db.py
import firebase_admin
from firebase_admin import credentials, firestore
import os
import logging

logging.basicConfig(level=logging.INFO)

# --- CONFIGURACIÓN DE FIREBASE (PRODUCCIÓN) ---
# IMPORTANTE: 
# 1. Este archivo de credenciales DEBE descargarse de la consola de Firebase.
# 2. Debes instalar 'firebase-admin' (pip install firebase-admin).
CREDENTIALS_PATH = 'serviceAccountKey.json' 
DB_COLLECTION = 'inten_miner_chain' # Colección principal para la cadena
DB_DOCUMENT = 'MINER_STATE_5001'   # Documento único para almacenar el estado del minero 5001

db = None # Objeto Firestore Client

try:
    if os.path.exists(CREDENTIALS_PATH):
        # 1. Inicialización del SDK de Admin con las credenciales
        cred = credentials.Certificate(CREDENTIALS_PATH)
        # El nombre de la aplicación ayuda a evitar errores si se llama dos veces
        firebase_admin.initialize_app(cred, name='miner_app') 
        db = firestore.client()
        logging.info("✅ CONEXIÓN A FIREBASE ESTABLECIDA con credenciales de producción.")
    else:
        logging.error(f"❌ ERROR: Archivo de credenciales '{CREDENTIALS_PATH}' no encontrado.")
        logging.warning("⚠️ Advertencia: El script está corriendo, pero NO habrá persistencia en la base de datos.")
except Exception as e:
    logging.error(f"❌ ERROR CRÍTICO al inicializar Firebase Admin SDK: {e}")
    db = None
# -----------------------------------------------------------------------------

def save_miner_state(blockchain, transactions, known_wallets, peer_nodes, miner_address):
    """Guarda el estado completo del minero en Firestore."""
    if db is None:
        return
    try:
        doc_ref = db.collection(DB_COLLECTION).document(DB_DOCUMENT)
        
        # Firestore no guarda 'sets' nativamente, convertimos a lista
        data_to_save = {
            'blockchain': blockchain,
            'transactions': transactions,
            'known_wallets': list(known_wallets),
            'peer_nodes': list(peer_nodes),
            'miner_address': miner_address
        }
        
        doc_ref.set(data_to_save)
        logging.info(f"💾 Estado guardado en Firestore. Bloques: {len(blockchain)}")
    except Exception as e:
        logging.error(f"❌ ERROR al guardar en Firestore: {e}")

def load_miner_state():
    """Carga el estado completo del minero desde Firestore."""
    if db is None:
        return None
    try:
        doc_ref = db.collection(DB_COLLECTION).document(DB_DOCUMENT)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            logging.info("♻️ Estado cargado de Firestore con éxito.")
            # Convertimos las listas de vuelta a sets para su uso interno
            return {
                'blockchain': data.get('blockchain', []),
                'transactions': data.get('transactions', []),
                'known_wallets': set(data.get('known_wallets', [])),
                'peer_nodes': set(data.get('peer_nodes', [])),
            }
        else:
            logging.warning(f"⚠️ Documento '{DB_DOCUMENT}' no encontrado. Iniciando de cero.")
            return None
    except Exception as e:
        logging.error(f"❌ ERROR al cargar desde Firestore: {e}")
        return None




