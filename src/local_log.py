"""데이터 입력 로그를 로컬 CSV에 append-only로 기록한다.

같은 배포 인스턴스를 쓰는 팀원들은 이 파일을 공유해서 본다(Streamlit이 서버 하나로
여러 사용자를 처리하기 때문). 재배포·슬립 이후에도 남기고 싶으면 GitHub 백업
(src/github_sync.py, '⚙️ 설정'에서 켤 수 있음)을 함께 쓸 것.
"""

import csv
from pathlib import Path


def append_row(csv_path: Path, columns: list, row: dict):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if is_new:
            writer.writeheader()
        writer.writerow({c: row.get(c, "") for c in columns})
