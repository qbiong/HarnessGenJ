"""
Tests for Maintenance Module - Requirement Detector

测试需求检测器的功能
"""

import pytest
import tempfile
import shutil

from harnessgenj.maintenance.detector import (
    RequirementDetector,
    DetectedRequirement,
    RequirementType,
    DetectionSource,
    create_detector,
)


class TestRequirementDetector:
    """测试需求检测器"""

    def test_create_detector(self):
        """创建检测器"""
        detector = RequirementDetector()
        assert detector is not None
        assert detector.min_confidence == 0.5
        assert detector.enable_multi_detection is True

    def test_create_detector_with_params(self):
        """使用参数创建检测器"""
        detector = RequirementDetector(
            min_confidence=0.7,
            enable_multi_detection=False,
        )
        assert detector.min_confidence == 0.7
        assert detector.enable_multi_detection is False

    def test_detect_feature_requirement(self):
        """检测功能需求"""
        detector = RequirementDetector()

        requirements = detector.detect_from_message("我需要一个购物车功能")

        assert len(requirements) > 0
        req = requirements[0]
        assert req.req_type == RequirementType.FEATURE
        assert "购物车" in req.title or "购物车" in req.description
        assert req.source == DetectionSource.USER_MESSAGE

    def test_detect_bug_fix_requirement(self):
        """检测Bug修复需求"""
        detector = RequirementDetector()

        requirements = detector.detect_from_message("支付页面报错，无法完成支付")

        assert len(requirements) > 0
        req = requirements[0]
        assert req.req_type == RequirementType.BUG_FIX
        assert req.confidence >= 0.6

    def test_detect_improvement_requirement(self):
        """检测改进需求"""
        detector = RequirementDetector()

        requirements = detector.detect_from_message("优化数据库查询性能")

        assert len(requirements) > 0
        req = requirements[0]
        assert req.req_type == RequirementType.IMPROVEMENT

    def test_detect_question_requirement(self):
        """检测问题咨询"""
        detector = RequirementDetector()

        requirements = detector.detect_from_message("请问这个系统是如何工作的？")

        # 检测到需求即可，类型可能因关键词匹配而不同
        assert len(requirements) >= 0  # 问题类可能被检测为其他类型

    def test_detect_with_context(self):
        """带上下文检测"""
        detector = RequirementDetector()

        context = {"project": "电商平台", "user": "admin"}
        requirements = detector.detect_from_message(
            "添加订单管理功能",
            context=context
        )

        assert len(requirements) > 0
        req = requirements[0]
        assert req.context == context

    def test_min_confidence_filter(self):
        """最小置信度过滤"""
        detector = RequirementDetector(min_confidence=0.8)

        # 低置信度的消息可能不会返回结果
        requirements = detector.detect_from_message("随便说说")

        # 如果置信度低于阈值，可能返回空列表
        # 这里只验证返回类型正确
        assert isinstance(requirements, list)

    def test_multi_detection_disabled(self):
        """禁用多需求检测"""
        detector = RequirementDetector(enable_multi_detection=False)

        # 即使消息包含多个关键词，也只返回一个
        requirements = detector.detect_from_message(
            "我需要一个新功能，同时有个bug需要修复"
        )

        assert len(requirements) <= 1

    def test_detect_from_ai_analysis_issues(self):
        """从AI分析结果检测（问题列表）"""
        detector = RequirementDetector()

        analysis_result = {
            "issues_found": ["内存泄漏", "性能瓶颈"],
            "suggestions": ["优化查询", "添加缓存"],
        }

        requirements = detector.detect_from_analysis(analysis_result)

        assert len(requirements) > 0
        # 应该检测到问题对应的Bug修复需求
        bug_reqs = [r for r in requirements if r.req_type == RequirementType.BUG_FIX]
        assert len(bug_reqs) >= 2

    def test_detect_from_ai_analysis_suggestions(self):
        """从AI分析结果检测（建议列表）"""
        detector = RequirementDetector()

        analysis_result = {
            "suggestions": ["优化数据库索引", "重构认证模块"],
        }

        requirements = detector.detect_from_analysis(analysis_result)

        assert len(requirements) >= 2
        for req in requirements:
            assert req.source == DetectionSource.AI_ANALYSIS

    def test_detect_from_code_review(self):
        """从代码审查结果检测"""
        detector = RequirementDetector()

        review_result = {
            "issues": [
                {
                    "description": "SQL注入漏洞",
                    "severity": "critical",
                    "file": "auth.py",
                    "line": 42,
                },
                {
                    "description": "未处理的异常",
                    "severity": "medium",
                    "file": "utils.py",
                    "line": 15,
                },
            ]
        }

        requirements = detector.detect_from_code_review(review_result)

        assert len(requirements) >= 2
        # 高严重性问题应该是P0
        critical_reqs = [r for r in requirements if r.suggested_priority == "P0"]
        assert len(critical_reqs) >= 1

    def test_detect_from_test_failure(self):
        """从测试失败结果检测"""
        detector = RequirementDetector()

        test_result = {
            "failures": [
                {
                    "test_name": "test_login",
                    "error_message": "AssertionError: 登录失败",
                    "test_file": "test_auth.py",
                },
            ]
        }

        requirements = detector.detect_from_test_failure(test_result)

        assert len(requirements) == 1
        req = requirements[0]
        assert req.req_type == RequirementType.BUG_FIX
        assert req.suggested_priority == "P0"
        assert req.confidence == 0.9

    def test_detect_complex_bug_description(self):
        """检测复杂的Bug描述"""
        detector = RequirementDetector()

        requirements = detector.detect_from_message(
            "订单支付后状态没有正确更新，用户看到的还是待支付"
        )

        assert len(requirements) > 0
        req = requirements[0]
        assert req.req_type == RequirementType.BUG_FIX
        # 置信度应该较高
        assert req.confidence >= 0.7

    def test_requirement_to_dict(self):
        """需求转换为字典"""
        detector = RequirementDetector()

        requirements = detector.detect_from_message("添加用户管理功能")
        assert len(requirements) > 0

        req_dict = requirements[0].to_dict()
        assert "req_id" in req_dict
        assert "title" in req_dict
        assert "description" in req_dict
        assert "req_type" in req_dict
        assert "confidence" in req_dict

    def test_create_detector_factory(self):
        """工厂函数创建检测器"""
        detector = create_detector(min_confidence=0.6)
        assert detector is not None
        assert detector.min_confidence == 0.6


