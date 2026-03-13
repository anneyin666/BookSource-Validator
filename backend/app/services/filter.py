# 书源过滤服务
import re
from typing import List, Set


class FilterService:
    """书源过滤服务"""

    # bookSourceType 数值映射
    # 0=文字, 1=音频, 2=图片, 3=正版
    SOURCE_TYPES = {
        'audio': 1,      # 听书/音频
        'image': 2,      # 图片/漫画
        'official': 3,   # 正版书籍
    }

    # bookSourceComment / bookSourceName 关键词过滤
    KEYWORDS = {
        'comic': ['漫画', 'manga', 'comic', '动漫', '漫'],
        'video': ['影视', '电影', 'video', 'movie', '电视剧', '剧集'],
        'audio': ['听书', '有声', 'audio', '朗读', 'TTS', '喜马拉雅', 'FM', 'fm', '听', '电台'],
        'official': ['正版', '官方'],
    }

    # 正版网站域名列表（用于URL匹配）
    OFFICIAL_DOMAINS: Set[str] = {
        # 男频向网站
        'qidian.com', 'www.qidian.com',           # 起点中文网
        'zongheng.com', 'www.zongheng.com',       # 纵横中文网
        'chuangshi.qq.com',                        # 创世中文网
        'faloo.com', 'b.faloo.com',               # 飞卢小说网
        '17k.com', 'www.17k.com',                 # 17K小说网
        'ciweimao.com', 'www.ciweimao.com',       # 刺猬猫
        'sfacg.com', 'www.sfacg.com',             # SF轻小说

        # 女频向网站
        'jjwxc.net', 'www.jjwxc.net',             # 晋江文学城
        'hongxiu.com', 'www.hongxiu.com',         # 红袖添香
        'xxsy.net', 'www.xxsy.net',               # 潇湘书院
        'qdmm.com', 'www.qdmm.com',               # 起点女生网
        'yunqi.qq.com',                            # 云起书院
        'readnovel.com', 'www.readnovel.com',     # 小说阅读网
        'xs8.cn', 'www.xs8.cn',                   # 言情小说吧
        'gongzicp.com', 'www.gongzicp.com',       # 长佩文学

        # 综合/免费/移动端平台
        'fanqienovel.com',                         # 番茄小说
        'qimao.com', 'www.qimao.com',             # 七猫小说
        'zhangyue.com', 'www.zhangyue.com',       # 掌阅
        'book.qq.com',                             # QQ阅读
        'read.douban.com',                         # 豆瓣阅读
        'zhihu.com', 'www.zhihu.com',             # 知乎盐选
        'tadu.com', 'www.tadu.com',               # 塔读文学
        'zhulang.com', 'www.zhulang.com',         # 逐浪网
        'shuhai.com', 'www.shuhai.com',           # 书海小说网
        'motie.com', 'www.motie.com',             # 磨铁读书

        # 电子书资源站
        'zxcs.info', 'www.zxcs.info',             # 知轩藏书
        'jiumodiary.com', 'www.jiumodiary.com',   # 鸠摩搜书
    }

    # 正版网站域名前缀（用于模糊匹配）
    OFFICIAL_DOMAIN_PREFIXES = [
        'qidian', 'zongheng', 'chuangshi', 'faloo', '17k',
        'ciweimao', 'sfacg', 'jjwxc', 'hongxiu', 'xxsy',
        'qdmm', 'yunqi', 'readnovel', 'xs8', 'gongzicp',
        'fanqienovel', 'qimao', 'zhangyue', 'douban',
        'zhihu', 'tadu', 'zhulang', 'shuhai', 'motie',
        'zxcs', 'jiumodiary',
    ]

    @staticmethod
    def filter_sources(sources: List[dict], filter_types: List[str]) -> List[dict]:
        """
        过滤指定类型的书源

        同时检查 bookSourceType 数值和 bookSourceComment/bookSourceName 关键词

        Args:
            sources: 书源列表
            filter_types: 要过滤的类型 ['official', 'audio', 'comic', 'video']

        Returns:
            过滤后的书源列表
        """
        if not filter_types:
            return sources

        filtered = []
        for source in sources:
            if FilterService._should_remove(source, filter_types):
                continue
            filtered.append(source)
        return filtered

    @staticmethod
    def _should_remove(source: dict, filter_types: List[str]) -> bool:
        """检查书源是否应该被移除"""
        source_type = source.get('bookSourceType')
        # 同时检查 bookSourceComment 和 bookSourceName
        comment = str(source.get('bookSourceComment', '')).lower()
        name = str(source.get('bookSourceName', '')).lower()
        combined_text = comment + ' ' + name

        # 获取书源URL
        source_url = str(source.get('bookSourceUrl', '')).lower()

        for ftype in filter_types:
            # 检查 bookSourceType 数值
            if source_type is not None and source_type == FilterService.SOURCE_TYPES.get(ftype):
                return True

            # 检查关键词
            if ftype in FilterService.KEYWORDS:
                for keyword in FilterService.KEYWORDS[ftype]:
                    if keyword.lower() in combined_text:
                        return True

            # 检查正版网站域名
            if ftype == 'official':
                # 精确匹配域名
                for domain in FilterService.OFFICIAL_DOMAINS:
                    if domain in source_url:
                        return True
                # 模糊匹配域名前缀
                for prefix in FilterService.OFFICIAL_DOMAIN_PREFIXES:
                    # 匹配 http(s)://prefix. 或 .prefix.
                    if f'//{prefix}.' in source_url or f'.{prefix}.' in source_url:
                        return True

        return False

    @staticmethod
    def get_filter_count(sources: List[dict], filter_types: List[str]) -> int:
        """
        获取将被过滤的书源数量

        Args:
            sources: 书源列表
            filter_types: 要过滤的类型

        Returns:
            将被过滤的数量
        """
        count = 0
        for source in sources:
            if FilterService._should_remove(source, filter_types):
                count += 1
        return count