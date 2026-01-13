import os
import sys
import subprocess
import re
import io
from datetime import datetime
from bson import ObjectId

# --- ১. অটোমেটিক লাইব্রেরি ইনস্টল ---
def install_requirements():
    required = ['flask', 'pymongo', 'dnspython', 'flask-admin', 'wtforms', 'gunicorn']
    for lib in required:
        try:
            __import__(lib.replace('-', '_'))
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

install_requirements()

from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify, send_file
from pymongo import MongoClient
import gridfs
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.pymongo import ModelView
from wtforms import form, fields

# --- ২. কনফিগারেশন ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'MY_SUPER_SECRET_KEY_123'
app.config['FLASK_ADMIN_TEMPLATE_MODE'] = 'bootstrap3'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # ২ জিবি লিমিট

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# মাস্টার ডাটাবেস সংযোগ
MONGO_URI = "mongodb+srv://tmlbdmovies:tmlbd198j@cluster0.op4v2d8.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
master_db = client['shorts_app_db'] 
managed_dbs_col = master_db['managed_databases']

# --- ৩. সাহায্যকারী ফাংশন (Helpers) ---
def get_video_type(url):
    if any(ext in url.lower() for ext in ['.mp4', '.webm', '.ogg', '.mov']):
        return 'direct'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    else: 
        return 'iframe' # ফেসবুক বা অন্য থার্ড পার্টি লিংকের জন্য

def get_youtube_id(url):
    pattern = r'(?:v=|\/shorts\/|be\/|embed\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_active_db():
    active_conf = managed_dbs_col.find_one({'is_active': True})
    if active_conf:
        try:
            db_client = MongoClient(active_conf['uri'])
            return db_client['content_db'], active_conf['name'], str(active_conf['_id'])
        except: return None, None, None
    return None, None, None

def get_all_content():
    all_videos = []
    total_size = 0
    for conf in managed_dbs_col.find():
        try:
            db = MongoClient(conf['uri'])['content_db']
            v_list = list(db['videos'].find().sort('created_at', -1))
            for v in v_list:
                v['db_id'] = str(conf['_id'])
                all_videos.append(v)
            total_size += db.command("dbStats").get('storageSize', 0)
        except: continue
    return all_videos, round(total_size / (1024*1024), 2)

# --- ৪. এডমিন ভিউ সেটআপ ---
class DBForm(form.Form):
    name = fields.StringField('Server Name')
    uri = fields.StringField('MongoDB Connection URI')
    is_active = fields.BooleanField('Set Active for New Uploads')

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not session.get('logged_in'): return redirect(url_for('login'))
        all_v, size = get_all_content()
        return self.render('admin/index.html', total_videos=len(all_v), total_size=size)
    
    @expose('/upload_center')
    def upload_center(self):
        if not session.get('logged_in'): return redirect(url_for('login'))
        db, name, db_id = get_active_db()
        return self.render('admin/upload_page.html', db_name=name)

class DBAdminView(ModelView):
    form = DBForm
    column_list = ('name', 'is_active', 'uri')
    def on_model_change(self, form, model, is_created):
        if model.get('is_active'):
            managed_dbs_col.update_many({}, {'$set': {'is_active': False}})
        return model
    def is_accessible(self): return session.get('logged_in')

admin = Admin(app, name='Shorts Admin', index_view=MyAdminIndexView())
admin.add_view(DBAdminView(managed_dbs_col, name='Manage Databases'))

