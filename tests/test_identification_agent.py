"""智能识别Agent测试"""
import pytest
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.identification_agent import IdentificationAgent


class TestIdentificationAgent:
    """智能识别Agent测试类"""

    def test_init(self):
        """测试初始化"""
        agent = IdentificationAgent()
        assert agent.probe_rules is not None

    def test_identify_order_number(self):
        """测试识别订单号 - 网络订单号格式（2字母+12数字）"""
        agent = IdentificationAgent()

        # 网络订单号格式：2字母+12数字=14位
        result = agent.identify("OA123456789012")
        assert result["type"] == "订单号"
        assert result["confidence"] >= 0.8
        assert "orders" in result["tables"]

    def test_identify_order_number_ticket(self):
        """测试识别订单号 - 窗口售票格式（16位纯数字）"""
        agent = IdentificationAgent()

        # 窗口售票订单号：16位纯数字
        result = agent.identify("1234567890123456")
        assert result["type"] == "订单号"
        assert result["confidence"] >= 0.7  # priority=2 => 0.8
        assert "ticket_orders" in result["tables"]

    def test_identify_payment_number(self):
        """测试识别支付流水号"""
        agent = IdentificationAgent()

        # 支付流水号：P + 14位数字 = 15位
        result = agent.identify("P20261225000001")
        assert result["type"] == "支付流水号"
        assert result["confidence"] >= 0.9  # priority=1 => exactly 0.9
        assert "pay_create" in result["tables"]

    def test_identify_refund_number(self):
        """测试识别退款单号"""
        agent = IdentificationAgent()

        # 退款单号：R + 14位数字
        result = agent.identify("R20261225000001")
        assert result["type"] == "退款单号"
        assert result["confidence"] >= 0.9
        assert "refund_create" in result["tables"]

    def test_identify_member_id(self):
        """测试识别会员ID"""
        agent = IdentificationAgent()

        # 会员ID：M + 8位数字 = 9位
        result = agent.identify("M00000001")
        assert result["type"] == "会员ID"
        assert result["confidence"] >= 0.9
        assert "member" in result["tables"]

    def test_identify_unknown_format(self):
        """测试无法识别的格式"""
        agent = IdentificationAgent()

        result = agent.identify("random123abc")
        assert result["type"] == "未知"
        assert result["confidence"] < 0.5
        assert len(result["tables"]) == 0

    def test_generate_probe_sql(self):
        """测试生成探测SQL"""
        agent = IdentificationAgent()

        result = agent.identify("P20261225000001")
        sql_scripts = agent.generate_probe_sql(result)

        assert len(sql_scripts) > 0
        assert "SELECT" in sql_scripts[0]
        assert "P20261225000001" in sql_scripts[0]

    def test_generate_probe_sql_multiple_tables(self):
        """测试多表探测SQL生成"""
        agent = IdentificationAgent()

        # 支付流水号会探测 pay_create 和 pay_callback 两个表
        result = agent.identify("P20261225000001")
        sql_scripts = agent.generate_probe_sql(result)

        # 应该为每个候选表生成SQL
        assert len(sql_scripts) >= len(result["tables"])

    def test_format_sql_output(self):
        """测试SQL脚本格式化输出"""
        agent = IdentificationAgent()

        result = agent.identify("P20261225000001")
        output = agent.format_sql_output(result, sql_scripts=agent.generate_probe_sql(result))

        assert "## SQL查询脚本" in output
        assert "**业务类型**" in output
        assert "```sql" in output