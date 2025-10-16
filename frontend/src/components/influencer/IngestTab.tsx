import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import styled from 'styled-components';
import toast from 'react-hot-toast';
import { Download, Loader2, CheckCircle, XCircle, Users, Activity, User, Video, RefreshCcw, Trash2 } from 'lucide-react';
import { useAppStore } from '../../store/influencer/useAppStore';
import { influencerApi } from '../../services/influencer/influencerApi';

const Section = styled.div`
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 1.5rem;
`;

const SectionTitle = styled.h2`
  color: #2c3e50;
  margin-bottom: 1rem;
  font-size: 1.25rem;
  font-weight: 600;
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

const TextArea = styled.textarea`
  width: 100%;
  min-height: 120px;
  padding: 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1rem;
  resize: vertical;

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
  display: flex;
  align-items: center;
  gap: 0.5rem;

  &:hover {
    background-color: #2980b9;
  }

  &:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
  }
`;

const InfoText = styled.p`
  color: #6c757d;
  margin-bottom: 1rem;
  font-size: 0.9rem;
`;

const OptionsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
`;

const OptionCard = styled.div<{ selected: boolean }>`
  border: 2px solid ${props => props.selected ? '#3498db' : '#e9ecef'};
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  background: ${props => props.selected ? '#f0f8ff' : 'white'};
  
  &:hover {
    border-color: #3498db;
    background: #f0f8ff;
  }
`;

const OptionHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
`;

const OptionTitle = styled.h3`
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
`;

const OptionDescription = styled.p`
  margin: 0;
  font-size: 0.875rem;
  color: #6c757d;
  line-height: 1.4;
`;

const ProgressDetailCard = styled.div`
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
`;

const ProgressDetailHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
`;

const ProgressDetailTitle = styled.h4`
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const ProgressDetailStatus = styled.span<{ status: 'pending' | 'running' | 'completed' | 'failed' }>`
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  
  ${props => {
    switch (props.status) {
      case 'pending':
        return 'background: #f8f9fa; color: #6c757d;';
      case 'running':
        return 'background: #fff3cd; color: #856404;';
      case 'completed':
        return 'background: #d4edda; color: #155724;';
      case 'failed':
        return 'background: #f8d7da; color: #721c24;';
      default:
        return 'background: #f8f9fa; color: #6c757d;';
    }
  }}
`;

const ProgressDetailBar = styled.div`
  background: #e9ecef;
  border-radius: 4px;
  height: 6px;
  overflow: hidden;
`;

const ProgressDetailFill = styled.div<{ percentage: number; status: 'pending' | 'running' | 'completed' | 'failed' }>`
  height: 100%;
  width: ${props => props.percentage}%;
  transition: width 0.3s ease;
  
  ${props => {
    switch (props.status) {
      case 'running':
        return 'background: #ffc107;';
      case 'completed':
        return 'background: #28a745;';
      case 'failed':
        return 'background: #dc3545;';
      default:
        return 'background: #6c757d;';
    }
  }}
`;

// 모달 스타일
const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background: white;
  border-radius: 8px;
  padding: 2rem;
  max-width: 800px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
`;

const ModalHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e9ecef;
`;

const ModalTitle = styled.h2`
  color: #2c3e50;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6c757d;
  padding: 0.25rem;
  
  &:hover {
    color: #495057;
  }
`;

const ProgressSection = styled.div`
  margin-bottom: 2rem;
`;

const ProgressBar = styled.div`
  background: #e9ecef;
  border-radius: 4px;
  height: 8px;
  margin-bottom: 1rem;
  overflow: hidden;
`;

const ProgressFill = styled.div<{ percentage: number }>`
  background: #3498db;
  height: 100%;
  width: ${props => props.percentage}%;
  transition: width 0.3s ease;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
`;

const LogContainer = styled.div`
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 1rem;
  height: 200px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.85rem;
  margin-bottom: 1rem;
`;

const LogEntry = styled.div`
  margin-bottom: 0.25rem;
  line-height: 1.4;
  color: #495057;
  
  &:last-child {
    margin-bottom: 0;
  }
`;

const CurrentStatus = styled.div`
  background: #e3f2fd;
  border: 1px solid #2196f3;
  border-radius: 4px;
  padding: 0.75rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #1976d2;
  font-weight: 500;
`;

const StatCard = styled.div`
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  text-align: center;
`;

const StatValue = styled.div`
  font-size: 1.5rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.25rem;
`;

const StatLabel = styled.div`
  font-size: 0.875rem;
  color: #6c757d;
`;

const ResultsList = styled.div`
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #e9ecef;
  border-radius: 4px;
`;

const ResultItem = styled.div<{ success: boolean }>`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-bottom: 1px solid #f8f9fa;
  
  &:last-child {
    border-bottom: none;
  }
  
  background: ${props => props.success ? '#d4edda' : '#f8d7da'};
