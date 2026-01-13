from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
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
    user_col = db['users'] # ইউজার কালেকশন যোগ করা হয়েছে
    print("✓ MongoDB Connected Successfully")
except Exception as e:
    print(f"✗ MongoDB Connection Error: {e}")

# পাসওয়ার্ড হ্যাশিং ফাংশন
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

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
        body { background: #000; color: #fff; font-family: 'Inter', sans-serif; overflow: hidden; margin: 0; }
        
        .feed-container { 
            height: 100vh; 
            scroll-snap-type: y mandatory; 
            overflow-y: scroll; 
            scrollbar-width: none; 
            max-width: 500px; 
            margin: 0 auto; 
            position: relative;
            background: #000;
        }
        @media (max-width: 600px) { .feed-container { max-width: 100%; } }

        .video-card { height: 100vh; scroll-snap-align: start; position: relative; background: #000; display: flex; align-items: center; justify-content: center; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
        video { height: 100%; width: 100%; object-fit: cover; }
        .glass-ui { background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .active-api { border: 2px solid #06b6d4 !important; background: rgba(6, 182, 212, 0.15); }
        .btn-grad { background: linear-gradient(45deg, #06b6d4, #3b82f6); transition: 0.3s; }
        .btn-grad:active { transform: scale(0.95); }
        
        .video-progress-container { position: absolute; bottom: 90px; left: 5%; width: 90%; height: 6px; background: rgba(255,255,255,0.2); cursor: pointer; z-index: 60; border-radius: 10px; }
        .video-progress-bar { height: 100%; background: #06b6d4; width: 0%; border-radius: 10px; transition: width 0.1s linear; position: relative; }
        .time-info { position: absolute; top: -20px; right: 0; font-size: 10px; color: #06b6d4; font-weight: bold; }
        
        .bottom-nav { position: fixed; bottom: 0; width: 100%; max-width: 500px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.85); display: flex; justify-content: space-around; padding: 15px; z-index: 70; border-top: 1px solid rgba(255,255,255,0.1); }
        
        .skip-area { position: absolute; top: 0; height: 100%; width: 30%; z-index: 40; }
        .skip-left { left: 0; }
        .skip-right { right: 0; }
        
        .explore-grid { display: grid; grid-template-cols: repeat(2, 1fr); gap: 10px; padding: 20px; padding-top: 80px; padding-bottom: 100px; }

        .heart-animation {
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            font-size: 80px; color: #ff2d55; pointer-events: none;
            animation: heartFade 0.8s ease-out forwards; z-index: 100; text-shadow: 0 0 20px rgba(0,0,0,0.5);
        }
        @keyframes heartFade {
            0% { opacity: 0; transform: translate(-50%, -50%) scale(0.3); }
            50% { opacity: 1; transform: translate(-50%, -50%) scale(1.2); }
            100% { opacity: 0; transform: translate(-50%, -50%) scale(1.5); }
        }

        /* Profile Nav Image Style */
        .nav-avatar { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; border: 1px solid #06b6d4; }
    </style>
</head>
<body>

    <nav class="fixed top-0 w-full max-width-[500px] z-50 flex justify-between p-5 bg-gradient-to-b from-black/80 to-transparent">
        <h1 onclick="loadHome()" class="text-2xl font-black italic text-cyan-400 uppercase tracking-tighter cursor-pointer">Cloud<span class="text-white">Tok</span></h1>
    </nav>

    <div id="videoFeed" class="feed-container scrollbar-hide"></div>

    <div class="bottom-nav">
        <button onclick="loadHome()" class="flex flex-col items-center">
            <span class="text-2xl">🏠</span>
            <span class="text-[9px] font-bold">HOME</span>
        </button>
        <button onclick="loadExplore()" class="flex flex-col items-center">
            <span class="text-2xl">🔍</span>
            <span class="text-[9px] font-bold">EXPLORE</span>
        </button>
        <button onclick="handleProfileClick()" class="flex flex-col items-center">
            <div id="navProfileIcon">
                <span class="text-2xl">👤</span>
            </div>
            <span class="text-[9px] font-bold">PROFILE</span>
        </button>
    </div>

    <!-- User Login Modal -->
    <div id="userLoginModal" class="hidden fixed inset-0 z-[110] bg-black/95 flex items-center justify-center p-6">
        <div class="glass-ui p-8 rounded-3xl w-full max-sm:max-w-xs text-center">
            <h2 class="text-2xl font-black mb-6 text-cyan-400">LOGIN</h2>
            <input id="uPhone" type="text" placeholder="Number" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-4 outline-none">
            <input id="uPass" type="password" placeholder="Password" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-6 outline-none">
            <button onclick="tryUserLogin()" class="w-full btn-grad p-4 rounded-xl font-bold uppercase">Login</button>
            <p class="mt-4 text-xs">No account? <span class="text-cyan-400 cursor-pointer" onclick="openRegister()">Register</span></p>
            <button onclick="closeModal('userLoginModal')" class="mt-4 text-gray-500 text-xs">Close</button>
        </div>
    </div>

    <!-- User Register Modal -->
    <div id="userRegModal" class="hidden fixed inset-0 z-[110] bg-black/95 flex items-center justify-center p-6">
        <div class="glass-ui p-8 rounded-3xl w-full max-sm:max-w-xs text-center">
            <h2 class="text-2xl font-black mb-6 text-cyan-400">REGISTER</h2>
            <input id="regName" type="text" placeholder="Full Name" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-4 outline-none">
            <input id="regPhone" type="text" placeholder="Number" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-4 outline-none">
            <input id="regPass" type="password" placeholder="Password" class="w-full bg-white/5 p-4 rounded-xl border border-white/10 mb-6 outline-none">
            <button onclick="tryUserRegister()" class="w-full btn-grad p-4 rounded-xl font-bold uppercase">Join Now</button>
            <p class="mt-4 text-xs">Have account? <span class="text-cyan-400 cursor-pointer" onclick="openLogin()">Login</span></p>
            <button onclick="closeModal('userRegModal')" class="mt-4 text-gray-500 text-xs">Close</button>
        </div>
    </div>

    <!-- User Profile Modal -->
    <div id="profileModal" class="hidden fixed inset-0 z-[110] bg-black/95 flex items-center justify-center p-6">
        <div class="glass-ui p-8 rounded-3xl w-full max-sm:max-w-xs text-center">
            <img id="profImg" src="" class="w-24 h-24 rounded-full mx-auto border-4 border-cyan-400 object-cover mb-4">
            <h2 id="profName" class="text-xl font-black text-white mb-2"></h2>
            <p id="profPhone" class="text-gray-400 text-sm mb-6"></p>
            
            <input id="newAvatar" placeholder="Profile Image URL" class="w-full bg-white/5 p-3 rounded-xl border border-white/10 mb-4 text-xs">
            <button onclick="updateAvatar()" class="w-full bg-cyan-600 p-3 rounded-xl font-bold text-xs uppercase mb-3">Update Image</button>
            <button onclick="doUserLogout()" class="w-full bg-red-600 p-3 rounded-xl font-bold text-xs uppercase">Logout</button>
            <button onclick="closeModal('profileModal')" class="mt-4 text-gray-500 text-xs">Close</button>
        </div>
    </div>

    <!-- Admin Login Modal -->
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
                <button onclick="closeModal('commentModal')" class="text-white text-xl">✖</button>
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
                    <button onclick="location.href='/'" class="text-white text-3xl">✖</button>
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
                                    <button onclick="initUpload()" class="flex-1 btn-grad p-2 rounded-lg font-bold text-xs">🚀 UPLOAD VIDEO</button>
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
        let appState = { apis: [], videos: [], active_id: null, user: null };
        let currentMode = 'home'; 
        let filteredVideos = [];
        let observer;

        window.addEventListener('load', function() {
            checkUserStatus(); // ইউজারের অবস্থা চেক করা
            if(window.location.pathname.includes('/admin')) {
                openAuth();
            }
        });

        async function checkUserStatus() {
            const res = await fetch('/api/user/status');
            const data = await res.json();
            appState.user = data.user;
            updateNavProfile();
        }

        function updateNavProfile() {
            const iconContainer = document.getElementById('navProfileIcon');
            if (appState.user) {
                const avatar = appState.user.profile_img || `https://ui-avatars.com/api/?name=${appState.user.name}&background=random&color=fff`;
                iconContainer.innerHTML = `<img src="${avatar}" class="nav-avatar">`;
            } else {
                iconContainer.innerHTML = `<span class="text-2xl">👤</span>`;
            }
        }

        function handleProfileClick() {
            if (appState.user) {
                document.getElementById('profName').innerText = appState.user.name;
                document.getElementById('profPhone').innerText = appState.user.phone;
                document.getElementById('profImg').src = appState.user.profile_img || `https://ui-avatars.com/api/?name=${appState.user.name}&background=random&color=fff`;
                document.getElementById('profileModal').classList.remove('hidden');
            } else {
                openLogin();
            }
        }

        async function tryUserRegister() {
            const name = document.getElementById('regName').value;
            const phone = document.getElementById('regPhone').value;
            const pass = document.getElementById('regPass').value;
            if(!name || !phone || !pass) return alert("Fill all fields");

            const res = await fetch('/api/user/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name, phone, pass })
            });
            const data = await res.json();
            if(data.success) { alert("Registration Success! Login Now."); openLogin(); }
            else alert(data.error);
        }

        async function tryUserLogin() {
            const phone = document.getElementById('uPhone').value;
            const pass = document.getElementById('uPass').value;
            const res = await fetch('/api/user/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone, pass })
            });
            const data = await res.json();
            if(data.success) { location.reload(); }
            else alert("Invalid Login!");
        }

        async function updateAvatar() {
            const url = document.getElementById('newAvatar').value;
            if(!url) return;
            const res = await fetch('/api/user/update_img', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url })
            });
            if((await res.json()).success) { alert("Profile Updated!"); location.reload(); }
        }

        async function doUserLogout() {
            await fetch('/api/user/logout');
            location.reload();
        }

        function openLogin() {
            closeModal('userRegModal');
            document.getElementById('userLoginModal').classList.remove('hidden');
        }

        function openRegister() {
            closeModal('userLoginModal');
            document.getElementById('userRegModal').classList.remove('hidden');
        }

        async function refreshData() {
            const res = await fetch('/api/data');
            appState = {...appState, ...await res.json()};

            const urlParams = new URLSearchParams(window.location.search);
            const vId = urlParams.get('v');
            if(vId && currentMode === 'home') {
                const specificVid = appState.videos.find(v => v.id === vId);
                if(specificVid) {
                    filteredVideos = [specificVid, ...appState.videos.filter(v => v.id !== vId)];
                    renderFeed();
                    return;
                }
            }

            if(currentMode === 'home') loadHome();
            if(!document.getElementById('adminPanel').classList.contains('hidden')) renderAdmin();
        }

        function loadHome() {
            currentMode = 'home';
            filteredVideos = appState.videos.filter(v => parseInt(v.episode) === 1);
            renderFeed();
            document.getElementById('videoFeed').scrollTo(0,0);
        }

        function loadExplore() {
            currentMode = 'explore';
            const feed = document.getElementById('videoFeed');
            const seriesList = [...new Map(appState.videos.map(item => [item.series, item])).values()];
            
            feed.innerHTML = `
                <div class="explore-grid">
                    ${seriesList.map(s => `
                        <div onclick="loadSeries('${s.series}')" class="relative group cursor-pointer overflow-hidden rounded-xl border border-white/10">
                            <img src="${s.poster}" class="w-full aspect-[2/3] object-cover group-hover:scale-110 transition">
                            <div class="absolute bottom-0 p-2 bg-black/60 w-full text-[10px] font-bold truncate">${s.series}</div>
                        </div>
                    `).join('')}
                </div>
            `;
            feed.scrollTo(0,0);
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
                    
                    <video id="vid-${v.id}" src="${v.url}" loop playsinline 
                        onclick="togglePlay('vid-${v.id}')"
                        ondblclick="handleDoubleTap(event, '${v.id}')"
                        ontimeupdate="updateProgress('${v.id}')"></video>
                    
                    <div class="absolute right-5 bottom-32 flex flex-col gap-5 text-center z-50">
                        <div onclick="toggleMute('vid-${v.id}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl" id="vol-icon-vid-${v.id}">🔊</div>
                        </div>
                        <div onclick="handleInteraction('${v.id}', 'like')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl">❤️</div>
                            <span class="text-[10px] font-bold" id="like-count-${v.id}">${v.likes || 0}</span>
                        </div>
                        <div onclick="openComments('${v.id}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl">💬</div>
                            <span class="text-[10px] font-bold">${(v.comments || []).length}</span>
                        </div>
                        <div onclick="shareVideo('${v.id}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl">🔗</div>
                            <span class="text-[10px] font-bold uppercase">Share</span>
                        </div>
                        <div onclick="downloadVideo('${v.url}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl bg-green-500/20">⬇️</div>
                            <span class="text-[10px] font-bold uppercase">Save</span>
                        </div>
                        <div onclick="loadSeries('${v.series}')" class="cursor-pointer">
                            <div class="glass-ui p-3 rounded-full text-xl bg-cyan-500/50 border-cyan-400 border">🎬</div>
                            <span class="text-[10px] font-bold text-cyan-400">PARTS</span>
                        </div>
                    </div>

                    <div class="absolute bottom-24 left-6 right-20 z-10 pointer-events-none">
                        <div class="flex items-center gap-3 mb-2">
                            <img src="${v.poster || 'https://via.placeholder.com/150'}" class="w-12 h-12 rounded-lg border border-white/20 object-cover shadow-lg">
                            <div>
                                <h3 class="text-cyan-400 font-black text-xl italic uppercase leading-none">${v.series}</h3>
                                <p class="text-white font-bold text-[10px] opacity-90">Episode: ${v.episode}</p>
                            </div>
                        </div>
                    </div>

                    <div class="video-progress-container" onclick="seekVideo(event, 'vid-${v.id}')">
                        <div id="progress-${v.id}" class="video-progress-bar">
                            <span id="time-${v.id}" class="time-info">00:00</span>
                        </div>
                    </div>
                </div>
            `).join('');

            initObserver();
        }

        function handleDoubleTap(e, id) {
            handleInteraction(id, 'like');
            const heart = document.createElement('div');
            heart.innerHTML = '❤️';
            heart.className = 'heart-animation';
            e.target.parentElement.appendChild(heart);
            setTimeout(() => heart.remove(), 800);
        }

        function initObserver() {
            if(observer) observer.disconnect();
            observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    const video = entry.target.querySelector('video');
                    if (entry.isIntersecting) { video.play().catch(e => {}); } 
                    else { video.pause(); video.currentTime = 0; }
                });
            }, { threshold: 0.8 });
            document.querySelectorAll('.video-card').forEach(card => observer.observe(card));
        }

        function seekVideo(e, videoId) {
            const video = document.getElementById(videoId);
            const rect = e.currentTarget.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const clickedValue = x / rect.width;
            video.currentTime = clickedValue * video.duration;
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

        function shareVideo(id) {
            const mainUrl = window.location.origin + "/?v=" + id;
            navigator.clipboard.writeText(mainUrl);
            alert("Main Site Link Copied!");
        }

        function downloadVideo(url) {
            const downloadUrl = url.replace("/upload/", "/upload/fl_attachment/");
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = "CloudTok_Video.mp4";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }

        function updateProgress(id) {
            const v = document.getElementById('vid-' + id);
            const bar = document.getElementById('progress-' + id);
            const timeTxt = document.getElementById('time-' + id);
            if(v && bar) {
                const percent = (v.currentTime / v.duration) * 100;
                bar.style.width = percent + '%';
                
                let m = Math.floor(v.currentTime / 60);
                let s = Math.floor(v.currentTime % 60);
                let durM = Math.floor(v.duration / 60) || 0;
                let durS = Math.floor(v.duration % 60) || 0;
                timeTxt.innerText = `${m}:${s < 10 ? '0'+s : s} / ${durM}:${durS < 10 ? '0'+durS : durS}`;
            }
        }

        function renderAdmin() {
            document.getElementById('apiList').innerHTML = appState.apis.map(a => `
                <div onclick="switchActiveApi('${a.id}')" class="flex justify-between items-center p-3 rounded-xl border cursor-pointer ${a.id === appState.active_id ? 'active-api shadow-lg' : 'border-gray-800'}">
                    <span class="text-xs font-bold">${a.cloud}</span>
                    <button onclick="delApi('${a.id}')" class="text-red-500 font-bold px-2">✖</button>
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

        async function handleInteraction(id, type, commentText = "") {
            const res = await fetch('/api/interaction', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, type, comment: commentText })
            });
            if(type === 'like' && document.getElementById('like-count-'+id)) {
                let el = document.getElementById('like-count-'+id);
                el.innerText = parseInt(el.innerText) + 1;
            }
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
            const data = await res.json();
            if(data.is_auth) {
                document.getElementById('adminPanel').classList.remove('hidden');
            } else {
                document.getElementById('loginModal').classList.remove('hidden');
            }
            refreshData();
        }

        async function tryLogin() {
            const pass = document.getElementById('adminPass').value;
            const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ pass }) });
            if((await res.json()).success) { location.reload(); } else { alert("Wrong Password!"); }
        }

        async function doLogout() {
            await fetch('/api/logout');
            location.href = '/';
        }

        function closeModal(id) { 
            document.getElementById(id).classList.add('hidden'); 
            if(id === 'loginModal' && window.location.pathname.includes('/admin')) window.location.href = '/';
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
                    }).then(() => { refreshData(); alert("Uploaded!"); });
                }
            }).open();
        }

        refreshData();
    </script>
