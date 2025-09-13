const express = require('express');
const session = require('express-session');
const bodyParser = require('body-parser');
const axios = require('axios');
const path = require('path');
const musicRouter = require('./routes/music');
const db = require('./db');
const bcrypt = require('bcrypt');


const app = express();
const port = 3000;
const saltRounds = 10; // 비밀번호 해싱을 위한 bcrypt 라운드 수


// ✅ JSON 요청 파싱 미들웨어 추가!
app.use(express.json());
app.use(bodyParser.urlencoded({ extended: true }));

// ───────────────────────────────────────
// ✅ 미들웨어 설정
app.use(bodyParser.urlencoded({ extended: true }));
app.use(session({
  secret: 'oopsmv-secret-key',
  resave: false,
  saveUninitialized: true
}));

// ✅ 정적 파일 제공 (예: /oopsmv/templates/front1.html 등)
app.use(express.static(path.join(__dirname, 'oopsmv', 'templates')));
app.use(express.static(path.join(__dirname, 'public')));

// ✅ 템플릿 디렉토리 경로 변수
const TEMPLATE_DIR = path.join(__dirname, 'oopsmv', 'templates');

// ✅ music 라우터
app.use('/music', musicRouter);

app.get('/music_form', (req, res) => {
  res.sendFile(path.join(__dirname, 'oopsmv', 'templates', 'music_play2.html'));
});

// ───────────────────────────────────────
// ✅ 라우트 설정

// 메인 페이지
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'oopsmv', 'templates', 'front1.html'));
});


// 세션 사용자 정보 API (fetch로 username 가져오기)
app.get('/session-user', (req, res) => {
  if (req.session.username) {
    res.json({ username: req.session.username });
  } else {
    res.json({ username: null });
  }
});

// 회원가입
app.post('/register', async (req, res) => {
  const { username, password, nickname } = req.body;

  try {
    const hashedPassword = await bcrypt.hash(password, saltRounds);
    const sql = 'INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)';
    db.query(sql, [username, hashedPassword, nickname], (err, result) => {
      if (err) {
        console.error('회원가입 실패:', err);
        return res.send('회원가입 실패');
      }
      // 로그인 상태로 만들기 (세션에 사용자 정보 저장)
req.session.user = {
  username: username,
  nickname: nickname
};

// 메인 페이지로 리디렉션
res.redirect('/');

    });
  } catch (error) {
    console.error('서버 오류:', error);
    res.send('서버 오류 발생');
  }
});

// 로그인
app.post('/login', (req, res) => {
  const { username, password } = req.body;

  const sql = 'SELECT * FROM users WHERE username = ?';
  db.query(sql, [username], async (err, results) => {
    if (err) return res.send('서버 오류');
    if (results.length === 0) return res.send('존재하지 않는 사용자입니다.');

    const user = results[0];
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) return res.send('비밀번호가 틀렸습니다.');

    req.session.username = user.username;
    res.send('로그인 성공!'); // 여기서 redirect 말고 '성공!' 텍스트만 반환
  });
});


// 로그아웃
app.get('/logout', (req, res) => {
  req.session.destroy(() => {
    res.redirect('/');
  });
});

app.post('/music/play', async (req, res) => {
  const { emotion, activity, weather } = req.body;

  try {
    const response = await axios.post('http://localhost:5000/recommend', {
      emotion, activity, weather
    });

    // Flask 서버에서 받아온 추천 결과를 클라이언트에 그대로 전달
    res.json(response.data);
  } catch (error) {
    console.error('Flask 서버 호출 실패:', error.message);
    res.status(500).send('추천 처리 실패');
  }
});

// // 위치 저장 요청
// fetch('http://localhost:5000/save_location', {
//   method: 'POST',
//   headers: { 'Content-Type': 'application/json' },
//   body: JSON.stringify({
//     lat: 35.5,
//     lon: 126.7,
//     accuracy: 10
//   })
// }).then(res => res.json()).then(console.log);

// // 위치 기반 음악 추천
// fetch('http://localhost:5000/recommend_with_location', {
//   method: 'POST',
//   headers: { 'Content-Type': 'application/json' },
//   body: JSON.stringify({
//     emotion: "calm"
//   })
// }).then(res => res.json()).then(console.log);


// ───────────────────────────────────────
// ✅ 서버 실행
app.listen(port, '0.0.0.0', () => {
  console.log(`✅ Node.js 서버 실행 중: http://220.68.27.143:${port}`);
});
