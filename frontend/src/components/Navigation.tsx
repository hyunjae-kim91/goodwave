import React, { useState } from 'react';
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
  Activity,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

const NavContainer = styled.nav<{ $isCollapsed: boolean }>`
  width: ${props => props.$isCollapsed ? '60px' : '250px'};
  background-color: #34495e;
  min-height: calc(100vh - 80px);
  padding: 1rem 0;
  transition: width 0.3s ease;
  position: relative;
`;

const ToggleButton = styled.button`
  position: absolute;
  top: 10px;
  right: -15px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: #3498db;
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  z-index: 10;
  transition: all 0.3s ease;

  &:hover {
    background-color: #2980b9;
    transform: scale(1.1);
  }
`;

const NavItem = styled(Link)<{ $isActive: boolean; $isCollapsed: boolean }>`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  color: ${props => props.$isActive ? '#3498db' : '#ecf0f1'};
  text-decoration: none;
  background-color: ${props => props.$isActive ? '#2c3e50' : 'transparent'};
  border-left: ${props => props.$isActive ? '4px solid #3498db' : '4px solid transparent'};
  transition: all 0.3s ease;
  white-space: nowrap;
  overflow: hidden;

  &:hover {
    background-color: #2c3e50;
    color: #3498db;
  }

  svg {
    font-size: 1.1rem;
    flex-shrink: 0;
  }

  span {
    opacity: ${props => props.$isCollapsed ? '0' : '1'};
    transition: opacity 0.3s ease;
    ${props => props.$isCollapsed && 'display: none;'}
  }
`;

const NavSection = styled.div`
  margin-bottom: 1rem;
`;

const SectionTitle = styled.div<{ $isCollapsed: boolean }>`
  padding: 0.5rem 1.5rem;
  color: #bdc3c7;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  white-space: nowrap;
  overflow: hidden;
  opacity: ${props => props.$isCollapsed ? '0' : '1'};
  transition: opacity 0.3s ease;
  ${props => props.$isCollapsed && 'display: none;'}
`;

const Navigation: React.FC = () => {
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(true);

  const isActive = (path: string) => location.pathname === path;

  return (
    <NavContainer $isCollapsed={isCollapsed}>
      <ToggleButton onClick={() => setIsCollapsed(!isCollapsed)}>
        {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </ToggleButton>
      
      <NavSection>
        <SectionTitle $isCollapsed={isCollapsed}>관리자 메뉴</SectionTitle>
        <NavItem to="/admin/dashboard" $isActive={isActive('/admin/dashboard')} $isCollapsed={isCollapsed}>
          <BarChart2 size={16} />
          <span>대시보드</span>
        </NavItem>
        <NavItem to="/admin/campaigns" $isActive={isActive('/admin/campaigns')} $isCollapsed={isCollapsed}>
          <Settings size={16} />
          <span>캠페인 관리</span>
        </NavItem>
        <NavItem to="/admin/campaign-collection-status" $isActive={isActive('/admin/campaign-collection-status')} $isCollapsed={isCollapsed}>
          <Activity size={16} />
          <span>캠페인 수집 조회</span>
        </NavItem>
      </NavSection>
      
      <NavSection>
        <SectionTitle $isCollapsed={isCollapsed}>인플루언서 분석</SectionTitle>
        <NavItem to="/admin/influencer/ingest" $isActive={isActive('/admin/influencer/ingest')} $isCollapsed={isCollapsed}>
          <Download size={16} />
          <span>수집</span>
        </NavItem>
        <NavItem to="/admin/influencer/explore" $isActive={isActive('/admin/influencer/explore')} $isCollapsed={isCollapsed}>
          <Search size={16} />
          <span>탐색</span>
        </NavItem>
        <NavItem to="/admin/influencer/classification" $isActive={isActive('/admin/influencer/classification')} $isCollapsed={isCollapsed}>
          <Tag size={16} />
          <span>구독동기/카테고리 분류</span>
        </NavItem>
        <NavItem to="/admin/influencer/prompt" $isActive={isActive('/admin/influencer/prompt')} $isCollapsed={isCollapsed}>
          <MessageSquare size={16} />
          <span>프롬프트 관리</span>
        </NavItem>
        <NavItem to="/admin/influencer/analysis" $isActive={isActive('/admin/influencer/analysis')} $isCollapsed={isCollapsed}>
          <PieChart size={16} />
          <span>전체 분석</span>
        </NavItem>
      </NavSection>
      
      <NavSection>
        <SectionTitle $isCollapsed={isCollapsed}>보고서 바로가기</SectionTitle>
        <NavItem to="/report/instagram-reel" $isActive={isActive('/report/instagram-reel')} $isCollapsed={isCollapsed}>
          <Video size={16} />
          <span>인스타그램 캠페인</span>
        </NavItem>
        <NavItem to="/report/blog" $isActive={isActive('/report/blog')} $isCollapsed={isCollapsed}>
          <Edit3 size={16} />
          <span>네이버 블로그</span>
        </NavItem>
      </NavSection>
    </NavContainer>
  );
};

export default Navigation;
