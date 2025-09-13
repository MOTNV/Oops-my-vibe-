import sqlite3
import json
from googleapiclient.discovery import build

# ─── 설정 부분 ─────────────────────────────
API_KEY      = 'YOUR_API_KEY'      # YouTube Data API 키
DB_FILENAME  = 'USER.SQL'          # SQLite 파일명
TABLE_NAME   = 'youtube_id'        # 테이블명
ID_COLUMN    = 'id'                # youtube_id 테이블의 ID 컬럼명
BATCH_SIZE   = 50                  # 한 번에 조회할 ID 개수
# ────────────────────────────────────────────

def fetch_all_ids(conn):
  cursor = conn.cursor()
  cursor.execute(f"SELECT {ID_COLUMN} FROM {TABLE_NAME}")
  return [row[0] for row in cursor.fetchall()]

def delete_ids(conn, ids_to_delete):
  cursor = conn.cursor()
  cursor.executemany(
    f"DELETE FROM {TABLE_NAME} WHERE {ID_COLUMN} = ?",
    [(vid,) for vid in ids_to_delete]
  )
  conn.commit()
  print(f"삭제된 ID 개수: {len(ids_to_delete)}")

def filter_embeddable(ids):
  youtube = build('youtube', 'v3', developerKey=API_KEY)
  embeddable, not_embeddable = [], []

  for i in range(0, len(ids), BATCH_SIZE):
    batch = ids[i:i+BATCH_SIZE]
    resp = youtube.videos().list(
      part='status',
      id=','.join(batch)
    ).execute()
    for item in resp.get('items', []):
      vid = item['id']
      if item['status'].get('embeddable'):
        embeddable.append(vid)
      else:
        not_embeddable.append(vid)
        print(f"임베드 불가: {vid}")
  return embeddable, not_embeddable

def main():
  # 1) DB 연결
  conn = sqlite3.connect(DB_FILENAME)
  all_ids = fetch_all_ids(conn)
  print(f"총 ID 개수: {len(all_ids)}")

  # 2) 임베드 가능 여부 필터
  embeddable, not_embeddable = filter_embeddable(all_ids)
  print(f"임베드 가능: {len(embeddable)}, 불가: {len(not_embeddable)}")

  # 3) 불가 ID 삭제
  if not_embeddable:
    delete_ids(conn, not_embeddable)
  conn.close()

if __name__ == '__main__':
  main()
