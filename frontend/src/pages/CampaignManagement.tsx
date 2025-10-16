import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { campaignsApi } from '../services/api';
import { Campaign, CampaignCreate, CampaignUpdate, CampaignURLCreate, CampaignURLUpdatePayload } from '../types';

const CAMPAIGN_TYPE_OPTIONS = [
  { value: 'instagram_post', label: '인스타그램 캠페인' },
  { value: 'blog', label: '네이버 블로그' }
] as const;

const CAMPAIGN_TYPE_LABELS = CAMPAIGN_TYPE_OPTIONS.reduce<Record<string, string>>((acc, option) => {
  acc[option.value] = option.label;
  return acc;
}, {
  instagram_reel: '인스타그램 릴스',
  all: '전체',
});

type EditCampaignURL = {
  id: number;
  url: string;
  channel: string;
};

type EditFormField = 'budget' | 'product' | 'startDate' | 'endDate';

type EditFormState = {
  budget: string;
  product: string;
  startDate: string;
  endDate: string;
  urls: EditCampaignURL[];
};

const toDateInputValue = (isoDate: string): string => {
  if (!isoDate) {
    return '';
  }
  const [datePart] = isoDate.split('T');
  return datePart || '';
};

const Container = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const Title = styled.h1`
  color: #2c3e50;
  margin-bottom: 2rem;
`;

const FormSection = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
`;

const FormGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
`;

const FormGroup = styled.div`
  margin-bottom: 1rem;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #495057;
`;

const Input = styled.input`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1rem;

  &:focus {
    outline: none;
    border-color: #3498db;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.25);
  }
`;

const Select = styled.select`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1rem;
  background-color: white;

  &:focus {
    outline: none;
    border-color: #3498db;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.25);
  }
`;

const URLSection = styled.div`
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
`;

const URLItem = styled.div`
  display: grid;
  grid-template-columns: 1fr 150px 100px;
  gap: 1rem;
  margin-bottom: 1rem;
  align-items: center;
`;

const Button = styled.button`
  padding: 0.75rem 1.5rem;
  background-color: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;

  &:hover {
    background-color: #2980b9;
  }

  &:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
  }
`;

const SecondaryButton = styled(Button)`
  background-color: #95a5a6;
  
  &:hover {
    background-color: #7f8c8d;
  }
`;

const DangerButton = styled(Button)`
  background-color: #e74c3c;
  
  &:hover {
    background-color: #c0392b;
  }
`;

const CampaignList = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
`;

const CampaignCard = styled.div`
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 1.5rem;
  margin-bottom: 1rem;
`;

const CampaignHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
`;

const ActionButtons = styled.div`
  display: flex;
  gap: 0.5rem;
  align-items: center;
`;

const CampaignTitle = styled.h3`
  color: #2c3e50;
  margin: 0;
  flex: 1;
`;

const CampaignInfo = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
`;

const CampaignURLSection = styled.div`
  margin-bottom: 1rem;
`;

const URLSectionTitle = styled.div`
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.5rem;
`;

const URLList = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`;

const URLListItem = styled.li`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  background: #f8f9fa;
  padding: 0.75rem;
  border-radius: 4px;
  word-break: break-all;
`;

const URLChannel = styled.span`
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  background: #e9ecef;
  color: #495057;
  font-size: 0.75rem;
  font-weight: 600;
`;

const InfoItem = styled.div`
  color: #6c757d;
  font-size: 0.9rem;
`;

const EditSection = styled.div`
  border-top: 1px solid #e9ecef;
  margin-top: 1rem;
  padding-top: 1rem;
`;

const EditURLSection = styled.div`
  margin-top: 1rem;
`;

const EditURLItem = styled.div`
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1rem;
  align-items: center;
  margin-bottom: 0.75rem;
`;

const EditButtonGroup = styled.div`
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  flex-wrap: wrap;
`;

