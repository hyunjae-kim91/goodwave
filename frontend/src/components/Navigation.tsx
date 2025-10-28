import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import { 
  BarChart2,
  Settings, 
  Instagram, 
  Video, 
  Edit3,
  Users,
  Download,
  Search,
  Tag,
  MessageSquare,
  PieChart,
  Activity
} from 'lucide-react';

const NavContainer = styled.nav`
  width: 250px;
  background-color: #34495e;
  min-height: calc(100vh - 80px);
  padding: 1rem 0;
`;

const NavItem = styled(Link)<{ $isActive: boolean }>`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  color: ${props => props.$isActive ? '#3498db' : '#ecf0f1'};
  text-decoration: none;
  background-color: ${props => props.$isActive ? '#2c3e50' : 'transparent'};
  border-left: ${props => props.$isActive ? '4px solid #3498db' : '4px solid transparent'};
  transition: all 0.3s ease;

  &:hover {
    background-color: #2c3e50;
    color: #3498db;
  }

  svg {
    font-size: 1.1rem;
    flex-shrink: 0;
  }
`;

const NavSection = styled.div`
  margin-bottom: 1rem;
`;

const SectionTitle = styled.div`
  padding: 0.5rem 1.5rem;
  color: #bdc3c7;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
`;

const Navigation: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <NavContainer>
      <NavSection>
        <SectionTitle>관리자 메뉴</SectionTitle>
        <NavItem to="/admin/dashboard" $isActive={isActive('/admin/dashboard')}>
          <BarChart2 size={16} />
          대시보드
        </NavItem>
        <NavItem to="/admin/campaigns" $isActive={isActive('/admin/campaigns')}>
          <Settings size={16} />
          캠페인 관리
        </NavItem>
        <NavItem to="/admin/campaign-collection-status" $isActive={isActive('/admin/campaign-collection-status')}>
          <Activity size={16} />
          캠페인 수집 조회
        </NavItem>
      </NavSection>
      
      <NavSection>
        <SectionTitle>인플루언서 분석</SectionTitle>
        <NavItem to="/admin/influencer/ingest" $isActive={isActive('/admin/influencer/ingest')}>
          <Download size={16} />
          수집
        </NavItem>
        <NavItem to="/admin/influencer/explore" $isActive={isActive('/admin/influencer/explore')}>
          <Search size={16} />
          탐색
        </NavItem>
        <NavItem to="/admin/influencer/classification" $isActive={isActive('/admin/influencer/classification')}>
          <Tag size={16} />
          구독동기/카테고리 분류
        </NavItem>
        <NavItem to="/admin/influencer/prompt" $isActive={isActive('/admin/influencer/prompt')}>
          <MessageSquare size={16} />
          프롬프트 관리
        </NavItem>
        <NavItem to="/admin/influencer/analysis" $isActive={isActive('/admin/influencer/analysis')}>
          <PieChart size={16} />
          전체 분석
        </NavItem>
      </NavSection>
      
      <NavSection>
        <SectionTitle>보고서 바로가기</SectionTitle>
        <NavItem to="/report/instagram-reel" $isActive={isActive('/report/instagram-reel')}>
          <Video size={16} />
          인스타그램 캠페인
        </NavItem>
        <NavItem to="/report/blog" $isActive={isActive('/report/blog')}>
          <Edit3 size={16} />
          네이버 블로그
        </NavItem>
      </NavSection>
    </NavContainer>
  );
};

export default Navigation;
