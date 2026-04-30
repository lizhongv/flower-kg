# flower-kg 项目规范化与适度重构设计

- **日期**：2026-05-01
- **作者**：siren
- **范围**：现有「花卉知识图谱」项目（仓库目录 `huahuiKG`）

---

## 1. 目标与范围

### 1.1 目标

在保持运行结果一致的前提下，把现有项目规范化为可维护的 Python 包：

1. 拆分单一巨文件 `createKG.py`（195 行）与 `crawler/main.py`（291 行）为职责单一的模块
2. 抽离配置（YAML + .env），统一日志，统一 CLI 入口
3. 删除死代码（`lib/`）和不应入库的缓存（`home_html.txt`）
4. 编写规范的中文 README

**例外**：原 `createKG.py` step 4 存在路径 bug（详见 §5.1），导致原代码 step 4 实际未生效。重构会**修复**该 bug。这意味着重构后 Neo4j 图会**多出**原本缺失的「具体分支」节点（界门纲目科属种的叶子节点）—— 这是符合作者意图的修正，而不是回归。如需严格对照原行为，可在 spec review 阶段要求保留 bug。

### 1.2 非目标（明确不做，避免范围蔓延）

- 不改算法 / 数据结构 / Neo4j schema
- 不写单元测试
- 不做可视化导出
- 不切换爬虫框架（保留 requests + re）
- 不重命名 Neo4j 节点标签或 `data/` 中的中文文件名（这些是业务数据本身）
- 不保留旧路径 shim（用户从旧版升级时通过 README 的迁移表对照新旧命令）

### 1.3 关键决策（由 brainstorming 阶段确定）

| 维度 | 决策 |
|---|---|
| 重构力度 | 适度重构（保持运行逻辑不变） |
| 标识符语言 | 英文标识符 + 中文注释/docstring（PEP 8） |
| 项目名 | `flower-kg` / Python 包名 `flower_kg` |
| 配置 | `config.yaml`（PyYAML） + `.env`（敏感字段） |
| CLI | argparse 子命令，`python -m flower_kg <cmd>` |
| 历史包袱 | 删 `lib/`、`home_html.txt` 移到 gitignored 缓存目录、删旧 `createKG.py` |
| 附加功能 | 仅替换 print 为 logging，不写测试、不做可视化 |

### 1.4 成功判据

1. `python -m flower_kg crawl` 产出与原 `crawler/main.py` 完全相同的 `data/**/*.xlsx` 与 `data/*.txt`
2. `python -m flower_kg build` 产出的 Neo4j 图与原 `createKG.py` 在 step 0–3 + createFlower 部分完全一致；step 4 因修复路径 bug 会新增一批「具体分支」节点（详见 §1.1 例外条款）
3. 任何敏感配置（密码、Cookie）不再出现在源码中
4. README 含项目介绍、目录、功能、环境、启动 5 个章节

---

## 2. 目标目录结构

```
flower-kg/
├── flower_kg/                       # 主包
│   ├── __init__.py                  # 暴露 __version__
│   ├── __main__.py                  # python -m flower_kg → cli.main()
│   ├── cli.py                       # argparse 子命令分发
│   ├── config.py                    # 加载 config.yaml + .env，dataclass 校验
│   ├── logging_setup.py             # logging.basicConfig 统一配置
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── client.py                # HTTP GET 封装 + 重试 + headers 注入
│   │   ├── parser.py                # 纯函数：正则解析 → dict
│   │   ├── taxonomy.py              # 界门纲目科属种聚合
│   │   └── runner.py                # 编排入口 run(cfg, logger)
│   └── builder/
│       ├── __init__.py
│       ├── connection.py            # py2neo Graph 工厂 + clear_all()
│       ├── entities.py              # 原 createEntity0 拆 4 个函数
│       ├── flowers.py               # 原 createFlower
│       └── runner.py                # 编排入口 run(cfg, logger)
├── data/                            # 保留中文目录名 / 中文文件名（业务数据）
│   ├── cache/                       # ← 新增，被 .gitignore 忽略
│   ├── 养护难度/                     # 保持不变
│   ├── 应用环境/                     # 保持不变
│   ├── 盛花期_习性/                  # 保持不变
│   ├── 花卉功能/                     # 保持不变
│   ├── 花卉类别/                     # 保持不变
│   ├── 花卉大全.txt                  # 保持不变
│   ├── 种类.txt
│   └── 界.txt / 门.txt / ... / 种.txt
├── docs/
│   └── superpowers/specs/           # 本设计文档所在地
├── config.yaml.example              # 配置模板（提交入库）
├── config.yaml                      # 实际配置（被 .gitignore）
├── .env.example                     # 仅放敏感字段模板
├── .env                             # 实际敏感配置（被 .gitignore）
├── .gitignore                       # 新增
├── pyproject.toml                   # PEP 621 标准
├── requirements.txt                 # 保留兼容，从 pyproject 同步
└── README.md                        # 重写
```

