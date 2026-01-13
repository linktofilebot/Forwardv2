from flask import Flask, render_template_string, request, jsonify, session
import json
import os
import uuid
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ডাটাবেস ফাইল পাথ
DB_FILE = 'database.json'
ADMIN_PASS = "admin786" # আপনার অ্যাডমিন পাসওয়ার্ড (এটি পরিবর্তন করতে পারেন)

def load_db():
    if not os.path.exists(DB_FILE):
        return {"apis": [], "videos": [], "active_api_id": None}
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"apis": [], "videos": [], "active_api_id": None}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- Frontend (HTML, CSS, JS) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudTok Ultimate - Admin Control</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://upload-widget.cloudinary.com/global/all.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        body { background-color: #000; color: #fff; font-family: 'Inter', sans-serif; overflow: hidden; }
        .video-feed { height: 100vh; scroll-snap-type: y mandatory; overflow-y: scroll; scrollbar-width: none; }
        .video-card { height: 100vh; scroll-snap-align: start; position: relative; background: #000; display: flex; align-items: center; justify-content: center; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
        video { height: 100%; width: 100%; object-fit: cover; }
        .glass { background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .admin-btn { background: linear-gradient(45deg, #06b6d4, #3b82f6); }
    </style>
</head>
<body>

    <!-- Header -->
    <nav class="fixed top-0 w-full z-50 flex justify-between p-5 bg-gradient-to-b from-black to-transparent">
        <h1 class="text-2xl font-black italic text-cyan-500 tracking-tighter">CLOUD<span class="text-white">TOK</span></h1>
        <button onclick="checkAuth()" class="bg-white/10 backdrop-blur-md px-5 py-2 rounded-full text-xs font-bold border border-white/20">ADMIN PANEL</button>
    </nav>

    <!-- UI: Video Feed -->
    <div id="videoFeed" class="video-feed scrollbar-hide"></div>

    <!-- UI: Login Modal -->
    <div id="loginModal" class="hidden fixed inset-0 z-[100] bg-black/90 flex items-center justify-center p-6">
        <div class="glass p-8 rounded-3xl w-full max-w-sm text-center">
            <h2 class="text-2xl font-bold mb-6 text-cyan-400 uppercase tracking-widest">Admin Login</h2>
            <input id="adminPass" type="password" placeholder="Enter Admin Password" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-4 outline-none focus:border-cyan-500">
            <button onclick="login()" class="w-full admin-btn p-4 rounded-xl font-bold uppercase tracking-widest">Unlock Panel</button>
            <button onclick="closeModals()" class="mt-4 text-gray-500 text-sm">Cancel</button>
        </div>
    </div>

    <!-- UI: Admin Dashboard -->
    <div id="adminPanel" class="hidden fixed inset-0 z-[80] bg-black p-6 overflow-y-auto">
        <div class="max-w-4xl mx-auto pb-20">
            <div class="flex justify-between items-center mb-10 border-b border-gray-800 pb-5">
                <h2 class="text-3xl font-black text-cyan-500 uppercase">Dashboard</h2>
                <div class="flex gap-4">
                    <button onclick="logout()" class="text-red-500 text-sm font-bold uppercase">Logout</button>
                    <button onclick="closeModals()" class="text-white text-2xl">✕</button>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <!-- Column 1: API & Upload -->
                <div class="space-y-8">
                    <div class="glass p-6 rounded-3xl">
                        <h3 class="text-gray-400 font-bold mb-4 uppercase text-xs">1. API Manager</h3>
                        <div class="space-y-3 mb-4">
                            <input id="cloudInput" placeholder="Cloud Name" class="w-full bg-black p-3 rounded-xl border border-gray-800">
                            <input id="presetInput" placeholder="Upload Preset" class="w-full bg-black p-3 rounded-xl border border-gray-800">
                        </div>
                        <button onclick="addAPI()" class="w-full bg-cyan-600 p-3 rounded-xl font-bold hover:bg-cyan-500 transition">Add New API</button>
                        
                        <div id="apiList" class="mt-6 space-y-2 max-h-40 overflow-y-auto scrollbar-hide"></div>
                    </div>

                    <div class="glass p-6 rounded-3xl">
                        <h3 class="text-gray-400 font-bold mb-4 uppercase text-xs">2. Upload Episode</h3>
                        <div class="flex gap-2 mb-4">
                            <input id="seriesName" placeholder="Series Name" class="w-2/3 bg-black p-3 rounded-xl border border-gray-800">
                            <input id="episodeNo" type="number" placeholder="Ep." class="w-1/3 bg-black p-3 rounded-xl border border-gray-800">
                        </div>
                        <div id="uploadStatus" class="hidden mb-4 p-4 rounded-2xl bg-cyan-900/20 border border-cyan-500/30">
                            <p id="progressText" class="text-cyan-400 font-bold text-xs uppercase mb-2">Uploading: 0%</p>
                            <div class="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                                <div id="progressBar" class="bg-cyan-500 h-full transition-all" style="width: 0%"></div>
                            </div>
                        </div>
                        <button onclick="startUpload()" class="w-full bg-white text-black p-4 rounded-xl font-black text-lg">🚀 UPLOAD NOW</button>
                    </div>
                </div>

                <!-- Column 2: Content Manager -->
                <div class="glass p-6 rounded-3xl">
                    <h3 class="text-gray-400 font-bold mb-4 uppercase text-xs">3. Content Manager (Delete/Edit)</h3>
                    <div id="contentList" class="space-y-4 max-h-[600px] overflow-y-auto pr-2 scrollbar-hide text-sm">
                        <!-- Videos List with Delete Button -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let db = { apis: [], videos: [], active_api_id: null };
        let isLoggedIn = false;

        async function init() {
            const res = await fetch('/api/get_db');
            db = await res.json();
            renderFeed();
        }

        async function checkAuth() {
            const res = await fetch('/api/check_session');
            const data = await res.json();
            if (data.auth) {
                showAdmin();
            } else {
                document.getElementById('loginModal').classList.remove('hidden');
            }
        }

        async function login() {
            const pass = document.getElementById('adminPass').value;
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ pass })
            });
            const data = await res.json();
            if (data.success) {
                location.reload();
            } else {
                alert("Wrong Password!");
            }
        }

        async function logout() {
            await fetch('/api/logout');
            location.reload();
        }

        function showAdmin() {
            document.getElementById('loginModal').classList.add('hidden');
            document.getElementById('adminPanel').classList.remove('hidden');
            renderAdmin();
        }

        function renderFeed() {
            const feed = document.getElementById('videoFeed');
            if(db.videos.length === 0) {
                feed.innerHTML = `<div class="h-screen flex items-center justify-center text-gray-500 uppercase tracking-widest">No Content</div>`;
                return;
            }
            feed.innerHTML = db.videos.map(vid => `
                <div class="video-card">
                    <video src="${vid.url}" loop autoplay muted playsinline onclick="this.paused?this.play():this.pause()"></video>
                    <div class="absolute right-4 bottom-32 flex flex-col gap-6 text-center z-10">
                        <div onclick="action('${vid.id}', 'like')" class="cursor-pointer group">
                            <div class="glass p-4 rounded-full mb-1 group-active:scale-150 transition">❤️</div>
                            <span class="text-xs font-bold">${vid.likes}</span>
                        </div>
                        <div onclick="addComment('${vid.id}')" class="cursor-pointer">
                            <div class="glass p-4 rounded-full mb-1">💬</div>
                            <span class="text-xs font-bold">${vid.comments.length}</span>
                        </div>
                        <div onclick="action('${vid.id}', 'share')" class="cursor-pointer">
                            <div class="glass p-4 rounded-full mb-1">🔗</div>
                            <span class="text-xs font-bold">${vid.shares}</span>
                        </div>
                    </div>
                    <div class="absolute bottom-10 left-5 right-16 z-10">
                        <h3 class="text-cyan-400 font-black text-2xl italic uppercase tracking-tighter">${vid.series}</h3>
                        <p class="text-white font-medium">Episode: ${vid.episode}</p>
                    </div>
                </div>
            `).join('');
        }

        function renderAdmin() {
            const apiList = document.getElementById('apiList');
            apiList.innerHTML = db.apis.map(api => `
                <div class="flex items-center justify-between p-3 rounded-xl border ${api.id === db.active_api_id ? 'border-cyan-500 bg-cyan-900/20' : 'border-gray-800 bg-black'}">
                    <span onclick="setApi('${api.id}')" class="cursor-pointer text-sm font-bold">${api.cloudName}</span>
                    <button onclick="deleteAPI('${api.id}')" class="text-red-500 text-xs">Delete</button>
                </div>
            `).join('');

            const contentList = document.getElementById('contentList');
            contentList.innerHTML = db.videos.map(vid => `
                <div class="flex items-center gap-4 bg-gray-900 p-3 rounded-xl border border-gray-800">
                    <video src="${vid.url}" class="w-16 h-20 object-cover rounded-lg"></video>
                    <div class="flex-1">
                        <p class="font-bold text-cyan-400">${vid.series}</p>
                        <p class="text-xs text-gray-500">Episode: ${vid.episode}</p>
                        <p class="text-[10px] text-gray-600">ID: ${vid.id}</p>
                    </div>
                    <button onclick="deleteVideo('${vid.id}')" class="bg-red-500/10 text-red-500 p-2 rounded-lg text-xs hover:bg-red-500 hover:text-white transition">Delete</button>
                </div>
            `).join('');
        }

        async function addAPI() {
            const cloudName = document.getElementById('cloudInput').value;
            const preset = document.getElementById('presetInput').value;
            await fetch('/api/add_api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ cloudName, preset })
            });
            location.reload();
        }

        async function deleteAPI(id) {
            if(!confirm("Delete this API?")) return;
            await fetch('/api/del_api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id })
            });
            location.reload();
        }

        async function deleteVideo(id) {
            if(!confirm("Delete this video permanently?")) return;
            await fetch('/api/del_video', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id })
            });
            location.reload();
        }

        async function setApi(id) {
            await fetch('/api/set_api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id })
            });
            location.reload();
        }

        function startUpload() {
            const active = db.apis.find(a => a.id === db.active_api_id);
            const series = document.getElementById('seriesName').value;
            const epNo = document.getElementById('episodeNo').value;
            if(!active) return alert("Select an API first!");
            if(!series || !epNo) return alert("Enter series and episode info!");

            cloudinary.openUploadWidget({
                cloudName: active.cloudName, uploadPreset: active.preset, resourceType: 'video'
            }, async (err, result) => {
                const sDiv = document.getElementById('uploadStatus');
                if (result.event === "upload-progress") {
                    sDiv.classList.remove('hidden');
                    let p = Math.round(result.info.progress);
                    document.getElementById('progressText').innerText = `Uploading: ${p}%`;
                    document.getElementById('progressBar').style.width = `${p}%`;
                }
                if (!err && result.event === "success") {
                    await fetch('/api/save_video', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ url: result.info.secure_url, series, epNo })
                    });
                    location.reload();
                }
            });
        }

        async function action(id, type, comment="") {
            await fetch('/api/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, type, comment })
            });
            init();
        }

        function addComment(id) {
            const msg = prompt("Write comment:");
            if(msg) action(id, 'comment', msg);
        }

        function closeModals() {
            document.getElementById('loginModal').classList.add('hidden');
            document.getElementById('adminPanel').classList.add('hidden');
        }

        init();
    </script>
