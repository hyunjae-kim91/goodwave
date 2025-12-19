"""
SSH Tunnel management for local development to access RDS via EC2 bastion host.
"""
import logging
from typing import Optional
from sshtunnel import SSHTunnelForwarder
from app.core.config import settings

logger = logging.getLogger(__name__)

_ssh_tunnel: Optional[SSHTunnelForwarder] = None


def start_ssh_tunnel() -> Optional[SSHTunnelForwarder]:
    """
    Start SSH tunnel to RDS via EC2 bastion host.
    Returns the tunnel instance if successful, None otherwise.
    """
    global _ssh_tunnel
    
    if not settings.use_ssh_tunnel:
        logger.info("SSH tunnel is disabled. Using direct database connection.")
        return None
    
    if _ssh_tunnel and _ssh_tunnel.is_active:
        logger.info("SSH tunnel is already active.")
        return _ssh_tunnel
    
    # Validate required settings
    required_settings = [
        settings.ssh_host,
        settings.ssh_user,
        settings.ssh_pem_key_path,
        settings.rds_host,
    ]
    
    if not all(required_settings):
        logger.warning(
            "SSH tunnel is enabled but required settings are missing. "
            "Please set SSH_HOST, SSH_USER, SSH_PEM_KEY_PATH, and RDS_HOST."
        )
        return None
    
    try:
        logger.info(f"Starting SSH tunnel: {settings.ssh_user}@{settings.ssh_host}:{settings.ssh_port}")
        logger.info(f"Tunneling to RDS: {settings.rds_host}:{settings.rds_port} -> localhost:{settings.local_tunnel_port}")
        
        # Windows 경로 처리: ~ 확장 및 경로 정규화
        import os
        from pathlib import Path
        import paramiko
        
        ssh_key_path = settings.ssh_pem_key_path
        if ssh_key_path:
            # ~ 확장
            ssh_key_path = os.path.expanduser(ssh_key_path)
            # 절대 경로로 변환
            ssh_key_path = str(Path(ssh_key_path).resolve())
            logger.info(f"Using SSH key: {ssh_key_path}")
            
            # SSH 키 파일 존재 확인
            if not os.path.exists(ssh_key_path):
                logger.error(f"SSH key file not found: {ssh_key_path}")
                return None
            
            # paramiko를 사용하여 키를 직접 로드 (DSSKey 호환성 문제 해결)
            try:
                # RSA 키 시도
                try:
                    ssh_pkey = paramiko.RSAKey.from_private_key_file(ssh_key_path)
                except:
                    # ED25519 키 시도
                    try:
                        ssh_pkey = paramiko.Ed25519Key.from_private_key_file(ssh_key_path)
                    except:
                        # ECDSA 키 시도
                        try:
                            ssh_pkey = paramiko.ECDSAKey.from_private_key_file(ssh_key_path)
                        except:
                            # 기본적으로 파일 경로 사용
                            ssh_pkey = ssh_key_path
                            logger.warning("Could not load SSH key with paramiko, using file path directly")
            except Exception as e:
                logger.warning(f"Error loading SSH key with paramiko: {e}, using file path directly")
                ssh_pkey = ssh_key_path
        else:
            ssh_pkey = None
        
        # sshtunnel 0.4.0에서는 look_for_keys와 allow_agent 인자가 지원되지 않음
        # paramiko 3.0+ 호환성을 위해 키를 직접 로드하여 전달
        _ssh_tunnel = SSHTunnelForwarder(
            (settings.ssh_host, settings.ssh_port),
            ssh_username=settings.ssh_user,
            ssh_pkey=ssh_pkey,
            remote_bind_address=(settings.rds_host, settings.rds_port),
            local_bind_address=('127.0.0.1', settings.local_tunnel_port),
        )
        
        _ssh_tunnel.start()
        
        if _ssh_tunnel.is_active:
            logger.info(f"SSH tunnel established successfully on localhost:{settings.local_tunnel_port}")
            return _ssh_tunnel
        else:
            logger.error("SSH tunnel failed to start")
            _ssh_tunnel = None
            return None
            
    except Exception as e:
        logger.error(f"Failed to start SSH tunnel: {str(e)}", exc_info=True)
        _ssh_tunnel = None
        return None


def stop_ssh_tunnel():
    """Stop the SSH tunnel if it's active."""
    global _ssh_tunnel
    
    if _ssh_tunnel and _ssh_tunnel.is_active:
        try:
            logger.info("Stopping SSH tunnel...")
            _ssh_tunnel.stop()
            logger.info("SSH tunnel stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping SSH tunnel: {str(e)}", exc_info=True)
        finally:
            _ssh_tunnel = None
    else:
        logger.info("No active SSH tunnel to stop")


def get_tunnel_status() -> dict:
    """Get the current status of the SSH tunnel."""
    global _ssh_tunnel
    
    if not settings.use_ssh_tunnel:
        return {"enabled": False, "active": False}
    
    if _ssh_tunnel is None:
        return {"enabled": True, "active": False, "error": "Tunnel not initialized"}
    
    return {
        "enabled": True,
        "active": _ssh_tunnel.is_active,
        "local_port": settings.local_tunnel_port if _ssh_tunnel.is_active else None,
        "remote_host": settings.rds_host,
        "remote_port": settings.rds_port,
    }