**删除项**：`createKG.py`、`crawler/`（旧目录）、`crawler/home_html.txt`、`lib/` 整个

---

## 3. 模块职责与接口

### 3.1 `flower_kg/config.py`

```python
@dataclass(frozen=True)
class CrawlerConfig:
    base_url: str
    home_path: str
    headers: dict[str, str]
    request_timeout: int
    page_sleep_seconds: float
    cache_dir: Path

@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str  # 从 .env 注入

@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    crawler: CrawlerConfig
    neo4j: Neo4jConfig

def load_config(path: Path = Path("config.yaml")) -> AppConfig: ...
```

加载顺序：`load_dotenv()` → 读 yaml → 用 `os.getenv()` 覆盖敏感字段。
缺失敏感字段时抛 `ConfigError("NEO4J_PASSWORD 未配置")`，错误信息中文。

### 3.2 `flower_kg/crawler/client.py`

```python
class HttpClient:
    def __init__(self, headers: dict, timeout: int): ...
    def get_text(self, url: str) -> str | None  # 失败返回 None
```

### 3.3 `flower_kg/crawler/parser.py`（纯函数）

```python
def parse_titles(home_html: str) -> tuple[list[str], list[tuple[str, str]]]
def parse_detail(html: str) -> dict
def parse_belongs(belong_text: str) -> dict[str, list[str]]   # 拆界门纲目科属种
def is_last_page(page_html: str) -> bool
```

### 3.4 `flower_kg/crawler/taxonomy.py`

```python
class TaxonomyCollector:
    """累计 7 级分类，跨花卉去重。消除原全局可变状态 Kingdom/Phylum/..."""
    LEVELS = ["界", "门", "纲", "目", "科", "属", "种"]

    def add(self, parsed_belongs: dict[str, list[str]]) -> None
    def write_to(self, data_dir: Path) -> None        # 7 个 .txt
```

### 3.5 `flower_kg/crawler/runner.py`

```python
def run(cfg: AppConfig, logger: logging.Logger) -> None:
    """编排：抓主页 → 建索引 → 遍历每个 title/category/page/flower → 保存 xlsx。
    将原 crawl_page_content 中 4 层嵌套循环拆为有名小函数：
      _iter_categories / _iter_pages / _iter_details / _save_category
    """
```

### 3.6 `flower_kg/builder/connection.py`

```python
def connect(cfg: Neo4jConfig) -> Graph
def clear_all(graph: Graph) -> None      # MATCH (n) DETACH DELETE n
```

### 3.7 `flower_kg/builder/entities.py`（原 `createEntity0` 拆开）

```python
def build_root_categories(graph, data_dir, title_classes, page_size) -> None  # step 0+1
def build_flower_types(graph, data_dir) -> None                               # step 2
def build_taxonomy_branches(graph) -> None                                    # step 3
def build_taxonomy_leaves(graph, data_dir, taxonomy_levels) -> None           # step 4
```

### 3.8 `flower_kg/builder/flowers.py`

```python
_FORBIDDEN_CHARS = ["'", ")", "(", "{", "}"]

def build_flowers(graph, data_dir, title_classes, page_size) -> None
def _sanitize(text: str) -> str
def _link_taxonomy_chain(graph, belongs: list[str]) -> None
```

### 3.9 `flower_kg/builder/runner.py`

