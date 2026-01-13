import os
import sys
import subprocess
import re

# --- অটোমেটিক লাইব্রেরি ইনস্টল ---
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

# --- ১. কনফিগারেশন ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'MY_SUPER_SECRET_KEY_123')
app.config['FLASK_ADMIN_TEMPLATE_MODE'] = 'bootstrap3'

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://tmlbdmovies:tmlbd198j@cluster0.op4v2d8.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['shorts_app_db'] 
videos_col = db['videos']

# --- ২. সাহায্যকারী ফাংশন (URL Parser) ---
def get_video_type(url):
    """লিঙ্কটি কি সরাসরি ভিডিও ফাইল নাকি ইউটিউব তা চেক করবে"""
    if any(ext in url.lower() for ext in ['.mp4', '.webm', '.ogg', '.mov']):
        return 'direct'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    else:
        return 'iframe'  # অন্য যে কোন লিঙ্কের জন্য (যেমন ফেসবুক/টিকটক যা আইফ্রেম সাপোর্ট করে)

def get_youtube_id(url):
    """ইউটিউব ভিডিও বা শর্টস আইডি এক্সট্রাক্ট করে"""
    pattern = r'(?:v=|\/shorts\/|be\/|embed\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

# --- ৩. এডমিন প্যানেল লজিক ---
class VideoForm(form.Form):
    title = fields.StringField('Video Title')
    url = fields.StringField('Video Link (YouTube/Direct MP4/Other)')
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

# --- ৪. HTML টেমপ্লেটসমূহ ---
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Source Shorts</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body, html { height: 100%; background: #000; overflow: hidden; font-family: sans-serif; }
        .container { height: 100vh; overflow-y: scroll; scroll-snap-type: y mandatory; scrollbar-width: none; }
        .container::-webkit-scrollbar { display: none; }
        .video-card { height: 100vh; width: 100%; scroll-snap-align: start; position: relative; display: flex; justify-content: center; align-items: center; background: #000; }
        video, iframe { height: 100%; width: 100%; border: none; }
        .overlay { position: absolute; bottom: 40px; left: 20px; color: white; text-shadow: 2px 2px 5px #000; z-index: 10; pointer-events: none; }
        .admin-link { position: fixed; top: 15px; right: 15px; background: rgba(0,0,0,0.5); color: white; padding: 5px 15px; border-radius: 20px; text-decoration: none; z-index: 100; font-size: 12px; border: 1px solid #fff; }
    </style>
</head>
<body>
    <a href="/admin" class="admin-link">Admin Panel</a>
    <div class="container">
        {% if videos %}
            {% for video in videos %}
            <div class="video-card">
                {% set vtype = get_type(video.url) %}
                
                {% if vtype == 'direct' %}
                    <video src="{{ video.url }}" loop playsinline onclick="this.paused?this.play():this.pause()"></video>
                {% elif vtype == 'youtube' %}
                    {% set yt_id = get_yt_id(video.url) %}
                    <iframe src="https://www.youtube.com/embed/{{ yt_id }}?autoplay=0&controls=0&loop=1&playlist={{ yt_id }}" allow="autoplay; encrypted-media" allowfullscreen></iframe>
                {% else %}
                    <iframe src="{{ video.url }}" allow="autoplay"></iframe>
                {% endif %}

                <div class="overlay">
                    <h3>@{{ video.title }}</h3>
                    <p>{{ video.description }}</p>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div style="color: white; text-align: center; margin-top: 50vh;">No videos found. Go to Admin Panel to add some.</div>
        {% endif %}
    </div>

    <script>
        // অটো-প্লে লজিক শুধুমাত্র সরাসরি ভিডিওর জন্য (ইউটিউব আইফ্রেম ব্রাউজার সিকিউরিটির কারণে অটো-প্লে ব্লক করতে পারে)
        const videos = document.querySelectorAll('video');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    if(entry.target.tagName === 'VIDEO') entry.target.play();
                } else {
                    if(entry.target.tagName === 'VIDEO') entry.target.pause();
                }
            });
        }, { threshold: 0.6 });
        videos.forEach(v => observer.observe(v));
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
        body { background: #111; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin:0; }
        .box { background: #222; padding: 30px; border-radius: 10px; text-align: center; border: 1px solid #444; width: 300px; }
        input { display: block; width: 100%; margin: 10px 0; padding: 10px; border-radius: 5px; border: none; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #e50914; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        a { color: #888; text-decoration: none; font-size: 12px; display: block; margin-top: 15px; }
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
        {% if err %}<p style="color:red; margin-top:10px;">{{ err }}</p>{% endif %}
        <a href="/">← Back to Videos</a>
    </div>
</body>
</html>
"""

# --- ৫. রাউটস (Routes) ---

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
    error = None
    if request.method == 'POST':
        if request.form['u'] == ADMIN_USER and request.form['p'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin.index'))
        error = "Invalid Username or Password"
    return render_template_string(LOGIN_HTML, err=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
