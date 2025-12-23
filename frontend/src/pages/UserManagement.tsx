import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import axios from 'axios';
import { getToken } from '../services/auth';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';

const Container = styled.div`
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
`;

const Title = styled.h1`
  font-size: 2rem;
  color: #333;
  margin-bottom: 2rem;
`;

const Section = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
`;

const SectionTitle = styled.h2`
  font-size: 1.5rem;
  color: #333;
  margin-bottom: 1.5rem;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
`;

const Th = styled.th`
  text-align: left;
  padding: 0.75rem;
  border-bottom: 2px solid #e0e0e0;
  color: #555;
  font-weight: 600;
`;

const Td = styled.td`
  padding: 0.75rem;
  border-bottom: 1px solid #f0f0f0;
`;

const Button = styled.button<{ variant?: 'primary' | 'danger' | 'secondary' }>`
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  margin-right: 0.5rem;
  transition: background-color 0.2s;

  ${props => {
    if (props.variant === 'danger') {
      return `
        background-color: #e74c3c;
        color: white;
        &:hover {
          background-color: #c0392b;
        }
      `;
    } else if (props.variant === 'secondary') {
      return `
        background-color: #95a5a6;
        color: white;
        &:hover {
          background-color: #7f8c8d;
        }
      `;
    } else {
      return `
        background-color: #3498db;
        color: white;
        &:hover {
          background-color: #2980b9;
        }
      `;
    }
  }}
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const InputGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`;

const Label = styled.label`
  font-size: 0.9rem;
  color: #555;
  font-weight: 500;
`;

const Input = styled.input`
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 4px;
  font-size: 1rem;

  &:focus {
    outline: none;
    border-color: #3498db;
  }
`;

const StatusBadge = styled.span<{ active: boolean }>`
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 500;
  ${props => props.active 
    ? 'background-color: #d4edda; color: #155724;'
    : 'background-color: #f8d7da; color: #721c24;'
  }
`;

const ErrorMessage = styled.div`
  color: #e74c3c;
  padding: 0.75rem;
  background-color: #fee;
  border-radius: 4px;
  margin-bottom: 1rem;
`;

const SuccessMessage = styled.div`
  color: #155724;
  padding: 0.75rem;
  background-color: #d4edda;
  border-radius: 4px;
  margin-bottom: 1rem;
`;

interface User {
  id: number;
  username: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // 새 사용자 생성
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  
  // 비밀번호 변경
  const [oldPassword, setOldPassword] = useState('');
  const [newPasswordChange, setNewPasswordChange] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const token = getToken();
      const response = await axios.get(`${API_BASE_URL}/api/auth/users`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      setUsers(response.data);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || '사용자 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const token = getToken();
      await axios.post(
        `${API_BASE_URL}/api/auth/create-user`,
        null,
        {
          params: {
            username: newUsername,
            password: newPassword,
          },
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      setSuccess('사용자가 생성되었습니다.');
      setNewUsername('');
      setNewPassword('');
      fetchUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || '사용자 생성에 실패했습니다.');
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPasswordChange !== confirmPassword) {
      setError('새 비밀번호가 일치하지 않습니다.');
      return;
    }

    try {
      const token = getToken();
      await axios.put(
        `${API_BASE_URL}/api/auth/change-password`,
        null,
        {
          params: {
            old_password: oldPassword,
            new_password: newPasswordChange,
          },
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      setSuccess('비밀번호가 변경되었습니다.');
      setOldPassword('');
      setNewPasswordChange('');
      setConfirmPassword('');
    } catch (err: any) {
      setError(err.response?.data?.detail || '비밀번호 변경에 실패했습니다.');
    }
  };

  const handleToggleActive = async (userId: number) => {
    if (!window.confirm('사용자 상태를 변경하시겠습니까?')) {
      return;
    }

    try {
      const token = getToken();
      await axios.put(
        `${API_BASE_URL}/api/auth/users/${userId}/toggle-active`,
        null,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      setSuccess('사용자 상태가 변경되었습니다.');
      fetchUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || '사용자 상태 변경에 실패했습니다.');
    }
  };

  const handleDeleteUser = async (userId: number, username: string) => {
    if (!window.confirm(`사용자 '${username}'를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
      return;
    }

    try {
      const token = getToken();
      await axios.delete(`${API_BASE_URL}/api/auth/users/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      setSuccess('사용자가 삭제되었습니다.');
      fetchUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || '사용자 삭제에 실패했습니다.');
    }
  };

  if (loading) {
    return <Container>로딩 중...</Container>;
  }

  return (
    <Container>
      <Title>사용자 관리</Title>

      {error && <ErrorMessage>{error}</ErrorMessage>}
      {success && <SuccessMessage>{success}</SuccessMessage>}

      {/* 비밀번호 변경 */}
      <Section>
        <SectionTitle>내 비밀번호 변경</SectionTitle>
        <Form onSubmit={handleChangePassword}>
          <InputGroup>
            <Label>현재 비밀번호</Label>
            <Input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
            />
          </InputGroup>
          <InputGroup>
            <Label>새 비밀번호</Label>
            <Input
              type="password"
              value={newPasswordChange}
              onChange={(e) => setNewPasswordChange(e.target.value)}
              required
            />
          </InputGroup>
          <InputGroup>
            <Label>새 비밀번호 확인</Label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </InputGroup>
          <Button type="submit">비밀번호 변경</Button>
        </Form>
      </Section>

      {/* 새 사용자 생성 */}
      <Section>
        <SectionTitle>새 사용자 생성</SectionTitle>
        <Form onSubmit={handleCreateUser}>
          <InputGroup>
            <Label>아이디</Label>
            <Input
              type="text"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              required
            />
          </InputGroup>
          <InputGroup>
            <Label>비밀번호</Label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </InputGroup>
          <Button type="submit">사용자 생성</Button>
        </Form>
      </Section>

      {/* 사용자 목록 */}
      <Section>
        <SectionTitle>사용자 목록</SectionTitle>
        <Table>
          <thead>
            <tr>
              <Th>ID</Th>
              <Th>아이디</Th>
              <Th>상태</Th>
              <Th>생성일</Th>
              <Th>작업</Th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <Td>{user.id}</Td>
                <Td>{user.username}</Td>
                <Td>
                  <StatusBadge active={user.is_active}>
                    {user.is_active ? '활성' : '비활성'}
                  </StatusBadge>
                </Td>
                <Td>{new Date(user.created_at).toLocaleDateString('ko-KR')}</Td>
                <Td>
                  <Button
                    variant="secondary"
                    onClick={() => handleToggleActive(user.id)}
                  >
                    {user.is_active ? '비활성화' : '활성화'}
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => handleDeleteUser(user.id, user.username)}
                  >
                    삭제
                  </Button>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Section>
    </Container>
  );
};

export default UserManagement;
