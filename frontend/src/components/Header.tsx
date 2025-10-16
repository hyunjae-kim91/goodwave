import React from 'react';
import styled from 'styled-components';
import { FiTrendingUp } from 'react-icons/fi';

const HeaderContainer = styled.header`
  background-color: #2c3e50;
  color: white;
  padding: 1rem 2rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
`;

const Title = styled.h1`
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  
  svg {
    color: #3498db;
    font-size: 1.8rem;
  }
`;

const Subtitle = styled.p`
  margin: 0.25rem 0 0 0;
  font-size: 0.9rem;
  opacity: 0.8;
`;

const Header: React.FC = () => {
  return (
    <HeaderContainer>
      <Title>
        {React.createElement(FiTrendingUp as any)}
        Goodwave Report
      </Title>
      <Subtitle>인스타그램 & 블로그 데이터 수집 및 보고서 관리 시스템</Subtitle>
    </HeaderContainer>
  );
};

export default Header;