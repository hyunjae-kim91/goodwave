import axios from 'axios';

// API 클라이언트 설정
const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 300000, // 5분 타임아웃
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  withCredentials: false, // CORS 문제 해결을 위해 false로 설정
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
    if (error.response?.status === 400) {
      console.error('❌ 400 Bad Request - 요청 데이터 확인 필요');
    }
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
}

export interface Post {
  id: string;
  mediaType: 'IMAGE' | 'VIDEO' | 'CAROUSEL';
  mediaUrls: string[];
  caption?: string;
  timestamp?: string;
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
  reels: Post[];  // Reels 데이터 필드 추가
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

// API 함수들
export const ingestApi = {
  // 단일 Instagram 프로필 수집
  async ingestProfile(instagramUrl: string): Promise<IngestResponse> {
    const response = await apiClient.post('/influencer/ingest', { instagramUrls: [instagramUrl] });
    return response.data;
  },

  // 배치 Instagram 프로필 수집
  async batchIngest(instagramUrls: string[], options?: { collectProfile?: boolean; collectPosts?: boolean; collectReels?: boolean }): Promise<BatchIngestResponse> {
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
};

// 파싱 관련 타입 정의
export interface ParsingStatus {
  username: string;
  status: 'not_parsed' | 'parsed' | 'error';
  last_modified?: number;
  parsed_at?: string;
  profile_count: number;
  posts_count: number;
  reels_count: number;
  message: string;
  error?: string;
}

export interface AllUsersParsingStatus {
  users: ParsingStatus[];
  total_users: number;
  parsed_users: number;
  not_parsed_users: number;
  error_users: number;
}

export interface ParsingResponse {
  message: string;
  username?: string;
  total_users?: number;
  usernames?: string[];
  status: 'processing' | 'no_users';
}

// 파싱 API 함수들
export const parsingApi = {
  // 단일 사용자 데이터 파싱
  async parseUserData(username: string): Promise<ParsingResponse> {
    const response = await apiClient.post(`/parsing/parse-user/${username}`);
    return response.data;
  },

  // 사용자 파싱 상태 확인
  async getParsingStatus(username: string): Promise<ParsingStatus> {
    const response = await apiClient.get(`/parsing/parse-user/${username}/status`);
    return response.data;
  },

  // 파싱된 사용자 데이터 조회
  async getParsedData(username: string): Promise<any> {
    const response = await apiClient.get(`/parsing/parse-user/${username}/data`);
    return response.data;
  },

  // 모든 사용자 데이터 파싱
  async parseAllUsers(): Promise<ParsingResponse> {
    const response = await apiClient.post('/parsing/parse-all-users');
    return response.data;
  },

  // 모든 사용자 파싱 상태 확인
  async getAllUsersParsingStatus(): Promise<AllUsersParsingStatus> {
    const response = await apiClient.get('/parsing/users/status');
    return response.data;
  }
};

export default apiClient;
 