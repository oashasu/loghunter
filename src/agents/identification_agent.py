"""智能识别Agent - 从不确定输入推断业务类型"""
import re
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


class IdentificationAgent:
    """智能识别Agent"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化Agent

        Args:
            config_path: probe_rules.yaml配置文件路径
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "probe_rules.yaml"

        self._load_probe_rules(config_path)

    def _load_probe_rules(self, config_path: Path):
        """加载探测规则配置"""
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                self.probe_rules = config.get("probe_rules", {}).get("rules", [])
        else:
            # 默认规则
            self.probe_rules = self._default_rules()

    def _default_rules(self) -> List[Dict]:
        """默认探测规则"""
        return [
            {
                "name": "订单号",
                "patterns": [
                    {"regex": "^[A-Z]{2}[0-9]{12}$", "tables": ["orders"], "priority": 1},
                    {"regex": "^[0-9]{16}$", "tables": ["ticket_orders"], "priority": 2}
                ],
                "probe_sql_template": "SELECT * FROM {table} WHERE order_no = '{input}' LIMIT 1"
            },
            {
                "name": "支付流水号",
                "patterns": [
                    {"regex": "^P[0-9]{14}$", "tables": ["pay_create"], "priority": 1}
                ],
                "probe_sql_template": "SELECT * FROM {table} WHERE pay_no = '{input}' LIMIT 1"
            },
            {
                "name": "退款单号",
                "patterns": [
                    {"regex": "^R[0-9]{14}$", "tables": ["refund_create"], "priority": 1}
                ],
                "probe_sql_template": "SELECT * FROM {table} WHERE refund_no = '{input}' LIMIT 1"
            },
            {
                "name": "会员ID",
                "patterns": [
                    {"regex": "^M[0-9]{8}$", "tables": ["member"], "priority": 1}
                ],
                "probe_sql_template": "SELECT * FROM {table} WHERE member_id = '{input}' LIMIT 1"
            }
        ]

    def identify(self, input_str: str) -> Dict[str, Any]:
        """识别输入参数类型

        Args:
            input_str: 用户输入的不确定参数

        Returns:
            识别结果，包含type, tables, confidence, patterns
        """
        matches = []

        for rule in self.probe_rules:
            rule_name = rule.get("name")
            patterns = rule.get("patterns", [])
            sql_template = rule.get("probe_sql_template", "")

            for pattern in patterns:
                regex = pattern.get("regex")
                tables = pattern.get("tables", [])
                priority = pattern.get("priority", 1)

                try:
                    if re.match(regex, input_str):
                        # 匹配成功，计算置信度
                        confidence = 0.9 - (priority - 1) * 0.1  # priority 1 -> 0.9, priority 2 -> 0.8

                        matches.append({
                            "type": rule_name,
                            "tables": tables,
                            "confidence": confidence,
                            "sql_template": sql_template,
                            "pattern_desc": pattern.get("description", regex)
                        })
                except re.error:
                    # 正则表达式错误，跳过
                    continue

        if matches:
            # 按置信度排序，返回最高置信度的结果
            matches.sort(key=lambda x: x["confidence"], reverse=True)
            best_match = matches[0]
            return {
                "type": best_match["type"],
                "tables": best_match["tables"],
                "confidence": best_match["confidence"],
                "sql_template": best_match["sql_template"],
                "pattern_desc": best_match["pattern_desc"],
                "input": input_str,
                "all_matches": matches  # 保留所有匹配结果供参考
            }

        # 未匹配
        return {
            "type": "未知",
            "tables": [],
            "confidence": 0.3,
            "sql_template": "",
            "pattern_desc": "无法识别格式",
            "input": input_str,
            "all_matches": []
        }

    def generate_probe_sql(self, identification_result: Dict[str, Any]) -> List[str]:
        """生成探测SQL脚本

        Args:
            identification_result: identify()返回的识别结果

        Returns:
            SQL脚本列表
        """
        sql_scripts = []
        input_str = identification_result["input"]
        tables = identification_result["tables"]
        sql_template = identification_result.get("sql_template", "")

        if not tables or not sql_template:
            return sql_scripts

        # 为每个候选表生成SQL
        for table in tables:
            sql = sql_template.replace("{table}", table).replace("{input}", input_str)
            sql_scripts.append(sql)

        return sql_scripts

    def format_sql_output(
        self,
        identification_result: Dict[str, Any],
        sql_scripts: List[str]
    ) -> str:
        """格式化SQL脚本输出

        Args:
            identification_result: 识别结果
            sql_scripts: SQL脚本列表

        Returns:
            格式化的Markdown输出
        """
        output = "## SQL查询脚本\n\n"
        output += f"**业务类型**: {identification_result['type']}\n"
        output += f"**输入参数**: {identification_result['input']}\n\n"
        output += "**探测SQL**（请运维执行并反馈结果）:\n\n"

        for i, sql in enumerate(sql_scripts, 1):
            table = identification_result["tables"][i-1] if i <= len(identification_result["tables"]) else "unknown"
            output += f"### SQL {i}: {table}表探测\n"
            output += "```sql\n"
            output += sql
            output += "\n```\n\n"

        output += "**执行说明**:\n"
        output += "1. 按顺序执行SQL脚本\n"
        output += "2. 将查询结果反馈给Agent继续分析\n"
        output += "3. 使用命令: `loghunter feedback --sql<n> '<json_result>'`\n"

        return output