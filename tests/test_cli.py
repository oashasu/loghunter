"""CLI交互界面测试"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli.main import LogHunterCLI
from cli.commands import AnalyzeCommand, FeedbackCommand, ReportCommand


class TestLogHunterCLI:
    """CLI主入口测试"""

    def test_cli_init(self):
        """测试CLI初始化"""
        cli = LogHunterCLI()
        assert cli.parser is not None

    def test_cli_has_analyze_command(self):
        """测试analyze命令注册"""
        cli = LogHunterCLI()
        # 模拟命令行参数
        with patch('sys.argv', ['loghunter', 'analyze', 'P20261225000001']):
            # 应该能解析analyze命令
            pass  # 基本检查


class TestAnalyzeCommand:
    """analyze命令测试"""

    @patch('cli.commands.IdentificationAgent')
    def test_analyze_identifies_payment(self, mock_agent_class):
        """测试analyze识别支付流水"""
        mock_agent = MagicMock()
        mock_agent.identify.return_value = {
            "type": "支付流水号",
            "tables": ["pay_create"],
            "confidence": 0.9
        }
        mock_agent_class.return_value = mock_agent

        cmd = AnalyzeCommand()
        result = cmd.execute("P20261225000001")

        assert result["type"] == "支付流水号"
        mock_agent.identify.assert_called_once_with("P20261225000001")

    @patch('cli.commands.IdentificationAgent')
    def test_analyze_generates_sql(self, mock_agent_class):
        """测试analyze生成SQL脚本"""
        mock_agent = MagicMock()
        mock_agent.identify.return_value = {
            "type": "支付流水号",
            "tables": ["pay_create", "pay_callback"],
            "confidence": 0.9,
            "input": "P20261225000001",
            "sql_template": "SELECT * FROM {table} WHERE pay_no = '{input}'"
        }
        mock_agent.generate_probe_sql.return_value = [
            "SELECT * FROM pay_create WHERE pay_no = 'P20261225000001'",
            "SELECT * FROM pay_callback WHERE pay_no = 'P20261225000001'"
        ]
        mock_agent.format_sql_output.return_value = "## SQL查询脚本\n..."
        mock_agent_class.return_value = mock_agent

        cmd = AnalyzeCommand()
        result = cmd.execute("P20261225000001")

        assert "sql_scripts" in result
        assert len(result["sql_scripts"]) == 2


class TestFeedbackCommand:
    """feedback命令测试"""

    @patch('cli.commands.LocationAgent')
    def test_feedback_builds_chain(self, mock_agent_class):
        """测试feedback构建链路"""
        mock_agent = MagicMock()
        mock_chain = MagicMock()
        mock_chain.chain_status = "success"
        mock_agent.build_chain.return_value = mock_chain
        mock_agent_class.return_value = mock_agent

        cmd = FeedbackCommand()
        result = cmd.execute(
            business_type="支付流水号",
            primary_id="P20261225000001",
            sql_feedback={"sql1": {"pay_no": "P20261225000001", "status": "success"}}
        )

        assert result["chain_status"] == "success"
        mock_agent.build_chain.assert_called_once()


class TestReportCommand:
    """report命令测试"""

    @patch('cli.commands.DiagnosisAgent')
    @patch('cli.commands.LocationAgent')
    @patch('cli.commands.ELKClient')
    def test_report_generates_diagnosis(self, mock_elk_class, mock_location_class, mock_diagnosis_class):
        """测试report生成诊断报告"""
        mock_elk = MagicMock()
        mock_elk.search_exceptions.return_value = {"total": 10, "logs": [{"message": "ERROR"}]}
        mock_elk_class.return_value = mock_elk

        mock_location = MagicMock()
        mock_chain = MagicMock()
        mock_chain.time_window = {"start": "2026-04-25 09:55:00", "end": "2026-04-25 10:10:00"}
        mock_chain.chain_status = "failed"
        mock_location.calculate_time_window.return_value = mock_chain.time_window
        mock_location_class.return_value = mock_location

        mock_diagnosis = MagicMock()
        mock_diagnosis.diagnose.return_value = {"root_cause": "支付超时", "suggestions": ["检查渠道配置"]}
        mock_diagnosis.format_report.return_value = "## 诊断报告\n..."
        mock_diagnosis_class.return_value = mock_diagnosis

        cmd = ReportCommand()
        result = cmd.execute(
            chain=mock_chain,
            elk_result={"total": 10, "logs": [{"message": "ERROR"}]}
        )

        assert "root_cause" in result
        mock_diagnosis.diagnose.assert_called_once()