`;

const ResultIcon = styled.div<{ success: boolean }>`
  color: ${props => props.success ? '#155724' : '#721c24'};
  display: flex;
  align-items: center;
`;

const ResultText = styled.div`
  flex: 1;
  font-size: 0.875rem;
`;

const ErrorText = styled.div`
  color: #dc3545;
  font-size: 0.75rem;
  margin-top: 0.25rem;
`;

const QueueHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
`;

const QueueControls = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: flex-end;
`;

const QueueFilterGroup = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #495057;
`;

const QueueFilterSelect = styled.select`
  padding: 0.35rem 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background: white;
  font-size: 0.875rem;
  color: #495057;

  &:focus {
    outline: none;
    border-color: #3498db;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.25);
  }
`;

const RefreshButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  background: white;
  border: 1px solid #ced4da;
  border-radius: 4px;
  color: #495057;
  cursor: pointer;

  &:hover {
    background: #f8f9fa;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const QueueActions = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
`;

const DeleteButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  background: #fff5f5;
  border: 1px solid #ff8787;
  border-radius: 4px;
  color: #c92a2a;
  cursor: pointer;

  &:hover {
    background: #ffe3e3;
  }

  &:disabled {
    background: #f8f9fa;
    border-color: #dee2e6;
    color: #adb5bd;
    cursor: not-allowed;
  }
`;

const CheckboxInput = styled.input.attrs({ type: 'checkbox' })`
  width: 1rem;
  height: 1rem;
  cursor: pointer;

  &:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }
`;

const SummaryGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
`;

const SummaryCard = styled.div`
  background: #f8f9fa;
  border-radius: 6px;
  padding: 0.9rem;
  border: 1px solid #edf2f6;
`;

const SummaryLabel = styled.div`
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #6c757d;
  margin-bottom: 0.25rem;
`;

const SummaryValue = styled.div`
  font-size: 1.25rem;
  font-weight: 600;
  color: #2c3e50;
`;

const QueueTableWrapper = styled.div`
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
`;

const QueueTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
`;

const QueueHeadCell = styled.th`
  background: #f8f9fa;
  text-align: left;
  padding: 0.75rem;
  font-weight: 600;
  color: #495057;
  border-bottom: 1px solid #e9ecef;
`;

const QueueCell = styled.td`
  padding: 0.75rem;
  border-bottom: 1px solid #f1f3f5;
  vertical-align: top;
  color: #495057;

  &:last-child {
    color: #868e96;
    max-width: 280px;
    word-break: break-word;
  }
`;

const StatusPill = styled.span<{ status: 'pending' | 'processing' | 'completed' | 'failed' | 'skipped' }>`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;

  ${({ status }) => {
    switch (status) {
      case 'processing':
        return 'background: #fff3cd; color: #856404;';
      case 'completed':
        return 'background: #d4edda; color: #155724;';
      case 'failed':
        return 'background: #f8d7da; color: #721c24;';
      case 'skipped':
        return 'background: #e9ecef; color: #495057;';
      default:
        return 'background: #f1f3f5; color: #495057;';
    }
  }}
`;

const Username = styled.div`
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.25rem;
`;

const UrlLink = styled.a`
  color: #1d4ed8;
  font-size: 0.75rem;
  word-break: break-all;

  &:hover {
    text-decoration: underline;
  }
`;

const QueueEmpty = styled.div`
  padding: 1.5rem;
  text-align: center;
  color: #868e96;
  font-size: 0.9rem;
  background: #f8f9fa;
`;

interface CollectionResult {
  url: string;
  success: boolean;
  username?: string;
  error?: string;
}

interface ProgressDetail {
  status: 'pending' | 'running' | 'completed' | 'failed';
  completed: number;
  total: number;
  message?: string;
}

interface CollectionStatus {
  isRunning: boolean;
  total: number;
  completed: number;
  successful: number;
  failed: number;
  results: CollectionResult[];
  currentUrl?: string;
  progress: {
    profile: ProgressDetail;
    posts: ProgressDetail;
    reels: ProgressDetail;
  };
}

interface CollectionOptions {
  collectProfile: boolean;
  collectPosts: boolean;
  collectReels: boolean;
}

interface CollectionJobSummary {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  total: number;
  recent_24h: number;
}

type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';
type StepStatus = JobStatus | 'skipped';

interface CollectionJobItem {
  id: number;
  job_id: string;
  url: string;
  username: string;
  status: JobStatus;
  profile_status: StepStatus | string;
  posts_status: StepStatus | string;
  reels_status: StepStatus | string;
  profile_count?: number;
  posts_count?: number;
  reels_count?: number;
  error_message?: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

const VALID_JOB_STATUSES: JobStatus[] = ['pending', 'processing', 'completed', 'failed'];
const VALID_STEP_STATUSES: StepStatus[] = ['pending', 'processing', 'completed', 'failed', 'skipped'];

const normalizeJobStatus = (status?: string | null): JobStatus =>
  VALID_JOB_STATUSES.includes(status as JobStatus) ? (status as JobStatus) : 'pending';

const normalizeStepStatus = (status?: string | null): StepStatus =>
  VALID_STEP_STATUSES.includes(status as StepStatus) ? (status as StepStatus) : 'pending';

const isDeletableStatus = (status: JobStatus) => status !== 'processing';

const IngestTab: React.FC = () => {
  const [urls, setUrls] = useState('');
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [collectionOptions, setCollectionOptions] = useState<CollectionOptions>({
    collectProfile: true,
    collectPosts: false,
    collectReels: true
  });
  const [collectionStatus, setCollectionStatus] = useState<CollectionStatus>({
    isRunning: false,
    total: 0,
    completed: 0,
    successful: 0,
    failed: 0,
    results: [],
    progress: {
      profile: { status: 'pending', completed: 0, total: 0 },
      posts: { status: 'pending', completed: 0, total: 0 },
      reels: { status: 'pending', completed: 0, total: 0 }
    }
  });
  const [progressLogs, setProgressLogs] = useState<string[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  
  // 새로운 큐 상태들
  const [collectionJobs, setCollectionJobs] = useState<CollectionJobItem[]>([]);
  const [jobSummary, setJobSummary] = useState<CollectionJobSummary>({
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
    total: 0,
    recent_24h: 0
  });
  const [jobStatusFilter, setJobStatusFilter] = useState<JobStatus | 'all'>('all');
  const [refreshing, setRefreshing] = useState(false);
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([]);
  const [deleteLoading, setDeleteLoading] = useState(false);
  
  // SSE 연결 설정
  const setupSSE = (sessionId: string) => {
    const eventSource = new EventSource(`/api/progress/stream?session_id=${sessionId}`);
    eventSourceRef.current = eventSource;
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const timestamp = new Date().toLocaleTimeString();
        
        switch (data.event) {
          case 'start':
            setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] 🚀 ${data.data.message}`]);
            setCollectionStatus(prev => ({
              ...prev,
              total: data.data.total_urls,
              isRunning: true
            }));
            break;
            
          case 'processing':
            setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] 🔄 ${data.data.message} (${data.data.progress_percent}%)`]);
            setCollectionStatus(prev => ({
              ...prev,
              currentUrl: data.data.url,
              completed: data.data.current_index - 1
            }));
            break;
            
          case 'success':
            setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] ✅ ${data.data.message} - 게시물: ${data.data.posts_count}개, 릴스: ${data.data.reels_count}개`]);
            setCollectionStatus(prev => ({
              ...prev,
              successful: prev.successful + 1,
              completed: prev.completed + 1,
              results: [...(Array.isArray(prev.results) ? prev.results : []), {
                url: data.data.url,
                username: data.data.username,
                success: true,
                status: 'success',
                message: `수집 성공: 게시물 ${data.data.posts_count}개, 릴스 ${data.data.reels_count}개`
              }]
            }));
            break;
            
          case 'detail_progress':
            // 세부 진행상황 업데이트
            const { data_type, status, completed, total, message } = data.data;
            setCollectionStatus(prev => ({
              ...prev,
              progress: {
                ...prev.progress,
                [data_type]: {
                  status: status as 'pending' | 'running' | 'completed' | 'failed',
                  completed,
                  total,
                  message
                }
              }
            }));
            
            // 세부 진행상황 로그 추가
            const statusIcon = status === 'completed' ? '✅' : status === 'failed' ? '❌' : status === 'running' ? '🔄' : '⏳';
            const dataTypeKorean = data_type === 'profile' ? '프로필' : data_type === 'posts' ? '게시물' : '릴스';
            setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] ${statusIcon} ${dataTypeKorean}: ${message || status}`]);
            break;

          case 'error':
          case 'data_failed':
            setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] ❌ ${data.data.message} - ${data.data.error || data.data.reason}`]);
            setCollectionStatus(prev => ({
              ...prev,
              failed: prev.failed + 1,
              completed: prev.completed + 1,
              results: [...(Array.isArray(prev.results) ? prev.results : []), {
                url: data.data.url,
                username: data.data.username || data.data.url,
                success: false,
                status: 'error',
                message: data.data.error || data.data.reason || '수집 실패'
              }]
            }));
            break;
            
          case 'completed':
            setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] 🎉 ${data.data.message} - 성공: ${data.data.success_count}개, 실패: ${data.data.failure_count}개`]);
            setCollectionStatus(prev => ({
              ...prev,
              isRunning: false,
              currentUrl: undefined
            }));
            setLoading(false);
            break;
            
          case 'heartbeat':
            // Heartbeat - 아무것도 하지 않음
            break;
            
          case 'connected':
            setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] 📡 ${data.data.message}`]);
            break;
            
          case 'snapshot_request':
            setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] 📸 ${data.data.message}`]);
            break;
            
          case 'snapshot_triggered':
            setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] ✅ ${data.data.message}`]);
            break;
            
          case 'waiting_snapshot':
            setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] ⏳ ${data.data.message}`]);
            break;
            
          default:
            setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] 📝 ${data.data.message}`]);
        }
      } catch (error) {
        console.error('SSE 메시지 파싱 오류:', error);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('SSE 연결 오류:', error);
      const timestamp = new Date().toLocaleTimeString();
      setProgressLogs(prev => [...(Array.isArray(prev) ? prev : []), `[${timestamp}] ⚠️ 실시간 연결이 끊어졌습니다.`]);
    };
  };
  
  // 컴포넌트 언마운트 시 SSE 연결 정리
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);
  
  // const { setIngestData } = useAppStore();

  const toggleOption = (option: keyof CollectionOptions) => {
    setCollectionOptions(prev => ({
      ...prev,
      [option]: !prev[option]
    }));
  };

  // 큐 상태 조회 함수들
  const fetchCollectionJobs = useCallback(async (statusFilter: JobStatus | 'all' = jobStatusFilter) => {
    try {
      const params = new URLSearchParams({ limit: '20' });
      if (statusFilter && statusFilter !== 'all') {
        params.set('status', statusFilter);
      }

      const response = await fetch(`/api/influencer/collection-jobs?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`collection-jobs request failed with ${response.status}`);
      }

      const data = await response.json();
      if (data?.success) {
        const jobs: CollectionJobItem[] = Array.isArray(data.jobs) ? data.jobs : [];
        const visibleJobs = jobs.filter(job => normalizeJobStatus(job.status) !== 'completed');
        setCollectionJobs(visibleJobs);
        setSelectedJobIds(prev => {
          if (!prev.length) {
            return prev;
          }
          const deletableIds = new Set(
            visibleJobs
              .filter(job => isDeletableStatus(normalizeJobStatus(job.status)))
              .map(job => job.job_id)
          );
          const filtered = prev.filter(id => deletableIds.has(id));
          return filtered.length === prev.length ? prev : filtered;
        });
      }
    } catch (error) {
      console.error('큐 조회 실패:', error);
    }
  }, [jobStatusFilter]);

  const fetchJobSummary = useCallback(async () => {
    try {
      const response = await fetch('/api/influencer/collection-jobs/summary');
      if (!response.ok) {
        throw new Error(`collection-jobs summary request failed with ${response.status}`);
      }

      const data = await response.json();
      if (data?.success) {
        setJobSummary(data.summary);
      }
    } catch (error) {
      console.error('요약 정보 조회 실패:', error);
    }
  }, []);

  const refreshQueueData = useCallback(async (
    withSpinner = false,
    statusOverride?: JobStatus | 'all'
  ) => {
    if (withSpinner) {
      setRefreshing(true);
    }

    try {
      const effectiveFilter = statusOverride ?? jobStatusFilter;
      await Promise.all([fetchCollectionJobs(effectiveFilter), fetchJobSummary()]);
    } finally {
      if (withSpinner) {
        setRefreshing(false);
      }
    }
  }, [fetchCollectionJobs, fetchJobSummary, jobStatusFilter]);

  const jobStatusLabelMap: Record<JobStatus, string> = {
    pending: '대기',
    processing: '진행 중',
    completed: '완료',
    failed: '실패'
  };

  const stepStatusLabelMap: Record<StepStatus, string> = {
    pending: '대기',
    processing: '진행 중',
    completed: '완료',
    failed: '실패',
    skipped: '건너뜀'
  };

  const formatDateTime = (value?: string | null) => {
    if (!value) {
      return '-';
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString('ko-KR', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleRefreshClick = () => {
    void refreshQueueData(true);
  };

  const handleStatusFilterChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value as JobStatus | 'all';
    setJobStatusFilter(value);
    setSelectedJobIds([]);
    void refreshQueueData(true, value);
  };

  // 컴포넌트 마운트 시 데이터 로드
  useEffect(() => {
    refreshQueueData();

    // 5초마다 자동 새로고침
    const interval = setInterval(() => {
      refreshQueueData();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [refreshQueueData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!urls.trim()) {
      toast.error('Instagram 프로필 URL을 입력해주세요');
      return;
    }

    const urlList = urls.split('\n').map(url => url.trim()).filter(url => url);
    const validUrls = urlList.filter(url => 
      url.includes('instagram.com/') && !url.includes('/p/') && !url.includes('/reel/')
    );

    if (validUrls.length === 0) {
      toast.error('유효한 Instagram 프로필 URL을 입력해주세요');
      return;
    }

    if (validUrls.length > 50) {
      toast.error('최대 50개의 URL만 입력할 수 있습니다');
      return;
    }

    // 최소 하나의 수집 옵션이 선택되었는지 확인
    if (!collectionOptions.collectProfile && !collectionOptions.collectPosts && !collectionOptions.collectReels) {
      toast.error('최소 하나의 수집 유형을 선택해주세요');
      return;
    }

    try {
      setLoading(true);
      
      // 초기 상태 설정
      setCollectionStatus({
        isRunning: true,
        total: validUrls.length,
        completed: 0,
        successful: 0,
        failed: 0,
        results: [],
        progress: {
          profile: { 
            status: collectionOptions.collectProfile ? 'pending' : 'completed', 
            completed: collectionOptions.collectProfile ? 0 : 1, 
            total: 1,
            message: collectionOptions.collectProfile ? undefined : '선택되지 않음'
          },
          posts: { 
            status: 'completed',
            completed: 1,
            total: 1,
            message: '선택되지 않음'
          },
          reels: { 
            status: collectionOptions.collectReels ? 'pending' : 'completed', 
            completed: collectionOptions.collectReels ? 0 : 1, 
            total: 1,
            message: collectionOptions.collectReels ? undefined : '선택되지 않음'
          }
        }
      });
      
      toast.success(`${validUrls.length}개 계정의 데이터 수집을 시작합니다`);
      
      // API 호출 (선택된 수집 옵션으로)
      const response = await influencerApi.batchIngest(validUrls, collectionOptions);
      
      // SSE 연결 설정 (sessionId 사용)
      if (response.sessionId) {
        setupSSE(response.sessionId);
      }
      
      // 결과 처리
      const results: CollectionResult[] = (response.results || []).map(result => ({
        url: result.url,
        success: result.success,
        username: result.username,
        error: result.error
      }));
      
      setCollectionStatus(prev => ({
        ...prev,
        isRunning: false,
        total: response.totalRequested,
        completed: response.totalRequested,
        successful: response.successCount,
        failed: response.failureCount,
        results: results
      }));
      
      if (response.successCount > 0) {
        toast.success(`데이터 수집 완료: 성공 ${response.successCount}개, 실패 ${response.failureCount}개`);
      }
      
    } catch (error: any) {
      console.error('Error during ingest:', error);
      toast.error(`수집 중 오류가 발생했습니다: ${error.message}`);
      
      setCollectionStatus(prev => ({
        ...prev,
        isRunning: false
      }));
    } finally {
      setLoading(false);
      void refreshQueueData();
    }
  };

  const progressPercentage = collectionStatus.total > 0 
    ? (collectionStatus.completed / collectionStatus.total) * 100 
    : 0;

  const jobsToRender = Array.isArray(collectionJobs) ? collectionJobs : [];

  const deletableJobsInView = useMemo(
    () => jobsToRender.filter(job => isDeletableStatus(normalizeJobStatus(job.status))),
    [jobsToRender]
  );
  const allSelectableChecked = deletableJobsInView.length > 0 && deletableJobsInView.every(job => selectedJobIds.includes(job.job_id));
  const hasSelection = selectedJobIds.length > 0;

  const handleSelectAllChange = (checked: boolean) => {
    if (checked) {
      setSelectedJobIds(deletableJobsInView.map(job => job.job_id));
    } else {
      setSelectedJobIds([]);
    }
  };

  const toggleJobSelection = (jobId: string) => {
    setSelectedJobIds(prev => prev.includes(jobId)
      ? prev.filter(id => id !== jobId)
      : [...prev, jobId]
    );
  };

  const handleDeleteSelected = async () => {
    if (selectedJobIds.length === 0) {
      return;
    }

    const confirmed = window.confirm('선택한 작업을 삭제하시겠습니까? 진행 중인 작업은 삭제되지 않습니다.');
    if (!confirmed) {
      return;
    }

    setDeleteLoading(true);
    let failedJobIds: string[] = [];

    try {
      const results = await Promise.all(selectedJobIds.map(async (jobId) => {
        try {
          const response = await fetch(`/api/influencer/collection-jobs/${jobId}`, {
            method: 'DELETE'
          });
          const data = await response.json().catch(() => ({}));
          const success = Boolean(data?.success);
          return {
            jobId,
            success,
            message: data?.message || response.statusText || '알 수 없는 오류'
          };
        } catch (error: any) {
          return {
            jobId,
            success: false,
            message: error?.message || '요청 실패'
          };
        }
      }));

      const successCount = results.filter(result => result.success).length;
      const failureMessages = results.filter(result => !result.success).map(result => `${result.jobId.slice(0, 8)}: ${result.message}`);
      failedJobIds = results.filter(result => !result.success).map(result => result.jobId);

      if (successCount > 0) {
        toast.success(`${successCount}개의 작업을 삭제했습니다`);
      }

      if (failureMessages.length > 0) {
        toast.error(`삭제 실패 - ${failureMessages.join(', ')}`);
      }
    } finally {
      setDeleteLoading(false);
      setSelectedJobIds(failedJobIds);
      try {
        await refreshQueueData();
      } catch (error) {
        console.error('선택 삭제 후 큐 새로고침 실패:', error);
      }
    }
  };

  return (
    <div>
      <Section>
        <QueueHeader>
          <SectionTitle>수집 큐 현황</SectionTitle>
          <QueueControls>
            <QueueFilterGroup>
              <span>상태</span>
              <QueueFilterSelect
                value={jobStatusFilter}
                onChange={handleStatusFilterChange}
                disabled={refreshing || deleteLoading}
              >
                <option value="all">전체</option>
                <option value="pending">대기</option>
                <option value="processing">진행 중</option>
                <option value="failed">실패</option>
              </QueueFilterSelect>
            </QueueFilterGroup>
            <QueueActions>
              <DeleteButton
                type="button"
                onClick={handleDeleteSelected}
                disabled={!hasSelection || deleteLoading}
              >
                <Trash2 size={16} />
                {deleteLoading ? '삭제 중...' : `선택 삭제 (${selectedJobIds.length})`}
              </DeleteButton>
              <RefreshButton type="button" onClick={handleRefreshClick} disabled={refreshing}>
                <RefreshCcw size={16} style={refreshing ? { animation: 'spin 1s linear infinite' } : undefined} />
                {refreshing ? '새로고침 중...' : '새로고침'}
              </RefreshButton>
            </QueueActions>
          </QueueControls>
        </QueueHeader>

        <SummaryGrid>
          <SummaryCard>
            <SummaryLabel>총 작업</SummaryLabel>
            <SummaryValue>{jobSummary.total}</SummaryValue>
          </SummaryCard>
          <SummaryCard>
            <SummaryLabel>대기</SummaryLabel>
            <SummaryValue>{jobSummary.pending}</SummaryValue>
          </SummaryCard>
          <SummaryCard>
            <SummaryLabel>진행 중</SummaryLabel>
            <SummaryValue>{jobSummary.processing}</SummaryValue>
          </SummaryCard>
          <SummaryCard>
            <SummaryLabel>완료</SummaryLabel>
            <SummaryValue>{jobSummary.completed}</SummaryValue>
          </SummaryCard>
          <SummaryCard>
            <SummaryLabel>실패</SummaryLabel>
            <SummaryValue>{jobSummary.failed}</SummaryValue>
          </SummaryCard>
          <SummaryCard>
            <SummaryLabel>최근 24시간</SummaryLabel>
            <SummaryValue>{jobSummary.recent_24h}</SummaryValue>
          </SummaryCard>
        </SummaryGrid>

        <QueueTableWrapper>
          {jobsToRender.length > 0 ? (
            <QueueTable>
              <thead>
                <tr>
                  <QueueHeadCell style={{ width: '3rem' }}>
                    <CheckboxInput
                      checked={allSelectableChecked}
                      disabled={deletableJobsInView.length === 0 || deleteLoading}
                      onChange={(e) => handleSelectAllChange(e.target.checked)}
                      aria-label="작업 전체 선택"
                    />
                  </QueueHeadCell>
                  <QueueHeadCell>요청 시간</QueueHeadCell>
                  <QueueHeadCell>계정</QueueHeadCell>
                  <QueueHeadCell>작업 상태</QueueHeadCell>
                  <QueueHeadCell>프로필</QueueHeadCell>
                  <QueueHeadCell>릴스</QueueHeadCell>
                </tr>
              </thead>
              <tbody>
                {jobsToRender.map((job) => {
                  const normalizedStatus = normalizeJobStatus(job.status);
                  const jobStatus =
                    normalizedStatus === 'pending' && job.started_at ? 'processing' : normalizedStatus;
                  const profileStatus = normalizeStepStatus(job.profile_status);
                  const reelsStatus = normalizeStepStatus(job.reels_status);
                  const isSelectable = isDeletableStatus(jobStatus);
                  const isChecked = selectedJobIds.includes(job.job_id);

                  return (
                    <tr key={job.job_id || job.id}>
                      <QueueCell>
                        <CheckboxInput
                          checked={isChecked}
                          disabled={!isSelectable || deleteLoading}
                          onChange={() => {
                            if (!isSelectable || deleteLoading) {
                              return;
                            }
                            toggleJobSelection(job.job_id);
                          }}
                          aria-label={`${job.username || job.job_id} 작업 선택`}
                          title={!isSelectable ? '진행 중인 작업은 삭제할 수 없습니다' : undefined}
                        />
                      </QueueCell>
                      <QueueCell>{formatDateTime(job.created_at)}</QueueCell>
                      <QueueCell>
                        <Username>{job.username ? `@${job.username}` : '미확인 계정'}</Username>
                        {job.url ? (
                          <UrlLink href={job.url} target="_blank" rel="noopener noreferrer">
                            {job.url}
                          </UrlLink>
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: '#adb5bd' }}>URL 없음</span>
                        )}
                      </QueueCell>
                      <QueueCell>
                        <StatusPill status={jobStatus}>{jobStatusLabelMap[jobStatus]}</StatusPill>
                        {(job.started_at || job.completed_at) && (
                          <div style={{ marginTop: '0.35rem', fontSize: '0.75rem', color: '#868e96' }}>
                            {job.started_at && `시작 ${formatDateTime(job.started_at)}`}
                            {job.started_at && job.completed_at && ' · '}
                            {job.completed_at && `완료 ${formatDateTime(job.completed_at)}`}
                          </div>
                        )}
                      </QueueCell>
                      <QueueCell>
                        <StatusPill status={profileStatus}>{stepStatusLabelMap[profileStatus]}</StatusPill>
                        {typeof job.profile_count === 'number' && job.profile_count > 0 && (
                          <div style={{ marginTop: '0.35rem', fontSize: '0.75rem', color: '#868e96' }}>
                            {job.profile_count}건 저장
                          </div>
                        )}
                      </QueueCell>
                      <QueueCell>
                        <StatusPill status={reelsStatus}>{stepStatusLabelMap[reelsStatus]}</StatusPill>
                        {typeof job.reels_count === 'number' && job.reels_count > 0 && (
                          <div style={{ marginTop: '0.35rem', fontSize: '0.75rem', color: '#868e96' }}>
                            {job.reels_count}개 릴스
                          </div>
                        )}
                      </QueueCell>
                    </tr>
                  );
                })}
              </tbody>
            </QueueTable>
          ) : (
            <QueueEmpty>
              {jobStatusFilter === 'all'
                ? '표시할 작업이 없습니다.'
                : '선택한 상태에 해당하는 작업이 없습니다.'}
            </QueueEmpty>
          )}
        </QueueTableWrapper>
      </Section>

      <Section>
        <SectionTitle>Instagram 프로필 배치 수집</SectionTitle>
        
        <form onSubmit={handleSubmit}>
          <FormGroup>
            <Label>Instagram 프로필 URL (최대 50개)</Label>
            <TextArea
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
              placeholder="Instagram 프로필 URL을 한 줄에 하나씩 입력하세요&#10;예: https://www.instagram.com/username1/&#10;https://www.instagram.com/username2/"
              required
            />
            <InfoText>
              프로필 URL만 입력하세요 (게시물이나 릴스 URL 제외). BrightData API를 사용하여 실제 데이터를 수집합니다. 
              스냅샷 생성에 5-15분 정도 소요될 수 있습니다.
            </InfoText>
          </FormGroup>
          
          <FormGroup>
            <Label>수집할 데이터 유형 선택</Label>
            <OptionsGrid>
              <OptionCard 
                selected={collectionOptions.collectProfile} 
                onClick={() => toggleOption('collectProfile')}
              >
                <OptionHeader>
                  <User size={20} />
                  <OptionTitle>프로필 정보</OptionTitle>
                </OptionHeader>
                <OptionDescription>
                  사용자명, 팔로워 수, 바이오 등 기본 프로필 정보를 수집합니다.
                </OptionDescription>
              </OptionCard>
              
              <OptionCard 
                selected={collectionOptions.collectReels} 
                onClick={() => toggleOption('collectReels')}
              >
                <OptionHeader>
                  <Video size={20} />
                  <OptionTitle>릴스</OptionTitle>
                </OptionHeader>
                <OptionDescription>
                  최근 릴스 24개의 썸네일, 캡션, 조회수 등을 수집합니다.
                </OptionDescription>
              </OptionCard>
            </OptionsGrid>
          </FormGroup>
          
          <Button type="submit" disabled={loading}>
            {loading ? (
              <>
                <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
                실제 API 수집 중...
              </>
            ) : (
              <>
                <Download size={20} />
                실제 데이터 수집 시작
              </>
            )}
          </Button>
        </form>
      </Section>

      {/* 수집 상황 모달 */}
      {showModal && (
        <ModalOverlay>
          <ModalContent>
            <ModalHeader>
              <ModalTitle>
                <Users size={24} />
                데이터 수집 진행 상황
              </ModalTitle>
              <CloseButton onClick={() => setShowModal(false)}>
                ×
              </CloseButton>
            </ModalHeader>

            <ProgressSection>
              <ProgressBar>
                <ProgressFill percentage={progressPercentage} />
              </ProgressBar>
              
              {/* 세부 진행상황 */}
              <div style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#2c3e50' }}>수집 단계별 진행상황</h4>
                
                {collectionOptions.collectProfile && (
                  <ProgressDetailCard>
                    <ProgressDetailHeader>
                      <ProgressDetailTitle>
                        <User size={16} />
                        프로필 정보
                      </ProgressDetailTitle>
                      <ProgressDetailStatus status={collectionStatus.progress.profile.status}>
                        {collectionStatus.progress.profile.status}
                      </ProgressDetailStatus>
                    </ProgressDetailHeader>
                    <ProgressDetailBar>
                      <ProgressDetailFill 
                        percentage={collectionStatus.progress.profile.total > 0 ? 
                          (collectionStatus.progress.profile.completed / collectionStatus.progress.profile.total) * 100 : 0}
                        status={collectionStatus.progress.profile.status}
                      />
                    </ProgressDetailBar>
                    <div style={{ fontSize: '0.875rem', color: '#6c757d', marginTop: '0.25rem' }}>
                      {collectionStatus.progress.profile.completed} / {collectionStatus.progress.profile.total}
                      {collectionStatus.progress.profile.message && ` - ${collectionStatus.progress.profile.message}`}
                    </div>
                  </ProgressDetailCard>
                )}
                
                {collectionOptions.collectReels && (
                  <ProgressDetailCard>
                    <ProgressDetailHeader>
                      <ProgressDetailTitle>
                        <Video size={16} />
                        릴스
                      </ProgressDetailTitle>
                      <ProgressDetailStatus status={collectionStatus.progress.reels.status}>
                        {collectionStatus.progress.reels.status}
                      </ProgressDetailStatus>
                    </ProgressDetailHeader>
                    <ProgressDetailBar>
                      <ProgressDetailFill 
                        percentage={collectionStatus.progress.reels.total > 0 ? 
                          (collectionStatus.progress.reels.completed / collectionStatus.progress.reels.total) * 100 : 0}
                        status={collectionStatus.progress.reels.status}
                      />
                    </ProgressDetailBar>
                    <div style={{ fontSize: '0.875rem', color: '#6c757d', marginTop: '0.25rem' }}>
                      {collectionStatus.progress.reels.completed} / {collectionStatus.progress.reels.total}
                      {collectionStatus.progress.reels.message && ` - ${collectionStatus.progress.reels.message}`}
                    </div>
                  </ProgressDetailCard>
                )}
              </div>
              
              {/* 현재 상태 표시 */}
              {collectionStatus.isRunning && collectionStatus.currentUrl && (
                <CurrentStatus>
                  <Activity size={16} />
                  현재 처리 중: {collectionStatus.currentUrl}
                </CurrentStatus>
              )}
              
              {/* 실시간 로그 */}
              <div style={{ marginBottom: '1rem' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '1rem', color: '#495057' }}>실시간 진행 상황</h4>
                <LogContainer>
                  {(!Array.isArray(progressLogs) || progressLogs.length === 0) ? (
                    <LogEntry style={{ color: '#6c757d', fontStyle: 'italic' }}>
                      진행 상황이 여기에 실시간으로 표시됩니다...
                    </LogEntry>
                  ) : (
                    (Array.isArray(progressLogs) ? progressLogs : []).map((log, index) => (
                      <LogEntry key={index}>{log}</LogEntry>
                    ))
                  )}
                </LogContainer>
              </div>
              
              <div style={{ textAlign: 'center', color: '#6c757d', fontSize: '0.875rem' }}>
                {collectionStatus.isRunning ? (
                  <div>
                    <div style={{ fontSize: '0.75rem', color: '#28a745' }}>
                      진행률: {collectionStatus.completed}/{collectionStatus.total} ({progressPercentage.toFixed(1)}%)
                    </div>
                  </div>
                ) : (
                  `수집 완료: ${collectionStatus.completed}/${collectionStatus.total}`
                )}
              </div>
            </ProgressSection>

            <StatsGrid>
              <StatCard>
                <StatValue>{collectionStatus.total}</StatValue>
                <StatLabel>총 요청</StatLabel>
              </StatCard>
              <StatCard>
                <StatValue>{collectionStatus.successful}</StatValue>
                <StatLabel>성공</StatLabel>
              </StatCard>
              <StatCard>
                <StatValue>{collectionStatus.failed}</StatValue>
                <StatLabel>실패</StatLabel>
              </StatCard>
              <StatCard>
                <StatValue>{Math.round((collectionStatus.successful / Math.max(collectionStatus.total, 1)) * 100)}%</StatValue>
                <StatLabel>성공률</StatLabel>
              </StatCard>
            </StatsGrid>

            {(Array.isArray(collectionStatus.results) && collectionStatus.results.length > 0) && (
              <div>
                <h3 style={{ color: '#2c3e50', marginBottom: '1rem' }}>상세 결과</h3>
                <ResultsList>
                  {(Array.isArray(collectionStatus.results) ? collectionStatus.results : []).map((result, index) => (
                    <ResultItem key={index} success={result.success}>
                      <ResultIcon success={result.success}>
                        {result.success ? (
                          <CheckCircle size={16} />
                        ) : (
                          <XCircle size={16} />
                        )}
                      </ResultIcon>
                      <ResultText>
                        <div>{result.url}</div>
                        {result.success && result.username && (
                          <div style={{ fontSize: '0.75rem', color: '#28a745', marginTop: '0.25rem' }}>
                            @{result.username} 수집 완료
                          </div>
                        )}
                        {!result.success && result.error && (
                          <ErrorText>{result.error}</ErrorText>
                        )}
                      </ResultText>
                    </ResultItem>
                  ))}
                </ResultsList>
              </div>
            )}
          </ModalContent>
        </ModalOverlay>
      )}
    </div>
  );
};

export default IngestTab;