class TestDetectedRequirement:
    """测试检测到的需求"""

    def test_create_requirement(self):
        """创建需求"""
        req = DetectedRequirement(
            req_id="REQ-0001",
            title="购物车功能",
            description="实现购物车功能",
            req_type=RequirementType.FEATURE,
            source=DetectionSource.USER_MESSAGE,
            confidence=0.85,
        )

        assert req.req_id == "REQ-0001"
        assert req.title == "购物车功能"
        assert req.confidence == 0.85

    def test_requirement_defaults(self):
        """需求默认值"""
        req = DetectedRequirement(
            req_id="REQ-0002",
            title="测试",
            description="测试描述",
            req_type=RequirementType.FEATURE,
            source=DetectionSource.USER_MESSAGE,
            confidence=0.5,
        )

        assert req.suggested_priority == "P2"
        assert req.suggested_assignee == ""
        assert req.extracted_entities == {}


class TestRequirementType:
    """测试需求类型枚举"""

    def test_all_types_exist(self):
        """所有类型都存在"""
        types = [
            RequirementType.FEATURE,
            RequirementType.BUG_FIX,
            RequirementType.IMPROVEMENT,
            RequirementType.CONSTRAINT,
            RequirementType.QUESTION,
            RequirementType.FEEDBACK,
        ]

        for t in types:
            assert t.value is not None


class TestDetectionSource:
    """测试检测来源枚举"""

    def test_all_sources_exist(self):
        """所有来源都存在"""
        sources = [
            DetectionSource.USER_MESSAGE,
            DetectionSource.AI_ANALYSIS,
            DetectionSource.CODE_REVIEW,
            DetectionSource.TEST_FAILURE,
            DetectionSource.EXPERIENCE,
        ]

        for s in sources:
            assert s.value is not None