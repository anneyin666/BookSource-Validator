# JSON解析服务
from typing import Any, List


class ParserService:
    """JSON解析服务"""

    @staticmethod
    def extract_sources(data: Any) -> List[dict]:
        """
        从各种格式中提取书源数组

        支持格式：
        1. 直接数组
        2. { sources: [...] }
        3. { data: [...] }
        4. 嵌套对象（递归查找数组字段）
        """
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            # 尝试常见字段
            for key in ['sources', 'data', 'list']:
                if key in data:
                    if isinstance(data[key], list):
                        return data[key]
                    # 如果是嵌套的字典，递归查找
                    if isinstance(data[key], dict):
                        result = ParserService.extract_sources(data[key])
                        if result:
                            return result

            # 查找第一个数组字段
            for value in data.values():
                if isinstance(value, list):
                    return value
                # 递归查找嵌套字典中的数组
                if isinstance(value, dict):
                    result = ParserService.extract_sources(value)
                    if result:
                        return result

        return []

    @staticmethod
    def validate_json_structure(data: Any) -> bool:
        """验证JSON结构是否有效"""
        if isinstance(data, list):
            return True
        if isinstance(data, dict):
            return True
        return False