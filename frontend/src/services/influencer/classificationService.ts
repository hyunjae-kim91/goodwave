export interface ClassificationRequest {
  username: string;
  prompt?: string;
  classification_type?: string;
}

export interface ClassificationResponse {
  message: string;
  status: string;
  job_id?: string;
}

export interface ClassificationStatus {
  username: string;
  subscription_motivation: {
    exists: boolean;
    last_updated?: string;
    total_images?: number;
  };
  category: {
    exists: boolean;
    last_updated?: string;
    total_images?: number;
  };
}

export interface ClassificationResult {
  username: string;
  classification_type: string;
  prompt: string;
  classified_at: string;
  total_images: number;
  results: Array<{
    image_filename: string;
    classification: string;
    classified_at: string;
    error?: string;
  }>;
}

export interface ClassificationJobItem {
  job_id: string;
  username: string;
  classification_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
}

export type ReelClassificationStatus = 'completed' | 'error' | 'pending';

export interface ReelClassificationDetail {
  label: string | null;
  confidence: number | null;
  reasoning: string | null;
  image_url: string | null;
  raw_response?: Record<string, unknown> | null;
  error?: string | null;
  processed_at?: string | null;
  classification_job_id?: number | null;
  status: ReelClassificationStatus;
}

export interface IndividualReelEntry {
  reel_id: string;
  reel_db_id: number;
  caption?: string | null;
  description?: string | null;
  hashtags?: string[] | null;
  media_urls?: string[] | null;
  likes?: number | null;
  comments?: number | null;
  views?: number | null;
  created_at?: string | null;
  subscription_motivation: ReelClassificationDetail;
  category: ReelClassificationDetail;
}

export interface IndividualReelClassificationResponse {
  username: string;
  profile_id: number;
  total_reels: number;
  reels: IndividualReelEntry[];
}

export interface ClassificationDistributionEntry {
  label: string;
  count: number;
  percentage: number;
  average_confidence: number;
}

export interface AggregatedSummaryStatistics {
  total_reels_processed?: number;
  total_reels_considered?: number;
  successful_classifications?: number;
  failed_classifications?: number;
  success_rate?: number;
  average_confidence_score?: number;
}

export interface AggregatedSummary {
  classification_job_id?: number;
  primary_classification?: string;
  primary_percentage?: number;
  secondary_classification?: string | null;
  secondary_percentage?: number | null;
  classification_distribution: ClassificationDistributionEntry[] | { [key: string]: number };
  statistics?: AggregatedSummaryStatistics;
  method?: string;
  processed_at?: string | null;
  timestamp?: string;
}

export interface AggregatedSummaryResponse {
  username: string;
  aggregated_summaries: { [classification_type: string]: AggregatedSummary };
}

export interface ClassificationOverridePayload {
  primary_label: string;
  primary_percentage?: number;
  secondary_label?: string;
  secondary_percentage?: number;
}

export interface ClassificationOverrideUpdateRequest {
  subscription_motivation?: ClassificationOverridePayload;
  category?: ClassificationOverridePayload;
}

export interface ClassificationDataInfo {
  exists: boolean;
  created_at?: string;
  method?: string;
  primary_classification?: string;
  primary_percentage?: number;
  total_reels?: number;
}

export interface UserWithClassificationData {
  username: string;
  profile_id: number;
  classification_data: {
    subscription_motivation?: ClassificationDataInfo;
    category?: ClassificationDataInfo;
    reel_classification?: ClassificationDataInfo;
  };
}

export interface UsersWithDataResponse {
  users: UserWithClassificationData[];
  total_count: number;
}

export interface DeleteDataResponse {
  success: boolean;
  message: string;
  deleted_count: number;
  classification_type?: string;
}

class ClassificationService {
  private classificationBase = '/api/influencer/classification';
  private queueBase = '/api/influencer/classification-jobs';

  async startSubscriptionMotivationClassification(request: ClassificationRequest): Promise<ClassificationResponse> {
    const response = await fetch(`${this.classificationBase}/subscription-motivation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '구독 동기 분류 시작에 실패했습니다.');
    }

    return response.json();
  }

  async startCategoryClassification(request: ClassificationRequest): Promise<ClassificationResponse> {
    const response = await fetch(`${this.classificationBase}/category`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '카테고리 분류 시작에 실패했습니다.');
    }

    return response.json();
  }

  async getClassificationStatus(username: string): Promise<ClassificationStatus> {
    const response = await fetch(`${this.classificationBase}/status/${username}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '분류 상태 조회에 실패했습니다.');
    }

