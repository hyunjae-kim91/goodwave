import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
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

const AdminDashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<AdminDashboardType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
              </tr>
            ))}
          </tbody>
        </DataTable>
      </RecentDataSection>
    </Container>
  );
};

export default AdminDashboard;