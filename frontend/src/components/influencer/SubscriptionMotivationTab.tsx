import React, { useState, useEffect } from 'react';
import {
  classificationService,
  ClassificationRequest,
  ClassificationStatus,
  ClassificationResult,
  IndividualReelClassificationResponse,
  AggregatedSummaryResponse,
  AggregatedSummary,
  ClassificationDistributionEntry,
  IndividualReelEntry
} from '../../services/influencer/classificationService';
import { influencerApi, UserData as ApiUserData } from '../../services/influencer/influencerApi';

type UserData = Pick<ApiUserData, 'username' | 'hasProfile' | 'hasPosts' | 'hasReels' | 'lastModified'>;

interface ParsedSubscriptionResult {
  username: string;
  classification_type: string;
  parsed_at: string;
  total_images: number;
  results: Array<{
    image_filename: string;
    motivation: string;
    evidence: string;
    classified_at: string;
    description: string;
    hashtags: string[];
  }>;
}

const normalizeDistribution = (
  distribution?: AggregatedSummary['classification_distribution'],
): ClassificationDistributionEntry[] => {
  if (!distribution) {
    return [];
  }

  if (Array.isArray(distribution)) {
    return distribution;
  }

  return Object.entries(distribution).map(([label, value]) => {
    const numericValue = typeof value === 'number' ? value : Number(value) || 0;
    return {
      label,
      count: numericValue,
      percentage: numericValue,
      average_confidence: 0,
    };
  });
};

const getTotalReelsFromSummary = (summary?: AggregatedSummary): number => {
  if (!summary?.statistics) {
    return 0;
  }

  return (
    summary.statistics.total_reels_processed ??
    summary.statistics.total_reels_considered ??
    0
  );
};

const formatConfidencePercentage = (confidence?: number | null): string | null => {
  if (confidence == null) {
    return null;
  }
  return `${Math.round(confidence * 100)}%`;
};

