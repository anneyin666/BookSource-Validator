# 测试去重服务
import pytest
from app.services.deduper import DeduperService


class TestDeduperService:
    """测试去重服务"""

    def test_normalize_url(self):
        """测试URL标准化"""
        # 大小写
        assert DeduperService.normalize_url("https://EXAMPLE.COM") == "https://example.com"
        # 尾部斜杠
        assert DeduperService.normalize_url("https://example.com/") == "https://example.com"
        assert DeduperService.normalize_url("https://example.com///") == "https://example.com"
        # 空格
        assert DeduperService.normalize_url("  https://example.com  ") == "https://example.com"
        # 组合
        assert DeduperService.normalize_url("  HTTPS://Example.COM/  ") == "https://example.com"
        # # 后的制作者信息应被移除
        assert DeduperService.normalize_url("https://example.com#@遇知") == "https://example.com"
        assert DeduperService.normalize_url("https://example.com#🎃") == "https://example.com"
        assert DeduperService.normalize_url("https://www.wxscs.com#🎃") == "https://www.wxscs.com"
        assert DeduperService.normalize_url("https://example.com/#author") == "https://example.com"

    def test_dedupe_basic(self):
        """测试基本去重"""
        sources = [
            {"bookSourceName": "书源A", "bookSourceUrl": "https://example-a.com"},
            {"bookSourceName": "书源B", "bookSourceUrl": "https://example-b.com"},
            {"bookSourceName": "书源A重复", "bookSourceUrl": "https://example-a.com"},  # 重复
        ]
        result, duplicates, duplicate_urls = DeduperService.dedupe(sources)

        assert len(result) == 2
        assert duplicates == 1
        assert result[0]["bookSourceName"] == "书源A"
        assert result[1]["bookSourceName"] == "书源B"
        assert len(duplicate_urls) == 1
        assert duplicate_urls[0]["url"] == "https://example-a.com"
        assert duplicate_urls[0]["count"] == 2

    def test_dedupe_case_insensitive(self):
        """测试大小写不敏感去重"""
        sources = [
            {"bookSourceName": "书源A", "bookSourceUrl": "https://Example.COM"},
            {"bookSourceName": "书源B", "bookSourceUrl": "https://example.com"},  # 大小写不同，应去重
        ]
        result, duplicates, duplicate_urls = DeduperService.dedupe(sources)

        assert len(result) == 1
        assert duplicates == 1

    def test_dedupe_trailing_slash(self):
        """测试尾部斜杠去重"""
        sources = [
            {"bookSourceName": "书源A", "bookSourceUrl": "https://example.com/"},
            {"bookSourceName": "书源B", "bookSourceUrl": "https://example.com"},  # 尾部斜杠不同，应去重
        ]
        result, duplicates, duplicate_urls = DeduperService.dedupe(sources)

        assert len(result) == 1
        assert duplicates == 1

    def test_dedupe_empty_url(self):
        """测试空URL的书源"""
        sources = [
            {"bookSourceName": "有效书源", "bookSourceUrl": "https://example.com"},
            {"bookSourceName": "空URL书源", "bookSourceUrl": ""},
            {"bookSourceName": "无URL书源"},  # 没有bookSourceUrl字段
        ]
        result, duplicates, duplicate_urls = DeduperService.dedupe(sources)

        # 空URL的书源也会被保留
        assert len(result) == 3

    def test_dedupe_whitespace_url(self):
        """测试带空格的URL"""
        sources = [
            {"bookSourceName": "书源A", "bookSourceUrl": "  https://example.com  "},
            {"bookSourceName": "书源B", "bookSourceUrl": "https://example.com"},  # 去空格后重复
        ]
        result, duplicates, duplicate_urls = DeduperService.dedupe(sources)

        assert len(result) == 1
        assert duplicates == 1

    def test_dedupe_empty_list(self):
        """测试空列表"""
        result, duplicates, duplicate_urls = DeduperService.dedupe([])
        assert len(result) == 0
        assert duplicates == 0
        assert len(duplicate_urls) == 0

    def test_dedupe_no_duplicates(self):
        """测试无重复的情况"""
        sources = [
            {"bookSourceName": "书源A", "bookSourceUrl": "https://example-a.com"},
            {"bookSourceName": "书源B", "bookSourceUrl": "https://example-b.com"},
        ]
        result, duplicates, duplicate_urls = DeduperService.dedupe(sources)

        assert len(result) == 2
        assert duplicates == 0
        assert len(duplicate_urls) == 0

    def test_dedupe_with_hash_author(self):
        """测试URL带#制作者信息的去重"""
        sources = [
            {"bookSourceName": "书源A", "bookSourceUrl": "https://example.com#@遇知"},
            {"bookSourceName": "书源B", "bookSourceUrl": "https://example.com#🎃"},
            {"bookSourceName": "书源C", "bookSourceUrl": "https://example.com"},  # 与前两个相同
        ]
        result, duplicates, duplicate_urls = DeduperService.dedupe(sources)

        # #后面的内容被移除，应该去重为1个
        assert len(result) == 1
        assert duplicates == 2
        # 保留第一个书源
        assert result[0]["bookSourceName"] == "书源A"

    def test_normalize_url_chinese_author(self):
        """测试URL后面直接跟着中文作者信息"""
        # URL后面直接跟着中文（没有#分隔）
        assert DeduperService.normalize_url("https://www.hzxsw.com细雨尘寰") == "https://www.hzxsw.com"
        assert DeduperService.normalize_url("https://www.blshuge.com响海") == "https://www.blshuge.com"
        assert DeduperService.normalize_url("https://example.com/path书源作者") == "https://example.com/path"
        # 正常URL不受影响
        assert DeduperService.normalize_url("https://example.com/path") == "https://example.com/path"

    def test_dedupe_with_chinese_author(self):
        """测试URL带中文作者的去重"""
        sources = [
            {"bookSourceName": "书源A", "bookSourceUrl": "https://www.hzxsw.com细雨尘寰"},
            {"bookSourceName": "书源B", "bookSourceUrl": "https://www.hzxsw.com"},
            {"bookSourceName": "书源C", "bookSourceUrl": "https://www.hzxsw.com/"},
        ]
        result, duplicates, duplicate_urls = DeduperService.dedupe(sources)

        # 中文作者被移除，应该去重为1个
        assert len(result) == 1
        assert duplicates == 2