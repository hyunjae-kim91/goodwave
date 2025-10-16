import React from 'react';
import styled from 'styled-components';
import { Toaster } from 'react-hot-toast';

// Components from goodwave_web
import IngestTab from '../components/influencer/IngestTab';
import ExploreTab from '../components/influencer/ExploreTab';
import CombinedClassificationTab from '../components/influencer/CombinedClassificationTab';
import OverallAnalysisTab from '../components/influencer/OverallAnalysisTab';
import PromptTab from '../components/influencer/PromptTab';
import ClassificationDataManagementTab from '../components/influencer/ClassificationDataManagementTab';

const Container = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const Title = styled.h1`
  color: #2c3e50;
  margin-bottom: 2rem;
`;

const ContentSection = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
`;

type SubTab = 'ingest' | 'explore' | 'combined-classification' | 'overall-analysis' | 'prompt' | 'data-management';

interface InfluencerAnalysisProps {
  activeTab?: SubTab;
}

const InfluencerAnalysis: React.FC<InfluencerAnalysisProps> = ({ activeTab = 'ingest' }) => {
  const activeSubTab = activeTab;

  const getPageTitle = () => {
    switch (activeSubTab) {
      case 'ingest':
        return '수집';
      case 'explore':
        return '탐색';
      case 'combined-classification':
        return '구독동기/카테고리 분류';
      case 'prompt':
        return '프롬프트 관리';
      case 'overall-analysis':
        return '전체 분석';
      case 'data-management':
        return '분류 데이터 관리';
      default:
        return '인플루언서 분석';
    }
  };

  const renderSubTab = () => {
    switch (activeSubTab) {
      case 'ingest':
        return <IngestTab />;
      case 'explore':
        return <ExploreTab />;
      case 'combined-classification':
        return <CombinedClassificationTab />;
      case 'overall-analysis':
        return <OverallAnalysisTab />;
      case 'prompt':
        return <PromptTab />;
      case 'data-management':
        return <ClassificationDataManagementTab />;
      default:
        return <IngestTab />;
    }
  };

  return (
    <Container>
      <Title>굿웨이브 인플루언서 분석 - {getPageTitle()}</Title>
      
      <ContentSection>
        {renderSubTab()}
      </ContentSection>

      {/* 토스트 알림 */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
        }}
      />
    </Container>
  );
};

export default InfluencerAnalysis;