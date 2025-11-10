import React, { useEffect, useState, useMemo } from 'react';
import styled from 'styled-components';
import { adminApi } from '../services/api';
import { formatDateTimeKST, getTodayKST } from '../utils/dateUtils';
import { RefreshCw } from 'lucide-react';

// 날짜를 YYYY-mm-dd 형식으로 포맷팅
const formatDateOnly = (dateString?: string): string => {
  if (!dateString) return '-';
  try {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  } catch {
    return '-';
  }
};


interface CollectionJob {
  id: number;
  campaign_id: number;
  reel_url: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  user_posted?: string;
  video_play_count?: number;
  likes_count?: number;
  comments_count?: number;
  thumbnail_url?: string;
  s3_thumbnail_url?: string;
  date_posted?: string;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

interface CampaignCollectionStatus {
  campaign_id: number;
  campaign_name?: string;
  campaign_type?: string;
  product?: string;
  start_date?: string;
  end_date?: string;
  total_jobs: number;
  status_counts: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
  jobs: CollectionJob[];
}

interface CollectionStatusResponse {
  campaigns: CampaignCollectionStatus[];
  summary: {
    total_campaigns: number;
    total_jobs: number;
    completed_jobs: number;
    failed_jobs: number;
    pending_jobs: number;
    processing_jobs: number;
  };
}

const Container = styled.div`
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem;
`;

const Title = styled.h1`
  color: #2c3e50;
  margin-bottom: 2rem;
`;

const FilterSection = styled.div`
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
`;

const FilterGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 1rem;
  align-items: end;
`;

const FilterGroup = styled.div`
  display: flex;
  flex-direction: column;
`;

const FilterLabel = styled.label`
  font-size: 0.9rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.5rem;
`;

const FilterSelect = styled.select`
  padding: 0.5rem;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  font-size: 0.9rem;
  
  &:focus {
    outline: none;
    border-color: #3498db;
  }
`;

const SummaryGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
`;

const SummaryCard = styled.div`
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  text-align: center;
`;

const SummaryValue = styled.div`
  font-size: 1.8rem;
  font-weight: bold;
  color: #3498db;
  margin-bottom: 0.5rem;
`;

const SummaryLabel = styled.div`
  color: #7f8c8d;
  font-size: 0.9rem;
`;

const CampaignSection = styled.div`
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 1.5rem;
`;

const CampaignHeader = styled.div`
  display: flex;
  justify-content: between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #dee2e6;
`;

const CampaignTitle = styled.h3`
  color: #2c3e50;
  margin: 0;
  flex: 1;
`;

const StatusBadge = styled.span<{ status: string }>`
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.8rem;
  font-weight: 600;
  background-color: ${props => {
    switch (props.status) {
      case 'completed': return '#d4edda';
      case 'failed': return '#f8d7da';
      case 'processing': return '#fff3cd';
      case 'pending': return '#d1ecf1';
      default: return '#e2e3e5';
    }
  }};
  color: ${props => {
    switch (props.status) {
      case 'completed': return '#155724';
      case 'failed': return '#721c24';
      case 'processing': return '#856404';
      case 'pending': return '#0c5460';
      default: return '#6c757d';
    }
  }};
`;

const StatusGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1rem;
`;

const StatusCard = styled.div`
  text-align: center;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
`;

const JobsTable = styled.table`
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
`;

const TableCell = styled.td`
  padding: 0.75rem;
  border-bottom: 1px solid #dee2e6;
  font-size: 0.9rem;
`;

const Loading = styled.div`
  text-align: center;
  padding: 2rem;
  color: #7f8c8d;
`;

const ThumbnailImage = styled.img`
  width: 50px;
  height: 50px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #dee2e6;
`;

const ThumbnailPlaceholder = styled.div`
  width: 50px;
  height: 50px;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6c757d;
  font-size: 0.7rem;
`;

const RefreshButton = styled.button`
  background: #3498db;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 1rem;

