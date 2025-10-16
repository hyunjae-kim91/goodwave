import React, { useEffect, useMemo, useState } from 'react';
import styled from 'styled-components';
import toast from 'react-hot-toast';
import { Search, RefreshCw, Play, Database, BarChart3, CheckCircle, Trash2 } from 'lucide-react';
import {
  classificationService,
  ClassificationJobItem,
  IndividualReelClassificationResponse,
  IndividualReelEntry,
  AggregatedSummary,
  AggregatedSummaryResponse,
} from '../../services/influencer/classificationService';
import { promptService } from '../../services/influencer/promptService';

interface UserData {
  username: string;
  hasProfile: boolean;
  hasPosts: boolean;
  hasReels?: boolean;
  lastModified?: number;
}

interface SummaryTopEntry {
  label: string;
  percentage: number;
  count?: number;
}

interface CombinedSummary {
  motivationTop: SummaryTopEntry[];
  categoryTop: SummaryTopEntry[];
  motivation_details?: Record<string, unknown>;
  category_details?: Record<string, unknown>;
  overall_analysis?: {
    influencer_type?: string;
    engagement_strategy?: string[];
    target_audience?: Record<string, unknown>;
  } | null;
  timestamp?: string;
}

const CLASSIFICATION_STATUS_LABELS: Record<ClassificationJobItem['status'], string> = {
  pending: '대기',
  processing: '진행 중',
  failed: '실패',
  completed: '완료',
};

const Container = styled.div`
  max-width: 100%;
`;

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

const AlertBox = styled.div`
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;

  &.error {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
  }
`;

const SearchContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;

  @media (min-width: 640px) {
    flex-direction: row;
  }
`;

const SearchInput = styled.input`
  flex: 1;
  padding: 0.75rem 0.75rem 0.75rem 2.5rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1rem;

  &:focus {
    outline: none;
    border-color: #3498db;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.25);
  }
`;

const Button = styled.button<{ $variant?: 'secondary' | 'success' | 'danger' }>`
  padding: 0.75rem 1.5rem;
  background-color: ${({ $variant }) =>
    $variant === 'secondary' ? '#95a5a6' :
    $variant === 'success' ? '#27ae60' :
    $variant === 'danger' ? '#e74c3c' : '#3498db'};
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: ${({ $variant }) =>
      $variant === 'secondary' ? '#7f8c8d' :
      $variant === 'success' ? '#229954' :
      $variant === 'danger' ? '#c0392b' : '#2980b9'};
  }

  &:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
  }
`;

const QueueHeader = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justifyContent: space-between;
  gap: 0.75rem;
`;

const QueueActions = styled.div`
  display: inline-flex;
  gap: 0.5rem;
  flex-wrap: wrap;
`;

const QueueTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
`;

const QueueHeadCell = styled.th`
  background: #f8f9fa;
  text-align: left;
  padding: 0.65rem 0.75rem;
  font-weight: 600;
  color: #495057;
  border-bottom: 1px solid #dee2e6;
`;

const QueueRow = styled.tr`
  &:nth-child(even) {
    background: #f8f9fa;
  }
`;

const QueueCell = styled.td`
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid #f1f3f5;
  color: #495057;
  vertical-align: top;
`;

const QueueCheckbox = styled.input.attrs({ type: 'checkbox' })`
  width: 1rem;
  height: 1rem;
`;

const StatusBadge = styled.span<{ status: ClassificationJobItem['status'] }>`
  display: inline-flex;
  align-items: center;
  justifyContent: center;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  ${({ status }) => {
    switch (status) {
      case 'processing':
        return 'background:#fff3cd;color:#856404;';
      case 'completed':
        return 'background:#d4edda;color:#155724;';
      case 'failed':
        return 'background:#f8d7da;color:#721c24;';
      default:
        return 'background:#e7f5ff;color:#1c7ed6;';
    }
  }}
`;

const QueueEmpty = styled.div`
  padding: 1.25rem;
  background: #f8f9fa;
  border: 1px dashed #dee2e6;
  border-radius: 6px;
  text-align: center;
  color: #868e96;
`;

const SummaryGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
`;

const SummaryCard = styled.div`
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  padding: 1rem;
`;

const SummaryTitle = styled.div`
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.35rem;
`;

const SummaryValue = styled.div`
  font-size: 1.1rem;
  font-weight: 600;
  color: #1b4b8c;
`;

const SummaryItem = styled.div`
  font-size: 0.875rem;
  color: #495057;
  margin-top: 0.35rem;
`;

const PromptBox = styled.pre`
  white-space: pre-wrap;
  font-size: 0.875rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  overflow-x: auto;
`;

const SelectionTable = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const SelectionHeadCell = styled.th`
  padding: 0.75rem;
  background: #f8f9fa;
  text-align: left;
  font-size: 0.875rem;
  font-weight: 600;
  color: #495057;
  border-bottom: 1px solid #dee2e6;
`;

const SelectionRow = styled.tr`
  &:nth-child(even) {
    background: #f8f9fa;
  }
`;

const SelectionCell = styled.td`
  padding: 0.75rem;
  border-bottom: 1px solid #dee2e6;
  vertical-align: middle;
  font-size: 0.875rem;
  color: #495057;
`;

const UserBadge = styled.div`
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: linear-gradient(45deg, #3498db, #9b59b6);
  color: white;
  display: flex;
  align-items: center;
  justifyContent: center;
  font-weight: 600;
  font-size: 0.875rem;
  margin-right: 0.75rem;
`;

