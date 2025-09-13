// insert_user.js
const bcrypt = require('bcrypt');
const db = require('./db');

async function insertUser(username, password) {
  const hash = await bcrypt.hash(password, 10);

  await db.query(`
    WITH new_user AS (
      INSERT INTO users (is_guest) VALUES (false)
      RETURNING user_id
    )
    INSERT INTO credentials (user_id, username, password_hash)
    SELECT user_id, $1, $2 FROM new_user;
  `, [username, hash]);

  console.log('✅ 사용자 등록 완료');
}

insertUser('jsm', '1234');
