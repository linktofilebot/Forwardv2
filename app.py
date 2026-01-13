from flask import Flask, render_template_string, request, jsonify, session
from pymongo import MongoClient
import os
import uuid
import secrets
import time
import hashlib

app = Flask(__name__)
app.secret_key = secrets.token_hex(24)

# ================= MongoDB Configuration =================
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" 

try:
    client = MongoClient(MONGO_URI)
    db = client['CloudTok_Final_DB']
    api_col = db['apis']     
    video_col = db['videos'] 
    print("✓ MongoDB Connected Successfully")
except Exception as e:
    print(f"✗ MongoDB Connection Error: {e}")

ADMIN_PASS = "admin786"

# ================= HTML Template =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudTok Ultimate Pro</title>
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

    <nav class="fixed top-0 w-full z-50 flex justify-between p-5 bg-gradient-to-b from-black to-transparent">
        <h1 class="text-2xl font-black italic tracking-tighter text-cyan-400 uppercase">Cloud<span class="text-white">Tok</span></h1>
        <button onclick="checkAuthAndOpenAdmin()" class="bg-white/10 backdrop-blur-md px-6 py-2 rounded-full text-xs font-bold border border-white/20 hover:bg-cyan-500 transition">ADMIN DASHBOARD</button>
    </nav>

    <div id="videoFeed" class="feed-container scrollbar-hide"></div>

    <!-- Login Modal -->
    <div id="loginModal" class="hidden fixed inset-0 z-[100] bg-black/95 flex items-center justify-center p-6">
        <div class="glass-ui p-8 rounded-3xl w-full max-w-sm text-center">
            <h2 class="text-2xl font-black mb-6 text-cyan-400 uppercase italic">Admin Access</h2>
            <input id="adminPassInput" type="password" placeholder="Password" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-6 text-center outline-none">
            <button onclick="submitLogin()" class="w-full btn-gradient p-4 rounded-xl font-bold uppercase">Unlock</button>
            <button onclick="closeModals()" class="mt-4 text-gray-500 text-xs">Close</button>
        </div>
    </div>

    <!-- Admin Panel -->
    <div id="adminPanel" class="hidden fixed inset-0 z-[80] bg-black p-4 md:p-8 overflow-y-auto">
        <div class="max-w-6xl mx-auto pb-20">
            <div class="flex justify-between items-center mb-10 border-b border-gray-800 pb-5">
                <h2 class="text-3xl font-black text-cyan-500 uppercase italic">Control Center</h2>
                <button onclick="location.reload()" class="text-white text-3xl">✕</button>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-10">
                <div class="space-y-8">
                    <!-- API Settings -->
                    <div class="glass-ui p-6 rounded-3xl border border-gray-800">
                        <h3 class="text-cyan-400 font-bold mb-4 uppercase text-xs">1. Cloudinary API Setup (No Preset)</h3>
                        <div class="grid gap-4 mb-4">
                            <input id="api_cloud" placeholder="Cloud Name" class="bg-black p-3 rounded-xl border border-gray-800 text-sm">
                            <input id="api_key" placeholder="API Key" class="bg-black p-3 rounded-xl border border-gray-800 text-sm">
                            <input id="api_secret" placeholder="API Secret" class="bg-black p-3 rounded-xl border border-gray-800 text-sm">
                        </div>
                        <button onclick="saveApiConfig()" class="w-full bg-cyan-700 p-3 rounded-xl font-bold text-xs uppercase">Connect Cloud</button>
                        <div id="apiListContainer" class="mt-6 space-y-3"></div>
                    </div>

                    <!-- Upload Section -->
                    <div class="glass-ui p-6 rounded-3xl border border-cyan-500/20">
                        <h3 class="text-cyan-400 font-bold mb-4 uppercase text-xs">2. Quick Movie Upload</h3>
                        <div class="flex gap-3 mb-6">
                            <input id="seriesTitle" placeholder="Movie Name" class="w-2/3 bg-black p-4 rounded-xl border border-gray-800">
                            <input id="episodeNo" type="number" placeholder="Ep." class="w-1/3 bg-black p-4 rounded-xl border border-gray-800">
                        </div>
                        <button onclick="startSimpleUpload()" class="w-full btn-gradient p-5 rounded-2xl font-black text-xl shadow-lg">🚀 START UPLOAD</button>
                    </div>
                </div>

                <div class="glass-ui p-6 rounded-3xl border border-gray-800">
                    <h3 class="text-gray-500 font-bold mb-4 uppercase text-xs">3. Manage Episodes</h3>
                    <div id="contentListUI" class="space-y-4 max-h-[600px] overflow-y-auto scrollbar-hide"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let appState = { apis: [], videos: [], active_api_id: null };

        async function fetchSystemData() {
            const res = await fetch('/api/get_full_data');
            appState = await res.json();
            renderVideoFeed();
            if(!document.getElementById('adminPanel').classList.contains('hidden')) renderAdminDashboard();
        }

        function renderVideoFeed() {
            const feed = document.getElementById('videoFeed');
            if(appState.videos.length === 0) {
                feed.innerHTML = `<div class="h-screen flex items-center justify-center text-gray-500">No Videos Found</div>`;
                return;
            }
            feed.innerHTML = appState.videos.map(v => `
                <div class="video-card">
                    <video src="${v.url}" loop autoplay muted playsinline onclick="this.paused?this.play():this.pause()"></video>
                    <div class="absolute right-5 bottom-32 flex flex-col gap-6 text-center z-10">
                        <div onclick="handleInteraction('${v.id}', 'like')" class="cursor-pointer">
                            <div class="glass-ui p-4 rounded-full">❤️</div>
                            <span class="text-xs font-bold">${v.likes || 0}</span>
                        </div>
                    </div>
                    <div class="absolute bottom-12 left-6 right-20 z-10">
                        <h3 class="text-cyan-400 font-black text-4xl italic uppercase">${v.series}</h3>
                        <p class="text-white font-bold text-xl">Episode: ${v.episode}</p>
                    </div>
                </div>
            `).join('');
        }

        function renderAdminDashboard() {
            const apiContainer = document.getElementById('apiListContainer');
            apiContainer.innerHTML = appState.apis.map(api => `
                <div class="flex justify-between items-center p-4 rounded-2xl border ${api.id === appState.active_api_id ? 'active-api-border' : 'border-gray-800'}">
                    <div onclick="switchActiveApi('${api.id}')" class="cursor-pointer flex-1">
                        <span class="text-sm font-bold text-white">${api.cloud}</span>
                    </div>
                    <button onclick="removeApiConfig('${api.id}')" class="text-red-500 font-bold ml-4">✕</button>
                </div>
            `).join('');

            const contentContainer = document.getElementById('contentListUI');
            contentContainer.innerHTML = appState.videos.map(v => `
                <div class="flex items-center gap-4 bg-white/5 p-3 rounded-2xl border border-gray-800">
                    <div class="flex-1">
                        <p class="font-bold text-cyan-400 text-sm uppercase">${v.series}</p>
                        <p class="text-xs text-gray-400">Episode: ${v.episode}</p>
                    </div>
                    <button onclick="removeEpisode('${v.id}')" class="text-red-500 px-3 py-1 bg-red-500/10 rounded-lg">Delete</button>
                </div>
            `).join('');
        }

        async function saveApiConfig() {
            const cloud = document.getElementById('api_cloud').value;
            const key = document.getElementById('api_key').value;
            const secret = document.getElementById('api_secret').value;
            if(!cloud || !key || !secret) return alert("All fields are required!");
            
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
            await fetch('/api/set_active_api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id })
            });
            fetchSystemData();
        }

        async function removeApiConfig(id) {
            if(!confirm("Delete this API?")) return;
            await fetch('/api/delete_api_config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id })
            });
            fetchSystemData();
        }

        async function startSimpleUpload() {
            const series = document.getElementById('seriesTitle').value;
            const ep = document.getElementById('episodeNo').value;
            const activeAPI = appState.apis.find(a => a.id === appState.active_api_id);

            if(!series || !ep) return alert("Movie Name and Episode No required!");
            if(!activeAPI) return alert("Select an Active Cloud API first!");

            const sigRes = await fetch('/api/generate_signature');
            const sigData = await sigRes.json();

            const myWidget = cloudinary.createUploadWidget({
                cloudName: activeAPI.cloud,
                apiKey: activeAPI.key,
                uploadSignatureTimestamp: sigData.timestamp,
                uploadSignature: sigData.signature,
                resourceType: 'video',
                folder: 'cloudtok_videos'
            }, async (error, result) => {
                if (!error && result && result.event === "success") {
                    await fetch('/api/save_episode_meta', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ url: result.info.secure_url, series, ep })
                    });
                    fetchSystemData();
                }
            });
            myWidget.open();
        }

        async function handleInteraction(id, type) {
            await fetch('/api/video_interaction', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, type })
            });
            fetchSystemData();
        }

        async function removeEpisode(id) {
            if(!confirm("Delete video?")) return;
            await fetch('/api/delete_episode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id })
            });
            fetchSystemData();
        }

        async function checkAuthAndOpenAdmin() {
            const res = await fetch('/api/auth_check');
            const data = await res.json();
            if(data.is_auth) document.getElementById('adminPanel').classList.remove('hidden');
            else document.getElementById('loginModal').classList.remove('hidden');
        }

        async function submitLogin() {
            const pass = document.getElementById('adminPassInput').value;
            const res = await fetch('/api/admin_login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ pass })
            });
            const data = await res.json();
            if(data.success) { location.reload(); } else { alert("Wrong Password!"); }
        }

        function closeModals() { document.getElementById('loginModal').classList.add('hidden'); }

        fetchSystemData();
    </script>
</body>
</html>
"""

# ================= Backend Logic =================

@app.route('/')
def main_index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/generate_signature')
def generate_signature():
    """Preset ছাড়াই Signed Upload এর জন্য সার্ভার থেকে Signature তৈরি"""
    if not session.get('admin_session'): return jsonify({"error": "unauthorized"}), 401
    active_api = api_col.find_one({"is_active": True})
    if not active_api: return jsonify({"error": "No active API"}), 400

    timestamp = int(time.time())
    # Cloudinary parameter sorting (alphabetical)
    param_str = f"folder=cloudtok_videos&timestamp={timestamp}{active_api['secret']}"
    signature = hashlib.sha1(param_str.encode('utf-8')).hexdigest()
    
    return jsonify({"signature": signature, "timestamp": timestamp})

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

@app.route('/api/video_interaction', methods=['POST'])
def video_interaction():
    data = request.json
    video_col.update_one({"id": data['id']}, {"$inc": {"likes": 1}})
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
