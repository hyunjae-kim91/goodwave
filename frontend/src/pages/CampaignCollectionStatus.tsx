import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { adminApi } from '../services/api';

interface CollectionJob {
  id: number;
  campaign_id: number;
  reel_url: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  user_posted?: string;
  video_play_count?: number;
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
  const [selectedCampaign, setSelectedCampaign] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (!data) return;
    
    let filtered = { ...data };
    
    // 캠페인별 필터링
    if (selectedCampaign !== 'all') {
      const campaignId = parseInt(selectedCampaign);
      filtered.campaigns = data.campaigns.filter(c => c.campaign_id === campaignId);
    }
    
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
      const campaignId = selectedCampaign !== 'all' ? parseInt(selectedCampaign) : undefined;
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
      const campaignId = selectedCampaign !== 'all' ? parseInt(selectedCampaign) : undefined;
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
      const campaignId = selectedCampaign !== 'all' ? parseInt(selectedCampaign) : undefined;
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
      const campaignId = selectedCampaign !== 'all' ? parseInt(selectedCampaign) : undefined;
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
      const campaignId = selectedCampaign !== 'all' ? parseInt(selectedCampaign) : undefined;
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
      const campaignId = selectedCampaign !== 'all' ? parseInt(selectedCampaign) : undefined;
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR');
  };

  const formatUrl = (url: string) => {
    if (url.length > 50) {
      return url.substring(0, 50) + '...';
    }
    return url;
  };

  if (loading) return <Loading>로딩 중...</Loading>;
  if (error) return <Loading>{error}</Loading>;
  if (!data) return <Loading>데이터가 없습니다.</Loading>;

  const displayData = filteredData || data;

  return (
    <Container>
      <Title>캠페인 수집 조회 - 업데이트됨</Title>

      <FilterSection>
        <FilterGrid>
          <FilterGroup>
            <FilterLabel>캠페인 선택</FilterLabel>
            <FilterSelect 
              value={selectedCampaign} 
              onChange={(e) => setSelectedCampaign(e.target.value)}
            >
              <option value="all">전체 캠페인</option>
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
            {/* 빈 공간 */}
          </div>
        </FilterGrid>
      </FilterSection>
      
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '2rem' }}>
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

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '2rem', paddingTop: '1rem', borderTop: '1px solid #dee2e6' }}>
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
          선택한 조건에 해당하는 데이터가 없습니다.
        </div>
      ) : (
        displayData.campaigns.map(campaign => (
        <CampaignSection key={campaign.campaign_id}>
          <CampaignHeader>
            <CampaignTitle>
              {campaign.campaign_name || `캠페인 ${campaign.campaign_id}`}
              {campaign.product && ` - ${campaign.product}`}
            </CampaignTitle>
          </CampaignHeader>

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

          {campaign.jobs && campaign.jobs.length > 0 && (
            <JobsTable>
              <thead>
                <tr>
                  <TableHeader>릴스 URL</TableHeader>
                  <TableHeader>상태</TableHeader>
                  <TableHeader>계정명</TableHeader>
                  <TableHeader>재생수</TableHeader>
                  <TableHeader>썸네일</TableHeader>
                  <TableHeader>게시일자</TableHeader>
                  <TableHeader>완료일시</TableHeader>
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
                      {job.date_posted ? formatDate(job.date_posted) : formatDate(job.created_at)}
                    </TableCell>
                    <TableCell>
                      {job.completed_at ? formatDate(job.completed_at) : '-'}
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
          )}
        </CampaignSection>
        ))
      )}
    </Container>
  );
};

export default CampaignCollectionStatus;