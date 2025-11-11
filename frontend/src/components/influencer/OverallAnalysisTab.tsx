import React, { useState, useEffect, useMemo } from 'react';
import styled from 'styled-components';
import {
  BarChart3,
  Users,
  Download,
  CheckCircle,
  Search,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  AggregatedSummary,
  AggregatedSummaryResponse,
  ClassificationOverridePayload,
  ClassificationOverrideUpdateRequest,
  classificationService,
} from '../../services/influencer/classificationService';

interface UserData {
  username: string;
  hasProfile: boolean;
  hasPosts: boolean;
  hasReels?: boolean;
  lastModified?: number;
}

interface AnalysisData {
  username: string;
  fullName?: string;
  followers?: number;
  grade?: string;
  category?: string;
  avgEngagementRate?: number;
  avgVideoPlayCount?: number;
  avgLikes?: number;
  avgComments?: number;
  subscriptionMotivationStats?: Array<{motivation: string, percentage: number}>;
  categoryStats?: Array<{category: string, percentage: number}>;
  reelsStats?: Array<{reelId: string, videoPlayCount: number}>;
  postsCount?: number;
  memo?: string;
}

interface TopStatEntry {
  label: string;
  percentage: number;
  count?: number;
}

interface OverrideFieldState {
  primaryLabel: string;
  primaryPercentage: string;
  secondaryLabel: string;
  secondaryPercentage: string;
}

interface OverrideFormState {
  subscriptionMotivation: OverrideFieldState;
  category: OverrideFieldState;
}

const Container = styled.div`
  width: 100%;
  max-width: 100%;
  padding: 0 0.5rem;
`;

const Title = styled.h1`
  color: #2c3e50;
  margin-bottom: 2rem;
  font-size: 1.5rem;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const Section = styled.div`
  background: white;
  padding: 1rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 1.5rem;
  width: 100%;
  box-sizing: border-box;
`;

const SectionTitle = styled.h2`
  color: #2c3e50;
  margin-bottom: 1rem;
  font-size: 1.125rem;
  font-weight: 600;
`;

const Button = styled.button`
  padding: 0.75rem 1.5rem;
  background-color: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  margin-right: 0.5rem;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;

  &:hover {
    background-color: #2980b9;
  }

  &:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
  }
`;


const SuccessButton = styled(Button)`
  background-color: #27ae60;
  
  &:hover {
    background-color: #229954;
  }
`;

const SmallButton = styled(Button)`
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  background-color: #f8f9fa;
  color: #495057;
  border: 1px solid #dee2e6;
  
  &:hover {
    background-color: #e9ecef;
    color: #495057;
  }
`;

const Input = styled.input`
  padding: 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1rem;
  width: 100%;

  &:focus {
    outline: none;
    border-color: #3498db;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.25);
  }
`;

const Select = styled.select`
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.875rem;
  background-color: white;
  cursor: pointer;
`;

const RangeSliderContainer = styled.div`
  position: relative;
  width: 100%;
  height: 50px;
  display: flex;
  align-items: center;
`;

const RangeSliderWrapper = styled.div`
  position: relative;
  width: 100%;
  height: 6px;
`;

const RangeSliderTrack = styled.div`
  position: absolute;
  width: 100%;
  height: 6px;
  background: #ddd;
  border-radius: 3px;
  top: 50%;
  transform: translateY(-50%);
`;

const RangeSliderActiveTrack = styled.div<{ left: number; width: number }>`
  position: absolute;
  height: 6px;
  background: #3498db;
  border-radius: 3px;
  left: ${props => props.left}%;
  width: ${props => props.width}%;
  top: 50%;
  transform: translateY(-50%);
`;

const RangeSlider = styled.input<{ isMin?: boolean }>`
  position: absolute;
  width: 100%;
  height: 20px;
  background: transparent;
  outline: none;
  -webkit-appearance: none;
  pointer-events: auto;
  z-index: ${props => props.isMin ? 3 : 2};
  margin: 0;
  padding: 0;
  cursor: pointer;
  
  &::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #3498db;
    cursor: pointer;
    position: relative;
    z-index: 5;
    border: 2px solid white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  }
  
  &::-moz-range-thumb {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #3498db;
    cursor: pointer;
    border: 2px solid white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    position: relative;
    z-index: 5;
  }
  
  &::-webkit-slider-runnable-track {
    height: 6px;
    background: transparent;
  }
  
  &::-moz-range-track {
    height: 6px;
    background: transparent;
  }
`;

const RangeValue = styled.div`
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #6c757d;
`;

const SearchInput = styled(Input)`
  padding-left: 2.5rem;
`;

const SearchContainer = styled.div`
  position: relative;
  flex: 1;
`;

const SearchIcon = styled(Search)`
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  width: 1rem;
  height: 1rem;
  color: #6c757d;
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  align-items: start;
`;

const UserListContainer = styled.div`
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #dee2e6;
  border-radius: 4px;
`;

const UserItem = styled.label`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  cursor: pointer;
  border-bottom: 1px solid #f8f9fa;
  
  &:hover {
    background-color: #f8f9fa;
  }
  
  &:last-child {
    border-bottom: none;
  }
`;

const UserText = styled.span`
  font-size: 0.875rem;
  color: #495057;
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
  flex-wrap: wrap;
`;

const HeaderActions = styled.div`
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 1.5rem;
`;

const InfoBox = styled.div`
  background: #e8f4fd;
  border: 1px solid #bee5eb;
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
`;

const InfoText = styled.div`
  color: #0c5460;
`;

const InfoTitle = styled.p`
  font-size: 0.875rem;
  font-weight: 600;
  margin: 0 0 0.25rem 0;
`;

const InfoSubtext = styled.p`
  font-size: 0.75rem;
  margin: 0;
  opacity: 0.8;
`;

const TableContainer = styled.div`
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #dee2e6;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const TableHeader = styled.th`
  padding: 0.75rem;
  background-color: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
  text-align: left;
  font-weight: 600;
  color: #495057;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
  min-width: 80px;
`;

const TableCell = styled.td`
  padding: 0.75rem;
  border-bottom: 1px solid #f8f9fa;
  font-size: 0.875rem;
  color: #495057;
`;

const TableRow = styled.tr<{ isEven?: boolean }>`
  background-color: ${props => props.isEven ? '#ffffff' : '#f8f9fa'};
`;

const UsernameBadge = styled.div`
  font-weight: 600;
  color: #2c3e50;
`;

const PaginationContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1.5rem;
  padding: 1rem;
`;

const PaginationButton = styled.button`
  padding: 0.5rem 1rem;
  background-color: ${props => props.disabled ? '#e9ecef' : '#3498db'};
  color: ${props => props.disabled ? '#6c757d' : 'white'};
  border: none;
  border-radius: 4px;
  cursor: ${props => props.disabled ? 'not-allowed' : 'pointer'};
  font-size: 0.875rem;
  font-weight: 600;
  
  &:hover:not(:disabled) {
    background-color: #2980b9;
  }
`;

const PaginationInfo = styled.span`
  font-size: 0.875rem;
  color: #495057;
  margin: 0 0.5rem;
`;

const StatItem = styled.div`
  font-size: 0.75rem;
  margin-bottom: 0.25rem;
  
  &:last-child {
    margin-bottom: 0;
  }
`;

const OverrideFormContainer = styled.div`
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 1rem;
  display: grid;
  gap: 1rem;
`;

const OverrideSection = styled.div`
  display: grid;
  gap: 0.5rem;
`;

const OverrideSectionTitle = styled.h4`
  margin: 0;
  font-size: 0.875rem;
  color: #2c3e50;
  font-weight: 600;
`;

const OverrideFieldGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.5rem;
`;

const OverrideActions = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  flex-wrap: wrap;
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 4rem 2rem;
  background: linear-gradient(135deg, #e8f4fd 0%, #d1ecf1 100%);
  border-radius: 8px;
  border: 2px dashed #bee5eb;
`;

const EmptyStateIcon = styled(BarChart3)`
  width: 4rem;
  height: 4rem;
  color: #6c757d;
  margin: 0 auto 1rem;
`;

const EmptyStateTitle = styled.h3`
  font-size: 1.25rem;
  font-weight: 600;
  color: #495057;
  margin: 0 0 0.5rem 0;
`;

const EmptyStateText = styled.p`
  color: #6c757d;
  margin: 0 0 1rem 0;
  line-height: 1.5;
`;

const EmptyStateHint = styled.div`
  font-size: 0.875rem;
  color: #6c757d;
`;

const SuccessBox = styled.div`
  background: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
  padding: 1rem;
  margin-top: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
`;

const SuccessText = styled.p`
  color: #155724;
  font-size: 0.875rem;
  margin: 0;
`;

