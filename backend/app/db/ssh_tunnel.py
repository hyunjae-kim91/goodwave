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
        
        _ssh_tunnel = SSHTunnelForwarder(
            (settings.ssh_host, settings.ssh_port),
            ssh_username=settings.ssh_user,
            ssh_pkey=settings.ssh_pem_key_path,
            remote_bind_address=(settings.rds_host, settings.rds_port),
            local_bind_address=('127.0.0.1', settings.local_tunnel_port),
            allow_agent=False,
            look_for_keys=False,
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

