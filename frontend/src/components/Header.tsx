import React from 'react';
import styled from 'styled-components';

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
        핏플루언스 자동화 레포트
      </Title>
      <Subtitle>캠페인 관리 시스템</Subtitle>
    </HeaderContainer>
  );
};

export default Header;