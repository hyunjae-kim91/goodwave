const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // 환경 변수에서 백엔드 URL 가져오기
  // 로컬 환경: localhost:8000
  // Docker 환경: goodwave_backend:8000
  const target = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

  console.log(`[Proxy] Backend target: ${target}`);

  app.use(
    '/api',
    createProxyMiddleware({
      target: target,
      changeOrigin: true,
      logLevel: 'debug',
      // pathRewrite 제거 - 기본적으로 경로 유지
      onProxyReq: (proxyReq, req, res) => {
        // 실제 전송되는 경로 로깅
        const fullPath = proxyReq.path;
        console.log(`[Proxy Request] ${req.method} ${req.url} -> ${target}${fullPath}`);
      },
      onProxyRes: (proxyRes, req, res) => {
        console.log(`[Proxy Response] ${proxyRes.statusCode} ${req.url}`);
      },
      onError: (err, req, res) => {
        console.error('[Proxy Error]', err.message);
        res.status(504).json({ 
          error: 'Backend connection failed', 
          target: target,
          message: err.message 
        });
      }
    })
  );
};