</body>
</html>
"""

# ================= 3. ব্যাকএন্ড এপিআই লজিক =================

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/admin', strict_slashes=False)
def admin_page():
    return render_template_string(HTML_TEMPLATE)

# --- ইউজার ম্যানেজমেন্ট সিস্টেম ---

@app.route('/api/user/register', methods=['POST'])
def user_register():
    data = request.json
    if user_col.find_one({"phone": data['phone']}):
        return jsonify({"success": False, "error": "Phone number already exists!"})
    
    user_col.insert_one({
        "id": str(uuid.uuid4())[:8],
        "name": data['name'],
        "phone": data['phone'],
        "password": hash_password(data['pass']),
        "profile_img": "",
        "created_at": datetime.now()
    })
    return jsonify({"success": True})

@app.route('/api/user/login', methods=['POST'])
def user_login():
    data = request.json
    u = user_col.find_one({"phone": data['phone'], "password": hash_password(data['pass'])})
    if u:
        session['user_id'] = u['id']
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/user/status')
def user_status():
    uid = session.get('user_id')
    u = user_col.find_one({"id": uid}, {"_id": 0, "password": 0}) if uid else None
    return jsonify({"user": u})

@app.route('/api/user/logout')
def user_logout():
    session.pop('user_id', None)
    return jsonify({"success": True})

@app.route('/api/user/update_img', methods=['POST'])
def update_img():
    uid = session.get('user_id')
    if not uid: return jsonify({"success": False}), 401
    user_col.update_one({"id": uid}, {"$set": {"profile_img": request.json['url']}})
    return jsonify({"success": True})

# --- ভিডিও ও এডমিন এপিআই ---

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
