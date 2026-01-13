from flask import Flask, render_template_string, request, jsonify, session
from pymongo import MongoClient
import os
import uuid
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ================= MongoDB Configuration =================
# আপনার MongoDB Atlas থেকে পাওয়া Connection URL এখানে দিন
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" 

try:
    client = MongoClient(MONGO_URI)
    db = client['CloudTokDB']      # ডাটাবেস নাম
    api_col = db['cloudinary_apis'] # API সংরক্ষণের টেবিল
    video_col = db['episodes']     # ভিডিও সংরক্ষণের টেবিল
    print("✓ MongoDB Connected!")
except Exception as e:
    print(f"✗ MongoDB Connection Error: {e}")

# এডমিন পাসওয়ার্ড (এটি পরিবর্তন করতে পারেন)
ADMIN_PASS = "admin786"

# ================= Frontend Template (HTML/JS/CSS) =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudTok Pro - Unlimited Episodes</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://upload-widget.cloudinary.com/global/all.js"></script>
    <style>
        body { background-color: #000; color: #fff; font-family: 'Inter', sans-serif; overflow: hidden; }
        .feed-container { height: 100vh; scroll-snap-type: y mandatory; overflow-y: scroll; scrollbar-width: none; }
        .video-section { height: 100vh; scroll-snap-align: start; position: relative; background: #000; display: flex; align-items: center; justify-content: center; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
        video { height: 100%; width: 100%; object-fit: cover; }
        .glass-panel { background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .progress-bar { transition: width 0.3s ease; }
    </style>
</head>
<body>

    <!-- Top Navigation -->
    <nav class="fixed top-0 w-full z-50 flex justify-between p-5 bg-gradient-to-b from-black/80 to-transparent">
        <h1 class="text-2xl font-black italic tracking-tighter text-cyan-500">CLOUD<span class="text-white">TOK</span></h1>
        <button onclick="openAdmin()" class="bg-white/10 backdrop-blur-md px-5 py-2 rounded-full text-xs font-bold border border-white/20 hover:bg-cyan-500 transition">ADMIN DASHBOARD</button>
    </nav>

    <!-- UI: Vertical Video Feed -->
    <div id="videoFeed" class="feed-container scrollbar-hide">
        <!-- Videos will be loaded via JS -->
    </div>

    <!-- UI: Admin Login Modal -->
    <div id="loginModal" class="hidden fixed inset-0 z-[100] bg-black/90 flex items-center justify-center p-6">
        <div class="glass-panel p-8 rounded-3xl w-full max-w-sm text-center">
            <h2 class="text-2xl font-bold mb-6 text-cyan-400">Admin Security</h2>
            <input id="passInput" type="password" placeholder="Enter Password" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-4 outline-none focus:border-cyan-500">
            <button onclick="handleLogin()" class="w-full bg-cyan-600 p-4 rounded-xl font-bold uppercase tracking-widest">Login</button>
            <button onclick="closeModals()" class="mt-4 text-gray-500 text-sm">Close</button>
        </div>
    </div>

    <!-- UI: Full Admin Control Panel -->
    <div id="adminPanel" class="hidden fixed inset-0 z-[80] bg-black p-6 overflow-y-auto">
        <div class="max-w-5xl mx-auto pb-20">
            <div class="flex justify-between items-center mb-10 border-b border-gray-800 pb-5">
                <h2 class="text-3xl font-black text-cyan-500 uppercase">Control Center</h2>
                <div class="flex gap-4">
                    <button onclick="handleLogout()" class="text-red-500 font-bold text-xs uppercase underline">Logout</button>
                    <button onclick="closeModals()" class="text-white text-2xl">✕</button>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <!-- Left: API & Upload -->
                <div class="space-y-8">
                    <div class="glass-panel p-6 rounded-3xl">
                        <h3 class="text-cyan-400 font-bold mb-4 uppercase text-xs tracking-widest">1. API Manager (Unlimited)</h3>
                        <div class="grid grid-cols-2 gap-3 mb-4">
                            <input id="cloudName" placeholder="Cloud Name" class="bg-black p-3 rounded-xl border border-gray-800 text-sm">
                            <input id="presetName" placeholder="Upload Preset" class="bg-black p-3 rounded-xl border border-gray-800 text-sm">
                        </div>
                        <button onclick="addAPI()" class="w-full bg-cyan-600 p-3 rounded-xl font-bold text-sm">Add New API Connection</button>
                        <div id="apiList" class="mt-5 space-y-2 max-h-48 overflow-y-auto scrollbar-hide"></div>
                    </div>

                    <div class="glass-panel p-6 rounded-3xl">
                        <h3 class="text-cyan-400 font-bold mb-4 uppercase text-xs tracking-widest">2. Episode Uploader</h3>
                        <div class="flex gap-2 mb-4">
                            <input id="seriesTitle" placeholder="Series Name" class="w-2/3 bg-black p-4 rounded-xl border border-gray-800">
                            <input id="epNumber" type="number" placeholder="Ep." class="w-1/3 bg-black p-4 rounded-xl border border-gray-800">
                        </div>
                        
                        <!-- Real-time Progress -->
                        <div id="progBox" class="hidden mb-4 p-4 rounded-2xl bg-cyan-950 border border-cyan-500/30">
                            <div class="flex justify-between mb-2">
                                <span id="progText" class="text-cyan-400 font-bold text-xs">Uploading: 0%</span>
                            </div>
                            <div class="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                                <div id="progBar" class="progress-bar bg-cyan-500 h-full w-0 shadow-[0_0_10px_#06b6d4]"></div>
                            </div>
                        </div>

                        <button onclick="uploadVideo()" class="w-full bg-white text-black p-5 rounded-2xl font-black text-xl hover:bg-cyan-400 transition">🚀 START UPLOAD</button>
                    </div>
                </div>

                <!-- Right: Content Manager -->
                <div class="glass-panel p-6 rounded-3xl">
                    <h3 class="text-gray-400 font-bold mb-4 uppercase text-xs tracking-widest">3. Manage Content (Edit/Delete)</h3>
                    <div id="manageList" class="space-y-4 max-h-[600px] overflow-y-auto pr-2 scrollbar-hide"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let appData = { apis: [], videos: [], active_api_id: null };

        // Initial Load
        async function loadContent() {
            const res = await fetch('/api/data');
            appData = await res.json();
            renderFeed();
        }

        // Authentication
        async function openAdmin() {
            const res = await fetch('/api/check_auth');
            const status = await res.json();
            if(status.authorized) {
                document.getElementById('adminPanel').classList.remove('hidden');
                renderAdmin();
            } else {
                document.getElementById('loginModal').classList.remove('hidden');
            }
        }

        async function handleLogin() {
            const pass = document.getElementById('passInput').value;
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ pass })
            });
            const data = await res.json();
            if(data.success) location.reload(); else alert("Access Denied!");
        }

        async function handleLogout() {
            await fetch('/api/logout');
            location.reload();
        }

        // Render Functions
        function renderFeed() {
            const feed = document.getElementById('videoFeed');
            if(appData.videos.length === 0) {
                feed.innerHTML = `<div class="h-screen flex items-center justify-center text-gray-600 italic">No Episodes Uploaded Yet.</div>`;
                return;
            }
            feed.innerHTML = appData.videos.map(v => `
                <div class="video-section">
                    <video src="${v.url}" loop autoplay muted playsinline onclick="this.paused?this.play():this.pause()"></video>
                    <div class="absolute right-5 bottom-32 flex flex-col gap-6 text-center z-10">
                        <div onclick="interact('${v.id}', 'like')" class="cursor-pointer group">
                            <div class="glass-panel p-4 rounded-full mb-1 group-active:scale-150 transition">❤️</div>
                            <span class="text-xs font-bold">${v.likes}</span>
                        </div>
                        <div onclick="addComment('${v.id}')" class="cursor-pointer">
                            <div class="glass-panel p-4 rounded-full mb-1">💬</div>
                            <span class="text-xs font-bold">${v.comments.length}</span>
                        </div>
                        <div class="cursor-pointer">
                            <div class="glass-panel p-4 rounded-full mb-1">🔗</div>
                            <span class="text-xs font-bold">Share</span>
                        </div>
                    </div>
                    <div class="absolute bottom-12 left-6 right-20 z-10 pointer-events-none">
                        <h3 class="text-cyan-400 font-black text-3xl italic uppercase drop-shadow-2xl">${v.series}</h3>
                        <p class="text-white font-bold text-lg">Episode: ${v.episode}</p>
                    </div>
                </div>
            `).join('');
        }

        function renderAdmin() {
            const apiList = document.getElementById('apiList');
            apiList.innerHTML = appData.apis.map(api => `
                <div class="flex items-center justify-between p-4 rounded-2xl border ${api.id === appData.active_api_id ? 'border-cyan-500 bg-cyan-900/20' : 'border-gray-800 bg-black'}">
                    <span onclick="setActiveAPI('${api.id}')" class="cursor-pointer text-sm font-bold flex-1">${api.cloudName}</span>
                    <button onclick="delAPI('${api.id}')" class="text-red-500 text-[10px] font-bold uppercase ml-4">Remove</button>
                </div>
            `).join('');

            const manageList = document.getElementById('manageList');
            manageList.innerHTML = appData.videos.map(v => `
                <div class="flex items-center gap-4 bg-gray-900/50 p-3 rounded-2xl border border-gray-800">
                    <video src="${v.url}" class="w-16 h-20 object-cover rounded-xl bg-black"></video>
                    <div class="flex-1">
                        <p class="font-bold text-cyan-400 text-sm">${v.series}</p>
                        <p class="text-[10px] text-gray-500 uppercase">Episode ${v.episode}</p>
                    </div>
                    <button onclick="delVideo('${v.id}')" class="bg-red-500/20 text-red-500 p-3 rounded-xl hover:bg-red-500 hover:text-white transition">✕</button>
                </div>
            `).join('');
        }

        // Logic Functions
        async function addAPI() {
            const cloud = document.getElementById('cloudName').value;
            const preset = document.getElementById('presetName').value;
            await fetch('/api/api_add', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ cloud, preset }) });
            location.reload();
        }

        async function delAPI(id) {
            if(!confirm("Delete this API?")) return;
            await fetch('/api/api_del', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
            location.reload();
        }

        async function setActiveAPI(id) {
            await fetch('/api/api_set', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
            location.reload();
        }

        function uploadVideo() {
            const active = appData.apis.find(a => a.id === appData.active_api_id);
            const series = document.getElementById('seriesTitle').value;
            const ep = document.getElementById('epNumber').value;
            
            if(!active) return alert("Please select an active API first!");
            if(!series || !ep) return alert("Fill series info!");

            const widget = cloudinary.createUploadWidget({
                cloudName: active.cloudName, uploadPreset: active.preset, resourceType: 'video'
            }, async (err, result) => {
                const box = document.getElementById('progBox');
                if (result.event === "upload-progress") {
                    box.classList.remove('hidden');
                    let p = Math.round(result.info.progress);
                    document.getElementById('progText').innerText = `Uploading Episode: ${p}%`;
                    document.getElementById('progBar').style.width = `${p}%`;
                }
                if (!err && result.event === "success") {
                    await fetch('/api/vid_save', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ url: result.info.secure_url, series, ep })
                    });
                    location.reload();
                }
            });
            widget.open();
        }

        async function delVideo(id) {
            if(!confirm("Delete this episode?")) return;
            await fetch('/api/vid_del', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
            location.reload();
        }

        async function interact(id, type, comment="") {
            await fetch('/api/vid_action', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id, type, comment }) });
            loadContent();
        }

        function addComment(id) {
            const msg = prompt("Write a comment:");
            if(msg) interact(id, 'comment', msg);
        }

        function closeModals() {
            document.getElementById('loginModal').classList.add('hidden');
            document.getElementById('adminPanel').classList.add('hidden');
        }

        loadContent();
    </script>
