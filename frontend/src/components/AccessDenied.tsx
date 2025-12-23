import React from 'react';
import styled from 'styled-components';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: #f5f5f5;
  padding: 2rem;
`;

const Title = styled.h1`
  font-size: 2rem;
  color: #e74c3c;
  margin-bottom: 1rem;
`;

const Message = styled.p`
  font-size: 1.1rem;
  color: #555;
  text-align: center;
  max-width: 600px;
  line-height: 1.6;
`;

const IPInfo = styled.div`
  margin-top: 1.5rem;
  padding: 1rem;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  font-family: monospace;
  color: #333;
`;

interface AccessDeniedProps {
  ip?: string;
  message?: string;
}

const AccessDenied: React.FC<AccessDeniedProps> = ({ ip, message }) => {
  return (
    <Container>
      <Title>🚫 접근이 거부되었습니다</Title>
      <Message>
        {message || '이 페이지에 접근할 권한이 없습니다.'}
        <br />
        관리자에게 문의하세요.
      </Message>
      {ip && (
        <IPInfo>
          <strong>IP 주소:</strong> {ip}
        </IPInfo>
      )}
    </Container>
  );
};

export default AccessDenied;
