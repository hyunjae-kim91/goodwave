/**
 * IP 접근 권한 체크 유틸리티
 */
import api from '../services/api';

export interface IPAccessCheckResult {
  allowed: boolean;
  ip: string;
  message: string;
}

/**
 * 현재 클라이언트 IP가 허용 목록에 있는지 확인
 */
export const checkIPAccess = async (): Promise<IPAccessCheckResult> => {
  try {
    const response = await api.get<IPAccessCheckResult>('/check-ip-access');
    return response.data;
  } catch (error: any) {
    console.error('IP access check failed:', error);
    // 에러 발생 시 기본적으로 허용하지 않음
    return {
      allowed: false,
      ip: 'unknown',
      message: error.response?.data?.detail || 'IP access check failed'
    };
  }
};

/**
 * 공유된 보고서 경로인지 확인
 */
export const isSharedReportPath = (pathname: string): boolean => {
  return pathname.startsWith('/shared/reports/') || 
         pathname.startsWith('/reports/');
};

/**
 * Admin 경로인지 확인
 */
export const isAdminPath = (pathname: string): boolean => {
  return pathname.startsWith('/admin');
};
