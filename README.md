# Rajesh Bhardwaj / CR75HITS — V3 Creator Website

A Flask + SQLite creator website with a premium public site and a stronger Creator Studio.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5000`

If your existing project already has a `.venv`, you can use it instead of creating another one.

## Creator Studio

Open: `http://127.0.0.1:5000/login`

The initial local credentials remain:

- Username: `admin`
- Password: `ChangeMe123!`

**Change the password in Creator Studio before public deployment.**

## V3 additions

- Direct profile image upload from Creator Studio
- Direct song poster upload
- Edit existing songs instead of delete/re-add
- Edit existing YouTube videos
- Automatic YouTube thumbnail preview when a standard YouTube URL is supplied
- Dedicated Gallery database and Creator Studio management
- Existing 7 song posters are automatically seeded into the Gallery on first database initialization
- Gallery upload/edit/delete and visibility controls
- Announcement management
- Admin password change
- Upload validation for JPG/JPEG/PNG/WEBP/GIF images
- 5 MB image limit and 8 MB request limit
- Production debug mode is off by default
- Existing V2 databases are migrated automatically for the new video/gallery fields

## Important before going live

Set a strong environment variable:

```powershell
$env:SECRET_KEY="use-a-long-random-secret-here"
```

Do not publish the default admin password. For production, also use a production WSGI server/host, HTTPS, secure cookies, CSRF protection, rate limiting, proper backups, and object storage for larger media.

The site does not download or rip YouTube content. Download buttons only appear when the creator supplies an authorized media URL.

## V7 additions
- Dedicated Story page with editable story content
- Dedicated Gallery page with category filters
- Dedicated Contact / Business Enquiry form
- Enquiries are stored in SQLite and manageable from Creator Studio
- Admin can mark enquiries New / Read / Closed or delete them
- Homepage now links Story, Gallery and Contact to their dedicated pages
- Creator Studio can edit story title, story text, journey year and location

## V8 additions
- Creator Studio member management: view, edit, status, expiry date, notes, password reset and delete
- Member count in dashboard statistics
- Facebook and Instagram URLs are now preconfigured from the official links supplied by the creator
- Admin settings can edit Facebook URL alongside Instagram and YouTube
- Fixed route registration order so all admin enquiry routes are registered before the development server starts
