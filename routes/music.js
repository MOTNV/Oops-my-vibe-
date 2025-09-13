const express = require('express');
const router = express.Router();
const db = require('../db');  // ../로 상위에서 db.js import

// 음악 등록 폼
router.get('/form', (req, res) => {
  res.sendFile(__dirname + '/../templates/music_form.html');
});

// 음악 등록 처리
router.post('/register', (req, res) => {
  const {
    title, artist, genre, mood,
    duration_sec, file_path, youtube_id,
    weather, time_of_day, theme
  } = req.body;

  const insertMusic = `
    INSERT INTO music (title, artist, genre, mood, duration_sec, file_path, youtube_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `;

  db.query(insertMusic, [title, artist, genre, mood, duration_sec, file_path, youtube_id], (err, result) => {
    if (err) return res.send('❌ 음악 등록 실패: ' + err.message);

    const musicId = result.insertId;

    const insertContext = `
      INSERT INTO music_context (music_id, weather, time_of_day, theme)
      VALUES (?, ?, ?, ?)
    `;

    db.query(insertContext, [musicId, weather, time_of_day, theme], (err) => {
      if (err) return res.send('❌ 컨텍스트 등록 실패: ' + err.message);
      res.send('✅ 음악 + 컨텍스트 등록 완료!');
    });
  });
});

module.exports = router;