const SubscriptionMotivationTab: React.FC = () => {
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [users, setUsers] = useState<UserData[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [topSearch, setTopSearch] = useState('');
  const [subscriptionPrompt, setSubscriptionPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [status, setStatus] = useState<ClassificationStatus | null>(null);
  const [parsedSubscriptionResult, setParsedSubscriptionResult] = useState<ParsedSubscriptionResult | null>(null);
  const [motivationStats, setMotivationStats] = useState<Array<{motivation: string, count: number, percentage: number}>>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [showAllResults, setShowAllResults] = useState(false);
  const [selectedUsersForClassification, setSelectedUsersForClassification] = useState<string[]>([]);
  const [bulkClassifying, setBulkClassifying] = useState(false);
  const [bulkParsing, setBulkParsing] = useState(false);
  const [individualReelData, setIndividualReelData] = useState<IndividualReelClassificationResponse | null>(null);
  const [aggregatedSummary, setAggregatedSummary] = useState<AggregatedSummaryResponse | null>(null);
  const [showIndividualReels, setShowIndividualReels] = useState(false);

  const motivationSummary = aggregatedSummary?.aggregated_summaries?.subscription_motivation;
  const hasMotivationSummary = motivationSummary && !(motivationSummary as any).error;
  const motivationTotalReels = hasMotivationSummary ? getTotalReelsFromSummary(motivationSummary) : 0;
  const motivationDistribution = hasMotivationSummary
    ? normalizeDistribution(motivationSummary?.classification_distribution)
    : [];
  const motivationTimestamp = hasMotivationSummary
    ? motivationSummary?.processed_at || motivationSummary?.timestamp || null
    : null;
  const motivationReels: IndividualReelEntry[] = individualReelData?.reels ?? [];

  // 기본 프롬프트 설정
  useEffect(() => {
    setSubscriptionPrompt(`Instagram 이미지의 구독동기를 분석하여 분류해주세요.

분류 기준:
- 콘텐츠 품질: 고품질의 사진, 영상, 디자인 등
- 브랜드 신뢰도: 전문성, 일관성, 신뢰할 수 있는 브랜드 이미지
- 트렌드: 최신 유행, 인기 있는 스타일이나 콘텐츠
- 개인적 연결감: 공감대, 감정적 연결, 라이프스타일 공유
- 실용적 가치: 정보 제공, 팁, 가이드 등 유용한 콘텐츠
- 기타: 위 카테고리에 속하지 않는 특별한 이유

각 이미지에 대해 가장 적합한 구독동기와 구체적인 근거를 제공해주세요.`);
  }, []);

  // 사용자 목록 로드
  const loadUsers = async () => {
    try {
      setIsLoadingUsers(true);
      const { users: fetchedUsers } = await influencerApi.getUsers();
      setUsers((fetchedUsers || []).map((user) => ({
        username: user.username,
        hasProfile: user.hasProfile,
        hasPosts: user.hasPosts,
        hasReels: user.hasReels,
        lastModified: user.lastModified,
      })));
      console.log('로드된 사용자:', fetchedUsers);
    } catch (error) {
      console.error('사용자 목록 로드 실패:', error);
      setMessage({ type: 'error', text: '사용자 목록을 불러오는데 실패했습니다' });
    } finally {
      setIsLoadingUsers(false);
    }
  };

  // 컴포넌트 마운트 시 사용자 목록 로드
  useEffect(() => {
    loadUsers();
  }, []);

  // 사용자 변경 시 상태 및 결과 초기화
  useEffect(() => {
    if (selectedUser) {
      loadClassificationStatus();
      loadParsedResults();
      loadIndividualReelData();
      loadAggregatedSummary();
    } else {
      setStatus(null);
      setParsedSubscriptionResult(null);
      setMotivationStats([]);
      setShowAllResults(false);
      setIndividualReelData(null);
      setAggregatedSummary(null);
      setShowIndividualReels(false);
    }
  }, [selectedUser]);

  const loadClassificationStatus = async () => {
    if (!selectedUser) return;
    try {
      const statusData = await classificationService.getClassificationStatus(selectedUser);
      setStatus(statusData);
    } catch (error) {
      console.error('분류 상태 로드 실패:', error);
    }
  };

  const loadIndividualReelData = async () => {
    if (!selectedUser) return;
    try {
      const reelData = await classificationService.getIndividualReelClassifications(selectedUser);
      setIndividualReelData(reelData);
    } catch (error) {
      console.error('개별 릴스 데이터 로드 실패:', error);
      setIndividualReelData(null);
    }
  };

  const loadAggregatedSummary = async () => {
    if (!selectedUser) return;
    try {
      const summaryData = await classificationService.getAggregatedClassificationSummary(selectedUser);
      setAggregatedSummary(summaryData);
    } catch (error) {
      console.error('집계된 요약 데이터 로드 실패:', error);
      setAggregatedSummary(null);
    }
  };

  // 일괄 구독동기 분류 함수
  const bulkSubscriptionClassification = async () => {
    if (selectedUsersForClassification.length === 0) {
      setMessage({ type: 'error', text: '분류할 사용자를 선택해주세요' });
      return;
    }

    if (!subscriptionPrompt.trim()) {
      setMessage({ type: 'error', text: '프롬프트를 입력해주세요' });
      return;
    }

    try {
      setBulkClassifying(true);
      setMessage({ type: 'success', text: `${selectedUsersForClassification.length}명의 사용자 구독동기 분류를 시작합니다...` });
      let successCount = 0;
      let failCount = 0;

      for (const username of selectedUsersForClassification) {
        try {
          const request: ClassificationRequest = { username, prompt: subscriptionPrompt };
          await classificationService.startSubscriptionMotivationClassification(request);
          successCount++;
        } catch (error: any) {
          failCount++;
          console.error(`${username} 구독동기 분류 실패:`, error);
        }
      }

      if (successCount > 0) {
        setMessage({ type: 'success', text: `일괄 분류 완료! ${successCount}명 성공, ${failCount}명 실패` });
      } else {
        setMessage({ type: 'error', text: '모든 사용자의 구독동기 분류에 실패했습니다' });
      }

      setSelectedUsersForClassification([]);
    } catch (error) {
      console.error('일괄 분류 오류:', error);
      setMessage({ type: 'error', text: '일괄 분류 중 오류가 발생했습니다' });
    } finally {
      setBulkClassifying(false);
    }
  };

  // 일괄 구독동기 파싱 함수
  const bulkSubscriptionParsing = async () => {
    if (selectedUsersForClassification.length === 0) {
      setMessage({ type: 'error', text: '파싱할 사용자를 선택해주세요' });
      return;
    }

    try {
      setBulkParsing(true);
      setMessage({ type: 'success', text: `${selectedUsersForClassification.length}명의 사용자 구독동기 파싱을 시작합니다...` });
      let successCount = 0;
      let failCount = 0;

      for (const username of selectedUsersForClassification) {
        try {
          const request: ClassificationRequest = { username, prompt: '' };
          await classificationService.parseSubscriptionMotivationResults(request);
          successCount++;
        } catch (error: any) {
          failCount++;
          console.error(`${username} 구독동기 파싱 실패:`, error);
        }
      }

      if (successCount > 0) {
        setMessage({ type: 'success', text: `일괄 파싱 완료! ${successCount}명 성공, ${failCount}명 실패` });
      } else {
        setMessage({ type: 'error', text: '모든 사용자의 구독동기 파싱에 실패했습니다' });
      }

      setSelectedUsersForClassification([]);
    } catch (error) {
      console.error('일괄 파싱 오류:', error);
      setMessage({ type: 'error', text: '일괄 파싱 중 오류가 발생했습니다' });
    } finally {
      setBulkParsing(false);
    }
  };

  // 사용자 선택/해제 토글 함수
  const toggleUserSelection = (username: string) => {
    setSelectedUsersForClassification(prev => prev.includes(username) ? prev.filter(u => u !== username) : [...prev, username]);
  };

  // 전체 사용자 선택/해제 토글 함수
  const toggleAllUsers = () => {
    if (selectedUsersForClassification.length === (users || []).length) {
      setSelectedUsersForClassification([]);
    } else {
      setSelectedUsersForClassification((users || []).map(u => u.username));
    }
  };

  const handleSubscriptionClassification = async () => {
    if (!selectedUser || !subscriptionPrompt.trim()) {
      setMessage({ type: 'error', text: '사용자를 선택하고 프롬프트를 입력해주세요.' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      const request: ClassificationRequest = { username: selectedUser, prompt: subscriptionPrompt };
      const response = await classificationService.startSubscriptionMotivationClassification(request);
      setMessage({ type: 'success', text: response.message });
      setTimeout(() => { loadClassificationStatus(); }, 2000);
    } catch (error: any) {
      setMessage({ type: 'error', text: error.response?.data?.detail || '구독 동기 분류 시작에 실패했습니다.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleParseSubscriptionResults = async () => {
    if (!selectedUser) {
      setMessage({ type: 'error', text: '사용자를 선택해주세요.' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      const request: ClassificationRequest = { username: selectedUser, prompt: '' };
      const response = await classificationService.parseSubscriptionMotivationResults(request);
      setMessage({ type: 'success', text: response.message });
      setTimeout(() => { loadClassificationStatus(); loadParsedResults(); }, 2000);
    } catch (error: any) {
      setMessage({ type: 'error', text: error.response?.data?.detail || '구독 동기 분류 결과 파싱에 실패했습니다.' });
    } finally {
      setIsLoading(false);
    }
  };

  const refreshResults = async () => { await loadClassificationStatus(); };

  const loadParsedResults = async () => {
    if (!selectedUser) return;
    try {
      const response = await fetch(`http://localhost:8000/api/files/parsed-subscription-motivation/${selectedUser}`);
      if (response.ok) {
        const data = await response.json();
        setParsedSubscriptionResult(data);
        calculateMotivationStats(data.results);
        
        // 기존 파싱 결과에 description과 hashtags가 없는 경우 안내 메시지 표시
        if (data.results && data.results.length > 0) {
          const firstResult = data.results[0];
          if (!firstResult.hasOwnProperty('description') || !firstResult.hasOwnProperty('hashtags')) {
            setMessage({ 
              type: 'error', 
              text: '기존 파싱 결과에 상세설명과 해시태그 정보가 없습니다. "구독동기분류 결과 파싱" 버튼을 클릭하여 최신 정보로 다시 파싱해주세요.' 
            });
          }
        }
      } else {
        setParsedSubscriptionResult(null);
        setMotivationStats([]);
      }
    } catch (error) {
      console.error('파싱된 결과 로드 실패:', error);
      setParsedSubscriptionResult(null);
      setMotivationStats([]);
    }
  };

  const calculateMotivationStats = (results: ParsedSubscriptionResult['results']) => {
    const motivationCounts: { [key: string]: number } = {};
    const total = results.length;
    results.forEach(result => {
      const motivation = result.motivation || '알 수 없음';
      motivationCounts[motivation] = (motivationCounts[motivation] || 0) + 1;
    });
    const stats = Object.entries(motivationCounts)
      .map(([motivation, count]) => ({ motivation, count, percentage: Math.round((count / total) * 100) }))
      .sort((a, b) => b.count - a.count);
    setMotivationStats(stats);
  };

  // 사용자 데이터 상태 표시
  const getUserStatusText = (user: UserData) => {
    const status = [] as string[];
    if (user.hasProfile) status.push('프로필');
    if (user.hasPosts) status.push('게시물');
    if (user.hasReels) status.push('릴스');
    return status.length > 0 ? status.join(', ') : '데이터 없음';
  };

  const filteredUsers = (users || []).filter(u => u.username.toLowerCase().includes(userSearch.toLowerCase()));

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">구독 동기 AI 분류</h1>

      {message && (
        <div className={`mb-4 p-4 rounded-lg ${
          message.type === 'success' ? 'bg-green-100 border border-green-400 text-green-700' : 'bg-red-100 border border-red-400 text-red-700'
        }`}>
          {message.text}
        </div>
      )}

      {/* 개별 사용자 결과 확인 (상단) */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6 border border-gray-200">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">개별 사용자 결과 확인</h2>
        {/* 검색 입력 */}
        <div className="flex items-center gap-3 mb-3">
          <input
            type="text"
            value={topSearch}
            onChange={(e) => setTopSearch(e.target.value)}
            placeholder="@username 검색..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            onClick={loadUsers}
            disabled={isLoadingUsers}
            className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoadingUsers ? '로딩...' : '새로고침'}
          </button>
        </div>
        {/* 검색 결과 제안 리스트 */}
        <div className="max-h-40 overflow-auto border border-gray-200 rounded-lg divide-y">
          {(topSearch ? (users || []).filter(u => u.username.toLowerCase().includes(topSearch.toLowerCase())) : (users || []))
            .slice(0, 10)
            .map(u => (
              <button
                key={u.username}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 ${selectedUser === u.username ? 'bg-blue-50' : ''}`}
                onClick={() => setSelectedUser(u.username)}
              >
                @{u.username}
                <span className="ml-2 text-xs text-gray-500">{getUserStatusText(u)}</span>
              </button>
            ))}
          {users.length === 0 && (
            <div className="px-3 py-2 text-sm text-gray-500">사용자 목록이 없습니다</div>
          )}
        </div>
      </div>

      {/* 선택된 사용자 결과/통계 - 상단 바로 아래 */}
      {!selectedUser ? (
        <div className="text-center py-8 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border-2 border-dashed border-blue-300 mb-6">
          <div className="text-6xl mb-4">👤</div>
          <p className="text-gray-600">위의 검색에서 사용자를 선택하면 결과가 표시됩니다.</p>
        </div>
      ) : (
        <>
          {status?.subscription_motivation?.exists && (
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 mb-6">
              <h2 className="text-xl font-semibold mb-4 text-blue-800">📊 선택된 사용자 상태</h2>
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm text-green-700">📅 마지막 업데이트: {new Date(status.subscription_motivation.last_updated!).toLocaleString()}</p>
                <p className="text-sm text-green-700">📊 분류된 이미지: {status.subscription_motivation.total_images}개</p>
              </div>
            </div>
          )}

          <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-800">📋 구독 동기 분류 결과</h2>
              <button onClick={refreshResults} className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">🔄 새로고침</button>
            </div>
            {parsedSubscriptionResult ? (
              <div className="space-y-2">
                {(parsedSubscriptionResult.results || []).slice(0, 5).map((result, index) => (
                  <div key={index} className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                    <div className="flex gap-4">
                      <img src={`http://localhost:8000/static/uploads/users/${selectedUser}/images/${result.image_filename}`} alt={result.image_filename} className="w-20 h-20 object-cover rounded border border-gray-200 flex-shrink-0" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
                      <div className="flex-1 space-y-2">
                        <div className="flex items-start gap-2">
                          <span className="text-sm font-medium text-blue-600">구독동기:</span>
                          <span className="text-sm text-gray-800">{result.motivation}</span>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="text-sm font-medium text-gray-600">근거:</span>
                          <span className="text-sm text-gray-700">{result.evidence}</span>
                        </div>
                        {(result.description || result.description === '') && (
                          <div className="flex items-start gap-2">
                            <span className="text-sm font-medium text-gray-600">상세설명:</span>
                            <span className="text-sm text-gray-700 line-clamp-2">
                              {result.description || '상세설명 없음'}
                            </span>
                          </div>
                        )}
                        {(result.hashtags && result.hashtags.length > 0) && (
                          <div className="flex items-start gap-2">
                            <span className="text-sm font-medium text-gray-600">해시태그:</span>
                            <div className="flex flex-wrap gap-1">
                              {(result.hashtags || []).map((tag, tagIndex) => (
                                <span key={tagIndex} className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {parsedSubscriptionResult.results.length > 5 && (
                  <button onClick={() => setShowAllResults(!showAllResults)} className="w-full py-2 text-sm text-blue-600 hover:text-blue-800 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors">{showAllResults ? '접기' : `더 보기 (${parsedSubscriptionResult.results.length - 5}개)`}</button>
                )}
                {showAllResults && (parsedSubscriptionResult.results || []).slice(5).map((result, index) => (
                  <div key={index + 5} className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                    <div className="flex gap-4">
                      <img src={`http://localhost:8000/static/uploads/users/${selectedUser}/images/${result.image_filename}`} alt={result.image_filename} className="w-20 h-20 object-cover rounded border border-gray-200 flex-shrink-0" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
                      <div className="flex-1 space-y-2">
                        <div className="flex items-start gap-2">
                          <span className="text-sm font-medium text-blue-600">구독동기:</span>
                          <span className="text-sm text-gray-800">{result.motivation}</span>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="text-sm font-medium text-gray-600">근거:</span>
                          <span className="text-sm text-gray-700">{result.evidence}</span>
                        </div>
                        {(result.description || result.description === '') && (
                          <div className="flex items-start gap-2">
                            <span className="text-sm font-medium text-gray-600">상세설명:</span>
                            <span className="text-sm text-gray-700 line-clamp-2">
                              {result.description || '상세설명 없음'}
                            </span>
                          </div>
                        )}
                        {(result.hashtags && result.hashtags.length > 0) && (
                          <div className="flex items-start gap-2">
                            <span className="text-sm font-medium text-gray-600">해시태그:</span>
                            <div className="flex flex-wrap gap-1">
                              {(result.hashtags || []).map((tag, tagIndex) => (
                                <span key={tagIndex} className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500">아직 분류 결과가 없습니다.</div>
            )}
          </div>

          {status?.subscription_motivation?.exists && parsedSubscriptionResult && (
            <div className="bg-white rounded-lg shadow-md p-6 border border-purple-200 mb-6">
              <h3 className="text-lg font-semibold mb-3 text-purple-800">📊 파싱된 구독 동기 분류 결과 및 통계</h3>
              <div className="space-y-4">
                {(motivationStats || []).map((stat, index) => (
                  <div key={index} className="p-4 border border-purple-200 rounded-lg bg-purple-50">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-medium text-purple-800">{stat.motivation}</span>
                      <span className="text-sm text-purple-600">{stat.count}개 ({stat.percentage}%)</span>
                    </div>
                    <div className="w-full bg-purple-200 rounded-full h-2"><div className="bg-purple-600 h-2 rounded-full transition-all duration-300" style={{ width: `${stat.percentage}%` }}></div></div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 새로운 개별 릴스 기반 분류 결과 */}
          {hasMotivationSummary && motivationSummary && (
            <div className="bg-white rounded-lg shadow-md p-6 border border-indigo-200 mb-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-indigo-800">🔄 개별 릴스 기반 구독 동기 집계 결과</h3>
                <button 
                  onClick={() => { loadIndividualReelData(); loadAggregatedSummary(); }}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm"
                >
                  🔄 새로고침
                </button>
              </div>
              
              <div className="space-y-4">
                {/* 집계된 요약 정보 */}
                <div className="p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-sm font-medium text-indigo-700">주요 구독동기:</span>
                      <span className="ml-2 text-indigo-900">{motivationSummary.primary_classification || '-'}</span>
                      {motivationSummary.primary_percentage != null && (
                        <span className="ml-1 text-sm text-indigo-600">({motivationSummary.primary_percentage}%)</span>
                      )}
                    </div>
                    <div>
                      <span className="text-sm font-medium text-indigo-700">부차 구독동기:</span>
                      <span className="ml-2 text-indigo-900">{motivationSummary.secondary_classification || '-'}</span>
                      {motivationSummary.secondary_percentage != null && (
                        <span className="ml-1 text-sm text-indigo-600">({motivationSummary.secondary_percentage}%)</span>
                      )}
                    </div>
                    <div>
                      <span className="text-sm font-medium text-indigo-700">분석된 릴스:</span>
                      <span className="ml-2 text-indigo-900">{motivationTotalReels}개</span>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-indigo-700">분석 시간:</span>
                      <span className="ml-2 text-indigo-900">{motivationTimestamp ? new Date(motivationTimestamp).toLocaleString() : '정보 없음'}</span>
                    </div>
                  </div>
                </div>

                {/* 분류 분포 */}
                <div className="p-4 border border-indigo-200 rounded-lg">
                  <h4 className="font-medium text-indigo-800 mb-3">📈 구독동기 분포</h4>
                  <div className="space-y-2">
                    {motivationDistribution.length > 0 ? (
                      motivationDistribution.map((entry) => (
                        <div key={entry.label} className="flex justify-between items-center">
                          <span className="text-sm text-indigo-700">{entry.label}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-indigo-600">{entry.count}개 ({entry.percentage}%)</span>
                            <div className="w-20 h-2 bg-indigo-100 rounded-full">
                              <div
                                className="h-2 bg-indigo-500 rounded-full transition-all duration-300"
                                style={{ width: `${Math.min(entry.percentage, 100)}%` }}
                              ></div>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-indigo-600">분포 정보가 없습니다.</div>
                    )}
                  </div>
                </div>

                {/* 개별 릴스 보기 토글 */}
                {motivationReels.length > 0 && (
                  <div className="border-t border-indigo-200 pt-4">
                    <button 
                      onClick={() => setShowIndividualReels(!showIndividualReels)}
                      className="w-full py-2 text-sm text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded-lg hover:bg-indigo-50 transition-colors"
                    >
                      {showIndividualReels ? '개별 릴스 결과 숨기기' : `개별 릴스 결과 보기 (${motivationReels.length}개)`}
                    </button>
                    
                    {showIndividualReels && (
                      <div className="mt-4 space-y-3 max-h-96 overflow-y-auto">
                        {motivationReels.map((reel, index) => {
                          const detail = reel.subscription_motivation;
                          const confidenceLabel = formatConfidencePercentage(detail?.confidence ?? null);

                          return (
                            <div key={reel.reel_id} className="p-3 border border-gray-200 rounded-lg bg-gray-50">
                              <div className="flex gap-3">
                                {detail?.image_url ? (
                                  <img
                                    src={detail.image_url}
                                    alt={`릴스 ${index + 1}`}
                                    className="w-16 h-16 object-cover rounded border border-gray-200"
                                    onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                                  />
                                ) : (
                                  <div className="w-16 h-16 rounded border border-dashed border-gray-300 flex items-center justify-center text-xs text-gray-400">
                                    이미지 없음
                                  </div>
                                )}
                                <div className="flex-1 space-y-1">
                                  <div>
                                    <span className="text-sm font-medium text-indigo-600">구독동기:</span>
                                    <span className="ml-2 text-sm text-gray-800">{detail?.label || '분류 대기'}</span>
                                    {confidenceLabel && (
                                      <span className="ml-2 text-xs text-gray-500">({confidenceLabel})</span>
                                    )}
                                  </div>
                                  <div>
                                    <span className="text-sm font-medium text-gray-600">근거:</span>
                                    <span className="ml-2 text-sm text-gray-700">{detail?.reasoning || '설명 없음'}</span>
                                  </div>
                                  {detail?.error && (
                                    <div className="text-xs text-red-500">⚠️ {detail.error}</div>
                                  )}
                                  {reel.caption && (
                                    <div>
                                      <span className="text-sm font-medium text-gray-600">캡션:</span>
                                      <span className="ml-2 text-sm text-gray-700 line-clamp-2">{reel.caption}</span>
                                    </div>
                                  )}
                                  {detail?.processed_at && (
                                    <div className="text-xs text-gray-500">분류 시각: {new Date(detail.processed_at).toLocaleString()}</div>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* 프롬프트 입력 섹션 */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6 border border-gray-200">
        <h2 className="text-xl font-semibold mb-4 text-green-800">📝 구독동기 분류 프롬프트</h2>
        <textarea className="w-full p-3 border border-gray-300 rounded-lg mb-4 resize-none focus:ring-2 focus:ring-green-500 focus:border-transparent text-sm" rows={15} placeholder="구독동기 분류를 위한 프롬프트를 입력하세요..." value={subscriptionPrompt} onChange={(e) => setSubscriptionPrompt(e.target.value)} />
        <div className="text-sm text-gray-600 mb-4">💡 프롬프트 예시: "이 이미지에서 사용자가 해당 계정을 구독하게 된 동기를 분석하여 분류해주세요. 구독동기 유형: 콘텐츠 품질, 브랜드 신뢰도, 트렌드, 개인적 연결감, 실용적 가치 등"</div>
      </div>

      {/* 사용자 선택 섹션 */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6 border border-gray-200">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">👤 사용자 선택</h2>
        <div className="space-y-4">
          {/* 검색 및 전체 선택 */}
          <div className="flex items-center gap-3">
            <input type="text" value={userSearch} onChange={(e) => setUserSearch(e.target.value)} placeholder="사용자 검색..." className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
            <button onClick={toggleAllUsers} className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">{selectedUsersForClassification.length === users.length ? '전체 해제' : '전체 선택'}</button>
          </div>

          {/* 사용자 목록 테이블 */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-800">사용자 목록</h3>
              <div className="flex gap-2">
                <button onClick={bulkSubscriptionClassification} disabled={bulkClassifying || selectedUsersForClassification.length === 0} className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">{bulkClassifying ? '분류 중...' : `일괄 분류 (${selectedUsersForClassification.length}명)`}</button>
                <button onClick={bulkSubscriptionParsing} disabled={bulkParsing || selectedUsersForClassification.length === 0} className="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">{bulkParsing ? '파싱 중...' : `일괄 파싱 (${selectedUsersForClassification.length}명)`}</button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">선택</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">사용자명</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {(filteredUsers || []).map((user, index) => (
                    <tr key={user.username} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-4 py-2"><input type="checkbox" checked={selectedUsersForClassification.includes(user.username)} onChange={() => toggleUserSelection(user.username)} className="w-4 h-4 text-green-600 bg-gray-100 border-gray-300 rounded focus:ring-green-500 focus:ring-2" /></td>
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">@{user.username}</td>
                      <td className="px-4 py-2 text-sm text-gray-500">{getUserStatusText(user)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 개별 사용자 선택 섹션은 상단으로 이동 */}
        </div>
      </div>
    </div>
  );
};

export default SubscriptionMotivationTab;
