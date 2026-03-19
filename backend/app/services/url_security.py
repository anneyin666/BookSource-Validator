"""远程 URL 安全校验服务。"""
import ipaddress
import socket
from typing import Tuple
from urllib.parse import urlparse


DISALLOWED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
}


class UrlSecurityService:
    """校验远程 URL 是否允许被服务端访问。"""

    @staticmethod
    def is_safe_remote_url(url: str) -> Tuple[bool, str]:
        """
        检查远程 URL 是否安全。

        Returns:
            (是否安全, 错误信息)
        """
        if not url or not isinstance(url, str):
            return False, "URL不能为空"

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, "仅支持 HTTP/HTTPS 协议"

        if not parsed.hostname:
            return False, "URL格式不正确"

        hostname = parsed.hostname.strip().lower()
        if hostname in DISALLOWED_HOSTNAMES or hostname.endswith(".local"):
            return False, "不允许访问该地址"

        try:
            resolved_ips = UrlSecurityService._resolve_ip_addresses(hostname)
        except socket.gaierror:
            return False, "域名解析失败"
        except ValueError:
            return False, "URL格式不正确"

        if not resolved_ips:
            return False, "域名解析失败"

        for ip in resolved_ips:
            if not UrlSecurityService._is_public_ip(ip):
                return False, "不允许访问该地址"

        return True, ""

    @staticmethod
    def _resolve_ip_addresses(
        hostname: str
    ) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        """解析主机名对应的 IP 地址列表。"""
        try:
            return [ipaddress.ip_address(hostname)]
        except ValueError:
            pass

        addresses = []
        for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM):
            if not sockaddr:
                continue
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)
            if ip_obj not in addresses:
                addresses.append(ip_obj)
        return addresses

    @staticmethod
    def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """判断是否为允许访问的公网 IP。"""
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
