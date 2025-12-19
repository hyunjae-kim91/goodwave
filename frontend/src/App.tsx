import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import styled from 'styled-components';

// Pages
import AdminDashboard from './pages/AdminDashboard';
import CampaignManagement from './pages/CampaignManagement';
import CampaignCollectionStatus from './pages/CampaignCollectionStatus';
import InfluencerAnalysis from './pages/InfluencerAnalysis';
import InstagramReelReport from './pages/reports/InstagramReelReport';
import InstagramPostReport from './pages/reports/InstagramPostReport';
import BlogReport from './pages/reports/BlogReport';

// Components
import Header from './components/Header';
import Navigation from './components/Navigation';

const AppContainer = styled.div`
  min-height: 100vh;
  background-color: #f5f5f5;
`;

const MainContent = styled.div`
  display: flex;
`;

const ContentArea = styled.div`
  flex: 1;
  padding: 20px;
`;

// URL에서 # 제거하는 컴포넌트
function HashRedirect() {
  const navigate = useNavigate();
  const location = useLocation();
  
  useEffect(() => {
    // URL에 #이 있으면 제거하고 리다이렉트
    const hash = window.location.hash;
    if (hash && hash.startsWith('#/')) {
      const hashPath = hash.substring(1); // # 제거
      // 현재 경로와 다르면 리다이렉트
      if (location.pathname !== hashPath) {
        // URL 업데이트하고 리다이렉트
        window.history.replaceState(null, '', hashPath);
        navigate(hashPath, { replace: true });
      }
    }
  }, [navigate, location]); // location이 변경될 때마다 확인
  
  return null;
}

function App() {
  // 타이틀 설정
  useEffect(() => {
    document.title = 'Fitfluence Report';
  }, []);

  // 초기 로드 시 # 제거 (렌더링 전에 처리)
  const hash = window.location.hash;
  if (hash && hash.startsWith('#/')) {
    const hashPath = hash.substring(1);
    // URL 업데이트하고 페이지 리로드 (BrowserRouter가 제대로 인식하도록)
    window.location.replace(hashPath);
    // 리다이렉트 중이므로 아무것도 렌더링하지 않음
    return null;
  }

  const currentHash = window.location.hash;
  const currentPath = window.location.pathname;
  
  const isAdminRoute = currentHash.startsWith('#/admin') || currentPath.startsWith('/admin');
  // 공유 링크 경로만 네비게이션 숨김 (/shared/, /reports/만, /report/는 관리자 직접 접근이므로 네비게이션 표시)
  const isSharedReportRoute = 
    currentHash.startsWith('#/shared') || currentPath.startsWith('/shared') ||
    currentHash.startsWith('#/reports/') || currentPath.startsWith('/reports/');
  const isSharedRoute = isSharedReportRoute;
  
  // 관리자 경로 또는 /report/ 경로에서는 네비게이션 표시
  const shouldShowNavigation = isAdminRoute || currentPath.startsWith('/report/') || currentHash.startsWith('#/report/');

  return (
    <AppContainer>
      <Router>
        {shouldShowNavigation && <Header />}
        <MainContent>
          {shouldShowNavigation && <Navigation />}
          <ContentArea style={{ padding: shouldShowNavigation ? '20px' : '0' }}>
            <HashRedirect />
            <Routes>
              {/* Admin Routes */}
              <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
              <Route path="/admin/campaigns" element={<CampaignManagement />} />
              <Route path="/admin/campaign-collection-status" element={<CampaignCollectionStatus />} />
              <Route path="/admin/influencer/ingest" element={<InfluencerAnalysis activeTab="ingest" />} />
              <Route path="/admin/influencer/explore" element={<InfluencerAnalysis activeTab="explore" />} />
              <Route path="/admin/influencer/classification" element={<InfluencerAnalysis activeTab="combined-classification" />} />
              <Route path="/admin/influencer/prompt" element={<InfluencerAnalysis activeTab="prompt" />} />
              <Route path="/admin/influencer/analysis" element={<InfluencerAnalysis activeTab="overall-analysis" />} />
              
              {/* Public Report Routes */}
              <Route path="/report/instagram-reel" element={<InstagramReelReport />} />
              <Route path="/report/instagram-post" element={<InstagramPostReport />} />
              <Route path="/report/blog" element={<BlogReport />} />
              
              {/* Shared Report Routes with Campaign Parameter */}
              <Route path="/reports/instagram/reels/:campaignName" element={<InstagramReelReport />} />
              <Route path="/reports/instagram/posts/:campaignName" element={<InstagramPostReport />} />
              <Route path="/reports/blogs/:campaignName" element={<BlogReport />} />
              
              {/* Shared Report Routes (without navigation) */}
              <Route path="/shared/reports/instagram/reels/:campaignName" element={<InstagramReelReport />} />
              <Route path="/shared/reports/instagram/posts/:campaignName" element={<InstagramPostReport />} />
              <Route path="/shared/reports/blogs/:campaignName" element={<BlogReport />} />
              
              {/* Default Route - only redirect to admin if path is exactly "/" */}
              <Route path="/" element={<Navigate to="/admin" replace />} />
            </Routes>
          </ContentArea>
        </MainContent>
      </Router>
    </AppContainer>
  );
}

export default App;