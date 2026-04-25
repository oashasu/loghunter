"""诊断Agent - 根因分析与报告生成"""
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


class DiagnosisAgent:
    """诊断Agent"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化Agent

        Args:
            config_path: root_cause_rules.yaml配置文件路径
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "root_cause_rules.yaml"

        self._load_root_cause_rules(config_path)

    def _load_root_cause_rules(self, config_path: Path):
        """加载根因规则配置"""
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                self.root_cause_rules = config.get("root_cause_rules", {}).get("rules", [])
        else:
            self.root_cause_rules = self._default_rules()

    def _default_rules(self) -> List[Dict]:
        """默认根因规则"""
        return [
            {
                "name": "支付超时",
                "conditions": [
                    {"chain_status": "failed"},
                    {"log_keyword": "ChannelTimeoutException"},
                    {"log_keyword": "超时"}
                ],
                "suggestions": [
                    "检查渠道配置超时时间",
                    "确认渠道服务是否正常",
                    "查看渠道方是否有响应"
                ]
            },
            {
                "name": "支付渠道异常",
                "conditions": [
                    {"chain_status": "failed"},
                    {"log_keyword": "PaymentFailedException"},
                    {"log_keyword": "渠道"}
                ],
                "suggestions": [
                    "检查渠道接口返回码",
                    "确认渠道账户状态",
                    "验证渠道签名配置"
                ]
            },
            {
                "name": "支付金额异常",
                "conditions": [
                    {"chain_status": "failed"},
                    {"log_keyword": "金额"},
                    {"log_keyword": "AmountMismatchException"}
                ],
                "suggestions": [
                    "检查订单金额与支付金额是否一致",
                    "验证金额计算逻辑",
                    "确认是否有优惠活动影响"
                ]
            },
            {
                "name": "网络订单异常",
                "conditions": [
                    {"chain_status": "failed"},
                    {"business_type": "订单号"},
                    {"log_keyword": "ERROR"}
                ],
                "suggestions": [
                    "检查订单创建流程",
                    "确认库存状态",
                    "验证会员信息"
                ]
            },
            {
                "name": "未知异常",
                "conditions": [
                    {"chain_status": "failed"}
                ],
                "suggestions": [
                    "收集完整日志进行分析",
                    "检查相关系统状态",
                    "联系技术支持"
                ]
            }
        ]

    def diagnose(self, chain: Any, elk_result: Dict[str, Any]) -> Dict[str, Any]:
        """诊断分析

        Args:
            chain: 业务链路
            elk_result: ELK查询结果

        Returns:
            诊断结果
        """
        matches = []

        # 从ELK结果提取日志关键字
        log_keywords = []
        if elk_result and "logs" in elk_result:
            for log in elk_result["logs"]:
                message = log.get("message", "")
                # 提取关键字
                for keyword in ["ChannelTimeoutException", "PaymentFailedException", "超时", "失败", "ERROR", "Exception", "金额"]:
                    if keyword in message:
                        log_keywords.append(keyword)

        # 获取链路状态
        chain_status = chain.chain_status if hasattr(chain, 'chain_status') else "unknown"
        business_type = chain.business_type if hasattr(chain, 'business_type') else "unknown"

        # 匹配根因规则
        for rule in self.root_cause_rules:
            rule_name = rule.get("name")
            conditions = rule.get("conditions", [])
            suggestions = rule.get("suggestions", [])

            matched_conditions = 0
            for condition in conditions:
                if "chain_status" in condition and condition["chain_status"] == chain_status:
                    matched_conditions += 1
                if "log_keyword" in condition and condition["log_keyword"] in log_keywords:
                    matched_conditions += 1
                if "business_type" in condition and condition["business_type"] == business_type:
                    matched_conditions += 1

            # 至少匹配一个条件才考虑
            if matched_conditions > 0:
                confidence = matched_conditions / len(conditions)
                matches.append({
                    "name": rule_name,
                    "confidence": confidence,
                    "suggestions": suggestions,
                    "matched_conditions": matched_conditions
                })

        # 按置信度排序
        matches.sort(key=lambda x: x["confidence"], reverse=True)

        if matches:
            best_match = matches[0]
            return {
                "root_cause": best_match["name"],
                "confidence": best_match["confidence"],
                "suggestions": best_match["suggestions"],
                "all_matches": matches,
                "log_keywords": log_keywords,
                "chain_status": chain_status
            }

        # 未匹配
        return {
            "root_cause": "未知",
            "confidence": 0.3,
            "suggestions": ["收集更多日志信息", "检查系统状态"],
            "all_matches": [],
            "log_keywords": log_keywords,
            "chain_status": chain_status
        }

    def format_report(self, diagnosis_result: Dict[str, Any]) -> str:
        """格式化诊断报告

        Args:
            diagnosis_result: 诊断结果

        Returns:
            Markdown格式报告
        """
        output = "## 诊断报告\n\n"

        output += "### 根因分析\n\n"
        output += f"**推测根因**: {diagnosis_result['root_cause']}\n"
        output += f"**置信度**: {diagnosis_result['confidence']:.2f}\n\n"

        output += "### 相关日志关键字\n\n"
        for kw in diagnosis_result.get("log_keywords", []):
            output += f"- {kw}\n"

        output += "\n### 处理建议\n\n"
        for i, suggestion in enumerate(diagnosis_result.get("suggestions", []), 1):
            output += f"{i}. {suggestion}\n"

        output += "\n### 其他可能性\n\n"
        for match in diagnosis_result.get("all_matches", [])[:3]:
            if match["name"] != diagnosis_result["root_cause"]:
                output += f"- {match['name']} (置信度: {match['confidence']:.2f})\n"

        output += "\n---\n"
        output += "**说明**: 以上诊断基于链路状态和日志关键字推测，建议结合实际情况验证。\n"

        return output