# --- ৫. HTML টেমপ্লেটসমূহ ---
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Shorts Pro</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body, html { height: 100%; width: 100%; background: #000; overflow: hidden; font-family: sans-serif; }
        .app-container { height: 100vh; width: 100%; max-width: 450px; margin: 0 auto; position: relative; overflow-y: scroll; scroll-snap-type: y mandatory; scrollbar-width: none; }
        .app-container::-webkit-scrollbar { display: none; }
        .video-card { height: 100vh; width: 100%; scroll-snap-align: start; position: relative; display: flex; justify-content: center; align-items: center; background: #000; }
        .video-player { width: 100%; height: 100%; object-fit: cover; }
        .sidebar { position: absolute; right: 10px; bottom: 120px; display: flex; flex-direction: column; gap: 20px; z-index: 100; }
        .action-btn { background: none; border: none; color: white; text-align: center; cursor: pointer; }
        .action-btn i { font-size: 28px; filter: drop-shadow(2px 2px 2px rgba(0,0,0,0.8)); }
        .liked { color: #ff0050 !important; }
        .video-info { position: absolute; bottom: 40px; left: 15px; right: 70px; color: white; z-index: 10; text-shadow: 1px 1px 5px rgba(0,0,0,1); }
        .admin-link { position: fixed; top: 15px; right: 15px; background: rgba(0,0,0,0.5); color: white; padding: 5px 15px; border-radius: 20px; text-decoration: none; font-size: 12px; z-index: 1000; border: 1px solid #444; }
    </style>
</head>
<body>
    <a href="/admin" class="admin-link">Admin</a>
    <div class="app-container">
        {% for video in videos %}
        <div class="video-card">
            {% set vtype = get_type(video.url) %}
            
            {% if vtype == 'direct' %}
                <video class="video-player" src="{{ video.url }}" loop playsinline muted onclick="this.muted=!this.muted; this.paused?this.play():this.pause()"></video>
            {% elif vtype == 'youtube' %}
                {% set yt_id = get_yt_id(video.url) %}
                <iframe class="video-player" src="https://www.youtube.com/embed/{{ yt_id }}?autoplay=1&mute=1&loop=1&playlist={{ yt_id }}&controls=0" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>
            {% else %}
                <iframe class="video-player" src="{{ video.url }}" frameborder="0" allow="autoplay"></iframe>
            {% endif %}

            <div class="sidebar">
                <div class="action-btn" onclick="likeVideo('{{ video.db_id }}', '{{ video._id }}', this)">
                    <i class="fa-solid fa-heart {{ 'liked' if video.likes > 0 }}"></i>
                    <p id="like-{{ video._id }}">{{ video.likes or 0 }}</p>
                </div>
                <div class="action-btn">
                    <i class="fa-solid fa-comment-dots"></i>
                    <p>{{ video.comments|length }}</p>
                </div>
            </div>
            <div class="video-info">
                <h3>@{{ video.title }}</h3>
                <p>{{ video.description }}</p>
            </div>
        </div>
        {% endfor %}
    </div>

    <script>
        function likeVideo(db, vid, btn) {
            fetch(`/like/${db}/${vid}`, {method:'POST'}).then(r=>r.json()).then(data=>{
                document.getElementById(`like-${vid}`).innerText = data.likes;
                btn.querySelector('i').classList.add('liked');
            });
        }
        const obs = new IntersectionObserver(es => {
            es.forEach(e => {
                const v = e.target.querySelector('video');
                if(v) e.isIntersecting ? v.play() : v.pause();
            });
        }, {threshold: 0.6});
        document.querySelectorAll('.video-card').forEach(c => obs.observe(c));
    </script>
</body>
</html>
"""

UPLOAD_PAGE_HTML = """
{% extends 'admin/master.html' %}
{% block body %}
<div class="well">
    <h3>Add Content to: {{ db_name or 'No Database Selected' }}</h3>
    <hr>
    <form id="upForm">
        <input type="text" id="t" class="form-control" placeholder="Video Title" required><br>
        <textarea id="d" class="form-control" placeholder="Description"></textarea><br>
        
        <div class="panel panel-info" style="padding:15px">
            <label><input type="radio" name="stype" value="file" checked onclick="toggleInput()"> Upload MP4 File</label>
            &nbsp;&nbsp;
            <label><input type="radio" name="stype" value="link" onclick="toggleInput()"> Paste Video Link</label>
            
            <div id="file_sec" style="margin-top:10px">
                <input type="file" id="f" class="form-control" accept="video/*">
            </div>
            <div id="link_sec" style="margin-top:10px; display:none">
                <input type="text" id="u" class="form-control" placeholder="YouTube or MP4 URL">
            </div>
        </div>

        <div id="prog" style="display:none" class="progress">
            <div id="bar" class="progress-bar progress-bar-striped active" style="width:0%">0%</div>
        </div>
        <button type="submit" id="btn" class="btn btn-danger btn-block">Add Video Now</button>
    </form>
</div>
<script>
function toggleInput() {
    const isFile = document.querySelector('input[name="stype"]:checked').value === 'file';
    document.getElementById('file_sec').style.display = isFile ? 'block' : 'none';
    document.getElementById('link_sec').style.display = isFile ? 'none' : 'block';
}
document.getElementById('upForm').onsubmit = function(e) {
    e.preventDefault();
    const fd = new FormData();
    const type = document.querySelector('input[name="stype"]:checked').value;
    fd.append('title', document.getElementById('t').value);
    fd.append('desc', document.getElementById('d').value);
    
    if(type === 'file') {
        fd.append('video', document.getElementById('f').files[0]);
    } else {
        fd.append('video_url', document.getElementById('u').value);
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload', true);
    document.getElementById('prog').style.display = 'block';
    xhr.upload.onprogress = e => {
        let p = Math.round((e.loaded/e.total)*100);
        document.getElementById('bar').style.width = p+'%';
        document.getElementById('bar').innerHTML = p+'%';
    };
    xhr.onload = () => { alert('Added!'); location.reload(); };
    xhr.send(fd);
}
</script>
{% endblock %}
"""

# --- ৬. রাুটস ---
@app.route('/')
def index():
    vs, sz = get_all_content()
    return render_template_string(INDEX_HTML, videos=vs, get_type=get_video_type, get_yt_id=get_youtube_id)

@app.route('/api/upload', methods=['POST'])
def api_upload():
    db, name, db_id = get_active_db()
    if not db: return "No DB Selected", 400
    
    title = request.form.get('title')
    desc = request.form.get('desc')
    video_url = request.form.get('video_url')
    file = request.files.get('video')
    
    final_url = ""
    if file:
        fs = gridfs.GridFS(db)
        fid = fs.put(file, filename=file.filename)
        final_url = f'/stream/{db_id}/{fid}'
    else:
        final_url = video_url

    db['videos'].insert_one({
        'title': title, 'description': desc,
        'url': final_url, 'likes': 0, 'shares': 0, 'comments': [],
        'created_at': datetime.now()
    })
    return jsonify({'ok':True})

@app.route('/stream/<db_id>/<fid>')
def stream(db_id, fid):
    conf = managed_dbs_col.find_one({'_id': ObjectId(db_id)})
    db = MongoClient(conf['uri'])['content_db']
    fs = gridfs.GridFS(db)
    out = fs.get(ObjectId(fid))
    return send_file(io.BytesIO(out.read()), mimetype='video/mp4')

@app.route('/like/<db_id>/<vid>', methods=['POST'])
def like(db_id, vid):
    conf = managed_dbs_col.find_one({'_id': ObjectId(db_id)})
    db = MongoClient(conf['uri'])['content_db']
    db['videos'].update_one({'_id': ObjectId(vid)}, {'$inc': {'likes': 1}})
    v = db['videos'].find_one({'_id': ObjectId(vid)})
    return jsonify({'likes': v.get('likes', 0)})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['u'] == ADMIN_USER and request.form['p'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin.index'))
    return '<h3>Admin Login</h3><form method="POST">User: <input name="u"><br>Pass: <input name="p" type="password"><br><button>Login</button></form>'

if __name__ == "__main__":
    if not os.path.exists('templates/admin'): os.makedirs('templates/admin')
    with open('templates/admin/upload_page.html', 'w') as f: f.write(UPLOAD_PAGE_HTML)
    app.run(host='0.0.0.0', port=5000, debug=True)
