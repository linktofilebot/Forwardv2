from flask import Flask, render_template_string, request, jsonify, session
from pymongo import MongoClient
import uuid
import secrets
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

# ================= 2. ফ্রন্টএন্ড ডিজাইন (HTML/JS/CSS) =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudTok Ultimate - Home & Reels</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://upload-widget.cloudinary.com/global/all.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;900&display=swap" rel="stylesheet">
    <style>
        body { background: #000; color: #fff; font-family: 'Poppins', sans-serif; overflow: hidden; }
        
        /* Reels Scroll Logic */
        .reels-container { height: 100vh; scroll-snap-type: y mandatory; overflow-y: scroll; scrollbar-width: none; display: none; }
        .reels-container::-webkit-scrollbar { display: none; }
        .video-card { height: 100vh; scroll-snap-align: start; position: relative; background: #000; display: flex; align-items: center; }
        video { height: 100%; width: 100%; object-fit: cover; }

        /* Home Grid Logic */
        .home-container { height: 100vh; overflow-y: auto; padding: 80px 15px 100px; display: block; }
        .movie-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
        .movie-card { background: #111; border-radius: 15px; overflow: hidden; border: 1px solid #222; position: relative; aspect-ratio: 10/14; transition: 0.3s; }
        .movie-card:active { transform: scale(0.95); }
        .movie-thumb { width: 100%; height: 100%; object-fit: cover; opacity: 0.6; }

        /* UI Helpers */
        .glass { background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(10px); }
        .btn-cyan { background: linear-gradient(45deg, #06b6d4, #3b82f6); color: white; }
        .progress-bar { position: absolute; bottom: 0; left: 0; height: 4px; background: #06b6d4; width: 0%; z-index: 50; }
        
        /* Navigation */
        .bottom-nav { position: fixed; bottom: 0; width: 100%; display: flex; justify-content: space-around; padding: 15px; background: rgba(0,0,0,0.9); border-top: 1px solid #222; z-index: 100; }
        .nav-item { text-align: center; font-size: 10px; color: #888; cursor: pointer; }
        .nav-item.active { color: #06b6d4; }
    </style>
</head>
<body>

    <!-- Top Header -->
    <header class="fixed top-0 w-full z-[110] flex justify-between items-center p-4 bg-gradient-to-b from-black to-transparent">
        <h1 class="text-xl font-black italic text-cyan-400">CLOUD<span class="text-white">TOK</span></h1>
        <button onclick="openAdmin()" class="bg-white/10 px-4 py-1 rounded-full text-[10px] font-bold border border-white/20">ADMIN</button>
    </header>

    <!-- 1. Home View: Movie List -->
    <div id="homeView" class="home-container">
        <h2 class="text-lg font-bold mb-4 flex items-center gap-2">🎬 Recommended Movies</h2>
        <div id="movieGrid" class="movie-grid">
            <!-- Movie cards will load here -->
        </div>
    </div>

    <!-- 2. Reels View: Video Player -->
    <div id="reelsView" class="reels-container">
        <!-- Videos will load here -->
    </div>

    <!-- Bottom Navigation -->
    <div class="bottom-nav">
        <div class="nav-item active" id="navHome" onclick="showHome()">
            <div class="text-xl">🏠</div>
            <span>Home</span>
        </div>
        <div class="nav-item" id="navReels" onclick="alert('Please select a movie from Home first!')">
            <div class="text-xl">📺</div>
            <span>Reels</span>
        </div>
        <div class="nav-item" onclick="openAdmin()">
            <div class="text-xl">⚙️</div>
            <span>Manage</span>
        </div>
    </div>

    <!-- Admin Panel Modal -->
    <div id="adminPanel" class="hidden fixed inset-0 z-[200] bg-black overflow-y-auto p-5">
        <div class="flex justify-between items-center mb-8">
            <h2 class="text-2xl font-black text-cyan-500">CONTROL CENTER</h2>
            <button onclick="closeAdmin()" class="text-2xl">✕</button>
        </div>

        <div class="space-y-6">
            <!-- API Selection -->
            <div class="bg-white/5 p-4 rounded-2xl border border-white/10">
                <h3 class="text-xs font-bold text-gray-400 mb-3 uppercase">Cloudinary Settings</h3>
                <div id="apiList" class="space-y-2 mb-4"></div>
                <div class="grid grid-cols-3 gap-2">
                    <input id="c_name" placeholder="Name" class="bg-black p-2 rounded text-xs border border-white/10">
                    <input id="c_key" placeholder="Key" class="bg-black p-2 rounded text-xs border border-white/10">
                    <input id="c_sec" placeholder="Secret" class="bg-black p-2 rounded text-xs border border-white/10">
                </div>
                <button onclick="saveApi()" class="w-full mt-3 bg-cyan-700 py-2 rounded-xl text-xs font-bold">ADD ACCOUNT</button>
            </div>

            <!-- Upload Section -->
            <div class="bg-white/5 p-5 rounded-2xl border-2 border-cyan-500/30">
                <h3 class="text-cyan-400 font-bold mb-4">📤 UPLOAD EPISODE</h3>
                <input id="movieTitle" placeholder="Movie / Series Name" class="w-full bg-black p-4 rounded-xl border border-white/10 mb-3 outline-none focus:border-cyan-500">
                <input id="epNo" type="number" placeholder="Episode Number (e.g. 1)" class="w-full bg-black p-4 rounded-xl border border-white/10 mb-4 outline-none">
                <button onclick="startUpload()" class="w-full btn-cyan p-4 rounded-xl font-black text-lg">UPLOAD VIDEO</button>
            </div>

            <!-- Content List -->
            <div class="bg-white/5 p-4 rounded-2xl border border-white/10">
                <h3 class="text-xs font-bold text-gray-400 mb-3 uppercase">Manage Content</h3>
                <div id="contentList" class="space-y-2"></div>
            </div>
            
            <button onclick="doLogout()" class="w-full py-3 text-red-500 text-xs font-bold uppercase">Logout Admin</button>
        </div>
    </div>

    <!-- Login Modal -->
    <div id="loginModal" class="hidden fixed inset-0 z-[250] bg-black/95 flex items-center justify-center p-10">
        <div class="bg-white/5 p-8 rounded-3xl border border-white/10 w-full max-w-sm text-center">
            <h2 class="text-xl font-black text-cyan-400 mb-6 uppercase">Admin Login</h2>
            <input id="adminPass" type="password" placeholder="Enter Password" class="w-full bg-black p-4 rounded-xl border border-white/10 mb-6 text-center outline-none">
            <button onclick="tryLogin()" class="w-full btn-cyan p-4 rounded-xl font-bold">UNLOCK</button>
        </div>
    </div>

    <script>
        let state = { apis: [], videos: [], active_api_id: null, seriesGrouped: {} };

        // 1. ডাটা লোড করা
        async function loadAppData() {
            const res = await fetch('/api/data');
            const data = await res.json();
            state.apis = data.apis;
            state.videos = data.videos;
            state.active_api_id = data.active_api_id;

            // ভিডিওগুলোকে সিরিজ অনুযায়ী গ্রুপ করা
            state.seriesGrouped = {};
            state.videos.forEach(v => {
                if(!state.seriesGrouped[v.series]) state.seriesGrouped[v.series] = [];
                state.seriesGrouped[v.series].push(v);
            });

            // প্রতিটি সিরিজের ভিডিও পর্ব অনুযায়ী সাজানো (1, 2, 3...)
            for(let series in state.seriesGrouped) {
                state.seriesGrouped[series].sort((a, b) => a.episode - b.episode);
            }

            renderHome();
        }

        // 2. হোম স্ক্রিন রেন্ডার (মুভি কার্ড)
        function renderHome() {
            const grid = document.getElementById('movieGrid');
            grid.innerHTML = '';
            
            Object.keys(state.seriesGrouped).forEach(seriesName => {
                const firstVideo = state.seriesGrouped[seriesName][0];
                const card = document.createElement('div');
                card.className = 'movie-card';
                card.onclick = () => playSeries(seriesName);
                card.innerHTML = `
                    <div class="absolute inset-0 bg-gradient-to-b from-transparent to-black/90"></div>
                    <div class="absolute inset-0 flex items-center justify-center text-5xl opacity-20">🎬</div>
                    <div class="absolute bottom-3 left-3 right-3">
                        <p class="text-cyan-400 text-[10px] font-bold uppercase tracking-widest">Series</p>
                        <h3 class="font-bold text-sm leading-tight uppercase truncate">${seriesName}</h3>
                        <p class="text-[10px] text-gray-400">${state.seriesGrouped[seriesName].length} Episodes Available</p>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        // 3. রিলস প্লে করা (সিরিজ অনুযায়ী)
        function playSeries(seriesName) {
            const videos = state.seriesGrouped[seriesName];
            const reelsView = document.getElementById('reelsView');
            const homeView = document.getElementById('homeView');

            homeView.style.display = 'none';
            reelsView.style.display = 'block';
            document.getElementById('navHome').classList.remove('active');
            document.getElementById('navReels').classList.add('active');

            reelsView.innerHTML = videos.map((v, index) => `
                <div class="video-card">
                    <video id="vid-${v.id}" src="${v.url}" loop autoplay playsinline onclick="toggleVideo('vid-${v.id}')" ontimeupdate="updateProgress('${v.id}')"></video>
                    
                    <!-- Side Actions -->
                    <div class="absolute right-4 bottom-32 flex flex-col gap-5 text-center">
                        <div class="glass p-3 rounded-full">❤️<br><span class="text-[10px]">${v.likes}</span></div>
                        <div class="glass p-3 rounded-full">💬<br><span class="text-[10px]">0</span></div>
                        <div class="glass p-3 rounded-full" onclick="showHome()">🏠<br><span class="text-[10px]">Exit</span></div>
                    </div>

                    <!-- Video Info -->
                    <div class="absolute bottom-10 left-5 right-20 pointer-events-none">
                        <h2 class="text-cyan-400 font-black text-2xl uppercase italic">${v.series}</h2>
                        <p class="text-white font-bold text-sm">Episode: ${v.episode} / ${videos.length}</p>
                    </div>

                    <div class="progress-bar" id="bar-${v.id}"></div>
                </div>
            `).join('');
            
            reelsView.scrollTop = 0;
        }

        function showHome() {
            document.querySelectorAll('video').forEach(v => v.pause());
            document.getElementById('homeView').style.display = 'block';
            document.getElementById('reelsView').style.display = 'none';
            document.getElementById('navHome').classList.add('active');
            document.getElementById('navReels').classList.remove('active');
        }

        function toggleVideo(id) {
            const v = document.getElementById(id);
            v.paused ? v.play() : v.pause();
        }

        function updateProgress(id) {
            const v = document.getElementById('vid-' + id);
            const bar = document.getElementById('bar-' + id);
            if(v && bar) {
                const percent = (v.currentTime / v.duration) * 100;
                bar.style.width = percent + '%';
            }
        }

        // --- Admin Logic ---
        async function openAdmin() {
            const res = await fetch('/api/auth_check');
            const data = await res.json();
            if(data.is_auth) {
                document.getElementById('adminPanel').classList.remove('hidden');
                renderAdminUI();
            } else {
                document.getElementById('loginModal').classList.remove('hidden');
            }
        }

        function renderAdminUI() {
            // API List
            document.getElementById('apiList').innerHTML = state.apis.map(a => `
                <div onclick="setActiveApi('${a.id}')" class="flex justify-between items-center p-2 rounded border cursor-pointer ${a.id === state.active_api_id ? 'border-cyan-500 bg-cyan-500/10' : 'border-white/10'}">
                    <span class="text-xs">${a.cloud}</span>
                    <button onclick="deleteApi('${a.id}')" class="text-red-500 px-2 text-xs">Del</button>
                </div>
            `).join('');

            // Content List
            document.getElementById('contentList').innerHTML = state.videos.map(v => `
                <div class="flex justify-between bg-black/40 p-2 rounded text-[10px]">
                    <span class="truncate w-3/4">${v.series} (EP: ${v.episode})</span>
                    <button onclick="deleteVideo('${v.id}')" class="text-red-500">DELETE</button>
                </div>
            `).join('');
        }

        function startUpload() {
            const series = document.getElementById('movieTitle').value;
            const ep = document.getElementById('epNo').value;
            const activeApi = state.apis.find(a => a.id === state.active_api_id);

            if(!series || !ep || !activeApi) return alert("Fill Name/Episode and Select API Account!");

            cloudinary.createUploadWidget({
                cloudName: activeApi.cloud,
                apiKey: activeApi.key,
                uploadSignature: (callback, params) => {
                    fetch('/api/sign', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ params }) })
                    .then(r => r.json()).then(d => callback(d.signature));
                },
                resourceType: 'video'
            }, (err, res) => {
                if (res.event === "success") {
                    fetch('/api/save_video', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ url: res.info.secure_url, series, ep })
                    }).then(() => { alert("Success!"); loadAppData(); });
                }
            }).open();
        }

        async function tryLogin() {
            const pass = document.getElementById('adminPass').value;
            const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ pass }) });
            const data = await res.json();
            if(data.success) { location.reload(); } else { alert("Wrong Password!"); }
        }

        async function saveApi() {
            const cloud = document.getElementById('c_name').value;
            const key = document.getElementById('c_key').value;
            const sec = document.getElementById('c_sec').value;
            await fetch('/api/add_api', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ cloud, key, sec }) });
            loadAppData();
        }

        async function setActiveApi(id) {
            await fetch('/api/set_api', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
            loadAppData();
        }

        async function deleteVideo(id) {
            if(confirm("Delete this video?")) {
                await fetch('/api/del_vid', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
                loadAppData();
            }
        }

        function closeAdmin() { document.getElementById('adminPanel').classList.add('hidden'); }
        async function doLogout() { await fetch('/api/logout'); location.reload(); }

        loadAppData();
    </script>
</body>
</html>
"""

# ================= 3. ব্যাকএন্ড এপিআই লজিক (Python) =================

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

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
    vids = list(video_col.find({}, {'_id': 0}).sort([('series', 1), ('episode', 1)]))
    active = api_col.find_one({"is_active": True})
    return jsonify({
        "apis": apis, 
        "videos": vids, 
        "active_api_id": active['id'] if active else None
    })

@app.route('/api/sign', methods=['POST'])
def sign_api():
    active_api = api_col.find_one({"is_active": True})
    if not active_api: return jsonify({"error": "No API active"}), 400
    params = request.json.get('params', {})
    signature = cloudinary.utils.api_sign_request(params, active_api['secret'])
    return jsonify({"signature": signature})

@app.route('/api/add_api', methods=['POST'])
def add_api():
    data = request.json
    api_col.insert_one({
        "id": str(uuid.uuid4())[:8],
        "cloud": data['cloud'],
        "key": data['key'],
        "secret": data['sec'],
        "is_active": False
    })
    return jsonify({"success": True})

@app.route('/api/set_api', methods=['POST'])
def set_api():
    api_col.update_many({}, {"$set": {"is_active": False}})
    api_col.update_one({"id": request.json['id']}, {"$set": {"is_active": True}})
    return jsonify({"success": True})

@app.route('/api/save_video', methods=['POST'])
def save_video():
    data = request.json
    video_col.insert_one({
        "id": str(uuid.uuid4())[:8],
        "url": data['url'],
        "series": data['series'].strip().upper(),
        "episode": int(data['ep']),
        "likes": 0,
        "created_at": datetime.now()
    })
    return jsonify({"success": True})

@app.route('/api/del_vid', methods=['POST'])
def del_vid():
    video_col.delete_one({"id": request.json['id']})
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
