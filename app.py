from flask import Flask, render_template_string, request, jsonify, session
from pymongo import MongoClient
import uuid
import secrets
import time
import hashlib
from datetime import datetime
import cloudinary.utils

# ================= 1. ব্যাকএন্ড কনফিগারেশন =================
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# MongoDB কানেকশন
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" 
ADMIN_PASS = "admin786"

try:
    client = MongoClient(MONGO_URI)
    db = client['CloudTok_Final_Stable']
    api_col = db['apis']
    video_col = db['videos']
    print("✓ MongoDB Connected Successfully")
except Exception as e:
    print(f"✗ MongoDB Connection Error: {e}")

# ================= 2. ফ্রন্টএন্ড ডিজাইন (HTML/JS) =================
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
        video { height: 100%; width: 100%; object-fit: cover; cursor: pointer; }
        .glass-ui { background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .active-api { border: 2px solid #06b6d4 !important; background: rgba(6, 182, 212, 0.15); }
        .btn-grad { background: linear-gradient(45deg, #06b6d4, #3b82f6); transition: 0.3s; }
        .btn-grad:active { transform: scale(0.95); }
        .comment-item { background: rgba(255,255,255,0.05); padding: 8px; border-radius: 8px; margin-bottom: 5px; font-size: 12px; }
        
        /* Progress Bar Styling */
        .video-progress-container { position: absolute; bottom: 0; left: 0; width: 100%; height: 4px; background: rgba(255,255,255,0.2); cursor: pointer; z-index: 60; }
        .video-progress-bar { height: 100%; background: #06b6d4; width: 0%; transition: width 0.1s linear; }
        
        /* Skip Buttons Overlay */
        .skip-btn { position: absolute; top: 50%; transform: translateY(-50%); padding: 20px; background: rgba(0,0,0,0.3); border-radius: 50%; opacity: 0; transition: 0.3s; z-index: 40; pointer-events: none; }
        .video-card:hover .skip-btn { opacity: 0.5; pointer-events: auto; }
        .skip-left { left: 20px; }
        .skip-right { right: 20px; }
    </style>
</head>
<body>

    <!-- Header -->
    <nav class="fixed top-0 w-full z-50 flex justify-between p-5 bg-gradient-to-b from-black/80 to-transparent">
        <h1 class="text-2xl font-black italic text-cyan-400 uppercase tracking-tighter">Cloud<span class="text-white">Tok</span></h1>
        <button onclick="openAuth()" class="bg-white/10 px-6 py-2 rounded-full text-[10px] font-bold border border-white/20 hover:bg-cyan-500 transition">ADMIN DASHBOARD</button>
    </nav>

    <!-- Video Feed -->
    <div id="videoFeed" class="feed-container scrollbar-hide"></div>

    <!-- Login Modal -->
    <div id="loginModal" class="hidden fixed inset-0 z-[100] bg-black/95 flex items-center justify-center p-6">
        <div class="glass-ui p-8 rounded-3xl w-full max-sm:max-w-xs text-center">
            <h2 class="text-2xl font-black mb-6 text-cyan-400">ADMIN LOGIN</h2>
            <input id="adminPass" type="password" placeholder="Password" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-6 text-center outline-none focus:border-cyan-400">
            <button onclick="tryLogin()" class="w-full btn-grad p-4 rounded-xl font-bold uppercase">Unlock</button>
            <button onclick="closeModal('loginModal')" class="mt-4 text-gray-500 text-xs">Close</button>
        </div>
    </div>

    <!-- Comment Modal -->
    <div id="commentModal" class="hidden fixed inset-0 z-[100] bg-black/80 flex items-end justify-center">
        <div class="glass-ui w-full max-w-md p-6 rounded-t-3xl min-h-[50vh]">
            <div class="flex justify-between items-center mb-4">
                <h3 class="font-bold text-cyan-400">Comments</h3>
                <button onclick="closeModal('commentModal')" class="text-white text-xl">✕</button>
            </div>
            <div id="commentList" class="max-h-[35vh] overflow-y-auto pr-2 scrollbar-hide"></div>
            <div class="mt-4 flex gap-2">
                <input id="commentInput" type="text" placeholder="Add a comment..." class="flex-1 bg-white/10 p-3 rounded-xl border border-white/10 outline-none text-sm">
                <button id="sendCommentBtn" class="bg-cyan-500 px-4 rounded-xl font-bold">Send</button>
            </div>
        </div>
    </div>

    <!-- Admin Panel -->
    <div id="adminPanel" class="hidden fixed inset-0 z-[80] bg-black p-4 md:p-8 overflow-y-auto">
        <div class="max-w-6xl mx-auto pb-20">
            <div class="flex justify-between items-center mb-10 border-b border-gray-800 pb-5">
                <h2 class="text-3xl font-black text-cyan-500 uppercase">Control Center</h2>
                <div class="flex gap-4">
                    <button onclick="doLogout()" class="text-red-500 font-bold text-xs uppercase underline">Logout</button>
                    <button onclick="location.reload()" class="text-white text-3xl">✕</button>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-10">
                <div class="space-y-8">
                    <div class="glass-ui p-6 rounded-3xl border border-gray-800">
                        <h3 class="text-cyan-400 font-bold mb-4 text-xs uppercase">1. Cloudinary Setup (No Preset)</h3>
                        <div class="grid gap-3 mb-4">
                            <input id="c_name" placeholder="Cloud Name" class="bg-black p-3 rounded-xl border border-gray-800 text-sm">
                            <input id="c_key" placeholder="API Key" class="bg-black p-3 rounded-xl border border-gray-800 text-sm">
                            <input id="c_sec" placeholder="API Secret" class="bg-black p-3 rounded-xl border border-gray-800 text-sm">
                        </div>
                        <button onclick="saveApi()" class="w-full bg-cyan-700 p-3 rounded-xl font-bold text-xs uppercase">Save Account</button>
                        <div id="apiList" class="mt-6 space-y-2"></div>
                    </div>

                    <div class="glass-ui p-6 rounded-3xl border border-cyan-500/20 shadow-2xl">
                        <h3 class="text-cyan-400 font-bold mb-4 text-xs uppercase">2. Fast Upload Episode</h3>
                        <div class="space-y-4">
                            <input id="movieTitle" placeholder="Movie Name" class="w-full bg-black p-4 rounded-xl border border-gray-800">
                            <input id="epNo" type="number" placeholder="Episode Number" class="w-full bg-black p-4 rounded-xl border border-gray-800">
                            <button onclick="initUpload()" class="w-full btn-grad p-5 rounded-2xl font-black text-xl shadow-lg">🚀 UPLOAD VIDEO</button>
                        </div>
                    </div>
                </div>

                <div class="glass-ui p-6 rounded-3xl border border-gray-800">
                    <h3 class="text-gray-500 font-bold mb-4 text-xs uppercase">3. Content Manager</h3>
                    <div id="contentList" class="space-y-4 max-h-[700px] overflow-y-auto scrollbar-hide pr-2"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let appState = { apis: [], videos: [], active_id: null };

        async function refreshData() {
            const res = await fetch('/api/data');
            appState = await res.json();
            renderFeed();
            if(!document.getElementById('adminPanel').classList.contains('hidden')) renderAdmin();
        }

        function renderFeed() {
            const feed = document.getElementById('videoFeed');
            if(appState.videos.length === 0) {
                feed.innerHTML = `<div class="h-screen flex items-center justify-center opacity-30 uppercase text-xs">No Content</div>`;
                return;
            }
            feed.innerHTML = appState.videos.map((v, index) => `
                <div class="video-card" id="card-${v.id}">
                    <video id="vid-${v.id}" src="${v.url}" loop autoplay playsinline 
                        onclick="togglePlay('vid-${v.id}')"
                        ontimeupdate="updateProgress('${v.id}')"></video>
                    
                    <!-- Skip Buttons -->
                    <button class="skip-btn skip-left" onclick="skipTime('vid-${v.id}', -5)">⏪</button>
                    <button class="skip-btn skip-right" onclick="skipTime('vid-${v.id}', 5)">⏩</button>

                    <!-- Sidebar Actions -->
                    <div class="absolute right-5 bottom-32 flex flex-col gap-5 text-center z-50">
                        <div onclick="handleInteraction('${v.id}', 'like')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl">❤️</div>
                            <span class="text-[10px] font-bold">${v.likes || 0}</span>
                        </div>
                        <div onclick="openComments('${v.id}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl">💬</div>
                            <span class="text-[10px] font-bold">${(v.comments || []).length}</span>
                        </div>
                        <div onclick="shareVideo('${v.series}', '${v.url}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl">🔗</div>
                            <span class="text-[10px] font-bold">SHARE</span>
                        </div>
                        <div onclick="downloadVideo('${v.url}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl">⬇️</div>
                            <span class="text-[10px] font-bold">SAVE</span>
                        </div>
                        <div onclick="toggleMute('vid-${v.id}')" class="cursor-pointer">
                            <div id="mute-icon-vid-${v.id}" class="glass-ui p-3 rounded-full text-xl">🔊</div>
                        </div>
                    </div>

                    <!-- Info -->
                    <div class="absolute bottom-12 left-6 right-20 z-10 pointer-events-none">
                        <h3 class="text-cyan-400 font-black text-3xl italic uppercase leading-none">${v.series}</h3>
                        <p class="text-white font-bold text-lg opacity-90 mt-1">Episode: ${v.episode}</p>
                    </div>

                    <!-- YouTube Style Seeker -->
                    <div class="video-progress-container" onclick="seekVideo(event, 'vid-${v.id}')">
                        <div id="progress-${v.id}" class="video-progress-bar"></div>
                    </div>
                </div>
            `).join('');
        }

        // --- Video Control Functions ---
        function togglePlay(id) {
            const v = document.getElementById(id);
            v.paused ? v.play() : v.pause();
        }

        function toggleMute(id) {
            const v = document.getElementById(id);
            const btn = document.getElementById('mute-icon-' + id);
            v.muted = !v.muted;
            btn.innerText = v.muted ? "🔇" : "🔊";
        }

        function skipTime(id, sec) {
            const v = document.getElementById(id);
            v.currentTime += sec;
        }

        function updateProgress(id) {
            const v = document.getElementById('vid-' + id);
            const bar = document.getElementById('progress-' + id);
            const percent = (v.currentTime / v.duration) * 100;
            bar.style.width = percent + '%';
        }

        function seekVideo(e, id) {
            const v = document.getElementById(id);
            const rect = e.currentTarget.getBoundingClientRect();
            const pos = (e.pageX - rect.left) / rect.width;
            v.currentTime = pos * v.duration;
        }

        function shareVideo(title, url) {
            if (navigator.share) {
                navigator.share({ title: title, url: url });
            } else {
                alert("Link Copied: " + url);
            }
        }

        function downloadVideo(url) {
            const a = document.createElement('a');
            a.href = url;
            a.download = 'CloudTok_Video.mp4';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }

        function renderAdmin() {
            document.getElementById('apiList').innerHTML = appState.apis.map(a => `
                <div onclick="switchActiveApi('${a.id}')" class="flex justify-between items-center p-3 rounded-xl border cursor-pointer ${a.id === appState.active_id ? 'active-api shadow-lg' : 'border-gray-800'}">
                    <span class="text-xs font-bold">${a.cloud}</span>
                    <button onclick="delApi('${a.id}')" class="text-red-500 font-bold px-2">✕</button>
                </div>
            `).join('');

            document.getElementById('contentList').innerHTML = appState.videos.map(v => `
                <div class="flex items-center gap-4 bg-white/5 p-3 rounded-2xl border border-gray-800">
                    <div class="flex-1 overflow-hidden">
                        <p class="font-bold text-cyan-400 text-xs uppercase truncate">${v.series} - EP ${v.episode}</p>
                    </div>
                    <button onclick="delVideo('${v.id}')" class="text-red-500 text-[10px] font-bold bg-red-500/10 px-3 py-1 rounded-lg">DELETE</button>
                </div>
            `).join('');
        }

        // --- SIGNED UPLOAD ---
        function initUpload() {
            const title = document.getElementById('movieTitle').value;
            const ep = document.getElementById('epNo').value;
            const activeAPI = appState.apis.find(a => a.id === appState.active_id);

            if(!title || !ep || !activeAPI) return alert("Fill Name/Ep and Select API!");

            cloudinary.createUploadWidget({
                cloudName: activeAPI.cloud,
                apiKey: activeAPI.key,
                uploadSignature: (callback, params) => {
                    fetch('/api/sign', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ params: params })
                    })
                    .then(r => r.json())
                    .then(data => callback(data.signature));
                },
                resourceType: 'video'
            }, (err, res) => {
                if (!err && res && res.event === "success") {
                    fetch('/api/save_video', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ url: res.info.secure_url, series: title, ep: ep })
                    }).then(() => refreshData());
                    alert("Upload Complete!");
                }
            }).open();
        }

        async function handleInteraction(id, type, commentText = "") {
            await fetch('/api/interaction', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, type, comment: commentText })
            });
            refreshData();
        }

        function openComments(id) {
            const video = appState.videos.find(v => v.id === id);
            const list = document.getElementById('commentList');
            list.innerHTML = (video.comments || []).map(c => `<div class="comment-item">${c}</div>`).join('');
            document.getElementById('commentModal').classList.remove('hidden');
            
            document.getElementById('sendCommentBtn').onclick = () => {
                const txt = document.getElementById('commentInput').value;
                if(txt) {
                    handleInteraction(id, 'comment', txt);
                    document.getElementById('commentInput').value = '';
                    setTimeout(() => openComments(id), 500);
                }
            };
        }

        async function saveApi() {
            const cloud = document.getElementById('c_name').value;
            const key = document.getElementById('c_key').value;
            const sec = document.getElementById('c_sec').value;
            await fetch('/api/add_api', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ cloud, key, sec }) });
            refreshData();
        }

        async function switchActiveApi(id) {
            await fetch('/api/set_api', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
            refreshData();
        }

        async function delApi(id) {
            if(confirm("Delete API?")) {
                await fetch('/api/del_api', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
                refreshData();
            }
        }

        async function delVideo(id) {
            if(confirm("Delete Video?")) {
                await fetch('/api/del_vid', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
                refreshData();
            }
        }

        async function openAuth() {
            const res = await fetch('/api/auth_check');
            if((await res.json()).is_auth) document.getElementById('adminPanel').classList.remove('hidden');
            else document.getElementById('loginModal').classList.remove('hidden');
            refreshData();
        }

        async function tryLogin() {
            const pass = document.getElementById('adminPass').value;
            const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ pass }) });
            if((await res.json()).success) { location.reload(); } else { alert("Wrong!"); }
        }

        async function doLogout() {
            await fetch('/api/logout');
            location.reload();
        }

        function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

        refreshData();
    </script>
