"""CLI命令处理"""
import argparse
from typing import Dict, Any, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.identification_agent import IdentificationAgent
from agents.location_agent import LocationAgent
from agents.diagnosis_agent import DiagnosisAgent
from core.elk_client import ELKClient


class AnalyzeCommand:
    """analyze命令处理"""

    def __init__(self):
        self.identification_agent = IdentificationAgent()

    def execute(self, input_str: str) -> Dict[str, Any]:
        """执行analyze命令

        Args:
            input_str: 用户输入的参数

        Returns:
            识别结果和SQL脚本
        """
        # 1. 智能识别
        identification_result = self.identification_agent.identify(input_str)

        # 2. 生成探测SQL
        sql_scripts = self.identification_agent.generate_probe_sql(identification_result)

        # 3. 格式化输出
        sql_output = self.identification_agent.format_sql_output(identification_result, sql_scripts)

        return {
            "type": identification_result["type"],
            "tables": identification_result["tables"],
            "confidence": identification_result["confidence"],
            "sql_scripts": sql_scripts,
            "sql_output": sql_output,
            "identification_result": identification_result
        }


class FeedbackCommand:
    """feedback命令处理"""

    def __init__(self):
        self.location_agent = LocationAgent()

    def execute(
        self,
        business_type: str,
        primary_id: str,
        sql_feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行feedback命令

        Args:
            business_type: 业务类型
            primary_id: 主标识
            sql_feedback: SQL执行结果反馈

        Returns:
            业务链路图谱
        """
        # 1. 构建业务链路
        chain = self.location_agent.build_chain(
            business_type=business_type,
            primary_id=primary_id,
            sql_feedback=sql_feedback
        )

        # 2. 计算时间窗口
        self.location_agent.calculate_time_window(chain)

        # 3. 格式化输出
        chain_output = self.location_agent.format_chain_output(chain)

        return {
            "chain": chain,
            "chain_status": chain.chain_status,
            "time_window": chain.time_window,
            "chain_output": chain_output
        }


class ReportCommand:
    """report命令处理"""

    def __init__(self):
        self.diagnosis_agent = DiagnosisAgent()
        self.elk_client = ELKClient()

    def execute(
        self,
        chain: Any,
        elk_result: Optional[Dict[str, Any]] = None,
        keywords: Optional[list] = None
    ) -> Dict[str, Any]:
        """执行report命令

        Args:
            chain: 业务链路
            elk_result: ELK查询结果（可选，会自动查询）
            keywords: 异常关键字（可选）

        Returns:
            诊断报告
        """
        # 如果没有ELK结果，自动查询
        if elk_result is None and chain.time_window:
            # 使用默认关键字搜索异常
            default_keywords = keywords or ["ERROR", "Exception", "失败", "超时"]
            elk_result = self.elk_client.search_exceptions(
                keywords=default_keywords,
                time_range_hours=1  # 从时间窗口推导
            )

        # 诊断分析
        diagnosis_result = self.diagnosis_agent.diagnose(chain, elk_result)

        # 格式化报告
        report_output = self.diagnosis_agent.format_report(diagnosis_result)

        return {
            "root_cause": diagnosis_result.get("root_cause"),
            "suggestions": diagnosis_result.get("suggestions"),
            "report_output": report_output
        }


class ContinueCommand:
    """continue命令处理"""

    def __init__(self):
        self.elk_client = ELKClient()
        self.diagnosis_agent = DiagnosisAgent()

    def execute(self, chain: Any, time_window: Dict[str, str]) -> Dict[str, Any]:
        """执行continue命令 - 查询ELK日志

        Args:
            chain: 业务链路
            time_window: 时间窗口

        Returns:
            ELK查询结果
        """
        # 根据链路状态选择关键字
        keywords = []
        if chain.chain_status == "failed":
            keywords = ["ERROR", "Exception", "失败", "超时", "ChannelTimeout"]
        else:
            keywords = ["WARN", "INFO", chain.primary_id]

        # 查询ELK
        elk_result = self.elk_client.search_exceptions(
            keywords=keywords,
            time_range_hours=1
        )

        return {
            "elk_result": elk_result,
            "keywords": keywords
        }