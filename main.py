import os
import sys
import subprocess
import re

# --- ১. অটোমেটিক লাইব্রেরি ইনস্টল ---
def install_requirements():
    required = ['flask', 'pymongo', 'dnspython', 'flask-admin', 'wtforms', 'gunicorn']
    for lib in required:
        try:
            __import__(lib.replace('-', '_'))
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

install_requirements()

from flask import Flask, render_template_string, request, session, redirect, url_for
from pymongo import MongoClient
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.pymongo import ModelView
from wtforms import form, fields

# --- ২. কনফিগারেশন ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'MY_SUPER_SECRET_KEY_123')
app.config['FLASK_ADMIN_TEMPLATE_MODE'] = 'bootstrap3'

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# ডাটাবেস কানেকশন (আপনার দেওয়া URI)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://tmlbdmovies:tmlbd198j@cluster0.op4v2d8.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['shorts_app_db'] 
videos_col = db['videos']

# --- ৩. সাহায্যকারী ফাংশন (URL Parser) ---
def get_video_type(url):
    if any(ext in url.lower() for ext in ['.mp4', '.webm', '.ogg', '.mov']):
        return 'direct'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    else:
        return 'iframe'

def get_youtube_id(url):
    pattern = r'(?:v=|\/shorts\/|be\/|embed\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

# --- ৪. এডমিন প্যানেল লজিক ---
class VideoForm(form.Form):
    title = fields.StringField('Video Title')
    url = fields.StringField('Video Link (MP4/YouTube/Shorts)')
    description = fields.TextAreaField('Description')

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return super(MyAdminIndexView, self).index()

class VideoAdminView(ModelView):
    form = VideoForm
    column_list = ('title', 'url', 'description')
    def is_accessible(self):
        return session.get('logged_in')
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

admin = Admin(app, name='Shorts Admin', index_view=MyAdminIndexView())
admin.add_view(VideoAdminView(videos_col, name='Manage Videos'))