const CampaignManagement: React.FC = () => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<CampaignCreate>({
    name: '',
    campaign_type: CAMPAIGN_TYPE_OPTIONS[0].value,
    budget: 0,
    start_date: '',
    end_date: '',
    product: '',
    urls: [{ url: '', channel: CAMPAIGN_TYPE_OPTIONS[0].value }]
  });
  const [editingCampaignId, setEditingCampaignId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<EditFormState | null>(null);
  const [updatingCampaignId, setUpdatingCampaignId] = useState<number | null>(null);

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    try {
      setLoading(true);
      const data = await campaignsApi.getAll();
      setCampaigns(data);
    } catch (error) {
      console.error('Error fetching campaigns:', error);
    } finally {
      setLoading(false);
    }
  };

  const cancelEdit = () => {
    setEditingCampaignId(null);
    setEditForm(null);
  };

  const startEditingCampaign = (campaign: Campaign) => {
    if (editingCampaignId === campaign.id) {
      cancelEdit();
      return;
    }

    setEditingCampaignId(campaign.id);
    setEditForm({
      budget: campaign.budget !== undefined ? String(campaign.budget) : '',
      product: campaign.product || '',
      startDate: toDateInputValue(campaign.start_date),
      endDate: toDateInputValue(campaign.end_date),
      urls: (campaign.campaign_urls || []).map(url => ({
        id: url.id,
        url: url.url,
        channel: url.channel,
      })),
    });
  };

  const handleEditFormChange = (field: EditFormField, value: string) => {
    setEditForm(prev => (prev ? { ...prev, [field]: value } : prev));
  };

  const handleEditUrlChange = (index: number, value: string) => {
    setEditForm(prev => {
      if (!prev) {
        return prev;
      }
      const updatedUrls = prev.urls.map((url, i) =>
        i === index ? { ...url, url: value } : url
      );
      return { ...prev, urls: updatedUrls };
    });
  };

  const handleUpdateCampaign = async () => {
    if (!editingCampaignId || !editForm) {
      return;
    }

    const trimmedProduct = editForm.product.trim();
    if (!trimmedProduct) {
      alert('제품명을 입력해주세요.');
      return;
    }

    if (!editForm.startDate || !editForm.endDate) {
      alert('캠페인 시작일과 종료일을 입력해주세요.');
      return;
    }

    if (new Date(editForm.startDate) >= new Date(editForm.endDate)) {
      alert('시작일은 종료일보다 이전이어야 합니다.');
      return;
    }

    if (editForm.budget.trim() === '') {
      alert('예산을 입력해주세요.');
      return;
    }

    const budgetValue = Number(editForm.budget);
    if (Number.isNaN(budgetValue) || budgetValue < 0) {
      alert('올바른 예산 값을 입력해주세요.');
      return;
    }

    const trimmedUrls = (editForm.urls || []).map(url => ({
      ...url,
      url: url.url.trim(),
    }));

    if (trimmedUrls.some(url => !url.url)) {
      alert('캠페인 URL을 입력해주세요.');
      return;
    }

    const urlPayload: CampaignURLUpdatePayload[] = trimmedUrls.map(url => ({
      id: url.id,
      url: url.url,
      channel: url.channel,
    }));

    const payload: CampaignUpdate = {
      budget: budgetValue,
      product: trimmedProduct,
      start_date: `${editForm.startDate}T09:00:00`,
      end_date: `${editForm.endDate}T23:59:59`,
      urls: urlPayload.length > 0 ? urlPayload : undefined,
    };

    try {
      setUpdatingCampaignId(editingCampaignId);
      await campaignsApi.update(editingCampaignId, payload);
      await fetchCampaigns();
      alert('캠페인이 수정되었습니다.');
      cancelEdit();
    } catch (error: any) {
      console.error('Error updating campaign:', error);
      const errorMessage = error.response?.data?.detail || error.message || '캠페인 수정에 실패했습니다.';
      alert(`캠페인 수정에 실패했습니다.\n에러: ${errorMessage}`);
    } finally {
      setUpdatingCampaignId(null);
    }
  };

  const handleInputChange = (field: keyof CampaignCreate, value: any) => {
    setFormData(prev => {
      if (field === 'campaign_type') {
        return {
          ...prev,
          campaign_type: value,
          urls: (prev.urls || []).map(url => ({ ...url, channel: value }))
        };
      }
      return { ...prev, [field]: value };
    });
  };

  const handleURLChange = (index: number, field: keyof CampaignURLCreate, value: string) => {
    setFormData(prev => ({
      ...prev,
      urls: (prev.urls || []).map((url, i) => 
        i === index ? { ...url, [field]: value } : url
      )
    }));
  };

  const addURLField = () => {
    setFormData(prev => ({
      ...prev,
      urls: [...prev.urls, { url: '', channel: prev.campaign_type }]
    }));
  };

  const removeURLField = (index: number) => {
    if (formData.urls.length > 1) {
      setFormData(prev => ({
        ...prev,
        urls: prev.urls.filter((_, i) => i !== index)
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // 유효성 검사
    if (!formData.name.trim()) {
      alert('캠페인 이름을 입력해주세요.');
      return;
    }
    
    if (!formData.start_date || !formData.end_date) {
      alert('캠페인 시작일과 종료일을 입력해주세요.');
      return;
    }
    
    if (new Date(formData.start_date) >= new Date(formData.end_date)) {
      alert('시작일은 종료일보다 이전이어야 합니다.');
      return;
    }
    
    if (formData.urls.some(url => !url.url.trim())) {
      alert('모든 URL을 입력해주세요.');
      return;
    }
    
    try {
      setLoading(true);
      
      // date 입력을 datetime으로 변환 (오전 9시로 설정)
      const formattedData = {
        ...formData,
        start_date: formData.start_date ? formData.start_date + 'T09:00:00' : '',
        end_date: formData.end_date ? formData.end_date + 'T23:59:59' : ''
      };
      
      await campaignsApi.create(formattedData);
      await fetchCampaigns();
      
      // Reset form
      setFormData({
        name: '',
        campaign_type: CAMPAIGN_TYPE_OPTIONS[0].value,
        budget: 0,
        start_date: '',
        end_date: '',
        product: '',
        urls: [{ url: '', channel: CAMPAIGN_TYPE_OPTIONS[0].value }]
      });
      
      alert('캠페인이 성공적으로 생성되었습니다.');
    } catch (error: any) {
      console.error('Error creating campaign:', error);
      const errorMessage = error.response?.data?.detail || error.message || '캠페인 생성에 실패했습니다.';
      alert(`캠페인 생성에 실패했습니다.\n에러: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCampaign = async (id: number, name: string) => {
    if (window.confirm(`"${name}" 캠페인을 삭제하시겠습니까?`)) {
      try {
        await campaignsApi.delete(id);
        await fetchCampaigns();
        if (editingCampaignId === id) {
          cancelEdit();
        }
        alert('캠페인이 삭제되었습니다.');
      } catch (error) {
        console.error('Error deleting campaign:', error);
        alert('캠페인 삭제에 실패했습니다.');
      }
    }
  };

  return (
    <Container>
      <Title>캠페인 관리</Title>
      
      <FormSection>
        <h2>새 캠페인 생성</h2>
        <form onSubmit={handleSubmit}>
          <FormGrid>
            <FormGroup>
              <Label>캠페인 이름</Label>
              <Input
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                required
              />
            </FormGroup>
            
            <FormGroup>
              <Label>캠페인 유형</Label>
                <Select
                  value={formData.campaign_type}
                  onChange={(e) => handleInputChange('campaign_type', e.target.value)}
                  required
                >
                  {CAMPAIGN_TYPE_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
            </FormGroup>
            
            <FormGroup>
              <Label>광고비 (원)</Label>
              <Input
                type="number"
                value={formData.budget}
                onChange={(e) => handleInputChange('budget', parseFloat(e.target.value))}
                required
              />
            </FormGroup>
            
            <FormGroup>
              <Label>제품명</Label>
              <Input
                type="text"
                value={formData.product}
                onChange={(e) => handleInputChange('product', e.target.value)}
                required
              />
            </FormGroup>
            
            <FormGroup>
              <Label>시작날짜</Label>
              <Input
                type="date"
                value={formData.start_date}
                onChange={(e) => handleInputChange('start_date', e.target.value)}
                required
              />
            </FormGroup>
            
            <FormGroup>
              <Label>종료날짜</Label>
              <Input
                type="date"
                value={formData.end_date}
                onChange={(e) => handleInputChange('end_date', e.target.value)}
                required
              />
            </FormGroup>
          </FormGrid>
          
          <URLSection>
            <h3>캠페인 URL</h3>
            {(formData.urls || []).map((urlItem, index) => (
              <URLItem key={index}>
                <Input
                  type="url"
                  placeholder="URL을 입력하세요"
                  value={urlItem.url}
                  onChange={(e) => handleURLChange(index, 'url', e.target.value)}
                  required
                />
                <Select
                  value={urlItem.channel}
                  onChange={(e) => handleURLChange(index, 'channel', e.target.value)}
                >
                  {CAMPAIGN_TYPE_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
                <DangerButton
                  type="button"
                  onClick={() => removeURLField(index)}
                  disabled={formData.urls.length === 1}
                >
                  삭제
                </DangerButton>
              </URLItem>
            ))}
            <SecondaryButton type="button" onClick={addURLField}>
              URL 추가
            </SecondaryButton>
          </URLSection>
          
          <Button type="submit" disabled={loading}>
            {loading ? '생성 중...' : '캠페인 생성'}
          </Button>
        </form>
      </FormSection>
      
      <CampaignList>
        <h2>등록된 캠페인</h2>
        {(campaigns || []).map(campaign => (
          <CampaignCard key={campaign.id}>
            <CampaignHeader>
              <CampaignTitle>{campaign.name}</CampaignTitle>
              <ActionButtons>
                <SecondaryButton
                  type="button"
                  onClick={() => startEditingCampaign(campaign)}
                  disabled={updatingCampaignId === campaign.id}
                >
                  {editingCampaignId === campaign.id ? '수정 취소' : '수정'}
                </SecondaryButton>
                <DangerButton
                  type="button"
                  onClick={() => handleDeleteCampaign(campaign.id, campaign.name)}
                  disabled={updatingCampaignId === campaign.id}
                >
                  삭제
                </DangerButton>
              </ActionButtons>
            </CampaignHeader>
            <CampaignInfo>
              <InfoItem><strong>유형:</strong> {CAMPAIGN_TYPE_LABELS[campaign.campaign_type] || campaign.campaign_type}</InfoItem>
              <InfoItem><strong>예산:</strong> {campaign.budget.toLocaleString()}원</InfoItem>
              <InfoItem><strong>제품:</strong> {campaign.product}</InfoItem>
              <InfoItem><strong>기간:</strong> {new Date(campaign.start_date).toLocaleDateString()} ~ {new Date(campaign.end_date).toLocaleDateString()}</InfoItem>
            </CampaignInfo>
            {(campaign.campaign_urls || []).length > 0 && (
              <CampaignURLSection>
                <URLSectionTitle>캠페인 URL</URLSectionTitle>
                <URLList>
                  {(campaign.campaign_urls || []).map(url => (
                    <URLListItem key={url.id}>
                      <span>{url.url}</span>
                      <URLChannel>{CAMPAIGN_TYPE_LABELS[url.channel] || url.channel}</URLChannel>
                    </URLListItem>
                  ))}
                </URLList>
              </CampaignURLSection>
            )}
            {editingCampaignId === campaign.id && editForm && (
              <EditSection>
                <FormGrid>
                  <FormGroup>
                    <Label>예산 (원)</Label>
                    <Input
                      type="number"
                      value={editForm.budget}
                      onChange={(e) => handleEditFormChange('budget', e.target.value)}
                      min="0"
                    />
                  </FormGroup>
                  <FormGroup>
                    <Label>제품명</Label>
                    <Input
                      type="text"
                      value={editForm.product}
                      onChange={(e) => handleEditFormChange('product', e.target.value)}
                    />
                  </FormGroup>
                  <FormGroup>
                    <Label>시작날짜</Label>
                    <Input
                      type="date"
                      value={editForm.startDate}
                      onChange={(e) => handleEditFormChange('startDate', e.target.value)}
                    />
                  </FormGroup>
                  <FormGroup>
                    <Label>종료날짜</Label>
                    <Input
                      type="date"
                      value={editForm.endDate}
                      onChange={(e) => handleEditFormChange('endDate', e.target.value)}
                    />
                  </FormGroup>
                </FormGrid>
                {editForm.urls && editForm.urls.length > 0 && (
                  <EditURLSection>
                    <Label>캠페인 URL</Label>
                    {editForm.urls.map((urlItem, index) => (
                      <EditURLItem key={urlItem.id}>
                        <Input
                          type="url"
                          value={urlItem.url}
                          onChange={(e) => handleEditUrlChange(index, e.target.value)}
                          required
                        />
                        <URLChannel>{CAMPAIGN_TYPE_LABELS[urlItem.channel] || urlItem.channel}</URLChannel>
                      </EditURLItem>
                    ))}
                  </EditURLSection>
                )}
                <EditButtonGroup>
                  <Button
                    type="button"
                    onClick={handleUpdateCampaign}
                    disabled={updatingCampaignId === campaign.id}
                  >
                    {updatingCampaignId === campaign.id ? '저장 중...' : '저장'}
                  </Button>
                  <SecondaryButton
                    type="button"
                    onClick={cancelEdit}
                    disabled={updatingCampaignId === campaign.id}
                  >
                    취소
                  </SecondaryButton>
                </EditButtonGroup>
              </EditSection>
            )}
          </CampaignCard>
        ))}
      </CampaignList>
    </Container>
  );
};

export default CampaignManagement;
