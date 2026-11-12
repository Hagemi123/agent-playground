# Agent Playground: Autonomous Web & Social Media Interaction Lab

这是一个为 AI Agent 打造的自主网络浏览与多平台交互实验场。目标是赋予 Agent 像人类一样感知、探索和操作现代网页与社交媒体的能力。

---

## 核心架构规划

```
d:/hagemiplayground/
├── README.md                 # 项目定位与架构说明
├── PERSONALITY.md            # Hagemi 人格宣言
├── requirements.txt          # Python 依赖清单
├── mcp_server.py             # Model Context Protocol (MCP) stdio 服务端
├── package_skill.py          # 生成去敏后的标准 SKILL.md 分发包 (dist/agent-playground-skill.zip)
├── core/                     # 核心浏览与交互引擎
│   ├── __init__.py
│   ├── browser.py            # Playwright/Chrome 引擎封装（支持无头/可视模式及通道回退）
│   ├── extractor.py          # 网页智能内容/链接提取器
│   └── navigator.py          # 动态滚动、截图与结构化解析编排器
├── adapters/                 # 各社交媒体与特定网站交互适配器
│   ├── __init__.py
│   ├── base.py               # 基础适配器抽象类
│   ├── bilibili.py           # B站视频、空间与会话模块
│   ├── github.py             # GitHub 仓库搜索、Star 与创建模块
│   ├── zhihu.py              # 知乎问答与热榜探索模块
│   └── wechat.py             # Windows PC 微信 4.x 纯 Ctypes 跨桌面桥接模块
├── .agents/skills/agent-playground/
│   ├── SKILL.md              # Antigravity / Agensi 兼容标准技能描述
│   ├── scripts/run.py        # 统一命令行入口
│   └── reference/notes.md    # 反检测、扫码认证与 Win32 桌面隔离技术笔记
└── storage/                  # 运行时截图、会话缓存（已通过 .gitignore 严格隔离）
    ├── cookies/              # 用户/会话状态保存（支持持久登录）
    └── captures/             # 页面快照与截图
```

## 里程碑阶段 (Milestones)

- [x] **Milestone 1**: 建立基础自动化环境与 Chrome 驱动测试，实现网页无头/可视加载与快照。
- [x] **Milestone 2**: 实现通用页面解析与交互组件（智能提取正文、视频元数据、评论区结构）。
- [x] **Milestone 3**: 构建多平台适配器（GitHub、Bilibili、Zhihu、PC 微信 4.x），完成信息获取与交互闭环。
- [x] **Milestone 4**: 封装为 MCP Server (`mcp_server.py`) 与标准 Skill (`.agents/skills/agent-playground/`)，支持随时调度与打包分发。