    return response.json();
  }

  async getSubscriptionMotivationResult(username: string): Promise<ClassificationResult> {
    const response = await fetch(`/api/classification-result/${username}/subscription_motivation`);

    if (!response.ok) {
      throw new Error('구독 동기 분류 결과를 찾을 수 없습니다.');
    }

    return response.json();
  }

  async getCategoryResult(username: string): Promise<ClassificationResult> {
    const response = await fetch(`/api/classification-result/${username}/category`);

    if (!response.ok) {
      throw new Error('카테고리 분류 결과를 찾을 수 없습니다.');
    }

    return response.json();
  }

  async startCombinedClassification(username: string, promptType?: string): Promise<ClassificationResponse> {
    const payload: Record<string, unknown> = {
      username,
      classification_type: 'combined',
    };
    if (promptType) {
      payload.prompt_type = promptType;
    }
    const response = await fetch(`${this.classificationBase}/combined`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '통합 분류 시작에 실패했습니다.');
    }
    return response.json();
  }

  async parseSubscriptionMotivationResults(request: ClassificationRequest): Promise<ClassificationResponse> {
    const response = await fetch(`${this.classificationBase}/parse-subscription-motivation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '구독 동기 분류 결과 파싱에 실패했습니다.');
    }

    return response.json();
  }

  async parseCategoryResults(request: ClassificationRequest): Promise<ClassificationResponse> {
    const response = await fetch(`${this.classificationBase}/parse-category`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '카테고리 분류 결과 파싱에 실패했습니다.');
    }

    return response.json();
  }

  async getClassificationJobs(status?: string): Promise<ClassificationJobItem[]> {
    const params = status ? `?status=${encodeURIComponent(status)}` : '';
    const response = await fetch(`${this.queueBase}${params}`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '분류 작업 큐를 불러오지 못했습니다.');
    }
    const data = await response.json();
    return Array.isArray(data.jobs) ? data.jobs : [];
  }

  async deleteClassificationJob(jobId: string): Promise<{ success: boolean; message?: string }> {
    const response = await fetch(`${this.queueBase}/${jobId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '분류 작업 삭제에 실패했습니다.');
    }
    return response.json();
  }

  async getIndividualReelClassifications(username: string): Promise<IndividualReelClassificationResponse> {
    const response = await fetch(`/api/influencer/individual-reels/${username}`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '개별 릴스 분류 결과를 불러오지 못했습니다.');
    }
    return response.json();
  }

  async getAggregatedClassificationSummary(username: string): Promise<AggregatedSummaryResponse> {
    const response = await fetch(`/api/influencer/aggregated-summary/${username}`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '집계된 분류 요약을 불러오지 못했습니다.');
    }
    return response.json();
  }

  async updateAggregatedSummary(
    username: string,
    payload: ClassificationOverrideUpdateRequest,
  ): Promise<{ success: boolean; message?: string }> {
    const response = await fetch(`/api/influencer/aggregated-summary/${username}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '분류 결과 수정을 저장하지 못했습니다.');
    }

    return response.json();
  }

  async getUsersWithClassificationData(): Promise<UsersWithDataResponse> {
    const response = await fetch('/api/influencer/classification-data/users');
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '분류 데이터가 있는 사용자 목록을 불러오지 못했습니다.');
    }
    return response.json();
  }

  async deleteUserClassificationData(username: string, classificationType?: string): Promise<DeleteDataResponse> {
    const url = classificationType 
      ? `/api/influencer/classification-data/${username}?classification_type=${classificationType}`
      : `/api/influencer/classification-data/${username}`;
      
    const response = await fetch(url, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '분류 데이터 삭제에 실패했습니다.');
    }
    return response.json();
  }

  async deleteIndividualReelClassification(reelId: number, classificationType?: string): Promise<{ success: boolean; message: string }> {
    const params = classificationType ? `?classification_type=${classificationType}` : '';
    const response = await fetch(`/api/influencer/individual-reels/${reelId}${params}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '개별 릴 분류 결과 삭제에 실패했습니다.');
    }
    return response.json();
  }
}

export const classificationService = new ClassificationService();
