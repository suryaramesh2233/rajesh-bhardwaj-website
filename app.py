from flask import Flask, render_template, request, redirect, url_for, session, flash
import os, sqlite3, uuid, re
from functools import wraps
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "site.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE_THIS_BEFORE_DEPLOYMENT")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS admin(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS songs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      subtitle TEXT DEFAULT '',
      cover_url TEXT DEFAULT '',
      youtube_url TEXT DEFAULT '',
      streaming_url TEXT DEFAULT '',
      release_date TEXT DEFAULT '',
      featured INTEGER DEFAULT 0,
      audio_download_url TEXT DEFAULT '',
      video_download_url TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS videos(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      youtube_url TEXT NOT NULL,
      category TEXT DEFAULT 'Video',
      thumbnail_url TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS announcements(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      body TEXT DEFAULT '',
      published INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS gallery(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT DEFAULT '',
      image_url TEXT NOT NULL,
      category TEXT DEFAULT 'Photo',
      sort_order INTEGER DEFAULT 0,
      published INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS members(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      full_name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      mobile TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      membership_plan TEXT DEFAULT 'Annual Member',
      membership_amount INTEGER DEFAULT 199,
      status TEXT DEFAULT 'demo_active',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS enquiries(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL,
      mobile TEXT DEFAULT '',
      subject TEXT DEFAULT 'Business Enquiry',
      event_date TEXT DEFAULT '',
      message TEXT NOT NULL,
      status TEXT DEFAULT 'new',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Safe migrations for older V2 databases.
    song_cols = {r["name"] for r in c.execute("PRAGMA table_info(songs)").fetchall()}
    for col in ["audio_download_url", "video_download_url"]:
        if col not in song_cols:
            c.execute(f"ALTER TABLE songs ADD COLUMN {col} TEXT DEFAULT ''")

    enquiry_cols = {r["name"] for r in c.execute("PRAGMA table_info(enquiries)").fetchall()}
    if "event_date" not in enquiry_cols:
        c.execute("ALTER TABLE enquiries ADD COLUMN event_date TEXT DEFAULT ''")

    video_cols = {r["name"] for r in c.execute("PRAGMA table_info(videos)").fetchall()}
    if "thumbnail_url" not in video_cols:
        c.execute("ALTER TABLE videos ADD COLUMN thumbnail_url TEXT DEFAULT ''")

    member_cols = {r["name"] for r in c.execute("PRAGMA table_info(members)").fetchall()}
    for col, typ in [("membership_status", "TEXT DEFAULT 'demo_active'"), ("expiry_date", "TEXT DEFAULT ''"), ("notes", "TEXT DEFAULT ''")]:
        if col not in member_cols:
            c.execute(f"ALTER TABLE members ADD COLUMN {col} {typ}")

    if not c.execute("SELECT id FROM admin LIMIT 1").fetchone():
        c.execute(
            "INSERT INTO admin(username,password_hash) VALUES (?,?)",
            ("admin", generate_password_hash("ChangeMe123!")),
        )

    defaults = {
        "artist_name": "RAJESH BHARDWAJ",
        "tagline": "Music • Stories • Digital Creator",
        "hero_text": "Songs, stories and the sound of the hills — all in one official space.",
        "business_email": "business@example.com",
        "youtube_url": "https://www.youtube.com/@CR75HITS-RAJESHBHARDWAJ",
        "instagram_url": "https://www.instagram.com/cr_bhandari75?igshid=MzNlNGNkZWQ4Mg==",
        "facebook_url": "https://www.facebook.com/profile.php?id=100092178005125",
        "profile_image": "/static/uploads/profile.jpg",
        "story_title": "A voice from the hills. A story still unfolding.",
        "story_text": "CR75HITS is a creative space built around music, pahadi culture, visual storytelling and the everyday stories that deserve a sound of their own.",
        "story_year": "2021",
        "story_location": "Himachal Pradesh, India",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)", (k, v))

    if not c.execute("SELECT id FROM songs LIMIT 1").fetchone():
        seed = [
            ("Dincharya — The Village Life", "400K+ views", "/static/uploads/poster_dincharya.jpg", "", "", "", 1, "", ""),
            ("Anokha Himachal", "100K+ views", "/static/uploads/poster_himachal.jpg", "", "", "", 0, "", ""),
            ("Jeet Ki ZID", "Song dedicated to all strugglers", "/static/uploads/poster_jeet.jpg", "", "", "", 0, "", ""),
            ("Folk Melodies", "CR 75 HITS", "/static/uploads/poster_folk.jpg", "", "", "", 0, "", ""),
            ("Kahani", "The story of one side love", "/static/uploads/poster_kahani.jpg", "", "", "", 0, "", ""),
            ("Girgit Zamana", "Out Now", "/static/uploads/poster_girgit.jpg", "", "", "", 0, "", ""),
            ("Azad Parinda", "The Ever Savarkar", "/static/uploads/poster_azad.jpg", "", "", "", 0, "", ""),
        ]
        c.executemany("""INSERT INTO songs(title,subtitle,cover_url,youtube_url,streaming_url,release_date,featured,audio_download_url,video_download_url)
                         VALUES(?,?,?,?,?,?,?,?,?)""", seed)

    # Seed the official-channel video catalogue from the supplied channel screenshot.
    # Exact video URLs can be added later from Creator Studio once copied from YouTube.
    if not c.execute("SELECT id FROM videos LIMIT 1").fetchone():
        channel = "https://www.youtube.com/@CR75HITS-RAJESHBHARDWAJ"
        video_seed = [
            ("GIRGIT JAMANA | pahadi Rap song | Rap & Hook", channel, "Latest", "/static/uploads/poster_girgit.jpg"),
            ("JEET KI ZID | New Rap Song 2025", channel, "Latest", "/static/uploads/poster_jeet.jpg"),
            ("KHEDI MASTER | Latest Pahadi Comedy Rap Song", channel, "Comedy", "/static/uploads/poster_himachal.jpg"),
            ("SAVARKA THE EVER VINAYAK POEM", channel, "Poem", "/static/uploads/poster_azad.jpg"),
            ("AZAD PARINDA RAP SONG", channel, "Rap", "/static/uploads/poster_azad.jpg"),
            ("DINCHARYA — The Village Life | Himachali Pahadi Rap Song", channel, "Rap", "/static/uploads/poster_dincharya.jpg"),
            ("Dincharya — Teaser", channel, "Teaser", "/static/uploads/poster_dincharya.jpg"),
            ("Dosti New Rap Song 2022 | Rap & Hook", channel, "Rap", "/static/uploads/poster_kahani.jpg"),
            ("Folk Melodies (Hindi–Pahari–Rap Mashup 2021)", channel, "Mashup", "/static/uploads/poster_folk.jpg"),
            ("ANOKHA HIMACHAL — Cultural Rap Song", channel, "Cultural", "/static/uploads/poster_himachal.jpg"),
            ("KAHANI | The One Sided Love | Rap Song", channel, "Rap", "/static/uploads/poster_kahani.jpg"),
        ]
        c.executemany("INSERT INTO videos(title,youtube_url,category,thumbnail_url) VALUES(?,?,?,?)", video_seed)

    if not c.execute("SELECT id FROM gallery LIMIT 1").fetchone():
        posters = [
            ("Dincharya", "/static/uploads/poster_dincharya.jpg", "Song Poster", 1),
            ("Anokha Himachal", "/static/uploads/poster_himachal.jpg", "Song Poster", 2),
            ("Jeet Ki ZID", "/static/uploads/poster_jeet.jpg", "Song Poster", 3),
            ("Folk Melodies", "/static/uploads/poster_folk.jpg", "Song Poster", 4),
            ("Kahani", "/static/uploads/poster_kahani.jpg", "Song Poster", 5),
            ("Girgit Zamana", "/static/uploads/poster_girgit.jpg", "Song Poster", 6),
            ("Azad Parinda", "/static/uploads/poster_azad.jpg", "Song Poster", 7),
        ]
        c.executemany("INSERT INTO gallery(title,image_url,category,sort_order,published) VALUES(?,?,?,?,1)", posters)

    c.commit()
    c.close()


def setting(key):
    c = db()
    row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    c.close()
    return row["value"] if row else ""


def set_setting(key, value):
    c = db()
    c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", (key, value))
    c.commit()
    c.close()


def valid_mobile(value):
    digits = re.sub(r"\D", "", value or "")
    return len(digits) == 10 and digits[0] in "6789"


def valid_email(value):
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", value or ""))


def member_login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("member_id"):
            return redirect(url_for("member_login"))
        return fn(*args, **kwargs)
    return wrapper


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_image(file_storage, prefix="image"):
    if not file_storage or not file_storage.filename:
        return ""
    if not allowed_image(file_storage.filename):
        raise ValueError("Only JPG, PNG, WEBP or GIF images are allowed.")
    data = file_storage.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image is too large. Maximum size is 5 MB.")
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"
    (UPLOAD_DIR / filename).write_bytes(data)
    return f"/static/uploads/{filename}"


def youtube_id(url):
    if not url:
        return ""
    patterns = [r"youtu\.be/([\w-]{6,})", r"youtube\.com/watch\?v=([\w-]{6,})", r"youtube\.com/embed/([\w-]{6,})", r"youtube\.com/shorts/([\w-]{6,})"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


@app.template_filter("yt_thumb")
def yt_thumb(url):
    vid = youtube_id(url)
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""


@app.context_processor
def common():
    return {"artist_name": setting("artist_name"), "youtube_url": setting("youtube_url"), "member_logged_in": bool(session.get("member_id"))}


@app.route("/")
def home():
    c = db()
    songs = c.execute("SELECT * FROM songs ORDER BY featured DESC, id DESC").fetchall()
    videos = c.execute("SELECT * FROM videos ORDER BY id DESC").fetchall()
    announcements = c.execute("SELECT * FROM announcements WHERE published=1 ORDER BY id DESC").fetchall()
    gallery = c.execute("SELECT * FROM gallery WHERE published=1 ORDER BY sort_order ASC,id DESC").fetchall()
    c.close()
    return render_template(
        "home.html", songs=songs, videos=videos, announcements=announcements, gallery=gallery,
        tagline=setting("tagline"), hero_text=setting("hero_text"),
        instagram_url=setting("instagram_url"), business_email=setting("business_email"),
        profile_image=setting("profile_image") or "/static/uploads/profile.jpg",
        story_title=setting("story_title"), story_text=setting("story_text"),
        story_year=setting("story_year"), story_location=setting("story_location")
    )


@app.route("/music")
def music_library():
    c = db()
    songs = c.execute("SELECT * FROM songs ORDER BY featured DESC, CASE WHEN release_date = '' THEN 1 ELSE 0 END, release_date DESC, id DESC").fetchall()
    c.close()
    return render_template("music.html", songs=songs)


@app.route("/videos")
def video_hub():
    c = db()
    videos = c.execute("SELECT * FROM videos ORDER BY id DESC").fetchall()
    c.close()
    return render_template("videos.html", videos=videos)


@app.route("/story")
def story():
    c = db()
    gallery = c.execute("SELECT * FROM gallery WHERE published=1 ORDER BY sort_order ASC,id DESC LIMIT 6").fetchall()
    c.close()
    return render_template(
        "story.html", story_title=setting("story_title"), story_text=setting("story_text"),
        story_year=setting("story_year"), story_location=setting("story_location"),
        tagline=setting("tagline"), profile_image=setting("profile_image") or "/static/uploads/profile.jpg", gallery=gallery
    )


@app.route("/gallery")
def gallery_page():
    c = db()
    gallery = c.execute("SELECT * FROM gallery WHERE published=1 ORDER BY sort_order ASC,id DESC").fetchall()
    categories = [r["category"] for r in c.execute("SELECT DISTINCT category FROM gallery WHERE published=1 ORDER BY category").fetchall()]
    c.close()
    return render_template("gallery.html", gallery=gallery, categories=categories)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        mobile = re.sub(r"\D", "", request.form.get("mobile", ""))
        subject = request.form.get("subject", "Business Enquiry").strip() or "Business Enquiry"
        event_date = request.form.get("event_date", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not valid_email(email) or not message or not event_date:
            flash("Please enter your name, a valid email, the proposed date and your message.", "error")
        elif mobile and not valid_mobile(mobile):
            flash("Please enter a valid 10-digit Indian mobile number or leave it blank.", "error")
        else:
            c = db()
            c.execute("INSERT INTO enquiries(name,email,mobile,subject,event_date,message) VALUES(?,?,?,?,?,?)", (name,email,mobile,subject,event_date,message))
            c.commit(); c.close()
            flash("Thanks — your enquiry has been received. The creator team can follow up from Creator Studio.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html", business_email=setting("business_email"), youtube_url=setting("youtube_url"), instagram_url=setting("instagram_url"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        c = db(); user = c.execute("SELECT * FROM admin WHERE username=?", (username,)).fetchone(); c.close()
        if user and check_password_hash(user["password_hash"], password):
            session.pop("member_id", None)
            session["admin_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/member/register", methods=["GET", "POST"])
def member_register():
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        mobile = re.sub(r"\D", "", request.form.get("mobile", ""))
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not valid_email(email) or not valid_mobile(mobile):
            flash("Please enter a valid name, email and 10-digit Indian mobile number.", "error")
        elif len(password) < 8 or password != confirm:
            flash("Password must be at least 8 characters and both password fields must match.", "error")
        else:
            c = db()
            try:
                cur = c.execute("INSERT INTO members(full_name,email,mobile,password_hash,membership_plan,membership_amount,status,membership_status,expiry_date,notes) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (name,email,mobile,generate_password_hash(password),"Annual Member",199,"demo_active","active","","Prototype membership; payment pending launch."))
                c.commit(); member_id = cur.lastrowid
                session.clear(); session["member_id"] = member_id
                c.close()
                return redirect(url_for("member_account"))
            except sqlite3.IntegrityError:
                c.close(); flash("An account with this email already exists. Please sign in.", "error")
    return render_template("member_register.html")


@app.route("/member/login", methods=["GET", "POST"])
def member_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        c = db(); user = c.execute("SELECT * FROM members WHERE email=?", (email,)).fetchone(); c.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear(); session["member_id"] = user["id"]
            return redirect(url_for("member_account"))
        flash("Email or password is incorrect.", "error")
    return render_template("member_login.html")


@app.route("/member")
@member_login_required
def member_account():
    c = db(); member = c.execute("SELECT * FROM members WHERE id=?", (session["member_id"],)).fetchone(); c.close()
    if not member:
        session.clear(); return redirect(url_for("member_login"))
    return render_template("member_account.html", member=member)


@app.route("/member/logout")
def member_logout():
    session.pop("member_id", None)
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin")
@login_required
def dashboard():
    c = db()
    counts = {t: c.execute(f"SELECT COUNT(*) n FROM {t}").fetchone()["n"] for t in ["songs", "videos", "gallery", "announcements", "enquiries", "members"]}
    songs = c.execute("SELECT * FROM songs ORDER BY featured DESC,id DESC").fetchall()
    videos = c.execute("SELECT * FROM videos ORDER BY id DESC").fetchall()
    gallery = c.execute("SELECT * FROM gallery ORDER BY sort_order ASC,id DESC").fetchall()
    announcements = c.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()
    enquiries = c.execute("SELECT * FROM enquiries ORDER BY id DESC").fetchall()
    members = c.execute("SELECT * FROM members ORDER BY id DESC").fetchall()
    c.close()
    settings = {k: setting(k) for k in ["artist_name", "tagline", "hero_text", "business_email", "youtube_url", "instagram_url", "facebook_url", "profile_image", "story_title", "story_text", "story_year", "story_location"]}
    return render_template("dashboard.html", counts=counts, songs=songs, videos=videos, gallery=gallery, announcements=announcements, enquiries=enquiries, members=members, settings=settings)


@app.post("/admin/settings")
@login_required
def update_settings():
    keys = ["artist_name", "tagline", "hero_text", "business_email", "youtube_url", "instagram_url", "facebook_url", "story_title", "story_text", "story_year", "story_location"]
    c = db()
    for key in keys:
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", (key, request.form.get(key, "").strip()))
    c.commit(); c.close()
    profile = request.files.get("profile_image")
    if profile and profile.filename:
        try:
            path = save_image(profile, "profile")
            set_setting("profile_image", path)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("dashboard"))
    flash("Homepage updated.", "success")
    return redirect(url_for("dashboard"))


@app.post("/admin/song")
@login_required
def add_song():
    cover = request.files.get("cover_image")
    cover_url = request.form.get("cover_url", "").strip()
    try:
        if cover and cover.filename:
            cover_url = save_image(cover, "poster")
    except ValueError as e:
        flash(str(e), "error"); return redirect(url_for("dashboard"))
    c = db()
    c.execute("""INSERT INTO songs(title,subtitle,cover_url,youtube_url,streaming_url,release_date,featured,audio_download_url,video_download_url)
      VALUES(?,?,?,?,?,?,?,?,?)""", (
        request.form.get("title", "").strip(), request.form.get("subtitle", "").strip(), cover_url,
        request.form.get("youtube_url", "").strip(), request.form.get("streaming_url", "").strip(), request.form.get("release_date", "").strip(),
        1 if request.form.get("featured") else 0, request.form.get("audio_download_url", "").strip(), request.form.get("video_download_url", "").strip()))
    c.commit(); c.close(); flash("Song added.", "success"); return redirect(url_for("dashboard"))


@app.post("/admin/song/<int:id>/edit")
@login_required
def edit_song(id):
    cover = request.files.get("cover_image")
    c = db(); old = c.execute("SELECT cover_url FROM songs WHERE id=?", (id,)).fetchone()
    if not old:
        c.close(); flash("Song not found.", "error"); return redirect(url_for("dashboard"))
    cover_url = request.form.get("cover_url", "").strip() or old["cover_url"]
    try:
        if cover and cover.filename:
            cover_url = save_image(cover, "poster")
    except ValueError as e:
        c.close(); flash(str(e), "error"); return redirect(url_for("dashboard"))
    c.execute("""UPDATE songs SET title=?,subtitle=?,cover_url=?,youtube_url=?,streaming_url=?,release_date=?,featured=?,audio_download_url=?,video_download_url=? WHERE id=?""", (
        request.form.get("title", "").strip(), request.form.get("subtitle", "").strip(), cover_url,
        request.form.get("youtube_url", "").strip(), request.form.get("streaming_url", "").strip(), request.form.get("release_date", "").strip(),
        1 if request.form.get("featured") else 0, request.form.get("audio_download_url", "").strip(), request.form.get("video_download_url", "").strip(), id))
    c.commit(); c.close(); flash("Song updated.", "success"); return redirect(url_for("dashboard"))


@app.post("/admin/song/<int:id>/delete")
@login_required
def delete_song(id):
    c = db(); c.execute("DELETE FROM songs WHERE id=?", (id,)); c.commit(); c.close(); flash("Song deleted.", "success"); return redirect(url_for("dashboard"))


@app.post("/admin/video")
@login_required
def add_video():
    c = db(); c.execute("INSERT INTO videos(title,youtube_url,category,thumbnail_url) VALUES(?,?,?,?)", (
        request.form.get("title", "").strip(), request.form.get("youtube_url", "").strip(), request.form.get("category", "Video").strip(), request.form.get("thumbnail_url", "").strip()))
    c.commit(); c.close(); flash("Video added.", "success"); return redirect(url_for("dashboard"))


@app.post("/admin/video/<int:id>/edit")
@login_required
def edit_video(id):
    c = db(); c.execute("UPDATE videos SET title=?,youtube_url=?,category=?,thumbnail_url=? WHERE id=?", (
        request.form.get("title", "").strip(), request.form.get("youtube_url", "").strip(), request.form.get("category", "Video").strip(), request.form.get("thumbnail_url", "").strip(), id))
    c.commit(); c.close(); flash("Video updated.", "success"); return redirect(url_for("dashboard"))


@app.post("/admin/video/<int:id>/delete")
@login_required
def delete_video(id):
    c = db(); c.execute("DELETE FROM videos WHERE id=?", (id,)); c.commit(); c.close(); flash("Video deleted.", "success"); return redirect(url_for("dashboard"))


@app.post("/admin/gallery")
@login_required
def add_gallery():
    upload = request.files.get("image")
    try:
        image_url = save_image(upload, "gallery") if upload and upload.filename else request.form.get("image_url", "").strip()
    except ValueError as e:
        flash(str(e), "error"); return redirect(url_for("dashboard"))
    if not image_url:
        flash("Please upload an image or provide an image URL.", "error"); return redirect(url_for("dashboard"))
    c = db(); c.execute("INSERT INTO gallery(title,image_url,category,sort_order,published) VALUES(?,?,?,?,?)", (
        request.form.get("title", "").strip(), image_url, request.form.get("category", "Photo").strip(), int(request.form.get("sort_order") or 0), 1 if request.form.get("published") else 0))
    c.commit(); c.close(); flash("Gallery item added.", "success"); return redirect(url_for("dashboard"))


@app.post("/admin/gallery/<int:id>/edit")
@login_required
def edit_gallery(id):
    upload = request.files.get("image")
    c = db(); old = c.execute("SELECT image_url FROM gallery WHERE id=?", (id,)).fetchone()
    if not old:
        c.close(); flash("Gallery item not found.", "error"); return redirect(url_for("dashboard"))
    image_url = request.form.get("image_url", "").strip() or old["image_url"]
    try:
        if upload and upload.filename:
            image_url = save_image(upload, "gallery")
    except ValueError as e:
        c.close(); flash(str(e), "error"); return redirect(url_for("dashboard"))
    c.execute("UPDATE gallery SET title=?,image_url=?,category=?,sort_order=?,published=? WHERE id=?", (
        request.form.get("title", "").strip(), image_url, request.form.get("category", "Photo").strip(), int(request.form.get("sort_order") or 0), 1 if request.form.get("published") else 0, id))
    c.commit(); c.close(); flash("Gallery item updated.", "success"); return redirect(url_for("dashboard"))


@app.post("/admin/gallery/<int:id>/delete")
@login_required
def delete_gallery(id):
    c = db(); c.execute("DELETE FROM gallery WHERE id=?", (id,)); c.commit(); c.close(); flash("Gallery item deleted.", "success"); return redirect(url_for("dashboard"))


@app.post("/admin/member/<int:id>/status")
@login_required
def member_status(id):
    status = request.form.get("membership_status", "active")
    if status not in {"active", "pending", "expired", "suspended"}:
        status = "pending"
    c = db(); c.execute("UPDATE members SET membership_status=?, status=? WHERE id=?", (status, status, id)); c.commit(); c.close()
    flash("Member status updated.", "success")
    return redirect(url_for("dashboard"))

@app.post("/admin/member/<int:id>/edit")
@login_required
def edit_member(id):
    name = request.form.get("full_name", "").strip()
    mobile = re.sub(r"\D", "", request.form.get("mobile", ""))
    email = request.form.get("email", "").strip().lower()
    expiry = request.form.get("expiry_date", "").strip()
    notes = request.form.get("notes", "").strip()
    if not name or not valid_email(email) or not valid_mobile(mobile):
        flash("Please enter a valid name, email and 10-digit mobile number.", "error")
        return redirect(url_for("dashboard"))
    c = db()
    try:
        c.execute("UPDATE members SET full_name=?,email=?,mobile=?,expiry_date=?,notes=? WHERE id=?", (name,email,mobile,expiry,notes,id))
        c.commit(); flash("Member details updated.", "success")
    except sqlite3.IntegrityError:
        flash("That email address is already used by another member.", "error")
    finally:
        c.close()
    return redirect(url_for("dashboard"))

@app.post("/admin/member/<int:id>/delete")
@login_required
def delete_member(id):
    c = db(); c.execute("DELETE FROM members WHERE id=?", (id,)); c.commit(); c.close()
    flash("Member deleted.", "success")
    return redirect(url_for("dashboard"))

@app.post("/admin/member/<int:id>/reset")
@login_required
def reset_member_password(id):
    new_password = request.form.get("new_password", "")
    if len(new_password) < 8:
        flash("Member password must be at least 8 characters.", "error")
        return redirect(url_for("dashboard"))
    c = db(); c.execute("UPDATE members SET password_hash=? WHERE id=?", (generate_password_hash(new_password), id)); c.commit(); c.close()
    flash("Member password reset.", "success")
    return redirect(url_for("dashboard"))

@app.post("/admin/password")
@login_required
def change_password():
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")
    if len(new) < 10 or new != confirm:
        flash("New password must be at least 10 characters and both fields must match.", "error"); return redirect(url_for("dashboard"))
    c = db(); user = c.execute("SELECT password_hash FROM admin WHERE id=?", (session["admin_id"],)).fetchone()
    if not user or not check_password_hash(user["password_hash"], current):
        c.close(); flash("Current password is incorrect.", "error"); return redirect(url_for("dashboard"))
    c.execute("UPDATE admin SET password_hash=? WHERE id=?", (generate_password_hash(new), session["admin_id"]))
    c.commit(); c.close(); flash("Password changed successfully.", "success"); return redirect(url_for("dashboard"))


@app.errorhandler(413)
def too_large(_):
    flash("Upload is too large. Please keep images/files within the allowed size.", "error")
    return redirect(request.referrer or url_for("dashboard"))


init_db()

@app.post("/admin/enquiry/<int:id>/status")
@login_required
def enquiry_status(id):
    status = request.form.get("status", "read")
    if status not in {"new", "read", "closed"}:
        status = "read"
    c = db(); c.execute("UPDATE enquiries SET status=? WHERE id=?", (status, id)); c.commit(); c.close()
    flash("Enquiry status updated.", "success")
    return redirect(url_for("dashboard"))


@app.post("/admin/enquiry/<int:id>/delete")
@login_required
def delete_enquiry(id):
    c = db(); c.execute("DELETE FROM enquiries WHERE id=?", (id,)); c.commit(); c.close()
    flash("Enquiry deleted.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, host="127.0.0.1", port=5000)
