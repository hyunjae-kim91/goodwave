import React, { useState, useEffect } from 'react';
import {
  classificationService,
  UserWithClassificationData,
  UsersWithDataResponse,
  ClassificationDataInfo
} from '../../services/influencer/classificationService';

const ClassificationDataManagementTab: React.FC = () => {
  const [users, setUsers] = useState<UserWithClassificationData[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{
    username: string;
    type?: string;
    show: boolean;
  }>({ username: '', show: false });
  const [deleting, setDeleting] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadUsersWithData();
  }, []);

  const loadUsersWithData = async () => {
    try {
      setLoading(true);
      const response: UsersWithDataResponse = await classificationService.getUsersWithClassificationData();
      setUsers(response.users);
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (username: string, type?: string) => {
    setDeleteConfirm({ username, type, show: true });
  };

  const confirmDelete = async () => {
    if (!deleteConfirm.username) return;
    
    try {
      setDeleting(true);
      const response = await classificationService.deleteUserClassificationData(
        deleteConfirm.username, 
        deleteConfirm.type
      );
      
      setMessage({ 
        type: 'success', 
        text: `${response.deleted_count}개의 분류 데이터가 삭제되었습니다.`
      });
      
      // 목록 새로고침
      await loadUsersWithData();
      
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setDeleting(false);
      setDeleteConfirm({ username: '', show: false });
    }
  };

  const cancelDelete = () => {
    setDeleteConfirm({ username: '', show: false });
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '정보 없음';
    return new Date(dateString).toLocaleString();
  };

  const getMethodBadge = (method?: string) => {
    if (method === 'per_reel_classification') {
      return <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">릴스 기반</span>;
    }
    if (method === 'individual_reel_aggregation') {
      return <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">개별 릴스</span>;
    }
    return <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded-full">기존 방식</span>;
  };

  const renderClassificationInfo = (username: string, type: string, info?: ClassificationDataInfo) => {
    if (!info?.exists) {
      return (
        <div className="text-center text-gray-400 py-2">
          <span className="text-sm">데이터 없음</span>
        </div>
      );
    }

    return (
      <div className="p-3 border border-gray-200 rounded-lg bg-gray-50">
        <div className="flex justify-between items-start mb-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-gray-900">
                {info.primary_classification || '분류 없음'}
              </span>
              {info.primary_percentage && (
                <span className="text-sm text-gray-600">
                  ({info.primary_percentage}%)
                </span>
              )}
              {getMethodBadge(info.method)}
            </div>
            <div className="text-xs text-gray-500 space-y-1">
              <div>생성일: {formatDate(info.created_at)}</div>
              {info.total_reels && (
                <div>분석 릴스: {info.total_reels}개</div>
              )}
            </div>
          </div>
          <button
            onClick={() => handleDeleteClick(username, type)}
            className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
          >
            삭제
          </button>
        </div>
      </div>
    );
  };

  const filteredUsers = users.filter(user => 
    user.username.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">분류 데이터 관리</h1>
        <button
          onClick={loadUsersWithData}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {loading ? '로딩...' : '새로고침'}
        </button>
      </div>

      {message && (
        <div className={`mb-4 p-4 rounded-lg ${
          message.type === 'success' 
            ? 'bg-green-100 border border-green-400 text-green-700' 
            : 'bg-red-100 border border-red-400 text-red-700'
        }`}>
          {message.text}
        </div>
      )}

      <div className="mb-4">
        <input
          type="text"
          placeholder="사용자명으로 검색..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {loading ? (
        <div className="text-center py-8">
          <div className="text-gray-500">분류 데이터를 불러오는 중...</div>
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-gray-500">
            {searchTerm ? '검색 결과가 없습니다.' : '분류 데이터가 있는 사용자가 없습니다.'}
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {filteredUsers.map((user) => (
            <div key={user.username} className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">@{user.username}</h3>
                  <p className="text-sm text-gray-500">프로필 ID: {user.profile_id}</p>
                </div>
                <button
                  onClick={() => handleDeleteClick(user.username)}
                  className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                >
                  전체 삭제
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">구독동기</h4>
                  {renderClassificationInfo(user.username, 'subscription_motivation', user.classification_data.subscription_motivation)}
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">카테고리</h4>
                  {renderClassificationInfo(user.username, 'category', user.classification_data.category)}
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">릴스 분류 데이터</h4>
                  {renderClassificationInfo(user.username, 'reel_classification', user.classification_data.reel_classification)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 삭제 확인 다이얼로그 */}
      {deleteConfirm.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md mx-4">
            <h3 className="text-lg font-semibold mb-4">삭제 확인</h3>
            <p className="text-gray-600 mb-6">
              {deleteConfirm.type 
                ? `@${deleteConfirm.username}의 ${deleteConfirm.type} 분류 데이터를 삭제하시겠습니까?`
                : `@${deleteConfirm.username}의 모든 분류 데이터를 삭제하시겠습니까?`
              }
              <br />
              <span className="text-red-600 text-sm">이 작업은 되돌릴 수 없습니다.</span>
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={cancelDelete}
                disabled={deleting}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                취소
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleting}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {deleting ? '삭제 중...' : '삭제'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClassificationDataManagementTab;
