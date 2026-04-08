from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
from jose import jwt, JWTError
import uuid

# Config 
SECRET_KEY = "ganti-dengan-secret-key-aman-di-production"
ALGORITHM  = "HS256"

bearer_scheme = HTTPBearer()

# App
app = FastAPI(
    title="Tugas Praktikum IPBD",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory DB
users_db: dict = {}  
blogs_db: list = []   

# Schemas 
class RegisterIn(BaseModel):
    nama:  str
    nim:   str
    kelas: str

class BlogIn(BaseModel):
    judul: str
    isi:   str

# Helpers 
def make_token(nim: str) -> str:
    return jwt.encode({"sub": nim}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        nim: str = payload.get("sub")
        if nim is None or nim not in users_db:
            raise HTTPException(status_code=401, detail="Token tidak valid")
        return users_db[nim]
    except JWTError:
        raise HTTPException(status_code=401, detail="Token tidak valid")

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Routes 
@app.get("/")
def home():
    return FileResponse("frontend.html")

@app.get("/")
def root():
    return {
        "message": "Selamat datang di Blog API",
        "docs":    "/docs",
        "health":  "/health",
    }

@app.post("/api/register", status_code=201)
def register(body: RegisterIn):
    if body.nim in users_db:
        raise HTTPException(status_code=400, detail="NIM sudah terdaftar")
    users_db[body.nim] = {
        "id":         str(uuid.uuid4()),
        "nama":       body.nama,
        "nim":        body.nim,
        "kelas":      body.kelas,
        "created_at": now_str(),
    }
    return {
        "message":      "Registrasi berhasil",
        "nama":         body.nama,
        "nim":          body.nim,
        "kelas":        body.kelas,
        "access_token": make_token(body.nim),
        "token_type":   "bearer",
    }

@app.get("/api/blogs")
def get_blogs():
    result = []
    for b in blogs_db:
        author = users_db.get(b["author_nim"], {})
        result.append({
            "id":           b["id"],
            "judul":        b["judul"],
            "isi":          b["isi"],
            "author_id":    author.get("id", ""),
            "author_nama":  author.get("nama", ""),
            "author_nim":   b["author_nim"],
            "author_kelas": author.get("kelas", ""),
            "created_at":   b["created_at"],
            "updated_at":   b["updated_at"],
        })
    return result

@app.post("/api/blogs", status_code=201)
def create_blog(body: BlogIn, user: dict = Depends(get_current_user)):
    blog = {
        "id":         str(uuid.uuid4()),
        "judul":      body.judul,
        "isi":        body.isi,
        "author_nim": user["nim"],
        "created_at": now_str(),
        "updated_at": now_str(),
    }
    blogs_db.append(blog)
    return {"message": "Blog berhasil dibuat", "id": blog["id"]}

@app.put("/api/blogs/{blog_id}")
def update_blog(blog_id: str, body: BlogIn, user: dict = Depends(get_current_user)):
    for b in blogs_db:
        if b["id"] == blog_id:
            if b["author_nim"] != user["nim"]:
                raise HTTPException(status_code=403, detail="Bukan milik kamu")
            b["judul"]      = body.judul
            b["isi"]        = body.isi
            b["updated_at"] = now_str()
            return {"message": "Blog berhasil diupdate", "id": blog_id}
    raise HTTPException(status_code=404, detail="Blog tidak ditemukan")

@app.delete("/api/blogs/{blog_id}")
def delete_blog(blog_id: str, user: dict = Depends(get_current_user)):
    for i, b in enumerate(blogs_db):
        if b["id"] == blog_id:
            if b["author_nim"] != user["nim"]:
                raise HTTPException(status_code=403, detail="Bukan milik kamu")
            blogs_db.pop(i)
            return {"message": "Blog berhasil dihapus"}
    raise HTTPException(status_code=404, detail="Blog tidak ditemukan")

@app.get("/health")
def health():
    return {
        "status": "ok",
        "users":  len(users_db),
        "blogs":  len(blogs_db),
    }

# Run
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)