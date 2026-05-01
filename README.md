# 🌸 flower-kg | 花卉知识图谱

> 基于 Neo4j 的花卉百科知识图谱：从 [aihuhua.com](http://www.aihuhua.com) 爬取约 4500 种花卉数据，
> 构建覆盖 **花卉类别 / 花卉功能 / 应用环境 / 盛花期 & 习性 / 养护难度** 五大维度，
> 并补充 **界 → 门 → 纲 → 目 → 科 → 属 → 种** 七级生物分类的多维知识图。

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](#)
[![Neo4j](https://img.shields.io/badge/neo4j-4.x%2B-008CC1.svg)](#)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#)

---

## 目录

- [项目简介](#-项目简介)
- [功能特性](#-功能特性)
- [项目结构](#-项目结构)
- [环境要求](#-环境要求)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [常用 Cypher 查询](#-常用-cypher-查询)
- [从旧版迁移](#-从旧版迁移)
- [参考资料](#-参考资料)
- [License](#license)

---

## 📖 项目简介

`flower-kg` 是一个**端到端**的花卉领域知识图谱构建工具，分两步：

1. **采集**：从公开花卉百科网站爬取每个花卉的基础信息（名称、别名、图片、分类、科属、盛花期、简介）
2. **建图**：将爬取产物结构化导入 Neo4j，建立多维关联

整体数据流：

```
aihuhua.com 主页
        │  (HTTP 抓取，主页 HTML 缓存到 data/cache/)
        ▼
   解析一级分类
        │
        ▼
   遍历二级类别 → 列表页 → 详情页
        │
        ▼
   data/<title>/<class>.xlsx   (按二级类别一表)
   data/{界,门,纲,目,科,属,种}.txt (七级分类去重表)
   data/种类.txt               (花卉品种汇总)
   data/花卉大全.txt            (一级分类索引)
        │
        ▼
   py2neo 导入 Neo4j
        │
        ▼
   Neo4j 图数据库（http://localhost:7474）
```

---

## ✨ 功能特性

- 🕷 **多级爬取**：5 大一级分类 × 46 个二级类别 × 自动翻页 ≈ 4500 种花卉
- 🌳 **七级生物分类聚合**：跨花卉自动去重，输出独立索引文件
- 📊 **Excel 中间产物**：每个二级类别一份 `.xlsx`，便于人工审查
- 🔗 **Neo4j 自动建图**：节点 ~5000+ / 关系 ~10000+，多种关系类型（划分 / 归属 / 属于 / 归于 / 从属）
- ⚙️ **YAML + .env 配置**：业务参数与敏感信息分离，源码不留密码
- 📝 **统一日志**：标准 `logging`，支持终端 + 文件双输出
- 🎯 **统一 CLI**：`python -m flower_kg {crawl,build,clear}` 三个子命令搞定

---

## 📁 项目结构

```
flower-kg/
├── flower_kg/                    # Python 主包
│   ├── __init__.py
│   ├── __main__.py               # python -m flower_kg
│   ├── cli.py                    # argparse 子命令分发
│   ├── config.py                 # YAML + .env 加载
│   ├── logging_setup.py          # 日志初始化
│   ├── crawler/                  # 爬虫子包
│   │   ├── client.py             #   HTTP 客户端封装
│   │   ├── parser.py             #   纯函数：HTML 正则解析
│   │   ├── taxonomy.py           #   七级分类累积器
│   │   └── runner.py             #   编排入口
│   └── builder/                  # 图谱构建子包
│       ├── connection.py         #   Neo4j 连接 + 清空
│       ├── entities.py           #   根节点 / 一级二级分类 / 七级骨架
│       ├── flowers.py            #   花卉详情节点
│       └── runner.py             #   编排入口
├── data/                         # 数据目录（爬取产物 + 知识图谱源数据）
│   ├── cache/                    #   主页 HTML 缓存（gitignored）
│   ├── 花卉类别/ 花卉功能/ ...     #   每个一级分类一个目录，下含若干 .xlsx
│   ├── 花卉大全.txt               #   一级分类索引
│   ├── 种类.txt                   #   花卉品种汇总
│   └── 界.txt 门.txt ... 种.txt    #   七级生物分类
├── docs/superpowers/specs/       # 设计文档
├── config.yaml.example           # 配置模板
├── .env.example                  # 敏感配置模板
├── pyproject.toml                # PEP 621 包元数据
├── requirements.txt              # 依赖清单（与 pyproject 同步）
└── README.md
```

---

## 🛠 环境要求

| 组件 | 版本 |
|---|---|
| Python | ≥ 3.9 |
| Neo4j | ≥ 4.x（社区版即可） |
| OS | Windows / macOS / Linux |

依赖（详见 `pyproject.toml`）：`requests`、`lxml`、`pandas`、`numpy`、`openpyxl`、`py2neo`、`PyYAML`、`python-dotenv`。

---

## 🚀 快速开始

### 1. 克隆与安装

```bash
git clone <repo-url>
cd flower-kg

# 创建虚拟环境
python -m venv .venv

# 激活（Windows）
.venv\Scripts\activate
# 激活（macOS / Linux）
source .venv/bin/activate

# 以可编辑模式安装
pip install -e .
```

### 2. 配置

```bash
# 复制配置模板
cp config.yaml.example config.yaml
cp .env.example .env

# 编辑 .env，填入 Neo4j 密码（必填）
#   NEO4J_PASSWORD=your_password_here
# 如目标站点要求 Cookie，也可在此处填写 AIHUHUA_COOKIE
```

### 3. 启动 Neo4j

下载 [Neo4j 社区版](https://neo4j.com/download-center/) 解压，进入 `bin/` 目录：

```bash
neo4j console        # 前台启动（推荐）
# 或
neo4j start          # 后台启动；停止用 neo4j stop
```

浏览器打开 <http://localhost:7474>，首次登录默认账号 `neo4j / neo4j`，按提示修改密码后同步到 `.env`。

### 4. 爬取数据（首次运行约 30 分钟）

```bash
python -m flower_kg crawl
```

> 主页 HTML 会缓存到 `data/cache/home.html`，重复运行时复用。如需重新抓取主页，删掉该文件即可。

### 5. 构建图谱

```bash
python -m flower_kg build
```

构建过程会先清空 Neo4j 中已有数据，然后按以下顺序创建：根节点 → 一级二级分类 → 花卉品种 → 七级分类骨架 → 七级具体分支 → 花卉节点与关系。

### 6. 浏览器查看

打开 <http://localhost:7474>，运行：

```cypher
MATCH (n) RETURN n LIMIT 100
```

如需仅清空图数据库（运维用）：

```bash
python -m flower_kg clear
```

---

## ⚙️ 配置说明

### `config.yaml` 字段

| 字段 | 含义 | 默认值 |
|---|---|---|
| `data_dir` | 数据根目录 | `./data` |
| `crawler.base_url` | 目标站点根 URL | `http://www.aihuhua.com` |
| `crawler.home_path` | 主页路径 | `/hua/` |
| `crawler.request_timeout` | 单次 HTTP 超时（秒） | `15` |
| `crawler.page_sleep_seconds` | 翻页间隔（秒，控速） | `0.5` |
| `crawler.cache_dir` | 主页 HTML 缓存目录 | `./data/cache` |
| `crawler.headers` | 请求头（不含 Cookie） | 见模板 |
| `neo4j.uri` | Neo4j HTTP 地址 | `http://localhost:7474/` |
| `neo4j.user` | Neo4j 用户名 | `neo4j` |
| `logging.level` | 日志级别 | `INFO` |
| `logging.log_file` | 日志文件路径（null = 仅 stdout） | `null` |

### `.env` 字段（敏感信息，不入库）

| 字段 | 含义 | 必填 |
|---|---|---|
| `NEO4J_PASSWORD` | Neo4j 数据库密码 | 是 |
| `AIHUHUA_COOKIE` | 爬虫站点 Cookie | 否 |

---

## 🔍 常用 Cypher 查询

```cypher
// 1. 看图全貌
MATCH (n) RETURN n LIMIT 200;

// 2. 按花卉名查找（含别名）
MATCH (f:花卉)
WHERE f.name CONTAINS '玫瑰' OR f.别名 CONTAINS '玫瑰'
RETURN f;

// 3. 查询某花卉的全部分类层级
MATCH path = (f:花卉 {name: '月季'})-[*1..3]-(n)
RETURN path;

// 4. 统计每个「科」下的花卉数量 Top 10
MATCH (f:花卉)-[:属于]->(c:具体分支)
WHERE c.name ENDS WITH '科'
RETURN c.name AS 科, count(f) AS 数量
ORDER BY 数量 DESC LIMIT 10;

// 5. 查询所有「适合卧室养的、容易养护的」花卉
MATCH (f:花卉)-[:归于]->(:应用环境 {name: '卧室花卉'})
MATCH (f)-[:归于]->(:养护难度 {name: '容易养殖花卉'})
RETURN f.name, f.开花季节;

// 6. 清空整个图（谨慎使用）
MATCH (n) DETACH DELETE n;
```

---

## 🔄 从旧版迁移

如果你之前用的是仓库根目录下的 `createKG.py` 与 `crawler/main.py`，按下表替换命令即可：

| 旧命令 | 新命令 | 备注 |
|---|---|---|
| `python crawler/main.py` | `python -m flower_kg crawl` | 主页缓存改名为 `data/cache/home.html` |
| `python createKG.py` | `python -m flower_kg build` | 已修复 step 4 路径 bug |
| 改源码里的 `headers` / `auth` | 改 `config.yaml` + `.env` | 密码不再硬编码 |
| `pip install py2neo openpyxl` | `pip install -e .` | 依赖完整，含 requests/pandas 等 |

⚠️ **重要变化**：旧版 `createKG.py::createEntity0` 的 step 4 错误地拼接了不存在的 `data/科属/` 路径，导致七级分类的具体节点（如「植物界」「双子叶植物纲」等独立节点）从未真正写入 Neo4j。新版修复后，`build` 后图中会**新增**这些节点；标签 / 关系类型保持不变。

---

## 📚 参考资料

- 数据来源：<http://www.aihuhua.com>
- Neo4j Cypher 教程：<https://www.w3cschool.cn/neo4j/neo4j_cql_introduction.html>
- 视频教程（B 站）：<https://www.bilibili.com/video/BV1s44y1J7cG>
- 灵感参考：[Financial-Knowledge-Graphs](https://github.com/jm199504/Financial-Knowledge-Graphs)、[NlpPractice/KG_demo](https://github.com/coderLCJ/NlpPractice/tree/main/KG_demo)

---

## License

MIT
