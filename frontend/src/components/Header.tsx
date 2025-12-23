import React from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { logout, getToken } from '../services/auth';

const HeaderContainer = styled.header`
  background-color: #2c3e50;
  color: white;
  padding: 1rem 2rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const LeftSection = styled.div`
  flex: 1;
`;

const Title = styled.h1`
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s ease;

  &:hover {
    opacity: 0.8;
  }
`;

const Subtitle = styled.p`
  margin: 0.25rem 0 0 0;
  font-size: 0.9rem;
  opacity: 0.8;
`;

const RightSection = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
`;

const UserInfo = styled.span`
  font-size: 0.9rem;
  opacity: 0.9;
`;

const LogoutButton = styled.button`
  background-color: #e74c3c;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s;

  &:hover {
    background-color: #c0392b;
  }
`;

const Header: React.FC = () => {
  const navigate = useNavigate();
  const username = localStorage.getItem('username');

  const handleTitleClick = () => {
    navigate('/admin/dashboard');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <HeaderContainer>
      <LeftSection>
        <Title onClick={handleTitleClick}>
          핏플루언스 자동화 레포트
        </Title>
        <Subtitle>캠페인 관리 시스템</Subtitle>
      </LeftSection>
      {getToken() && (
        <RightSection>
          <UserInfo>{username}</UserInfo>
          <LogoutButton onClick={handleLogout}>로그아웃</LogoutButton>
        </RightSection>
      )}
    </HeaderContainer>
  );
};

export default Header;