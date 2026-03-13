# 测试解析服务
import pytest
from app.services.parser import ParserService


class TestParserService:
    """测试JSON解析服务"""

    def test_extract_sources_with_list(self):
        """测试直接数组格式"""
        data = [
            {"bookSourceName": "书源1", "bookSourceUrl": "https://example1.com"},
            {"bookSourceName": "书源2", "bookSourceUrl": "https://example2.com"}
        ]
        result = ParserService.extract_sources(data)
        assert len(result) == 2
        assert result[0]["bookSourceName"] == "书源1"

    def test_extract_sources_with_sources_key(self):
        """测试 sources 包装格式"""
        data = {
            "sources": [
                {"bookSourceName": "书源1", "bookSourceUrl": "https://example1.com"}
            ]
        }
        result = ParserService.extract_sources(data)
        assert len(result) == 1

    def test_extract_sources_with_data_key(self):
        """测试 data 包装格式"""
        data = {
            "data": [
                {"bookSourceName": "书源1", "bookSourceUrl": "https://example1.com"}
            ]
        }
        result = ParserService.extract_sources(data)
        assert len(result) == 1

    def test_extract_sources_with_list_key(self):
        """测试 list 包装格式"""
        data = {
            "list": [
                {"bookSourceName": "书源1", "bookSourceUrl": "https://example1.com"}
            ]
        }
        result = ParserService.extract_sources(data)
        assert len(result) == 1

    def test_extract_sources_with_nested_object(self):
        """测试嵌套对象格式"""
        data = {
            "code": 200,
            "data": {
                "list": [
                    {"bookSourceName": "书源1", "bookSourceUrl": "https://example1.com"}
                ]
            }
        }
        result = ParserService.extract_sources(data)
        assert len(result) == 1

    def test_extract_sources_empty(self):
        """测试空数据"""
        result = ParserService.extract_sources(None)
        assert result == []

        result = ParserService.extract_sources({})
        assert result == []

    def test_validate_json_structure(self):
        """测试JSON结构验证"""
        assert ParserService.validate_json_structure([]) is True
        assert ParserService.validate_json_structure({}) is True
        assert ParserService.validate_json_structure("string") is False
        assert ParserService.validate_json_structure(123) is False