import axios from 'axios';

// API 클라이언트 설정
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || '/api',
  timeout: 0, // 타임아웃 무제한
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  withCredentials: false,
});

// 요청/응답 인터셉터 설정
apiClient.interceptors.request.use(
  (config) => {
    console.log(`🌐 API 요청: ${config.method?.toUpperCase()} ${config.url}`);
    console.log(`📤 요청 데이터:`, config.data);
    return config;
  },
  (error) => {
    console.error('❌ API 요청 오류:', error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    console.log(`✅ API 응답: ${response.status} ${response.config.url}`);
    console.log(`📥 응답 데이터:`, response.data);
    return response;
  },
  (error) => {
    console.error('❌ API 응답 오류:', error.response?.status, error.response?.statusText);
    console.error('❌ 에러 상세:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// 타입 정의
export interface Profile {
  username: string;
  fullName?: string;
  followers?: number;
  following?: number;
  bio?: string;
  profilePicUrl?: string;
  account?: string;
  posts_count?: number;
  avg_engagement?: number;
  category_name?: string;
  profile_name?: string;
  email_address?: string;
  is_business_account?: boolean;
  is_professional_account?: boolean;
  is_verified?: boolean;
}

export interface Post {
  id: string;
  mediaType: 'IMAGE' | 'VIDEO' | 'CAROUSEL';
  mediaUrls: string[];
  caption?: string;
  timestamp?: string;
  user_posted?: string;
  profile_url?: string;
  date_posted?: string;
  num_comments?: number;
  likes?: number;
  photos?: string[];
  content_type?: string;
  description?: string;
  hashtags?: string[];
  reel_id?: string;
  thumbnail_url?: string;
  views?: number;
  video_play_count?: number;
}

export interface IngestResponse {
  sessionId: string;
  profile: Profile;
  posts: Post[];
}

export interface ProfileResult {
  url: string;
  success: boolean;
  username?: string;
  profile?: Profile;
  posts: Post[];
  reels: Post[];
  error?: string;
}

export interface BatchIngestResponse {
  sessionId: string;
  totalRequested: number;
  successCount: number;
  failureCount: number;
  results: ProfileResult[];
  summary: {
    total_requested: number;
    success_count: number;
    failure_count: number;
    success_rate: number;
    collected_usernames: string[];
    batch_session_id: string;
    processed_at: string;
  };
}

export interface UserData {
  username: string;
  hasProfile: boolean;
  hasPosts: boolean;
  hasReels: boolean;
  lastModified?: number;
  postsCount?: number;
  reelsCount?: number;
  followers?: number;
  fullName?: string;
}

export interface UserDetail {
  username: string;
  profile?: Profile;
  posts: Post[];
  reels: Post[];
}

export interface ClassificationResult {
  success: boolean;
  message: string;
  username: string;
  classification_type: string;
  result?: any;
}

export interface PromptSaveResponse {
  success: boolean;
  message: string;
  prompt_type: string;
  content?: string;
}

// 인플루언서 API 함수들
export const influencerApi = {
  // 데이터 수집
  async batchIngest(instagramUrls: string[], options?: { 
    collectProfile?: boolean; 
    collectPosts?: boolean; 
    collectReels?: boolean 
  }): Promise<BatchIngestResponse> {
    const response = await apiClient.post('/influencer/ingest/batch', { 
      instagramUrls,
      options: {
        collectProfile: options?.collectProfile ?? true,
        collectPosts: options?.collectPosts ?? true,
        collectReels: options?.collectReels ?? true
      }
    });
    return response.data;
  },

  async ingestProfile(instagramUrl: string): Promise<IngestResponse> {
    const response = await apiClient.post('/influencer/ingest', { 
      instagramUrls: [instagramUrl] 
    });
    return response.data;
  },

  // 파일 관리
  async getUsers(): Promise<{ users: UserData[] }> {
    const response = await apiClient.get('/influencer/files/users');
    return response.data;
  },

  async getUserData(username: string): Promise<UserDetail> {
    const response = await apiClient.get(`/influencer/files/user/${username}/data`);
    return response.data;
  },

  async deleteUsers(usernames: string[]): Promise<any> {
    const response = await apiClient.post('/influencer/files/users/delete', { usernames });
    return response.data;
  },

  async getUserProfile(username: string): Promise<Profile> {
    const response = await apiClient.get(`/influencer/files/user-profile/${username}`);
    return response.data;
  },

  async getUserReels(username: string): Promise<{ results: Post[] }> {
    const response = await apiClient.get(`/influencer/files/parsed-reels/${username}`);
    return response.data;
  },

  async getUserAnalysisData(username: string): Promise<{ username: string; profile: Profile; reels: Post[] }> {
    const response = await apiClient.get(`/influencer/files/analysis/user/${username}`);
    return response.data;
  },

  // 분류 분석
  async classifySubscriptionMotivation(username: string): Promise<ClassificationResult> {
    const response = await apiClient.post('/influencer/classification/subscription-motivation', {
      username,
      classification_type: 'subscription_motivation'
    });
    return response.data;
  },

  async classifyCategory(username: string): Promise<ClassificationResult> {
    const response = await apiClient.post('/influencer/classification/category', {
      username,
      classification_type: 'category'
    });
    return response.data;
  },

  async classifyCombined(username: string): Promise<ClassificationResult> {
    const response = await apiClient.post('/influencer/classification/combined', {
      username,
      classification_type: 'combined'
    });
    return response.data;
  },

  async getClassificationResult(username: string, classificationType: string): Promise<any> {
    const response = await apiClient.get(`/influencer/classification/${username}/${classificationType}`);
    return response.data;
  },

  async getParsedSubscriptionMotivation(username: string): Promise<any> {
    const response = await apiClient.get(`/influencer/files/parsed-subscription-motivation/${username}`);
    return response.data;
  },

  async getParsedCategory(username: string): Promise<any> {
    const response = await apiClient.get(`/influencer/files/parsed-category/${username}`);
    return response.data;
  },

  async getCombinedClassification(username: string): Promise<any> {
    const response = await apiClient.get(`/influencer/files/combined-classification/${username}`);
    return response.data;
  },

  // 프롬프트 관리
  async getPromptTypes(): Promise<string[]> {
    const response = await apiClient.get('/influencer/prompt-types');
    const types = response.data?.prompt_types;
    if (!Array.isArray(types)) {
      return [];
    }
    return types.map((type) => String(type));
  },

  async getPrompt(promptType: string): Promise<{ content: string }> {
    const response = await apiClient.get(`/influencer/prompt/${promptType}`);
    return response.data;
  },

  async savePrompt(promptType: string, content: string): Promise<PromptSaveResponse> {
    const response = await apiClient.post(`/influencer/prompt/${promptType}`, {
      prompt_type: promptType,
      content
    });
    return response.data;
  },

  async updatePrompt(promptType: string, content: string): Promise<PromptSaveResponse> {
    return this.savePrompt(promptType, content);
  },

  async getAllPrompts(): Promise<Record<string, { content: string; created_at?: string; updated_at?: string }>> {
    const response = await apiClient.get('/influencer/prompts');
    return response.data;
  }
};

export default apiClient;
