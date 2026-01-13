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
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'MY_SUPER_SECRET_KEY_123')
app.config['FLASK_ADMIN_TEMPLATE_MODE'] = 'bootstrap3'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # ২ জিবি লিমিট

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# মাস্টার ডাটাবেস
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
    else: return 'iframe'

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
            v_list = list(db['videos'].find())
            for v in v_list:
                v['db_id'] = str(conf['_id'])
                all_videos.append(v)
            total_size += db.command("dbStats").get('storageSize', 0)
        except: continue
    return all_videos, round(total_size / (1024*1024), 2)

# --- ৪. এডমিন ফর্ম ও ভিউ (Fixing NotImplementedError) ---

class DBForm(form.Form):
    name = fields.StringField('Database Alias (Server Name)')
    uri = fields.StringField('MongoDB URI Connection Link')
    is_active = fields.BooleanField('Set Active for Uploads')

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
    form = DBForm # এই লাইনটি এরর ফিক্স করবে
    column_list = ('name', 'is_active', 'uri')
    def on_model_change(self, form, model, is_created):
        if model.get('is_active'):
            managed_dbs_col.update_many({}, {'$set': {'is_active': False}})
        return model
    def is_accessible(self): return session.get('logged_in')

admin = Admin(app, name='Shorts Admin', index_view=MyAdminIndexView())
admin.add_view(DBAdminView(managed_dbs_col, name='Manage Databases'))

