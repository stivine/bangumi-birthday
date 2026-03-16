# Bangumi Birthday / 二次元角色生日追踪系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

基于 [Bangumi](https://bgm.tv) 数据库的动漫角色/声优生日查询系统，支持：

- **CLI 工具**：扫描本地 JSONLINES 数据库，列出指定日期生日的角色与人物
- **ETL 流水线**：将 JSONLINES 批量导入 MongoDB，构建可查询的生日索引
- **Web API + 前端**：用户输入 Bangumi ID 后，查看自己收藏作品中今天生日的角色
- **输出生成**：生成论坛帖子格式的生日榜单（动画/Galgame/芳文社分类）
- **Excel 匹配**：将角色名批量匹配为 Bangumi character ID

---

## 快速开始

### 环境准备

```bash
pip install -e ".[dev]"
```

拷贝 `.env.example` 为 `.env`，按需修改：

```bash
cp .env.example .env
```

### CLI 工具

```bash
# 查看指定日期生日的角色（需要本地 JSONLINES 文件）
bgm-birthday search --date 03-17

# 查看今天生日的角色
bgm-birthday search --date today

# 查看声优代表角色
bgm-birthday top-chars --person-id 32253 --top 15
```

### ETL 导入

```bash
# 完整流水线：characters → subject-characters → merge
bgm-etl run

# 单步执行
bgm-etl characters   # 导入角色生日
bgm-etl relations    # 导入作品-角色关系
bgm-etl merge        # 合并两张表
```

### 启动 Web 服务

```bash
# 开发模式
cd web/backend
uvicorn app:app --reload --port 5000

# 前端
cd web/frontend
npm install
npm run dev
```

---

## 项目结构

```
bangumi-dev/
├── bangumi_birthday/          # 核心 Python 包
│   ├── config.py              # 统一配置（Pydantic Settings）
│   ├── utils/
│   │   ├── date_utils.py      # 日期解析工具
│   │   └── jsonlines.py       # JSONLINES 流式读取
│   ├── db/
│   │   ├── mongo.py           # MongoDB 连接与操作
│   │   └── models.py          # Pydantic 数据模型
│   ├── etl/
│   │   ├── pipeline.py        # ETL CLI（Click）
│   │   ├── extract_chars.py   # 角色生日提取
│   │   ├── extract_relations.py # 作品-角色关系导入
│   │   └── merge.py           # 数据合并
│   └── cli/
│       ├── main.py            # 主 CLI 入口
│       ├── birthday_search.py # 生日搜索命令
│       ├── top_chars.py       # 声优代表角色命令
│       └── output_gen.py      # 榜单输出命令
├── web/
│   ├── backend/
│   │   ├── app.py             # Quart Web 应用
│   │   ├── routes/
│   │   │   ├── birthday.py    # 生日查询路由
│   │   │   └── user.py        # 用户收藏路由
│   │   └── services/
│   │       ├── birthday_svc.py
│   │       └── bangumi_api.py # Bangumi API 客户端
│   └── frontend/              # Vue 3 前端
├── scripts/
│   └── id_match.py            # Excel 批量匹配工具
├── tests/
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 数据文件

本项目依赖从 [bangumi-data-archive](https://github.com/bangumi/Archive) 下载的 JSONLINES 格式转储文件：

| 文件 | 用途 |
|------|------|
| `character.jsonlines` | 角色数据（含生日 infobox） |
| `person.jsonlines` | 人物数据（声优等） |
| `subject-characters.jsonlines` | 作品-角色关系 |
| `person-characters.jsonlines` | 声优-角色关系 |

默认路径通过 `.env` 中 `BGM_DATA_DIR` 配置。

---

## 许可证

MIT © Stivine