</body>
</html>
"""

# --- Backend Routes ---

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

@app.route('/api/check_session')
def check_session():
    return jsonify({"auth": session.get('admin', False)})

@app.route('/api/get_db')
def get_db():
    return jsonify(load_db())

# API & Video Management (Protected Routes)
@app.route('/api/add_api', methods=['POST'])
def add_api():
    if not session.get('admin'): return jsonify({"err": "unauthorized"}), 401
    d = request.json
    db = load_db()
    new_api = {"id": str(uuid.uuid4())[:6], "cloudName": d['cloudName'], "preset": d['preset']}
    db['apis'].append(new_api)
    if not db['active_api_id']: db['active_api_id'] = new_api['id']
    save_db(db)
    return jsonify({"s": 1})

@app.route('/api/del_api', methods=['POST'])
def del_api():
    if not session.get('admin'): return jsonify({"err": "unauthorized"}), 401
    db = load_db()
    db['apis'] = [a for a in db['apis'] if a['id'] != request.json['id']]
    save_db(db)
    return jsonify({"s": 1})

@app.route('/api/set_api', methods=['POST'])
def set_api():
    if not session.get('admin'): return jsonify({"err": "unauthorized"}), 401
    db = load_db()
    db['active_api_id'] = request.json['id']
    save_db(db)
    return jsonify({"s": 1})

@app.route('/api/save_video', methods=['POST'])
def save_video():
    if not session.get('admin'): return jsonify({"err": "unauthorized"}), 401
    d = request.json
    db = load_db()
    new_vid = {"id": str(uuid.uuid4())[:8], "url": d['url'], "series": d['series'], "episode": d['epNo'], "likes": 0, "shares": 0, "comments": []}
    db['videos'].insert(0, new_vid)
    save_db(db)
    return jsonify({"s": 1})

@app.route('/api/del_video', methods=['POST'])
def del_video():
    if not session.get('admin'): return jsonify({"err": "unauthorized"}), 401
    db = load_db()
    db['videos'] = [v for v in db['videos'] if v['id'] != request.json['id']]
    save_db(db)
    return jsonify({"s": 1})

@app.route('/api/action', methods=['POST'])
def video_action():
    d = request.json
    db = load_db()
    for v in db['videos']:
        if v['id'] == d['id']:
            if d['type'] == 'like': v['likes'] += 1
            if d['type'] == 'share': v['shares'] += 1
            if d['type'] == 'comment': v['comments'].append(d['comment'])
            break
    save_db(db)
    return jsonify({"s": 1})

if __name__ == '__main__':
    app.run(debug=True)
