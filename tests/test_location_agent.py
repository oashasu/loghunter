"""业务定位Agent测试"""
import pytest
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.location_agent import LocationAgent, BusinessChain, BusinessNode, BusinessLink


class TestLocationAgent:
    """业务定位Agent测试类"""

    def test_init(self):
        """测试初始化"""
        agent = LocationAgent()
        assert agent.chain_templates is not None

    def test_get_template_for_payment(self):
        """测试获取支付流水链路模板"""
        agent = LocationAgent()

        template = agent.get_template("支付流水号")
        assert template is not None
        assert template["start_type"] == "payment"

    def test_get_template_for_order(self):
        """测试获取订单链路模板"""
        agent = LocationAgent()

        template = agent.get_template("订单号")
        assert template is not None
        assert template["start_type"] == "order"

    def test_get_template_for_refund(self):
        """测试获取退款链路模板"""
        agent = LocationAgent()

        template = agent.get_template("退款单号")
        assert template is not None
        assert template["start_type"] == "refund"

    def test_get_template_unknown(self):
        """测试未知类型返回None"""
        agent = LocationAgent()

        template = agent.get_template("未知类型")
        assert template is None

    def test_build_chain_from_payment_feedback(self):
        """测试从支付流水反馈构建链路"""
        agent = LocationAgent()

        # 模拟用户反馈的SQL执行结果
        sql_feedback = {
            "sql1": {"pay_no": "P20261225000001", "order_no": "OA123456789012", "channel_id": "alipay", "status": "success", "create_time": "2026-04-25 10:00:00"},
            "sql2": {"order_no": "OA123456789012", "member_id": "M00000001", "status": "success"},
            "sql3": {"channel_id": "alipay", "channel_name": "支付宝", "channel_type": "online"}
        }

        chain = agent.build_chain(
            business_type="支付流水号",
            primary_id="P20261225000001",
            sql_feedback=sql_feedback
        )

        assert chain is not None
        assert chain.primary_id == "P20261225000001"
        assert chain.business_type == "支付流水号"
        assert len(chain.nodes) >= 2  # 至少有payment和order节点

    def test_build_chain_payment_node(self):
        """测试支付节点构建"""
        agent = LocationAgent()

        sql_feedback = {
            "sql1": {"pay_no": "P20261225000001", "order_no": "OA123456789012", "status": "success", "create_time": "2026-04-25 10:00:00"}
        }

        chain = agent.build_chain(
            business_type="支付流水号",
            primary_id="P20261225000001",
            sql_feedback=sql_feedback
        )

        # 检查支付节点
        payment_node = chain.get_node_by_type("payment")
        assert payment_node is not None
        assert payment_node.id == "P20261225000001"
        assert payment_node.status == "success"

    def test_calculate_time_window(self):
        """测试时间窗口计算"""
        agent = LocationAgent()

        # 交易时间: 2026-04-25 10:00:00
        sql_feedback = {
            "sql1": {"pay_no": "P20261225000001", "create_time": "2026-04-25 10:00:00", "status": "success"}
        }

        chain = agent.build_chain(
            business_type="支付流水号",
            primary_id="P20261225000001",
            sql_feedback=sql_feedback
        )

        agent.calculate_time_window(chain)

        # 前5分钟，后10分钟
        # 开始: 2026-04-25 09:55:00
        # 结束: 2026-04-25 10:10:00
        assert chain.time_window is not None
        assert chain.time_window["start"].startswith("2026-04-25 09:55")
        assert chain.time_window["end"].startswith("2026-04-25 10:10")

    def test_chain_status_success(self):
        """测试链路状态判断 - 成功"""
        agent = LocationAgent()

        sql_feedback = {
            "sql1": {"pay_no": "P001", "status": "success"},
            "sql2": {"order_no": "OA001", "status": "success"}
        }

        chain = agent.build_chain(
            business_type="支付流水号",
            primary_id="P001",
            sql_feedback=sql_feedback
        )

        assert chain.chain_status == "success"

    def test_chain_status_failed(self):
        """测试链路状态判断 - 失败"""
        agent = LocationAgent()

        sql_feedback = {
            "sql1": {"pay_no": "P001", "status": "failed"}
        }

        chain = agent.build_chain(
            business_type="支付流水号",
            primary_id="P001",
            sql_feedback=sql_feedback
        )

        assert chain.chain_status == "failed"

    def test_format_chain_output(self):
        """测试链路图谱格式化输出"""
        agent = LocationAgent()

        sql_feedback = {
            "sql1": {"pay_no": "P20261225000001", "order_no": "OA123456789012", "status": "success", "create_time": "2026-04-25 10:00:00"}
        }

        chain = agent.build_chain(
            business_type="支付流水号",
            primary_id="P20261225000001",
            sql_feedback=sql_feedback
        )
        agent.calculate_time_window(chain)

        output = agent.format_chain_output(chain)

        assert "## 业务链路图谱" in output
        assert "支付流水号" in output
        assert "时间窗口" in output
        assert "链路状态" in output


class TestBusinessChain:
    """业务链路数据结构测试"""

    def test_node_creation(self):
        """测试节点创建"""
        node = BusinessNode(
            id="P001",
            type="payment",
            table="pay_create",
            data={"pay_no": "P001", "status": "success"},
            timestamp=1713523200000,
            status="success"
        )
        assert node.id == "P001"
        assert node.type == "payment"

    def test_link_creation(self):
        """测试链路关系创建"""
        link = BusinessLink(
            source="OA001",
            target="P001",
            relation="payment_for"
        )
        assert link.source == "OA001"
        assert link.relation == "payment_for"

    def test_chain_get_node(self):
        """测试链路获取节点"""
        chain = BusinessChain(
            business_type="支付流水号",
            primary_id="P001"
        )
        chain.add_node(BusinessNode(id="P001", type="payment", table="pay_create", data={}, timestamp=0, status="success"))
        chain.add_node(BusinessNode(id="OA001", type="order", table="orders", data={}, timestamp=0, status="success"))

        node = chain.get_node_by_type("payment")
        assert node.id == "P001"

    def test_chain_add_link(self):
        """测试链路添加关系"""
        chain = BusinessChain(
            business_type="支付流水号",
            primary_id="P001"
        )
        chain.add_link(BusinessLink(source="OA001", target="P001", relation="payment_for"))

        assert len(chain.links) == 1
        assert chain.links[0].relation == "payment_for"