import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import styled from 'styled-components';

// Pages
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import CampaignManagement from './pages/CampaignManagement';
import CampaignCollectionStatus from './pages/CampaignCollectionStatus';
import InfluencerAnalysis from './pages/InfluencerAnalysis';
import UserManagement from './pages/UserManagement';
import InstagramReelReport from './pages/reports/InstagramReelReport';
import InstagramPostReport from './pages/reports/InstagramPostReport';
import BlogReport from './pages/reports/BlogReport';

// Components
import Header from './components/Header';
import Navigation from './components/Navigation';
import AccessDenied from './components/AccessDenied';

// Utils
import { isSharedReportPath } from './utils/ipAccessCheck';
import { isAuthenticated } from './services/auth';

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

// Admin 경로 보호 컴포넌트 (인증 필요)
const ProtectedAdminRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      // 로그인 페이지로 리다이렉트 (현재 위치 저장)
      navigate('/login', { 
        state: { from: location },
        replace: true 
      });
    } else {
      setLoading(false);
    }
  }, [navigate, location]);

  if (loading || !isAuthenticated()) {
    return (
      <AppContainer>
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <p>인증 확인 중...</p>
        </div>
      </AppContainer>
    );
  }

  return children;
};

// 공유 보고서 경로 보호 컴포넌트 (공유 경로가 아니면 차단)
const ProtectedReportRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const location = useLocation();
  const pathname = location.pathname;

  // 공유 경로인지 확인
  if (!isSharedReportPath(pathname)) {
    return <AccessDenied message="공유된 보고서 링크를 통해서만 접근할 수 있습니다." />;
  }

  return children;
};

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
              {/* Login Route */}
              <Route path="/login" element={<Login />} />
              
              {/* Admin Routes - 인증 필요 */}
              <Route path="/admin" element={
                <ProtectedAdminRoute>
                  <Navigate to="/admin/dashboard" replace />
                </ProtectedAdminRoute>
              } />
              <Route path="/admin/dashboard" element={
                <ProtectedAdminRoute>
                  <AdminDashboard />
                </ProtectedAdminRoute>
              } />
              <Route path="/admin/campaigns" element={
                <ProtectedAdminRoute>
                  <CampaignManagement />
                </ProtectedAdminRoute>
              } />
              <Route path="/admin/campaign-collection-status" element={
                <ProtectedAdminRoute>
                  <CampaignCollectionStatus />
                </ProtectedAdminRoute>
              } />
              <Route path="/admin/influencer/ingest" element={
                <ProtectedAdminRoute>
                  <InfluencerAnalysis activeTab="ingest" />
                </ProtectedAdminRoute>
              } />
              <Route path="/admin/influencer/explore" element={
                <ProtectedAdminRoute>
                  <InfluencerAnalysis activeTab="explore" />
                </ProtectedAdminRoute>
              } />
              <Route path="/admin/influencer/classification" element={
                <ProtectedAdminRoute>
                  <InfluencerAnalysis activeTab="combined-classification" />
                </ProtectedAdminRoute>
              } />
              <Route path="/admin/influencer/prompt" element={
                <ProtectedAdminRoute>
                  <InfluencerAnalysis activeTab="prompt" />
                </ProtectedAdminRoute>
              } />
              <Route path="/admin/influencer/analysis" element={
                <ProtectedAdminRoute>
                  <InfluencerAnalysis activeTab="overall-analysis" />
                </ProtectedAdminRoute>
              } />
              <Route path="/admin/users" element={
                <ProtectedAdminRoute>
                  <UserManagement />
                </ProtectedAdminRoute>
              } />
              
              {/* Public Report Routes - 인증 필요 (관리자용) */}
              <Route path="/report/instagram-reel" element={
                <ProtectedAdminRoute>
                  <InstagramReelReport />
                </ProtectedAdminRoute>
              } />
              <Route path="/report/instagram-post" element={
                <ProtectedAdminRoute>
                  <InstagramPostReport />
                </ProtectedAdminRoute>
              } />
              <Route path="/report/blog" element={
                <ProtectedAdminRoute>
                  <BlogReport />
                </ProtectedAdminRoute>
              } />
              
              {/* Shared Report Routes - 공유 경로만 접근 가능 */}
              <Route path="/reports/instagram/reels/:campaignName" element={
                <ProtectedReportRoute>
                  <InstagramReelReport />
                </ProtectedReportRoute>
              } />
              <Route path="/reports/instagram/posts/:campaignName" element={
                <ProtectedReportRoute>
                  <InstagramPostReport />
                </ProtectedReportRoute>
              } />
              <Route path="/reports/blogs/:campaignName" element={
                <ProtectedReportRoute>
                  <BlogReport />
                </ProtectedReportRoute>
              } />
              
              {/* Shared Report Routes (without navigation) - 공유 경로만 접근 가능 */}
              <Route path="/shared/reports/instagram/reels/:campaignName" element={
                <ProtectedReportRoute>
                  <InstagramReelReport />
                </ProtectedReportRoute>
              } />
              <Route path="/shared/reports/instagram/posts/:campaignName" element={
                <ProtectedReportRoute>
                  <InstagramPostReport />
                </ProtectedReportRoute>
              } />
              <Route path="/shared/reports/blogs/:campaignName" element={
                <ProtectedReportRoute>
                  <BlogReport />
                </ProtectedReportRoute>
              } />
              
              {/* Default Route - 인증 필요 */}
              <Route path="/" element={
                <ProtectedAdminRoute>
                  <Navigate to="/admin" replace />
                </ProtectedAdminRoute>
              } />
            </Routes>
          </ContentArea>
        </MainContent>
      </Router>
    </AppContainer>
  );
}

export default App;