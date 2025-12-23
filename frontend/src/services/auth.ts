/**
 * 인증 서비스
 */
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';

// 인증용 별도 axios 인스턴스 (순환 참조 방지)
const authApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
}

export interface UserInfo {
  id: number;
  username: string;
  is_active: boolean;
}

/**
 * 로그인
 */
export const login = async (username: string, password: string): Promise<LoginResponse> => {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  
  const response = await authApi.post<LoginResponse>('/auth/login', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  // 토큰을 localStorage에 저장
  if (response.data.access_token) {
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('username', response.data.username);
  }
  
  return response.data;
};

/**
 * 로그아웃
 */
export const logout = (): void => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('username');
};

/**
 * 현재 사용자 정보 조회
 */
export const getCurrentUser = async (): Promise<UserInfo> => {
  const token = getToken();
  const response = await authApi.get<UserInfo>('/auth/me', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  return response.data;
};

/**
 * 토큰 가져오기
 */
export const getToken = (): string | null => {
  return localStorage.getItem('access_token');
};

/**
 * 로그인 여부 확인
 */
export const isAuthenticated = (): boolean => {
  return !!getToken();
};

// api.ts에서 인터셉터를 설정하도록 변경 (순환 참조 방지)
