import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { useParams } from 'react-router-dom';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title as ChartTitle,
  Tooltip,
  Legend,
} from 'chart.js';
import { reportsApi } from '../../services/api';
import { InstagramReelReport as InstagramReelReportType, Campaign } from '../../types';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

// Chart.js 등록
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ChartTitle,
  Tooltip,
  Legend
);

const ANALYSIS_PLACEHOLDER = '인플루언서 분석 수집 필요';

const getAnalysisValue = (value?: string | null): string => {
  const normalized = (value ?? '').trim();
  // 빈 값이거나 null인 경우에만 "수집 필요" 표시
  // "미분류"나 다른 분류 결과는 모두 유효한 분석 결과로 인정
  return normalized ? normalized : ANALYSIS_PLACEHOLDER;
};

const Container = styled.div`
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
`;

const Header = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
`;

const TopControls = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
  background: white;
  padding: 1rem 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
`;

const ControlsLeft = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
`;

const ControlsRight = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
`;

const TitleRow = styled.div`
  margin-bottom: 1rem;
`;

const Title = styled.h1`
  color: #2c3e50;
  margin: 0;
`;

const CampaignSelector = styled.select`
  padding: 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1rem;
  min-width: 200px;
`;

const CampaignInfo = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  margin-bottom: 2rem;
`;

const InfoRow = styled.div`
  display: grid;
  gap: 0.8rem;
  
  &.top-row {
    grid-template-columns: repeat(3, 1fr);
  }
  
  &.bottom-row {
    grid-template-columns: repeat(4, 1fr);
  }
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr !important;
  }
`;

const InfoCard = styled.div`
  background: #f8f9fa;
  padding: 0.8rem;
  border-radius: 4px;
  text-align: center;
`;

const InfoLabel = styled.div`
  color: #6c757d;
  font-size: 0.85rem;
  margin-bottom: 0.4rem;
`;

const InfoValue = styled.div`
  color: #2c3e50;
  font-weight: 600;
  font-size: 1rem;
`;

const ChartSection = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
`;

const TableContainer = styled.div`
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow-x: auto;
`;

const Table = styled.table`
  width: 100%;
  white-space: nowrap;
  border-collapse: collapse;
`;

const TableHeader = styled.thead`
  background-color: #f8f9fa;
`;

const HeaderRow = styled.tr``;

const HeaderCell = styled.th`
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #495057;
  border-bottom: 2px solid #dee2e6;
  white-space: nowrap;

  &.image-column {
    width: 140px;
    text-align: center;
  }

  &.user-column {
    min-width: 250px;
  }

  &.view-column {
    width: 100px;
  }

  &.meta-column {
    width: 100px;
  }
`;

const TableBody = styled.tbody``;

const TableRow = styled.tr`
  &:nth-child(even) {
    background-color: #f8f9fa;
  }

  &:hover {
    background-color: #e9ecef;
  }
`;

const TableCell = styled.td`
  padding: 1rem;
  border-bottom: 1px solid #dee2e6;
  vertical-align: top;

  &.image-cell {
    text-align: center;
    padding: 0.5rem;
  }
`;

const ReelImage = styled.img`
  width: 120px;
  height: 120px;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;

  &:hover {
    opacity: 0.8;
  }
`;

const UserInfo = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`;

const Username = styled.div`
  font-weight: 600;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const DisplayName = styled.div`
  font-size: 0.85rem;
  color: #34495e;
`;

const Grade = styled.span<{ grade: string }>`
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
  color: white;
  background-color: ${props => 
    props.grade === '블루' || props.grade === 'blue' ? '#3498db' :
    props.grade === '레드' || props.grade === 'red' ? '#e74c3c' :
    props.grade === '골드' || props.grade === 'gold' ? '#f1c40f' :
    props.grade === '프리미엄' || props.grade === 'premium' ? '#9b59b6' :
    props.grade === 'A' ? '#27ae60' :
    props.grade === 'B' ? '#f39c12' : '#95a5a6'
  };
`;

const AvgViewCount = styled.div`
  font-size: 0.85rem;
  color: #6c757d;
`;

