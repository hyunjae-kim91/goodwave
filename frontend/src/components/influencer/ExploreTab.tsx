import React, { useState, useEffect, useMemo } from 'react';
import styled from 'styled-components';
import toast from 'react-hot-toast';
import {
  Search,
  Users,
  User,
  Eye,
  RefreshCw,
  Database,
  Download,
  X,
  PlayCircle
} from 'lucide-react';
import { influencerApi, UserData, UserDetail, Post } from '../../services/influencer/influencerApi';
import { useUserStore } from '../../store/influencer/userStore';

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

const StatGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
`;

const StatCard = styled.div`
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;

  &.blue {
    background-color: #e3f2fd;
    border-color: #2196f3;
  }

  &.green {
    background-color: #e8f5e8;
    border-color: #4caf50;
  }

  &.orange {
    background-color: #fff3e0;
    border-color: #ff9800;
  }

  &.purple {
    background-color: #f3e5f5;
    border-color: #9c27b0;
  }
`;

const StatValue = styled.div`
  font-size: 2rem;
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 0.5rem;
`;

const StatLabel = styled.div`
  font-size: 0.875rem;
  color: #6c757d;
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

  &.secondary {
    background-color: #95a5a6;
    
    &:hover {
      background-color: #7f8c8d;
    }
  }

  &.danger {
    background-color: #e74c3c;
    
    &:hover {
      background-color: #c0392b;
    }
  }
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const TableHeader = styled.thead`
  background-color: #f8f9fa;
`;

const TableRow = styled.tr`
  &:nth-child(even) {
    background-color: #f8f9fa;
  }
`;

const TableCell = styled.td`
  padding: 0.75rem;
  border-bottom: 1px solid #dee2e6;
  vertical-align: middle;
`;

const TableHeaderCell = styled.th`
  padding: 0.75rem;
  border-bottom: 2px solid #dee2e6;
  text-align: left;
  font-weight: 600;
  color: #495057;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
`;

const DetailGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
`;

const DetailCard = styled.div`
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 1rem;
`;

const DetailLabel = styled.div`
  font-size: 0.75rem;
  font-weight: 600;
  color: #6c757d;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.35rem;
`;

const DetailValue = styled.div`
  font-size: 0.95rem;
  color: #2c3e50;
  font-weight: 500;
  word-break: break-word;
`;

const ReelTableWrapper = styled.div`
  overflow-x: auto;
  border: 1px solid #e9ecef;
  border-radius: 8px;
`;

const ReelTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;

  th,
  td {
    padding: 0.75rem;
    border-bottom: 1px solid #f1f3f5;
    vertical-align: middle;
  }

  thead {
    background: #f8f9fa;
    text-transform: uppercase;
    font-size: 0.75rem;
    color: #6c757d;
    letter-spacing: 0.04em;
  }
`;

const ReelCaptionContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
`;

const ReelMediaLink = styled.a`
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  font-size: 0.75rem;
  color: #1c7ed6;
  text-decoration: none;
  word-break: break-all;

  &:hover {
    text-decoration: underline;
  }
`;

const ReelMediaFallback = styled.span`
  font-size: 0.75rem;
  color: #adb5bd;
`;

const ReelCaptionText = styled.div`
  color: #212529;
  line-height: 1.4;
  word-break: break-word;
`;

const ReelPreview = styled.img`
  display: block;
  width: 88px;
  height: 120px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #dee2e6;
  background: #f8f9fa;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
`;

const ReelPreviewFallback = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 88px;
  height: 120px;
  border-radius: 8px;
  border: 1px dashed #ced4da;
  background: #f8f9fa;
  color: #adb5bd;
  font-size: 0.75rem;
  text-align: center;
  padding: 0.5rem;
`;

const BioBox = styled.div`
  background: #f5f7fb;
  border-radius: 8px;
  border: 1px solid #dde4f0;
  padding: 1rem;
  font-size: 0.9rem;
  color: #495057;
  line-height: 1.6;
  margin-bottom: 1.5rem;
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 2rem;
  color: #6c757d;
  background: #f8f9fa;
  border-radius: 8px;
`;

// UserData와 UserDetail은 이제 influencerApi에서 import됨

