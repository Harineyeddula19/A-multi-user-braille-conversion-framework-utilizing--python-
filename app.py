from flask import Flask, request, jsonify, render_template_string
import firebase_admin
from firebase_admin import credentials, db

# =====================
# BRAILLE TRANSLATOR
# =====================
UEB_MAP = {
    "100000": "a", "110000": "b", "100100": "c", "100110": "d",
    "100010": "e", "110100": "f", "110110": "g", "110010": "h",
    "010100": "i", "010110": "j", "000000": " "
}

NEMETH_DIGITS = {
    "100000": "1", "110000": "2", "100100": "3", "100110": "4",
    "100010": "5", "110100": "6", "110110": "7", "110010": "8",
    "010100": "9", "010110": "0"
}

def translate_cell(bits: str, mode="UEB") -> str:
    if mode.upper() == "NEMETH":
        return NEMETH_DIGITS.get(bits, "?")
    return UEB_MAP.get(bits, "?")


# =====================
# FIREBASE SETUP
# =====================
cred = credentials.Certificate("firebase-key.json")  # <-- your Firebase service account file
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://<YOUR_PROJECT_ID>.firebaseio.com/"  # replace with your Firebase URL
})

def update_translation(user_id: str, text: str):
    ref = db.reference(f"translations/{user_id}")
    ref.set({"text": text})

def get_translation(user_id: str) -> str:
    ref = db.reference(f"translations/{user_id}")
    data = ref.get()
    return data["text"] if data else ""


# =====================
# FLASK APP
# =====================
app = Flask(__name__)
USER_BUFFERS = {}

# Web UI (inline template for simplicity)
HTML_PAGE = """
<!doctype html>
<html>
<head>
  <title>Braille Conversion</title>
  <meta charset="utf-8">
</head>
<body style="font-family:Arial;margin:30px;">
  <h2>Multi-user Braille Conversion</h2>
  <input id="user" placeholder="Enter User ID">
  <select id="mode">
    <option>UEB</option>
    <option>NEMETH</option>
  </select>
  <br><br>
  <input id="bits" placeholder="Enter 6-bit braille (e.g., 100000)">
  <button onclick="sendInput()">Send</button>
  <pre id="output"></pre>

  <script>
    async function sendInput(){
      const user = document.getElementById("user").value || "default";
      const bits = document.getElementById("bits").value;
      const mode = document.getElementById("mode").value;

      let res = await fetch("/api/input", {
        method:"POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({user_id:user, bits:bits, mode:mode})
      });
      let data = await res.json();
      document.getElementById("output").textContent = data.full_text;
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/api/input", methods=["POST"])
def api_input():
    data = request.get_json()
    user_id = data.get("user_id", "default")
    bits = data.get("bits", "000000")
    mode = data.get("mode", "UEB")

    token = translate_cell(bits, mode)
    USER_BUFFERS[user_id] = USER_BUFFERS.get(user_id, "") + token

    # Push to Firebase
    update_translation(user_id, USER_BUFFERS[user_id])
    return jsonify({"translated": token, "full_text": USER_BUFFERS[user_id]})

@app.route("/api/get/<user_id>")
def api_get(user_id):
    text = get_translation(user_id)
    return jsonify({"text": text})


# =====================
# RUN SERVER
# =====================
if __name__ == "__main__":
    app.run(debug=True)
