# 通用结构化输出智能体

基于 LLM 的文本结构化信息抽取工具。用户自定义输出 JSON 的字段（字段名、类型、描述、枚举值等），智能体根据输入文档按用户定义的 schema 输出结构化 JSON。

## 项目结构

```
├── structured_agent.py   # 核心智能体模块（字段定义、动态模型构建、Prompt 构建、提取逻辑）
├── structured_app.py     # Streamlit 前端界面
└── README.md
```

## 支持的字段类型

| 类型 | 说明 |
|------|------|
| `string` | 自由文本 |
| `enum` | 枚举值（需提供可选值列表） |
| `float` | 浮点数（可选 min/max 约束） |
| `int` | 整数（可选 min/max 约束） |
| `bool` | 布尔值 |
| `list[enum]` | 枚举值列表（多选） |

## 技术栈

- **LLM 调用**: LangChain + ChatOpenAI（默认接入 DeepSeek）
- **数据校验**: Pydantic（动态模型构建）
- **前端界面**: Streamlit

## 安装依赖

```bash
pip install langchain langchain-openai pydantic streamlit
```

## 使用方式

### 1. Streamlit 界面（推荐）

```bash
streamlit run structured_app.py
```

启动后可在浏览器中：
- 在侧边栏配置模型 API Key、模型名称、Base URL 等
- 在「字段定义」页签中添加/删除字段，或使用内置快速模板
- 在「文档提取」页签中输入文档内容，点击提取获得结构化 JSON 结果

内置快速模板：
- 研报打标模板
- 基金经理发言模板
- 新闻情感分析模板

### 2. Python 代码调用

```python
from structured_agent import FieldDefinition, StructuredAgent

fields = [
    FieldDefinition(
        name="industry",
        display_name="行业",
        field_type="enum",
        description="文章所属的行业分类",
        enum_values=["银行", "非银金融", "医药生物", "电子", "计算机"],
    ),
    FieldDefinition(
        name="summary",
        display_name="摘要",
        field_type="string",
        description="用一句话概括文章核心观点，50字以内",
    ),
]

agent = StructuredAgent(
    fields=fields,
    model_name="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key="your-api-key",
)

result = agent.run("你的文档内容...")
print(result)

# 批量提取
results = agent.run_batch(["文档1...", "文档2..."])
```

## 核心 API

### FieldDefinition

字段定义数据类，属性：

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | str | 字段名称（英文，作为 JSON key） |
| `display_name` | str | 字段显示名称（中文） |
| `field_type` | str | 字段类型（见上表） |
| `description` | str | 字段含义描述，指导模型理解该字段应填什么 |
| `enum_values` | list[str] \| None | enum / list[enum] 类型的可选值列表 |
| `min_value` | float \| None | 数值类型的最小值 |
| `max_value` | float \| None | 数值类型的最大值 |

### StructuredAgent

| 方法 | 说明 |
|------|------|
| `run(content: str) -> dict` | 对单篇文档进行结构化提取 |
| `run_batch(contents: list[str]) -> list[dict]` | 批量提取 |

构造参数：`fields`, `model_name`, `base_url`, `api_key`, `temperature`
