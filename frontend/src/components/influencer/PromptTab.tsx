import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { influencerApi } from '../../services/influencer/influencerApi';

const Container = styled.div`
  max-width: 1200px;
`;

const Title = styled.h1`
  color: #2c3e50;
  margin-bottom: 2rem;
  font-size: 1.5rem;
  font-weight: bold;
`;

const FormSection = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
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

const Textarea = styled.textarea`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1rem;
  resize: vertical;
  min-height: 400px;

  &:focus {
    outline: none;
    border-color: #3498db;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.25);
  }
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
  margin-right: 0.5rem;

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

const AlertMessage = styled.div<{ type: 'success' | 'error' }>`
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  background-color: ${props => props.type === 'success' ? '#d4edda' : '#f8d7da'};
  border: 1px solid ${props => props.type === 'success' ? '#c3e6cb' : '#f5c6cb'};
  color: ${props => props.type === 'success' ? '#155724' : '#721c24'};
`;

const FileControlsContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
`;

const FileNameContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 250px;
`;

const PromptTab: React.FC = () => {
  const [promptTypes, setPromptTypes] = useState<string[]>([]);
  const [name, setName] = useState('system_prompt');
  const [customName, setCustomName] = useState('');
  const [isCustomName, setIsCustomName] = useState(false);
  const [content, setContent] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const loadPromptByName = async (targetName: string) => {
    if (!targetName) {
      setContent('');
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const data = await influencerApi.getPrompt(targetName);
      setContent(data.content);
    } catch (e: any) {
      setContent('');
      setMessage({ type: 'error', text: e.message || '프롬프트 로드 실패' });
    } finally {
      setLoading(false);
    }
  };

  const fetchPromptTypes = async (): Promise<string[]> => {
    try {
      const types = await influencerApi.getPromptTypes();
      let uniqueTypes = Array.from(new Set(types));
      uniqueTypes.sort();
      if (uniqueTypes.includes('system_prompt')) {
        uniqueTypes = ['system_prompt', ...uniqueTypes.filter(type => type !== 'system_prompt')];
      }
      setPromptTypes(uniqueTypes);
      return uniqueTypes;
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message || '프롬프트 목록을 불러오지 못했습니다.' });
      return [];
    }
  };

  useEffect(() => {
    const init = async () => {
      const types = await fetchPromptTypes();
      const initialName = types.includes('system_prompt') ? 'system_prompt' : types[0] ?? 'system_prompt';
      setIsCustomName(false);
      setName(initialName);
    };
    void init();
  }, []);

  useEffect(() => {
    if (!isCustomName && name) {
      void loadPromptByName(name);
    }
  }, [name, isCustomName]);

  const handleManualLoad = () => {
    const target = (isCustomName ? customName : name).trim();
    if (!target) {
      setMessage({ type: 'error', text: '파일 이름을 입력해주세요.' });
      return;
    }
    void loadPromptByName(target);
  };

  const save = async () => {
    if (!content.trim()) {
      setMessage({ type: 'error', text: '프롬프트 내용을 입력해주세요.' });
      return;
    }

    const targetName = (isCustomName ? customName : name).trim();
    if (!targetName) {
      setMessage({ type: 'error', text: '파일 이름을 입력해주세요.' });
      return;
    }

    setLoading(true);
    setMessage(null);
    try {
      const res = await influencerApi.savePrompt(targetName, content);
      setMessage({ type: 'success', text: res.message });
      const updatedTypes = await fetchPromptTypes();
      if (!updatedTypes.includes(targetName)) {
        setPromptTypes([...updatedTypes, targetName]);
      }
      setIsCustomName(false);
      setName(targetName);
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message || '프롬프트 저장 실패' });
    } finally {
      setLoading(false);
    }
  };

  const handlePromptSelectionChange = (value: string) => {
    if (value === '__custom__') {
      setIsCustomName(true);
      setCustomName('');
      setContent('');
      setMessage(null);
    } else {
      setIsCustomName(false);
      setName(value);
    }
  };

  return (
    <Container>
      <Title>프롬프트 관리</Title>

      {message && (
        <AlertMessage type={message.type}>
          {message.text}
        </AlertMessage>
      )}

      <FormSection>
        <FileControlsContainer>
          <FileNameContainer>
            <Label>파일 이름:</Label>
            <Select
              value={isCustomName ? '__custom__' : name}
              onChange={(event) => handlePromptSelectionChange(event.target.value)}
            >
              {(promptTypes || []).map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
              <option value="__custom__">새 프롬프트 추가...</option>
            </Select>
          </FileNameContainer>
          {isCustomName && (
            <FileNameContainer>
              <Label style={{ marginBottom: 0 }}>새 파일 이름</Label>
              <Input
                type="text"
                value={customName}
                onChange={(event) => setCustomName(event.target.value)}
                placeholder="새 프롬프트 파일명을 입력하세요"
              />
            </FileNameContainer>
          )}
          <SecondaryButton onClick={handleManualLoad} disabled={loading}>
            {loading ? '로딩...' : '불러오기'}
          </SecondaryButton>
        </FileControlsContainer>

        <FormGroup>
          <Label>프롬프트 내용</Label>
          <Textarea
            placeholder="프롬프트 내용을 입력하세요..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </FormGroup>

        <Button
          onClick={save}
          disabled={loading}
        >
          {loading ? '저장 중...' : '저장'}
        </Button>
      </FormSection>
    </Container>
  );
};

export default PromptTab;
