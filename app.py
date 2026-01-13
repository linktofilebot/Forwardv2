from flask import Flask, render_template_string, request, jsonify, session
from pymongo import MongoClient
import uuid
import secrets
import time
import hashlib
from datetime import datetime

# ================= 1. Configuration & DB Connection =================
app = Flask(__name__)
app.secret_key = secrets.token_hex(24)

# আপনার MongoDB Atlas URL
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" 
ADMIN_PASS = "admin786"

try:
    client = MongoClient(MONGO_URI)
    db = client['CloudTok_Ultimate_V3']
    api_col = db['apis']      # API স্টোরেজ
    video_col = db['videos']  # ভিডিও এবং ইপিসোড স্টোরেজ
    print("✓ MongoDB Connected Successfully")
except Exception as e:
    print(f"✗ MongoDB Connection Error: {e}")

# ================= 2. Unified Frontend Template (HTML/CSS/JS) =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudTok Pro - Full System</title>
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
        .comment-box { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 5px 10px; margin-bottom: 5px; font-size: 12px; }
    </style>
</head>
<body>

    <!-- Header Navigation -->
    <nav class="fixed top-0 w-full z-50 flex justify-between p-5 bg-gradient-to-b from-black to-transparent">
        <h1 class="text-2xl font-black italic tracking-tighter text-cyan-400 uppercase">Cloud<span class="text-white">Tok</span></h1>
        <button onclick="checkAuthAndOpenAdmin()" class="bg-white/10 backdrop-blur-md px-5 py-2 rounded-full text-[10px] font-bold border border-white/20 hover:bg-cyan-500 transition">ADMIN PANEL</button>
    </nav>

    <!-- Main Video Feed -->
    <div id="videoFeed" class="feed-container scrollbar-hide"></div>

    <!-- Login Modal -->
    <div id="loginModal" class="hidden fixed inset-0 z-[100] bg-black/95 flex items-center justify-center p-6">
        <div class="glass-ui p-8 rounded-3xl w-full max-w-sm text-center">
            <h2 class="text-2xl font-black mb-6 text-cyan-400 uppercase italic">Admin Access</h2>
            <input id="adminPassInput" type="password" placeholder="Password" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-6 text-center outline-none">
            <button onclick="submitLogin()" class="w-full btn-gradient p-4 rounded-xl font-bold uppercase">Unlock</button>
            <button onclick="closeModals()" class="mt-4 text-gray-500 text-xs">Cancel</button>
        </div>
    </div>

    <!-- Admin Dashboard Panel -->
    <div id="adminPanel" class="hidden fixed inset-0 z-[80] bg-black p-4 md:p-8 overflow-y-auto">
        <div class="max-w-6xl mx-auto pb-20">
            <div class="flex justify-between items-center mb-10 border-b border-gray-800 pb-5">
                <h2 class="text-3xl font-black text-cyan-500 uppercase italic">Control Center</h2>
                <div class="flex gap-4">
                    <button onclick="logout()" class="text-red-500 text-xs font-bold uppercase">Logout</button>
                    <button onclick="location.reload()" class="text-white text-3xl">✕</button>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-10">
                <!-- Left: API & Upload -->
                <div class="space-y-8">
                    <div class="glass-ui p-6 rounded-3xl border border-gray-800">
                        <h3 class="text-cyan-400 font-bold mb-4 uppercase text-xs">1. Cloudinary API (No Preset)</h3>
                        <div class="grid gap-3 mb-4">
                            <input id="api_cloud" placeholder="Cloud Name" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none">
                            <input id="api_key" placeholder="API Key" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none">
                            <input id="api_secret" placeholder="API Secret" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none">
                        </div>
                        <button onclick="saveApiConfig()" class="w-full bg-cyan-700 p-3 rounded-xl font-bold text-xs uppercase">Add Account</button>
                        <div id="apiListContainer" class="mt-6 space-y-2"></div>
                    </div>

                    <div class="glass-ui p-6 rounded-3xl border border-cyan-500/20">
                        <h3 class="text-cyan-400 font-bold mb-4 uppercase text-xs">2. Upload Episode</h3>
                        <div class="flex gap-3 mb-6">
                            <input id="seriesTitle" placeholder="Movie Name" class="w-2/3 bg-black p-4 rounded-xl border border-gray-800">
                            <input id="episodeNo" type="number" placeholder="Ep." class="w-1/3 bg-black p-4 rounded-xl border border-gray-800">
                        </div>
                        <button onclick="startSimpleUpload()" class="w-full btn-gradient p-5 rounded-2xl font-black text-xl shadow-lg transition active:scale-95">🚀 SELECT & UPLOAD</button>
                    </div>
                </div>

                <!-- Right: Content Management -->
                <div class="glass-ui p-6 rounded-3xl border border-gray-800">
                    <h3 class="text-gray-500 font-bold mb-4 uppercase text-xs">3. Content Manager</h3>
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
                feed.innerHTML = `<div class="h-screen flex items-center justify-center opacity-30 text-xs uppercase tracking-widest">No Content Found</div>`;
                return;
            }
            feed.innerHTML = appState.videos.map(v => `
                <div class="video-card">
                    <video src="${v.url}" loop autoplay muted playsinline onclick="this.paused?this.play():this.pause()"></video>
                    
                    <!-- Side Actions -->
                    <div class="absolute right-5 bottom-32 flex flex-col gap-6 text-center z-10">
                        <div onclick="handleInteraction('${v.id}', 'like')" class="cursor-pointer group">
                            <div class="glass-ui p-4 rounded-full group-active:scale-125 transition">❤️</div>
                            <span class="text-xs font-bold">${v.likes || 0}</span>
                        </div>
                        <div onclick="showComments('${v.id}')" class="cursor-pointer">
                            <div class="glass-ui p-4 rounded-full">💬</div>
                            <span class="text-xs font-bold">${(v.comments || []).length}</span>
                        </div>
                    </div>

                    <!-- Video Info -->
                    <div class="absolute bottom-12 left-6 right-20 z-10">
                        <h3 class="text-cyan-400 font-black text-4xl italic uppercase tracking-tighter">${v.series}</h3>
                        <p class="text-white font-bold text-xl opacity-90">Episode: ${v.episode}</p>
                    </div>
                </div>
            `).join('');
        }

        function renderAdminDashboard() {
            const apiContainer = document.getElementById('apiListContainer');
            apiContainer.innerHTML = appState.apis.map(api => `
                <div onclick="switchActiveApi('${api.id}')" class="flex justify-between items-center p-3 rounded-xl border cursor-pointer transition ${api.id === appState.active_api_id ? 'active-api-border' : 'border-gray-800'}">
                    <span class="text-xs font-bold text-white">${api.cloud}</span>
                    <button onclick="removeApiConfig('${api.id}')" class="text-red-500 font-bold px-2">✕</button>
                </div>
            `).join('');

            const contentContainer = document.getElementById('contentListUI');
            contentContainer.innerHTML = appState.videos.map(v => `
                <div class="flex items-center gap-4 bg-white/5 p-3 rounded-2xl border border-gray-800">
                    <div class="flex-1 overflow-hidden">
                        <p class="font-bold text-cyan-400 text-xs uppercase truncate">${v.series} (EP-${v.episode})</p>
                        <p class="text-[9px] text-gray-500">ID: ${v.id}</p>
                    </div>
                    <button onclick="removeEpisode('${v.id}')" class="text-red-500 text-[10px] font-bold bg-red-500/10 px-3 py-1 rounded-lg">DELETE</button>
                </div>
            `).join('');
        }

        // --- SIGNED UPLOAD WITHOUT PRESET ---
        function startSimpleUpload() {
            const series = document.getElementById('seriesTitle').value;
            const ep = document.getElementById('episodeNo').value;
            const activeAPI = appState.apis.find(a => a.id === appState.active_api_id);

            if(!series || !ep) return alert("Series & Episode required!");
            if(!activeAPI) return alert("Select an Active API first!");

            const myWidget = cloudinary.createUploadWidget({
                cloudName: activeAPI.cloud,
                apiKey: activeAPI.key,
                uploadSignature: (callback, params_to_sign) => {
                    fetch('/api/generate_signature', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ params: params_to_sign })
                    })
                    .then(r => r.json())
                    .then(data => callback(data.signature));
                }
            }, async (error, result) => {
                if (!error && result && result.event === "success") {
                    await fetch('/api/save_episode_meta', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ url: result.info.secure_url, series, ep })
                    });
                    fetchSystemData();
                    alert("Upload Complete!");
                }
            });
            myWidget.open();
        }

        // --- Interactions ---
        async function handleInteraction(id, type) {
            let comment = "";
            if(type === 'comment') {
                comment = prompt("Enter your comment:");
                if(!comment) return;
            }
            await fetch('/api/video_interaction', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, type, comment })
            });
            fetchSystemData();
        }

        function showComments(id) {
            const video = appState.videos.find(v => v.id === id);
            const comments = video.comments || [];
            const msg = comments.length > 0 ? comments.join('\\n') : "No comments yet.";
            alert("Comments:\\n" + msg);
            handleInteraction(id, 'comment'); // Prompt to add new
        }

        // --- Admin Actions ---
        async function saveApiConfig() {
            const cloud = document.getElementById('api_cloud').value;
            const key = document.getElementById('api_key').value;
            const secret = document.getElementById('api_secret').value;
            if(!cloud || !key || !secret) return alert("All fields required!");
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
            if(confirm("Delete API?")) {
                await fetch('/api/delete_api_config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
                fetchSystemData();
            }
        }

        async function removeEpisode(id) {
            if(confirm("Delete video?")) {
                await fetch('/api/delete_episode', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
                fetchSystemData();
            }
        }

        async function checkAuthAndOpenAdmin() {
            const res = await fetch('/api/auth_check');
            const data = await res.json();
            if(data.is_auth) document.getElementById('adminPanel').classList.remove('hidden');
            else document.getElementById('loginModal').classList.remove('hidden');
            fetchSystemData();
        }

        async function submitLogin() {
            const pass = document.getElementById('adminPassInput').value;
            const res = await fetch('/api/admin_login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ pass }) });
            if((await res.json()).success) { location.reload(); } else { alert("Wrong Password!"); }
        }

        async function logout() {
            await fetch('/api/admin_logout');
            location.reload();
        }

        function closeModals() { document.getElementById('loginModal').classList.add('hidden'); }

        fetchSystemData();
    </script>
</body>
</html>
"""

# ================= 3. Backend Routes & Logic =================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/generate_signature', methods=['POST'])
def generate_signature():
    """ Signed Upload এর জন্য ব্যাকএন্ড সিগনেচার মেকার (No Preset Needed) """
    if not session.get('admin_session'): return jsonify({"error": "unauthorized"}), 401
    
    active_api = api_col.find_one({"is_active": True})
    if not active_api: return jsonify({"error": "No active API selected"}), 400

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

@app.route('/api/admin_logout')
def admin_logout():
    session.pop('admin_session', None)
    return jsonify({"success": True})

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

@app.route('/api/set_active_api', methods=['POST'])
def set_active_api():
    if not session.get('admin_session'): return jsonify({"error": "unauthorized"}), 401
    target_id = request.json['id']
    api_col.update_many({}, {"$set": {"is_active": False}})
    api_col.update_one({"id": target_id}, {"$set": {"is_active": True}})
    return jsonify({"success": True})

@app.route('/api/delete_api_config', methods=['POST'])
def delete_api_config():
    if not session.get('admin_session'): return jsonify({"error": "unauthorized"}), 401
    api_col.delete_one({"id": request.json['id']})
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
        "likes": 0,
        "comments": [],
        "created_at": datetime.now()
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
    if data['type'] == 'like':
        video_col.update_one({"id": data['id']}, {"$inc": {"likes": 1}})
    elif data['type'] == 'comment' and data.get('comment'):
        video_col.update_one({"id": data['id']}, {"$push": {"comments": data['comment']}})
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
