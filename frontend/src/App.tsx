import React from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
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

function App() {
  const currentHash = window.location.hash;
  const currentPath = window.location.pathname;
  
  const isAdminRoute = currentHash.startsWith('#/admin') || currentPath.startsWith('/admin');
  const isSharedReportRoute = 
    currentHash.startsWith('#/shared') || currentPath.startsWith('/shared') ||
    currentHash.startsWith('#/reports/') || currentPath.startsWith('/reports/') ||
    currentHash.startsWith('#/report/') || currentPath.startsWith('/report/');
  const isSharedRoute = isSharedReportRoute;

  return (
    <AppContainer>
      <Router>
        {isAdminRoute && !isSharedRoute && <Header />}
        <MainContent>
          {isAdminRoute && !isSharedRoute && <Navigation />}
          <ContentArea style={{ padding: isSharedRoute ? '0' : '20px' }}>
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
              
              {/* Default Route - only redirect to admin if not a shared report route */}
              <Route path="/" element={<Navigate to="/admin" replace />} />
            </Routes>
          </ContentArea>
        </MainContent>
      </Router>
    </AppContainer>
  );
}

export default App;