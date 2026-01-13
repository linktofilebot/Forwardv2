import os
import sys
import subprocess
import io
import re
from datetime import datetime
from bson import ObjectId

# --- ১. প্রয়োজনীয় লাইব্রেরি অটো-ইনস্টল ---
def install_requirements():
    required = ['flask', 'pymongo', 'dnspython', 'flask-admin', 'wtforms', 'gunicorn']
    for lib in required:
        try:
            __import__(lib.replace('-', '_'))
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

install_requirements()

from flask import Flask, render_template_string, request, session, redirect, url_for, flash, jsonify, send_file
from pymongo import MongoClient
import gridfs
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.pymongo import ModelView
from wtforms import form, fields

# --- ২. কনফিগারেশন ও ডাটাবেস কানেকশন ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'THE_ULTIMATE_CINEMA_KEY_2024'
app.config['FLASK_ADMIN_TEMPLATE_MODE'] = 'bootstrap3'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # ২ জিবি লিমিট

# মাস্টার ডাটাবেস (যেখানে সব কানেকশন ও মুভি লিস্টের তথ্য থাকবে)
MASTER_MONGO_URI = "mongodb+srv://tmlbdmovies:tmlbd198j@cluster0.op4v2d8.mongodb.net/?appName=Cluster0"
master_client = MongoClient(MASTER_MONGO_URI)
master_db = master_client['master_config_db']
managed_dbs_col = master_db['managed_databases']

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# --- ৩. সাহায্যকারী ফাংশনসমূহ (Helpers) ---

def get_active_db_info():
    """সিলেক্ট করা একটিভ ডাটাবেস কানেকশন দেয়"""
    active_conf = managed_dbs_col.find_one({'is_active': True})
    if active_conf:
        try:
            client = MongoClient(active_conf['uri'])
            db = client['movie_content_db']
            return db, active_conf['name'], str(active_conf['_id'])
        except: return None, None, None
    return None, None, None

def get_combined_stats():
    """সবগুলো মংোডিবি থেকে মুভি লিস্ট এবং স্টোরেজ হিসাব করে"""
    all_movies = []
    total_bytes = 0
    configs = list(managed_dbs_col.find())
    for conf in configs:
        try:
            client = MongoClient(conf['uri'])
            db = client['movie_content_db']
            # মুভি কালেকশন থেকে ডাটা নেওয়া
            movies = list(db['movies'].find())
            for m in movies:
                m['db_id'] = str(conf['_id']) # কোন ডিবি থেকে আসছে তা মনে রাখা
                all_movies.append(m)
            # স্টোরেজ সাইজ নেওয়া
            stats = db.command("dbStats")
            total_bytes += stats.get('storageSize', 0)
        except: continue
    total_mb = round(total_bytes / (1024 * 1024), 2)
    return all_movies, total_mb

# --- ৪. এডমিন প্যানেল লজিক ---

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not session.get('logged_in'): return redirect(url_for('login'))
        all_movies, total_mb = get_combined_stats()
        return self.render('admin/index.html', total_movies=len(all_movies), total_size=total_mb)

    @expose('/upload_center')
    def upload_center(self):
        if not session.get('logged_in'): return redirect(url_for('login'))
        db, db_name, db_id = get_active_db_info()
        return self.render('admin/upload_page.html', db_name=db_name)

class DBAdminView(ModelView):
    column_list = ('name', 'is_active', 'uri')
    def on_model_change(self, form, model, is_created):
        # একটি ডিবি একটিভ করলে বাকিগুলো অটো ইন-একটিভ হবে
        if model.get('is_active'):
            managed_dbs_col.update_many({}, {'$set': {'is_active': False}})
        return model
    def is_accessible(self): return session.get('logged_in')

admin = Admin(app, name='Cloud Drive Admin', index_view=MyAdminIndexView(), template_mode='bootstrap3')
admin.add_view(DBAdminView(managed_dbs_col, name='Manage Databases'))

# --- ৫. HTML টেমপ্লেটসমূহ (UI) ---

