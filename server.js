const express = require('express');
const session = require('express-session');
const bodyParser = require('body-parser');
const bcrypt = require('bcrypt');
const path = require('path');

const app = express();
const port = 3000;

// ───────────────────────────────────────
// ✅ 미들웨어 설정
app.use(bodyParser.urlencoded({ extended: false }));
app.use(session({
  secret: 'oopsmv-secret-key',
  resave: false,
  saveUninitialized: true
}));

// ✅ 정적 파일 제공 (예: /static/style.css 등)
app.use(express.static(path.join(__dirname, 'oopsmv', 'static')));

// ───────────────────────────────────────
// ✅ 임시 사용자 정보 (비밀번호는 해시로 저장)
const users = {
  jsm: bcrypt.hashSync('1234', 10),  // 아이디: jsm, 비번: 1234
};

// ───────────────────────────────────────
// ✅ 라우트 설정

// 루트 페이지
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'oopsmv', 'templates', 'index.html'));
});

// 로그인 폼 페이지
app.get('/login', (req, res) => {
  res.sendFile(path.join(__dirname, 'oopsmv', 'templates', 'login.html'));
});

// 로그인 처리
app.post('/login', (req, res) => {
  const { username, password } = req.body;
  const hashed = users[username];

  if (hashed && bcrypt.compareSync(password, hashed)) {
    req.session.user = username;
    res.redirect('/dashboard');
  } else {
    res.send('❌ 로그인 실패: 아이디 또는 비밀번호를 확인하세요.');
  }
});

// 대시보드
app.get('/dashboard', (req, res) => {
  if (!req.session.user) return res.redirect('/login');
  res.send(`👋 ${req.session.user}님, 대시보드에 오신 것을 환영합니다.`);
});

// 로그아웃
app.get('/logout', (req, res) => {
  req.session.destroy(() => {
    res.redirect('/');
  });
});

// ───────────────────────────────────────
// ✅ 서버 실행
app.listen(port, '0.0.0.0', () => {
  console.log(`✅ Node.js 서버 실행 중: http://220.68.27.143:${port}`);
});