# --- ৫. HTML টেমপ্লেট (Original Shorts UI) ---
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Shorts App</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body, html { height: 100%; width: 100%; background: #111; overflow: hidden; font-family: sans-serif; }
        .app-container { height: 100vh; width: 100%; max-width: 450px; margin: 0 auto; background: #000; position: relative; overflow-y: scroll; scroll-snap-type: y mandatory; scrollbar-width: none; }
        .app-container::-webkit-scrollbar { display: none; }
        .video-card { height: 100vh; width: 100%; scroll-snap-align: start; position: relative; display: flex; justify-content: center; align-items: center; }
        .video-player { width: 100%; height: 100%; object-fit: cover; }
        .sidebar { position: absolute; right: 10px; bottom: 120px; display: flex; flex-direction: column; gap: 20px; z-index: 100; }
        .action-btn { background: none; border: none; color: white; text-align: center; cursor: pointer; text-shadow: 1px 1px 3px rgba(0,0,0,0.8); }
        .action-btn i { font-size: 28px; }
        .liked { color: #ff0050 !important; }
        .video-info { position: absolute; bottom: 40px; left: 15px; right: 70px; color: white; z-index: 10; }
        .admin-link { position: fixed; top: 15px; right: 15px; background: rgba(0,0,0,0.5); color: white; padding: 5px 15px; border-radius: 20px; text-decoration: none; font-size: 12px; z-index: 1000; }
        #comment-modal { position: fixed; bottom: -100%; left: 50%; transform: translateX(-50%); width: 100%; max-width: 450px; height: 60%; background: white; z-index: 1000; transition: 0.3s; border-radius: 20px 20px 0 0; padding: 20px; color: #000; }
        #comment-modal.active { bottom: 0; }
        .comment-list { flex-grow: 1; overflow-y: auto; margin-bottom: 10px; }
        .overlay { position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); display:none; z-index:999; }
    </style>
</head>
<body>
    <div class="overlay" id="overlay" onclick="closeComments()"></div>
    <a href="/admin" class="admin-link">Admin Panel</a>
    <div class="app-container" id="container">
        {% for video in videos %}
        <div class="video-card">
            {% set vtype = get_type(video.url) %}
            {% if vtype == 'direct' %}
                <video class="video-player" src="{{ video.url }}" loop playsinline muted onclick="this.muted=!this.muted"></video>
            {% elif vtype == 'youtube' %}
                {% set yt_id = get_yt_id(video.url) %}
                <iframe class="video-player" src="https://www.youtube.com/embed/{{ yt_id }}?autoplay=1&mute=1&loop=1&playlist={{ yt_id }}" frameborder="0" allow="autoplay"></iframe>
            {% endif %}
            <div class="sidebar">
                <div class="action-btn" onclick="likeVideo('{{ video.db_id }}', '{{ video._id }}', this)">
                    <i class="fa-solid fa-heart {{ 'liked' if video.likes > 0 }}"></i>
                    <p id="like-{{ video._id }}">{{ video.likes or 0 }}</p>
                </div>
                <div class="action-btn" onclick="openComments('{{ video.db_id }}', '{{ video._id }}')">
                    <i class="fa-solid fa-comment-dots"></i>
                    <p>{{ video.comments|length }}</p>
                </div>
                <div class="action-btn" onclick="shareVideo('{{ video.url }}')">
                    <i class="fa-solid fa-share"></i>
                    <p>{{ video.shares or 0 }}</p>
                </div>
            </div>
            <div class="video-info">
                <h3>@{{ video.title }}</h3>
                <p>{{ video.description }}</p>
            </div>
        </div>
        {% endfor %}
    </div>

    <div id="comment-modal">
        <div style="display:flex; justify-content:space-between"><b>Comments</b><span onclick="closeComments()">✕</span></div>
        <div class="comment-list" id="comment-list"></div>
        <input type="text" id="cm-txt" placeholder="Add comment..." style="width:80%; padding:10px;">
        <button onclick="postComment()" style="padding:10px; background:#ff0050; color:#fff; border:none;">Post</button>
    </div>

    <script>
        let curV, curD;
        function likeVideo(db, vid, btn) {
            fetch(`/like/${db}/${vid}`, {method:'POST'}).then(r=>r.json()).then(data=>{
                document.getElementById(`like-${vid}`).innerText = data.likes;
                btn.querySelector('i').classList.add('liked');
            });
        }
        function openComments(db, vid) {
            curV=vid; curD=db;
            document.getElementById('comment-modal').classList.add('active');
            document.getElementById('overlay').style.display='block';
            fetch(`/comments/${db}/${vid}`).then(r=>r.json()).then(data=>{
                document.getElementById('comment-list').innerHTML = data.map(c=>`<p><b>User:</b> ${c.text}</p>`).join('');
            });
        }
        function closeComments() {
            document.getElementById('comment-modal').classList.remove('active');
            document.getElementById('overlay').style.display='none';
        }
        function postComment() {
            let t = document.getElementById('cm-txt');
            fetch(`/comment/${curD}/${curV}`, {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({text: t.value})
            }).then(()=> { t.value=''; closeComments(); location.reload(); });
        }
        function shareVideo(url) {
            if(navigator.share) navigator.share({url:url}); else alert(url);
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
    <h3>Upload Video to Cloud</h3>
    <p>Target Server: <b>{{ db_name or 'No DB Selected' }}</b></p>
    <form id="upForm">
        <input type="text" id="t" class="form-control" placeholder="Title" required><br>
        <textarea id="d" class="form-control" placeholder="Description"></textarea><br>
        <input type="file" id="f" class="form-control" accept="video/*" required><br>
        <div id="prog" style="display:none" class="progress">
            <div id="bar" class="progress-bar progress-bar-striped active" style="width:0%">0%</div>
        </div>
        <button type="submit" id="btn" class="btn btn-danger btn-block">Upload Video</button>
    </form>
</div>
<script>
document.getElementById('upForm').onsubmit = function(e) {
    e.preventDefault();
    const fd = new FormData();
    fd.append('title', document.getElementById('t').value);
    fd.append('desc', document.getElementById('d').value);
    fd.append('video', document.getElementById('f').files[0]);
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload', true);
    document.getElementById('prog').style.display = 'block';
    xhr.upload.onprogress = e => {
        let p = Math.round((e.loaded/e.total)*100);
        document.getElementById('bar').style.width = p+'%';
        document.getElementById('bar').innerHTML = p+'%';
    };
    xhr.onload = () => { alert('Success!'); location.reload(); };
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
    if not db: return "No DB", 400
    file = request.files['video']
    fs = gridfs.GridFS(db)
    fid = fs.put(file, filename=file.filename)
    db['videos'].insert_one({
        'title': request.form['title'], 'description': request.form['desc'],
        'url': f'/stream/{db_id}/{fid}', 'likes': 0, 'shares': 0, 'comments': [],
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

@app.route('/comments/<db_id>/<vid>')
def get_comments(db_id, vid):
    conf = managed_dbs_col.find_one({'_id': ObjectId(db_id)})
    db = MongoClient(conf['uri'])['content_db']
    v = db['videos'].find_one({'_id': ObjectId(vid)})
    return jsonify(v.get('comments', []))

@app.route('/comment/<db_id>/<vid>', methods=['POST'])
def post_comment(db_id, vid):
    conf = managed_dbs_col.find_one({'_id': ObjectId(db_id)})
    db = MongoClient(conf['uri'])['content_db']
    db['videos'].update_one({'_id': ObjectId(vid)}, {'$push': {'comments': {'text': request.json['text']}}})
    return jsonify({'ok': True})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['u'] == ADMIN_USER and request.form['p'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin.index'))
    return """<form method="POST">User: <input name="u"><br>Pass: <input name="p" type="password"><br><button>Login</button></form>"""

if __name__ == "__main__":
    if not os.path.exists('templates/admin'): os.makedirs('templates/admin')
    with open('templates/admin/upload_page.html', 'w') as f: f.write(UPLOAD_PAGE_HTML)
    app.run(host='0.0.0.0', port=5000)