const ExploreTab: React.FC = () => {
  const { selectedUser: globalSelectedUser, setSelectedUser: setGlobalSelectedUser } = useUserStore();
  const [users, setUsers] = useState<UserData[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'username' | 'lastModified'>('lastModified');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedUsersForDownload, setSelectedUsersForDownload] = useState<string[]>([]);
  const [deleting, setDeleting] = useState(false);

  // 사용자 목록 로드
  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await influencerApi.getUsers();
      setUsers(data.users || []);
    } catch (error) {
      console.error('사용자 목록 로드 실패:', error);
      toast.error('사용자 목록을 불러오는데 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  // 특정 사용자 상세 정보 로드
  const loadUserDetail = async (username: string) => {
    try {
      setLoading(true);
      const data = await influencerApi.getUserData(username);
      setSelectedUser(data);
      setGlobalSelectedUser(username);
    } catch (error) {
      console.error('사용자 상세 정보 로드 실패:', error);
      toast.error('사용자 상세 정보를 불러오는데 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  // 선택 삭제
  const deleteSelectedUsers = async () => {
    if (selectedUsersForDownload.length === 0) {
      toast.error('삭제할 사용자를 선택해주세요');
      return;
    }
    try {
      setDeleting(true);
      toast.loading(`${selectedUsersForDownload.length}명의 사용자 삭제 중...`);
      const data = await influencerApi.deleteUsers(selectedUsersForDownload);
      toast.dismiss();
      toast.success(`삭제 완료: ${data.deleted_count}명, 실패: ${data.failed_count}명`);
      await loadUsers();
      setSelectedUsersForDownload([]);
    } catch (e: any) {
      toast.dismiss();
      toast.error(`삭제 실패: ${e.message}`);
    } finally {
      setDeleting(false);
    }
  };

  // 사용자 선택/해제 토글 함수
  const toggleUserSelection = (username: string) => {
    setSelectedUsersForDownload(prev => 
      prev.includes(username) 
        ? prev.filter(u => u !== username)
        : [...prev, username]
    );
  };

  // 전체 사용자 선택/해제 토글 함수
  const toggleAllUsers = () => {
    if (selectedUsersForDownload.length === filteredAndSortedUsers.length) {
      setSelectedUsersForDownload([]);
    } else {
      setSelectedUsersForDownload(filteredAndSortedUsers.map(u => u.username));
    }
  };

  // 컴포넌트 마운트 시 사용자 목록 로드
  useEffect(() => {
    loadUsers();
  }, []);

  // 검색 및 정렬된 사용자 목록
  const filteredAndSortedUsers = (users || [])
    .filter(user => 
      user.username.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === 'username') {
        return sortOrder === 'asc' 
          ? a.username.localeCompare(b.username)
          : b.username.localeCompare(a.username);
      } else {
        const aTime = a.lastModified || 0;
        const bTime = b.lastModified || 0;
        return sortOrder === 'asc' ? aTime - bTime : bTime - aTime;
      }
    });

  // 숫자 및 날짜 포맷팅
  const formatNumber = (num?: number): string => {
    if (num === undefined || num === null) return '0';
    if (num >= 10000) {
      return `${(num / 10000).toFixed(1)}만`;
    }
    return num.toString();
  };

  const formatDate = (value?: string): string => {
    if (!value) return '-';
    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toISOString().slice(0, 10);
    }
    return value.slice(0, 10);
  };

  const removeS3Urls = (text: string): string => {
    const s3Pattern = /https?:\/\/[\w.-]*s3[\w.-]*\.[^\s)]+/gi;
    return text.replace(s3Pattern, '').replace(/\s{2,}/g, ' ').trim();
  };

  const formatCaption = (caption?: string): string => {
    if (!caption) return '-';
    const sanitized = removeS3Urls(caption);
    if (!sanitized) return '-';
    return sanitized.length > 120 ? `${sanitized.slice(0, 117)}...` : sanitized;
  };

  const formatMediaUrl = (url: string): string => {
    try {
      const parsed = new URL(url);
      const host = parsed.hostname.replace(/^www\./, '');
      const path = parsed.pathname && parsed.pathname !== '/' ? parsed.pathname : '';
      const truncatedPath = path.length > 32 ? `${path.slice(0, 29)}...` : path;
      const query = parsed.search ? '?' : '';
      return `${host}${truncatedPath}${query}` || host;
    } catch (error) {
      const safeUrl = url.trim();
      return safeUrl.length > 40 ? `${safeUrl.slice(0, 37)}...` : safeUrl;
    }
  };

  const reels: Post[] = selectedUser?.reels ?? [];

  const getReelDateValue = (reel: Post): number => {
    const rawDate = reel.date_posted || reel.timestamp;
    if (!rawDate) {
      return 0;
    }

    const parsed = new Date(rawDate);
    return Number.isNaN(parsed.getTime()) ? 0 : parsed.getTime();
  };

  const sortedReels = useMemo<Post[]>(() => {
    if (!Array.isArray(reels)) {
      return [];
    }

    return [...reels].sort((a, b) => getReelDateValue(b) - getReelDateValue(a));
  }, [reels]);

  const isS3Url = (url: string): boolean => /s3[.-]/i.test(url);

  const getPrimaryMediaUrl = (reel: Post): string | undefined => {
    const mediaUrls: string[] = Array.isArray(reel.mediaUrls) ? reel.mediaUrls : [];
    const legacyMedia = (reel as unknown as { media_urls?: string[] }).media_urls;
    const legacyMediaUrls: string[] = Array.isArray(legacyMedia) ? legacyMedia : [];
    const photoUrls: string[] = Array.isArray(reel.photos) ? reel.photos : [];

    return [...mediaUrls, ...legacyMediaUrls, ...photoUrls].find((candidate) => {
      return typeof candidate === 'string' && candidate.trim().length > 0;
    });
  };

  const getReelPreviewUrl = (reel: Post): string | undefined => {
    const mediaUrls: string[] = Array.isArray(reel.mediaUrls) ? reel.mediaUrls : [];
    const legacyMedia = (reel as unknown as { media_urls?: string[] }).media_urls;
    const legacyMediaUrls: string[] = Array.isArray(legacyMedia) ? legacyMedia : [];
    const photoUrls: string[] = Array.isArray(reel.photos) ? reel.photos : [];

    const candidates = [
      reel.thumbnail_url,
      ...mediaUrls,
      ...legacyMediaUrls,
      ...photoUrls
    ].filter(Boolean) as string[];

    if (!candidates.length) {
      return undefined;
    }

    const imageCandidate = candidates.find((url) => {
      const normalized = url.split('?')[0].toLowerCase();
      return /(\.jpg|\.jpeg|\.png|\.webp|\.gif)$/.test(normalized);
    });

    return imageCandidate || candidates[0];
  };

  return (
    <Container>
      <Section>
        <SectionTitle>수집된 데이터 탐색</SectionTitle>
        
        <StatGrid>
          <StatCard className="blue">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
              <Users size={32} style={{ color: '#2196f3' }} />
            </div>
            <StatValue style={{ color: '#2196f3' }}>{users.length}</StatValue>
            <StatLabel>총 사용자</StatLabel>
          </StatCard>
          
          <StatCard className="green">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
              <User size={32} style={{ color: '#4caf50' }} />
            </div>
            <StatValue style={{ color: '#4caf50' }}>
              {(users || []).filter(u => u.hasProfile).length}
            </StatValue>
            <StatLabel>프로필 있음</StatLabel>
          </StatCard>
          <StatCard className="orange">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
              <Download size={32} style={{ color: '#ff9800' }} />
            </div>
            <StatValue style={{ color: '#ff9800' }}>{selectedUsersForDownload.length}</StatValue>
            <StatLabel>선택된 사용자</StatLabel>
          </StatCard>
        </StatGrid>
        
        <SearchContainer>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', width: '1rem', height: '1rem', color: '#6c757d' }} />
            <SearchInput
              type="text"
              placeholder="사용자명으로 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'username' | 'lastModified')}
              style={{ padding: '0.75rem', border: '1px solid #ced4da', borderRadius: '4px' }}
            >
              <option value="username">사용자명순</option>
              <option value="lastModified">최근 수정순</option>
            </select>
            
            <button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              style={{ padding: '0.75rem', border: '1px solid #ced4da', borderRadius: '4px', background: 'white' }}
            >
              {sortOrder === 'asc' ? '↑' : '↓'}
            </button>
            
            <Button onClick={loadUsers} disabled={loading}>
              <RefreshCw size={16} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
              새로고침
            </Button>
            
            <Button 
              className="danger"
              onClick={deleteSelectedUsers}
              disabled={deleting || selectedUsersForDownload.length === 0}
            >
              <X size={16} />
              {deleting ? '삭제 중...' : `선택 삭제 (${selectedUsersForDownload.length}명)`}
            </Button>
          </div>
        </SearchContainer>
      </Section>

      <Section>
        <SectionTitle>사용자 목록</SectionTitle>
        
        <div style={{ overflowX: 'auto' }}>
          <Table>
            <TableHeader>
              <tr>
                <TableHeaderCell>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <input
                      type="checkbox"
                      checked={selectedUsersForDownload.length === filteredAndSortedUsers.length && filteredAndSortedUsers.length > 0}
                      onChange={toggleAllUsers}
                      style={{ marginRight: '0.5rem' }}
                    />
                    선택
                  </div>
                </TableHeaderCell>
                <TableHeaderCell>사용자명</TableHeaderCell>
                <TableHeaderCell>프로필</TableHeaderCell>
                <TableHeaderCell>릴스</TableHeaderCell>
                <TableHeaderCell>작업</TableHeaderCell>
              </tr>
            </TableHeader>
            <tbody>
              {filteredAndSortedUsers.map((user) => (
                <TableRow key={user.username}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedUsersForDownload.includes(user.username)}
                      onChange={() => toggleUserSelection(user.username)}
                    />
                  </TableCell>
                  <TableCell>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <div style={{
                        width: '2rem',
                        height: '2rem',
                        borderRadius: '50%',
                        background: globalSelectedUser === user.username ? '#3498db' : 'linear-gradient(45deg, #e91e63, #9c27b0)',
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: '600',
                        fontSize: '0.875rem',
                        marginRight: '0.75rem'
                      }}>
                        {user.username.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        @{user.username}
                        {globalSelectedUser === user.username && (
                          <span style={{
                            marginLeft: '0.5rem',
                            padding: '0.125rem 0.5rem',
                            background: '#e3f2fd',
                            color: '#2196f3',
                            fontSize: '0.75rem',
                            borderRadius: '9999px'
                          }}>
                            선택됨
                          </span>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.75rem',
                      fontWeight: '600',
                      borderRadius: '9999px',
                      background: user.hasProfile ? '#e8f5e8' : '#ffebee',
                      color: user.hasProfile ? '#4caf50' : '#f44336'
                    }}>
                      {user.hasProfile ? '있음' : '없음'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.75rem',
                      fontWeight: '600',
                      borderRadius: '9999px',
                      background: user.hasReels ? '#e8f5e8' : '#ffebee',
                      color: user.hasReels ? '#4caf50' : '#f44336'
                    }}>
                      {user.hasReels ? '있음' : '없음'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <button
                      onClick={() => loadUserDetail(user.username)}
                      disabled={loading}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        color: '#3498db',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '0.875rem'
                      }}
                    >
                      <Eye size={16} />
                      상세보기
                    </button>
                  </TableCell>
                </TableRow>
              ))}
            </tbody>
          </Table>
        </div>
        
        {filteredAndSortedUsers.length === 0 && (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#6c757d' }}>
            <Database size={48} style={{ margin: '0 auto 1rem', color: '#dee2e6' }} />
            <p>{searchTerm ? '검색 결과가 없습니다.' : '수집된 데이터가 없습니다.'}</p>
          </div>
        )}
      </Section>

      {/* 선택된 사용자 상세 정보 */}
      {selectedUser && (
        <Section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <SectionTitle>@{selectedUser.username} 상세 정보</SectionTitle>
            <button
              onClick={() => setSelectedUser(null)}
              style={{ background: 'none', border: 'none', color: '#6c757d', cursor: 'pointer' }}
            >
              <X size={20} />
            </button>
          </div>
          
          {/* 프로필 정보 */}
          {selectedUser.profile && (
            <div style={{ marginBottom: '2rem' }}>
              <h4 style={{ fontWeight: '600', marginBottom: '1rem' }}>프로필 정보</h4>
              <DetailGrid>
                <DetailCard>
                  <DetailLabel>계정</DetailLabel>
                  <DetailValue>@{selectedUser.profile.username}</DetailValue>
                </DetailCard>
                {selectedUser.profile.profile_name && (
                  <DetailCard>
                    <DetailLabel>닉네임</DetailLabel>
                    <DetailValue>{selectedUser.profile.profile_name}</DetailValue>
                  </DetailCard>
                )}
                {selectedUser.profile.category_name && (
                  <DetailCard>
                    <DetailLabel>카테고리</DetailLabel>
                    <DetailValue>{selectedUser.profile.category_name}</DetailValue>
                  </DetailCard>
                )}
                {selectedUser.profile.posts_count !== undefined && (
                  <DetailCard>
                    <DetailLabel>누적 게시물</DetailLabel>
                    <DetailValue>{formatNumber(selectedUser.profile.posts_count)}</DetailValue>
                  </DetailCard>
                )}
                {selectedUser.profile.followers !== undefined && (
                  <DetailCard>
                    <DetailLabel>팔로워</DetailLabel>
                    <DetailValue>{formatNumber(selectedUser.profile.followers)}</DetailValue>
                  </DetailCard>
                )}
                {selectedUser.profile.following !== undefined && (
                  <DetailCard>
                    <DetailLabel>팔로우</DetailLabel>
                    <DetailValue>{formatNumber(selectedUser.profile.following)}</DetailValue>
                  </DetailCard>
                )}
                {selectedUser.profile.avg_engagement !== undefined && (
                  <DetailCard>
                    <DetailLabel>평균 참여율</DetailLabel>
                    <DetailValue>{selectedUser.profile.avg_engagement ? `${Math.round(selectedUser.profile.avg_engagement * 100)}%` : '-'}</DetailValue>
                  </DetailCard>
                )}
                {selectedUser.profile.email_address && (
                  <DetailCard>
                    <DetailLabel>이메일</DetailLabel>
                    <DetailValue>{selectedUser.profile.email_address}</DetailValue>
                  </DetailCard>
                )}
                <DetailCard>
                  <DetailLabel>계정 유형</DetailLabel>
                  <DetailValue>{selectedUser.profile.is_business_account ? '비즈니스' : selectedUser.profile.is_professional_account ? '프로페셔널' : '개인'}</DetailValue>
                </DetailCard>
                <DetailCard>
                  <DetailLabel>인증 뱃지</DetailLabel>
                  <DetailValue>{selectedUser.profile.is_verified ? '있음' : '없음'}</DetailValue>
                </DetailCard>
              </DetailGrid>

              {selectedUser.profile.bio && (
                <BioBox>
                  <strong style={{ display: 'block', marginBottom: '0.5rem', color: '#2c3e50' }}>소개</strong>
                  {selectedUser.profile.bio}
                </BioBox>
              )}
            </div>
          )}

          <div style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h4 style={{ fontWeight: '600' }}>릴스 정보</h4>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: '#6c757d' }}>
                <PlayCircle size={16} /> 총 {reels.length}개
              </div>
            </div>

            {reels.length === 0 ? (
              <EmptyState>
                <PlayCircle size={28} style={{ marginBottom: '0.5rem', color: '#dee2e6' }} />
                <p>수집된 릴스가 없습니다</p>
                <p style={{ fontSize: '0.85rem', marginTop: '0.35rem' }}>탐색 탭에서 릴스 수집 옵션을 활성화하고 다시 시도해주세요.</p>
              </EmptyState>
            ) : (
              <ReelTableWrapper>
                <ReelTable>
                  <thead>
                    <tr>
                      <th style={{ width: '40%' }}>캡션</th>
                      <th style={{ width: '120px' }}>미리보기</th>
                      <th>게시일자</th>
                      <th>좋아요</th>
                      <th>댓글</th>
                      <th>조회수</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedReels.map((reel, index) => {
                      const previewUrl = getReelPreviewUrl(reel);
                      const primaryMediaUrl = getPrimaryMediaUrl(reel);
                      const displayMediaLink = Boolean(primaryMediaUrl && !isS3Url(primaryMediaUrl));
                      const legacyExternalUrl = (reel as unknown as { url?: string; external_url?: string }).url
                        || (reel as unknown as { url?: string; external_url?: string }).external_url
                        || reel.profile_url;
                      const externalUrl = displayMediaLink ? primaryMediaUrl : legacyExternalUrl;
                      const previewContent = previewUrl ? (
                        <ReelPreview src={previewUrl} alt={`${selectedUser?.username || '릴스'} 미리보기`} loading="lazy" />
                      ) : (
                        <ReelPreviewFallback>미리보기 없음</ReelPreviewFallback>
                      );
                      return (
                      <tr key={reel.id || reel.timestamp || index}>
                        <td>
                          <ReelCaptionContainer>
                            {displayMediaLink ? (
                              <ReelMediaLink
                                href={primaryMediaUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                title={primaryMediaUrl}
                              >
                                {formatMediaUrl(primaryMediaUrl || '')}
                              </ReelMediaLink>
                            ) : (
                              <ReelMediaFallback>미디어 URL 없음</ReelMediaFallback>
                            )}
                            <ReelCaptionText>{formatCaption(reel.caption)}</ReelCaptionText>
                          </ReelCaptionContainer>
                        </td>
                        <td>
                          {externalUrl ? (
                            <a href={externalUrl} target="_blank" rel="noopener noreferrer">
                              {previewContent}
                            </a>
                          ) : previewContent}
                        </td>
                        <td>{formatDate(reel.date_posted || reel.timestamp)}</td>
                        <td>{formatNumber(reel.likes)}</td>
                        <td>{formatNumber(reel.num_comments)}</td>
                        <td>{formatNumber(reel.video_play_count ?? reel.views)}</td>
                      </tr>
                      );
                    })}
                  </tbody>
                </ReelTable>
              </ReelTableWrapper>
            )}
          </div>
        </Section>
      )}
    </Container>
  );
};

export default ExploreTab;
