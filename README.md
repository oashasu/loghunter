# LogHunter - 日志智能检索Agent

> 智能运维平台：ELK日志智能检索、业务链路重建、异常诊断

## 项目状态

**版本**: v1.0.0
**阶段**: Phase 1 - 核心Agent实现完成
**测试**: 38个测试全部通过

## 核心能力

| 能力 | 说明 | Phase |
|------|------|-------|
| 智能识别 | 从不确定输入推断业务类型 | 1 |
| SQL生成 | 输出SQL脚本供运维执行 | 1 |
| 业务定位 | 建立业务链路关联 | 1 |
| ELK查询 | HTTP API自动化查询 | 1 |
| 诊断输出 | 根因分析+处理建议 | 1 |
| SQL安全网关 | 自动化安全查询 | 2 |

## 项目结构

```
loghunter/
├── src/
│   ├── agents/          # Agent实现
│   ├── core/            # 核心模块（SQL生成/配置/ELK）
│   ├── cli/             # CLI交互界面
│   └── utils/           # 工具函数
├── config/              # YAML配置文件
├── tests/               # 测试文件
└── requirements.txt
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 分析订单号
loghunter analyze O20261225000001

# 反馈SQL执行结果
loghunter feedback --sql1 '{"order_no":"O20261225000001","member_id":"M001"}'

# 继续分析
loghunter continue

# 生成诊断报告
loghunter report
```

## 配置

编辑 `config/` 目录下的 YAML 文件：
- `probe_rules.yaml` - 参数探测规则
- `chain_templates.yaml` - 链路模板
- `exception_patterns.yaml` - 异常类型定义
- `root_cause_rules.yaml` - 根因推测规则
- `elk_config.yaml` - ES连接配置

## 相关文档

- [需求全景](../tasks/2026-04-25_日志智能检索Agent/01_需求收集/需求全景.md)
- [第一阶段实施计划](../tasks/2026-04-25_日志智能检索Agent/05_实施路线/第一阶段实施计划.md)
- [API文档](../tasks/2026-04-25_日志智能检索Agent/06_文档/API文档.md)