</body>
</html>
"""

# ================= Backend API Logic =================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def login():
    if request.json.get('pass') == ADMIN_PASS:
        session['admin'] = True
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/logout')
def logout():
    session.pop('admin', None)
    return jsonify({"success": True})

@app.route('/api/check_auth')
def check_auth():
    return jsonify({"authorized": session.get('admin', False)})

@app.route('/api/data')
def get_data():
    apis = list(api_col.find({}, {'_id': 0}))
    videos = list(video_col.find({}, {'_id': 0}).sort('_id', -1))
    
    active_api = api_col.find_one({"is_active": True})
    active_id = active_api['id'] if active_api else (apis[0]['id'] if apis else None)
    
    return jsonify({"apis": apis, "videos": videos, "active_api_id": active_id})

# --- Admin Protected Actions ---
@app.route('/api/api_add', methods=['POST'])
def api_add():
    if not session.get('admin'): return jsonify({"err": 401})
    d = request.json
    new_api = {"id": str(uuid.uuid4())[:6], "cloudName": d['cloud'], "preset": d['preset'], "is_active": False}
    api_col.insert_one(new_api)
    return jsonify({"s": 1})

@app.route('/api/api_del', methods=['POST'])
def api_del():
    if not session.get('admin'): return jsonify({"err": 401})
    api_col.delete_one({"id": request.json['id']})
    return jsonify({"s": 1})

@app.route('/api/api_set', methods=['POST'])
def api_set():
    if not session.get('admin'): return jsonify({"err": 401})
    api_col.update_many({}, {"$set": {"is_active": False}})
    api_col.update_one({"id": request.json['id']}, {"$set": {"is_active": True}})
    return jsonify({"s": 1})

@app.route('/api/vid_save', methods=['POST'])
def vid_save():
    if not session.get('admin'): return jsonify({"err": 401})
    d = request.json
    video_col.insert_one({
        "id": str(uuid.uuid4())[:8],
        "url": d['url'],
        "series": d['series'],
        "episode": d['ep'],
        "likes": 0,
        "comments": []
    })
    return jsonify({"s": 1})

@app.route('/api/vid_del', methods=['POST'])
def vid_del():
    if not session.get('admin'): return jsonify({"err": 401})
    video_col.delete_one({"id": request.json['id']})
    return jsonify({"s": 1})

@app.route('/api/vid_action', methods=['POST'])
def vid_action():
    d = request.json
    if d['type'] == 'like':
        video_col.update_one({"id": d['id']}, {"$inc": {"likes": 1}})
    elif d['type'] == 'comment':
        video_col.update_one({"id": d['id']}, {"$push": {"comments": d['comment']}})
    return jsonify({"s": 1})

if __name__ == '__main__':
    app.run(debug=True)
