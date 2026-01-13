import os
import sys
import subprocess

# --- অটোমেটিক লাইব্রেরি ইনস্টল (আপনার পিসিতে না থাকলে নিজে থেকেই ইনস্টল হবে) ---
def install_requirements():
    required = ['flask', 'pymongo', 'dnspython', 'flask-admin', 'wtforms', 'gunicorn']
    for lib in required:
        try:
            __import__(lib)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

install_requirements()

from flask import Flask, render_template_string, request, session, redirect, url_for
from pymongo import MongoClient
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.pymongo import ModelView
from wtforms import form, fields

# --- ১. কনফিগারেশন এবং ডাটাবেস সেটআপ ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'MY_SUPER_SECRET_KEY_786' # সেশন সিকিউরিটির জন্য

# এডমিন লগইন তথ্য
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# MongoDB সংযোগ (আপনার Atlas Link এখানে বসান)
# উদাহরণ: "mongodb+srv://user:pass@cluster.mongodb.net/dbname"
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://tmlbdmovies:tmlbd198j@cluster0.op4v2d8.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client.get_database()
videos_col = db['videos']

# --- ২. এডমিন প্যানেল লজিক (লগইন সিস্টেম সহ) ---

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return super(MyAdminIndexView, self).index()

class VideoAdminView(ModelView):
    column_list = ('title', 'url', 'description')
    
    def is_accessible(self):
        return session.get('logged_in')

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

    # ডাটাবেসে ভিডিও সেভ করার ফরম
    form_extra_fields = {
        'title': fields.StringField('Video Title'),
        'url': fields.StringField('Direct MP4 Link'),
        'description': fields.TextAreaField('Description')
    }

# এডমিন প্যানেল ইনিশিয়ালাইজ
admin = Admin(app, name='Shorts Admin', template_mode='bootstrap3', index_view=MyAdminIndexView())
admin.add_view(VideoAdminView(videos_col, name='Manage Videos'))

# --- ৩. ফ্রন্টএন্ড এবং লগইন টেমপ্লেট (HTML/CSS/JS) ---

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
        
        /* ভার্টিক্যাল স্ক্রল স্ন্যাপ */
        .shorts-container {
            height: 100vh;
            overflow-y: scroll;
            scroll-snap-type: y mandatory;
            scrollbar-width: none;
        }
        .shorts-container::-webkit-scrollbar { display: none; }

        .video-card {
            height: 100vh;
            width: 100%;
            scroll-snap-align: start;
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        video {
            height: 100%;
            width: 100%;
            object-fit: cover;
        }

        .overlay {
            position: absolute;
            bottom: 40px;
            left: 20px;
            color: white;
            z-index: 10;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.8);
        }

        .admin-link {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.3);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            text-decoration: none;
            z-index: 100;
            font-size: 14px;
            border: 1px solid white;
        }
    </style>
</head>
<body>
    <a href="/admin" class="admin-link">Admin Panel</a>

    <div class="shorts-container">
        {% for video in videos %}
        <div class="video-card">
            <video class="v-player" src="{{ video.url }}" loop muted playsinline onclick="togglePlay(this)"></video>
            <div class="overlay">
                <h2>@{{ video.title }}</h2>
                <p>{{ video.description }}</p>
            </div>
        </div>
        {% endfor %}
    </div>

    <script>
        // অটো-প্লে লজিক যখন স্ক্রল করা হয়
        const videos = document.querySelectorAll('.v-player');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.play();
                } else {
                    entry.target.pause();
                }
            });
        }, { threshold: 0.6 });

        videos.forEach(v => observer.observe(v));

        function togglePlay(v) {
            if (v.paused) v.play();
            else v.pause();
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
        body { background: #111; color: white; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; }
        form { background: #222; padding: 30px; border-radius: 10px; border: 1px solid #444; }
        input { display: block; width: 250px; margin-bottom: 15px; padding: 10px; border-radius: 5px; border: none; }
        button { width: 100%; padding: 10px; background: red; color: white; border: none; border-radius: 5px; cursor: pointer; }
    </style>
</head>
<body>
    <form method="POST">
        <h2>Admin Login</h2>
        <input type="text" name="u" placeholder="Username" required>
        <input type="password" name="p" placeholder="Password" required>
        <button type="submit">Login</button>
        {% if err %}<p style="color:red; margin-top:10px;">{{ err }}</p>{% endif %}
    </form>
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
        error = "Invalid Login!"
    return render_template_string(LOGIN_HTML, err=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

# --- ৫. অ্যাপ রান ---
if __name__ == "__main__":
    # Render/Vercel অটোমেটিক পোর্ট হ্যান্ডেল করবে
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
