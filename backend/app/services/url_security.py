"""远程 URL 安全校验服务。"""
import asyncio
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
    async def is_safe_remote_url(url: str) -> Tuple[bool, str]:
        """
        检查远程 URL 是否安全（异步，不阻塞事件循环）。

        在线导入场景使用：完整解析主机名的所有 IP，
        要求全部为公网地址。

        Returns:
            (是否安全, 错误信息)
        """
        if not url or not isinstance(url, str):
            return False, "URL不能为空"

        try:
            parsed = urlparse(url)
        except ValueError:
            return False, "URL格式不正确"

        if parsed.scheme not in ("http", "https"):
            return False, "仅支持 HTTP/HTTPS 协议"

        if not parsed.hostname:
            return False, "URL格式不正确"

        hostname = parsed.hostname.strip().lower()
        if hostname in DISALLOWED_HOSTNAMES or hostname.endswith(".local"):
            return False, "不允许访问该地址"

        # 字面量 IP 直接检查，避免无谓的解析
        literal_ip = UrlSecurityService._parse_literal_ip(hostname)
        if literal_ip is not None:
            if not UrlSecurityService._is_public_ip(literal_ip):
                return False, "不允许访问该地址"
            return True, ""

        # DNS 解析放到事件循环的默认执行器，避免阻塞其他请求
        try:
            resolved_ips = await UrlSecurityService._aresolve_ip_addresses(hostname)
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
    def is_safe_request_target(url: str) -> bool:
        """
        轻量请求目标检查（同步、无 DNS 解析，用于高频校验场景）。

        拦截本地主机名与私网/回环字面量 IP，防止书源 URL
        被用作 SSRF 跳板。域名形式的 URL 不做解析，直接放行。
        """
        if not url or not isinstance(url, str):
            return False

        try:
            parsed = urlparse(url)
        except ValueError:
            return False

        if parsed.scheme not in ("http", "https"):
            return False

        hostname = (parsed.hostname or "").strip().lower()
        if not hostname:
            return False

        if hostname in DISALLOWED_HOSTNAMES or hostname.endswith(".local"):
            return False

        literal_ip = UrlSecurityService._parse_literal_ip(hostname)
        if literal_ip is not None:
            return UrlSecurityService._is_public_ip(literal_ip)

        return True

    @staticmethod
    def _parse_literal_ip(hostname: str):
        """若主机名是字面量 IP 则返回地址对象，否则返回 None。"""
        try:
            return ipaddress.ip_address(hostname)
        except ValueError:
            return None

    @staticmethod
    async def _aresolve_ip_addresses(
        hostname: str
    ) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        """异步解析主机名对应的 IP 地址列表（去重）。"""
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)

        addresses: list = []
        for _, _, _, _, sockaddr in infos:
            if not sockaddr:
                continue
            ip_obj = ipaddress.ip_address(sockaddr[0])
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