const FollowerCount = styled.div`
  font-size: 0.85rem;
  color: #6c757d;
`;

const ViewCount = styled.div`
  font-weight: 600;
  color: #e74c3c;
  font-size: 1.1rem;
`;

const MetaInfo = styled.div`
  font-size: 0.85rem;
  color: #6c757d;
  margin-bottom: 0.25rem;

  &:last-child {
    margin-bottom: 0;
  }
`;

const Loading = styled.div`
  text-align: center;
  padding: 2rem;
  color: #7f8c8d;
`;

const ErrorMessage = styled.div`
  background: #fff5f5;
  border: 1px solid #fed7d7;
  border-radius: 8px;
  padding: 1rem;
  margin: 1rem 0;
  color: #c53030;
  text-align: center;
`;

const NoDataMessage = styled.div`
  background: #fffbeb;
  border: 1px solid #fbd38d;
  border-radius: 8px;
  padding: 2rem;
  margin: 1rem 0;
  color: #c05621;
  text-align: center;
  
  h3 {
    margin-top: 0;
    color: #c05621;
  }
  
  p {
    margin-bottom: 0;
    line-height: 1.6;
  }
`;

const ShareButton = styled.button`
  background: #3498db;
  color: white;
  border: none;
  padding: 0.75rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  white-space: nowrap;
  transition: background-color 0.2s;

  &:hover {
    background: #2980b9;
  }

  &:active {
    background: #21618c;
  }
`;

const PDFButton = styled.button`
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.75rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  white-space: nowrap;
  transition: background-color 0.2s;

  &:hover {
    background: #c0392b;
  }

  &:active {
    background: #a93226;
  }

  &:disabled {
    background: #95a5a6;
    cursor: not-allowed;
  }
`;

