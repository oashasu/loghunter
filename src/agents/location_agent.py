"""业务定位Agent - 建立业务链路图谱"""
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta


class BusinessNode:
    """业务链路节点"""

    def __init__(
        self,
        id: str,
        type: str,
        table: str,
        data: Dict[str, Any],
        timestamp: int,
        status: str
    ):
        self.id = id
        self.type = type
        self.table = table
        self.data = data
        self.timestamp = timestamp
        self.status = status


class BusinessLink:
    """业务链路关系"""

    def __init__(self, source: str, target: str, relation: str):
        self.source = source
        self.target = target
        self.relation = relation


class BusinessChain:
    """业务链路图谱"""

    def __init__(self, business_type: str, primary_id: str):
        self.business_type = business_type
        self.primary_id = primary_id
        self.nodes: List[BusinessNode] = []
        self.links: List[BusinessLink] = []
        self.time_window: Optional[Dict[str, str]] = None
        self.chain_status: str = "pending"

    def add_node(self, node: BusinessNode):
        """添加节点"""
        self.nodes.append(node)

    def add_link(self, link: BusinessLink):
        """添加链路关系"""
        self.links.append(link)

    def get_node_by_type(self, type: str) -> Optional[BusinessNode]:
        """按类型获取节点"""
        for node in self.nodes:
            if node.type == type:
                return node
        return None

    def get_node_by_id(self, id: str) -> Optional[BusinessNode]:
        """按ID获取节点"""
        for node in self.nodes:
            if node.id == id:
                return node
        return None

    def calculate_status(self) -> str:
        """计算链路状态"""
        statuses = [node.status for node in self.nodes]

        if "failed" in statuses:
            return "failed"
        if "pending" in statuses:
            return "pending"
        if any(s not in ["success", "pending"] for s in statuses):
            return "partial"
        if all(s == "success" for s in statuses):
            return "success"
        return "partial"


