from flask import Flask, render_template_string, request, jsonify, session
from pymongo import MongoClient
import os
import uuid
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(24)

# ================= MongoDB Configuration =================
# আপনার MongoDB Atlas URL এখানে দিন
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" 

try:
    client = MongoClient(MONGO_URI)
    db = client['CloudTok_Final_DB']
    api_col = db['apis']     # API কালেকশন
    video_col = db['videos'] # ভিডিও কালেকশন
    print("✓ MongoDB Connected Successfully")
except Exception as e:
    print(f"✗ MongoDB Connection Error: {e}")

# এডমিন প্যানেল পাসওয়ার্ড
ADMIN_PASS = "admin786"

# ================= Full Combined Template (HTML/JS/CSS) =================
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

    <!-- Top Navigation -->
    <nav class="fixed top-0 w-full z-50 flex justify-between p-5 bg-gradient-to-b from-black to-transparent">
        <h1 class="text-2xl font-black italic tracking-tighter text-cyan-400 uppercase">Cloud<span class="text-white">Tok</span></h1>
        <button onclick="checkAuthAndOpenAdmin()" class="bg-white/10 backdrop-blur-md px-6 py-2 rounded-full text-xs font-bold border border-white/20 hover:bg-cyan-500 transition">ADMIN DASHBOARD</button>
    </nav>

    <!-- Main Content: Vertical Video Feed -->
    <div id="videoFeed" class="feed-container scrollbar-hide">
        <!-- Videos will be rendered here -->
    </div>

    <!-- Modal: Admin Login -->
    <div id="loginModal" class="hidden fixed inset-0 z-[100] bg-black/95 flex items-center justify-center p-6">
        <div class="glass-ui p-8 rounded-3xl w-full max-w-sm text-center shadow-2xl">
            <h2 class="text-2xl font-black mb-6 text-cyan-400 uppercase italic tracking-widest">Admin Access</h2>
            <input id="adminPassInput" type="password" placeholder="Enter Admin Password" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-6 outline-none focus:border-cyan-500 text-center text-lg">
            <button onclick="submitLogin()" class="w-full btn-gradient p-4 rounded-xl font-bold uppercase tracking-widest shadow-lg">Unlock Dashboard</button>
            <button onclick="closeAllModals()" class="mt-4 text-gray-500 text-xs hover:text-white transition uppercase">Cancel</button>
        </div>
    </div>

    <!-- Modal: Full Admin Dashboard -->
    <div id="adminPanel" class="hidden fixed inset-0 z-[80] bg-black p-4 md:p-8 overflow-y-auto">
        <div class="max-w-6xl mx-auto pb-20">
            <div class="flex justify-between items-center mb-10 border-b border-gray-800 pb-5">
                <h2 class="text-3xl font-black text-cyan-500 uppercase italic">Control Center</h2>
                <div class="flex gap-4">
                    <button onclick="performLogout()" class="text-red-500 font-bold text-xs uppercase underline">Logout</button>
                    <button onclick="closeAllModals()" class="text-white text-3xl hover:rotate-90 transition">✕</button>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-10">
                <!-- Column Left: API Management -->
                <div class="space-y-8">
                    <div class="glass-ui p-6 rounded-3xl shadow-xl border border-gray-800">
                        <h3 class="text-cyan-400 font-bold mb-6 uppercase text-xs tracking-widest border-b border-white/5 pb-2">1. Add Unlimited Cloudinary API</h3>
                        <div class="grid grid-cols-2 gap-4 mb-4">
                            <input id="api_cloud" placeholder="Cloud Name" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none focus:border-cyan-500">
                            <input id="api_key" placeholder="API Key" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none focus:border-cyan-500">
                        </div>
                        <div class="grid grid-cols-2 gap-4 mb-4">
                            <input id="api_secret" placeholder="API Secret" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none focus:border-cyan-500">
                            <input id="api_preset" placeholder="Upload Preset" class="bg-black p-3 rounded-xl border border-gray-800 text-sm outline-none focus:border-cyan-500">
                        </div>
                        <button onclick="saveApiConfig()" class="w-full bg-cyan-700 p-4 rounded-xl font-bold text-xs uppercase tracking-widest hover:bg-cyan-600 transition">Save API Connection</button>
                        
                        <div class="mt-8">
                            <p class="text-[10px] text-gray-500 font-bold mb-4 uppercase tracking-widest">Select API to use for Upload:</p>
                            <div id="apiListContainer" class="space-y-3 max-h-60 overflow-y-auto pr-2 scrollbar-hide">
                                <!-- API List items -->
                            </div>
                        </div>
                    </div>

                    <div class="glass-ui p-6 rounded-3xl shadow-xl border border-cyan-500/10">
                        <h3 class="text-cyan-400 font-bold mb-6 uppercase text-xs tracking-widest border-b border-white/5 pb-2">2. Upload Video Episode</h3>
                        <div class="flex gap-3 mb-6">
                            <input id="seriesTitle" placeholder="Series Name (e.g. My Drama)" class="w-2/3 bg-black p-4 rounded-xl border border-gray-800 outline-none focus:border-cyan-500">
                            <input id="episodeNo" type="number" placeholder="Ep." class="w-1/3 bg-black p-4 rounded-xl border border-gray-800 outline-none focus:border-cyan-500">
                        </div>
                        
                        <!-- Progress Indicator -->
                        <div id="progressBox" class="hidden mb-6 p-5 rounded-2xl bg-cyan-950/30 border border-cyan-500/30">
                            <div class="flex justify-between mb-2">
                                <span id="percentText" class="text-cyan-400 font-bold text-[10px] uppercase">Uploading Data: 0%</span>
                            </div>
                            <div class="w-full bg-gray-800 h-2 rounded-full overflow-hidden shadow-inner">
                                <div id="progressFillUI" class="bg-cyan-500 h-full w-0 shadow-[0_0_15px_#06b6d4] transition-all"></div>
                            </div>
                        </div>

                        <button onclick="initCloudinaryUpload()" class="w-full bg-white text-black p-5 rounded-2xl font-black text-xl hover:scale-[1.02] transition transform active:scale-95 shadow-2xl">
                            🚀 START UPLOAD
                        </button>
                    </div>
                </div>

                <!-- Column Right: Content Manager -->
                <div class="glass-ui p-6 rounded-3xl shadow-xl border border-gray-800">
                    <h3 class="text-gray-500 font-bold mb-6 uppercase text-xs tracking-widest border-b border-white/5 pb-2">3. Manage Uploaded Episodes</h3>
                    <div id="contentListUI" class="space-y-4 max-h-[700px] overflow-y-auto pr-3 scrollbar-hide">
                        <!-- Videos List -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let appState = { apis: [], videos: [], active_api_id: null };

        // --- Core Data Logic ---
        async function fetchSystemData() {
            const res = await fetch('/api/get_full_data');
            appState = await res.json();
            renderVideoFeed();
            if(!document.getElementById('adminPanel').classList.contains('hidden')) renderAdminDashboard();
        }

        // --- UI Rendering ---
        function renderVideoFeed() {
            const feed = document.getElementById('videoFeed');
            if(appState.videos.length === 0) {
                feed.innerHTML = `<div class="h-screen flex items-center justify-center opacity-30 tracking-widest uppercase text-xs">No episodes available.</div>`;
                return;
            }
            feed.innerHTML = appState.videos.map(v => `
                <div class="video-card">
                    <video src="${v.url}" loop autoplay muted playsinline onclick="this.paused?this.play():this.pause()"></video>
                    
                    <div class="absolute right-5 bottom-32 flex flex-col gap-6 text-center z-10">
                        <div onclick="handleInteraction('${v.id}', 'like')" class="cursor-pointer group">
                            <div class="glass-ui p-4 rounded-full mb-1 group-active:scale-150 transition shadow-lg">❤️</div>
                            <span class="text-xs font-bold">${v.likes || 0}</span>
                        </div>
                        <div onclick="addCommentPrompt('${v.id}')" class="cursor-pointer">
                            <div class="glass-ui p-4 rounded-full mb-1">💬</div>
                            <span class="text-xs font-bold">${(v.comments || []).length}</span>
                        </div>
                        <div class="cursor-pointer">
                            <div class="glass-ui p-4 rounded-full mb-1">🔗</div>
                            <span class="text-[10px] uppercase font-bold tracking-tighter">Share</span>
                        </div>
                    </div>

                    <div class="absolute bottom-12 left-6 right-20 z-10 pointer-events-none drop-shadow-2xl">
                        <h3 class="text-cyan-400 font-black text-4xl italic uppercase tracking-tighter drop-shadow-2xl">${v.series}</h3>
                        <p class="text-white font-bold text-xl opacity-90">Episode: ${v.episode}</p>
                    </div>
                </div>
            `).join('');
        }

        function renderAdminDashboard() {
            // API Selection List
            const apiContainer = document.getElementById('apiListContainer');
            apiContainer.innerHTML = appState.apis.map(api => `
                <div class="flex items-center justify-between p-4 rounded-2xl border transition ${api.id === appState.active_api_id ? 'active-api-border shadow-[0_0_15px_rgba(6,182,212,0.2)]' : 'border-gray-800 bg-black hover:border-gray-700'}">
                    <div onclick="switchActiveApi('${api.id}')" class="cursor-pointer flex-1">
                        <p class="font-bold text-sm text-white">${api.cloud}</p>
                        <p class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Key: ${api.key.substring(0,8)}... | Preset: ${api.preset}</p>
                    </div>
                    <button onclick="removeApiConfig('${api.id}')" class="text-red-500 font-black text-xs hover:scale-125 transition ml-4">✕</button>
                </div>
            `).join('');

            // Content Management
            const contentContainer = document.getElementById('contentListUI');
            contentContainer.innerHTML = appState.videos.map(v => `
                <div class="flex items-center gap-4 bg-gray-900/40 p-3 rounded-2xl border border-gray-800 hover:border-gray-600 transition">
                    <video src="${v.url}" class="w-16 h-20 object-cover rounded-xl bg-black border border-gray-700 shadow-lg"></video>
                    <div class="flex-1 overflow-hidden">
                        <p class="font-bold text-cyan-400 text-sm truncate uppercase tracking-tighter">${v.series}</p>
                        <p class="text-[10px] text-gray-500 font-bold uppercase">Episode No: ${v.episode}</p>
                    </div>
                    <button onclick="removeEpisode('${v.id}')" class="bg-red-500/10 text-red-500 p-3 rounded-xl hover:bg-red-500 hover:text-white transition">✕</button>
                </div>
            `).join('');
        }

        // --- Auth & Navigation ---
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
            const data = await res.json();
            if(data.success) {
                location.reload();
            } else {
                alert("Incorrect Admin Password!");
            }
        }

        async function performLogout() {
            await fetch('/api/admin_logout');
            location.reload();
        }

        function closeAllModals() {
            document.getElementById('loginModal').classList.add('hidden');
            document.getElementById('adminPanel').classList.add('hidden');
        }

        // --- API & Content Actions ---
        async function saveApiConfig() {
            const cloud = document.getElementById('api_cloud').value;
            const key = document.getElementById('api_key').value;
            const secret = document.getElementById('api_secret').value;
            const preset = document.getElementById('api_preset').value;

            if(!cloud || !key || !secret || !preset) return alert("All API fields are mandatory!");

            await fetch('/api/add_api_config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ cloud, key, secret, preset })
            });
            fetchSystemData();
            // Clear inputs
            document.getElementById('api_cloud').value = '';
            document.getElementById('api_key').value = '';
            document.getElementById('api_secret').value = '';
            document.getElementById('api_preset').value = '';
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
            if(!confirm("Are you sure you want to delete this API?")) return;
            await fetch('/api/delete_api_config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id })
            });
            fetchSystemData();
        }

        // --- UPLOAD LOGIC (USE SELECTED API) ---
        function initCloudinaryUpload() {
            const activeAPI = appState.apis.find(a => a.id === appState.active_api_id);
            const series = document.getElementById('seriesTitle').value;
            const ep = document.getElementById('episodeNo').value;

            if(!activeAPI) return alert("Critical: No Active API selected! Please add and click an API from the list.");
            if(!series || !ep) return alert("Series name and episode number are required.");

            // উইজেট কনফিগারেশন - ইউজার দ্বারা সিলেক্ট করা API সরাসরি ব্যবহার হবে
            const myWidget = cloudinary.createUploadWidget({
                cloudName: activeAPI.cloud,
                uploadPreset: activeAPI.preset,
                resourceType: 'video',
                multiple: false
            }, async (error, result) => {
                const progBox = document.getElementById('progressBox');
                const progUI = document.getElementById('progressFillUI');
                const progText = document.getElementById('percentText');

                if (result.event === "upload-progress") {
                    progBox.classList.remove('hidden');
                    let progressValue = Math.round(result.info.progress);
                    progText.innerText = `Uploading Episode Content: ${progressValue}%`;
                    progUI.style.width = `${progressValue}%`;
                }

                if (!error && result && result.event === "success") {
                    await fetch('/api/save_episode_meta', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ 
                            url: result.info.secure_url, 
                            series: series, 
                            ep: ep 
                        })
                    });
                    location.reload();
                }
            });

            myWidget.open();
        }

        async function removeEpisode(id) {
            if(!confirm("Delete this episode permanently?")) return;
            await fetch('/api/delete_episode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id })
            });
            fetchSystemData();
        }

        async function handleInteraction(id, type, comment="") {
            await fetch('/api/video_interaction', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, type, comment })
            });
            fetchSystemData();
        }

        function addCommentPrompt(id) {
            const msg = prompt("Enter your comment:");
            if(msg) handleInteraction(id, 'comment', msg);
        }

        // Initialize App
        fetchSystemData();
    </script>
</body>
</html>
"""

# ================= Backend Control API Logic =================

@app.route('/')
def main_index():
    return render_template_string(HTML_TEMPLATE)

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
    
    # সক্রিয় API নির্বাচন করার লজিক (ডাটাবেস থেকে চেক করা)
    active_entry = api_col.find_one({"is_active": True})
    active_id = active_entry['id'] if active_entry else (all_apis[0]['id'] if all_apis else None)
    
    return jsonify({
        "apis": all_apis,
        "videos": all_videos,
        "active_api_id": active_id
    })

# --- Admin Shielded Endpoints ---

@app.route('/api/add_api_config', methods=['POST'])
def add_api_config():
    if not session.get('admin_session'): return jsonify({"error": "unauthorized"}), 401
    data = request.json
    new_entry = {
        "id": str(uuid.uuid4())[:8],
        "cloud": data['cloud'],
        "key": data['key'],
        "secret": data['secret'],
        "preset": data['preset'],
        "is_active": False
    }
    api_col.insert_one(new_entry)
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
        "comments": []
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
    elif data['type'] == 'comment':
        video_col.update_one({"id": data['id']}, {"$push": {"comments": data['comment']}})
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