# --- ৫. HTML টেমপ্লেট (Responsive & Feature Rich) ---
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Video Shorts App</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body, html { 
            height: 100%; width: 100%; 
            background: #111; overflow: hidden; 
            font-family: 'Segoe UI', sans-serif; 
        }

        /* ডেক্সটপ ও মোবাইলের জন্য মেইন কন্টেইনার */
        .app-container {
            height: 100vh;
            width: 100%;
            max-width: 450px; /* ডেক্সটপে ফোনের মতো দেখাবে */
            margin: 0 auto;
            background: #000;
            position: relative;
            overflow-y: scroll;
            scroll-snap-type: y mandatory;
            scrollbar-width: none; /* Firefox */
            -ms-overflow-style: none; /* IE */
        }
        .app-container::-webkit-scrollbar { display: none; } /* Chrome/Safari */

        /* প্রতিটি ভিডিওর কার্ড */
        .video-card {
            height: 100vh;
            width: 100%;
            scroll-snap-align: start;
            scroll-snap-stop: always;
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;
            background: #000;
        }

        .video-player {
            width: 100%;
            height: 100%;
            object-fit: cover; /* শর্টস এর মতো ফুল স্ক্রিন */
        }

        /* ডানে সোশ্যাল বাটন */
        .sidebar {
            position: absolute;
            right: 10px;
            bottom: 120px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            z-index: 100;
        }

        .action-btn {
            background: none;
            border: none;
            color: white;
            text-align: center;
            cursor: pointer;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
        }

        .action-btn i { font-size: 28px; }
        .action-btn p { font-size: 12px; margin-top: 5px; }
        .action-btn i.liked { color: #ff0050; }

        /* ভিডিও তথ্য (নিচে) */
        .video-info {
            position: absolute;
            bottom: 40px;
            left: 15px;
            right: 70px;
            color: white;
            z-index: 10;
            text-shadow: 1px 1px 4px rgba(0,0,0,0.9);
        }

        .video-info h3 { font-size: 16px; margin-bottom: 5px; }
        .video-info p { font-size: 14px; opacity: 0.8; }

        /* ডেস্কটপ ভিউতে ব্যাকগ্রাউন্ড */
        @media (min-width: 768px) {
            body { background: #222; }
            .app-container { border-left: 1px solid #333; border-right: 1px solid #333; }
        }

        .admin-link {
            position: fixed; top: 15px; right: 15px;
            background: rgba(0,0,0,0.5); color: white;
            padding: 5px 15px; border-radius: 20px;
            text-decoration: none; font-size: 12px; border: 1px solid #fff; z-index: 1000;
        }
    </style>
</head>
<body>

    <a href="/admin" class="admin-link"><i class="fa fa-cog"></i> Admin</a>

    <div class="app-container" id="container">
        {% if videos %}
            {% for video in videos %}
            <div class="video-card">
                {% set vtype = get_type(video.url) %}
                
                {% if vtype == 'direct' %}
                    <video class="video-player" src="{{ video.url }}" loop playsinline muted onclick="handleVideoClick(this)"></video>
                {% elif vtype == 'youtube' %}
                    {% set yt_id = get_yt_id(video.url) %}
                    <iframe class="video-player" src="https://www.youtube.com/embed/{{ yt_id }}?autoplay=1&mute=1&controls=0&loop=1&playlist={{ yt_id }}&rel=0" allow="autoplay; encrypted-media"></iframe>
                {% else %}
                    <iframe class="video-player" src="{{ video.url }}" allow="autoplay"></iframe>
                {% endif %}

                <!-- সোশ্যাল সাইডবার বাটনসমূহ -->
                <div class="sidebar">
                    <div class="action-btn" onclick="toggleLike(this)">
                        <i class="fa-solid fa-heart"></i>
                        <p>Likes</p>
                    </div>
                    <div class="action-btn" onclick="alert('Comments are disabled')">
                        <i class="fa-solid fa-comment-dots"></i>
                        <p>Chat</p>
                    </div>
                    <div class="action-btn" onclick="shareVideo('{{ video.title }}', '{{ video.url }}')">
                        <i class="fa-solid fa-share"></i>
                        <p>Share</p>
                    </div>
                    <a href="{{ video.url }}" download class="action-btn" style="text-decoration:none;">
                        <i class="fa-solid fa-cloud-arrow-down"></i>
                        <p>Save</p>
                    </a>
                </div>

                <!-- ভিডিও এর টাইটেল ও বর্ণনা -->
                <div class="video-info">
                    <h3>@{{ video.title }}</h3>
                    <p>{{ video.description }}</p>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div style="color:white; text-align:center; margin-top:50vh;">No videos available.</div>
        {% endif %}
    </div>

    <script>
        // অটো-প্লে লজিক: ভিডিও স্ক্রিনে আসলে চলবে, না থাকলে পজ হবে
        const container = document.getElementById('container');
        const allVideos = document.querySelectorAll('video');

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    if (entry.target.tagName === 'VIDEO') {
                        entry.target.play().catch(e => console.log("Auto-play blocked"));
                    }
                } else {
                    if (entry.target.tagName === 'VIDEO') {
                        entry.target.pause();
                    }
                }
            });
        }, { threshold: 0.6 });

        allVideos.forEach(v => observer.observe(v));

        // ভিডিওতে ক্লিক করলে মিউট/আনমিউট হবে
        function handleVideoClick(video) {
            video.muted = !video.muted;
        }

        // লাইক বাটন লজিক
        function toggleLike(btn) {
            const icon = btn.querySelector('i');
            icon.classList.toggle('liked');
            if(icon.classList.contains('liked')) {
                icon.style.color = '#ff0050';
            } else {
                icon.style.color = 'white';
            }
        }

        // শেয়ার লজিক
        function shareVideo(title, url) {
            if (navigator.share) {
                navigator.share({ title: title, url: url });
            } else {
                alert("Link: " + url);
            }
        }
    </script>
</body>
</html>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <style>
        body { background: #111; color: white; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0; }
        .box { background: #222; padding: 30px; border-radius: 10px; width: 300px; text-align: center; border: 1px solid #444; }
        input { width: 100%; padding: 10px; margin: 10px 0; border-radius: 5px; border: none; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #e50914; color: white; border: none; cursor: pointer; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>Admin Login</h2>
        <form method="POST">
            <input type="text" name="u" placeholder="Username" required>
            <input type="password" name="p" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""

# --- ৬. রাুটস (Routes) ---

@app.route('/')
def index():
    videos = list(videos_col.find())
    return render_template_string(
        INDEX_HTML, 
        videos=videos, 
        get_type=get_video_type, 
        get_yt_id=get_youtube_id
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['u'] == ADMIN_USER and request.form['p'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin.index'))
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