const EmptyPlaceholder = styled.div`
  text-align: center;
  padding: 3rem 1rem;
  color: #6c757d;
`;

const ListButton = styled.button`
  width: 100%;
  text-align: left;
  padding: 0.75rem;
  font-size: 0.875rem;
  border: none;
  border-bottom: 1px solid #dee2e6;
  background: white;
  cursor: pointer;

  &:hover {
    background: #f8f9fa;
  }
`;

const formatDateTime = (value?: string) => {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return '-';
  }
  return parsed.toLocaleString('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return !!value && typeof value === 'object' && !Array.isArray(value);
};

const normalizePercentageValue = (value: unknown): number | undefined => {
  if (value === null || value === undefined) {
    return undefined;
  }
  const numeric = typeof value === 'string' ? Number.parseFloat(value) : Number(value);
  if (Number.isNaN(numeric)) {
    return undefined;
  }
  return numeric;
};

const normalizeToPercent = (value?: number): number | undefined => {
  if (value === undefined) return undefined;
  if (value <= 1) {
    return value * 100;
  }
  return value;
};

const formatPercentage = (value?: number | null) => {
  if (value === undefined || value === null) {
    return '0%';
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return '0%';
  }
  return `${Math.round(numeric)}%`;
};

const extractTopEntriesFromDistribution = (
  distribution: AggregatedSummary['classification_distribution'] | unknown,
): SummaryTopEntry[] => {
  if (!distribution) {
    return [];
  }

  let entries: SummaryTopEntry[] = [];

  if (Array.isArray(distribution)) {
    const totalCount = distribution.reduce(
      (acc, item) => acc + (typeof item.count === 'number' ? item.count : 0),
      0,
    );
    entries = distribution
      .map((item) => ({
        label: typeof item.label === 'string' ? item.label : '',
        percentage:
          totalCount > 0 && typeof item.count === 'number'
            ? (item.count / totalCount) * 100
            : normalizePercentageValue(item.percentage) ?? 0,
        count: typeof item.count === 'number' ? item.count : undefined,
      }))
      .filter((item) => item.label);
  } else if (isRecord(distribution)) {
    const mapped = Object.entries(distribution).map(([label, value]) => ({
      label,
      raw: value,
    }));

    const total = mapped.reduce(
      (sum, item) => sum + (typeof item.raw === 'number' ? item.raw : 0),
      0,
    );

    if (total > 0) {
      entries = mapped.map((item) => ({
        label: item.label,
        percentage:
          typeof item.raw === 'number' ? (item.raw / total) * 100 : 0,
        count: typeof item.raw === 'number' ? Math.round(item.raw) : undefined,
      }));
    } else {
      entries = mapped.map((item) => ({
        label: item.label,
        percentage: normalizePercentageValue(item.raw) ?? 0,
      }));
    }
  }

  entries.sort((a, b) => (b.count ?? b.percentage) - (a.count ?? a.percentage));
  return entries.slice(0, 2);
};

const buildTopEntriesFromFallback = (
  details: Record<string, unknown> | undefined,
  primaryLabel?: string,
  secondaryLabel?: string,
  primaryValue?: unknown,
  secondaryValue?: unknown,
  totalCount?: number,
): SummaryTopEntry[] => {
  const detailData = details as Record<string, any> | undefined;

  if (detailData && detailData.classification_distribution) {
    const fromDistribution = extractTopEntriesFromDistribution(
      detailData.classification_distribution,
    );
    if (fromDistribution.length > 0) {
      return fromDistribution;
    }
  }

  const results: SummaryTopEntry[] = [];

  if (primaryLabel) {
    const percentValue = normalizeToPercent(
      normalizePercentageValue(
        primaryValue ??
          (detailData ? detailData.primary_percentage ?? detailData.confidence_score : undefined),
      ),
    ) ?? 0;
    results.push({
      label: primaryLabel,
      percentage: percentValue,
      count:
        totalCount && percentValue
          ? Math.round((percentValue / 100) * totalCount)
          : undefined,
    });
  }

  if (secondaryLabel) {
    const percentValue = normalizeToPercent(
      normalizePercentageValue(
        secondaryValue ?? (detailData ? detailData.secondary_percentage : undefined),
      ),
    );
    if (percentValue !== undefined) {
      results.push({
        label: secondaryLabel,
        percentage: percentValue,
        count:
          totalCount && percentValue
            ? Math.round((percentValue / 100) * totalCount)
            : undefined,
      });
    }
  }

  return results.slice(0, 2);
};

const formatTopEntriesLine = (entries: SummaryTopEntry[]) =>
  entries
    .map((entry) => `${entry.label} ${formatPercentage(entry.percentage)}`)
    .join(', ');

const getUserStatusText = (user: UserData) => {
  const status: string[] = [];
  if (user.hasProfile) status.push('프로필');
  if (user.hasPosts) status.push('게시물');
  if (user.hasReels) status.push('릴스');
  return status.length > 0 ? status.join(', ') : '데이터 없음';
};

