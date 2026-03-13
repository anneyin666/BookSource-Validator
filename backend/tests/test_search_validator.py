# 测试搜索校验服务
import pytest
from app.services.search_validator import SearchValidatorService


class TestSearchValidatorService:
    """测试搜索校验服务"""

    def test_build_search_request_direct_url(self):
        """测试直接URL"""
        url, method, post_data = SearchValidatorService.build_search_request(
            "https://example.com/search?q={{key}}",
            "玄幻"
        )
        assert url == "https://example.com/search?q=玄幻"
        assert method == "GET"
        assert post_data is None

    def test_build_search_request_with_encode(self):
        """测试URL编码"""
        url, method, post_data = SearchValidatorService.build_search_request(
            "https://example.com/search?q={{key|encode}}",
            "玄幻"
        )
        assert "q=%E7%8E%84%E5%B9%BB" in url  # URL编码的"玄幻"
        assert method == "GET"

    def test_build_search_request_post_format(self):
        """测试POST格式"""
        url, method, post_data = SearchValidatorService.build_search_request(
            'https://example.com/search/,{"method":"POST","body":"q={{key}}"}',
            "玄幻"
        )
        assert url == "https://example.com/search/"
        assert method == "POST"
        assert post_data == "q=玄幻"

    def test_build_search_request_relative_path(self):
        """测试相对路径（不带前导斜杠）"""
        url, method, post_data = SearchValidatorService.build_search_request(
            "modules/article/search.php?k={{key}}",
            "玄幻",
            "https://example.com"
        )
        assert url == "https://example.com/modules/article/search.php?k=玄幻"
        assert method == "GET"

    def test_build_search_request_relative_path_with_leading_slash(self):
        """测试相对路径（带前导斜杠）"""
        url, method, post_data = SearchValidatorService.build_search_request(
            "/search/api?q={{key}}",
            "玄幻",
            "https://example.com"
        )
        assert url == "https://example.com/search/api?q=玄幻"
        assert method == "GET"

    def test_build_search_request_relative_path_post(self):
        """测试相对路径POST格式"""
        url, method, post_data = SearchValidatorService.build_search_request(
            '/search/,{"method":"POST","body":"q={{key}}"}',
            "玄幻",
            "https://example.com"
        )
        assert url == "https://example.com/search/"
        assert method == "POST"
        assert post_data == "q=玄幻"

    def test_build_search_request_base_url_with_chinese(self):
        """测试base_url包含中文字符"""
        # 模拟书源URL包含中文的情况
        url, method, post_data = SearchValidatorService.build_search_request(
            "/search?q={{key}}",
            "玄幻",
            "https://example.com/作者信息"
        )
        # 应该正确提取域名部分
        assert url.startswith("https://example.com")
        assert "q=玄幻" in url

    def test_build_search_request_multiline_json(self):
        """测试多行JSON配置格式"""
        # 模拟实际书源的多行格式
        search_url = '''https://www.example.com/search/,{
  "body": "searchkey={{key}}&type=articlename",
  "charset": "UTF-8",
  "method": "POST"
}'''
        url, method, post_data = SearchValidatorService.build_search_request(
            search_url,
            "玄幻"
        )
        assert url == "https://www.example.com/search/"
        assert method == "POST"
        assert post_data == "searchkey=玄幻&type=articlename"

    def test_build_search_request_json_with_charset(self):
        """测试带charset字段的JSON配置"""
        url, method, post_data = SearchValidatorService.build_search_request(
            'https://example.com/search,{"method":"POST","body":"q={{key}}","charset":"UTF-8"}',
            "玄幻"
        )
        assert url == "https://example.com/search"
        assert method == "POST"
        assert post_data == "q=玄幻"

    def test_has_search_rule_with_searchurl(self):
        """测试搜索规则检测 - 有searchUrl"""
        source = {
            "searchUrl": "https://example.com/search?q={{key}}"
        }
        assert SearchValidatorService.has_search_rule(source) is True

    def test_has_search_rule_without_searchurl(self):
        """测试搜索规则检测 - 无searchUrl"""
        source = {
            "bookSourceUrl": "https://example.com"
        }
        assert SearchValidatorService.has_search_rule(source) is False

    def test_has_explore_rule_with_exploreurl(self):
        """测试发现规则检测 - 有exploreUrl"""
        source = {
            "exploreUrl": "推荐::https://example.com/recommend"
        }
        assert SearchValidatorService.has_explore_rule(source) is True

    def test_has_explore_rule_without_exploreurl(self):
        """测试发现规则检测 - 无exploreUrl"""
        source = {
            "bookSourceUrl": "https://example.com"
        }
        assert SearchValidatorService.has_explore_rule(source) is False