```python
def run(cfg: AppConfig, logger) -> None:
    graph = connect(cfg.neo4j)
    clear_all(graph)
    build_root_categories(...)
    build_flower_types(...)
    build_taxonomy_branches(...)
    build_taxonomy_leaves(...)
    build_flowers(...)
```

### 3.10 `flower_kg/cli.py`

```
python -m flower_kg crawl              # 调 crawler.runner.run
python -m flower_kg build              # 调 builder.runner.run
python -m flower_kg clear              # 仅清空 Neo4j 图（运维用）
python -m flower_kg --version
```

---

## 4. 配置与日志

### 4.1 `config.yaml.example`

```yaml
data_dir: ./data

crawler:
  base_url: http://www.aihuhua.com
  home_path: /hua/
  request_timeout: 15
  page_sleep_seconds: 0.5
  cache_dir: ./data/cache
  headers:
    User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ..."
    Accept: "text/html,application/xhtml+xml,..."
    # Cookie 从 .env 注入

neo4j:
  uri: http://localhost:7474/
  user: neo4j
  # password 从 .env 读取
```

### 4.2 `.env.example`

```
NEO4J_PASSWORD=your_password_here
AIHUHUA_COOKIE=
```

### 4.3 `.gitignore`

```
__pycache__/
*.pyc
.venv/
venv/
.env
config.yaml
data/cache/
.idea/
.vscode/
*.egg-info/
dist/
build/
```

注：`data/` 里的爬取结果（xlsx、txt）保留入库，因为是项目「成果产物」，重新爬取代价较高。

### 4.4 日志（`logging_setup.py`）

格式：`2026-05-01 10:00:00 [INFO] flower_kg.crawler: 消息`，输出到 stdout（可选写文件）。

替换规则：
- 业务进度（`>>> 开始爬取-{name}`）→ `logger.info`
- 异常分支（爬取失败、解析错误）→ `logger.warning`
- step 完成（`step 0 done`）→ `logger.info`
- 单条花卉成功记录 → `logger.debug`（默认不显示）

---

## 5. 迁移流程与代码改动要点

### 5.1 文件迁移映射（一一对应，便于核对）

| 旧位置 | 新位置 | 处理方式 |
|---|---|---|
| `createKG.py::createEntity0` step 0+1 | `flower_kg/builder/entities.py::build_root_categories` | 函数体几乎不变，去掉硬编码 `data_dir` |
| `createKG.py::createEntity0` step 2 | `entities.py::build_flower_types` | 同上 |
| `createKG.py::createEntity0` step 3 | `entities.py::build_taxonomy_branches` | 同上 |
| `createKG.py::createEntity0` step 4 | `entities.py::build_taxonomy_leaves` | **修一个 bug**：原代码 `os.path.join(data_dir,'科属', p+'.txt')` 路径不存在（实际文件在 `data/属.txt`），需改为 `os.path.join(data_dir, p+'.txt')` |
| `createKG.py::createFlower` | `flower_kg/builder/flowers.py::build_flowers` | 内部 `delt` 列表抽成 `_FORBIDDEN_CHARS` 常量；去字符的逻辑抽 `_sanitize` |
| `crawler/main.py::construct_title_class` | `crawler/runner.py` 内部步骤 + `parser.py::parse_titles` | 拆 IO 与解析 |
| `crawler/main.py::crawl_page_content` | `crawler/runner.py::run` | 嵌套 4 层 while/for 拆为 `_iter_categories` / `_iter_pages` / `_iter_details` / `_save_category` |
| `crawler/main.py` 全局 `Kingdom/Phylum/...` | `crawler/taxonomy.py::TaxonomyCollector` 实例属性 | 消除全局可变状态 |
| `crawler/main.py::get_belongs` | `parser.py::parse_belongs` + `TaxonomyCollector.add` | 解析与累积分离 |
| `crawler/main.py::save_pd` | `crawler/runner.py::_save_category` | DataFrame 列定义抽成 `_COLUMNS` 常量 |
| `crawler/main.py::save_belongs` | `TaxonomyCollector.write_to` | 7 行重复 `with open` 改为循环 |
| `crawler/main.py::headers` 字典 | `config.yaml` | Cookie 从 `.env` 注入 |
| `crawler/home_html.txt` | `data/cache/home.html`（gitignored） | 移动 + 改名 |
| `lib/` 整个 | 删除 | 已确认未被引用 |
| `requirements.txt`（2 行） | `pyproject.toml` 的 `dependencies` | 补齐：`requests`, `pandas`, `numpy`, `lxml`, `openpyxl`, `py2neo`, `pyyaml`, `python-dotenv` |
| 旧 `README.md` | 重写 | 见 §6 |

