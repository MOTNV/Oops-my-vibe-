// db.js
const { Pool } = require('pg');

const pool = new Pool({
  user: 'jsm',
  host: 'localhost',
  database: 'oopsmv',
  password: 'yourpassword', // 위에서 만든 패스워드
  port: 5432,
});

module.exports = pool;
