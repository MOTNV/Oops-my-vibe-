const mysql = require('mysql2');

const db = mysql.createConnection({
  host: 'localhost',
  user: 'root',
  password: 'Abcd1234!',
  database: 'oopsmv'
});

db.connect((err) => {
  if (err) {
    console.error('❌ DB 연결 실패:', err.message);
  } else {
    console.log('✅ MySQL 연결 성공');
  }
});

module.exports = db;