  &:hover {
    background: #2980b9;
  }

  &:disabled {
    background: #bdc3c7;
    cursor: not-allowed;
  }
`;

const ProcessButton = styled.button`
  background: #27ae60;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 0.5rem;

  &:hover {
    background: #229954;
  }

  &:disabled {
    background: #bdc3c7;
    cursor: not-allowed;
  }
`;

const CancelButton = styled.button`
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 0.5rem;

  &:hover {
    background: #c0392b;
  }

  &:disabled {
    background: #bdc3c7;
    cursor: not-allowed;
  }
`;

const CampaignCollectionStatus: React.FC = () => {
  const [data, setData] = useState<CollectionStatusResponse | null>(null);
  const [filteredData, setFilteredData] = useState<CollectionStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [stoppingWorker, setStoppingWorker] = useState(false);
  const [cancellingAll, setCancellingAll] = useState(false);
  const [deletingPending, setDeletingPending] = useState(false);
  const [deletingFailed, setDeletingFailed] = useState(false);
  const [deletingCompleted, setDeletingCompleted] = useState(false);
  const [retryingReelJobs, setRetryingReelJobs] = useState(false);
  const [retryingCollectionJobs, setRetryingCollectionJobs] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCampaign, setSelectedCampaign] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [controlsExpanded, setControlsExpanded] = useState(false);
  const [checkingToday, setCheckingToday] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [todayDataInfo, setTodayDataInfo] = useState<{ has_today_data: boolean; today_count: number; today_date: string } | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    // 캠페인이 선택되면 오늘 날짜 데이터 확인
    if (selectedCampaign) {
      checkTodayData();
    } else {
      setTodayDataInfo(null);
    }
  }, [selectedCampaign]);

  useEffect(() => {
    if (!data) return;
    
    // 캠페인이 선택되지 않은 경우 빈 결과 반환
    if (!selectedCampaign) {
      setFilteredData({
        campaigns: [],
        summary: {
          total_campaigns: 0,
          total_jobs: 0,
          completed_jobs: 0,
          failed_jobs: 0,
          pending_jobs: 0,
          processing_jobs: 0
        }
      });
      return;
    }
    
    let filtered = { ...data };
    
    // 캠페인별 필터링
    const campaignId = parseInt(selectedCampaign);
    filtered.campaigns = data.campaigns.filter(c => c.campaign_id === campaignId);
    
    // 상태별 필터링
    if (selectedStatus !== 'all') {
      filtered.campaigns = filtered.campaigns.map(campaign => ({
        ...campaign,
        jobs: campaign.jobs.filter(job => job.status === selectedStatus)
      })).filter(campaign => campaign.jobs.length > 0);
    }
    
    // 요약 정보 재계산
    const summary = {
      total_campaigns: filtered.campaigns.length,
      total_jobs: filtered.campaigns.reduce((sum, c) => sum + c.jobs.length, 0),
      completed_jobs: filtered.campaigns.reduce((sum, c) => sum + c.jobs.filter(j => j.status === 'completed').length, 0),
      failed_jobs: filtered.campaigns.reduce((sum, c) => sum + c.jobs.filter(j => j.status === 'failed').length, 0),
      pending_jobs: filtered.campaigns.reduce((sum, c) => sum + c.jobs.filter(j => j.status === 'pending').length, 0),
      processing_jobs: filtered.campaigns.reduce((sum, c) => sum + c.jobs.filter(j => j.status === 'processing').length, 0)
    };
    
    filtered.summary = summary;
    setFilteredData(filtered);
  }, [data, selectedCampaign, selectedStatus]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await adminApi.getCampaignCollectionStatus();
      setData(response);
      setError(null);
    } catch (err) {
      setError('수집 현황 데이터를 불러오는데 실패했습니다.');
      console.error('Error fetching collection status:', err);
    } finally {
      setLoading(false);
    }
  };

  const processJobs = async () => {
    try {
      setProcessing(true);
      await adminApi.processReelCollectionJobs();
      // 처리 후 데이터 새로고침
      await fetchData();
    } catch (err) {
      setError('작업 처리 중 오류가 발생했습니다.');
      console.error('Error processing jobs:', err);
    } finally {
      setProcessing(false);
    }
  };

  const retryFailedJobs = async () => {
    try {
      setRetrying(true);
      const campaignId = selectedCampaign ? parseInt(selectedCampaign) : undefined;
      await adminApi.retryFailedReelJobs(campaignId);
      // 재시도 후 데이터 새로고침
      await fetchData();
    } catch (err) {
      setError('실패한 작업 재시도 중 오류가 발생했습니다.');
      console.error('Error retrying failed jobs:', err);
    } finally {
      setRetrying(false);
    }
  };

  const cancelProcessingJobs = async () => {
    try {
      setCancelling(true);
      const campaignId = selectedCampaign ? parseInt(selectedCampaign) : undefined;
      await adminApi.cancelProcessingReelJobs(campaignId);
      // 취소 후 데이터 새로고침
      await fetchData();
    } catch (err) {
      setError('처리 중인 작업 취소 중 오류가 발생했습니다.');
      console.error('Error cancelling processing jobs:', err);
    } finally {
      setCancelling(false);
    }
  };

  const stopCollectionWorker = async () => {
    try {
      setStoppingWorker(true);
      await adminApi.stopCollectionWorker();
      // 워커 중지 후 데이터 새로고침
      await fetchData();
    } catch (err) {
      setError('수집 워커 중지 중 오류가 발생했습니다.');
      console.error('Error stopping collection worker:', err);
    } finally {
      setStoppingWorker(false);
    }
  };

  const cancelAllProcessingJobs = async () => {
    if (!window.confirm('모든 처리 중인 작업을 취소하고 워커를 중지하시겠습니까?')) {
      return;
    }
    
    try {
      setCancellingAll(true);
      await adminApi.cancelProcessingJobs();
      // 모든 작업 취소 후 데이터 새로고침
      await fetchData();
    } catch (err) {
      setError('모든 처리 중인 작업 취소 중 오류가 발생했습니다.');
      console.error('Error cancelling all processing jobs:', err);
    } finally {
      setCancellingAll(false);
    }
  };

  const deletePendingJobs = async () => {
    if (!window.confirm('모든 대기 중인 작업을 삭제하시겠습니까?')) {
      return;
    }
    
    try {
      setDeletingPending(true);
      const campaignId = selectedCampaign ? parseInt(selectedCampaign) : undefined;
      await adminApi.deletePendingJobs(campaignId);
      // 삭제 후 데이터 새로고침
      await fetchData();
    } catch (err) {
      setError('대기 중인 작업 삭제 중 오류가 발생했습니다.');
      console.error('Error deleting pending jobs:', err);
    } finally {
      setDeletingPending(false);
    }
  };

  const deleteFailedJobs = async () => {
    if (!window.confirm('모든 실패한 작업을 삭제하시겠습니까?')) {
      return;
    }
    
    try {
      setDeletingFailed(true);
      const campaignId = selectedCampaign ? parseInt(selectedCampaign) : undefined;
      await adminApi.deleteFailedJobs(campaignId);
      // 삭제 후 데이터 새로고침
      await fetchData();
    } catch (err) {
      setError('실패한 작업 삭제 중 오류가 발생했습니다.');
      console.error('Error deleting failed jobs:', err);
    } finally {
      setDeletingFailed(false);
    }
  };

  const deleteCompletedJobs = async () => {
    if (!window.confirm('모든 완료된 작업을 삭제하시겠습니까?')) {
      return;
    }
    
    try {
      setDeletingCompleted(true);
      const campaignId = selectedCampaign ? parseInt(selectedCampaign) : undefined;
      await adminApi.deleteCompletedJobs(campaignId);
      // 삭제 후 데이터 새로고침
      await fetchData();
    } catch (err) {
      setError('완료된 작업 삭제 중 오류가 발생했습니다.');
      console.error('Error deleting completed jobs:', err);
    } finally {
      setDeletingCompleted(false);
    }
  };

  const retryFailedReelJobs = async () => {
    if (!window.confirm('실패한 릴스 수집 작업들을 재시도하시겠습니까?')) {
      return;
    }
    
    try {
      setRetryingReelJobs(true);
      const campaignId = selectedCampaign ? parseInt(selectedCampaign) : undefined;
      await adminApi.retryFailedReelJobs(campaignId);
      // 재시도 후 데이터 새로고침
      await fetchData();
    } catch (err) {
      setError('실패한 릴스 작업 재시도 중 오류가 발생했습니다.');
      console.error('Error retrying failed reel jobs:', err);
    } finally {
      setRetryingReelJobs(false);
    }
  };

  const retryFailedCollectionJobs = async () => {
    if (!window.confirm('실패한 인플루언서 분석 작업들을 재시도하시겠습니까?')) {
      return;
    }
    
    try {
      setRetryingCollectionJobs(true);
      await adminApi.retryFailedCollectionJobs();
      // 재시도 후 데이터 새로고침
      await fetchData();
    } catch (err) {
      setError('실패한 인플루언서 분석 작업 재시도 중 오류가 발생했습니다.');
      console.error('Error retrying failed collection jobs:', err);
    } finally {
      setRetryingCollectionJobs(false);
    }
  };

  const formatUrl = (url: string) => {
    if (url.length > 50) {
      return url.substring(0, 50) + '...';
    }
    return url;
  };

  const checkTodayData = async () => {
    if (!selectedCampaign) return;
    
    try {
      setCheckingToday(true);
      const campaignId = parseInt(selectedCampaign);
      const result = await adminApi.checkTodayCollection(campaignId);
      setTodayDataInfo(result);
    } catch (err) {
      console.error('Error checking today data:', err);
      setTodayDataInfo(null);
    } finally {
      setCheckingToday(false);
    }
  };

  const handleImmediateCollection = async () => {
    if (!selectedCampaign) {
      alert('캠페인을 선택해주세요.');
      return;
    }

    try {
      setCollecting(true);
      const campaignId = parseInt(selectedCampaign);
      const result = await adminApi.immediateCollection(campaignId);
      
      if (result.skipped) {
        alert(result.message);
      } else {
        // 즉시 수집 시작 메시지
        alert(result.message + '\n\n수집 작업이 큐에 추가되었습니다. 아래 표에서 작업 상태를 확인할 수 있습니다.');
        
        // 수집 후 데이터 새로고침 및 오늘 날짜 데이터 재확인
        await fetchData();
        await checkTodayData();
        
        // 작업이 처리될 때까지 주기적으로 새로고침 (최대 30초)
        let refreshCount = 0;
        const maxRefreshes = 6; // 5초마다 6번 = 30초
        
        const refreshInterval = setInterval(async () => {
          refreshCount++;
          const freshData = await adminApi.getCampaignCollectionStatus() as CollectionStatusResponse;
          
          // 선택된 캠페인의 pending이나 processing 작업이 있는지 확인
          const campaignId = parseInt(selectedCampaign);
          const campaign = freshData.campaigns.find((c: CampaignCollectionStatus) => c.campaign_id === campaignId);
          
          if (campaign) {
            const hasPendingOrProcessing = campaign.jobs.some((job: CollectionJob) => 
              job.status === 'pending' || job.status === 'processing'
            );
            
            if (!hasPendingOrProcessing || refreshCount >= maxRefreshes) {
              clearInterval(refreshInterval);
              await fetchData(); // 최종 새로고침
              await checkTodayData();
            } else {
              // 데이터 업데이트
              setData(freshData);
            }
          } else if (refreshCount >= maxRefreshes) {
            clearInterval(refreshInterval);
            await fetchData();
            await checkTodayData();
          }
        }, 5000); // 5초마다 새로고침
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || '즉시 수집 중 오류가 발생했습니다.';
      alert(errorMessage);
      console.error('Error in immediate collection:', err);
    } finally {
      setCollecting(false);
    }
  };

  if (loading) return <Loading>로딩 중...</Loading>;
  if (error) return <Loading>{error}</Loading>;
  if (!data) return <Loading>데이터가 없습니다.</Loading>;

  const displayData = filteredData || data;

  return (
    <Container>
      <Title>캠페인 수집 조회</Title>

      <FilterSection>
        {selectedCampaign && todayDataInfo && (
          <div style={{ 
            marginBottom: '1rem', 
            padding: '0.75rem', 
            backgroundColor: todayDataInfo.has_today_data ? '#d4edda' : '#fff3cd',
            border: `1px solid ${todayDataInfo.has_today_data ? '#c3e6cb' : '#ffeaa7'}`,
            borderRadius: '4px',
            color: todayDataInfo.has_today_data ? '#155724' : '#856404',
            fontSize: '0.9rem'
          }}>
            {todayDataInfo.has_today_data 
              ? `✅ 오늘(${todayDataInfo.today_date}) ${todayDataInfo.today_count}개의 릴스 데이터가 이미 수집되어 있습니다.`
              : `ℹ️ 오늘(${todayDataInfo.today_date}) 수집된 데이터가 없습니다. 즉시 수집 버튼을 클릭하여 수집을 시작하세요.`
            }
          </div>
        )}
        <FilterGrid>
          <FilterGroup>
            <FilterLabel>캠페인 선택</FilterLabel>
            <FilterSelect 
              value={selectedCampaign} 
              onChange={(e) => setSelectedCampaign(e.target.value)}
            >
              <option value="">캠페인을 선택하세요</option>
              {data.campaigns.map(campaign => (
                <option key={campaign.campaign_id} value={campaign.campaign_id.toString()}>
                  {campaign.campaign_name || `캠페인 ${campaign.campaign_id}`}
                </option>
              ))}
            </FilterSelect>
          </FilterGroup>
          
          <FilterGroup>
            <FilterLabel>상태 필터</FilterLabel>
            <FilterSelect 
              value={selectedStatus} 
              onChange={(e) => setSelectedStatus(e.target.value)}
            >
              <option value="all">전체 상태</option>
              <option value="pending">대기중</option>
              <option value="processing">처리중</option>
              <option value="completed">완료</option>
              <option value="failed">실패</option>
            </FilterSelect>
          </FilterGroup>
          
          <div>
            {selectedCampaign && (
              <ProcessButton 
                onClick={handleImmediateCollection} 
                disabled={collecting || checkingToday}
                style={{ width: '100%' }}
              >
                {collecting ? '수집 중...' : checkingToday ? '확인 중...' : '즉시 수집'}
              </ProcessButton>
            )}
          </div>
        </FilterGrid>
      </FilterSection>
      
      <div style={{ marginBottom: '2rem' }}>
        <div 
          onClick={() => setControlsExpanded(!controlsExpanded)} 
          style={{ 
            cursor: 'pointer', 
            display: 'inline-flex', 
            alignItems: 'center', 
            gap: '0.5rem',
            fontSize: '0.9rem',
            color: '#495057',
            fontWeight: '500',
            marginBottom: controlsExpanded ? '1rem' : '0'
          }}
        >
          <span style={{ fontSize: '0.8rem' }}>{controlsExpanded ? '▼' : '▶'}</span>
          컨트롤
        </div>
        
        {controlsExpanded && (
          <>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              <RefreshButton onClick={fetchData} disabled={loading}>
                새로고침
              </RefreshButton>
              <ProcessButton onClick={processJobs} disabled={processing}>
                {processing ? '처리 중...' : '대기 작업 처리'}
              </ProcessButton>
              <ProcessButton onClick={retryFailedReelJobs} disabled={retryingReelJobs}>
                {retryingReelJobs ? '릴스 재시도 중...' : '실패 릴스 재시도'}
              </ProcessButton>
              <ProcessButton onClick={retryFailedCollectionJobs} disabled={retryingCollectionJobs}>
                {retryingCollectionJobs ? '인플루언서 재시도 중...' : '실패 인플루언서 재시도'}
              </ProcessButton>
              <CancelButton onClick={cancelProcessingJobs} disabled={cancelling}>
                {cancelling ? '취소 중...' : '처리중 작업 취소'}
              </CancelButton>
              <CancelButton onClick={stopCollectionWorker} disabled={stoppingWorker}>
                {stoppingWorker ? '중지 중...' : '워커 중지'}
              </CancelButton>
              <CancelButton onClick={cancelAllProcessingJobs} disabled={cancellingAll}>
                {cancellingAll ? '전체 취소 중...' : '전체 작업 중지'}
              </CancelButton>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', paddingTop: '1rem', borderTop: '1px solid #dee2e6' }}>
              <CancelButton onClick={deletePendingJobs} disabled={deletingPending}>
                {deletingPending ? '삭제 중...' : '대기 작업 삭제'}
              </CancelButton>
              <CancelButton onClick={deleteFailedJobs} disabled={deletingFailed}>
                {deletingFailed ? '삭제 중...' : '실패 작업 삭제'}
              </CancelButton>
              <CancelButton onClick={deleteCompletedJobs} disabled={deletingCompleted}>
                {deletingCompleted ? '삭제 중...' : '완료 작업 삭제'}
              </CancelButton>
            </div>
          </>
        )}
      </div>

      <SummaryGrid>
        <SummaryCard>
          <SummaryValue>{displayData.summary.total_campaigns}</SummaryValue>
          <SummaryLabel>전체 캠페인</SummaryLabel>
        </SummaryCard>
        <SummaryCard>
          <SummaryValue>{displayData.summary.total_jobs}</SummaryValue>
          <SummaryLabel>전체 작업</SummaryLabel>
        </SummaryCard>
        <SummaryCard>
          <SummaryValue>{displayData.summary.completed_jobs}</SummaryValue>
          <SummaryLabel>완료된 작업</SummaryLabel>
        </SummaryCard>
        <SummaryCard>
          <SummaryValue>{displayData.summary.failed_jobs}</SummaryValue>
          <SummaryLabel>실패한 작업</SummaryLabel>
        </SummaryCard>
        <SummaryCard>
          <SummaryValue>{displayData.summary.pending_jobs}</SummaryValue>
          <SummaryLabel>대기 중 작업</SummaryLabel>
        </SummaryCard>
        <SummaryCard>
          <SummaryValue>{displayData.summary.processing_jobs}</SummaryValue>
          <SummaryLabel>처리 중 작업</SummaryLabel>
        </SummaryCard>
      </SummaryGrid>

      {displayData.campaigns.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#7f8c8d' }}>
          {!selectedCampaign 
            ? '상단에서 캠페인을 선택해주세요.' 
            : '선택한 조건에 해당하는 데이터가 없습니다.'}
        </div>
      ) : (
        displayData.campaigns.map(campaign => (
        <CampaignSection key={campaign.campaign_id}>
          <CampaignHeader>
            <CampaignTitle>
              {campaign.campaign_name || `캠페인 ${campaign.campaign_id}`}
              {campaign.product && ` - ${campaign.product}`}
              {campaign.start_date && campaign.end_date && (
                <span style={{ 
                  fontSize: '0.9rem', 
                  fontWeight: 'normal', 
                  color: '#6c757d',
                  marginLeft: '0.5rem'
                }}>
                  ({formatDateOnly(campaign.start_date)} ~ {formatDateOnly(campaign.end_date)})
                </span>
              )}
            </CampaignTitle>
          </CampaignHeader>

          <div style={{ 
            marginBottom: '1rem', 
            padding: '0.75rem', 
            backgroundColor: '#e7f3ff',
            border: '1px solid #b3d9ff',
            borderRadius: '4px',
            fontSize: '0.9rem',
            color: '#004085'
          }}>
            📋 <strong>캠페인 릴스 수집 큐</strong> - 아래 표에서 수집 작업 상태를 확인할 수 있습니다.
          </div>

          <StatusGrid>
            <StatusCard>
              <div style={{ fontWeight: 'bold', fontSize: '1.2rem', color: '#0c5460' }}>
                {campaign.status_counts.pending}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#6c757d' }}>대기중</div>
            </StatusCard>
            <StatusCard>
              <div style={{ fontWeight: 'bold', fontSize: '1.2rem', color: '#856404' }}>
                {campaign.status_counts.processing}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#6c757d' }}>처리중</div>
            </StatusCard>
            <StatusCard>
              <div style={{ fontWeight: 'bold', fontSize: '1.2rem', color: '#155724' }}>
                {campaign.status_counts.completed}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#6c757d' }}>완료</div>
            </StatusCard>
            <StatusCard>
              <div style={{ fontWeight: 'bold', fontSize: '1.2rem', color: '#721c24' }}>
                {campaign.status_counts.failed}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#6c757d' }}>실패</div>
            </StatusCard>
          </StatusGrid>

          {campaign.jobs && campaign.jobs.length > 0 ? (
            <>
              {/* 캠페인 기간 내 없는 날짜 데이터 표시 (수집 작업 목록 위) */}
              {campaign.start_date && campaign.end_date && (() => {
                const startDate = new Date(campaign.start_date);
                const endDate = new Date(campaign.end_date);
                const todayKST = getTodayKST();
                const datesWithData = new Set<string>();
                
                // 수집된 작업의 수집일자(completed_at) 추출
                campaign.jobs.forEach(job => {
                  if (job.completed_at) {
                    const collectionDate = new Date(job.completed_at);
                    const dateStr = formatDateOnly(collectionDate.toISOString());
                    datesWithData.add(dateStr);
                  }
                });
                
                // 캠페인 기간 내 모든 날짜 생성
                const allDates: string[] = [];
                const currentDate = new Date(startDate);
                while (currentDate <= endDate) {
                  const dateStr = formatDateOnly(currentDate.toISOString());
                  // 오늘 날짜(KST)보다 뒤의 날짜는 제외
                  if (dateStr <= todayKST) {
                    allDates.push(dateStr);
                  }
                  currentDate.setDate(currentDate.getDate() + 1);
                }
                
                // 없는 날짜 찾기
                const missingDates = allDates.filter(date => !datesWithData.has(date));
                
                if (missingDates.length > 0) {
                  return (
                    <div style={{ 
                      marginTop: '1rem',
                      marginBottom: '1rem',
                      padding: '1rem',
                      backgroundColor: '#fff3cd',
                      border: '1px solid #ffc107',
                      borderRadius: '4px',
                      fontSize: '0.9rem',
                      color: '#856404'
                    }}>
                      <strong>⚠️ 캠페인 기간 내 데이터 없음:</strong>
                      <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        {missingDates.map(date => (
                          <span 
                            key={date}
                            style={{
                              padding: '0.25rem 0.5rem',
                              backgroundColor: '#fff',
                              border: '1px solid #ffc107',
                              borderRadius: '4px',
                              fontSize: '0.85rem'
                            }}
                          >
                            {date}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                }
                return null;
              })()}
              
              <div style={{ 
                marginTop: '1rem', 
                marginBottom: '0.5rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div style={{ 
                  fontSize: '0.9rem',
                  fontWeight: '600',
                  color: '#495057'
                }}>
                  수집 작업 목록 ({campaign.jobs.length}개)
                </div>
                <RefreshButton 
                  onClick={fetchData} 
                  disabled={loading}
                  style={{ 
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.5rem 1rem',
                    fontSize: '0.875rem'
                  }}
                >
                  <RefreshCw size={16} style={loading ? { animation: 'spin 1s linear infinite' } : undefined} />
                  새로고침
                </RefreshButton>
              </div>
              <JobsTable>
                <thead>
                  <tr>
                    <TableHeader>릴스 URL</TableHeader>
                    <TableHeader>상태</TableHeader>
                    <TableHeader>계정명</TableHeader>
                    <TableHeader>좋아요 수</TableHeader>
                    <TableHeader>댓글 수</TableHeader>
                    <TableHeader>재생수</TableHeader>
                    <TableHeader>썸네일</TableHeader>
                    <TableHeader>게시일자</TableHeader>
                    <TableHeader>수집일자</TableHeader>
                    <TableHeader>오류 메시지</TableHeader>
                  </tr>
                </thead>
              <tbody>
                {campaign.jobs.map(job => (
                  <tr key={job.id}>
                    <TableCell title={job.reel_url}>
                      {formatUrl(job.reel_url)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={job.status}>
                        {job.status === 'pending' && '대기중'}
                        {job.status === 'processing' && '처리중'}
                        {job.status === 'completed' && '완료'}
                        {job.status === 'failed' && '실패'}
                      </StatusBadge>
                    </TableCell>
                    <TableCell>
                      {job.user_posted ? (
                        <a 
                          href={`https://www.instagram.com/${job.user_posted}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ 
                            color: '#1d4ed8', 
                            textDecoration: 'none',
                            fontSize: '0.9rem'
                          }}
                        >
                          https://www.instagram.com/{job.user_posted}
                        </a>
                      ) : '-'}
                    </TableCell>
                    <TableCell>
                      {job.likes_count !== undefined && job.likes_count !== null 
                        ? job.likes_count.toLocaleString() 
                        : 'N/A'}
                    </TableCell>
                    <TableCell>
                      {job.comments_count !== undefined && job.comments_count !== null 
                        ? job.comments_count.toLocaleString() 
                        : 'N/A'}
                    </TableCell>
                    <TableCell>
                      {job.video_play_count ? job.video_play_count.toLocaleString() : '-'}
                    </TableCell>
                    <TableCell>
                      {job.s3_thumbnail_url ? (
                        <ThumbnailImage 
                          src={job.s3_thumbnail_url} 
                          alt="썸네일"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                            (e.target as HTMLImageElement).nextElementSibling?.setAttribute('style', 'display: flex');
                          }}
                        />
                      ) : (
                        <ThumbnailPlaceholder>
                          이미지 없음
                        </ThumbnailPlaceholder>
                      )}
                    </TableCell>
                    <TableCell>
                      {job.date_posted ? formatDateOnly(job.date_posted) : formatDateOnly(job.created_at)}
                    </TableCell>
                    <TableCell>
                      {job.completed_at ? formatDateOnly(job.completed_at) : '-'}
                    </TableCell>
                    <TableCell>
                      {job.error_message ? (
                        <span style={{ color: '#721c24', fontSize: '0.8rem' }}>
                          {job.error_message}
                        </span>
                      ) : '-'}
                    </TableCell>
                  </tr>
                ))}
              </tbody>
            </JobsTable>
            </>
          ) : (
            <div style={{ 
              textAlign: 'center', 
              padding: '2rem', 
              color: '#7f8c8d',
              backgroundColor: '#f8f9fa',
              borderRadius: '4px',
              marginTop: '1rem'
            }}>
              수집 작업이 없습니다. 즉시 수집 버튼을 클릭하여 수집을 시작하세요.
            </div>
          )}
        </CampaignSection>
        ))
      )}
    </Container>
  );
};

export default CampaignCollectionStatus;