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

### 数据文件

本项目依赖从 [Bangumi Archive](https://github.com/bangumi/Archive) 下载的 JSONLINES 格式转储文件，解压后放到同一目录，在 `.env` 中用 `BGM_DATA_DIR` 指定路径：

| 文件 | 用途 |
|------|------|
| `character.jsonlines` | 角色数据（含生日 infobox） |
| `person.jsonlines` | 人物数据（声优等） |
| `subject-characters.jsonlines` | 作品-角色关系 |
| `person-characters.jsonlines` | 声优-角色关系 |

---

## CLI 工具（`bgm-birthday`）

需要本地 JSONLINES 文件，**不依赖** MongoDB。

### `search` — 搜索生日角色/人物

```bash
# 搜索今天生日的角色和人物
bgm-birthday search

# 搜索指定日期（MM-DD 格式）
bgm-birthday search --date 03-17

# 仅搜索角色，跳过声优等人物
bgm-birthday search --date 12-25 --chars-only

# 仅搜索人物（声优、创作者等）
bgm-birthday search --date 01-01 --persons-only

# 设置评论数门槛（过滤冷门角色）
bgm-birthday search --date 03-17 --min-comments 10

# 限制角色 ID 范围（只看新角色）
bgm-birthday search --date 03-17 --min-char-id 150000

# 在浏览器中打开所有匹配角色的 Bangumi 页面
bgm-birthday search --date 03-17 --open
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--date` | `today` | 目标生日，`MM-DD` 格式或 `today` |
| `--min-comments` | `0` | 角色最低评论数 |
| `--person-comment-threshold` | `3` | 人物最低评论数（通常更严格） |
| `--min-char-id` | 无限制 | 角色 ID 下限 |
| `--max-char-id` | 无限制 | 角色 ID 上限 |
| `--min-person-id` | 无限制 | 人物 ID 下限 |
| `--max-person-id` | 无限制 | 人物 ID 上限 |
| `--chars-only` | `false` | 仅搜索角色 |
| `--persons-only` | `false` | 仅搜索人物 |
| `--open` | `false` | 在浏览器中打开匹配页面 |

### `top-chars` — 声优代表角色 Top-K

按评论数排名，找出某位声优配音过的最受欢迎角色。

```bash
# 首次使用：必须先构建缓存（扫描全量 JSONLINES，约需几分钟）
bgm-birthday top-chars --person-id 32253 --build-cache

# 之后直接查询（秒级响应）
bgm-birthday top-chars --person-id 32253

# 自定义返回数量
bgm-birthday top-chars --person-id 32253 --top 20

# 指定缓存目录
bgm-birthday top-chars --person-id 32253 --cache-dir /tmp/bgm-cache

# 在浏览器中打开 Top-K 角色页面
bgm-birthday top-chars --person-id 32253 --open
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--person-id` | 必填 | 声优/人物的 Bangumi ID |
| `--top` | `15` | 返回前 K 个角色 |
| `--build-cache` | `false` | 重新扫描 JSONLINES 构建缓存 |
| `--cache-dir` | `.`（当前目录）| 缓存文件（`person_entries.json`、`character_entries.json`）存放目录 |
| `--open` | `false` | 在浏览器中打开角色页面 |

### `output-gen` — 生成论坛格式生日榜单

从维护的 Excel 文件读取数据，生成可直接粘贴到论坛的 BBCode 格式榜单文本。

```bash
# 生成今天生日的榜单
bgm-birthday output-gen --excel /path/to/hbd2waifu.xlsm

# 生成指定日期的榜单
bgm-birthday output-gen --excel /path/to/hbd2waifu.xlsm --date 03-17

# 指定输出文件路径
bgm-birthday output-gen --excel /path/to/hbd2waifu.xlsm --date 03-17 --output ./output.txt

# 自定义各榜单的 Top-N 数量
bgm-birthday output-gen --excel /path/to/data.xlsm --date 03-17 \
    --top-anime 50 --top-gal 20 --top-fangwen 10

# 设置人气分数门槛（过滤过于冷门的角色）
bgm-birthday output-gen --excel /path/to/data.xlsm --date 03-17 \
    --popularity-threshold 5.0
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--excel` | 必填 | Excel 数据文件路径（`.xlsm` 或 `.xlsx`） |
| `--output` | `output.txt` | 输出文本文件路径 |
| `--date` | `today` | 目标日期，`MM-DD` 格式或 `today` |
| `--top-anime` | `1000` | 动画榜 Top N |
| `--top-gal` | `40` | Galgame 榜 Top N |
| `--top-fangwen` | `30` | 芳文社榜 Top N |
| `--popularity-threshold` | `0.0` | 人气分数门槛（`评论数 × 1.0 + 收藏数 × 0.3`） |

---

## ETL 流水线（`bgm-etl`）

将 JSONLINES 数据导入 MongoDB，供 Web API 查询。

### `run` — 执行完整流水线

```bash
# 完整流水线：角色提取 → 关系导入 → 数据合并 → 创建索引
bgm-etl run

# 跳过某些步骤（增量更新时使用）
bgm-etl run --skip-chars       # 跳过角色提取
bgm-etl run --skip-relations   # 跳过关系导入
bgm-etl run --skip-merge       # 跳过合并

# 调整批量写入大小（内存受限时减小）
bgm-etl run --batch-size-chars 500 --batch-size-rels 2000
```

### 单步命令

```bash
bgm-etl characters   # 提取角色生日 → characters 集合
bgm-etl relations    # 导入作品-角色关系 → subject_characters 集合
bgm-etl merge        # 合并两表 → date_char_sub 集合
bgm-etl indexes      # 在所有集合上创建索引（幂等）
```

### `--dry-run` 模式

`characters` 和 `relations` 子命令支持 `--dry-run`，只统计行数不写库：

```bash
bgm-etl characters --dry-run
bgm-etl relations --dry-run
```

---

## Web 服务

### 启动后端

```bash
cd web/backend
uvicorn app:app --reload --port 5000
```

### 启动前端（开发模式）

```bash
cd web/frontend
npm install
npm run dev      # 默认 http://localhost:5173，自动代理 /api 到后端
```

### 构建前端

```bash
npm run build    # 输出到 web/frontend/dist/
```

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/` | 健康检查 |
| `GET` | `/api/today` | 全站今日生日角色列表 |
| `GET` | `/api/date/<MM-DD>` | 全站指定日期生日角色列表 |
| `GET` | `/api/hbd2waifu` | 用户收藏作品中指定日期生日的角色 |

**`/api/hbd2waifu` 查询参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `userid` | ✅ | Bangumi 用户名或数字 ID |
| `date` | 可选 | `MM-DD` 格式，默认今日 |
| `subject_type` | 可选 | 条目类型过滤（`2`=动画，`4`=游戏 等） |

**响应格式（数组）：**

```json
[
  {
    "character_id": 76324,
    "name": "市川雛菜",
    "chinese_name": "市川雏菜",
    "birthday": "03-17"
  }
]
```

---

## Excel 批量 ID 匹配

将 Excel 表格中的角色名（B 列）+ 生日（J 列）自动匹配为 Bangumi character ID，写入 A 列：

```bash
# 基本用法（只填充 A 列为空的行）
python scripts/id_match.py --excel /path/to/相关人物.xlsm

# 覆盖 A 列已有值
python scripts/id_match.py --excel /path/to/相关人物.xlsm --overwrite

# 指定输出文件（默认：原文件名 + _matched 后缀）
python scripts/id_match.py --excel /path/to/相关人物.xlsm \
    --output /path/to/相关人物_匹配后.xlsm

# 指定数据目录（覆盖 .env 中的 BGM_DATA_DIR）
python scripts/id_match.py --excel /path/to/相关人物.xlsm \
    --data-dir /data/bangumi
```

---

## 配置说明（`.env`）

```dotenv
# JSONLINES 数据文件目录
BGM_DATA_DIR=/path/to/bangumi-data

# MongoDB 连接
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=hbd2waifu

# Redis 连接
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600          # 缓存过期时间（秒）

# CORS（浏览器插件跨域调用，生产环境保持 * 即可）
# 若需要限制来源，改为具体域名，如 https://bgm.tv
CORS_ALLOW_ORIGIN=*

# 浏览器路径（CLI --open 参数使用，留空则调用系统默认浏览器）
# BROWSER_PATH="/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"

# 日志级别（DEBUG / INFO / WARNING / ERROR）
LOG_LEVEL=INFO
```

---

## 开发

### 运行测试

```bash
pytest                        # 运行所有测试
pytest -v                     # 详细输出
pytest tests/test_date_utils.py  # 运行单个测试文件
pytest --cov=bangumi_birthday    # 生成覆盖率报告
```

### 代码检查

```bash
ruff check .     # lint
ruff format .    # 格式化
mypy bangumi_birthday/  # 类型检查
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
│   │   ├── mongo.py           # MongoDB 同步/异步双客户端
│   │   └── models.py          # Pydantic 数据模型
│   ├── etl/
│   │   ├── pipeline.py        # ETL CLI 入口（Click）
│   │   ├── extract_chars.py   # 角色生日提取
│   │   ├── extract_relations.py # 作品-角色关系导入
│   │   └── merge.py           # 数据合并
│   └── cli/
│       ├── main.py            # bgm-birthday 主入口
│       ├── birthday_search.py # search 命令
│       ├── top_chars.py       # top-chars 命令
│       └── output_gen.py      # output-gen 命令
├── web/
│   ├── backend/
│   │   ├── app.py             # Quart App Factory
│   │   ├── routes/
│   │   │   └── birthday.py    # 路由蓝图
│   │   └── services/
│   │       ├── birthday_svc.py  # 生日查询业务逻辑
│   │       └── bangumi_api.py   # Bangumi API 异步客户端
│   └── frontend/              # Vue 3 + Vite
│       └── src/
│           ├── views/         # 页面视图
│           ├── components/    # 可复用组件
│           └── composables/   # 状态逻辑（useBirthday 等）
├── scripts/
│   └── id_match.py            # Excel 批量 ID 匹配工具
├── tests/                     # 单元测试
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 许可证

MIT © Stivine