const LoadingSpinner = styled.div`
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const isRecordValue = (value: unknown): value is Record<string, unknown> => {
  return !!value && typeof value === 'object' && !Array.isArray(value);
};

const normalizePercentageValue = (value: unknown): number | undefined => {
  if (value === null || value === undefined) {
    return undefined;
  }
  const numeric = typeof value === 'string' ? Number.parseFloat(value) : Number(value);
  if (Number.isNaN(numeric)) {
    return undefined;
  }
  return numeric;
};

const normalizeToPercent = (value?: number): number | undefined => {
  if (value === undefined) return undefined;
  if (value <= 1) {
    return value * 100;
  }
  return value;
};

const extractTopEntriesFromDistribution = (
  distribution: AggregatedSummary['classification_distribution'] | unknown,
): TopStatEntry[] => {
  if (!distribution) {
    return [];
  }

  let entries: TopStatEntry[] = [];

  if (Array.isArray(distribution)) {
    const totalCount = distribution.reduce(
      (acc, item) => acc + (typeof item.count === 'number' ? item.count : 0),
      0,
    );

    entries = distribution
      .map((item) => ({
        label: typeof item.label === 'string' ? item.label : '',
        percentage:
          totalCount > 0 && typeof item.count === 'number'
            ? (item.count / totalCount) * 100
            : normalizePercentageValue(item.percentage) ?? 0,
        count: typeof item.count === 'number' ? item.count : undefined,
      }))
      .filter((item) => item.label);
  } else if (isRecordValue(distribution)) {
    const mapped = Object.entries(distribution).map(([label, value]) => ({
      label,
      raw: value,
    }));

    const total = mapped.reduce(
      (sum, item) => sum + (typeof item.raw === 'number' ? item.raw : 0),
      0,
    );

    if (total > 0) {
      entries = mapped.map((item) => ({
        label: item.label,
        percentage:
          typeof item.raw === 'number' ? (item.raw / total) * 100 : 0,
        count: typeof item.raw === 'number' ? Math.round(item.raw) : undefined,
      }));
    } else {
      entries = mapped.map((item) => ({
        label: item.label,
        percentage: normalizePercentageValue(item.raw) ?? 0,
      }));
    }
  }

  entries.sort((a, b) => (b.count ?? b.percentage) - (a.count ?? a.percentage));
  return entries.slice(0, 2);
};

const buildTopEntriesFromAggregated = (aggregated?: AggregatedSummary | null): TopStatEntry[] => {
  if (!aggregated) {
    return [];
  }

  const fromDistribution = extractTopEntriesFromDistribution(
    aggregated.classification_distribution,
  );
  if (fromDistribution.length) {
    return fromDistribution;
  }

  const totalCount =
    aggregated.statistics?.successful_classifications ||
    aggregated.statistics?.total_reels_processed;

  const results: TopStatEntry[] = [];

  if (aggregated.primary_classification) {
    const percentValue = normalizeToPercent(
      normalizePercentageValue(aggregated.primary_percentage),
    ) ?? 0;
    results.push({
      label: aggregated.primary_classification,
      percentage: percentValue,
      count:
        totalCount && percentValue
          ? Math.round((percentValue / 100) * totalCount)
          : undefined,
    });
  }

  if (aggregated.secondary_classification) {
    const percentValue = normalizeToPercent(
      normalizePercentageValue(aggregated.secondary_percentage),
    );
    if (percentValue !== undefined) {
      results.push({
        label: aggregated.secondary_classification,
        percentage: percentValue,
        count:
          totalCount && percentValue !== undefined
            ? Math.round((percentValue / 100) * totalCount)
            : undefined,
      });
    }
  }

  return results.slice(0, 2);
};

const mapTopEntriesToMotivationStats = (
  entries: TopStatEntry[],
): Array<{ motivation: string; percentage: number }> =>
  entries.map((entry) => ({
    motivation: entry.label,
    percentage: Math.round(entry.percentage),
  }));

const mapTopEntriesToCategoryStats = (
  entries: TopStatEntry[],
): Array<{ category: string; percentage: number }> =>
  entries.map((entry) => ({
    category: entry.label,
    percentage: Math.round(entry.percentage),
  }));

const formatMotivationStatsLine = (
  stats?: Array<{ motivation: string; percentage: number }>,
) =>
  stats && stats.length
    ? stats
        .map((stat) => `${stat.motivation} ${Math.round(stat.percentage)}%`)
        .join(', ')
    : '';

const formatCategoryStatsLine = (
  stats?: Array<{ category: string; percentage: number }>,
) =>
  stats && stats.length
    ? stats
        .map((stat) => `${stat.category} ${Math.round(stat.percentage)}%`)
        .join(', ')
    : '';

// 등급 계산 함수 (평균 조회수 기반)
const calculateGrade = (avgViews: number | undefined): string => {
  if (!avgViews || avgViews < 1000) return 'N/A';
  if (avgViews >= 100001) return '프리미엄';
  if (avgViews >= 30001) return '골드';
  if (avgViews >= 5001) return '블루';
  if (avgViews >= 1000) return '레드';
  return 'N/A';
};

const OverallAnalysisTab: React.FC = () => {
  const [users, setUsers] = useState<UserData[]>([]);
  const [analysisData, setAnalysisData] = useState<AnalysisData[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [editingUsername, setEditingUsername] = useState<string | null>(null);
  const [overrideForm, setOverrideForm] = useState<OverrideFormState | null>(null);
  const [isSavingOverride, setIsSavingOverride] = useState(false);
  // 메모 편집 상태
  const [editingMemo, setEditingMemo] = useState<{username: string, memo: string} | null>(null);
  // 전체 분석 결과 수정 상태
  const [editingAnalysisRow, setEditingAnalysisRow] = useState<string | null>(null);
  const [analysisEditForm, setAnalysisEditForm] = useState<{
    motivation1: string;
    motivation2: string;
    category1: string;
    category2: string;
    memo: string;
  } | null>(null);
  const [isSavingAnalysisEdit, setIsSavingAnalysisEdit] = useState(false);
  // 필터 상태
  const [filterExpanded, setFilterExpanded] = useState(false);
  // 페이지네이션 상태
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  // 선택된 계정 상태
  const [selectedUsernames, setSelectedUsernames] = useState<Set<string>>(new Set());
  
  const [filters, setFilters] = useState<{
    username: string;
    followersMin: number;
    followersMax: number;
    avgLikesMin: number;
    avgLikesMax: number;
    avgCommentsMin: number;
    avgCommentsMax: number;
    grade: string;
    motivation1: string;
    motivation2: string;
    category1: string;
    category2: string;
    memo: string;
    accountType: string;
  }>({
    username: '',
    followersMin: 0,
    followersMax: 10000, // 초기값은 작게 설정, 데이터 로드 후 실제 최대값으로 업데이트됨
    avgLikesMin: 0,
    avgLikesMax: 1000, // 초기값은 작게 설정, 데이터 로드 후 실제 최대값으로 업데이트됨
    avgCommentsMin: 0,
    avgCommentsMax: 100, // 초기값은 작게 설정, 데이터 로드 후 실제 최대값으로 업데이트됨
    grade: '',
    motivation1: '',
    motivation2: '',
    category1: '',
    category2: '',
    memo: '',
    accountType: ''
  });

  // 필터 변경 시 첫 페이지로 리셋 및 선택 초기화
  useEffect(() => {
    setCurrentPage(1);
    // 필터가 변경되면 선택된 항목 중 필터링된 항목에 포함되지 않는 항목 제거
    const filteredUsernames = new Set(
      (analysisData || []).filter((data) => {
        if (filters.username && data.username !== filters.username) return false;
        if (data.followers !== undefined) {
          const min = filters.followersMin || 0;
          const max = filters.followersMax || getMaxValue('followers');
          if (data.followers < min || data.followers > max) return false;
        }
        if (data.avgLikes !== undefined) {
          const min = filters.avgLikesMin || 0;
          const max = filters.avgLikesMax || getMaxValue('avgLikes');
          if (data.avgLikes < min || data.avgLikes > max) return false;
        }
        if (data.avgComments !== undefined) {
          const min = filters.avgCommentsMin || 0;
          const max = filters.avgCommentsMax || getMaxValue('avgComments');
          if (data.avgComments < min || data.avgComments > max) return false;
        }
        if (filters.grade && data.grade !== filters.grade) return false;
        const motivation1 = data.subscriptionMotivationStats?.[0];
        if (filters.motivation1 && (!motivation1 || motivation1.motivation !== filters.motivation1)) return false;
        const motivation2 = data.subscriptionMotivationStats?.[1];
        if (filters.motivation2 && (!motivation2 || motivation2.motivation !== filters.motivation2)) return false;
        const category1 = data.categoryStats?.[0];
        if (filters.category1 && (!category1 || category1.category !== filters.category1)) return false;
        const category2 = data.categoryStats?.[1];
        if (filters.category2 && (!category2 || category2.category !== filters.category2)) return false;
        if (filters.memo && (!data.memo || !data.memo.toLowerCase().includes(filters.memo.toLowerCase()))) return false;
        if (filters.accountType && (!data.category || data.category !== filters.accountType)) return false;
        return true;
      }).map(data => data.username)
    );
    
    // 선택된 항목 중 필터링된 항목에 포함되지 않는 항목 제거
    const newSelected = new Set<string>();
    selectedUsernames.forEach(username => {
      if (filteredUsernames.has(username)) {
        newSelected.add(username);
      }
    });
    setSelectedUsernames(newSelected);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.username, filters.grade, filters.motivation1, filters.motivation2, filters.category1, filters.category2, filters.accountType, filters.memo, filters.followersMin, filters.followersMax, filters.avgLikesMin, filters.avgLikesMax, filters.avgCommentsMin, filters.avgCommentsMax]);

  // 필터 옵션 정의
  const gradeOptions = ['', '레드', '블루', '골드', '프리미엄'];
  const motivationOptions = ['', '실용정보', '리뷰', '스토리', '자기계발', '웰니스', '프리미엄', '감성', '유머', '비주얼'];
  const categoryOptions = ['', '리빙', '맛집', '뷰티', '여행', '운동/레저', '육아/가족', '일상', '패션', '푸드'];
  
  // 실제 데이터에서 distinct한 계정 유형 추출
  const accountTypeOptions = useMemo(() => {
    const distinctTypes = new Set<string>();
    analysisData.forEach(data => {
      if (data.category && data.category.trim() !== '') {
        distinctTypes.add(data.category);
      }
    });
    const sortedTypes = Array.from(distinctTypes).sort();
    return ['', ...sortedTypes];
  }, [analysisData]);
  
  // 범위 슬라이더의 최대값 계산
  const getMaxValue = (field: 'followers' | 'avgLikes' | 'avgComments'): number => {
    if (analysisData.length === 0) {
      // 데이터가 없을 때는 작은 기본값 반환
      if (field === 'followers') return 10000;
      if (field === 'avgLikes') return 1000;
      if (field === 'avgComments') return 100;
      return 1000;
    }
    const values = analysisData.map(data => {
      if (field === 'followers') return data.followers || 0;
      if (field === 'avgLikes') return data.avgLikes || 0;
      if (field === 'avgComments') return data.avgComments || 0;
      return 0;
    });
    const maxValue = Math.max(...values);
    // 최소값 보장 (0보다 큰 값이 없으면 작은 기본값 반환)
    return maxValue > 0 ? maxValue : (field === 'followers' ? 10000 : field === 'avgLikes' ? 1000 : 100);
  };

  // 사용자 목록 로드
  const loadUsers = async () => {
    try {
      const response = await fetch('/api/influencer/files/users');
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users || []);
      } else {
        toast.error('사용자 목록을 불러오는데 실패했습니다');
      }
    } catch (error) {
      console.error('사용자 목록 로드 실패:', error);
      toast.error('사용자 목록을 불러오는데 실패했습니다');
    }
  };

  // 전체 분석 실행
  const runOverallAnalysis = async () => {
    if (users.length === 0) {
      toast.error('분석할 사용자가 없습니다');
      return;
    }

    try {
      setIsAnalyzing(true);
      toast.loading('전체 분석을 시작합니다...');

      const analysisResults: AnalysisData[] = [];

      for (const user of users) {
        try {
          // 사용자별 분석 데이터 수집
          const userAnalysis = await analyzeUser(user.username);
          analysisResults.push(userAnalysis);
        } catch (error) {
          console.error(`${user.username} 분석 실패:`, error);
          // 에러가 발생해도 기본 데이터는 추가
          analysisResults.push({
            username: user.username,
            followers: 0,
            category: '분석 실패',
            avgEngagementRate: 0,
            avgVideoPlayCount: 0,
            subscriptionMotivationStats: [],
            categoryStats: []
          });
        }
      }

      setAnalysisData(analysisResults);
      
      // 필터 최대값 업데이트 (실제 데이터의 최대값만 사용)
      const maxFollowers = analysisResults.length > 0 
        ? Math.max(...analysisResults.map(r => r.followers || 0), 0)
        : 10000;
      const maxLikes = analysisResults.length > 0
        ? Math.max(...analysisResults.map(r => r.avgLikes || 0), 0)
        : 1000;
      const maxComments = analysisResults.length > 0
        ? Math.max(...analysisResults.map(r => r.avgComments || 0), 0)
        : 100;
      
      // 실제 최대값이 0보다 크면 사용, 아니면 작은 기본값 사용
      setFilters(prev => ({
        ...prev,
        followersMax: maxFollowers > 0 ? maxFollowers : 10000,
        avgLikesMax: maxLikes > 0 ? maxLikes : 1000,
        avgCommentsMax: maxComments > 0 ? maxComments : 100,
      }));
      
      toast.success('전체 분석이 완료되었습니다');
      
    } catch (error) {
      console.error('전체 분석 오류:', error);
      toast.error('전체 분석 중 오류가 발생했습니다');
    } finally {
      setIsAnalyzing(false);
      toast.dismiss();
    }
  };

  // 개별 사용자 분석
  const analyzeUser = async (username: string): Promise<AnalysisData> => {
    const userAnalysis: AnalysisData = {
      username
    };

    userAnalysis.subscriptionMotivationStats = [];
    userAnalysis.categoryStats = [];

    try {
      // 1. 프로필 데이터 로드 (followers, category_name, avg_engagement 포함)
      try {
        const profileResponse = await fetch(`/api/influencer/files/user-profile/${username}`);
        if (profileResponse.ok) {
          const profileData = await profileResponse.json();
          
          console.log(`${username} 프로필 데이터:`, profileData);
          
          // followers, category_name, avg_engagement, fullName, memo를 profile.json에서 가져오기
          userAnalysis.followers = profileData.followers || 0;
          userAnalysis.category = profileData.category_name || '';
          userAnalysis.postsCount = profileData.posts_count || 0;
          userAnalysis.fullName = profileData.fullName || '';
          userAnalysis.memo = profileData.memo || '';
          
          // 평균 참여율 계산 (소수점을 퍼센트로 변환)
          if (profileData.avg_engagement !== undefined) {
            // avg_engagement는 소수점 형태 (예: 0.0462)이므로 100을 곱해서 퍼센트로 변환
            userAnalysis.avgEngagementRate = Math.round(profileData.avg_engagement * 100 * 100) / 100;
          }
          
          console.log(`${username} 분석 결과:`, {
            followers: userAnalysis.followers,
            category: userAnalysis.category,
            avgEngagementRate: userAnalysis.avgEngagementRate
          });
        }
      } catch (error) {
        console.log(`${username} 프로필 데이터 로드 실패:`, error);
      }

      // 2. 릴스 데이터 로드 (reels.json에서 video_play_count 가져오기)
      try {
        const reelsResponse = await fetch(`/api/influencer/files/parsed-reels/${username}`);
        if (reelsResponse.ok) {
          const reelsData = await reelsResponse.json();
          
          console.log(`${username} 릴스 데이터 응답:`, reelsData);
          
          userAnalysis.reelsStats = calculateReelsStats(reelsData.results || []);
          
          // 평균 비디오 재생수 계산 (reels.json에서 video_play_count 값만 추출)
          if (reelsData.results && Array.isArray(reelsData.results)) {
            const videoPlayCounts: number[] = [];
            
            // reels.json에서 video_play_count 값만 추출
            reelsData.results.forEach((reel: any) => {
              if (reel.video_play_count !== undefined && reel.video_play_count !== null && reel.video_play_count > 0) {
                videoPlayCounts.push(reel.video_play_count);
              }
            });

            console.log(`${username} 릴스 비디오 재생수:`, videoPlayCounts);

            // 릴스 비디오 재생수 평균 계산 (최고/최저 2개 제거)
            if (videoPlayCounts.length > 4) {
              const sortedCounts = videoPlayCounts.sort((a, b) => a - b);
              const filteredCounts = sortedCounts.slice(2, -2); // 최고/최저 2개 제거
              const sum = filteredCounts.reduce((acc, count) => acc + count, 0);
              userAnalysis.avgVideoPlayCount = Math.round(sum / filteredCounts.length);
              
              console.log(`${username} 정렬된 재생수:`, sortedCounts);
              console.log(`${username} 필터링된 재생수 (최고/최저 2개 제거):`, filteredCounts);
              console.log(`${username} 평균 비디오 재생수:`, userAnalysis.avgVideoPlayCount);
            } else if (videoPlayCounts.length > 0) {
              const sum = videoPlayCounts.reduce((acc, count) => acc + count, 0);
              userAnalysis.avgVideoPlayCount = Math.round(sum / videoPlayCounts.length);
              
              console.log(`${username} 전체 평균 비디오 재생수:`, userAnalysis.avgVideoPlayCount);
            }
            
            // 릴스 24개의 평균 좋아요 수, 평균 댓글 수 계산 (최고/최저 2개 제거)
            const reels = reelsData.results || [];
            const top24Reels = reels.slice(0, 24); // 최신 24개 릴스
            
            const likesCounts: number[] = [];
            const commentsCounts: number[] = [];
            
            top24Reels.forEach((reel: any) => {
              // 좋아요 수: likes, likes_count, like_count 등 여러 필드명 지원
              const likes = reel.likes ?? reel.likes_count ?? reel.like_count;
              if (likes !== undefined && likes !== null && likes > 0) {
                likesCounts.push(Number(likes));
              }
              // 댓글 수: num_comments, comments_count, comment_count 등 여러 필드명 지원
              const comments = reel.num_comments ?? reel.comments_count ?? reel.comment_count;
              if (comments !== undefined && comments !== null && comments > 0) {
                commentsCounts.push(Number(comments));
              }
            });
            
            // 좋아요 수 평균 계산 (최고/최저 2개 제거)
            if (likesCounts.length > 4) {
              const sortedLikes = likesCounts.sort((a, b) => a - b);
              const filteredLikes = sortedLikes.slice(2, -2); // 최고/최저 2개 제거
              const likesSum = filteredLikes.reduce((acc, count) => acc + count, 0);
              userAnalysis.avgLikes = Math.round(likesSum / filteredLikes.length);
            } else if (likesCounts.length > 0) {
              const likesSum = likesCounts.reduce((acc, count) => acc + count, 0);
              userAnalysis.avgLikes = Math.round(likesSum / likesCounts.length);
            }
            
            // 댓글 수 평균 계산 (최고/최저 2개 제거)
            if (commentsCounts.length > 4) {
              const sortedComments = commentsCounts.sort((a, b) => a - b);
              const filteredComments = sortedComments.slice(2, -2); // 최고/최저 2개 제거
              const commentsSum = filteredComments.reduce((acc, count) => acc + count, 0);
              userAnalysis.avgComments = Math.round(commentsSum / filteredComments.length);
            } else if (commentsCounts.length > 0) {
              const commentsSum = commentsCounts.reduce((acc, count) => acc + count, 0);
              userAnalysis.avgComments = Math.round(commentsSum / commentsCounts.length);
            }
            
            // 등급 계산 (평균 조회수 기반)
            if (userAnalysis.avgVideoPlayCount) {
              userAnalysis.grade = calculateGrade(userAnalysis.avgVideoPlayCount);
            }
          }
        }
      } catch (error) {
        console.log(`${username} 릴스 데이터 로드 실패:`, error);
      }

      // 3. 집계된 분류 요약 데이터 로드
      try {
        const aggregatedResponse = await fetch(`/api/influencer/aggregated-summary/${username}`);
        if (aggregatedResponse.ok) {
          const aggregatedData: AggregatedSummaryResponse = await aggregatedResponse.json();
          const aggregatedSummaries = aggregatedData?.aggregated_summaries ?? {};

          const motivationEntries = buildTopEntriesFromAggregated(
            aggregatedSummaries.subscription_motivation,
          );
          if (motivationEntries.length) {
            userAnalysis.subscriptionMotivationStats = mapTopEntriesToMotivationStats(
              motivationEntries,
            );
          }

          const categoryEntries = buildTopEntriesFromAggregated(
            aggregatedSummaries.category,
          );
          if (categoryEntries.length) {
            userAnalysis.categoryStats = mapTopEntriesToCategoryStats(categoryEntries);
          }
        } else {
          console.log(`${username} 집계된 분류 요약 없음 (${aggregatedResponse.status})`);
        }
      } catch (error) {
        console.log(`${username} 집계된 분류 요약 로드 실패:`, error);
      }

      // 4. 통합 classification.json에서 동기/카테고리 분류 통계 로드 (집계 데이터 미존재 시 fallback)
      try {
        const clsResponse = await fetch(`/api/influencer/files/combined-classification/${username}`);
        if (clsResponse.ok) {
          const clsData = await clsResponse.json();
          const results = Array.isArray(clsData?.results) ? clsData.results : [];
          if (!userAnalysis.subscriptionMotivationStats?.length) {
            userAnalysis.subscriptionMotivationStats = calculateSubscriptionMotivationStats(results);
          }
          if (!userAnalysis.categoryStats?.length) {
            userAnalysis.categoryStats = calculateCategoryStats(results);
          }
        } else {
          console.log(`${username} 통합 분류 결과 없음 (${clsResponse.status})`);
        }
      } catch (error) {
        console.log(`${username} 통합 분류 결과 로드 실패:`, error);
      }

    } catch (error) {
      console.error(`${username} 분석 중 오류:`, error);
    }

    return userAnalysis;
  };

  // 구독 동기 통계 계산 (최대 2개) - classification.json 기반
  const calculateSubscriptionMotivationStats = (results: any[]): Array<{motivation: string, percentage: number}> => {
    const motivationCounts: { [key: string]: number } = {};
    const total = results.length;
    
    if (total === 0) return [];

    results.forEach(result => {
      const motivation = result.motivation || '알 수 없음';
      motivationCounts[motivation] = (motivationCounts[motivation] || 0) + 1;
    });
    
    const stats = Object.entries(motivationCounts)
      .map(([motivation, count]) => ({
        motivation,
        percentage: Math.round((count / total) * 100)
      }))
      .sort((a, b) => b.percentage - a.percentage)
      .slice(0, 2); // 최대 2개만 반환
    
    return stats;
  };

  // 카테고리 통계 계산 (최대 2개) - classification.json 기반
  const calculateCategoryStats = (results: any[]): Array<{category: string, percentage: number}> => {
    const categoryCounts: { [key: string]: number } = {};
    const total = results.length;
    
    if (total === 0) return [];

    results.forEach(result => {
      const category = result.category || '알 수 없음';
      categoryCounts[category] = (categoryCounts[category] || 0) + 1;
    });
    
    const stats = Object.entries(categoryCounts)
      .map(([category, count]) => ({
        category,
        percentage: Math.round((count / total) * 100)
      }))
      .sort((a, b) => b.percentage - a.percentage)
      .slice(0, 2); // 최대 2개만 반환
    
    return stats;
  };

  // 릴스 재생수 통계 계산
  const calculateReelsStats = (results: any[]): Array<{reelId: string, videoPlayCount: number}> => {
    const reelPlayCounts: { [key: string]: number } = {};
    const total = results.length;

    if (total === 0) return [];

    results.forEach(result => {
      const reelId = result.reel_id || '알 수 없음';
      reelPlayCounts[reelId] = (reelPlayCounts[reelId] || 0) + 1;
    });

    const stats = Object.entries(reelPlayCounts)
      .map(([reelId, count]) => ({
        reelId,
        videoPlayCount: count
      }))
      .sort((a, b) => b.videoPlayCount - a.videoPlayCount);

    return stats;
  };

  const buildOverrideEntryFromStats = (
    stats: Array<{ motivation?: string; category?: string; percentage: number }>,
    labelKey: 'motivation' | 'category',
  ): OverrideFieldState => {
    const primary = stats?.[0];
    const secondary = stats?.[1];

    const toStringValue = (value?: number) =>
      value === undefined || value === null ? '' : String(value);

    return {
      primaryLabel: primary ? String(primary[labelKey] ?? '') : '',
      primaryPercentage: toStringValue(primary?.percentage),
      secondaryLabel: secondary ? String(secondary[labelKey] ?? '') : '',
      secondaryPercentage: toStringValue(secondary?.percentage),
    };
  };

  const cancelOverrideEdit = () => {
    setEditingUsername(null);
    setOverrideForm(null);
    setIsSavingOverride(false);
  };

  const toggleOverrideEditor = (row: AnalysisData) => {
    if (editingUsername === row.username) {
      cancelOverrideEdit();
      return;
    }

    setEditingUsername(row.username);
    setOverrideForm({
      subscriptionMotivation: buildOverrideEntryFromStats(
        row.subscriptionMotivationStats || [],
        'motivation',
      ),
      category: buildOverrideEntryFromStats(row.categoryStats || [], 'category'),
    });
  };

  const handleOverrideInputChange = (
    section: keyof OverrideFormState,
    field: keyof OverrideFieldState,
    value: string,
  ) => {
    setOverrideForm(prev =>
      prev
        ? {
            ...prev,
            [section]: {
              ...prev[section],
              [field]: value,
            },
          }
        : prev,
    );
  };

  const composeOverridePayload = (
    entry: OverrideFieldState,
    sectionName: string,
  ): { payload?: ClassificationOverridePayload; error?: boolean } => {
    const primaryLabel = entry.primaryLabel.trim();
    const primaryPercentageRaw = entry.primaryPercentage.trim();
    const secondaryLabel = entry.secondaryLabel.trim();
    const secondaryPercentageRaw = entry.secondaryPercentage.trim();

    if (!primaryLabel) {
      if (primaryPercentageRaw || secondaryLabel || secondaryPercentageRaw) {
        toast.error(`${sectionName} 1순위 항목과 비율을 모두 입력해주세요.`);
        return { error: true };
      }
      return {};
    }

    if (!primaryPercentageRaw) {
      toast.error(`${sectionName} 1순위 비율을 입력해주세요.`);
      return { error: true };
    }

    const primaryPercentage = Number(primaryPercentageRaw);
    if (Number.isNaN(primaryPercentage) || primaryPercentage < 0 || primaryPercentage > 100) {
      toast.error(`${sectionName} 1순위 비율은 0~100 사이의 숫자여야 합니다.`);
      return { error: true };
    }

    const payload: ClassificationOverridePayload = {
      primary_label: primaryLabel,
      primary_percentage: primaryPercentage,
    };

    if (secondaryLabel || secondaryPercentageRaw) {
      if (!secondaryLabel || !secondaryPercentageRaw) {
        toast.error(`${sectionName} 2순위 항목은 명칭과 비율을 모두 입력해주세요.`);
        return { error: true };
      }

      const secondaryPercentage = Number(secondaryPercentageRaw);
      if (Number.isNaN(secondaryPercentage) || secondaryPercentage < 0 || secondaryPercentage > 100) {
        toast.error(`${sectionName} 2순위 비율은 0~100 사이의 숫자여야 합니다.`);
        return { error: true };
      }

      payload.secondary_label = secondaryLabel;
      payload.secondary_percentage = secondaryPercentage;
    }

    return { payload };
  };

  const buildMotivationStatsFromPayload = (
    payload: ClassificationOverridePayload,
  ): Array<{ motivation: string; percentage: number }> => {
    const stats: Array<{ motivation: string; percentage: number }> = [];

    if (payload.primary_label) {
      stats.push({
        motivation: payload.primary_label,
        percentage: payload.primary_percentage ?? 0,
      });
    }

    if (payload.secondary_label) {
      stats.push({
        motivation: payload.secondary_label,
        percentage: payload.secondary_percentage ?? 0,
      });
    }

    return stats;
  };

  const buildCategoryStatsFromPayload = (
    payload: ClassificationOverridePayload,
  ): Array<{ category: string; percentage: number }> => {
    const stats: Array<{ category: string; percentage: number }> = [];

    if (payload.primary_label) {
      stats.push({
        category: payload.primary_label,
        percentage: payload.primary_percentage ?? 0,
      });
    }

    if (payload.secondary_label) {
      stats.push({
        category: payload.secondary_label,
        percentage: payload.secondary_percentage ?? 0,
      });
    }

    return stats;
  };

  const saveOverrideChanges = async () => {
    if (!editingUsername || !overrideForm) {
      return;
    }

    const motivationResult = composeOverridePayload(
      overrideForm.subscriptionMotivation,
      '구독 동기',
    );
    if (motivationResult?.error) {
      return;
    }

    const categoryResult = composeOverridePayload(overrideForm.category, '카테고리');
    if (categoryResult?.error) {
      return;
    }

    const payload: ClassificationOverrideUpdateRequest = {};
    if (motivationResult?.payload) {
      payload.subscription_motivation = motivationResult.payload;
    }
    if (categoryResult?.payload) {
      payload.category = categoryResult.payload;
    }

    if (!payload.subscription_motivation && !payload.category) {
      toast.error('최소 한 종류의 1순위 분류를 입력해주세요.');
      return;
    }

    try {
      setIsSavingOverride(true);
      await classificationService.updateAggregatedSummary(editingUsername, payload);
      toast.success('수정 내용이 저장되었습니다.');
      
      // analysisData 업데이트
      setAnalysisData(prev =>
        prev.map(row => {
          if (row.username !== editingUsername) {
            return row;
          }

          const updatedRow: AnalysisData = { ...row };

          if (payload.subscription_motivation) {
            updatedRow.subscriptionMotivationStats = buildMotivationStatsFromPayload(
              payload.subscription_motivation,
            );
          }

          if (payload.category) {
            updatedRow.categoryStats = buildCategoryStatsFromPayload(payload.category);
          }

          return updatedRow;
        }),
      );
      cancelOverrideEdit();
    } catch (error: any) {
      const message = error?.message || '수정 내용을 저장하지 못했습니다.';
      toast.error(message);
    } finally {
      setIsSavingOverride(false);
    }
  };

  // 분석 결과 내보내기
  const exportAnalysisResults = () => {
    // 필터링된 데이터 계산
    const filteredData = (analysisData || []).filter((data) => {
      if (filters.username && data.username !== filters.username) {
        return false;
      }
      if (data.followers !== undefined) {
        const min = filters.followersMin || 0;
        const max = filters.followersMax || getMaxValue('followers');
        if (data.followers < min || data.followers > max) {
          return false;
        }
      }
      if (data.avgLikes !== undefined) {
        const min = filters.avgLikesMin || 0;
        const max = filters.avgLikesMax || getMaxValue('avgLikes');
        if (data.avgLikes < min || data.avgLikes > max) {
          return false;
        }
      }
      if (data.avgComments !== undefined) {
        const min = filters.avgCommentsMin || 0;
        const max = filters.avgCommentsMax || getMaxValue('avgComments');
        if (data.avgComments < min || data.avgComments > max) {
          return false;
        }
      }
      if (filters.grade && data.grade !== filters.grade) {
        return false;
      }
      const motivation1 = data.subscriptionMotivationStats?.[0];
      if (filters.motivation1 && (!motivation1 || motivation1.motivation !== filters.motivation1)) {
        return false;
      }
      const motivation2 = data.subscriptionMotivationStats?.[1];
      if (filters.motivation2 && (!motivation2 || motivation2.motivation !== filters.motivation2)) {
        return false;
      }
      const category1 = data.categoryStats?.[0];
      if (filters.category1 && (!category1 || category1.category !== filters.category1)) {
        return false;
      }
      const category2 = data.categoryStats?.[1];
      if (filters.category2 && (!category2 || category2.category !== filters.category2)) {
        return false;
      }
      if (filters.memo && (!data.memo || !data.memo.toLowerCase().includes(filters.memo.toLowerCase()))) {
        return false;
      }
      if (filters.accountType && (!data.category || data.category !== filters.accountType)) {
        return false;
      }
      return true;
    });

    // 선택된 계정만 필터링
    const dataToExport = selectedUsernames.size > 0
      ? filteredData.filter(data => selectedUsernames.has(data.username))
      : filteredData;

    if (dataToExport.length === 0) {
      toast.error('내보낼 분석 결과가 없습니다');
      return;
    }

    // UTF-8 BOM 추가하여 엑셀에서 한글이 깨지지 않도록 함
    const BOM = '\uFEFF';
    const csvContent = BOM + [
      ['사용자명', '이름', '팔로워', '등급', '계정 유형', '평균참여율', '평균 조회수', '평균 좋아요', '평균 댓글', '구독 동기 1', '구독 동기 2', '카테고리 1', '카테고리 2', '메모'].join(','),
      ...dataToExport.map(data => {
        const motivation1 = data.subscriptionMotivationStats?.[0];
        const motivation2 = data.subscriptionMotivationStats?.[1];
        const category1 = data.categoryStats?.[0];
        const category2 = data.categoryStats?.[1];
        
        return [
          data.username,
          data.fullName || '-',
          data.followers || 0,
          data.grade || 'N/A',
          data.category ?? '',
          data.avgEngagementRate ? `${data.avgEngagementRate}%` : 'N/A',
          data.avgVideoPlayCount || 'N/A',
          data.avgLikes || 'N/A',
          data.avgComments || 'N/A',
          motivation1 ? motivation1.motivation : '-',
          motivation2 ? motivation2.motivation : '-',
          category1 ? category1.category : '-',
          category2 ? category2.category : '-',
          data.memo || '-'
        ].map(cell => {
          // CSV에서 쉼표나 따옴표가 포함된 경우 처리
          const cellStr = String(cell);
          if (cellStr.includes(',') || cellStr.includes('"') || cellStr.includes('\n')) {
            return `"${cellStr.replace(/"/g, '""')}"`;
          }
          return cellStr;
        }).join(',');
      })
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `전체분석결과_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    toast.success(`선택된 ${dataToExport.length}명의 분석 결과가 CSV 파일로 내보내졌습니다`);
  };

  // 컴포넌트 마운트 시 사용자 목록 로드
  useEffect(() => {
    loadUsers();
  }, []);

  return (
    <Container>
      <Title>
        <BarChart3 size={24} />
        전체 분석
      </Title>

      <HeaderActions>
        <Button
          onClick={runOverallAnalysis}
          disabled={isAnalyzing || users.length === 0}
        >
          {isAnalyzing ? (
            <>
              <LoadingSpinner />
              분석 중...
            </>
          ) : (
            <>
              <BarChart3 size={16} />
              전체 분석 실행
            </>
          )}
        </Button>
        
        {analysisData.length > 0 && (
          <SuccessButton onClick={exportAnalysisResults}>
            <Download size={16} />
            CSV 내보내기
          </SuccessButton>
        )}
      </HeaderActions>

      {/* 분석 상태 정보 */}
      <InfoBox>
        <Users size={20} style={{ color: '#0c5460' }} />
        <InfoText>
          <InfoTitle>
            총 <strong>{users.length}명</strong>의 사용자 데이터가 있습니다
          </InfoTitle>
          <InfoSubtext>
            전체 분석을 실행하면 각 사용자의 상세 통계를 확인할 수 있습니다
          </InfoSubtext>
        </InfoText>
      </InfoBox>

      {/* 필터 섹션 */}
      {analysisData.length > 0 && (
        <Section>
          <div 
            onClick={() => setFilterExpanded(!filterExpanded)} 
            style={{ 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem',
              marginBottom: filterExpanded ? '1rem' : '0'
            }}
          >
            <span style={{ fontSize: '0.8rem' }}>{filterExpanded ? '▼' : '▶'}</span>
            <SectionTitle style={{ margin: 0 }}>필터</SectionTitle>
          </div>
          
          {filterExpanded && (
            <div style={{ marginTop: '1rem' }}>
              {/* 첫 번째 줄: 아이디, 등급, 계정 유형 (각각 밑에 슬라이더) */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>아이디</label>
                  <Select
                    value={filters.username}
                    onChange={(e) => setFilters({...filters, username: e.target.value})}
                  >
                    <option value="">전체</option>
                    {analysisData.map(data => (
                      <option key={data.username} value={data.username}>@{data.username}</option>
                    ))}
                  </Select>
                  <div style={{ marginTop: '0.5rem' }}>
                    <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.5rem', display: 'block' }}>
                      팔로워 수
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <div style={{ flex: 1 }}>
                        <label style={{ fontSize: '0.7rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>최소</label>
                        <Input
                          type="number"
                          min="0"
                          max={getMaxValue('followers')}
                          value={filters.followersMin || ''}
                          onChange={(e) => {
                            const value = e.target.value;
                            if (value === '') {
                              setFilters({...filters, followersMin: 0});
                              return;
                            }
                            const newMin = parseInt(value) || 0;
                            const max = Math.min(filters.followersMax || getMaxValue('followers'), getMaxValue('followers'));
                            if (newMin <= max && newMin >= 0) {
                              setFilters({...filters, followersMin: newMin});
                            }
                          }}
                          style={{ padding: '0.5rem', fontSize: '0.875rem' }}
                        />
                      </div>
                      <span style={{ marginTop: '1.5rem', color: '#6c757d' }}>~</span>
                      <div style={{ flex: 1 }}>
                        <label style={{ fontSize: '0.7rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>최대</label>
                        <Input
                          type="number"
                          min={filters.followersMin || 0}
                          max={getMaxValue('followers')}
                          value={filters.followersMax || ''}
                          onChange={(e) => {
                            const value = e.target.value;
                            const maxValue = getMaxValue('followers');
                            if (value === '') {
                              setFilters({...filters, followersMax: maxValue});
                              return;
                            }
                            const newMax = Math.min(parseInt(value) || maxValue, maxValue);
                            const min = filters.followersMin || 0;
                            if (newMax >= min && newMax <= maxValue) {
                              setFilters({...filters, followersMax: newMax});
                            }
                          }}
                          style={{ padding: '0.5rem', fontSize: '0.875rem' }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>등급</label>
                  <Select
                    value={filters.grade}
                    onChange={(e) => setFilters({...filters, grade: e.target.value})}
                  >
                    {gradeOptions.map(option => (
                      <option key={option} value={option}>{option || '전체'}</option>
                    ))}
                  </Select>
                  <div style={{ marginTop: '0.5rem' }}>
                    <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.5rem', display: 'block' }}>
                      평균 좋아요 수
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <div style={{ flex: 1 }}>
                        <label style={{ fontSize: '0.7rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>최소</label>
                        <Input
                          type="number"
                          min="0"
                          max={getMaxValue('avgLikes')}
                          value={filters.avgLikesMin || ''}
                          onChange={(e) => {
                            const value = e.target.value;
                            if (value === '') {
                              setFilters({...filters, avgLikesMin: 0});
                              return;
                            }
                            const newMin = parseInt(value) || 0;
                            const max = Math.min(filters.avgLikesMax || getMaxValue('avgLikes'), getMaxValue('avgLikes'));
                            if (newMin <= max && newMin >= 0) {
                              setFilters({...filters, avgLikesMin: newMin});
                            }
                          }}
                          style={{ padding: '0.5rem', fontSize: '0.875rem' }}
                        />
                      </div>
                      <span style={{ marginTop: '1.5rem', color: '#6c757d' }}>~</span>
                      <div style={{ flex: 1 }}>
                        <label style={{ fontSize: '0.7rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>최대</label>
                        <Input
                          type="number"
                          min={filters.avgLikesMin || 0}
                          max={getMaxValue('avgLikes')}
                          value={filters.avgLikesMax || ''}
                          onChange={(e) => {
                            const value = e.target.value;
                            const maxValue = getMaxValue('avgLikes');
                            if (value === '') {
                              setFilters({...filters, avgLikesMax: maxValue});
                              return;
                            }
                            const newMax = Math.min(parseInt(value) || maxValue, maxValue);
                            const min = filters.avgLikesMin || 0;
                            if (newMax >= min && newMax <= maxValue) {
                              setFilters({...filters, avgLikesMax: newMax});
                            }
                          }}
                          style={{ padding: '0.5rem', fontSize: '0.875rem' }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>계정 유형</label>
                  <Select
                    value={filters.accountType}
                    onChange={(e) => setFilters({...filters, accountType: e.target.value})}
                  >
                    {accountTypeOptions.map(option => (
                      <option key={option} value={option}>{option || '전체'}</option>
                    ))}
                  </Select>
                  <div style={{ marginTop: '0.5rem' }}>
                    <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.5rem', display: 'block' }}>
                      평균 댓글 수
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <div style={{ flex: 1 }}>
                        <label style={{ fontSize: '0.7rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>최소</label>
                        <Input
                          type="number"
                          min="0"
                          max={getMaxValue('avgComments')}
                          value={filters.avgCommentsMin || ''}
                          onChange={(e) => {
                            const value = e.target.value;
                            if (value === '') {
                              setFilters({...filters, avgCommentsMin: 0});
                              return;
                            }
                            const newMin = parseInt(value) || 0;
                            const max = Math.min(filters.avgCommentsMax || getMaxValue('avgComments'), getMaxValue('avgComments'));
                            if (newMin <= max && newMin >= 0) {
                              setFilters({...filters, avgCommentsMin: newMin});
                            }
                          }}
                          style={{ padding: '0.5rem', fontSize: '0.875rem' }}
                        />
                      </div>
                      <span style={{ marginTop: '1.5rem', color: '#6c757d' }}>~</span>
                      <div style={{ flex: 1 }}>
                        <label style={{ fontSize: '0.7rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>최대</label>
                        <Input
                          type="number"
                          min={filters.avgCommentsMin || 0}
                          max={getMaxValue('avgComments')}
                          value={filters.avgCommentsMax || ''}
                          onChange={(e) => {
                            const value = e.target.value;
                            const maxValue = getMaxValue('avgComments');
                            if (value === '') {
                              setFilters({...filters, avgCommentsMax: maxValue});
                              return;
                            }
                            const newMax = Math.min(parseInt(value) || maxValue, maxValue);
                            const min = filters.avgCommentsMin || 0;
                            if (newMax >= min && newMax <= maxValue) {
                              setFilters({...filters, avgCommentsMax: newMax});
                            }
                          }}
                          style={{ padding: '0.5rem', fontSize: '0.875rem' }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 두 번째 줄: 구독동기1, 구독동기 2, 카테고리 1, 카테고리 2 */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>구독동기 1</label>
                  <Select
                    value={filters.motivation1}
                    onChange={(e) => setFilters({...filters, motivation1: e.target.value})}
                  >
                    {motivationOptions.map(option => (
                      <option key={option} value={option}>{option || '전체'}</option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>구독동기 2</label>
                  <Select
                    value={filters.motivation2}
                    onChange={(e) => setFilters({...filters, motivation2: e.target.value})}
                  >
                    {motivationOptions.map(option => (
                      <option key={option} value={option}>{option || '전체'}</option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>카테고리 1</label>
                  <Select
                    value={filters.category1}
                    onChange={(e) => setFilters({...filters, category1: e.target.value})}
                  >
                    {categoryOptions.map(option => (
                      <option key={option} value={option}>{option || '전체'}</option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>카테고리 2</label>
                  <Select
                    value={filters.category2}
                    onChange={(e) => setFilters({...filters, category2: e.target.value})}
                  >
                    {categoryOptions.map(option => (
                      <option key={option} value={option}>{option || '전체'}</option>
                    ))}
                  </Select>
                </div>
              </div>

              {/* 세 번째 줄: 메모 */}
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>메모</label>
                <div style={{ maxWidth: '50%' }}>
                  <Input
                    type="text"
                    placeholder="메모 검색"
                    value={filters.memo}
                    onChange={(e) => setFilters({...filters, memo: e.target.value})}
                  />
                </div>
              </div>

              {/* 필터 초기화 버튼 */}
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <SmallButton
                  onClick={() => {
                    const maxFollowers = getMaxValue('followers');
                    const maxLikes = getMaxValue('avgLikes');
                    const maxComments = getMaxValue('avgComments');
                    setFilters({
                      username: '',
                      followersMin: 0,
                      followersMax: maxFollowers,
                      avgLikesMin: 0,
                      avgLikesMax: maxLikes,
                      avgCommentsMin: 0,
                      avgCommentsMax: maxComments,
                      grade: '',
                      motivation1: '',
                      motivation2: '',
                      category1: '',
                      category2: '',
                      memo: '',
                      accountType: ''
                    });
                  }}
                >
                  필터 초기화
                </SmallButton>
              </div>
            </div>
          )}
        </Section>
      )}

      {/* 분석 결과 테이블 */}
      {analysisData.length > 0 ? (() => {
        // 필터링된 데이터 계산
        const filteredData = (analysisData || []).filter((data) => {
                  // 필터링 로직
                  if (filters.username && data.username !== filters.username) {
                    return false;
                  }
                  if (data.followers !== undefined) {
                    const min = filters.followersMin || 0;
                    const max = filters.followersMax || getMaxValue('followers');
                    if (data.followers < min || data.followers > max) {
                      return false;
                    }
                  }
                  if (data.avgLikes !== undefined) {
                    const min = filters.avgLikesMin || 0;
                    const max = filters.avgLikesMax || getMaxValue('avgLikes');
                    if (data.avgLikes < min || data.avgLikes > max) {
                      return false;
                    }
                  }
                  if (data.avgComments !== undefined) {
                    const min = filters.avgCommentsMin || 0;
                    const max = filters.avgCommentsMax || getMaxValue('avgComments');
                    if (data.avgComments < min || data.avgComments > max) {
                      return false;
                    }
                  }
                  if (filters.grade && data.grade !== filters.grade) {
                    return false;
                  }
                  const motivation1 = data.subscriptionMotivationStats?.[0];
                  if (filters.motivation1 && (!motivation1 || motivation1.motivation !== filters.motivation1)) {
                    return false;
                  }
                  const motivation2 = data.subscriptionMotivationStats?.[1];
                  if (filters.motivation2 && (!motivation2 || motivation2.motivation !== filters.motivation2)) {
                    return false;
                  }
                  const category1 = data.categoryStats?.[0];
                  if (filters.category1 && (!category1 || category1.category !== filters.category1)) {
                    return false;
                  }
                  const category2 = data.categoryStats?.[1];
                  if (filters.category2 && (!category2 || category2.category !== filters.category2)) {
                    return false;
                  }
                  if (filters.memo && (!data.memo || !data.memo.toLowerCase().includes(filters.memo.toLowerCase()))) {
                    return false;
                  }
                  if (filters.accountType && (!data.category || data.category !== filters.accountType)) {
                    return false;
                  }
                  return true;
                });

        // 페이지네이션 계산
        const totalPages = Math.ceil(filteredData.length / itemsPerPage);
        const startIndex = (currentPage - 1) * itemsPerPage;
        const endIndex = startIndex + itemsPerPage;
        const paginatedData = filteredData.slice(startIndex, endIndex);

        // 현재 페이지의 모든 항목이 선택되었는지 확인
        const allPageSelected = paginatedData.length > 0 && paginatedData.every(data => selectedUsernames.has(data.username));
        // 필터링된 데이터 중 선택된 항목 수
        const selectedCount = filteredData.filter(data => selectedUsernames.has(data.username)).length;

        // 전체 선택/해제 핸들러
        const handleSelectAll = (checked: boolean) => {
          if (checked) {
            const newSelected = new Set(selectedUsernames);
            filteredData.forEach(data => newSelected.add(data.username));
            setSelectedUsernames(newSelected);
          } else {
            const newSelected = new Set(selectedUsernames);
            filteredData.forEach(data => newSelected.delete(data.username));
            setSelectedUsernames(newSelected);
          }
        };

        // 개별 선택/해제 핸들러
        const handleSelectOne = (username: string, checked: boolean) => {
          const newSelected = new Set(selectedUsernames);
          if (checked) {
            newSelected.add(username);
          } else {
            newSelected.delete(username);
          }
          setSelectedUsernames(newSelected);
        };

        return (
          <Section>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.875rem', color: '#6c757d' }}>
                {selectedCount > 0 && (
                  <span>선택된 계정: {selectedCount}개</span>
                )}
              </div>
              {selectedCount > 0 && (
                <SmallButton
                  onClick={() => {
                    const newSelected = new Set(selectedUsernames);
                    filteredData.forEach(data => newSelected.delete(data.username));
                    setSelectedUsernames(newSelected);
                  }}
                >
                  선택 해제
                </SmallButton>
              )}
            </div>
            <TableContainer>
              <Table>
                <thead>
                  <tr>
                    <TableHeader style={{ width: '40px', textAlign: 'center' }}>
                      <input
                        type="checkbox"
                        checked={allPageSelected}
                        onChange={(e) => handleSelectAll(e.target.checked)}
                        style={{ cursor: 'pointer' }}
                      />
                    </TableHeader>
                    <TableHeader>사용자명</TableHeader>
                    <TableHeader>이름</TableHeader>
                    <TableHeader>팔로워</TableHeader>
                    <TableHeader>등급</TableHeader>
                    <TableHeader>계정 유형</TableHeader>
                    <TableHeader>평균참여율</TableHeader>
                    <TableHeader>평균 조회수</TableHeader>
                    <TableHeader>평균 좋아요</TableHeader>
                    <TableHeader>평균 댓글</TableHeader>
                    <TableHeader>구독 동기 1</TableHeader>
                    <TableHeader>구독 동기 2</TableHeader>
                    <TableHeader>카테고리 1</TableHeader>
                    <TableHeader>카테고리 2</TableHeader>
                    <TableHeader>메모</TableHeader>
                    <TableHeader>관리</TableHeader>
                  </tr>
                </thead>
                <tbody>
                  {paginatedData.map((data, index) => {
                    const motivation1 = data.subscriptionMotivationStats?.[0];
                    const motivation2 = data.subscriptionMotivationStats?.[1];
                    const category1 = data.categoryStats?.[0];
                    const category2 = data.categoryStats?.[1];
                    
                    return (
                      <React.Fragment key={data.username}>
                        <TableRow isEven={index % 2 === 0}>
                      <TableCell style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={selectedUsernames.has(data.username)}
                          onChange={(e) => handleSelectOne(data.username, e.target.checked)}
                          style={{ cursor: 'pointer' }}
                        />
                      </TableCell>
                      <TableCell>
                        <UsernameBadge>@{data.username}</UsernameBadge>
                      </TableCell>
                      <TableCell>
                        {data.fullName || '-'}
                      </TableCell>
                      <TableCell>
                        {data.followers ? data.followers.toLocaleString() : 'N/A'}
                      </TableCell>
                      <TableCell>
                        {data.grade || 'N/A'}
                      </TableCell>
                      <TableCell>
                        {data.category ?? ''}
                      </TableCell>
                      <TableCell>
                        {data.avgEngagementRate ? `${data.avgEngagementRate}%` : 'N/A'}
                      </TableCell>
                      <TableCell>
                        {data.avgVideoPlayCount ? data.avgVideoPlayCount.toLocaleString() : 'N/A'}
                      </TableCell>
                      <TableCell>
                        {data.avgLikes ? data.avgLikes.toLocaleString() : 'N/A'}
                      </TableCell>
                      <TableCell>
                        {data.avgComments ? data.avgComments.toLocaleString() : 'N/A'}
                      </TableCell>
                      <TableCell>
                          {motivation1 ? motivation1.motivation : '-'}
                      </TableCell>
                      <TableCell>
                          {motivation2 ? motivation2.motivation : '-'}
                      </TableCell>
                      <TableCell>
                          {category1 ? category1.category : '-'}
                      </TableCell>
                      <TableCell>
                          {category2 ? category2.category : '-'}
                      </TableCell>
                      <TableCell>
                          {editingAnalysisRow === data.username && analysisEditForm ? (
                          <input
                            type="text"
                              value={analysisEditForm.memo}
                              onChange={(e) => analysisEditForm && setAnalysisEditForm({...analysisEditForm, memo: e.target.value})}
                              style={{width: '100%', padding: '4px', border: '1px solid #ddd', borderRadius: '4px'}}
                            />
                          ) : (
                            <span>{data.memo || '-'}</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {editingAnalysisRow === data.username ? (
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                              <SmallButton
                                onClick={async () => {
                                  if (!analysisEditForm) return;
                                  
                                  try {
                                    setIsSavingAnalysisEdit(true);
                                    
                                    // 구독동기/카테고리 저장
                                    const classificationPayload: ClassificationOverrideUpdateRequest = {};
                                    
                                    if (analysisEditForm.motivation1) {
                                      const motivation1Percent = motivation1?.percentage || 0;
                                      const motivation2Percent = motivation2?.percentage || 0;
                                      classificationPayload.subscription_motivation = {
                                        primary_label: analysisEditForm.motivation1,
                                        primary_percentage: motivation1Percent,
                                        ...(analysisEditForm.motivation2 ? {
                                          secondary_label: analysisEditForm.motivation2,
                                          secondary_percentage: motivation2Percent
                                        } : {})
                                      };
                                    }
                                    
                                    if (analysisEditForm.category1) {
                                      const category1Percent = category1?.percentage || 0;
                                      const category2Percent = category2?.percentage || 0;
                                      classificationPayload.category = {
                                        primary_label: analysisEditForm.category1,
                                        primary_percentage: category1Percent,
                                        ...(analysisEditForm.category2 ? {
                                          secondary_label: analysisEditForm.category2,
                                          secondary_percentage: category2Percent
                                        } : {})
                                      };
                                    }
                                    
                                    if (Object.keys(classificationPayload).length > 0) {
                                      await classificationService.updateAggregatedSummary(data.username, classificationPayload);
                                    }
                                    
                                    // 메모 저장
                                    const memoResponse = await fetch(`/api/influencer/files/user-profile/${data.username}/memo`, {
                                      method: 'PUT',
                                      headers: {
                                        'Content-Type': 'application/json',
                                      },
                                      body: JSON.stringify({ memo: analysisEditForm.memo || null }),
                                    });
                                    
                                    if (!memoResponse.ok) {
                                      throw new Error('메모 저장 실패');
                                    }
                                    
                                    // 로컬 상태 업데이트
                                    const updated = analysisData.map(item => {
                                      if (item.username === data.username) {
                                        const updatedItem = {...item};
                                        
                                        if (analysisEditForm.motivation1) {
                                          updatedItem.subscriptionMotivationStats = [
                                            { motivation: analysisEditForm.motivation1, percentage: motivation1?.percentage || 0 },
                                            ...(analysisEditForm.motivation2 ? [{ motivation: analysisEditForm.motivation2, percentage: motivation2?.percentage || 0 }] : [])
                                          ];
                                        }
                                        
                                        if (analysisEditForm.category1) {
                                          updatedItem.categoryStats = [
                                            { category: analysisEditForm.category1, percentage: category1?.percentage || 0 },
                                            ...(analysisEditForm.category2 ? [{ category: analysisEditForm.category2, percentage: category2?.percentage || 0 }] : [])
                                          ];
                                        }
                                        
                                        updatedItem.memo = analysisEditForm.memo || '';
                                        
                                        return updatedItem;
                                      }
                                      return item;
                                    });
                                    
                              setAnalysisData(updated);
                                    setEditingAnalysisRow(null);
                                    setAnalysisEditForm(null);
                                    toast.success('수정 내용이 저장되었습니다');
                                  } catch (error: any) {
                                    console.error('저장 오류:', error);
                                    toast.error(error?.message || '저장 중 오류가 발생했습니다');
                                  } finally {
                                    setIsSavingAnalysisEdit(false);
                                  }
                                }}
                                disabled={isSavingAnalysisEdit}
                              >
                                {isSavingAnalysisEdit ? '저장 중...' : '저장'}
                              </SmallButton>
                              <SmallButton
                                onClick={() => {
                                  setEditingAnalysisRow(null);
                                  setAnalysisEditForm(null);
                                }}
                                disabled={isSavingAnalysisEdit}
                              >
                                취소
                              </SmallButton>
                            </div>
                          ) : (
                            <SmallButton
                              onClick={() => {
                                setEditingAnalysisRow(data.username);
                                setAnalysisEditForm({
                                  motivation1: motivation1?.motivation || '',
                                  motivation2: motivation2?.motivation || '',
                                  category1: category1?.category || '',
                                  category2: category2?.category || '',
                                  memo: data.memo || ''
                                });
                              }}
                            >
                              수정
                            </SmallButton>
                        )}
                      </TableCell>
                    </TableRow>
                      {editingAnalysisRow === data.username && analysisEditForm && (
                        <TableRow>
                          <TableCell colSpan={16}>
                            <OverrideFormContainer>
                              <OverrideSection>
                                <OverrideSectionTitle>구독 동기</OverrideSectionTitle>
                                <OverrideFieldGrid>
                                  <div>
                                    <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>구독 동기 1</label>
                                    <Input
                                      type="text"
                                      placeholder="구독 동기 1"
                                      value={analysisEditForm.motivation1}
                                      onChange={(e) => setAnalysisEditForm({...analysisEditForm, motivation1: e.target.value})}
                                    />
                                  </div>
                                  <div>
                                    <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>구독 동기 2</label>
                                    <Input
                                      type="text"
                                      placeholder="구독 동기 2"
                                      value={analysisEditForm.motivation2}
                                      onChange={(e) => setAnalysisEditForm({...analysisEditForm, motivation2: e.target.value})}
                                    />
                                  </div>
                                </OverrideFieldGrid>
                              </OverrideSection>
                              <OverrideSection>
                                <OverrideSectionTitle>카테고리</OverrideSectionTitle>
                                <OverrideFieldGrid>
                                  <div>
                                    <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>카테고리 1</label>
                                    <Input
                                      type="text"
                                      placeholder="카테고리 1"
                                      value={analysisEditForm.category1}
                                      onChange={(e) => setAnalysisEditForm({...analysisEditForm, category1: e.target.value})}
                                    />
                                  </div>
                                  <div>
                                    <label style={{ fontSize: '0.75rem', color: '#6c757d', marginBottom: '0.25rem', display: 'block' }}>카테고리 2</label>
                                    <Input
                                      type="text"
                                      placeholder="카테고리 2"
                                      value={analysisEditForm.category2}
                                      onChange={(e) => setAnalysisEditForm({...analysisEditForm, category2: e.target.value})}
                                    />
                                  </div>
                                </OverrideFieldGrid>
                              </OverrideSection>
                              <OverrideSection>
                                <OverrideSectionTitle>메모</OverrideSectionTitle>
                                <Input
                                  type="text"
                                  placeholder="메모"
                                  value={analysisEditForm.memo}
                                  onChange={(e) => setAnalysisEditForm({...analysisEditForm, memo: e.target.value})}
                                />
                              </OverrideSection>
                            </OverrideFormContainer>
                          </TableCell>
                        </TableRow>
                      )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </Table>
            </TableContainer>
            
            {/* 페이지네이션 */}
            {totalPages > 1 && (
              <PaginationContainer>
                <PaginationButton
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  이전
                </PaginationButton>
                <PaginationInfo>
                  {currentPage} / {totalPages} 페이지 (총 {filteredData.length}명)
                </PaginationInfo>
                <PaginationButton
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                >
                  다음
                </PaginationButton>
              </PaginationContainer>
            )}
          </Section>
        );
      })() : (
        <EmptyState>
          <EmptyStateIcon />
          <EmptyStateTitle>
            전체 분석을 실행해주세요
          </EmptyStateTitle>
          <EmptyStateText>
            위의 "전체 분석 실행" 버튼을 클릭하면<br />
            모든 사용자의 상세 통계를 분석하여 표로 보여줍니다.
          </EmptyStateText>
          <EmptyStateHint>
            💡 분석에는 시간이 걸릴 수 있습니다
          </EmptyStateHint>
        </EmptyState>
      )}

      {/* 분석 완료 후 안내 */}
      {analysisData.length > 0 && (
        <SuccessBox>
          <CheckCircle size={20} style={{ color: '#155724' }} />
          <SuccessText>
            분석이 완료되었습니다! CSV 내보내기 버튼으로 결과를 다운로드할 수 있습니다.
          </SuccessText>
        </SuccessBox>
      )}
    </Container>
  );
};

export default OverallAnalysisTab;
