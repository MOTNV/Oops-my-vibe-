from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import bcrypt

# FastAPI 앱 생성
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

# 템플릿, 정적 파일 폴더 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 임시 사용자 데이터 (나중에 DB 연동 가능)
users = {
    "jsm": bcrypt.hashpw("1234".encode(), bcrypt.gensalt())  # jsm / 1234
}

# 홈 페이지
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 로그인 폼
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 로그인 처리
@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    hashed = users.get(username)
    if hashed and bcrypt.checkpw(password.encode(), hashed):
        request.session["user"] = username
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "❌ 로그인 실패"})

# 대시보드
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

# 로그아웃
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)
