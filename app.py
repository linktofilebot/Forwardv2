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
        video { height: 100%; width: 100%; object-fit: cover; }
        .glass-ui { background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .active-api { border: 2px solid #06b6d4 !important; background: rgba(6, 182, 212, 0.15); }
        .btn-grad { background: linear-gradient(45deg, #06b6d4, #3b82f6); transition: 0.3s; }
        .btn-grad:active { transform: scale(0.95); }
        
        .video-progress-container { position: absolute; bottom: 0; left: 0; width: 100%; height: 4px; background: rgba(255,255,255,0.2); cursor: pointer; z-index: 60; }
        .video-progress-bar { height: 100%; background: #06b6d4; width: 0%; transition: width 0.1s linear; }
        
        /* Bottom Nav */
        .bottom-nav { position: fixed; bottom: 0; width: 100%; background: linear-gradient(to top, black, transparent); display: flex; justify-content: space-around; padding: 15px; z-index: 70; }
        
        /* Touch Skip Overlay */
        .skip-area { position: absolute; top: 0; height: 100%; width: 30%; z-index: 40; }
        .skip-left { left: 0; }
        .skip-right { right: 0; }
    </style>
</head>
<body>

    <!-- Header -->
    <nav class="fixed top-0 w-full z-50 flex justify-between p-5 bg-gradient-to-b from-black/80 to-transparent">
        <h1 onclick="loadHome()" class="text-2xl font-black italic text-cyan-400 uppercase tracking-tighter cursor-pointer">Cloud<span class="text-white">Tok</span></h1>
        <button onclick="openAuth()" class="bg-white/10 px-6 py-2 rounded-full text-[10px] font-bold border border-white/20 hover:bg-cyan-500 transition">ADMIN</button>
    </nav>

    <!-- Video Feed -->
    <div id="videoFeed" class="feed-container scrollbar-hide"></div>

    <!-- Bottom Navigation -->
    <div class="bottom-nav">
        <button onclick="loadHome()" class="flex flex-col items-center">
            <span class="text-2xl">🏠</span>
            <span class="text-[10px] font-bold">HOME</span>
        </button>
        <div class="flex flex-col items-center opacity-30">
            <span class="text-2xl">🔍</span>
            <span class="text-[10px] font-bold">EXPLORE</span>
        </div>
    </div>

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
                        <h3 class="text-cyan-400 font-bold mb-4 text-xs uppercase">1. Cloudinary Setup</h3>
                        <div class="grid gap-3 mb-4">
                            <input id="c_name" placeholder="Cloud Name" class="bg-black p-3 rounded-xl border border-gray-800 text-sm">
                            <input id="c_key" placeholder="API Key" class="bg-black p-3 rounded-xl border border-gray-800 text-sm">
                            <input id="c_sec" placeholder="API Secret" class="bg-black p-3 rounded-xl border border-gray-800 text-sm">
                        </div>
                        <button onclick="saveApi()" class="w-full bg-cyan-700 p-3 rounded-xl font-bold text-xs uppercase">Save Account</button>
                        <div id="apiList" class="mt-6 space-y-2"></div>
                    </div>

                    <div class="glass-ui p-6 rounded-3xl border border-cyan-500/20 shadow-2xl">
                        <h3 class="text-cyan-400 font-bold mb-4 text-xs uppercase">2. Post Movie/Series</h3>
                        <div class="space-y-4">
                            <input id="movieTitle" placeholder="Movie Name" class="w-full bg-black p-4 rounded-xl border border-gray-800">
                            <input id="moviePoster" placeholder="Poster Image URL" class="w-full bg-black p-4 rounded-xl border border-gray-800">
                            <div class="p-4 border border-dashed border-gray-700 rounded-xl">
                                <p class="text-[10px] text-gray-400 mb-2">ADD EPISODE</p>
                                <div class="flex gap-2">
                                    <input id="epNo" type="number" placeholder="No." class="w-20 bg-black p-2 rounded-lg border border-gray-800">
                                    <button onclick="initUpload()" class="flex-1 btn-grad p-2 rounded-lg font-bold text-xs">🚀 UPLOAD VIDEO FOR THIS EPISODE</button>
                                </div>
                            </div>
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
        let currentMode = 'home'; 
        let filteredVideos = [];

        async function refreshData() {
            const res = await fetch('/api/data');
            appState = await res.json();
            if(currentMode === 'home') loadHome();
            if(!document.getElementById('adminPanel').classList.contains('hidden')) renderAdmin();
        }

        function loadHome() {
            currentMode = 'home';
            filteredVideos = appState.videos.filter(v => parseInt(v.episode) === 1);
            renderFeed();
            window.scrollTo(0,0);
        }

        function loadSeries(seriesName) {
            currentMode = 'series';
            filteredVideos = appState.videos
                .filter(v => v.series === seriesName)
                .sort((a, b) => parseInt(a.episode) - parseInt(b.episode));
            renderFeed();
        }

        function renderFeed() {
            const feed = document.getElementById('videoFeed');
            if(filteredVideos.length === 0) {
                feed.innerHTML = `<div class="h-screen flex items-center justify-center opacity-30 uppercase text-xs">No Content Found</div>`;
                return;
            }
            feed.innerHTML = filteredVideos.map((v, index) => `
                <div class="video-card" id="card-${v.id}">
                    <div class="skip-area skip-left" onclick="skipTime('vid-${v.id}', -5)"></div>
                    <div class="skip-area skip-right" onclick="skipTime('vid-${v.id}', 5)"></div>
                    
                    <video id="vid-${v.id}" src="${v.url}" loop autoplay playsinline 
                        onclick="togglePlay('vid-${v.id}')"
                        ontimeupdate="updateProgress('${v.id}')"></video>
                    
                    <!-- Sidebar Actions -->
                    <div class="absolute right-5 bottom-32 flex flex-col gap-5 text-center z-50">
                        <div onclick="toggleMute('vid-${v.id}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl" id="vol-icon-vid-${v.id}">🔊</div>
                        </div>
                        <div onclick="handleInteraction('${v.id}', 'like')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl">❤️</div>
                            <span class="text-[10px] font-bold">${v.likes || 0}</span>
                        </div>
                        <div onclick="openComments('${v.id}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl">💬</div>
                            <span class="text-[10px] font-bold">${(v.comments || []).length}</span>
                        </div>
                        <div onclick="shareVideo('${v.url}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl">🔗</div>
                            <span class="text-[10px] font-bold uppercase">Share</span>
                        </div>
                        <div onclick="downloadVideo('${v.url}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl bg-green-500/20">⬇️</div>
                            <span class="text-[10px] font-bold uppercase">Save</span>
                        </div>
                        <div onclick="loadSeries('${v.series}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl bg-cyan-500/50 border-cyan-400 border">🎬</div>
                            <span class="text-[10px] font-bold text-cyan-400">ALL PARTS</span>
                        </div>
                    </div>

                    <!-- Info -->
                    <div class="absolute bottom-20 left-6 right-20 z-10 pointer-events-none">
                        <div class="flex items-center gap-3 mb-2">
                            <img src="${v.poster || 'https://via.placeholder.com/150'}" class="w-12 h-12 rounded-lg border border-white/20 object-cover shadow-lg">
                            <div>
                                <h3 class="text-cyan-400 font-black text-xl italic uppercase leading-none">${v.series}</h3>
                                <p class="text-white font-bold text-[10px] opacity-90">Episode: ${v.episode}</p>
                            </div>
                        </div>
                    </div>

                    <div class="video-progress-container" onclick="seekVideo(event, 'vid-${v.id}')">
                        <div id="progress-${v.id}" class="video-progress-bar"></div>
                    </div>
                </div>
            `).join('');
        }

        function togglePlay(id) {
            const v = document.getElementById(id);
            v.paused ? v.play() : v.pause();
        }
        
        function toggleMute(id) {
            const v = document.getElementById(id);
            const icon = document.getElementById('vol-icon-' + id);
            v.muted = !v.muted;
            icon.innerText = v.muted ? '🔇' : '🔊';
        }

        function skipTime(id, sec) {
            const v = document.getElementById(id);
            v.currentTime += sec;
        }

        function shareVideo(url) {
            navigator.clipboard.writeText(url);
            alert("Video Link Copied!");
        }

        function downloadVideo(url) {
            const a = document.createElement('a');
            a.href = url;
            a.download = "CloudTok_Video.mp4";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }

        function updateProgress(id) {
            const v = document.getElementById('vid-' + id);
            const bar = document.getElementById('progress-' + id);
            if(v && bar) {
                const percent = (v.currentTime / v.duration) * 100;
                bar.style.width = percent + '%';
            }
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
                    <img src="${v.poster}" class="w-10 h-10 rounded object-cover">
                    <div class="flex-1 overflow-hidden">
                        <p class="font-bold text-cyan-400 text-xs uppercase truncate">${v.series} - EP ${v.episode}</p>
                    </div>
                    <button onclick="delVideo('${v.id}')" class="text-red-500 text-[10px] font-bold bg-red-500/10 px-3 py-1 rounded-lg">DELETE</button>
                </div>
            `).join('');
        }

        function initUpload() {
            const title = document.getElementById('movieTitle').value;
            const poster = document.getElementById('moviePoster').value;
            const ep = document.getElementById('epNo').value;
            const activeAPI = appState.apis.find(a => a.id === appState.active_id);

            if(!title || !ep || !activeAPI) return alert("Fill Name, Episode and Select API!");

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
                        body: JSON.stringify({ url: res.info.secure_url, series: title, ep: ep, poster: poster })
                    }).then(() => {
                        refreshData();
                        alert("Uploaded Episode " + ep);
                    });
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
            list.innerHTML = (video.comments || []).map(c => `<div class="comment-item bg-white/5 p-2 rounded mb-2 text-xs">${c}</div>`).join('');
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
            if((await res.json()).success) { location.reload(); } else { alert("Wrong Password!"); }
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
    vids = list(video_col.find({}, {'_id': 0}).sort('episode', 1))
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
        "series": data['series'].strip(),
        "episode": int(data['ep']),
        "poster": data.get('poster', ''),
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
