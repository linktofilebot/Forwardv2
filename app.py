from flask import Flask, render_template_string, request, jsonify, session
from pymongo import MongoClient
import uuid
import secrets
import time
import hashlib
from datetime import datetime
import cloudinary.utils # সিগনেচার তৈরির জন্য অফিসিয়াল লাইব্রেরি

# ================= 1. কনফিগারেশন এবং ডাটাবেস কানেকশন =================
app = Flask(__name__)
app.secret_key = secrets.token_hex(24)

# আপনার MongoDB Atlas URL
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" 
ADMIN_PASS = "admin786"

try:
    client = MongoClient(MONGO_URI)
    db = client['CloudTok_Final_V4']
    api_col = db['apis']      
    video_col = db['videos']  
    print("✓ MongoDB Connected Successfully")
except Exception as e:
    print(f"✗ MongoDB Connection Error: {e}")

# ================= 2. ফ্রন্টএন্ড টেমপ্লেট (HTML/JS) =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudTok Ultimate Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://upload-widget.cloudinary.com/global/all.js"></script>
    <style>
        body { background: #000; color: #fff; font-family: 'Inter', sans-serif; overflow: hidden; }
        .feed-container { height: 100vh; scroll-snap-type: y mandatory; overflow-y: scroll; scrollbar-width: none; }
        .video-card { height: 100vh; scroll-snap-align: start; position: relative; background: #000; display: flex; align-items: center; justify-content: center; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
        video { height: 100%; width: 100%; object-fit: cover; }
        .glass-ui { background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .active-api-border { border: 2px solid #06b6d4 !important; }
        .btn-gradient { background: linear-gradient(45deg, #06b6d4, #3b82f6); }
    </style>
</head>
<body>

    <nav class="fixed top-0 w-full z-50 flex justify-between p-5 bg-gradient-to-b from-black to-transparent">
        <h1 class="text-2xl font-black text-cyan-400 uppercase italic">Cloud<span class="text-white">Tok</span></h1>
        <button onclick="checkAuthAndOpenAdmin()" class="bg-white/10 px-4 py-2 rounded-full text-[10px] font-bold border border-white/20">ADMIN PANEL</button>
    </nav>

    <div id="videoFeed" class="feed-container scrollbar-hide"></div>

    <!-- Admin Login -->
    <div id="loginModal" class="hidden fixed inset-0 z-[100] bg-black/95 flex items-center justify-center p-6">
        <div class="glass-ui p-8 rounded-3xl w-full max-w-sm text-center">
            <h2 class="text-xl font-bold mb-6 text-cyan-400 uppercase">Admin Access</h2>
            <input id="adminPassInput" type="password" placeholder="Password" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-6 text-center outline-none">
            <button onclick="submitLogin()" class="w-full btn-gradient p-4 rounded-xl font-bold uppercase">Unlock</button>
        </div>
    </div>

    <!-- Admin Panel -->
    <div id="adminPanel" class="hidden fixed inset-0 z-[80] bg-black p-4 md:p-8 overflow-y-auto">
        <div class="max-w-6xl mx-auto pb-10">
            <div class="flex justify-between items-center mb-8 border-b border-gray-800 pb-4">
                <h2 class="text-2xl font-black text-cyan-500 uppercase">Control Center</h2>
                <button onclick="location.reload()" class="text-white text-3xl">✕</button>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="space-y-6">
                    <!-- API Settings -->
                    <div class="glass-ui p-6 rounded-3xl border border-gray-800">
                        <h3 class="text-cyan-400 font-bold mb-4 text-xs uppercase">1. Cloudinary API (No Preset)</h3>
                        <div class="grid gap-3 mb-4">
                            <input id="api_cloud" placeholder="Cloud Name" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none">
                            <input id="api_key" placeholder="API Key" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none">
                            <input id="api_secret" placeholder="API Secret" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none">
                        </div>
                        <button onclick="saveApiConfig()" class="w-full bg-cyan-700 p-3 rounded-xl font-bold text-xs uppercase">Add Account</button>
                        <div id="apiListContainer" class="mt-4 space-y-2"></div>
                    </div>

                    <!-- Upload Form -->
                    <div class="glass-ui p-6 rounded-3xl border border-cyan-500/20">
                        <h3 class="text-cyan-400 font-bold mb-4 text-xs uppercase">2. Upload Movie/Episode</h3>
                        <input id="seriesTitle" placeholder="Movie Name" class="w-full bg-black p-4 rounded-xl border border-gray-800 mb-3">
                        <input id="episodeNo" type="number" placeholder="Episode Number" class="w-full bg-black p-4 rounded-xl border border-gray-800 mb-4">
                        <button onclick="startSignedUpload()" class="w-full btn-gradient p-5 rounded-2xl font-black text-xl shadow-lg">🚀 SELECT VIDEO</button>
                    </div>
                </div>

                <div class="glass-ui p-6 rounded-3xl border border-gray-800">
                    <h3 class="text-gray-500 font-bold mb-4 text-xs uppercase">3. Content Management</h3>
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
            feed.innerHTML = appState.videos.map(v => `
                <div class="video-card">
                    <video src="${v.url}" loop autoplay muted playsinline onclick="this.paused?this.play():this.pause()"></video>
                    <div class="absolute right-5 bottom-32 flex flex-col gap-6 text-center z-10">
                        <div onclick="interact('${v.id}', 'like')" class="cursor-pointer">
                            <div class="glass-ui p-4 rounded-full">❤️</div>
                            <span class="text-xs font-bold">${v.likes || 0}</span>
                        </div>
                        <div onclick="addComment('${v.id}')" class="cursor-pointer">
                            <div class="glass-ui p-4 rounded-full">💬</div>
                            <span class="text-xs font-bold">${(v.comments || []).length}</span>
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
            const apiList = document.getElementById('apiListContainer');
            apiList.innerHTML = appState.apis.map(api => `
                <div onclick="switchApi('${api.id}')" class="flex justify-between p-3 rounded-xl border cursor-pointer ${api.id === appState.active_api_id ? 'active-api-border' : 'border-gray-800'}">
                    <span class="text-xs font-bold">${api.cloud}</span>
                    <button onclick="deleteApi('${api.id}')" class="text-red-500 font-bold">✕</button>
                </div>
            `).join('');

            const contentList = document.getElementById('contentListUI');
            contentList.innerHTML = appState.videos.map(v => `
                <div class="flex items-center gap-4 bg-white/5 p-3 rounded-2xl border border-gray-800">
                    <div class="flex-1 overflow-hidden">
                        <p class="font-bold text-cyan-400 text-xs uppercase truncate">${v.series} - EP ${v.episode}</p>
                    </div>
                    <button onclick="deleteVideo('${v.id}')" class="text-red-500 text-[10px] font-bold">DELETE</button>
                </div>
            `).join('');
        }

        // --- অফিসিয়াল সিগনেচার আপলোড মেথড ---
        function startSignedUpload() {
            const series = document.getElementById('seriesTitle').value;
            const ep = document.getElementById('episodeNo').value;
            const activeAPI = appState.apis.find(a => a.id === appState.active_api_id);

            if(!series || !ep || !activeAPI) return alert("Fill Name, Ep and Select API!");

            const widget = cloudinary.createUploadWidget({
                cloudName: activeAPI.cloud,
                apiKey: activeAPI.key,
                uploadSignature: (callback, params) => {
                    fetch('/api/generate_signature', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ params: params })
                    })
                    .then(r => r.json())
                    .then(data => callback(data.signature));
                },
                resourceType: 'video'
            }, (error, result) => {
                if (!error && result && result.event === "success") {
                    fetch('/api/save_video', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ url: result.info.secure_url, series, ep })
                    }).then(() => fetchSystemData());
                }
            });
            widget.open();
        }

        async function interact(id, type) {
            await fetch('/api/interact', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id, type }) });
            fetchSystemData();
        }

        async function addComment(id) {
            const comment = prompt("Enter Comment:");
            if(comment) {
                await fetch('/api/interact', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id, type:'comment', comment }) });
                fetchSystemData();
            }
        }

        async function saveApiConfig() {
            const cloud = document.getElementById('api_cloud').value;
            const key = document.getElementById('api_key').value;
            const secret = document.getElementById('api_secret').value;
            await fetch('/api/add_api', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ cloud, key, secret }) });
            fetchSystemData();
        }

        async function switchApi(id) {
            await fetch('/api/set_api', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
            fetchSystemData();
        }

        async function deleteVideo(id) {
            if(confirm("Delete Video?")) {
                await fetch('/api/delete_video', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ id }) });
                fetchSystemData();
            }
        }

        async function checkAuthAndOpenAdmin() {
            const res = await fetch('/api/auth');
            if((await res.json()).is_auth) document.getElementById('adminPanel').classList.remove('hidden');
            else document.getElementById('loginModal').classList.remove('hidden');
            fetchSystemData();
        }

        async function submitLogin() {
            const pass = document.getElementById('adminPassInput').value;
            const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ pass }) });
            if((await res.json()).success) location.reload(); else alert("Wrong!");
        }

        fetchSystemData();
    </script>
</body>
</html>
"""

# ================= 3. ব্যাকএন্ড লজিক (Python) =================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/generate_signature', methods=['POST'])
def generate_signature():
    """ ক্লাউডিনারি অফিসিয়াল সিগনেচার জেনারেটর """
    if not session.get('admin_session'): return jsonify({"error": "No Auth"}), 401
    
    active_api = api_col.find_one({"is_active": True})
    params = request.json.get('params', {})
    
    # Cloudinary Library ব্যবহার করে নিখুঁত সিগনেচার তৈরি
    signature = cloudinary.utils.api_sign_request(params, active_api['secret'])
    return jsonify({"signature": signature})

@app.route('/api/login', methods=['POST'])
def login():
    if request.json.get('pass') == ADMIN_PASS:
        session['admin_session'] = True
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/auth')
def auth():
    return jsonify({"is_auth": session.get('admin_session', False)})

@app.route('/api/get_full_data')
def get_data():
    apis = list(api_col.find({}, {'_id': 0}))
    vids = list(video_col.find({}, {'_id': 0}).sort('_id', -1))
    active = api_col.find_one({"is_active": True})
    return jsonify({"apis": apis, "videos": vids, "active_api_id": active['id'] if active else None})

@app.route('/api/add_api', methods=['POST'])
def add_api():
    if not session.get('admin_session'): return 401
    data = request.json
    api_col.insert_one({"id": str(uuid.uuid4())[:8], "cloud": data['cloud'], "key": data['key'], "secret": data['secret'], "is_active": False})
    return jsonify({"success": True})

@app.route('/api/set_api', methods=['POST'])
def set_api():
    api_col.update_many({}, {"$set": {"is_active": False}})
    api_col.update_one({"id": request.json['id']}, {"$set": {"is_active": True}})
    return jsonify({"success": True})

@app.route('/api/save_video', methods=['POST'])
def save_video():
    if not session.get('admin_session'): return 401
    data = request.json
    video_col.insert_one({"id": str(uuid.uuid4())[:8], "url": data['url'], "series": data['series'], "episode": data['ep'], "likes": 0, "comments": []})
    return jsonify({"success": True})

@app.route('/api/interact', methods=['POST'])
def interact():
    data = request.json
    if data['type'] == 'like':
        video_col.update_one({"id": data['id']}, {"$inc": {"likes": 1}})
    elif data['type'] == 'comment':
        video_col.update_one({"id": data['id']}, {"$push": {"comments": data['comment']}})
    return jsonify({"success": True})

@app.route('/api/delete_video', methods=['POST'])
def delete_video():
    video_col.delete_one({"id": request.json['id']})
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