UPLOAD_PAGE_HTML = """
{% extends 'admin/master.html' %}
{% block body %}
<div class="well" style="background: #fff; border-radius: 10px;">
    <h3><i class="fa fa-upload"></i> Direct Video Upload (to GridFS)</h3>
    <p>Upload Destination: <span class="label label-danger">{{ db_name if db_name else 'None Selected' }}</span></p>
    <hr>
    <form id="fileUploadForm">
        <div class="form-group"><label>Movie Name</label><input type="text" id="title" class="form-control" required></div>
        <div class="form-group"><label>Poster URL</label><input type="text" id="poster" class="form-control" required></div>
        <div class="form-group"><label>Description</label><textarea id="desc" class="form-control"></textarea></div>
        <div class="form-group"><label>Select Movie File</label><input type="file" id="video_file" class="form-control" accept="video/*" required></div>
        
        <div id="progressArea" style="display:none; margin: 20px 0;">
            <div class="progress"><div id="pBar" class="progress-bar progress-bar-striped active" style="width: 0%">0%</div></div>
            <p id="pStatus" class="text-center font-bold"></p>
        </div>
        <button type="submit" id="upBtn" class="btn btn-primary btn-block">Start Cloud Upload</button>
    </form>
</div>
<script>
document.getElementById('fileUploadForm').onsubmit = function(e) {
    e.preventDefault();
    const formData = new FormData();
    formData.append('title', document.getElementById('title').value);
    formData.append('poster', document.getElementById('poster').value);
    formData.append('desc', document.getElementById('desc').value);
    formData.append('video_file', document.getElementById('video_file').files[0]);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload_direct', true);
    document.getElementById('progressArea').style.display = 'block';
    document.getElementById('upBtn').disabled = true;

    xhr.upload.onprogress = function(ev) {
        if (ev.lengthComputable) {
            const percent = Math.round((ev.loaded / ev.total) * 100);
            document.getElementById('pBar').style.width = percent + '%';
            document.getElementById('pBar').innerHTML = percent + '%';
            document.getElementById('pStatus').innerHTML = `Uploading: ${(ev.loaded/(1024*1024)).toFixed(2)}MB / ${(ev.total/(1024*1024)).toFixed(2)}MB`;
        }
    };
    xhr.onload = function() {
        if(xhr.status === 200) { alert('Upload Complete!'); location.reload(); }
        else { alert('Upload Failed! Check DB Connection.'); }
    };
    xhr.send(formData);
};
</script>
{% endblock %}
"""

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CloudStream - All-in-One</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background: #000; color: white; font-family: sans-serif; margin: 0; }
        .stats { background: #e50914; padding: 10px; text-align: center; font-size: 13px; font-weight: bold; }
        .nav { padding: 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; padding: 15px; }
        .card { background: #111; border-radius: 8px; overflow: hidden; text-decoration: none; color: white; border: 1px solid #333; }
        .card img { width: 100%; height: 200px; object-fit: cover; }
        .card h3 { font-size: 12px; padding: 8px; margin: 0; text-align: center; }
    </style>
</head>
<body>
    <div class="stats">Total Content: {{ t_count }} | Storage Used: {{ t_size }} MB</div>
    <div class="nav">
        <h2 style="color:#e50914; margin:0;">CLOUD DRIVE</h2>
        <a href="/admin" style="color:white; text-decoration:none; background:#333; padding:5px 15px; border-radius:20px;">Admin</a>
    </div>
    <div class="grid">
        {% for movie in movies %}
        <a href="/watch/{{ movie.db_id }}/{{ movie._id }}" class="card">
            <img src="{{ movie.poster }}">
            <h3>{{ movie.title }}</h3>
        </a>
        {% endfor %}
    </div>
</body>
</html>
"""

WATCH_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ movie.title }}</title>
    <style>
        body { background: #000; color: white; font-family: sans-serif; margin: 0; }
        .video-player { width: 100%; aspect-ratio: 16/9; background: #000; }
        video { width: 100%; height: 100%; }
        .info { padding: 20px; }
        .ep-btn { background: #222; color: white; border: 1px solid #444; padding: 10px; border-radius: 5px; cursor: pointer; margin: 5px; }
    </style>
</head>
<body>
    <div class="video-player">
        <video id="v-player" controls autoplay src="{{ movie.episodes[0].url if movie.episodes else '' }}"></video>
    </div>
    <div class="info">
        <a href="/" style="color:#e50914; text-decoration:none;">← Back Home</a>
        <h1>{{ movie.title }}</h1>
        <p>{{ movie.description }}</p>
        <hr>
        <h3>Episode List:</h3>
        {% for ep in movie.episodes %}
        <button class="ep-btn" onclick="document.getElementById('v-player').src='{{ ep.url }}'">{{ ep.name }}</button>
        {% endfor %}
    </div>
</body>
</html>
"""

# --- ৬. রাুটস ও এপিআই (Routes & API) ---

@app.route('/')
def index():
    all_m, t_size = get_combined_stats()
    return render_template_string(INDEX_HTML, movies=all_m, t_count=len(all_m), t_size=t_size)

@app.route('/watch/<db_id>/<m_id>')
def watch(db_id, m_id):
    conf = managed_dbs_col.find_one({'_id': ObjectId(db_id)})
    db = MongoClient(conf['uri'])['movie_content_db']
    movie = db['movies'].find_one({'_id': ObjectId(m_id)})
    return render_template_string(WATCH_HTML, movie=movie)

@app.route('/api/upload_direct', methods=['POST'])
def upload_api():
    if not session.get('logged_in'): return "Unauthorized", 401
    db, db_name, db_id = get_active_db_info()
    if not db: return jsonify({"error": "No DB Selected"}), 400
    
    file = request.files.get('video_file')
    fs = gridfs.GridFS(db)
    file_id = fs.put(file, filename=file.filename, content_type=file.content_type)

    movie_data = {
        'title': request.form.get('title'),
        'poster': request.form.get('poster'),
        'description': request.form.get('desc'),
        'episodes': [{'name': 'Full Quality', 'url': f'/stream/{db_id}/{file_id}'}],
        'created_at': datetime.now()
    }
    db['movies'].insert_one(movie_data)
    return jsonify({"success": True})

@app.route('/stream/<db_id>/<file_id>')
def stream_video(db_id, file_id):
    conf = managed_dbs_col.find_one({'_id': ObjectId(db_id)})
    db = MongoClient(conf['uri'])['movie_content_db']
    fs = gridfs.GridFS(db)
    try:
        grid_out = fs.get(ObjectId(file_id))
        return send_file(io.BytesIO(grid_out.read()), mimetype=grid_out.content_type)
    except: return "File Not Found", 404

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['u'] == ADMIN_USER and request.form['p'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin.index'))
    return """<body style="background:#000; color:white; display:flex; justify-content:center; align-items:center; height:100vh;">
    <form method="POST" style="background:#111; padding:30px; border:1px solid #e50914; border-radius:10px;">
    <h2>Admin Login</h2>
    <input name="u" placeholder="User" style="width:100%; padding:10px; margin-bottom:10px;"><br>
    <input name="p" type="password" placeholder="Pass" style="width:100%; padding:10px; margin-bottom:10px;"><br>
    <button style="width:100%; background:#e50914; color:white; padding:10px; border:none; cursor:pointer;">LOGIN</button></form></body>"""

# কাস্টম পেজ রেজিস্টার করা
@app.before_first_request
def setup_admin_templates():
    with open('upload_page.html', 'w') as f: f.write(UPLOAD_PAGE_HTML)
    # ফ্লাস্ক অ্যাডমিন টেমপ্লেট ফোল্ডারে এটি নিজে সেভ হবে

if __name__ == "__main__":
    # টেমপ্লেট ফাইলটি এডমিন ডিরেক্টরির জন্য তৈরি করা
    if not os.path.exists('templates/admin'): os.makedirs('templates/admin')
    with open('templates/admin/upload_page.html', 'w') as f: f.write(UPLOAD_PAGE_HTML)
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