const InstagramReelReport: React.FC = () => {
  const { campaignName } = useParams<{ campaignName?: string }>();
  const [reportData, setReportData] = useState<InstagramReelReportType | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    fetchAvailableCampaigns();
  }, []);

  useEffect(() => {
    if (campaignName) {
      // URL에서 캠페인명이 제공된 경우
      const decodedCampaignName = decodeURIComponent(campaignName);
      setSelectedCampaign(decodedCampaignName);
      fetchReportData(decodedCampaignName);
    }
  }, [campaignName]);

  useEffect(() => {
    if (selectedCampaign && !campaignName) {
      fetchReportData(selectedCampaign);
    }
  }, [selectedCampaign, campaignName]);

  const fetchAvailableCampaigns = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await reportsApi.getAvailableCampaigns();
      const reelCampaigns = data.filter(c => 
        c.campaign_type === 'instagram_reel' || 
        c.campaign_type === 'instagram_post' ||  // 인스타그램 포스트도 포함 (릴스 포함)
        c.campaign_type === 'all'
      );
      setCampaigns(reelCampaigns);
      
      if (reelCampaigns.length > 0 && !selectedCampaign && !campaignName) {
        setSelectedCampaign(reelCampaigns[0].name);
      }
    } catch (error) {
      console.error('Error fetching campaigns:', error);
      setError('캠페인 목록을 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const fetchReportData = async (campaignName: string) => {
    try {
      setLoading(true);
      setError(null);
      console.log('Fetching report data for campaign:', campaignName);
      const data = await reportsApi.getInstagramReelReport(campaignName);
      console.log('Report data received:', data);
      setReportData(data);
      
      // 데이터가 비어있는 경우 사용자에게 알림
      if (!data.reels || data.reels.length === 0) {
        setError('이 캠페인에 대한 인스타그램 릴스 데이터가 아직 수집되지 않았습니다. 데이터 수집을 먼저 진행해주세요.');
      }
    } catch (error: any) {
      console.error('Error fetching report data:', error);
      if (error.response) {
        // API 응답 오류
        if (error.response.status === 404) {
          setError('해당 캠페인을 찾을 수 없습니다.');
        } else if (error.response.status === 500) {
          setError('서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        } else {
          setError('보고서 데이터를 불러오는 중 오류가 발생했습니다.');
        }
      } else if (error.request) {
        // 네트워크 오류
        setError('네트워크 연결을 확인해주세요.');
      } else {
        setError('알 수 없는 오류가 발생했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCampaignChange = (campaignName: string) => {
    setSelectedCampaign(campaignName);
  };

  const handleShare = () => {
    if (!selectedCampaign) return;
    
    const shareUrl = `${window.location.origin}/#/reports/instagram/reels/${encodeURIComponent(selectedCampaign)}`;
    
    // 클립보드 API 사용 가능 여부 확인
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(shareUrl).then(() => {
        alert('보고서 링크가 클립보드에 복사되었습니다');
      }).catch(() => {
        // 클립보드 복사가 실패한 경우 URL을 표시
        prompt('보고서 링크를 복사하세요', shareUrl);
      });
    } else {
      // 클립보드 API를 지원하지 않는 경우 직접 URL 표시
      prompt('보고서 링크를 복사하세요', shareUrl);
    }
  };

  const handlePDFDownload = async () => {
    if (!reportData || !selectedCampaign) return;

    setPdfLoading(true);
    
    // DOM 업데이트를 위해 잠시 대기
    await new Promise(resolve => setTimeout(resolve, 100));
    
    try {
      const reportElement = document.getElementById('report-content');
      if (!reportElement) {
        alert('보고서 콘텐츠를 찾을 수 없습니다.');
        return;
      }

      // 버튼 컨테이너를 강제로 숨기기
      const buttonContainer = reportElement.querySelector('[style*="display: none"]');
      if (buttonContainer) {
        (buttonContainer as HTMLElement).style.display = 'none !important';
        (buttonContainer as HTMLElement).style.visibility = 'hidden';
      }

      // html2canvas로 페이지를 이미지로 변환
      const canvas = await html2canvas(reportElement, {
        scale: 1.5,
        useCORS: true,
        allowTaint: false,
        backgroundColor: '#ffffff',
        scrollY: -window.scrollY,
        windowWidth: 1200,
        windowHeight: Math.max(reportElement.scrollHeight + 100, 1000)
      });

      // PDF 생성
      const pdf = new jsPDF('p', 'mm', 'a4');
      const imgData = canvas.toDataURL('image/png');
      
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      const imgWidth = pdfWidth - 20; // 좌우 여백 10mm씩
      const imgHeight = (canvas.height * imgWidth) / canvas.width;

      // 페이지가 여러 개 필요한 경우 처리
      if (imgHeight <= pdfHeight - 20) {
        // 한 페이지에 들어가는 경우
        pdf.addImage(imgData, 'PNG', 10, 10, imgWidth, imgHeight, '', 'FAST');
      } else {
        // 여러 페이지가 필요한 경우
        let remainingHeight = imgHeight;
        let yPosition = 0;
        let pageNumber = 1;
        const pages = Math.ceil(imgHeight / (pdfHeight - 20));

        while (remainingHeight > 0) {
          const currentPageHeight = Math.min(remainingHeight, pdfHeight - 20);
          
          if (pageNumber > 1) {
            pdf.addPage();
          }
          
          pdf.addImage(imgData, 'PNG', 10, 10 - yPosition, imgWidth, imgHeight, '', 'FAST');
          
          // 페이지 번호 추가
          if (pages > 1) {
            pdf.setFontSize(10);
            pdf.text(`${pageNumber} / ${pages}`, pdfWidth - 20, pdfHeight - 5);
          }
          
          remainingHeight -= currentPageHeight;
          yPosition += currentPageHeight;
          pageNumber++;
        }
      }

      // PDF 다운로드
      const fileName = `인스타그램_릴스_보고서_${selectedCampaign}_${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(fileName);
      
    } catch (error) {
      console.error('PDF 생성 중 오류:', error);
      alert('PDF 생성 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setPdfLoading(false);
    }
  };

  const chartData = reportData?.reels ? (() => {
    const uniqueAccounts = Array.from(new Set((reportData.reels || []).map(r => r.username)));
    
    // 날짜 데이터 수집 및 정렬
    const dateMap = new Map<string, Date>();
    reportData.reels.forEach(r => {
      const date = r.collection_date || r.posted_at;
      if (date) {
        const dateObj = new Date(date);
        const dateStr = dateObj.toLocaleDateString('ko-KR');
        dateMap.set(dateStr, dateObj);
      }
    });
    
    // 날짜 객체를 정렬한 후 표시용 문자열 생성
    const allDates = Array.from(dateMap.entries())
      .sort(([, a], [, b]) => a.getTime() - b.getTime())
      .map(([dateStr]) => dateStr);
    
    const colors = [
      { border: '#e74c3c', background: 'rgba(231, 76, 60, 0.1)' },
      { border: '#3498db', background: 'rgba(52, 152, 219, 0.1)' },
      { border: '#2ecc71', background: 'rgba(46, 204, 113, 0.1)' },
      { border: '#f39c12', background: 'rgba(243, 156, 18, 0.1)' },
      { border: '#9b59b6', background: 'rgba(155, 89, 182, 0.1)' },
      { border: '#1abc9c', background: 'rgba(26, 188, 156, 0.1)' },
      { border: '#34495e', background: 'rgba(52, 73, 94, 0.1)' },
      { border: '#e67e22', background: 'rgba(230, 126, 34, 0.1)' }
    ];

    const datasets = uniqueAccounts.map((username, index) => {
      const accountReels = reportData.reels.filter(r => r.username === username);
      const data = allDates.map(date => {
        const reel = accountReels.find(r => {
          const reelDate = r.collection_date || r.posted_at;
          return reelDate ? new Date(reelDate).toLocaleDateString('ko-KR') === date : false;
        });
        return reel ? reel.video_view_count : 0;
      });
      
      const color = colors[index % colors.length];
      return {
        label: `@${username}`,
        data,
        borderColor: color.border,
        backgroundColor: color.background,
        tension: 0.4
      };
    });

    return {
      labels: allDates,
      datasets
    };
  })() : null;

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: '계정별 시간대별 비디오 조회수 추이'
      }
    },
    scales: {
      y: {
        beginAtZero: true
      }
    }
  };

  if (loading && campaigns.length === 0) {
    return <Loading>캠페인 정보를 불러오는 중...</Loading>;
  }

  if (error && campaigns.length === 0) {
    return (
      <Container>
        <Header>
          <Title>인스타그램 캠페인 보고서</Title>
          <ErrorMessage>{error}</ErrorMessage>
        </Header>
      </Container>
    );
  }

  if (campaigns.length === 0) {
    return (
      <Container>
        <Header>
          <Title>인스타그램 캠페인 보고서</Title>
          <NoDataMessage>
            <h3>현재 사용 가능한 인스타그램 캠페인이 없습니다</h3>
            <p>새 캠페인을 생성하고 데이터를 수집한 후 다시 확인해주세요.</p>
          </NoDataMessage>
        </Header>
      </Container>
    );
  }

  return (
    <Container id="report-content">
      <TopControls>
        <ControlsLeft>
          {!campaignName && (
            <CampaignSelector
              value={selectedCampaign}
              onChange={(e) => handleCampaignChange(e.target.value)}
            >
              {(campaigns || []).map(campaign => (
                <option key={campaign.id} value={campaign.name}>
                  {campaign.name}
                </option>
              ))}
            </CampaignSelector>
          )}
        </ControlsLeft>
        <ControlsRight>
          {!campaignName && (
            <>
              <ShareButton onClick={() => handleShare()}>
                📤 보고서 공유
              </ShareButton>
              <PDFButton 
                onClick={() => handlePDFDownload()} 
                disabled={pdfLoading}
              >
                {pdfLoading ? '📄 PDF 생성 중..' : '📄 PDF 다운로드'}
              </PDFButton>
            </>
          )}
        </ControlsRight>
      </TopControls>

      <Header>
        <TitleRow>
          <Title>인스타그램 캠페인 보고서</Title>
        </TitleRow>

        {reportData && (() => {
          // 전체 조회수 계산 (최신 기준)
          const totalViews = reportData.reels.reduce((sum, reel) => sum + (reel.video_view_count || 0), 0);
          
          // CPV 계산 (광고비 / 전체 조회수)
          const budget = reportData.campaign.budget || 0;
          const cpv = totalViews > 0 ? budget / totalViews : 0;
          
          return (
            <CampaignInfo>
              <InfoRow className="top-row">
                <InfoCard>
                  <InfoLabel>캠페인명</InfoLabel>
                  <InfoValue>{reportData.campaign.name}</InfoValue>
                </InfoCard>
                <InfoCard>
                  <InfoLabel>제품</InfoLabel>
                  <InfoValue>{reportData.campaign.product}</InfoValue>
                </InfoCard>
                <InfoCard>
                  <InfoLabel>기간</InfoLabel>
                  <InfoValue>
                    {new Date(reportData.campaign.start_date).toLocaleDateString()} ~{' '}
                    {new Date(reportData.campaign.end_date).toLocaleDateString()}
                  </InfoValue>
                </InfoCard>
              </InfoRow>
              <InfoRow className="bottom-row">
                <InfoCard>
                  <InfoLabel>총 릴스 수</InfoLabel>
                  <InfoValue>{reportData.unique_reel_count || reportData.reels.length}</InfoValue>
                </InfoCard>
                <InfoCard>
                  <InfoLabel>광고비</InfoLabel>
                  <InfoValue>{budget.toLocaleString()}원</InfoValue>
                </InfoCard>
                <InfoCard>
                  <InfoLabel>전체 조회수</InfoLabel>
                  <InfoValue>{totalViews.toLocaleString()}회</InfoValue>
                </InfoCard>
                <InfoCard>
                  <InfoLabel>CPV</InfoLabel>
                  <InfoValue>{cpv.toFixed(2)}원</InfoValue>
                </InfoCard>
              </InfoRow>
            </CampaignInfo>
          );
        })()}

        {error && (
          <ErrorMessage>{error}</ErrorMessage>
        )}
      </Header>

      {reportData && reportData.reels && reportData.reels.length > 0 && (
        <TableContainer>
          <Table>
            <TableHeader>
              <HeaderRow>
                <HeaderCell className="image-column">이미지</HeaderCell>
                <HeaderCell className="user-column">사용자</HeaderCell>
                <HeaderCell className="view-column">조회수</HeaderCell>
                <HeaderCell className="meta-column">구독 동기</HeaderCell>
                <HeaderCell className="meta-column">카테고리</HeaderCell>
                <HeaderCell className="meta-column">등록일</HeaderCell>
              </HeaderRow>
            </TableHeader>
            <TableBody>
              {reportData.reels.map(reel => {
                  const gradeValue = getAnalysisValue(reel.grade);
                  return (
                    <TableRow key={reel.id}>
                      <TableCell className="image-cell">
                        {reel.s3_thumbnail_url && (
                          <ReelImage 
                            src={reel.s3_thumbnail_url} 
                            alt={`${reel.username} reel`}
                            onClick={() => window.open(reel.campaign_url, '_blank')}
                          />
                        )}
                      </TableCell>
                      <TableCell>
                      <UserInfo>
                        <Username>
                          @{reel.username}
                          <Grade grade={gradeValue}>{gradeValue}</Grade>
                        </Username>
                        {reel.display_name && reel.display_name !== reel.username && (
                          <DisplayName>{reel.display_name}</DisplayName>
                        )}
                        <FollowerCount>
                          팔로워: {reel.follower_count?.toLocaleString() || 'N/A'}
                        </FollowerCount>
                        {reel.grade_avg_views && (
                          <AvgViewCount>
                            조회수 평균: {Math.round(reel.grade_avg_views).toLocaleString()}
                          </AvgViewCount>
                        )}
                      </UserInfo>
                    </TableCell>
                      <TableCell>
                        <ViewCount>{reel.video_view_count.toLocaleString()}</ViewCount>
                      </TableCell>
                      <TableCell>
                        <MetaInfo>{getAnalysisValue(reel.subscription_motivation)}</MetaInfo>
                      </TableCell>
                      <TableCell>
                        <MetaInfo>{getAnalysisValue(reel.category)}</MetaInfo>
                      </TableCell>
                      <TableCell>
                        <MetaInfo>
                          {reel.posted_at ? new Date(reel.posted_at).toLocaleDateString() : 'N/A'}
                        </MetaInfo>
                      </TableCell>
                    </TableRow>
                  );
                })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {reportData && reportData.reels && reportData.reels.length > 0 && reportData.chart_data_by_reel && (() => {
        // 계정별 카운트 관리
        const usernameCount: { [key: string]: number } = {};
        const usernameOccurrence: { [key: string]: number } = {};
        
        // 각 계정이 몇 개씩 있는지 카운트
        Object.entries(reportData.chart_data_by_reel).forEach(([reelUrl]) => {
          const reel = reportData.reels.find(r => r.reel_url === reelUrl || r.campaign_url === reelUrl);
          if (reel && reel.username) {
            usernameCount[reel.username] = (usernameCount[reel.username] || 0) + 1;
          }
        });
        
        // 차상 팔레트
        const colors = [
          '#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', 
          '#1abc9c', '#34495e', '#e67e22', '#95a5a6', '#d35400'
        ];
        
        // 모든 날짜 수집 (모든 릴스의 날짜 수집함) - yyyy-mm-dd 형식으로 변환
        const allDatesSet = new Set<string>();
        Object.values(reportData.chart_data_by_reel).forEach((chartInfo: any) => {
          chartInfo.labels.forEach((date: string) => {
            // yyyy-mm-dd 형식으로 변환 (시간 부분 제거)
            const dateOnly = date.split(' ')[0];
            allDatesSet.add(dateOnly);
          });
        });
        const allDates = Array.from(allDatesSet).sort();
        
        // 각 릴스를 데이터셋으로 변환
        const datasets = Object.entries(reportData.chart_data_by_reel).map(([reelUrl, chartInfo]: [string, any], index) => {
          const reel = reportData.reels.find(r => r.reel_url === reelUrl || r.campaign_url === reelUrl);
          let label = reelUrl;
          
          if (reel && reel.username) {
            // 같은 계정이 여러 개인 경우 번호 추가
            if (usernameCount[reel.username] > 1) {
              usernameOccurrence[reel.username] = (usernameOccurrence[reel.username] || 0) + 1;
              const suffix = String(usernameOccurrence[reel.username]).padStart(2, '0');
              label = `@${reel.username}_${suffix}`;
            } else {
              label = `@${reel.username}`;
            }
          }
          
          // 날짜별 데이터 매핑 (없는 날짜는 null)
          const dataMap: { [key: string]: number } = {};
          chartInfo.labels.forEach((date: string, i: number) => {
            // yyyy-mm-dd 형식으로 변환
            const dateOnly = date.split(' ')[0];
            // 같은 날짜의 여러 값이 있으면 합산
            dataMap[dateOnly] = (dataMap[dateOnly] || 0) + chartInfo.data[i];
          });
          
          const data = allDates.map(date => dataMap[date] || null);
          
          return {
            label: label,
            data: data,
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length].replace(')', ', 0.1)').replace('rgb', 'rgba'),
            tension: 0.1,
            spanGaps: true
          };
        });
        
        const unifiedChartData = {
          labels: allDates,
          datasets: datasets
        };
        
        return (
          <ChartSection>
            <h2>릴스별 시간대별 조회수 추이</h2>
            <Line data={unifiedChartData} options={chartOptions} />
          </ChartSection>
        );
      })()}

      {reportData && (!reportData.reels || reportData.reels.length === 0) && !error && (
        <NoDataMessage>
          <h3>아직 데이터 수집이 필요합니다</h3>
          <p>이 캠페인에 대한 인스타그램 릴스 데이터가 아직 수집되지 않았습니다.<br/>
             관리자 페이지에서 데이터 수집을 진행하거나, 자동 수집이 완료될 때까지 기다려주세요.</p>
        </NoDataMessage>
      )}
    </Container>
  );
};

export default InstagramReelReport;
