"""LogHunter CLI主入口"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.commands import AnalyzeCommand, FeedbackCommand, ReportCommand, ContinueCommand


class LogHunterCLI:
    """LogHunter命令行界面"""

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog='loghunter',
            description='日志智能检索与诊断Agent'
        )
        self._setup_subcommands()

    def _setup_subcommands(self):
        """设置子命令"""
        subparsers = self.parser.add_subparsers(dest='command', help='可用命令')

        # analyze命令
        analyze_parser = subparsers.add_parser('analyze', help='分析输入参数')
        analyze_parser.add_argument('input', help='输入参数（订单号/支付流水等）')

        # feedback命令
        feedback_parser = subparsers.add_parser('feedback', help='反馈SQL执行结果')
        feedback_parser.add_argument('--sql1', help='SQL1执行结果JSON')
        feedback_parser.add_argument('--sql2', help='SQL2执行结果JSON')
        feedback_parser.add_argument('--sql3', help='SQL3执行结果JSON')
        feedback_parser.add_argument('--business-type', help='业务类型')
        feedback_parser.add_argument('--primary-id', help='主标识ID')

        # continue命令
        continue_parser = subparsers.add_parser('continue', help='继续分析流程')
        continue_parser.add_argument('--business-type', help='业务类型')
        continue_parser.add_argument('--primary-id', help='主标识ID')

        # report命令
        report_parser = subparsers.add_parser('report', help='生成诊断报告')
        report_parser.add_argument('--business-type', help='业务类型')
        report_parser.add_argument('--primary-id', help='主标识ID')

    def run(self, args=None):
        """运行CLI"""
        if args is None:
            args = sys.argv[1:]

        parsed = self.parser.parse_args(args)

        if parsed.command == 'analyze':
            return self._handle_analyze(parsed.input)
        elif parsed.command == 'feedback':
            return self._handle_feedback(parsed)
        elif parsed.command == 'continue':
            return self._handle_continue(parsed)
        elif parsed.command == 'report':
            return self._handle_report(parsed)
        else:
            self.parser.print_help()
            return None

    def _handle_analyze(self, input_str: str):
        """处理analyze命令"""
        cmd = AnalyzeCommand()
        result = cmd.execute(input_str)

        # 输出SQL脚本
        print(result["sql_output"])
        print("\n--- 下一步 ---")
        print("请将上述SQL脚本发送给运维执行，执行后将结果通过 feedback 命令反馈:")
        print(f"  loghunter feedback --sql1 '<json结果>' --business-type '{result['type']}' --primary-id '{input_str}'")

        return result

    def _handle_feedback(self, parsed):
        """处理feedback命令"""
        import json

        sql_feedback = {}
        if parsed.sql1:
            sql_feedback["sql1"] = json.loads(parsed.sql1)
        if parsed.sql2:
            sql_feedback["sql2"] = json.loads(parsed.sql2)
        if parsed.sql3:
            sql_feedback["sql3"] = json.loads(parsed.sql3)

        cmd = FeedbackCommand()
        result = cmd.execute(
            business_type=parsed.business_type,
            primary_id=parsed.primary_id,
            sql_feedback=sql_feedback
        )

        # 输出链路图谱
        print(result["chain_output"])
        print("\n--- 下一步 ---")
        print("链路已构建完成，可以使用以下命令继续:")
        print(f"  loghunter continue --business-type '{parsed.business_type}' --primary-id '{parsed.primary_id}'")
        print("或直接生成报告:")
        print(f"  loghunter report --business-type '{parsed.business_type}' --primary-id '{parsed.primary_id}'")

        return result

    def _handle_continue(self, parsed):
        """处理continue命令"""
        # 要从之前的会话状态获取chain
        print("continue命令需要保存链路状态，当前版本请直接使用report命令")
        return None

    def _handle_report(self, parsed):
        """处理report命令"""
        print("report命令需要完整的链路和ELK结果，请先完成analyze和feedback流程")
        return None


def main():
    """CLI入口函数"""
    cli = LogHunterCLI()
    cli.run()


if __name__ == '__main__':
    main()