### 5.2 错误处理统一约定

- **网络层**（`client.py`）：`requests` 异常 → log warning + 返回 `None`，调用方决定跳过还是终止
- **解析层**（`parser.py`）：纯函数，不抛业务异常；返回值为 `None` 或空 list 表示无匹配
- **编排层**（`runner.py`）：捕获所有，决定继续或退出，确保已抓数据不丢

### 5.3 兼容性

不保留旧路径 shim。用户从旧版升级时，README「迁移说明」一节给出新旧命令对照表。

---

## 6. README 结构

```markdown
# 🌸 flower-kg | 花卉知识图谱

> 基于 Neo4j 的花卉百科知识图谱，从 aihuhua.com 爬取约 4500 种花卉数据，构建包含
> 花卉类别、功能、应用环境、习性、养护难度、生物分类（界门纲目科属种）的多维知识图。

## 目录
- 项目简介
- 功能特性
- 项目结构
- 环境要求
- 快速开始
- 配置说明
- 常用 Cypher 查询
- 从旧版迁移
- 参考资料

## 项目简介
（一段：项目背景、数据来源、整体流程图——主页爬取 → 详情爬取 → Excel 落地 → 导入 Neo4j）

## 功能特性
- 多级爬取（5 大分类 / 46 小类 / ~4500 种花卉）
- 7 级生物分类自动聚合（界门纲目科属种 + 跨花卉去重）
- Excel 中间数据落地，便于审查
- 自动导入 Neo4j
- YAML 配置 + .env 敏感信息分离
- 统一日志

## 项目结构
（tree 图，对应 §2）

## 环境要求
- Python ≥ 3.9
- Neo4j ≥ 4.x（社区版即可）
- Windows / macOS / Linux

## 快速开始

### 1. 克隆与安装
git clone <repo>
cd flower-kg
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .

### 2. 配置
cp config.yaml.example config.yaml
cp .env.example .env
# 编辑 .env，填入 NEO4J_PASSWORD

### 3. 启动 Neo4j
neo4j console        # 或 neo4j start
# 浏览器访问 http://localhost:7474

### 4. 爬取数据（首次需要，约 30 分钟）
python -m flower_kg crawl

### 5. 构建图谱
python -m flower_kg build

### 6. 浏览器查看
http://localhost:7474，运行 MATCH (n) RETURN n LIMIT 100

## 配置说明
（表格：每个 yaml/.env 字段名、含义、默认值）

## 常用 Cypher 查询
（4-6 个示例）

## 从旧版迁移
| 旧命令 | 新命令 |
|---|---|
| python crawler/main.py | python -m flower_kg crawl |
| python createKG.py | python -m flower_kg build |

## 参考资料
- 数据来源：aihuhua.com
- Neo4j Cypher 教程
- 视频教程
- 相关参考项目
```

---

## 7. 实施风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| Neo4j 图与原版有差异 | 成功判据 #2 不通过 | 重构后跑一次 build，用 `MATCH (n) RETURN labels(n), count(*)` 与原版逐项对照 |
| 爬虫产物文件不一致 | 成功判据 #1 不通过 | 保留原 `data/` 当前内容作为基准；如需重爬，diff 文件清单 |
| 修复 step 4 路径 bug 时引入回归 | step 4 节点缺失 | 修复后单独跑 `build_taxonomy_leaves` 验证 7 个层级文件全部读到 |
| `.env` 缺失导致首次运行报错 | 用户体验差 | `config.py` 给出明确中文报错指引，README 第 2 步突出强调 |
| 删除 `lib/` 后某处隐式依赖 | 运行报错 | grep 验证零引用（已完成），删除后跑一次完整流程兜底 |

---

## 8. 后续步骤

设计审核通过后，下一步进入 `writing-plans` 技能，产出按文件级别拆分、可串行执行的实现计划。
