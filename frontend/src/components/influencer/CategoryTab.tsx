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

interface ParsedCategoryResult {
  username: string;
  classification_type: string;
  parsed_at: string;
  total_images: number;
  results: Array<{
    image_filename: string;
    category: string;
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

const CategoryTab: React.FC = () => {
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [users, setUsers] = useState<UserData[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [categoryPrompt, setCategoryPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [status, setStatus] = useState<ClassificationStatus | null>(null);
  const [categoryResult, setCategoryResult] = useState<ClassificationResult | null>(null);
  const [parsedCategoryResult, setParsedCategoryResult] = useState<ParsedCategoryResult | null>(null);
  const [categoryStats, setCategoryStats] = useState<Array<{category: string, count: number, percentage: number}>>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [showAllResults, setShowAllResults] = useState(false);
  const [selectedUsersForClassification, setSelectedUsersForClassification] = useState<string[]>([]);
  const [bulkClassifying, setBulkClassifying] = useState(false);
  const [bulkParsing, setBulkParsing] = useState(false);
  const [individualReelData, setIndividualReelData] = useState<IndividualReelClassificationResponse | null>(null);
  const [aggregatedSummary, setAggregatedSummary] = useState<AggregatedSummaryResponse | null>(null);
  const [showIndividualReels, setShowIndividualReels] = useState(false);
  const categorySummary = aggregatedSummary?.aggregated_summaries?.category;
  const hasCategorySummary = categorySummary && !(categorySummary as any).error;
  const categoryTotalReels = hasCategorySummary ? getTotalReelsFromSummary(categorySummary) : 0;
  const categoryDistribution = hasCategorySummary
    ? normalizeDistribution(categorySummary?.classification_distribution)
    : [];
  const categoryTimestamp = hasCategorySummary
    ? categorySummary?.processed_at || categorySummary?.timestamp || null
    : null;
  const categoryReels: IndividualReelEntry[] = individualReelData?.reels ?? [];

  // 기본 프롬프트 설정
  useEffect(() => {
    setCategoryPrompt(`Instagram 이미지의 카테고리를 분석하여 분류해주세요.

분류 기준:
- 패션/뷰티: 패션, 메이크업, 스타일링 관련
- 음식/요리: 음식, 요리, 카페 관련
- 여행/풍경: 여행, 자연, 건축물 관련
- 라이프스타일: 일상, 취미, 운동 관련
- 엔터테인먼트: 영화, 음악, 예술 관련
- 기타: 위 카테고리에 속하지 않는 내용

각 이미지에 대해 가장 적합한 카테고리와 구체적인 설명을 제공해주세요.`);
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
      loadCategoryResults();
      loadParsedResults();
      loadIndividualReelData();
      loadAggregatedSummary();
    } else {
      setStatus(null);
      setCategoryResult(null);
      setParsedCategoryResult(null);
      setCategoryStats([]);
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

  const loadCategoryResults = async () => {
    if (!selectedUser) return;
    
    try {
      // 카테고리 분류 결과 로드
      if (status?.category.exists) {
        const result = await classificationService.getCategoryResult(selectedUser);
        setCategoryResult(result);
      }
    } catch (error) {
      console.error('카테고리 분류 결과 로드 실패:', error);
    }
  };

  const loadParsedResults = async () => {
    if (!selectedUser) return;
    
    try {
      // 파싱된 결과 파일 읽기
      const response = await fetch(`http://localhost:8000/api/files/parsed-category/${selectedUser}`);
      
      if (response.ok) {
        const data = await response.json();
        setParsedCategoryResult(data);
        
        // 카테고리별 통계 계산
        calculateCategoryStats(data.results);
      } else {
        console.log('파싱된 결과 파일이 아직 없습니다.');
        setParsedCategoryResult(null);
        setCategoryStats([]);
      }
    } catch (error) {
      console.error('파싱된 결과 로드 실패:', error);
      setParsedCategoryResult(null);
      setCategoryStats([]);
    }
  };

  const calculateCategoryStats = (results: ParsedCategoryResult['results']) => {
    const categoryCounts: { [key: string]: number } = {};
    const total = results.length;
    
    // 각 카테고리별 개수 계산
    results.forEach(result => {
      const category = result.category || '알 수 없음';
      categoryCounts[category] = (categoryCounts[category] || 0) + 1;
    });
    
    // 비율 계산 및 정렬
    const stats = Object.entries(categoryCounts)
      .map(([category, count]) => ({
        category,
        count,
        percentage: Math.round((count / total) * 100)
      }))
      .sort((a, b) => b.count - a.count); // 개수 기준 내림차순 정렬
    
    setCategoryStats(stats);
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

  // 일괄 카테고리 분류 함수
  const bulkCategoryClassification = async () => {
    if (selectedUsersForClassification.length === 0) {
      setMessage({ type: 'error', text: '분류할 사용자를 선택해주세요' });
      return;
    }

    if (!categoryPrompt.trim()) {
      setMessage({ type: 'error', text: '프롬프트를 입력해주세요' });
      return;
    }

    try {
      setBulkClassifying(true);
      setMessage({ type: 'success', text: `${selectedUsersForClassification.length}명의 사용자 카테고리 분류를 시작합니다...` });
      
      let successCount = 0;
      let failCount = 0;

      for (const username of selectedUsersForClassification) {
        try {
          const request: ClassificationRequest = {
            username: username,
            prompt: categoryPrompt
          };

          await classificationService.startCategoryClassification(request);
          successCount++;
          console.log(`${username} 카테고리 분류 시작 완료`);
        } catch (error: any) {
          failCount++;
          console.error(`${username} 카테고리 분류 실패:`, error);
        }
      }

      // 결과 요약
      if (successCount > 0) {
        setMessage({ 
          type: 'success', 
          text: `일괄 분류 완료! ${successCount}명 성공, ${failCount}명 실패` 
        });
      } else {
        setMessage({ 
          type: 'error', 
          text: '모든 사용자의 카테고리 분류에 실패했습니다' 
        });
      }

      // 선택 초기화
      setSelectedUsersForClassification([]);
      
    } catch (error) {
      console.error('일괄 분류 오류:', error);
      setMessage({ 
        type: 'error', 
        text: '일괄 분류 중 오류가 발생했습니다' 
      });
    } finally {
      setBulkClassifying(false);
    }
  };

  // 일괄 카테고리 파싱 함수
  const bulkCategoryParsing = async () => {
    if (selectedUsersForClassification.length === 0) {
      setMessage({ type: 'error', text: '파싱할 사용자를 선택해주세요' });
      return;
    }

    try {
      setBulkParsing(true);
      setMessage({ type: 'success', text: `${selectedUsersForClassification.length}명의 사용자 카테고리 파싱을 시작합니다...` });
      
      let successCount = 0;
      let failCount = 0;

      for (const username of selectedUsersForClassification) {
        try {
          const request: ClassificationRequest = {
            username: username,
            prompt: '' // 파싱에는 프롬프트가 필요 없음
          };

          await classificationService.parseCategoryResults(request);
          successCount++;
          console.log(`${username} 카테고리 파싱 완료`);
        } catch (error: any) {
          failCount++;
          console.error(`${username} 카테고리 파싱 실패:`, error);
        }
      }

      // 결과 요약
      if (successCount > 0) {
        setMessage({ 
          type: 'success', 
          text: `일괄 파싱 완료! ${successCount}명 성공, ${failCount}명 실패` 
        });
      } else {
        setMessage({ 
          type: 'error', 
          text: '모든 사용자의 카테고리 파싱에 실패했습니다' 
        });
      }

      // 선택 초기화
      setSelectedUsersForClassification([]);
      
    } catch (error) {
      console.error('일괄 파싱 오류:', error);
      setMessage({ 
        type: 'error', 
        text: '일괄 파싱 중 오류가 발생했습니다' 
      });
    } finally {
      setBulkParsing(false);
    }
  };

  // 사용자 선택/해제 토글 함수
  const toggleUserSelection = (username: string) => {
    setSelectedUsersForClassification(prev => 
      prev.includes(username) 
        ? prev.filter(u => u !== username)
        : [...prev, username]
    );
  };

  // 전체 사용자 선택/해제 토글 함수
  const toggleAllUsers = () => {
    if (selectedUsersForClassification.length === (users || []).length) {
      setSelectedUsersForClassification([]);
    } else {
      setSelectedUsersForClassification((users || []).map(u => u.username));
    }
  };

  const handleCategoryClassification = async () => {
    if (!selectedUser || !categoryPrompt.trim()) {
      setMessage({ type: 'error', text: '사용자를 선택하고 프롬프트를 입력해주세요.' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      const request: ClassificationRequest = {
        username: selectedUser,
        prompt: categoryPrompt
      };

      const response = await classificationService.startCategoryClassification(request);
      setMessage({ type: 'success', text: response.message });
      
      // 상태 새로고침
      setTimeout(() => {
        loadClassificationStatus();
      }, 2000);
      
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || '카테고리 분류 시작에 실패했습니다.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleParseCategoryResults = async () => {
    if (!selectedUser) {
      setMessage({ type: 'error', text: '사용자를 선택해주세요.' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      const request: ClassificationRequest = {
        username: selectedUser,
        prompt: '' // 파싱에는 프롬프트가 필요 없음
      };

      const response = await classificationService.parseCategoryResults(request);
      setMessage({ type: 'success', text: response.message });
      
      // 상태 새로고침 및 결과 로드
      setTimeout(() => {
        loadClassificationStatus();
        loadCategoryResults();
        loadParsedResults();
      }, 2000);
      
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || '카테고리 분류 결과 파싱에 실패했습니다.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const refreshResults = async () => {
    await loadClassificationStatus();
    await loadCategoryResults();
  };

  // 사용자 데이터 상태 표시
  const getUserStatusText = (user: UserData) => {
    const status = [];
    if (user.hasProfile) status.push('프로필');
    if (user.hasPosts) status.push('게시물');
    if (user.hasReels) status.push('릴스');
    return status.length > 0 ? status.join(', ') : '데이터 없음';
  };

  const filteredUsers = (users || []).filter(u => u.username.toLowerCase().includes(userSearch.toLowerCase()));

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">
        카테고리 AI 분류
      </h1>

      {message && (
        <div className={`mb-4 p-4 rounded-lg ${
          message.type === 'success' 
            ? 'bg-green-100 border border-green-400 text-green-700' 
            : 'bg-red-100 border border-red-400 text-red-700'
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
            value={userSearch}
            onChange={(e) => setUserSearch(e.target.value)}
            placeholder="@username 검색..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
          />
          <button onClick={loadUsers} disabled={isLoadingUsers} className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">{isLoadingUsers ? '로딩...' : '새로고침'}</button>
        </div>
        {/* 검색 결과 제안 리스트 */}
        <div className="max-h-40 overflow-auto border border-gray-200 rounded-lg divide-y">
          {(userSearch ? (users || []).filter(u => u.username.toLowerCase().includes(userSearch.toLowerCase())) : (users || []))
            .slice(0, 10)
            .map(u => (
              <button key={u.username} className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 ${selectedUser === u.username ? 'bg-green-50' : ''}`} onClick={() => setSelectedUser(u.username)}>
                @{u.username}
                <span className="ml-2 text-xs text-gray-500">{getUserStatusText(u)}</span>
              </button>
            ))}
          {users.length === 0 && (<div className="px-3 py-2 text-sm text-gray-500">사용자 목록이 없습니다</div>)}
        </div>
      </div>

      {/* 선택된 사용자 결과/통계 - 상단 바로 아래 */}
      {!selectedUser ? (
        <div className="text-center py-8 bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg border-2 border-dashed border-green-300 mb-6">
          <div className="text-6xl mb-4">🏷️</div>
          <p className="text-gray-600">위의 검색에서 사용자를 선택하면 결과가 표시됩니다.</p>
        </div>
      ) : (
        <>
          {status?.category?.exists && (
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 mb-6">
              <h2 className="text-xl font-semibold mb-4 text-green-800">📊 선택된 사용자 상태</h2>
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm text-green-700">📅 마지막 업데이트: {new Date(status.category.last_updated!).toLocaleString()}</p>
                <p className="text-sm text-green-700">📊 분류된 이미지: {status.category.total_images}개</p>
              </div>
            </div>
          )}

          {status?.category?.exists && parsedCategoryResult && (
            <div className="bg-white rounded-lg shadow-md p-6 border border-purple-200 mb-6">
              <h3 className="text-lg font-semibold mb-3 text-purple-800">📊 카테고리 분류 결과 및 통계</h3>
              <div className="space-y-4">
                {categoryStats.map((stat, index) => (
                  <div key={index} className="p-4 border border-purple-200 rounded-lg bg-purple-50">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-medium text-purple-800">{stat.category}</span>
                      <span className="text-sm text-purple-600">{stat.count}개 ({stat.percentage}%)</span>
                    </div>
                    <div className="w-full bg-purple-200 rounded-full h-2"><div className="bg-purple-600 h-2 rounded-full transition-all duration-300" style={{ width: `${stat.percentage}%` }}></div></div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {parsedCategoryResult && (
            <div className="bg-white rounded-lg shadow-md p-6 border border-purple-200 mb-6">
              <h3 className="text-lg font-semibold mb-3 text-purple-800">🏷️ 카테고리 분류 결과</h3>
              <div className="space-y-2">
                {(parsedCategoryResult.results || []).slice(0, 5).map((result, index) => (
                  <div key={index} className="p-3 border border-gray-200 rounded-lg bg-gray-50">
                    <div className="flex items-center gap-3">
                      <img 
                        src={`http://localhost:8000/static/uploads/users/${selectedUser}/images/${result.image_filename}`}
                        alt={result.image_filename}
                        className="w-16 h-16 object-cover rounded border border-gray-200"
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).style.display = 'none';
                        }}
                      />
                      <div className="flex-1">
                        <p className="text-sm text-purple-600">
                          <strong>카테고리:</strong> {result.category}
                        </p>
                        <p className="text-sm text-gray-600">
                          <strong>근거:</strong> {result.evidence}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}

                {parsedCategoryResult.results.length > 5 && (
                  <button 
                    onClick={() => setShowAllResults(!showAllResults)}
                    className="w-full py-2 text-sm text-purple-600 hover:text-purple-800 border border-purple-200 rounded-lg hover:bg-purple-50 transition-colors"
                  >
                    {showAllResults ? '접기' : `더 보기 (${parsedCategoryResult.results.length - 5}개)`}
                  </button>
                )}

                {showAllResults && (parsedCategoryResult.results || []).slice(5).map((result, index) => (
                  <div key={index + 5} className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                    <div className="flex gap-4">
                      <img 
                        src={`http://localhost:8000/static/uploads/users/${selectedUser}/images/${result.image_filename}`}
                        alt={result.image_filename}
                        className="w-20 h-20 object-cover rounded border border-gray-200 flex-shrink-0"
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).style.display = 'none';
                        }}
                      />
                      <div className="flex-1 space-y-2">
                        <div className="flex items-start gap-2">
                          <span className="text-sm font-medium text-purple-600">카테고리:</span>
                          <span className="text-sm text-gray-800">{result.category}</span>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="text-sm font-medium text-gray-600">근거:</span>
                          <span className="text-sm text-gray-700">{result.evidence}</span>
                        </div>
                        {result.description && (
                          <div className="flex items-start gap-2">
                            <span className="text-sm font-medium text-gray-600">상세설명:</span>
                            <span className="text-sm text-gray-700 line-clamp-2">{result.description}</span>
                          </div>
                        )}
                        {result.hashtags && result.hashtags.length > 0 && (
                          <div className="flex items-start gap-2">
                            <span className="text-sm font-medium text-gray-600">해시태그:</span>
                            <div className="flex flex-wrap gap-1">
                              {(result.hashtags || []).map((tag, tagIndex) => (
                                <span key={tagIndex} className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
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
            </div>
          )}

          {/* 새로운 개별 릴스 기반 카테고리 분류 결과 */}
          {hasCategorySummary && categorySummary && (
            <div className="bg-white rounded-lg shadow-md p-6 border border-teal-200 mb-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-teal-800">🔄 개별 릴스 기반 카테고리 집계 결과</h3>
                <button 
                  onClick={() => { loadIndividualReelData(); loadAggregatedSummary(); }}
                  className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors text-sm"
                >
                  🔄 새로고침
                </button>
              </div>
              
              <div className="space-y-4">
                {/* 집계된 요약 정보 */}
                <div className="p-4 bg-teal-50 border border-teal-200 rounded-lg">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-sm font-medium text-teal-700">주요 카테고리:</span>
                      <span className="ml-2 text-teal-900">{categorySummary.primary_classification || '-'}</span>
                      {categorySummary.primary_percentage != null && (
                        <span className="ml-1 text-sm text-teal-600">({categorySummary.primary_percentage}%)</span>
                      )}
                    </div>
                    <div>
                      <span className="text-sm font-medium text-teal-700">부차 카테고리:</span>
                      <span className="ml-2 text-teal-900">{categorySummary.secondary_classification || '-'}</span>
                      {categorySummary.secondary_percentage != null && (
                        <span className="ml-1 text-sm text-teal-600">({categorySummary.secondary_percentage}%)</span>
                      )}
                    </div>
                    <div>
                      <span className="text-sm font-medium text-teal-700">분석된 릴스:</span>
                      <span className="ml-2 text-teal-900">{categoryTotalReels}개</span>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-teal-700">분석 시간:</span>
                      <span className="ml-2 text-teal-900">{categoryTimestamp ? new Date(categoryTimestamp).toLocaleString() : '정보 없음'}</span>
                    </div>
                  </div>
                </div>

                {/* 분류 분포 */}
                <div className="p-4 border border-teal-200 rounded-lg">
                  <h4 className="font-medium text-teal-800 mb-3">📈 카테고리 분포</h4>
                  <div className="space-y-2">
                    {categoryDistribution.length > 0 ? (
                      categoryDistribution.map((entry) => (
                        <div key={entry.label} className="flex justify-between items-center">
                          <span className="text-sm text-teal-700">{entry.label}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-teal-600">{entry.count}개 ({entry.percentage}%)</span>
                            <div className="w-20 h-2 bg-teal-100 rounded-full">
                              <div
                                className="h-2 bg-teal-500 rounded-full transition-all duration-300"
                                style={{ width: `${Math.min(entry.percentage, 100)}%` }}
                              ></div>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-teal-600">분포 정보가 없습니다.</div>
                    )}
                  </div>
                </div>

                {/* 개별 릴스 보기 토글 */}
                {categoryReels.length > 0 && (
                  <div className="border-t border-teal-200 pt-4">
                    <button 
                      onClick={() => setShowIndividualReels(!showIndividualReels)}
                      className="w-full py-2 text-sm text-teal-600 hover:text-teal-800 border border-teal-200 rounded-lg hover:bg-teal-50 transition-colors"
                    >
                      {showIndividualReels ? '개별 릴스 결과 숨기기' : `개별 릴스 결과 보기 (${categoryReels.length}개)`}
                    </button>
                    
                    {showIndividualReels && (
                      <div className="mt-4 space-y-3 max-h-96 overflow-y-auto">
                        {categoryReels.map((reel, index) => {
                          const detail = reel.category;
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
                                    <span className="text-sm font-medium text-teal-600">카테고리:</span>
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
        <h2 className="text-xl font-semibold mb-4 text-green-800">
          📝 카테고리 분류 프롬프트
        </h2>
        
        <textarea
          className="w-full p-3 border border-gray-300 rounded-lg mb-4 resize-none focus:ring-2 focus:ring-green-500 focus:border-transparent text-sm"
          rows={15}
          placeholder="카테고리 분류를 위한 프롬프트를 입력하세요..."
          value={categoryPrompt}
          onChange={(e) => setCategoryPrompt(e.target.value)}
        />
        
        <div className="text-sm text-gray-600 mb-4">
          💡 프롬프트 예시: "Instagram 이미지의 카테고리를 분석하여 분류해주세요. 
          분류 기준: 패션/뷰티, 음식/요리, 여행/풍경, 라이프스타일, 엔터테인먼트, 기타"
        </div>
      </div>

      {/* 사용자 선택 섹션 */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6 border border-gray-200">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">
          👤 사용자 선택
        </h2>
        
        <div className="space-y-4">
          {/* 검색 및 전체 선택 */}
          <div className="flex items-center gap-3">
            <input type="text" value={userSearch} onChange={(e) => setUserSearch(e.target.value)} placeholder="사용자 검색..." className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent" />
            <button onClick={toggleAllUsers} className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">{selectedUsersForClassification.length === users.length ? '전체 해제' : '전체 선택'}</button>
          </div>
          {/* 사용자 목록 테이블 */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-800">사용자 목록</h3>
              <div className="flex gap-2">
                <button
                  onClick={toggleAllUsers}
                  className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  {selectedUsersForClassification.length === users.length ? '전체 해제' : '전체 선택'}
                </button>
                                 <button
                   onClick={bulkCategoryClassification}
                   disabled={bulkClassifying || selectedUsersForClassification.length === 0}
                   className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                 >
                   {bulkClassifying ? '분류 중...' : `일괄 분류 (${selectedUsersForClassification.length}명)`}
                 </button>
                 <button
                   onClick={bulkCategoryParsing}
                   disabled={bulkParsing || selectedUsersForClassification.length === 0}
                   className="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                 >
                   {bulkParsing ? '파싱 중...' : `일괄 파싱 (${selectedUsersForClassification.length}명)`}
                 </button>
              </div>
            </div>
            
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      선택
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      사용자명
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      상태
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {(filteredUsers || []).map((user, index) => (
                    <tr key={user.username} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-4 py-2">
                        <input
                          type="checkbox"
                          checked={selectedUsersForClassification.includes(user.username)}
                          onChange={() => toggleUserSelection(user.username)}
                          className="w-4 h-4 text-green-600 bg-gray-100 border-gray-300 rounded focus:ring-green-500 focus:ring-2"
                        />
                      </td>
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">
                        @{user.username}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-500">
                        {getUserStatusText(user)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 개별 사용자 선택 섹션은 상단으로 이동 */}

          {/* 선택된 사용자 정보 */}
          {selectedUser && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-600 rounded-full flex items-center justify-center text-white font-bold text-lg">
                  {selectedUser.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h3 className="font-semibold text-green-900">
                    선택된 사용자: @{selectedUser}
                  </h3>
                  <p className="text-sm text-green-700">
                    이 사용자의 이미지들을 AI로 분석하여 카테고리를 분류합니다
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 사용자 목록 상태 */}
          <div className="text-sm text-gray-600">
            {isLoadingUsers ? (
              <span className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                사용자 목록을 불러오는 중...
              </span>
            ) : users.length > 0 ? (
              <span>총 {users.length}명의 사용자를 찾았습니다</span>
            ) : (
              <span className="text-red-600">사용자를 찾을 수 없습니다. 새로고침을 시도해보세요.</span>
            )}
          </div>
        </div>
      </div>

      {!selectedUser ? (
        <div className="text-center py-16 bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg border-2 border-dashed border-green-300">
          <div className="text-8xl mb-6">🏷️</div>
          <h3 className="text-2xl font-semibold text-gray-700 mb-3">
            사용자를 선택해주세요
          </h3>
          <p className="text-gray-600 mb-4 max-w-md mx-auto">
            위의 드롭다운에서 분류할 Instagram 사용자를 선택하면<br />
            AI 카테고리 분류 결과를 확인할 수 있습니다.
          </p>
          <div className="text-sm text-gray-500">
            💡 일괄 분류 및 파싱은 위의 사용자 선택 테이블에서 진행하세요
          </div>
        </div>
      ) : (
        <>
          {/* 선택된 사용자 상태 정보 */}
          {status?.category.exists && (
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 mb-6">
              <h2 className="text-xl font-semibold mb-4 text-green-800">
                📊 선택된 사용자 상태
              </h2>
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm text-green-700">
                  📅 마지막 업데이트: {new Date(status.category.last_updated!).toLocaleString()}
                </p>
                                <p className="text-sm text-green-700">
                  📊 분류된 이미지: {status.category.total_images}개
                </p>
              </div>
            </div>
          )}

          {/* 카테고리 분류 결과 및 통계 */}
          {status?.category.exists && (
            <div className="mt-8">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold text-purple-800">
                  📊 카테고리 분류 결과 및 통계
                </h2>
                <button 
                  onClick={loadParsedResults} 
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                >
                  🔄 결과 새로고침
                </button>
              </div>

              {parsedCategoryResult ? (
                <div className="grid grid-cols-1 gap-6">
                  {/* 카테고리별 통계 */}
                  <div className="bg-white rounded-lg shadow-md p-6 border border-purple-200">
                    <h3 className="text-lg font-semibold mb-3 text-purple-800">
                      📊 카테고리별 통계
                    </h3>
                    
                    <div className="space-y-4">
                      {(categoryStats || []).map((stat, index) => (
                        <div key={index} className="p-4 border border-purple-200 rounded-lg bg-purple-50">
                          <div className="flex justify-between items-center mb-2">
                            <span className="font-medium text-purple-800">{stat.category}</span>
                            <span className="text-sm text-purple-600">{stat.count}개 ({stat.percentage}%)</span>
                          </div>
                          <div className="w-full bg-purple-200 rounded-full h-2">
                            <div 
                              className="bg-purple-600 h-2 rounded-full transition-all duration-300" 
                              style={{ width: `${stat.percentage}%` }}
                            ></div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* 전체 요약 */}
                    <div className="mt-6 p-4 bg-purple-100 border border-purple-300 rounded-lg">
                      <h4 className="font-semibold text-purple-800 mb-2">📋 전체 요약</h4>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-purple-700">파싱 시간:</span>
                          <span className="ml-2 font-medium">{new Date(parsedCategoryResult.parsed_at).toLocaleString()}</span>
                        </div>
                        <div>
                          <span className="text-purple-700">총 이미지:</span>
                          <span className="ml-2 font-medium">{parsedCategoryResult.total_images}개</span>
                        </div>
                        <div>
                          <span className="text-purple-700">고유 카테고리:</span>
                          <span className="ml-2 font-medium">{categoryStats.length}개</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 파싱된 결과 상세 */}
                  <div className="bg-white rounded-lg shadow-md p-6 border border-purple-200">
                    <h3 className="text-lg font-semibold mb-3 text-purple-800">
                      🏷️ 카테고리 분류 결과
                    </h3>
                    
                    <div className="space-y-2">
                      {(parsedCategoryResult.results || []).slice(0, 5).map((result, index) => (
                        <div key={index} className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                          <div className="flex gap-4">
                            <img 
                              src={`http://localhost:8000/static/uploads/users/${selectedUser}/images/${result.image_filename}`}
                              alt={result.image_filename}
                              className="w-20 h-20 object-cover rounded border border-gray-200 flex-shrink-0"
                              onError={(e) => {
                                (e.currentTarget as HTMLImageElement).style.display = 'none';
                              }}
                            />
                            <div className="flex-1 space-y-2">
                              <div className="flex items-start gap-2">
                                <span className="text-sm font-medium text-purple-600">카테고리:</span>
                                <span className="text-sm text-gray-800">{result.category}</span>
                              </div>
                              <div className="flex items-start gap-2">
                                <span className="text-sm font-medium text-gray-600">근거:</span>
                                <span className="text-sm text-gray-700">{result.evidence}</span>
                              </div>
                              {result.description && (
                                <div className="flex items-start gap-2">
                                  <span className="text-sm font-medium text-gray-600">상세설명:</span>
                                  <span className="text-sm text-gray-700 line-clamp-2">{result.description}</span>
                                </div>
                              )}
                              {result.hashtags && result.hashtags.length > 0 && (
                                <div className="flex items-start gap-2">
                                  <span className="text-sm font-medium text-gray-600">해시태그:</span>
                                  <div className="flex flex-wrap gap-1">
                                    {(result.hashtags || []).map((tag, tagIndex) => (
                                      <span key={tagIndex} className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
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
                      
                      {/* 더 보기 버튼 */}
                      {parsedCategoryResult.results.length > 5 && (
                        <button 
                          onClick={() => setShowAllResults(!showAllResults)}
                          className="w-full py-2 text-sm text-purple-600 hover:text-purple-800 border border-purple-200 rounded-lg hover:bg-purple-50 transition-colors"
                        >
                          {showAllResults ? '접기' : `더 보기 (${parsedCategoryResult.results.length - 5}개)`}
                        </button>
                      )}
                      
                      {/* 추가 결과들 */}
                      {showAllResults && (parsedCategoryResult.results || []).slice(5).map((result, index) => (
                        <div key={index + 5} className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                          <div className="flex gap-4">
                            <img 
                              src={`http://localhost:8000/static/uploads/users/${selectedUser}/images/${result.image_filename}`}
                              alt={result.image_filename}
                              className="w-20 h-20 object-cover rounded border border-gray-200 flex-shrink-0"
                              onError={(e) => {
                                (e.currentTarget as HTMLImageElement).style.display = 'none';
                              }}
                            />
                            <div className="flex-1 space-y-2">
                              <div className="flex items-start gap-2">
                                <span className="text-sm font-medium text-purple-600">카테고리:</span>
                                <span className="text-sm text-gray-800">{result.category}</span>
                              </div>
                              <div className="flex items-start gap-2">
                                <span className="text-sm font-medium text-gray-600">근거:</span>
                                <span className="text-sm text-gray-700">{result.evidence}</span>
                              </div>
                              {result.description && (
                                <div className="flex items-start gap-2">
                                  <span className="text-sm font-medium text-gray-600">상세설명:</span>
                                  <span className="text-sm text-gray-700 line-clamp-2">{result.description}</span>
                                </div>
                              )}
                              {result.hashtags && result.hashtags.length > 0 && (
                                <div className="flex items-start gap-2">
                                  <span className="text-sm font-medium text-gray-600">해시태그:</span>
                                  <div className="flex flex-wrap gap-1">
                                    {(result.hashtags || []).map((tag, tagIndex) => (
                                      <span key={tagIndex} className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
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
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 bg-purple-50 rounded-lg border border-purple-200">
                  <div className="text-4xl mb-2">📊</div>
                  <p className="text-purple-600 mb-2">
                    카테고리 분류 결과를 불러오는 중입니다...
                  </p>
                  <button 
                    onClick={loadParsedResults}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    결과 로드
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}
      {/* 하단 중복 결과 블록 제거 */}
    </div>
  );
};

export default CategoryTab;
