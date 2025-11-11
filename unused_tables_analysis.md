# RDS 테이블 사용 여부 분석 결과

## API에서 사용되지 않는 테이블 (4개)

다음 테이블들은 모델 정의만 있고 실제 API 엔드포인트에서 직접 쿼리되지 않습니다:

1. **blog_posts** - 모델만 정의되어 있고 API에서 사용되지 않음
2. **blog_rankings** - 모델만 정의되어 있고 API에서 사용되지 않음
3. **instagram_posts** - 모델만 정의되어 있고 API에서 사용되지 않음
4. **instagram_reels** - 모델만 정의되어 있고 API에서 사용되지 않음

## 참고사항

- **influencer_posts**: 직접 쿼리는 없지만 `InfluencerProfile`의 relationship을 통해 간접적으로 사용됨 (`len(profile.influencer_posts)`)

## 사용 중인 테이블 (21개)

- batch_ingest_sessions
- batch_session_results
- campaign_blog_rankings
- campaign_blogs
- campaign_instagram_posts
- campaign_instagram_reels
- campaign_reel_collection_jobs
- campaign_urls
- campaigns
- classification_jobs
- collection_jobs
- collection_schedules
- influencer_analysis
- influencer_classification_overrides
- influencer_classification_summaries
- influencer_profiles
- influencer_reels
- instagram_grade_thresholds
- reel_classifications
- system_prompts

