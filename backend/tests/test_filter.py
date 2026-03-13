# 测试过滤服务
import pytest
from app.services.filter import FilterService


class TestFilterService:
    """测试过滤服务"""

    def test_filter_by_type_audio(self):
        """测试过滤听书源 - bookSourceType"""
        sources = [
            {"bookSourceName": "普通书源", "bookSourceUrl": "https://example1.com", "bookSourceType": 0},
            {"bookSourceName": "听书源", "bookSourceUrl": "https://example2.com", "bookSourceType": 1},
            {"bookSourceName": "漫画源", "bookSourceUrl": "https://example3.com", "bookSourceType": 2},
        ]
        result = FilterService.filter_sources(sources, ['audio'])
        assert len(result) == 2
        assert result[0]["bookSourceName"] == "普通书源"
        assert result[1]["bookSourceName"] == "漫画源"

    def test_filter_by_type_official(self):
        """测试过滤正版书籍 - bookSourceType"""
        sources = [
            {"bookSourceName": "普通书源", "bookSourceUrl": "https://example1.com"},
            {"bookSourceName": "正版源", "bookSourceUrl": "https://example2.com", "bookSourceType": 3},
        ]
        result = FilterService.filter_sources(sources, ['official'])
        assert len(result) == 1
        assert result[0]["bookSourceName"] == "普通书源"

    def test_filter_by_keyword_comic(self):
        """测试过滤漫画源 - 关键词"""
        sources = [
            {"bookSourceName": "普通书源", "bookSourceUrl": "https://example1.com"},
            {"bookSourceName": "漫画天堂", "bookSourceUrl": "https://example2.com"},
            {"bookSourceName": "Manga网站", "bookSourceUrl": "https://example3.com"},
        ]
        result = FilterService.filter_sources(sources, ['comic'])
        assert len(result) == 1
        assert result[0]["bookSourceName"] == "普通书源"

    def test_filter_by_keyword_audio(self):
        """测试过滤听书源 - 关键词"""
        sources = [
            {"bookSourceName": "普通书源", "bookSourceUrl": "https://example1.com"},
            {"bookSourceName": "喜马拉雅听书", "bookSourceUrl": "https://example2.com"},
            {"bookSourceName": "FM电台", "bookSourceUrl": "https://example3.com"},
        ]
        result = FilterService.filter_sources(sources, ['audio'])
        assert len(result) == 1
        assert result[0]["bookSourceName"] == "普通书源"

    def test_filter_by_keyword_video(self):
        """测试过滤影视源 - 关键词"""
        sources = [
            {"bookSourceName": "普通书源", "bookSourceUrl": "https://example1.com"},
            {"bookSourceName": "影视大全", "bookSourceUrl": "https://example2.com"},
        ]
        result = FilterService.filter_sources(sources, ['video'])
        assert len(result) == 1

    def test_filter_multiple_types(self):
        """测试过滤多种类型"""
        sources = [
            {"bookSourceName": "普通书源", "bookSourceUrl": "https://example1.com"},
            {"bookSourceName": "听书源", "bookSourceUrl": "https://example2.com", "bookSourceType": 1},
            {"bookSourceName": "漫画源", "bookSourceUrl": "https://example3.com", "bookSourceComment": "漫画"},
        ]
        result = FilterService.filter_sources(sources, ['audio', 'comic'])
        assert len(result) == 1
        assert result[0]["bookSourceName"] == "普通书源"

    def test_filter_empty_types(self):
        """测试空过滤类型"""
        sources = [
            {"bookSourceName": "书源1", "bookSourceUrl": "https://example1.com"},
            {"bookSourceName": "书源2", "bookSourceUrl": "https://example2.com"},
        ]
        result = FilterService.filter_sources(sources, [])
        assert len(result) == 2

    def test_filter_comment_keyword(self):
        """测试 bookSourceComment 关键词过滤"""
        sources = [
            {"bookSourceName": "书源A", "bookSourceUrl": "https://example1.com", "bookSourceComment": "正版书籍"},
            {"bookSourceName": "书源B", "bookSourceUrl": "https://example2.com"},
        ]
        result = FilterService.filter_sources(sources, ['official'])
        assert len(result) == 1
        assert result[0]["bookSourceName"] == "书源B"

    def test_get_filter_count(self):
        """测试获取过滤数量"""
        sources = [
            {"bookSourceName": "普通", "bookSourceUrl": "https://example1.com"},
            {"bookSourceName": "听书", "bookSourceUrl": "https://example2.com", "bookSourceType": 1},
            {"bookSourceName": "漫画", "bookSourceUrl": "https://example3.com", "bookSourceType": 2},
        ]
        count = FilterService.get_filter_count(sources, ['audio', 'comic'])
        assert count == 2

    def test_filter_official_by_domain_qidian(self):
        """测试过滤正版源 - 起点中文网域名"""
        sources = [
            {"bookSourceName": "普通书源", "bookSourceUrl": "https://example.com"},
            {"bookSourceName": "起点", "bookSourceUrl": "https://www.qidian.com"},
            {"bookSourceName": "起点2", "bookSourceUrl": "https://qidian.com/rank"},
        ]
        result = FilterService.filter_sources(sources, ['official'])
        assert len(result) == 1
        assert result[0]["bookSourceName"] == "普通书源"

    def test_filter_official_by_domain_jjwxc(self):
        """测试过滤正版源 - 晋江文学城域名"""
        sources = [
            {"bookSourceName": "普通书源", "bookSourceUrl": "https://example.com"},
            {"bookSourceName": "晋江", "bookSourceUrl": "https://www.jjwxc.net"},
        ]
        result = FilterService.filter_sources(sources, ['official'])
        assert len(result) == 1

    def test_filter_official_by_domain_fanqie(self):
        """测试过滤正版源 - 番茄小说域名"""
        sources = [
            {"bookSourceName": "普通书源", "bookSourceUrl": "https://example.com"},
            {"bookSourceName": "番茄", "bookSourceUrl": "https://fanqienovel.com/page"},
        ]
        result = FilterService.filter_sources(sources, ['official'])
        assert len(result) == 1

    def test_filter_official_multiple_domains(self):
        """测试过滤多个正版网站"""
        sources = [
            {"bookSourceName": "起点", "bookSourceUrl": "https://www.qidian.com"},
            {"bookSourceName": "纵横", "bookSourceUrl": "https://www.zongheng.com"},
            {"bookSourceName": "晋江", "bookSourceUrl": "https://www.jjwxc.net"},
            {"bookSourceName": "七猫", "bookSourceUrl": "https://www.qimao.com"},
            {"bookSourceName": "普通", "bookSourceUrl": "https://example.com"},
        ]
        result = FilterService.filter_sources(sources, ['official'])
        assert len(result) == 1
        assert result[0]["bookSourceName"] == "普通"

    def test_filter_official_domain_prefix(self):
        """测试域名前缀匹配"""
        sources = [
            {"bookSourceName": "普通", "bookSourceUrl": "https://example.com"},
            {"bookSourceName": "起点M", "bookSourceUrl": "https://m.qidian.com"},
            {"bookSourceName": "起点Wap", "bookSourceUrl": "https://wap.qidian.com"},
        ]
        result = FilterService.filter_sources(sources, ['official'])
        assert len(result) == 1