</body>
</html>
"""

# ================= 3. ব্যাকএন্ড এপিআই লজিক (Python) =================

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/sign', methods=['POST'])
def sign_api():
    if not session.get('admin_session'): return jsonify({"error": "Unauthorized"}), 401
    active_api = api_col.find_one({"is_active": True})
    if not active_api: return jsonify({"error": "No Active API"}), 400
    params = request.json.get('params', {})
    signature = cloudinary.utils.api_sign_request(params, active_api['secret'])
    return jsonify({"signature": signature})

@app.route('/api/login', methods=['POST'])
def login():
    if request.json.get('pass') == ADMIN_PASS:
        session['admin_session'] = True
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/logout')
def logout():
    session.pop('admin_session', None)
    return jsonify({"success": True})

@app.route('/api/auth_check')
def auth_check():
    return jsonify({"is_auth": session.get('admin_session', False)})

@app.route('/api/data')
def get_data():
    apis = list(api_col.find({}, {'_id': 0}))
    vids = list(video_col.find({}, {'_id': 0}).sort('_id', -1))
    active = api_col.find_one({"is_active": True})
    return jsonify({
        "apis": apis, 
        "videos": vids, 
        "active_id": active['id'] if active else None
    })

@app.route('/api/add_api', methods=['POST'])
def add_api():
    if not session.get('admin_session'): return "Unauthorized", 401
    data = request.json
    api_col.insert_one({
        "id": str(uuid.uuid4())[:8],
        "cloud": data['cloud'],
        "key": data['key'],
        "secret": data['sec'],
        "is_active": False
    })
    return jsonify({"success": True})

@app.route('/api/del_api', methods=['POST'])
def del_api():
    if not session.get('admin_session'): return "Unauthorized", 401
    api_col.delete_one({"id": request.json['id']})
    return jsonify({"success": True})

@app.route('/api/set_api', methods=['POST'])
def set_api():
    if not session.get('admin_session'): return "Unauthorized", 401
    api_col.update_many({}, {"$set": {"is_active": False}})
    api_col.update_one({"id": request.json['id']}, {"$set": {"is_active": True}})
    return jsonify({"success": True})

@app.route('/api/save_video', methods=['POST'])
def save_video():
    if not session.get('admin_session'): return "Unauthorized", 401
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

@app.route('/api/interaction', methods=['POST'])
def interaction():
    data = request.json
    if data['type'] == 'like':
        video_col.update_one({"id": data['id']}, {"$inc": {"likes": 1}})
    elif data['type'] == 'comment' and data.get('comment'):
        video_col.update_one({"id": data['id']}, {"$push": {"comments": data['comment']}})
    return jsonify({"success": True})

@app.route('/api/del_vid', methods=['POST'])
def del_vid():
    if not session.get('admin_session'): return "Unauthorized", 401
    video_col.delete_one({"id": request.json['id']})
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