const CombinedClassificationTab: React.FC = () => {
  const [users, setUsers] = useState<UserData[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [topSearch, setTopSearch] = useState('');
  const [userSearch, setUserSearch] = useState('');
  const [selectedUsersForClassification, setSelectedUsersForClassification] = useState<string[]>([]);
  const [bulkClassifying, setBulkClassifying] = useState(false);

  const [classificationJobs, setClassificationJobs] = useState<ClassificationJobItem[]>([]);
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([]);
  const [queueLoading, setQueueLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteResultsLoading, setDeleteResultsLoading] = useState(false);

  const [systemPrompt, setSystemPrompt] = useState('');
  const [promptTypes, setPromptTypes] = useState<string[]>([]);
  const [selectedPromptType, setSelectedPromptType] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [combinedSummary, setCombinedSummary] = useState<CombinedSummary | null>(null);
  const [individualReelData, setIndividualReelData] = useState<IndividualReelClassificationResponse | null>(null);
  const [showIndividualReels, setShowIndividualReels] = useState(false);
  const [deletingReelIds, setDeletingReelIds] = useState<number[]>([]);

  const filteredUsers = useMemo(() => {
    const term = userSearch.trim().toLowerCase();
    if (!term) {
      return users;
    }
    return users.filter(user => user.username.toLowerCase().includes(term));
  }, [users, userSearch]);

  const topFilteredUsers = useMemo(() => {
    const term = topSearch.trim().toLowerCase();
    const source = term ? users.filter(user => user.username.toLowerCase().includes(term)) : users;
    return source.slice(0, 10);
  }, [users, topSearch]);

  const loadUsers = async () => {
    try {
      setIsLoadingUsers(true);
      const response = await fetch('/api/influencer/files/users');
      if (!response.ok) {
        throw new Error('사용자 목록을 불러오지 못했습니다');
      }
      const data = await response.json();
      setUsers(Array.isArray(data.users) ? data.users : []);
    } catch (error) {
      console.error(error);
      toast.error('사용자 목록을 불러오는데 실패했습니다');
    } finally {
      setIsLoadingUsers(false);
    }
  };

  const loadPrompt = async (promptType?: string) => {
    const normalizedType = promptType?.trim() || selectedPromptType.trim();

    if (!normalizedType) {
      if (promptType !== undefined) {
        setSelectedPromptType('');
      }
      setSystemPrompt('');
      return;
    }

    try {
      const data = await promptService.loadPrompt(normalizedType);
      setSelectedPromptType(normalizedType);
      setSystemPrompt(data.content || '');
    } catch (error) {
      setSystemPrompt('');
    }
  };

  const loadPromptTypes = async () => {
    try {
      const types = await promptService.getPromptTypes();
      setPromptTypes(types);

      if (Array.isArray(types) && types.length > 0) {
        const initialType =
          selectedPromptType && types.includes(selectedPromptType)
            ? selectedPromptType
            : types[0];

        if (message?.type === 'error' && message.text.includes('저장된 프롬프트가 없습니다')) {
          setMessage(null);
        }

        await loadPrompt(initialType);
      } else {
        setSelectedPromptType('');
        setSystemPrompt('');
        setMessage({
          type: 'error',
          text: '저장된 프롬프트가 없습니다. 프롬프트 탭에서 먼저 저장해주세요.',
        });
      }
    } catch (error) {
      setPromptTypes([]);
      setSelectedPromptType('');
      setSystemPrompt('');
      setMessage({
        type: 'error',
        text: '프롬프트 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.',
      });
    }
  };

  const refreshClassificationJobs = async (withSpinner = false) => {
    if (withSpinner) {
      setQueueLoading(true);
    }
    try {
      const jobs = await classificationService.getClassificationJobs('active');
      const activeJobs = jobs.filter(job => job.status !== 'completed');
      setClassificationJobs(activeJobs);
      setSelectedJobIds(prev => prev.filter(id => {
        const job = activeJobs.find(item => item.job_id === id);
        return job && job.status !== 'processing';
      }));
    } catch (error) {
      console.error(error);
      toast.error('분류 큐를 불러오지 못했습니다');
    } finally {
      if (withSpinner) {
        setQueueLoading(false);
      }
    }
  };

  const loadCombinedSummary = async (username: string) => {
    try {
      const [aggregatedResult, combinedResult] = await Promise.allSettled([
        classificationService.getAggregatedClassificationSummary(username),
        fetch(`/api/influencer/files/combined-classification/${username}`).then((res) =>
          res.ok ? res.json() : null,
        ),
      ]);

      const aggregatedData =
        aggregatedResult.status === 'fulfilled' ? aggregatedResult.value : null;
      const combinedData = combinedResult.status === 'fulfilled' ? combinedResult.value : null;

      const summaryPayload =
        combinedData && Array.isArray(combinedData.results) && combinedData.results.length > 0
          ? combinedData.results[0]
          : null;

      const motivationDetails = isRecord(summaryPayload?.motivation_details)
        ? (summaryPayload.motivation_details as Record<string, unknown>)
        : undefined;
      const categoryDetails = isRecord(summaryPayload?.category_details)
        ? (summaryPayload.category_details as Record<string, unknown>)
        : undefined;

      const aggregatedSummaries = aggregatedData?.aggregated_summaries ?? {};
      const motivationAggregated = aggregatedSummaries['subscription_motivation'];
      const categoryAggregated = aggregatedSummaries['category'];

      let motivationTop = extractTopEntriesFromDistribution(
        motivationAggregated?.classification_distribution,
      );
      if (!motivationTop.length && motivationAggregated) {
        motivationTop = buildTopEntriesFromFallback(
          motivationAggregated as unknown as Record<string, unknown>,
          motivationAggregated.primary_classification,
          motivationAggregated.secondary_classification ?? undefined,
          motivationAggregated.primary_percentage,
          motivationAggregated.secondary_percentage,
          motivationAggregated.statistics?.successful_classifications ||
            motivationAggregated.statistics?.total_reels_processed,
        );
      }
      if (!motivationTop.length && summaryPayload) {
        motivationTop = buildTopEntriesFromFallback(
          motivationDetails,
          typeof summaryPayload.motivation === 'string' ? summaryPayload.motivation : undefined,
          typeof summaryPayload.motivation_secondary === 'string'
            ? summaryPayload.motivation_secondary
            : undefined,
          summaryPayload.motivation_confidence,
          (motivationDetails as Record<string, any> | undefined)?.secondary_percentage,
        );
      }

      let categoryTop = extractTopEntriesFromDistribution(
        categoryAggregated?.classification_distribution,
      );
      if (!categoryTop.length && categoryAggregated) {
        categoryTop = buildTopEntriesFromFallback(
          categoryAggregated as unknown as Record<string, unknown>,
          categoryAggregated.primary_classification,
          categoryAggregated.secondary_classification ?? undefined,
          categoryAggregated.primary_percentage,
          categoryAggregated.secondary_percentage,
          categoryAggregated.statistics?.successful_classifications ||
            categoryAggregated.statistics?.total_reels_processed,
        );
      }
      if (!categoryTop.length && summaryPayload) {
        categoryTop = buildTopEntriesFromFallback(
          categoryDetails,
          typeof summaryPayload.category === 'string' ? summaryPayload.category : undefined,
          typeof summaryPayload.category_secondary === 'string'
            ? summaryPayload.category_secondary
            : undefined,
          summaryPayload.category_confidence,
          (categoryDetails as Record<string, any> | undefined)?.secondary_percentage,
        );
      }

      const timestamp =
        motivationAggregated?.processed_at ??
        motivationAggregated?.timestamp ??
        categoryAggregated?.processed_at ??
        categoryAggregated?.timestamp ??
        summaryPayload?.timestamp ??
        undefined;

      if (!motivationTop.length && !categoryTop.length && !summaryPayload) {
        setCombinedSummary(null);
        return;
      }

      setCombinedSummary({
        motivationTop,
        categoryTop,
        motivation_details: motivationDetails,
        category_details: categoryDetails,
        overall_analysis: summaryPayload?.overall_analysis ?? null,
        timestamp,
      });
    } catch (error) {
      setCombinedSummary(null);
    }
  };

  const loadIndividualReelClassifications = async (username: string) => {
    try {
      const data = await classificationService.getIndividualReelClassifications(username);
      setIndividualReelData(data);
    } catch (error) {
      console.error('개별 릴스 분류 결과 로드 실패:', error);
      setIndividualReelData(null);
    }
  };

  useEffect(() => {
    loadUsers();
    loadPromptTypes();
    refreshClassificationJobs(true);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      refreshClassificationJobs();
    }, 7000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedUser) {
      loadCombinedSummary(selectedUser);
      loadIndividualReelClassifications(selectedUser);
    } else {
      setCombinedSummary(null);
      setIndividualReelData(null);
      setShowIndividualReels(false);
    }
  }, [selectedUser]);

  const toggleJobSelection = (jobId: string, status: ClassificationJobItem['status']) => {
    if (status === 'processing') {
      return;
    }
    setSelectedJobIds(prev => prev.includes(jobId)
      ? prev.filter(id => id !== jobId)
      : [...prev, jobId]
    );
  };

  const handleSelectAllJobs = (checked: boolean) => {
    if (checked) {
      const selectable = classificationJobs.filter(job => job.status !== 'processing').map(job => job.job_id);
      setSelectedJobIds(selectable);
    } else {
      setSelectedJobIds([]);
    }
  };

  const handleDeleteSelectedJobs = async () => {
    if (selectedJobIds.length === 0) {
      return;
    }
    const confirmed = window.confirm('선택한 분류 작업을 삭제하시겠습니까? 진행 중인 작업은 삭제되지 않습니다.');
    if (!confirmed) {
      return;
    }
    setDeleteLoading(true);
    try {
      const results = await Promise.all(selectedJobIds.map(async jobId => {
        try {
          const res = await classificationService.deleteClassificationJob(jobId);
          return { jobId, ...res };
        } catch (error) {
          return {
            jobId,
            success: false,
            message: error instanceof Error ? error.message : '삭제 실패',
          };
        }
      }));
      const failed = results.filter(result => !result.success);
      const succeeded = results.length - failed.length;
      if (succeeded > 0) {
        toast.success(`${succeeded}개의 작업을 삭제했습니다`);
      }
      if (failed.length > 0) {
        toast.error(`삭제 실패: ${failed.map(item => item.message).join(', ')}`);
      }
    } finally {
      setDeleteLoading(false);
      setSelectedJobIds([]);
      refreshClassificationJobs(true);
    }
  };

  const toggleUserSelection = (username: string) => {
    setSelectedUsersForClassification(prev => prev.includes(username)
      ? prev.filter(item => item !== username)
      : [...prev, username]
    );
  };

  const toggleAllUsers = () => {
    if (selectedUsersForClassification.length === filteredUsers.length && filteredUsers.length > 0) {
      setSelectedUsersForClassification([]);
    } else {
      setSelectedUsersForClassification(filteredUsers.map(user => user.username));
    }
  };

  const handleDeleteUserResults = async () => {
    if (!selectedUser) {
      toast.error('삭제할 사용자를 먼저 선택하세요.');
      return;
    }
    const confirmed = window.confirm(`${selectedUser}의 분류 결과를 모두 삭제하시겠습니까?`);
    if (!confirmed) {
      return;
    }
    setDeleteResultsLoading(true);
    try {
      await classificationService.deleteUserClassificationData(selectedUser);
      toast.success('분류 결과를 삭제했습니다.');
      await Promise.all([
        loadCombinedSummary(selectedUser),
        loadIndividualReelClassifications(selectedUser),
      ]);
      setShowIndividualReels(false);
      setMessage({ type: 'success', text: '분류 결과를 삭제했습니다.' });
    } catch (error: any) {
      const message = error?.message || '분류 결과 삭제에 실패했습니다.';
      toast.error(message);
      setMessage({ type: 'error', text: message });
    } finally {
      setDeleteResultsLoading(false);
    }
  };

  const handleDeleteIndividualReel = async (reelId: number) => {
    if (!selectedUser) {
      toast.error('삭제할 사용자를 먼저 선택하세요.');
      return;
    }
    const confirmed = window.confirm('해당 릴의 분류 결과를 삭제하시겠습니까?');
    if (!confirmed) {
      return;
    }

    setDeletingReelIds(prev => [...prev, reelId]);
    try {
      await classificationService.deleteIndividualReelClassification(reelId);
      toast.success('릴 분류 결과를 삭제했습니다.');
      await Promise.all([
        loadIndividualReelClassifications(selectedUser),
        loadCombinedSummary(selectedUser),
      ]);
    } catch (error: any) {
      const message = error?.message || '릴 분류 결과 삭제에 실패했습니다.';
      toast.error(message);
      setMessage({ type: 'error', text: message });
    } finally {
      setDeletingReelIds(prev => prev.filter(id => id !== reelId));
    }
  };

  const handlePromptTypeChange = async (value: string) => {
    setSelectedPromptType(value);
    await loadPrompt(value);
  };

  const runCombined = async () => {
    if (!selectedUser) {
      setMessage({ type: 'error', text: '사용자를 선택해주세요.' });
      return;
    }
    if (!systemPrompt) {
      setMessage({ type: 'error', text: '선택한 프롬프트 내용을 불러오지 못했습니다. 프롬프트 탭에서 먼저 저장해주세요.' });
      return;
    }
    try {
      await classificationService.startCombinedClassification(
        selectedUser,
        selectedPromptType || undefined,
      );
      setMessage({ type: 'success', text: '통합 분류 작업을 큐에 등록했습니다.' });
      toast.success('분류 작업이 큐에 추가되었습니다');
      refreshClassificationJobs();
    } catch (error: any) {
      setMessage({ type: 'error', text: error?.message || '통합 분류 시작 실패' });
    }
  };

  const bulkRunCombined = async () => {
    if (selectedUsersForClassification.length === 0) {
      setMessage({ type: 'error', text: '사용자를 선택해주세요.' });
      return;
    }
    if (!systemPrompt) {
      setMessage({ type: 'error', text: '선택한 프롬프트 내용을 불러오지 못했습니다. 프롬프트 탭에서 먼저 저장해주세요.' });
      return;
    }
    setBulkClassifying(true);
    let success = 0;
    let fail = 0;
    for (const username of selectedUsersForClassification) {
      try {
        await classificationService.startCombinedClassification(
          username,
          selectedPromptType || undefined,
        );
        success += 1;
      } catch {
        fail += 1;
      }
    }
    setBulkClassifying(false);
    setSelectedUsersForClassification([]);
    refreshClassificationJobs();
    setMessage({
      type: success > 0 ? 'success' : 'error',
      text: `일괄 실행 완료 - 성공 ${success}명, 실패 ${fail}명`,
    });
    if (success) {
      toast.success(`${success}명의 사용자 분류 작업이 큐에 등록되었습니다.`);
    }
    if (fail) {
      toast.error(`${fail}명의 분류 작업을 등록하지 못했습니다.`);
    }
  };

  const motivationTopEntries = combinedSummary?.motivationTop ?? [];
  const categoryTopEntries = combinedSummary?.categoryTop ?? [];
  const motivationSummaryText = formatTopEntriesLine(motivationTopEntries);
  const categorySummaryText = formatTopEntriesLine(categoryTopEntries);

  return (
    <Container>
      <Section>
        <SectionTitle>구독동기/카테고리 분류</SectionTitle>
        <p style={{ fontSize: '0.875rem', color: '#6c757d', marginBottom: '1rem' }}>
          분류 작업은 백그라운드 큐에서 순차적으로 실행됩니다. 완료된 작업은 자동으로 숨겨집니다.
        </p>
        {message && (
          <AlertBox className={message.type === 'error' ? 'error' : undefined}>{message.text}</AlertBox>
        )}
      </Section>

      <Section>
        <QueueHeader>
          <SectionTitle>분류 큐 현황</SectionTitle>
          <QueueActions>
            <Button
              $variant="danger"
              onClick={handleDeleteSelectedJobs}
              disabled={selectedJobIds.length === 0 || deleteLoading}
            >
              <Trash2 size={16} />
              {deleteLoading ? '삭제 중...' : `선택 삭제 (${selectedJobIds.length})`}
            </Button>
            <Button $variant="secondary" onClick={() => refreshClassificationJobs(true)} disabled={queueLoading}>
              <RefreshCw size={16} style={{ animation: queueLoading ? 'spin 1s linear infinite'  : 'none' }} />
              {queueLoading ? '새로고침 중...' : '새로고침'}
            </Button>
          </QueueActions>
        </QueueHeader>

        {classificationJobs.length > 0 ? (
          <QueueTable>
            <thead>
              <tr>
                <QueueHeadCell style={{ width: '2.25rem' }}>
                  <QueueCheckbox
                    checked={selectedJobIds.length > 0 && selectedJobIds.length === classificationJobs.filter(job => job.status !== 'processing').length}
                    onChange={(event) => handleSelectAllJobs(event.target.checked)}
                  />
                </QueueHeadCell>
                <QueueHeadCell>사용자</QueueHeadCell>
                <QueueHeadCell>상태</QueueHeadCell>
                <QueueHeadCell>요청 시간</QueueHeadCell>
                <QueueHeadCell>시작 / 완료</QueueHeadCell>
                <QueueHeadCell>메시지</QueueHeadCell>
              </tr>
            </thead>
            <tbody>
              {classificationJobs.map(job => (
                <QueueRow key={job.job_id}>
                  <QueueCell>
                    <QueueCheckbox
                      checked={selectedJobIds.includes(job.job_id)}
                      disabled={job.status === 'processing' || deleteLoading}
                      onChange={() => toggleJobSelection(job.job_id, job.status)}
                    />
                  </QueueCell>
                  <QueueCell>@{job.username}</QueueCell>
                  <QueueCell>
                    <StatusBadge status={job.status}>{CLASSIFICATION_STATUS_LABELS[job.status]}</StatusBadge>
                  </QueueCell>
                  <QueueCell>{formatDateTime(job.created_at)}</QueueCell>
                  <QueueCell>
                    <div>시작: {formatDateTime(job.started_at)}</div>
                    <div>완료: {formatDateTime(job.completed_at)}</div>
                  </QueueCell>
                  <QueueCell style={{ color: job.status === 'failed' ? '#c92a2a' : '#495057' }}>
                    {job.error_message || '-'}
                  </QueueCell>
                </QueueRow>
              ))}
            </tbody>
          </QueueTable>
        ) : (
          <QueueEmpty>표시할 작업이 없습니다. 새로운 분류 작업을 추가해보세요.</QueueEmpty>
        )}
      </Section>

      <Section>
        <SectionTitle>사용자 빠른 선택</SectionTitle>
        <SearchContainer>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              style={{
                position: 'absolute',
                left: '0.75rem',
                top: '50%',
                transform: 'translateY(-50%)',
                width: '1rem',
                height: '1rem',
                color: '#6c757d',
              }}
            />
            <SearchInput
              type="text"
              value={topSearch}
              onChange={(event) => setTopSearch(event.target.value)}
              placeholder="@username 검색..."
            />
          </div>
          <Button $variant="secondary" onClick={loadUsers} disabled={isLoadingUsers}>
            <RefreshCw size={16} style={{ animation: isLoadingUsers ? 'spin 1s linear infinite'  : 'none' }} />
            {isLoadingUsers ? '로딩...' : '새로고침'}
          </Button>
        </SearchContainer>
        <div style={{ maxHeight: '10rem', overflowY: 'auto', border: '1px solid #dee2e6', borderRadius: '4px', marginTop: '1rem' }}>
          {topFilteredUsers.length === 0 && (
            <div style={{ padding: '0.75rem', fontSize: '0.875rem', color: '#6c757d' }}>검색 결과가 없습니다.</div>
          )}
          {topFilteredUsers.map(user => (
            <ListButton
              key={user.username}
              style={{ background: selectedUser === user.username ? '#e3f2fd' : 'white' }}
              onClick={() => setSelectedUser(user.username)}
            >
              @{user.username}
              <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: '#6c757d' }}>
                {getUserStatusText(user)}
              </span>
            </ListButton>
          ))}
        </div>
      </Section>

      {selectedUser && (
        <Section>
          <SectionTitle>@{selectedUser} 분류 결과</SectionTitle>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <Button
                $variant="danger"
                onClick={handleDeleteUserResults}
                disabled={deleteResultsLoading}
              >
                <Trash2 size={16} /> {deleteResultsLoading ? '삭제 중...' : '분류 결과 삭제'}
              </Button>
              <Button $variant="secondary" onClick={() => loadCombinedSummary(selectedUser)}>
                <RefreshCw size={16} /> 결과 새로고침
              </Button>
            </div>

            {combinedSummary ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <SummaryGrid>
                  <SummaryCard>
                    <SummaryTitle>주요 구독 동기</SummaryTitle>
                    <SummaryValue>
                      {motivationSummaryText || '데이터 없음'}
                    </SummaryValue>
                    {Array.isArray(combinedSummary.motivation_details?.key_factors) && (
                      <SummaryItem>
                        핵심 요인:
                        <ul style={{ margin: '0.35rem 0 0 1rem' }}>
                          {(combinedSummary.motivation_details!.key_factors as string[]).map((factor, index) => (
                            <li key={index} style={{ marginBottom: '0.25rem' }}>{factor}</li>
                          ))}
                        </ul>
                      </SummaryItem>
                    )}
                  </SummaryCard>
                  <SummaryCard>
                    <SummaryTitle>주요 카테고리</SummaryTitle>
                    <SummaryValue>
                      {categorySummaryText || '데이터 없음'}
                    </SummaryValue>
                    {Array.isArray(combinedSummary.category_details?.content_themes) && (
                      <SummaryItem>
                        주요 테마:
                        <ul style={{ margin: '0.35rem 0 0 1rem' }}>
                          {(combinedSummary.category_details!.content_themes as string[]).map((theme, index) => (
                            <li key={index} style={{ marginBottom: '0.25rem' }}>{theme}</li>
                          ))}
                        </ul>
                      </SummaryItem>
                    )}
                  </SummaryCard>
                </SummaryGrid>

                {combinedSummary.overall_analysis && (
                  <SummaryCard>
                    <SummaryTitle>전체 분석</SummaryTitle>
                    {combinedSummary.overall_analysis?.influencer_type && (
                      <SummaryItem>인플루언서 유형: {combinedSummary.overall_analysis.influencer_type}</SummaryItem>
                    )}
                    {Array.isArray(combinedSummary.overall_analysis?.engagement_strategy) && (
                      <SummaryItem>
                        참여 전략:
                        <ul style={{ margin: '0.35rem 0 0 1rem' }}>
                          {(combinedSummary.overall_analysis!.engagement_strategy as string[]).map((strategy, index) => (
                            <li key={index} style={{ marginBottom: '0.25rem' }}>{strategy}</li>
                          ))}
                        </ul>
                      </SummaryItem>
                    )}
                    {combinedSummary.overall_analysis?.target_audience && (
                      <SummaryItem>
                        타겟 오디언스: {JSON.stringify(combinedSummary.overall_analysis.target_audience, null, 2)}
                      </SummaryItem>
                    )}
                    <SummaryItem>
                      갱신 시각: {combinedSummary.timestamp ? formatDateTime(combinedSummary.timestamp) : '-'}
                    </SummaryItem>
                  </SummaryCard>
                )}
              </div>
            ) : (
              <EmptyPlaceholder>
                <BarChart3 size={32} style={{ marginBottom: '0.5rem', color: '#dee2e6' }} />
                <p>아직 분류 결과가 없습니다.</p>
              </EmptyPlaceholder>
            )}
          </div>
        </Section>
      )}

      {selectedUser && (
        <Section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', gap: '0.75rem', flexWrap: 'wrap' }}>
            <SectionTitle>개별 릴스 분류 결과</SectionTitle>
            <div style={{ display: 'inline-flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <Button $variant="secondary" onClick={() => loadIndividualReelClassifications(selectedUser)}>
                <RefreshCw size={16} /> 데이터 새로고침
              </Button>
              <Button
                $variant="secondary"
                onClick={() => setShowIndividualReels(prev => !prev)}
                disabled={!individualReelData || individualReelData.reels.length === 0}
              >
                {showIndividualReels ? '개별 결과 숨기기' : `개별 결과 보기 (${individualReelData?.reels.length ?? 0}개)`}
              </Button>
            </div>
          </div>

          {individualReelData && individualReelData.reels.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '1rem',
              }}>
                <SummaryCard>
                  <SummaryTitle>분석된 릴스</SummaryTitle>
                  <SummaryValue>{individualReelData.total_reels}</SummaryValue>
                  <SummaryItem>프로필 ID: {individualReelData.profile_id}</SummaryItem>
                </SummaryCard>
              </div>

              {showIndividualReels && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {individualReelData.reels.map((reel: IndividualReelEntry, index) => {
                    const motivation = reel.subscription_motivation;
                    const category = reel.category;
                    const isDeleting = deletingReelIds.includes(reel.reel_db_id);
                    const canDeleteClassification = Boolean(
                      motivation?.label ||
                      category?.label ||
                      motivation?.error ||
                      category?.error
                    );

                    const formatConfidencePercent = (value?: number | null) => {
                      if (value == null) return null;
                      if (value <= 1) {
                        return `${Math.round(value * 100)}%`;
                      }
                      return `${Math.round(value)}%`;
                    };

                    return (
                      <div
                        key={reel.reel_id || reel.reel_db_id || index}
                        style={{
                          border: '1px solid #dee2e6',
                          borderRadius: '8px',
                          padding: '1rem',
                          background: '#f8f9fa',
                        }}
                      >
                        <div style={{ display: 'flex', gap: '1rem' }}>
                          {motivation?.image_url || category?.image_url ? (
                            <img
                              src={motivation?.image_url || category?.image_url || ''}
                              alt={`릴스 ${index + 1}`}
                              style={{ width: '120px', height: '120px', objectFit: 'cover', borderRadius: '6px', border: '1px solid #dee2e6' }}
                              onError={(event) => { (event.currentTarget as HTMLImageElement).style.display = 'none'; }}
                            />
                          ) : (
                            <div
                              style={{
                                width: '120px',
                                height: '120px',
                                borderRadius: '6px',
                                border: '1px dashed #ced4da',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: '#adb5bd',
                                fontSize: '0.85rem',
                              }}
                            >
                              이미지 없음
                            </div>
                          )}

                          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            {canDeleteClassification && (
                              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                                <button
                                  onClick={() => handleDeleteIndividualReel(reel.reel_db_id)}
                                  disabled={isDeleting}
                                  style={{
                                    backgroundColor: '#e74c3c',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    padding: '0.35rem 0.75rem',
                                    fontSize: '0.75rem',
                                    cursor: isDeleting ? 'not-allowed' : 'pointer',
                                  }}
                                >
                                  {isDeleting ? '삭제 중...' : '분류 삭제'}
                                </button>
                              </div>
                            )}
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                              <div>
                                <SummaryTitle style={{ marginBottom: '0.25rem' }}>구독 동기</SummaryTitle>
                                <SummaryValue style={{ fontSize: '1rem' }}>{motivation?.label || '분류 대기'}</SummaryValue>
                                {formatConfidencePercent(motivation?.confidence) && (
                                  <SummaryItem>신뢰도: {formatConfidencePercent(motivation?.confidence)}</SummaryItem>
                                )}
                                {motivation?.reasoning && (
                                  <SummaryItem>근거: {motivation.reasoning}</SummaryItem>
                                )}
                                {motivation?.error && (
                                  <SummaryItem style={{ color: '#c92a2a' }}>오류: {motivation.error}</SummaryItem>
                                )}
                              </div>
                              <div>
                                <SummaryTitle style={{ marginBottom: '0.25rem' }}>카테고리</SummaryTitle>
                                <SummaryValue style={{ fontSize: '1rem' }}>{category?.label || '분류 대기'}</SummaryValue>
                                {formatConfidencePercent(category?.confidence) && (
                                  <SummaryItem>신뢰도: {formatConfidencePercent(category?.confidence)}</SummaryItem>
                                )}
                                {category?.reasoning && (
                                  <SummaryItem>근거: {category.reasoning}</SummaryItem>
                                )}
                                {category?.error && (
                                  <SummaryItem style={{ color: '#c92a2a' }}>오류: {category.error}</SummaryItem>
                                )}
                              </div>
                            </div>

                            {reel.caption && (
                              <SummaryItem>캡션: {reel.caption}</SummaryItem>
                            )}
                            {Array.isArray(reel.hashtags) && reel.hashtags.length > 0 && (
                              <SummaryItem>해시태그: {reel.hashtags.join(', ')}</SummaryItem>
                            )}
                            {motivation?.processed_at && (
                              <SummaryItem>분류 시각: {new Date(motivation.processed_at).toLocaleString()}</SummaryItem>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <EmptyPlaceholder>
              <Database size={48} style={{ marginBottom: '1rem', color: '#dee2e6' }} />
              <p>표시할 개별 릴스 분류 결과가 없습니다.</p>
            </EmptyPlaceholder>
          )}
        </Section>
      )}

      <Section>
      <SectionTitle>저장된 프롬프트</SectionTitle>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <label htmlFor="prompt-selector" style={{ fontSize: '0.9rem', color: '#495057', fontWeight: 600 }}>
              사용할 프롬프트
            </label>
            <select
              id="prompt-selector"
              value={selectedPromptType}
              onChange={(event) => handlePromptTypeChange(event.target.value)}
              disabled={promptTypes.length === 0}
              style={{
                padding: '0.5rem 0.75rem',
                borderRadius: '4px',
                border: '1px solid #ced4da',
                fontSize: '0.9rem',
                color: '#495057',
                minWidth: '12rem',
              }}
            >
              {promptTypes.length === 0 ? (
                <option value="" disabled>
                  저장된 프롬프트가 없습니다
                </option>
              ) : (
                promptTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))
              )}
            </select>
            <Button $variant="secondary" onClick={loadPromptTypes}>
              <RefreshCw size={16} /> 프롬프트 새로고침
            </Button>
          </div>
          <Button onClick={runCombined} disabled={!selectedUser || !systemPrompt}>
            <Play size={16} /> 통합 분류 실행
          </Button>
        </div>
        <PromptBox>{systemPrompt || '저장된 프롬프트가 없습니다.'}</PromptBox>
      </Section>

      <Section>
        <SectionTitle>사용자 선택 및 일괄 처리</SectionTitle>
        <SearchContainer style={{ marginBottom: '1rem' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              style={{
                position: 'absolute',
                left: '0.75rem',
                top: '50%',
                transform: 'translateY(-50%)',
                width: '1rem',
                height: '1rem',
                color: '#6c757d',
              }}
            />
            <SearchInput
              type="text"
              value={userSearch}
              onChange={(event) => setUserSearch(event.target.value)}
              placeholder="사용자 검색..."
            />
          </div>
          <Button onClick={toggleAllUsers}>
            <CheckCircle size={16} />
            {selectedUsersForClassification.length === filteredUsers.length && filteredUsers.length > 0 ? '전체 해제' : '전체 선택'}
          </Button>
          <Button onClick={bulkRunCombined} disabled={bulkClassifying || selectedUsersForClassification.length === 0 || !systemPrompt}>
            <Play size={16} />
            {bulkClassifying ? '분류 중...' : `일괄 분류 (${selectedUsersForClassification.length})`}
          </Button>
        </SearchContainer>

        <div style={{ overflowX: 'auto' }}>
          <SelectionTable>
            <thead>
              <tr>
                <SelectionHeadCell style={{ width: '2.25rem' }}>선택</SelectionHeadCell>
                <SelectionHeadCell>사용자명</SelectionHeadCell>
                <SelectionHeadCell>데이터 상태</SelectionHeadCell>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map(user => (
                <SelectionRow key={user.username}>
                  <SelectionCell>
                    <input
                      type="checkbox"
                      checked={selectedUsersForClassification.includes(user.username)}
                      onChange={() => toggleUserSelection(user.username)}
                      style={{ width: '1rem', height: '1rem' }}
                    />
                  </SelectionCell>
                  <SelectionCell>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <UserBadge>{user.username.charAt(0).toUpperCase()}</UserBadge>
                      @{user.username}
                    </div>
                  </SelectionCell>
                  <SelectionCell>{getUserStatusText(user)}</SelectionCell>
                </SelectionRow>
              ))}
            </tbody>
          </SelectionTable>
        </div>

        {filteredUsers.length === 0 && (
          <EmptyPlaceholder>
            <Database size={48} style={{ marginBottom: '1rem', color: '#dee2e6' }} />
            <p>{userSearch ? '검색 결과가 없습니다.' : '사용자 목록이 없습니다.'}</p>
          </EmptyPlaceholder>
        )}
      </Section>
    </Container>
  );
};

export default CombinedClassificationTab;