class LocationAgent:
    """业务定位Agent"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化Agent

        Args:
            config_path: chain_templates.yaml配置文件路径
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "chain_templates.yaml"

        self._load_chain_templates(config_path)

    def _load_chain_templates(self, config_path: Path):
        """加载链路模板配置"""
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                self.chain_templates = config.get("chain_templates", {}).get("templates", [])
        else:
            self.chain_templates = self._default_templates()

    def _default_templates(self) -> List[Dict]:
        """默认链路模板"""
        return [
            {
                "name": "支付流水链路",
                "trigger_type": "支付流水号",
                "start_type": "payment",
                "nodes": [
                    {"id": "payment", "table": "pay_create", "query_field": "pay_no"},
                    {"id": "order", "table": "orders", "query_field": "order_no"},
                    {"id": "channel", "table": "channel_config", "query_field": "channel_id"}
                ],
                "time_window": {"before_minutes": 5, "after_minutes": 10}
            },
            {
                "name": "订单号链路",
                "trigger_type": "订单号",
                "start_type": "order",
                "nodes": [
                    {"id": "order", "table": "orders", "query_field": "order_no"},
                    {"id": "payment", "table": "pay_create", "query_field": "order_no"}
                ],
                "time_window": {"before_minutes": 10, "after_minutes": 15}
            },
            {
                "name": "退款链路",
                "trigger_type": "退款单号",
                "start_type": "refund",
                "nodes": [
                    {"id": "refund", "table": "refund_create", "query_field": "refund_no"},
                    {"id": "payment", "table": "pay_create", "query_field": "pay_no"},
                    {"id": "order", "table": "orders", "query_field": "order_no"}
                ],
                "time_window": {"before_minutes": 5, "after_minutes": 60}
            }
        ]

    def get_template(self, business_type: str) -> Optional[Dict]:
        """获取匹配的链路模板

        Args:
            business_type: 业务类型

        Returns:
            匹配的模板或None
        """
        for template in self.chain_templates:
            if template.get("trigger_type") == business_type:
                return template
        return None

    def build_chain(
        self,
        business_type: str,
        primary_id: str,
        sql_feedback: Dict[str, Any]
    ) -> BusinessChain:
        """从SQL反馈构建业务链路

        Args:
            business_type: 业务类型
            primary_id: 主标识ID
            sql_feedback: SQL执行结果反馈

        Returns:
            业务链路图谱
        """
        chain = BusinessChain(business_type, primary_id)
        template = self.get_template(business_type)

        if not template:
            chain.chain_status = "partial"
            return chain

        # 根据SQL反馈构建节点
        template_nodes = template.get("nodes", [])

        # SQL反馈按顺序编号(sql1, sql2, sql3...)
        for i, node_def in enumerate(template_nodes):
            sql_key = f"sql{i + 1}"
            if sql_key in sql_feedback:
                node_data = sql_feedback[sql_key]

                # 提取时间戳
                timestamp = 0
                if "create_time" in node_data:
                    try:
                        dt = datetime.strptime(node_data["create_time"], "%Y-%m-%d %H:%M:%S")
                        timestamp = int(dt.timestamp() * 1000)
                    except ValueError:
                        timestamp = 0

                node = BusinessNode(
                    id=node_data.get(node_def["query_field"], f"{node_def['id']}_{i}"),
                    type=node_def["id"],
                    table=node_def["table"],
                    data=node_data,
                    timestamp=timestamp,
                    status=node_data.get("status", "unknown")
                )
                chain.add_node(node)

        # 建立节点间链接关系
        for i in range(len(chain.nodes) - 1):
            source_node = chain.nodes[i]
            target_node = chain.nodes[i + 1]
            link = BusinessLink(
                source=source_node.id,
                target=target_node.id,
                relation=f"{target_node.type}_for"
            )
            chain.add_link(link)

        # 计算链路状态
        chain.chain_status = chain.calculate_status()

        return chain

    def calculate_time_window(self, chain: BusinessChain) -> Dict[str, str]:
        """计算日志查询时间窗口

        Args:
            chain: 业务链路

        Returns:
            时间窗口 {start, end}
        """
        template = self.get_template(chain.business_type)

        if not template or not chain.nodes:
            chain.time_window = {"start": "", "end": ""}
            return chain.time_window

        # 获取时间窗口配置
        tw_config = template.get("time_window", {"before_minutes": 5, "after_minutes": 10})
        before_minutes = tw_config.get("before_minutes", 5)
        after_minutes = tw_config.get("after_minutes", 10)

        # 找到主节点的时间戳
        primary_node = chain.get_node_by_id(chain.primary_id)
        if not primary_node or primary_node.timestamp == 0:
            # 使用第一个有时间戳的节点
            for node in chain.nodes:
                if node.timestamp > 0:
                    primary_node = node
                    break

        if primary_node and primary_node.timestamp > 0:
            dt = datetime.fromtimestamp(primary_node.timestamp / 1000)
            start_dt = dt - timedelta(minutes=before_minutes)
            end_dt = dt + timedelta(minutes=after_minutes)

            chain.time_window = {
                "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end_dt.strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            chain.time_window = {"start": "", "end": ""}

        return chain.time_window

    def format_chain_output(self, chain: BusinessChain) -> str:
        """格式化链路图谱输出

        Args:
            chain: 业务链路

        Returns:
            Markdown格式输出
        """
        output = "## 业务链路图谱\n\n"
        output += f"**业务类型**: {chain.business_type}\n"
        output += f"**主标识**: {chain.primary_id}\n\n"

        output += "**链路节点**:\n"
        for node in chain.nodes:
            output += f"- {node.type}: {node.id} (状态: {node.status})\n"
            for key, value in node.data.items():
                if key not in ["status", "create_time"]:
                    output += f"  - {key}: {value}\n"

        output += "\n**链路关系**:\n"
        for link in chain.links:
            output += f"- {link.source} → {link.target} ({link.relation})\n"

        output += "\n**时间窗口**:\n"
        if chain.time_window:
            output += f"- 开始: {chain.time_window.get('start', '未知')}\n"
            output += f"- 结束: {chain.time_window.get('end', '未知')}\n"

        output += "\n**链路状态**: " + chain.chain_status + "\n"

        return output