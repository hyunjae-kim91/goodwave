import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { useParams } from 'react-router-dom';
import { reportsApi } from '../../services/api';
import { BlogReport as BlogReportType, Campaign } from '../../types';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

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
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr !important;
  }
`;

const InfoCard = styled.div`
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  text-align: center;
`;

const InfoLabel = styled.div`
  color: #6c757d;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
`;

const InfoValue = styled.div`
  color: #2c3e50;
  font-weight: 600;
  font-size: 1.1rem;
`;

const TableContainer = styled.div`
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow-x: auto;
`;

const Table = styled.table`
  width: 100%;
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
  min-width: 120px;

  &.url-column {
    min-width: 200px;
    max-width: 300px;
  }

  &.date-column {
    min-width: 100px;
    font-size: 0.8rem;
    text-align: center;
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

  &.url-cell {
    max-width: 300px;
    word-break: break-all;
  }

  &.ranking-cell {
    text-align: center;
    font-size: 0.9rem;
    
    &.has-ranking {
      background-color: #d4edda;
      color: #155724;
      font-weight: 600;
    }
  }
`;

const BlogURL = styled.a`
  color: #3498db;
  text-decoration: none;
  font-size: 0.9rem;
  
  &:hover {
    text-decoration: underline;
  }
`;

const StatsSection = styled.div`
  display: flex;
  gap: 1rem;
  margin-bottom: 0.5rem;
`;

const StatItem = styled.div`
  background: #e3f2fd;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #1976d2;
`;

const PostingDate = styled.div`
  font-size: 0.8rem;
  color: #6c757d;
`;

const Loading = styled.div`
  text-align: center;
  padding: 2rem;
  color: #7f8c8d;
`;

const NoData = styled.div`
  text-align: center;
  padding: 3rem;
  color: #6c757d;
  font-size: 1.1rem;
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

const BlogReport: React.FC = () => {
  const { campaignName } = useParams<{ campaignName?: string }>();
  const [reportData, setReportData] = useState<BlogReportType | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<string>('');
  const [loading, setLoading] = useState(true);
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
      const data = await reportsApi.getAvailableCampaigns();
      const blogCampaigns = data.filter(c => 
        c.campaign_type === 'blog' || c.campaign_type === 'all'
      );
      setCampaigns(blogCampaigns);
      
      if (blogCampaigns.length > 0 && !selectedCampaign && !campaignName) {
        setSelectedCampaign(blogCampaigns[0].name);
      }
    } catch (error) {
      console.error('Error fetching campaigns:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchReportData = async (campaignName: string) => {
    try {
      setLoading(true);
      const data = await reportsApi.getBlogReport(campaignName);
      setReportData(data);
    } catch (error) {
      console.error('Error fetching report data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCampaignChange = (campaignName: string) => {
    setSelectedCampaign(campaignName);
  };

  const handleShare = () => {
    if (!selectedCampaign) return;
    
    // 캠페인 이름 정규화 (탭, 줄바꿈, 공백 제거)
    const normalizedCampaignName = selectedCampaign.trim().replace(/\t/g, '').replace(/\n/g, '').replace(/\r/g, '');
    const shareUrl = `${window.location.origin}/#/reports/blogs/${encodeURIComponent(normalizedCampaignName)}`;
    
    // 클립보드 API 사용 가능 여부 확인
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(shareUrl).then(() => {
        alert('보고서 링크가 클립보드에 복사되었습니다!');
      }).catch(() => {
        // 클립보드 복사가 실패한 경우 URL을 표시
        prompt('보고서 링크를 복사하세요:', shareUrl);
      });
    } else {
      // 클립보드 API를 지원하지 않는 경우 직접 URL 표시
      prompt('보고서 링크를 복사하세요:', shareUrl);
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
      const fileName = `네이버_블로그_보고서_${selectedCampaign}_${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(fileName);
      
    } catch (error) {
      console.error('PDF 생성 중 오류:', error);
      alert('PDF 생성 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setPdfLoading(false);
    }
  };

  if (loading && campaigns.length === 0) {
    return <Loading>캠페인 정보를 불러오는 중...</Loading>;
  }

  if (campaigns.length === 0) {
    return <Container><Header><Title>블로그 보고서</Title><p>사용 가능한 블로그 캠페인이 없습니다.</p></Header></Container>;
  }

  if (!reportData || reportData.blogs.length === 0) {
    return (
      <Container>
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
        </TopControls>
        <Header>
          <TitleRow>
            <Title>네이버 블로그 보고서</Title>
          </TitleRow>
        </Header>
        <NoData>선택한 캠페인에 대한 블로그 데이터가 없습니다.</NoData>
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
                {pdfLoading ? '📄 PDF 생성 중...' : '📄 PDF 다운로드'}
              </PDFButton>
            </>
          )}
        </ControlsRight>
      </TopControls>

      <Header>
        <TitleRow>
          <Title>네이버 블로그 보고서</Title>
        </TitleRow>

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
              <InfoLabel>총 블로그 수</InfoLabel>
              <InfoValue>{reportData.blogs.length}</InfoValue>
            </InfoCard>
            <InfoCard>
              <InfoLabel>광고비</InfoLabel>
              <InfoValue>{reportData.campaign.budget?.toLocaleString() || 0}원</InfoValue>
            </InfoCard>
          </InfoRow>
        </CampaignInfo>
      </Header>

      <TableContainer>
        <Table>
          <TableHeader>
            <HeaderRow>
              <HeaderCell>사용자</HeaderCell>
              <HeaderCell className="url-column">블로그 URL</HeaderCell>
              <HeaderCell>공감</HeaderCell>
              <HeaderCell>댓글</HeaderCell>
              {(reportData.date_columns || []).map(date => (
                <HeaderCell key={date} className="date-column">
                  {date}
                </HeaderCell>
              ))}
            </HeaderRow>
          </TableHeader>
          <TableBody>
            {(reportData.blogs || []).map((blog, index) => (
              <TableRow key={index}>
                <TableCell>
                  {blog.username || 'N/A'}
                </TableCell>
                <TableCell className="url-cell">
                  <BlogURL href={blog.url} target="_blank" rel="noopener noreferrer">
                    {blog.title || blog.url}
                  </BlogURL>
                </TableCell>
                <TableCell>
                  <StatItem>{blog.likes_count}</StatItem>
                </TableCell>
                <TableCell>
                  <StatItem>{blog.comments_count}</StatItem>
                </TableCell>
                {(reportData.date_columns || []).map(date => (
                  <TableCell 
                    key={date} 
                    className={`ranking-cell ${blog.rankings?.[date] ? 'has-ranking' : ''}`}
                  >
                    {blog.rankings?.[date] || '-'}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Container>
  );
};

export default BlogReport;