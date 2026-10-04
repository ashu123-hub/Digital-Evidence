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
| 🛡️ **Zero Raw File Exposure** | Raw evidence files never leave the server; in-browser preview is disabled to prevent browser cache leakage |
| 📜 **Cryptographic Hash Certificates** | Downloads provide an official `.hash` certificate with SHA-256 checksum and CLI verification steps |
| 🔍 **SHA-256 Integrity Verification** | Cryptographic hash verification engine detects any byte-level tampering via the Avalanche Effect |
| 📋 **Chain of Custody** | Immutable, tamper-evident audit trail chained with cryptographic block hashes (ISO/IEC 27037 aligned) |
| 🔑 **Access Code Protection** | Optional per-file PIN/passphrase protection with bcrypt hashing |
| 👥 **Role-Based Access Control** | Admin, Investigator, and Analyst roles |
| 📊 **Audit Logs** | Complete system-wide audit logging of all actions with IP and timestamp |
| 📄 **PDF Reports** | Generate forensic evidence reports with ReportLab |
| 🗑️ **Secure Deletion** | Removes encrypted files, DB records, and custody chain |

---

## 🔒 Forensic Integrity & Tamper-Detection Model

### Why Raw Files Do Not Download:
In professional cyber forensics, digital evidence must be protected from contamination:
1. **Evidence Stays Encrypted at Rest:** Files uploaded to DEMS are stored exclusively as AES-256-CBC `.enc` files.
2. **Hash Certificates Instead of Raw Files:** When evidence is downloaded, DEMS generates and returns a **SHA-256 Hash Certificate (`.hash`)**. The certificate contains:
   - Evidence ID, File Name, and File Type
   - Case ID, Uploaded By, and Upload Timestamp
   - Downloader identity and UTC download timestamp
   - The authoritative 64-character SHA-256 checksum
   - Forensic verification commands for Windows (`certutil`), Linux (`sha256sum`), and macOS (`shasum`)
3. **In-Browser Decryption Disabled:** Browser previews are disabled across all file types (images, PDFs, videos, text, and documents) to prevent cached local copies and unauthorized screengrabs.

### How Tampering Is Detected:
- **Baseline Hash:** At upload time, the file's raw SHA-256 hash is computed and stored immutably in MongoDB and sealed into the Chain of Custody.
- **Verification Engine:** When **"Run Integrity Verification"** is triggered, DEMS decrypts the stored `.enc` file in an isolated temporary memory buffer and computes a fresh SHA-256 hash.
- **The Avalanche Effect:** If an attacker modifies even a single byte or bit in storage, the new hash completely changes. The system immediately flags the evidence as **`TAMPERED`** (status turns RED), generates a high-severity audit alert, and permanently appends the violation to the Chain of Custody.

---

## 🖥️ Screenshots

> Login → Dashboard → Evidence Management → Encrypted Details View → Integrity Verification & Chain of Custody

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
cd Digital-Evidence/DEMS
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
│   ├── evidence.py         # Evidence upload, encrypted view, hash certificate download
│   ├── verification.py     # Integrity verification & tampering detection engine
│   └── reports.py          # PDF report generation
│
├── security/
│   └── crypto_utils.py     # AES-256 encrypt/decrypt, SHA-256, bcrypt, custody hash chaining
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
| View Evidence Status & Details | ✅ | ✅ | ✅ |
| Upload Evidence | ✅ | ✅ | ❌ |
| Download Hash Certificate | ✅ | ✅ | ✅ |
| Verify Integrity | ✅ | ✅ | ✅ |
| Delete Evidence | ✅ | ✅ | ❌ |
| Manage Users | ✅ | ❌ | ❌ |
| View Audit Logs | ✅ | ✅ | ✅ |
| Generate Reports | ✅ | ✅ | ✅ |

---

## 🔐 Security Features

- **AES-256-CBC** encryption for all evidence files stored on disk.
- **SHA-256** cryptographic hash verification — detects file tampering via the Avalanche Effect.
- **Cryptographic Hash Certificate Generation** — issues verifiable `.hash` certificates instead of raw files.
- **bcrypt** password hashing (never stores plain passwords).
- **Per-file access codes** — optional PIN protection per evidence item.
- **Immutable audit logs** — every action is logged with IP, user, and timestamp.
- **Chain of custody** — cryptographically chained records (`record_hash = SHA256(data + prev_hash)`).
- **Zero raw file leakage** — in-browser media rendering and raw downloads disabled across all evidence types.

---

## 📋 Evidence Types Supported

| Type | Extensions | Storage & Verification | Download Type |
|---|---|---|---|
| Images | jpg, jpeg, png, gif, bmp, webp | 🔒 AES-256 Encrypted | 📜 `.hash` Certificate |
| PDFs | pdf | 🔒 AES-256 Encrypted | 📜 `.hash` Certificate |
| Text/Logs | txt, log, csv, json, xml, md | 🔒 AES-256 Encrypted | 📜 `.hash` Certificate |
| Video | mp4, avi, mov, mkv, webm | 🔒 AES-256 Encrypted | 📜 `.hash` Certificate |
| Audio | mp3, wav, aac, ogg, flac | 🔒 AES-256 Encrypted | 📜 `.hash` Certificate |
| Documents | doc, docx, xls, xlsx, ppt, pptx | 🔒 AES-256 Encrypted | 📜 `.hash` Certificate |
| Archives | zip, tar, gz, 7z, rar | 🔒 AES-256 Encrypted | 📜 `.hash` Certificate |
| Email | eml, msg | 🔒 AES-256 Encrypted | 📜 `.hash` Certificate |

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
