import React, { useState, useEffect } from 'react';
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
  followers?: number;
  category?: string;
  avgEngagementRate?: number;
  avgVideoPlayCount?: number;
  subscriptionMotivationStats?: Array<{motivation: string, percentage: number}>;
  categoryStats?: Array<{category: string, percentage: number}>;
  reelsStats?: Array<{reelId: string, videoPlayCount: number}>;
  postsCount?: number;
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
  max-width: 1200px;
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
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 1.5rem;
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
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
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

const OverallAnalysisTab: React.FC = () => {
  const [users, setUsers] = useState<UserData[]>([]);
  const [analysisData, setAnalysisData] = useState<AnalysisData[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  // 선택 사용자 분류 결과 보기 상태
  const [selectSearch, setSelectSearch] = useState('');
  const [selectedUsernames, setSelectedUsernames] = useState<string[]>([]);
  const [selectedViewData, setSelectedViewData] = useState<AnalysisData[]>([]);
  const [editingUsername, setEditingUsername] = useState<string | null>(null);
  const [overrideForm, setOverrideForm] = useState<OverrideFormState | null>(null);
  const [isSavingOverride, setIsSavingOverride] = useState(false);
  const filteredUsersForSelect = (users || []).filter(u => u.username.toLowerCase().includes(selectSearch.toLowerCase()));

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

  // 선택 사용자 분류 결과 로드
  const loadSelectedUsersClassification = async () => {
    if (selectedUsernames.length === 0) {
      toast.error('최소 한 명의 사용자를 선택해주세요');
      return;
    }
    try {
      toast.loading('선택한 사용자 분류 결과를 불러오는 중...');
      const results: AnalysisData[] = [];
      for (const username of selectedUsernames) {
        const data: AnalysisData = { username } as AnalysisData;
        data.subscriptionMotivationStats = [];
        data.categoryStats = [];

        try {
          const aggregatedResponse = await fetch(`/api/influencer/aggregated-summary/${username}`);
          if (aggregatedResponse.ok) {
            const aggregatedData: AggregatedSummaryResponse = await aggregatedResponse.json();
            const aggregatedSummaries = aggregatedData?.aggregated_summaries ?? {};

            const motivationEntries = buildTopEntriesFromAggregated(
              aggregatedSummaries.subscription_motivation,
            );
            if (motivationEntries.length) {
              data.subscriptionMotivationStats = mapTopEntriesToMotivationStats(
                motivationEntries,
              );
            }

            const categoryEntries = buildTopEntriesFromAggregated(aggregatedSummaries.category);
            if (categoryEntries.length) {
              data.categoryStats = mapTopEntriesToCategoryStats(categoryEntries);
            }
          }
        } catch (error) {
          console.log(`${username} 집계된 분류 요약 로드 실패:`, error);
        }

        if (!data.subscriptionMotivationStats?.length || !data.categoryStats?.length) {
          try {
            const res = await fetch(`/api/influencer/files/combined-classification/${username}`);
            if (res.ok) {
              const cls = await res.json();
              const results = Array.isArray(cls.results) ? cls.results : [];
              if (!data.subscriptionMotivationStats?.length) {
                data.subscriptionMotivationStats = calculateSubscriptionMotivationStats(results);
              }
              if (!data.categoryStats?.length) {
                data.categoryStats = calculateCategoryStats(results);
              }
            }
          } catch (error) {
            console.log(`${username} 통합 분류 결과 로드 실패:`, error);
          }
        }
        results.push(data);
      }
      setSelectedViewData(results);
      cancelOverrideEdit();
      toast.success('분류 결과를 불러왔습니다');
    } catch (e: any) {
      toast.error('분류 결과 로드 중 오류가 발생했습니다');
    } finally {
      toast.dismiss();
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
          
          // followers, category_name, avg_engagement을 profile.json에서 가져오기
          userAnalysis.followers = profileData.followers || 0;
          userAnalysis.category = profileData.category_name || '';
          userAnalysis.postsCount = profileData.posts_count || 0;
          
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
      setSelectedViewData(prev =>
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
    if (analysisData.length === 0) {
      toast.error('내보낼 분석 결과가 없습니다');
      return;
    }

    // UTF-8 BOM 추가하여 엑셀에서 한글이 깨지지 않도록 함
    const BOM = '\uFEFF';
    const csvContent = BOM + [
      ['사용자명', '팔로워', '카테고리', '평균참여율(%)', '평균비디오재생수', '구독 동기 분류', '카테고리 분류'].join(','),
      ...(analysisData || []).map(data => [
        data.username,
        data.followers || 0,
        data.category ?? '',
        data.avgEngagementRate || 0,
        data.avgVideoPlayCount || 0,
        formatMotivationStatsLine(data.subscriptionMotivationStats),
        formatCategoryStatsLine(data.categoryStats)
      ].join(','))
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
    
    toast.success('분석 결과가 CSV 파일로 내보내졌습니다');
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

      {/* 선택 사용자 분류 결과 보기 */}
      <Section>
        <SectionTitle>선택 사용자 분류 결과 보기</SectionTitle>
        <Grid>
          <div>
            <SearchContainer>
              <SearchIcon />
              <SearchInput
                type="text"
                value={selectSearch}
                onChange={(e) => setSelectSearch(e.target.value)}
                placeholder="사용자 검색..."
              />
            </SearchContainer>
            <UserListContainer style={{ marginTop: '0.75rem' }}>
              {(filteredUsersForSelect || []).map(u => (
                <UserItem key={u.username}>
                  <input
                    type="checkbox"
                    checked={selectedUsernames.includes(u.username)}
                    onChange={(e) => {
                      setSelectedUsernames(prev => e.target.checked ? [...prev, u.username] : prev.filter(x => x !== u.username));
                    }}
                  />
                  <UserText>@{u.username}</UserText>
                </UserItem>
              ))}
              {filteredUsersForSelect.length === 0 && (
                <div style={{ padding: '0.75rem', fontSize: '0.875rem', color: '#6c757d' }}>검색 결과 없음</div>
              )}
            </UserListContainer>
            <ButtonGroup>
              <SmallButton
                onClick={() => setSelectedUsernames((filteredUsersForSelect || []).map(u => u.username))}
              >
                전체 선택
              </SmallButton>
              <SmallButton
                onClick={() => setSelectedUsernames([])}
              >
                선택 해제
              </SmallButton>
            </ButtonGroup>
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <Button onClick={loadSelectedUsersClassification}>
                선택한 사용자 분류 결과 보기
              </Button>
              {selectedViewData.length > 0 && (
                <span style={{ fontSize: '0.875rem', color: '#6c757d' }}>{selectedViewData.length}명 결과</span>
              )}
            </div>
            {selectedViewData.length > 0 ? (
              <TableContainer>
                <Table>
                  <thead>
                    <tr>
                      <TableHeader>사용자</TableHeader>
                      <TableHeader>구독 동기 상위2</TableHeader>
                      <TableHeader>카테고리 상위2</TableHeader>
                      <TableHeader>관리</TableHeader>
                    </tr>
                  </thead>
                  <tbody>
                    {(selectedViewData || []).map(row => (
                      <React.Fragment key={row.username}>
                        <tr>
                          <TableCell>@{row.username}</TableCell>
                          <TableCell>
                            {formatMotivationStatsLine(row.subscriptionMotivationStats)
                              ? (
                                <StatItem>
                                  {formatMotivationStatsLine(row.subscriptionMotivationStats)}
                                </StatItem>
                              ) : (
                                <span style={{ color: '#9ca3af' }}>N/A</span>
                              )}
                          </TableCell>
                          <TableCell>
                            {formatCategoryStatsLine(row.categoryStats)
                              ? (
                                <StatItem>
                                  {formatCategoryStatsLine(row.categoryStats)}
                                </StatItem>
                              ) : (
                                <span style={{ color: '#9ca3af' }}>N/A</span>
                              )}
                          </TableCell>
                          <TableCell>
                            <SmallButton
                              type="button"
                              onClick={() => toggleOverrideEditor(row)}
                              disabled={isSavingOverride && editingUsername === row.username}
                            >
                              {editingUsername === row.username ? '편집 취소' : '수정'}
                            </SmallButton>
                          </TableCell>
                        </tr>
                        {editingUsername === row.username && overrideForm && (
                          <tr>
                            <TableCell colSpan={4}>
                              <OverrideFormContainer>
                                <OverrideSection>
                                  <OverrideSectionTitle>구독 동기 상위 2</OverrideSectionTitle>
                                  <OverrideFieldGrid>
                                    <Input
                                      type="text"
                                      placeholder="1순위 분류명"
                                      value={overrideForm.subscriptionMotivation.primaryLabel}
                                      onChange={(e) => handleOverrideInputChange('subscriptionMotivation', 'primaryLabel', e.target.value)}
                                    />
                                    <Input
                                      type="number"
                                      placeholder="1순위 %"
                                      min="0"
                                      max="100"
                                      step="0.1"
                                      value={overrideForm.subscriptionMotivation.primaryPercentage}
                                      onChange={(e) => handleOverrideInputChange('subscriptionMotivation', 'primaryPercentage', e.target.value)}
                                    />
                                    <Input
                                      type="text"
                                      placeholder="2순위 분류명"
                                      value={overrideForm.subscriptionMotivation.secondaryLabel}
                                      onChange={(e) => handleOverrideInputChange('subscriptionMotivation', 'secondaryLabel', e.target.value)}
                                    />
                                    <Input
                                      type="number"
                                      placeholder="2순위 %"
                                      min="0"
                                      max="100"
                                      step="0.1"
                                      value={overrideForm.subscriptionMotivation.secondaryPercentage}
                                      onChange={(e) => handleOverrideInputChange('subscriptionMotivation', 'secondaryPercentage', e.target.value)}
                                    />
                                  </OverrideFieldGrid>
                                </OverrideSection>
                                <OverrideSection>
                                  <OverrideSectionTitle>카테고리 상위 2</OverrideSectionTitle>
                                  <OverrideFieldGrid>
                                    <Input
                                      type="text"
                                      placeholder="1순위 카테고리"
                                      value={overrideForm.category.primaryLabel}
                                      onChange={(e) => handleOverrideInputChange('category', 'primaryLabel', e.target.value)}
                                    />
                                    <Input
                                      type="number"
                                      placeholder="1순위 %"
                                      min="0"
                                      max="100"
                                      step="0.1"
                                      value={overrideForm.category.primaryPercentage}
                                      onChange={(e) => handleOverrideInputChange('category', 'primaryPercentage', e.target.value)}
                                    />
                                    <Input
                                      type="text"
                                      placeholder="2순위 카테고리"
                                      value={overrideForm.category.secondaryLabel}
                                      onChange={(e) => handleOverrideInputChange('category', 'secondaryLabel', e.target.value)}
                                    />
                                    <Input
                                      type="number"
                                      placeholder="2순위 %"
                                      min="0"
                                      max="100"
                                      step="0.1"
                                      value={overrideForm.category.secondaryPercentage}
                                      onChange={(e) => handleOverrideInputChange('category', 'secondaryPercentage', e.target.value)}
                                    />
                                  </OverrideFieldGrid>
                                </OverrideSection>
                                <OverrideActions>
                                  <Button
                                    type="button"
                                    onClick={saveOverrideChanges}
                                    disabled={isSavingOverride}
                                  >
                                    {isSavingOverride ? '저장 중...' : '저장'}
                                  </Button>
                                  <SmallButton
                                    type="button"
                                    onClick={cancelOverrideEdit}
                                    disabled={isSavingOverride}
                                  >
                                    취소
                                  </SmallButton>
                                </OverrideActions>
                              </OverrideFormContainer>
                            </TableCell>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </Table>
              </TableContainer>
            ) : (
              <div style={{ fontSize: '0.875rem', color: '#6c757d' }}>왼쪽에서 사용자 검색/선택 후 "선택한 사용자 분류 결과 보기"를 눌러주세요.</div>
            )}
          </div>
        </Grid>
      </Section>

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

      {/* 분석 결과 테이블 */}
      {analysisData.length > 0 ? (
        <Section>
          <TableContainer>
            <Table>
              <thead>
                <tr>
                  <TableHeader>사용자명</TableHeader>
                  <TableHeader>팔로워</TableHeader>
                  <TableHeader>카테고리</TableHeader>
                  <TableHeader>평균참여율</TableHeader>
                  <TableHeader>평균비디오재생수</TableHeader>
                  <TableHeader>구독 동기 분류</TableHeader>
                  <TableHeader>카테고리 분류</TableHeader>
                </tr>
              </thead>
              <tbody>
                {(analysisData || []).map((data, index) => (
                  <TableRow key={data.username} isEven={index % 2 === 0}>
                    <TableCell>
                      <UsernameBadge>@{data.username}</UsernameBadge>
                    </TableCell>
                    <TableCell>
                      {data.followers ? data.followers.toLocaleString() : 'N/A'}
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
                      {formatMotivationStatsLine(data.subscriptionMotivationStats)
                        ? (
                          <StatItem>
                            {formatMotivationStatsLine(data.subscriptionMotivationStats)}
                          </StatItem>
                        ) : (
                          <span style={{ color: '#9ca3af' }}>N/A</span>
                        )}
                    </TableCell>
                    <TableCell>
                      {formatCategoryStatsLine(data.categoryStats)
                        ? (
                          <StatItem>
                            {formatCategoryStatsLine(data.categoryStats)}
                          </StatItem>
                        ) : (
                          <span style={{ color: '#9ca3af' }}>N/A</span>
                        )}
                    </TableCell>
                  </TableRow>
                ))}
              </tbody>
            </Table>
          </TableContainer>
        </Section>
      ) : (
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
