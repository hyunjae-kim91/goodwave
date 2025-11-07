# PostgreSQL 시퀀스 리셋 가이드

## 문제 상황

다음과 같은 에러가 발생하는 경우:

```
UniqueViolation: duplicate key value violates unique constraint "influencer_analysis_pkey"
DETAIL: Key (id)=(13) already exists.
```

이는 PostgreSQL의 시퀀스(sequence)가 테이블의 실제 최대 ID보다 낮은 값을 가리키고 있어서 발생하는 문제입니다.

---

## 해결 방법 (3가지)

### ✅ 방법 1: 자동 복구 (권장) - 이미 적용됨!

**더 이상 조치 불필요!** 시스템이 자동으로 처리합니다.

`InfluencerAnalysis` 저장 시 ID 중복 에러가 발생하면:
1. 자동으로 시퀀스를 리셋
2. 작업을 재시도 (최대 2회)
3. 성공 시 정상 진행

**코드에 이미 적용되어 있습니다:**
- `backend/app/services/influencer_service.py`의 `save_analysis_result()` 메서드
- `backend/app/utils/sequence_fixer.py`의 자동 복구 유틸리티

---

### 방법 2: API를 통한 수동 리셋

#### 2-1. 모든 테이블 시퀀스 리셋

```bash
# curl 사용
curl -X POST http://localhost:8000/api/admin/fix-sequences

# PowerShell (Windows)
Invoke-WebRequest -Uri http://localhost:8000/api/admin/fix-sequences -Method POST
```

#### 2-2. 특정 테이블만 리셋

```bash
# 예시: influencer_analysis 테이블만
curl -X POST http://localhost:8000/api/admin/fix-sequence/influencer_analysis

# PowerShell
Invoke-WebRequest -Uri http://localhost:8000/api/admin/fix-sequence/influencer_analysis -Method POST
```

---

### 방법 3: Python 스크립트 실행

```bash
cd backend
python fix_sequences.py
```

**출력 예시:**
```
============================================================
PostgreSQL 시퀀스 리셋 시작
============================================================

✅ influencer_analysis: 시퀀스를 22로 리셋했습니다 (현재 최대 ID: 21)
✅ influencer_profiles: 시퀀스를 96으로 리셋했습니다 (현재 최대 ID: 95)
✅ influencer_reels: 시퀀스를 2301로 리셋했습니다 (현재 최대 ID: 2300)
...

============================================================
✅ 모든 시퀀스 리셋 완료!
============================================================
```

---

## 지원되는 테이블

자동으로 시퀀스가 리셋되는 테이블 목록:

- `influencer_analysis` ⭐ (주요 문제 발생 테이블)
- `influencer_profiles`
- `influencer_reels`
- `influencer_posts`
- `influencer_classification_summaries`
- `classification_jobs`
- `collection_jobs`
- `campaigns`
- `campaign_urls`
- `campaign_instagram_reels`
- `campaign_blogs`

---

## 로그 확인

시퀀스 자동 복구 로그는 다음과 같이 출력됩니다:

```
⚠️  'influencer_analysis'에서 ID 중복 에러 감지 - 시퀀스 자동 리셋 시도
✅ 'influencer_analysis' 시퀀스를 22로 리셋했습니다 (최대 ID: 21)
✅ 'influencer_analysis' 시퀀스 자동 리셋 완료
🔄 'influencer_analysis' 작업 재시도 중 (시도 2/3)
```

---

## 예방 방법

### 1. 모델에 autoincrement 명시

```python
# ✅ 올바른 방법
id = Column(Integer, primary_key=True, index=True, autoincrement=True)

# ❌ 문제가 될 수 있음
id = Column(Integer, primary_key=True, index=True)
```

### 2. 직접 ID 지정 금지

```python
# ❌ 절대 하지 마세요!
obj = InfluencerAnalysis(id=123, ...)

# ✅ ID는 자동으로 생성되도록
obj = InfluencerAnalysis(profile_id=1, ...)
```

### 3. 데이터 복원 시 주의

SQL 덤프를 복원한 후에는 반드시 시퀀스를 리셋하세요:

```bash
python fix_sequences.py
```

---

## 트러블슈팅

### Q: 여전히 에러가 발생해요

**A:** 다음을 확인하세요:
1. 백엔드 재시작 (변경사항 적용)
2. API로 수동 리셋: `POST /api/admin/fix-sequences`
3. 로그 확인: 자동 복구가 실행되었는지 확인

### Q: 다른 테이블에서도 같은 문제가 발생해요

**A:** `backend/app/utils/sequence_fixer.py`의 `fix_all_sequences()` 함수에 테이블을 추가하세요:

```python
tables = [
    'influencer_analysis',
    'your_new_table',  # 여기에 추가
    ...
]
```

### Q: 자동 복구가 작동하지 않아요

**A:** 해당 서비스의 저장 메서드에서 `safe_db_operation`을 사용하도록 수정하세요:

```python
from app.utils.sequence_fixer import safe_db_operation

def save_something(self):
    def _save():
        # 저장 로직
        pass
    
    return safe_db_operation(
        self.db,
        _save,
        'table_name',
        max_retries=2
    )
```

---

## 참고

- **자동 복구**: `backend/app/utils/sequence_fixer.py`
- **API 엔드포인트**: `backend/app/api/admin.py`
- **스크립트**: `backend/fix_sequences.py`
- **적용된 서비스**: `backend/app/services/influencer_service.py`

