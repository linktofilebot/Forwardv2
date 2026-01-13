from flask import Flask, render_template_string, request, jsonify, session
from pymongo import MongoClient
import uuid
import secrets
import time
import hashlib

# ================= Configuration =================
app = Flask(__name__)
app.secret_key = secrets.token_hex(24)

# আপনার MongoDB Atlas URL
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" 
ADMIN_PASS = "admin786"

try:
    client = MongoClient(MONGO_URI)
    db = client['CloudTok_Final_DB']
    api_col = db['apis']     
    video_col = db['videos'] 
    print("✓ MongoDB Connected Successfully")
except Exception as e:
    print(f"✗ MongoDB Connection Error: {e}")

# ================= Frontend Template (HTML/CSS/JS) =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudTok Pro - Unlimited</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://upload-widget.cloudinary.com/global/all.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        body { background: #000; color: #fff; font-family: 'Inter', sans-serif; overflow: hidden; }
        .feed-container { height: 100vh; scroll-snap-type: y mandatory; overflow-y: scroll; scrollbar-width: none; }
        .video-card { height: 100vh; scroll-snap-align: start; position: relative; background: #000; display: flex; align-items: center; justify-content: center; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
        video { height: 100%; width: 100%; object-fit: cover; }
        .glass-ui { background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .active-api-border { border: 2px solid #06b6d4 !important; background: rgba(6, 182, 212, 0.15); }
        .btn-gradient { background: linear-gradient(45deg, #06b6d4, #3b82f6); }
    </style>
</head>
<body>

    <!-- Navigation -->
    <nav class="fixed top-0 w-full z-50 flex justify-between p-5 bg-gradient-to-b from-black to-transparent">
        <h1 class="text-2xl font-black italic tracking-tighter text-cyan-400 uppercase">Cloud<span class="text-white">Tok</span></h1>
        <button onclick="checkAuthAndOpenAdmin()" class="bg-white/10 backdrop-blur-md px-6 py-2 rounded-full text-[10px] font-bold border border-white/20 hover:bg-cyan-500 transition">ADMIN DASHBOARD</button>
    </nav>

    <!-- Vertical Video Feed -->
    <div id="videoFeed" class="feed-container scrollbar-hide"></div>

    <!-- Admin Login Modal -->
    <div id="loginModal" class="hidden fixed inset-0 z-[100] bg-black/95 flex items-center justify-center p-6">
        <div class="glass-ui p-8 rounded-3xl w-full max-w-sm text-center">
            <h2 class="text-2xl font-black mb-6 text-cyan-400 uppercase italic">Admin Access</h2>
            <input id="adminPassInput" type="password" placeholder="Enter Password" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-6 text-center outline-none focus:border-cyan-500">
            <button onclick="submitLogin()" class="w-full btn-gradient p-4 rounded-xl font-bold uppercase tracking-widest">Unlock</button>
            <button onclick="closeModals()" class="mt-4 text-gray-500 text-xs">Close</button>
        </div>
    </div>

    <!-- Admin Dashboard Panel -->
    <div id="adminPanel" class="hidden fixed inset-0 z-[80] bg-black p-4 md:p-8 overflow-y-auto">
        <div class="max-w-6xl mx-auto pb-20">
            <div class="flex justify-between items-center mb-10 border-b border-gray-800 pb-5">
                <h2 class="text-3xl font-black text-cyan-500 uppercase italic">Control Center</h2>
                <button onclick="location.reload()" class="text-white text-3xl hover:rotate-90 transition">✕</button>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-10">
                <!-- Column Left: API Management -->
                <div class="space-y-8">
                    <div class="glass-ui p-6 rounded-3xl border border-gray-800">
                        <h3 class="text-cyan-400 font-bold mb-4 uppercase text-xs tracking-widest">1. Add Cloudinary API (No Preset)</h3>
                        <div class="grid gap-4 mb-4">
                            <input id="api_cloud" placeholder="Cloud Name" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none">
                            <input id="api_key" placeholder="API Key" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none">
                            <input id="api_secret" placeholder="API Secret" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none">
                        </div>
                        <button onclick="saveApiConfig()" class="w-full bg-cyan-700 p-3 rounded-xl font-bold text-xs uppercase">Connect Account</button>
                        
                        <p class="mt-6 text-[10px] text-gray-500 uppercase font-bold mb-2 tracking-widest">Select Account to Use:</p>
                        <div id="apiListContainer" class="space-y-3"></div>
                    </div>

                    <!-- Column Left: Upload Section -->
                    <div class="glass-ui p-6 rounded-3xl border border-cyan-500/20 shadow-2xl">
                        <h3 class="text-cyan-400 font-bold mb-4 uppercase text-xs tracking-widest">2. Quick Upload Episode</h3>
                        <div class="flex gap-3 mb-6">
                            <input id="seriesTitle" placeholder="Movie/Series Name" class="w-2/3 bg-black p-4 rounded-xl border border-gray-800 outline-none">
                            <input id="episodeNo" type="number" placeholder="Ep." class="w-1/3 bg-black p-4 rounded-xl border border-gray-800 outline-none">
                        </div>
                        <button onclick="startSimpleUpload()" class="w-full btn-gradient p-5 rounded-2xl font-black text-xl hover:scale-[1.02] transition shadow-lg">🚀 SELECT VIDEO</button>
                    </div>
                </div>

                <!-- Column Right: Content List -->
                <div class="glass-ui p-6 rounded-3xl border border-gray-800">
                    <h3 class="text-gray-500 font-bold mb-4 uppercase text-xs tracking-widest">3. Manage Episodes</h3>
                    <div id="contentListUI" class="space-y-4 max-h-[600px] overflow-y-auto scrollbar-hide"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let appState = { apis: [], videos: [], active_api_id: null };

        // Fetch all data from server
        async function fetchSystemData() {
            const res = await fetch('/api/get_full_data');
            appState = await res.json();
            renderVideoFeed();
            if(!document.getElementById('adminPanel').classList.contains('hidden')) renderAdminDashboard();
        }

        // Render Vertical Feed
        function renderVideoFeed() {
            const feed = document.getElementById('videoFeed');
            if(appState.videos.length === 0) {
                feed.innerHTML = `<div class="h-screen flex items-center justify-center opacity-30 text-xs tracking-widest uppercase">No Content Available</div>`;
                return;
            }
            feed.innerHTML = appState.videos.map(v => `
                <div class="video-card">
                    <video src="${v.url}" loop autoplay muted playsinline onclick="this.paused?this.play():this.pause()"></video>
                    <div class="absolute bottom-12 left-6 right-20 z-10 pointer-events-none drop-shadow-2xl">
                        <h3 class="text-cyan-400 font-black text-4xl italic uppercase tracking-tighter">${v.series}</h3>
                        <p class="text-white font-bold text-xl opacity-90">Episode: ${v.episode}</p>
                    </div>
                </div>
            `).join('');
        }

        // Render Admin Lists
        function renderAdminDashboard() {
            const apiContainer = document.getElementById('apiListContainer');
            apiContainer.innerHTML = appState.apis.map(api => `
                <div onclick="switchActiveApi('${api.id}')" class="flex justify-between items-center p-4 rounded-2xl border cursor-pointer transition ${api.id === appState.active_api_id ? 'active-api-border shadow-lg' : 'border-gray-800 hover:border-gray-600'}">
                    <span class="text-sm font-bold text-white">${api.cloud}</span>
                    <button onclick="removeApiConfig('${api.id}')" class="text-red-500 font-black hover:scale-125 transition px-2">✕</button>
                </div>
            `).join('');

            const contentContainer = document.getElementById('contentListUI');
            contentContainer.innerHTML = appState.videos.map(v => `
                <div class="flex items-center gap-4 bg-white/5 p-3 rounded-2xl border border-gray-800">
                    <div class="flex-1">
                        <p class="font-bold text-cyan-400 text-sm uppercase truncate">${v.series}</p>
                        <p class="text-[10px] text-gray-500 font-bold">EPISODE: ${v.episode}</p>
                    </div>
                    <button onclick="removeEpisode('${v.id}')" class="bg-red-500/10 text-red-500 text-xs font-bold px-3 py-1 rounded-lg hover:bg-red-500 hover:text-white transition">Delete</button>
                </div>
            `).join('');
        }

        // --- SIGNED UPLOAD (NO PRESET) ---
        function startSimpleUpload() {
            const series = document.getElementById('seriesTitle').value;
            const ep = document.getElementById('episodeNo').value;
            const activeAPI = appState.apis.find(a => a.id === appState.active_api_id);

            if(!series || !ep) return alert("Series name and episode number required!");
            if(!activeAPI) return alert("Please add and select an Active API first!");

            const myWidget = cloudinary.createUploadWidget({
                cloudName: activeAPI.cloud,
                apiKey: activeAPI.key,
                // এটি সিগনেচার মেথড, যা প্রিসেট ছাড়াই আপলোড করতে সাহায্য করে
                uploadSignature: (callback, params_to_sign) => {
                    fetch('/api/generate_signature', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ params: params_to_sign })
                    })
                    .then(r => r.json())
                    .then(data => {
                        if(data.error) alert(data.error);
                        else callback(data.signature);
                    });
                }
            }, async (error, result) => {
                if (!error && result && result.event === "success") {
                    await fetch('/api/save_episode_meta', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ url: result.info.secure_url, series, ep })
                    });
                    alert("Episode Uploaded Successfully!");
                    fetchSystemData();
                }
            });
            myWidget.open();
        }

        // --- Core Functions ---
        async function saveApiConfig() {
            const cloud = document.getElementById('api_cloud').value;
            const key = document.getElementById('api_key').value;
            const secret = document.getElementById('api_secret').value;
            if(!cloud || !key || !secret) return alert("All fields are mandatory!");
            await fetch('/api/add_api_config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ cloud, key, secret })
            });
            fetchSystemData();
            document.getElementById('api_cloud').value = '';
            document.getElementById('api_key').value = '';
            document.getElementById('api_secret').value = '';
        }

        async function switchActiveApi(id) {
            await fetch('/api/set_active_api', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
            fetchSystemData();
        }

        async function removeApiConfig(id) {
            if(!confirm("Delete this API configuration?")) return;
            await fetch('/api/delete_api_config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
            fetchSystemData();
        }

        async function removeEpisode(id) {
            if(!confirm("Delete this episode?")) return;
            await fetch('/api/delete_episode', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
            fetchSystemData();
        }

        async function checkAuthAndOpenAdmin() {
            const res = await fetch('/api/auth_check');
            const data = await res.json();
            if(data.is_auth) {
                document.getElementById('adminPanel').classList.remove('hidden');
                renderAdminDashboard();
            } else {
                document.getElementById('loginModal').classList.remove('hidden');
            }
        }

        async function submitLogin() {
            const pass = document.getElementById('adminPassInput').value;
            const res = await fetch('/api/admin_login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ pass })
            });
            if((await res.json()).success) location.reload();
            else alert("Incorrect Password!");
        }

        function closeModals() {
            document.getElementById('loginModal').classList.add('hidden');
        }

        fetchSystemData();
    </script>
</body>
</html>
"""

# ================= Backend API Logic =================

@app.route('/')
def main_index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/generate_signature', methods=['POST'])
def generate_signature():
    """Signed Upload এর জন্য API Secret ব্যবহার করে Signature তৈরি"""
    if not session.get('admin_session'): return jsonify({"error": "unauthorized"}), 401
    
    active_api = api_col.find_one({"is_active": True})
    if not active_api: return jsonify({"error": "No active API selected!"}), 400

    params = request.json.get('params', {})
    # Cloudinary নিয়ম: প্যারামিটারগুলোকে alphabetical অর্ডারে সাজিয়ে secret শেষে যোগ করতে হয়
    sorted_params = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    to_sign = f"{sorted_params}{active_api['secret']}"
    
    signature = hashlib.sha1(to_sign.encode('utf-8')).hexdigest()
    return jsonify({"signature": signature})

@app.route('/api/admin_login', methods=['POST'])
def admin_login():
    if request.json.get('pass') == ADMIN_PASS:
        session['admin_session'] = True
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/auth_check')
def auth_check():
    return jsonify({"is_auth": session.get('admin_session', False)})

@app.route('/api/get_full_data')
def get_full_data():
    all_apis = list(api_col.find({}, {'_id': 0}))
    all_videos = list(video_col.find({}, {'_id': 0}).sort('_id', -1))
    active_entry = api_col.find_one({"is_active": True})
    active_id = active_entry['id'] if active_entry else (all_apis[0]['id'] if all_apis else None)
    return jsonify({"apis": all_apis, "videos": all_videos, "active_api_id": active_id})

@app.route('/api/add_api_config', methods=['POST'])
def add_api_config():
    if not session.get('admin_session'): return jsonify({"error": "unauthorized"}), 401
    data = request.json
    api_col.insert_one({
        "id": str(uuid.uuid4())[:8],
        "cloud": data['cloud'],
        "key": data['key'],
        "secret": data['secret'],
        "is_active": False
    })
    return jsonify({"success": True})

@app.route('/api/delete_api_config', methods=['POST'])
def delete_api_config():
    if not session.get('admin_session'): return jsonify({"error": "unauthorized"}), 401
    api_col.delete_one({"id": request.json['id']})
    return jsonify({"success": True})

@app.route('/api/set_active_api', methods=['POST'])
def set_active_api():
    if not session.get('admin_session'): return jsonify({"error": "unauthorized"}), 401
    api_col.update_many({}, {"$set": {"is_active": False}})
    api_col.update_one({"id": request.json['id']}, {"$set": {"is_active": True}})
    return jsonify({"success": True})

@app.route('/api/save_episode_meta', methods=['POST'])
def save_episode_meta():
    if not session.get('admin_session'): return jsonify({"error": "unauthorized"}), 401
    data = request.json
    video_col.insert_one({
        "id": str(uuid.uuid4())[:8],
        "url": data['url'],
        "series": data['series'],
        "episode": data['ep'],
        "likes": 0
    })
    return jsonify({"success": True})

@app.route('/api/delete_episode', methods=['POST'])
def delete_episode():
    if not session.get('admin_session'): return jsonify({"error": "unauthorized"}), 401
    video_col.delete_one({"id": request.json['id']})
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
