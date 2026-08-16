# 🛡️ DEMS — Digital Evidence Management System

<div align="center">
  <img src="https://img.shields.io/badge/Flask-3.1.0-blue?style=for-the-badge&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/MongoDB-4.10-green?style=for-the-badge&logo=mongodb" alt="MongoDB">
  <img src="https://img.shields.io/badge/AES--256-Encrypted-red?style=for-the-badge&logo=lock" alt="AES-256">
  <img src="https://img.shields.io/badge/Python-3.10+-yellow?style=for-the-badge&logo=python" alt="Python">
</div>

<br>

A secure, full-featured **Digital Evidence Management System** for cyber forensics and crime investigation. Built for law enforcement agencies, forensic investigators, and security analysts to securely upload, encrypt, manage, and verify digital evidence with a complete chain of custody.

---

## 🌟 Key Features

| Feature | Description |
|---|---|
| 🔐 **AES-256 Encryption** | All evidence files are encrypted at rest using AES-256-CBC |
| 🔍 **SHA-256 Integrity Verification** | Cryptographic hash verification on every evidence file |
| 📋 **Chain of Custody** | Immutable, tamper-evident audit trail for every evidence action |
| 👁️ **In-Browser Preview** | View PDFs, images, text, video, and audio without downloading |
| 🔑 **Access Code Protection** | Optional per-file PIN/passphrase protection with bcrypt hashing |
| 👥 **Role-Based Access Control** | Admin, Investigator, and Analyst roles |
| 📊 **Audit Logs** | Complete system-wide audit logging of all actions |
| 📄 **PDF Reports** | Generate forensic evidence reports with ReportLab |
| 🗑️ **Secure Deletion** | Removes encrypted files, DB records, and custody chain |

---

## 🖥️ Screenshots

> Login → Dashboard → Evidence Management → In-Browser Preview → Chain of Custody

---

## 🔧 Tech Stack

- **Backend:** Python 3.10+, Flask 3.1
- **Database:** MongoDB (local or Atlas)
- **Encryption:** AES-256-CBC (PyCryptodome)
- **Password Hashing:** bcrypt
- **File Hashing:** SHA-256
- **PDF Reports:** ReportLab
- **Frontend:** Vanilla HTML/CSS/JS, Font Awesome 6, Google Fonts (Inter)
- **Sessions:** Flask-Session (filesystem)

---

## 🚀 Quick Start (Local)

### 1. Prerequisites

- Python 3.10+
- MongoDB running locally (`mongod`) **or** a [MongoDB Atlas](https://www.mongodb.com/atlas) URI

### 2. Clone the Repository

```bash
git clone https://github.com/ashu123-hub/Digital-Evidence.git
cd Digital-Evidence
```

### 3. Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment (Optional)

Create a `.env` file or set these environment variables:

```env
SECRET_KEY=your-super-secret-key-here
MONGO_URI=mongodb://localhost:27017/dems_db
AES_KEY=your-32-byte-aes-key-here
```

> If not set, the app uses secure defaults for local development.

### 6. Run the Application

```bash
python app.py
```

Visit **http://127.0.0.1:5000**

### 7. Default Login Credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@dems.gov` | `Admin@123` |
| Investigator | `investigator@dems.gov` | `Inv@123` |
| Analyst | `analyst@dems.gov` | `Analyst@123` |

---

## 🌐 Deploy to Vercel

> **⚠️ Important:** Vercel is a serverless platform. Evidence files stored via Vercel use ephemeral `/tmp` storage — files do **not** persist between function invocations. For production forensics use, deploy on a persistent server (VPS, Railway, Render) or use cloud file storage (AWS S3).

For a detailed step-by-step Vercel deployment guide, see [VERCEL_DEPLOYMENT.md](./VERCEL_DEPLOYMENT.md).

---

## 📁 Project Structure

```
DEMS/
├── app.py                  # App factory & entry point
├── config.py               # Configuration (env vars, paths, keys)
├── database.py             # MongoDB connection
├── requirements.txt        # Python dependencies
│
├── routes/
│   ├── auth.py             # Login, logout, register
│   ├── main.py             # Dashboard, audit logs, user management
│   ├── cases.py            # Case CRUD
│   ├── evidence.py         # Evidence upload, view, preview, delete
│   ├── verification.py     # Integrity verification
│   └── reports.py          # PDF report generation
│
├── security/
│   └── crypto_utils.py     # AES-256 encrypt/decrypt, SHA-256, bcrypt
│
├── templates/              # Jinja2 HTML templates
├── static/
│   ├── css/style.css       # Full custom dark UI
│   └── js/app.js           # Frontend interactivity
│
├── uploads/                # Temporary upload staging (auto-created)
├── encrypted_evidence/     # AES-encrypted evidence store (auto-created)
├── reports/                # Generated PDF reports (auto-created)
└── flask_session/          # Server-side session files (auto-created)
```

---

## 👥 User Roles & Permissions

| Action | Admin | Investigator | Analyst |
|---|:---:|:---:|:---:|
| View Evidence | ✅ | ✅ | ✅ |
| Upload Evidence | ✅ | ✅ | ❌ |
| Delete Evidence | ✅ | ✅ | ❌ |
| Manage Users | ✅ | ❌ | ❌ |
| View Audit Logs | ✅ | ✅ | ✅ |
| Generate Reports | ✅ | ✅ | ✅ |

---

## 🔐 Security Features

- **AES-256-CBC** encryption for all evidence files
- **SHA-256** hash verification — detects tampering
- **bcrypt** password hashing (never stores plain passwords)
- **Per-file access codes** — additional PIN protection per evidence item
- **Immutable audit logs** — every action is logged with IP, user, and timestamp
- **Chain of custody** — cryptographically chained records
- **Zero disk trace viewing** — evidence is decrypted in-memory and streamed directly to the browser

---

## 📋 Evidence Types Supported

| Type | Extensions | In-Browser Preview |
|---|---|---|
| Images | jpg, jpeg, png, gif, bmp, webp | ✅ Inline viewer |
| PDFs | pdf | ✅ Embedded PDF reader |
| Text/Logs | txt, log, csv, json, xml, md | ✅ Formatted code viewer |
| Video | mp4, avi, mov, mkv, webm | ✅ HTML5 player |
| Audio | mp3, wav, aac, ogg, flac | ✅ HTML5 player |
| Documents | doc, docx, xls, xlsx, ppt, pptx | 📥 Download only |
| Archives | zip, tar, gz, 7z, rar | 📥 Download only |
| Email | eml, msg | 📥 Download only |

---

## 📄 License

MIT License — feel free to use, modify, and distribute.

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first.

---

<div align="center">
  Built with ❤️ for digital forensics and cybercrime investigation
</div>
