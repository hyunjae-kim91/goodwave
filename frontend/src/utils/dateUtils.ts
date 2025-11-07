/**
 * 날짜/시간 유틸리티 함수
 * 모든 시간을 한국 시간(KST, UTC+9)으로 표시
 */

/**
 * UTC 시간을 한국 시간으로 변환하여 표시
 * @param dateString - ISO 8601 형식의 날짜 문자열
 * @returns 한국 시간 기준 날짜/시간 문자열
 */
export const formatDateTimeKST = (dateString?: string | null): string => {
  if (!dateString) return '-';
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '-';
    
    // UTC 시간에 9시간 추가 (KST = UTC+9)
    const kstDate = new Date(date.getTime() + (9 * 60 * 60 * 1000));
    
    const year = kstDate.getUTCFullYear();
    const month = String(kstDate.getUTCMonth() + 1).padStart(2, '0');
    const day = String(kstDate.getUTCDate()).padStart(2, '0');
    const hours = String(kstDate.getUTCHours()).padStart(2, '0');
    const minutes = String(kstDate.getUTCMinutes()).padStart(2, '0');
    const seconds = String(kstDate.getUTCSeconds()).padStart(2, '0');
    
    return `${year}.${month}.${day} ${hours}:${minutes}:${seconds}`;
  } catch (e) {
    return '-';
  }
};

/**
 * UTC 날짜를 한국 시간 기준 날짜만 표시
 * @param dateString - ISO 8601 형식의 날짜 문자열
 * @returns 한국 시간 기준 날짜 문자열 (시간 제외)
 */
export const formatDateKST = (dateString?: string | null): string => {
  if (!dateString) return '-';
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '-';
    
    // UTC 시간에 9시간 추가 (KST = UTC+9)
    const kstDate = new Date(date.getTime() + (9 * 60 * 60 * 1000));
    
    const year = kstDate.getUTCFullYear();
    const month = String(kstDate.getUTCMonth() + 1).padStart(2, '0');
    const day = String(kstDate.getUTCDate()).padStart(2, '0');
    
    return `${year}.${month}.${day}`;
  } catch (e) {
    return '-';
  }
};

/**
 * UTC 시간을 한국 시간 기준 시:분:초만 표시
 * @param dateString - ISO 8601 형식의 날짜 문자열
 * @returns 한국 시간 기준 시간 문자열 (날짜 제외)
 */
export const formatTimeKST = (dateString?: string | null): string => {
  if (!dateString) return '-';
  
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '-';
    
    // UTC 시간에 9시간 추가 (KST = UTC+9)
    const kstDate = new Date(date.getTime() + (9 * 60 * 60 * 1000));
    
    const hours = String(kstDate.getUTCHours()).padStart(2, '0');
    const minutes = String(kstDate.getUTCMinutes()).padStart(2, '0');
    const seconds = String(kstDate.getUTCSeconds()).padStart(2, '0');
    
    return `${hours}:${minutes}:${seconds}`;
  } catch (e) {
    return '-';
  }
};

/**
 * 현재 한국 시간 반환
 * @returns 현재 한국 시간 Date 객체
 */
export const getNowKST = (): Date => {
  const now = new Date();
  // 한국 시간으로 변환된 시간을 반환
  const kstString = now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' });
  return new Date(kstString);
};

/**
 * 한국 시간 기준 오늘 날짜 (YYYY-MM-DD)
 * @returns 오늘 날짜 문자열
 */
export const getTodayKST = (): string => {
  const now = getNowKST();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

