import os
import sys
import subprocess

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
app.config['SECRET_KEY'] = 'MY_SUPER_SECRET_KEY_123'

# এডমিন লগইন ডিটেইলস
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# MongoDB কানেকশন ফিক্স
# Render Environment Variable থেকে নিবে, না থাকলে লোকাল কানেকশন
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
# ডাটাবেসের নাম সরাসরি উল্লেখ করে দেওয়া হলো যাতে 'No default database' এরর না আসে
db = client['shorts_app_db'] 
videos_col = db['videos']

# --- ২. এডমিন প্যানেল লজিক (লগইন সহ) ---

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return super(MyAdminIndexView, self).index()

class VideoAdminView(ModelView):
    def is_accessible(self):
        return session.get('logged_in')

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

    column_list = ('title', 'url')
    # ভিডিও যোগ করার ফরম
    form_extra_fields = {
        'title': fields.StringField('Video Title'),
        'url': fields.StringField('Direct MP4 Link'),
        'description': fields.TextAreaField('Description')
    }

# এডমিন প্যানেল সেটআপ (template_mode এরর ফিক্স করা হয়েছে)
admin = Admin(app, name='Shorts Admin', index_view=MyAdminIndexView())
admin.add_view(VideoAdminView(videos_col, name='Manage Videos'))

# --- ৩. HTML টেমপ্লেটসমূহ ---

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shorts Clone</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body, html { height: 100%; background: #000; overflow: hidden; font-family: sans-serif; }
        .container { height: 100vh; overflow-y: scroll; scroll-snap-type: y mandatory; scrollbar-width: none; }
        .container::-webkit-scrollbar { display: none; }
        .video-card { height: 100vh; width: 100%; scroll-snap-align: start; position: relative; display: flex; justify-content: center; align-items: center; }
        video { height: 100%; width: 100%; object-fit: cover; }
        .overlay { position: absolute; bottom: 40px; left: 20px; color: white; text-shadow: 2px 2px 5px #000; }
        .admin-link { position: fixed; top: 15px; right: 15px; background: rgba(255,255,255,0.2); color: white; padding: 5px 15px; border-radius: 20px; text-decoration: none; z-index: 100; font-size: 12px; border: 1px solid #fff; }
    </style>
</head>
<body>
    <a href="/admin" class="admin-link">Admin Panel</a>
    <div class="container">
        {% for video in videos %}
        <div class="video-card">
            <video src="{{ video.url }}" loop muted playsinline onclick="this.paused?this.play():this.pause()"></video>
            <div class="overlay">
                <h3>@{{ video.title }}</h3>
                <p>{{ video.description }}</p>
            </div>
        </div>
        {% endfor %}
    </div>
    <script>
        const videos = document.querySelectorAll('video');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) entry.target.play();
                else entry.target.pause();
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
        body { background: #111; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .box { background: #222; padding: 30px; border-radius: 10px; text-align: center; border: 1px solid #444; }
        input { display: block; width: 100%; margin: 10px 0; padding: 10px; border-radius: 5px; border: none; }
        button { width: 100%; padding: 10px; background: #e50914; color: white; border: none; border-radius: 5px; cursor: pointer; }
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
    </div>
</body>
</html>
"""

# --- ৪. রাউটস (Routes) ---

@app.route('/')
def index():
    videos = list(videos_col.find())
    return render_template_string(INDEX_HTML, videos=videos)

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
