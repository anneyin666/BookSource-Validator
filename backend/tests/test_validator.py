# 测试校验服务
import pytest
from app.services.validator import ValidatorService


class TestValidatorService:
    """测试校验服务"""

    def test_is_format_valid_with_https(self):
        """测试HTTPS URL格式校验"""
        source = {"bookSourceName": "书源", "bookSourceUrl": "https://example.com"}
        assert ValidatorService.is_format_valid(source) is True

    def test_is_format_valid_with_http(self):
        """测试HTTP URL格式校验"""
        source = {"bookSourceName": "书源", "bookSourceUrl": "http://example.com"}
        assert ValidatorService.is_format_valid(source) is True

    def test_is_format_valid_with_empty_url(self):
        """测试空URL"""
        source = {"bookSourceName": "书源", "bookSourceUrl": ""}
        assert ValidatorService.is_format_valid(source) is False

    def test_is_format_valid_with_missing_url(self):
        """测试缺少URL字段"""
        source = {"bookSourceName": "书源"}
        assert ValidatorService.is_format_valid(source) is False

    def test_is_format_valid_with_invalid_protocol(self):
        """测试无效协议"""
        source = {"bookSourceName": "书源", "bookSourceUrl": "ftp://example.com"}
        assert ValidatorService.is_format_valid(source) is False

    def test_is_format_valid_with_whitespace_url(self):
        """测试带空格的URL"""
        source = {"bookSourceName": "书源", "bookSourceUrl": "  https://example.com  "}
        assert ValidatorService.is_format_valid(source) is True

    def test_format_validate(self):
        """测试批量格式校验"""
        sources = [
            {"bookSourceName": "有效1", "bookSourceUrl": "https://example1.com"},
            {"bookSourceName": "有效2", "bookSourceUrl": "http://example2.com"},
            {"bookSourceName": "无效1", "bookSourceUrl": ""},
            {"bookSourceName": "无效2", "bookSourceUrl": "ftp://example.com"},
            {"bookSourceName": "无效3"},  # 缺少URL
        ]
        valid, invalid = ValidatorService.format_validate(sources)

        assert len(valid) == 2
        assert invalid == 3

    def test_set_source_group(self):
        """测试设置书源分组"""
        sources = [
            {"bookSourceName": "书源1", "bookSourceUrl": "https://example1.com"},
            {"bookSourceName": "书源2", "bookSourceUrl": "https://example2.com"},
        ]
        valid_count = 2
        ValidatorService.set_source_group(sources, valid_count)

        # 检查分组格式：YYYY-MM-DD去重有效XXX条
        assert "bookSourceGroup" in sources[0]
        assert "去重有效2条" in sources[0]["bookSourceGroup"]
        assert "去重有效2条" in sources[1]["bookSourceGroup"]

    def test_set_source_group_preserve_original(self):
        """测试设置书源分组 - 保留原有分组"""
        sources = [
            {"bookSourceName": "书源1", "bookSourceUrl": "https://example1.com", "bookSourceGroup": "原分组A"},
            {"bookSourceName": "书源2", "bookSourceUrl": "https://example2.com"},
        ]
        valid_count = 2
        ValidatorService.set_source_group(sources, valid_count)

        # 检查分组格式：原分组保留，新分组追加
        assert "原分组A" in sources[0]["bookSourceGroup"]
        assert "去重有效2条" in sources[0]["bookSourceGroup"]
        assert "," in sources[0]["bookSourceGroup"]  # 有逗号分隔

        # 无原分组的只设置新分组
        assert "去重有效2条" in sources[1]["bookSourceGroup"]
        assert "," not in sources[1]["bookSourceGroup"]

    def test_set_source_group_replace_old_validation(self):
        """测试设置书源分组 - 替换旧的校验分组"""
        sources = [
            {"bookSourceName": "书源1", "bookSourceUrl": "https://example1.com", "bookSourceGroup": "优质,2026-03-10去重有效100条"},
            {"bookSourceName": "书源2", "bookSourceUrl": "https://example2.com", "bookSourceGroup": "2026-01-15去重有效50条,测试"},
        ]
        valid_count = 2
        ValidatorService.set_source_group(sources, valid_count)

        # 检查：旧的校验分组被替换，非校验分组保留
        assert "优质" in sources[0]["bookSourceGroup"]
        assert "2026-03-10去重有效100条" not in sources[0]["bookSourceGroup"]
        assert "去重有效2条" in sources[0]["bookSourceGroup"]

        # 检查：第二个书源的校验分组也被替换
        assert "测试" in sources[1]["bookSourceGroup"]
        assert "2026-01-15去重有效50条" not in sources[1]["bookSourceGroup"]
        assert "去重有效2条" in sources[1]["bookSourceGroup"]