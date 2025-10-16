// API 응답 타입들
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

// API 요청/응답 타입들
export interface IngestResponse {
  sessionId: string;
  profile: Profile;
  posts: Post[];
}

export interface ErrorResponse {
  error: string;
  code?: string;
}

// 앱 상태 타입들
export type MainTabType = 'influencer-exploration';
export type SubTabType = 'ingest' | 'explore' | 'overall-analysis' | 'combined-classification' | 'prompt' | 'campaign-collection';
export type TabType = MainTabType | SubTabType;

export interface AppState {
  // 현재 탭
  activeMainTab: MainTabType;
  activeSubTab: SubTabType;
  
  // 세션 데이터
  sessionId?: string;
  profile?: Profile;
  posts: Post[];
  
  // UI 상태
  loading: {
    ingest: boolean;
    explore: boolean;
    classification: boolean;
    category: boolean;
    'overall-analysis': boolean;
  };
  
  // 액션들
  setActiveMainTab: (tab: MainTabType) => void;
  setActiveSubTab: (tab: SubTabType) => void;
  setIngestData: (sessionId: string, profile: Profile, posts: Post[]) => void;
  setLoading: (type: keyof AppState['loading'], value: boolean) => void;
  reset: () => void;
}

// 유틸리티 타입들
export interface ApiError extends Error {
  code?: string;
  status?: number;
} 