import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { useNavigate } from 'react-router-dom';
import { adminApi } from '../services/api';
import { AdminDashboard as AdminDashboardType } from '../types';

const Container = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const Title = styled.h1`
  color: #2c3e50;
  margin-bottom: 2rem;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
`;

const StatCard = styled.div`
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  text-align: center;
`;

const StatValue = styled.div`
  font-size: 2rem;
  font-weight: bold;
  color: #3498db;
  margin-bottom: 0.5rem;
`;

const StatLabel = styled.div`
  color: #7f8c8d;
  font-size: 0.9rem;
`;

const RecentDataSection = styled.div`
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 1rem;
`;

const SectionTitle = styled.h3`
  color: #2c3e50;
  margin-bottom: 1rem;
`;

const DataTable = styled.table`
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
`;

const Loading = styled.div`
  text-align: center;
  padding: 2rem;
  color: #7f8c8d;
`;

const ReportButton = styled.button`
  background-color: #3498db;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  margin-right: 0.5rem;
  
  &:hover {
    background-color: #2980b9;
  }
  
  &:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
  }
`;

const ShareButton = styled.button`
  background-color: #27ae60;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  margin-right: 0.5rem;
  
  &:hover {
    background-color: #229954;
  }
  
  &:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
  }
`;

const Modal = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
`;

const ModalTitle = styled.h3`
  margin-bottom: 1rem;
  color: #2c3e50;
`;

const UrlBox = styled.div`
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 1rem;
  margin: 1rem 0;
  word-break: break-all;
  font-family: monospace;
  font-size: 0.9rem;
`;

const CopyButton = styled.button`
  background-color: #3498db;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  margin-right: 0.5rem;
  
  &:hover {
    background-color: #2980b9;
  }
`;

const CloseButton = styled.button`
  background-color: #95a5a6;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  
  &:hover {
    background-color: #7f8c8d;
  }
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 0.5rem;
`;

const AdminDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState<AdminDashboardType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareUrl, setShareUrl] = useState('');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getDashboard();
      setDashboardData(data);
      setError(null);
    } catch (err) {
      setError('대시보드 데이터를 불러오는데 실패했습니다.');
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewReport = (campaignName: string, campaignType: string) => {
    // 캠페인 이름을 URL에 적합한 형태로 변환
    const encodedCampaignName = encodeURIComponent(campaignName);
    
    // 캠페인 타입에 따라 적절한 보고서 페이지로 이동
    switch (campaignType) {
      case 'instagram_reel':
        navigate(`/reports/instagram/reels/${encodedCampaignName}`);
        break;
      case 'blog':
        navigate(`/reports/blogs/${encodedCampaignName}`);
        break;
      default:
        console.warn('Unknown campaign type:', campaignType);
    }
  };

  const handleShareReport = (campaignName: string, campaignType: string) => {
    // 캠페인 이름 정규화 (탭, 줄바꿈, 공백 제거)
    const normalizedCampaignName = campaignName.trim().replace(/\t/g, '').replace(/\n/g, '').replace(/\r/g, '');
    // 캠페인 이름을 URL에 적합한 형태로 변환
    const encodedCampaignName = encodeURIComponent(normalizedCampaignName);
    
    // 현재 호스트 정보 가져오기
    const baseUrl = window.location.origin;
    
    // 캠페인 타입에 따라 공유 URL 생성
    let sharedUrl = '';
    switch (campaignType) {
      case 'instagram_reel':
        sharedUrl = `${baseUrl}/#/shared/reports/instagram/reels/${encodedCampaignName}`;
        break;
      case 'blog':
        sharedUrl = `${baseUrl}/#/shared/reports/blogs/${encodedCampaignName}`;
        break;
      default:
        console.warn('Unknown campaign type:', campaignType);
        return;
    }
    
    setShareUrl(sharedUrl);
    setShowShareModal(true);
  };

  const handleCopyUrl = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      alert('URL이 클립보드에 복사되었습니다!');
    } catch (err) {
      console.error('Failed to copy URL:', err);
      alert('URL 복사에 실패했습니다.');
    }
  };

  const handleCloseModal = () => {
    setShowShareModal(false);
    setShareUrl('');
  };

  if (loading) return <Loading>로딩 중...</Loading>;
  if (error) return <Loading>{error}</Loading>;
  if (!dashboardData) return <Loading>데이터가 없습니다.</Loading>;

  return (
    <Container>
      <Title>관리자 대시보드</Title>
      
      <StatsGrid>
        <StatCard>
          <StatValue>{dashboardData.statistics.total_campaigns}</StatValue>
          <StatLabel>전체 캠페인</StatLabel>
        </StatCard>
        <StatCard>
          <StatValue>{dashboardData.statistics.active_campaigns}</StatValue>
          <StatLabel>활성 캠페인</StatLabel>
        </StatCard>
        <StatCard>
          <StatValue>{dashboardData.statistics.total_instagram_posts}</StatValue>
          <StatLabel>인스타그램 게시물</StatLabel>
        </StatCard>
        <StatCard>
          <StatValue>{dashboardData.statistics.total_instagram_reels}</StatValue>
          <StatLabel>인스타그램 릴스</StatLabel>
        </StatCard>
        <StatCard>
          <StatValue>{dashboardData.statistics.total_blog_posts}</StatValue>
          <StatLabel>블로그 게시물</StatLabel>
        </StatCard>
      </StatsGrid>

      <RecentDataSection>
        <SectionTitle>캠페인 목록</SectionTitle>
        <DataTable>
          <thead>
            <tr>
              <TableHeader>캠페인명</TableHeader>
              <TableHeader>제품</TableHeader>
              <TableHeader>유형</TableHeader>
              <TableHeader>광고비</TableHeader>
              <TableHeader>기간</TableHeader>
              <TableHeader>작업</TableHeader>
            </tr>
          </thead>
          <tbody>
            {(dashboardData.campaigns || []).map(campaign => (
              <tr key={campaign.id}>
                <TableCell>{campaign.name}</TableCell>
                <TableCell>{campaign.product}</TableCell>
                <TableCell>{campaign.campaign_type}</TableCell>
                <TableCell>{campaign.budget.toLocaleString()}원</TableCell>
                <TableCell>
                  {new Date(campaign.start_date).toLocaleDateString()} ~ {new Date(campaign.end_date).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <ButtonGroup>
                    <ReportButton 
                      onClick={() => handleViewReport(campaign.name, campaign.campaign_type)}
                    >
                      📊 보고서 보기
                    </ReportButton>
                    <ShareButton 
                      onClick={() => handleShareReport(campaign.name, campaign.campaign_type)}
                    >
                      🔗 보고서 공유
                    </ShareButton>
                  </ButtonGroup>
                </TableCell>
              </tr>
            ))}
          </tbody>
        </DataTable>
      </RecentDataSection>

      {showShareModal && (
        <Modal onClick={handleCloseModal}>
          <ModalContent onClick={(e) => e.stopPropagation()}>
            <ModalTitle>보고서 공유</ModalTitle>
            <p>아래 URL을 복사하여 보고서를 공유하세요:</p>
            <UrlBox>{shareUrl}</UrlBox>
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <CopyButton onClick={handleCopyUrl}>
                📋 URL 복사
              </CopyButton>
              <CloseButton onClick={handleCloseModal}>
                닫기
              </CloseButton>
            </div>
          </ModalContent>
        </Modal>
      )}
    </Container>
  );
};

export default AdminDashboard;