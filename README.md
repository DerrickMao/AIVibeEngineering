# 通用结构化输出智能体

基于 LLM 的文本结构化信息抽取工具。用户自定义输出 JSON 的字段（字段名、类型、描述、枚举值等），智能体根据输入文档按用户定义的 schema 输出结构化 JSON。

支持为每个枚举值配置**判定标准**（定义、正例、反例），显著提升边界模糊标签的标注准确率。

## 项目结构

```
├── structured_agent.py    # 核心智能体模块（字段定义、动态模型构建、Prompt 构建、提取逻辑）
├── structured_app.py      # Streamlit 前端界面（通用结构化提取）
├── fund_manager_api.py    # FastAPI 接口（基金经理观点打标，固定 schema）
├── requirements.txt       # Python 依赖
├── .streamlit/config.toml # Streamlit 服务配置
└── README.md
```

## 支持的字段类型

| 类型 | 说明 |
|------|------|
| `string` | 自由文本 |
| `enum` | 枚举值（需提供可选值列表，可附带判定标准） |
| `float` | 浮点数（可选 min/max 约束） |
| `int` | 整数（可选 min/max 约束） |
| `bool` | 布尔值 |
| `list[enum]` | 枚举值列表（多选，可附带判定标准） |

## 技术栈

- **LLM 调用**: LangChain + ChatOpenAI（默认接入 DeepSeek）
- **数据校验**: Pydantic（动态模型构建）
- **前端界面**: Streamlit
- **HTTP 接口**: FastAPI + Uvicorn

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方式

### 1. Streamlit 界面（推荐）

```bash
streamlit run structured_app.py
```

启动后可在浏览器中：
- 在侧边栏配置模型 API Key、模型名称、Base URL 等
- 在「字段定义」页签中添加/删除字段，或使用内置快速模板
- 为枚举值配置判定标准（定义、正例、反例）
- 在「文档提取」页签中输入文档内容，点击提取获得结构化 JSON 结果

内置快速模板：
- 研报打标模板（含枚举判定标准示例）
- 基金经理发言模板
- 新闻情感分析模板

### 2. Python 代码调用

```python
from structured_agent import EnumValueDefinition, FieldDefinition, StructuredAgent

fields = [
    FieldDefinition(
        name="industry",
        display_name="行业",
        field_type="enum",
        description="文章所属的行业分类",
        enum_values=["银行", "电子", "计算机"],
        enum_definitions=[
            EnumValueDefinition(
                value="计算机",
                description="涉及软件开发、IT服务、云计算、信息安全、人工智能等",
                positive_examples=["某国产数据库厂商获得大额政府订单"],
                negative_examples=["消费电子芯片出货量下滑（应归为电子）"],
            ),
            EnumValueDefinition(
                value="电子",
                description="涉及半导体、消费电子、元器件等电子硬件领域",
                positive_examples=["某芯片公司量产28nm制程"],
                negative_examples=["软件SaaS公司营收增长（应归为计算机）"],
            ),
        ],
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

### EnumValueDefinition

枚举值判定标准，用于提升标注准确率：

| 参数 | 类型 | 说明 |
|------|------|------|
| `value` | str | 枚举值 |
| `description` | str | 该枚举值的含义定义 |
| `positive_examples` | list[str] | 正例：符合该标签的典型文本片段 |
| `negative_examples` | list[str] | 反例：容易误判为该标签但实际不属于的文本片段 |

### FieldDefinition

字段定义数据类：

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | str | 字段名称（英文，作为 JSON key） |
| `display_name` | str | 字段显示名称（中文） |
| `field_type` | str | 字段类型（见上表） |
| `description` | str | 字段含义描述，指导模型理解该字段应填什么 |
| `enum_values` | list[str] \| None | enum / list[enum] 类型的可选值列表 |
| `enum_definitions` | list[EnumValueDefinition] \| None | 每个枚举值的判定标准（可选） |
| `min_value` | float \| None | 数值类型的最小值 |
| `max_value` | float \| None | 数值类型的最大值 |

### StructuredAgent

| 方法 | 说明 |
|------|------|
| `run(content: str) -> dict` | 对单篇文档进行结构化提取 |
| `run_batch(contents: list[str]) -> list[dict]` | 批量提取 |

构造参数：`fields`, `model_name`, `base_url`, `api_key`, `temperature`

---

## 基金经理观点打标接口（FastAPI）

独立的 HTTP 接口，schema 固定，供下游 Java 等服务直接调用。

### 启动服务

```bash
# 设置环境变量（也可以直接修改 fund_manager_api.py 顶部的默认值）
export LLM_API_KEY="sk-your-api-key"
export LLM_BASE_URL="https://api.deepseek.com"
export LLM_MODEL="deepseek-chat"

# 启动（默认端口 8000）
python fund_manager_api.py
```

启动后可访问自动生成的交互式 API 文档：`http://localhost:8000/docs`

### 接口说明

**POST** `/api/fund-manager/label`

#### 请求参数

Content-Type: `application/json`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `queryContent` | string | 是 | 待分析的文章内容（可包含 HTML 标签如 `<p>`） |

请求示例：

```json
{
  "queryContent": "在信息过载、风格轮动加速的当下，投资似乎变得越来越"难"。某知名基金经理表示..."
}
```

#### 响应参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `code` | int | 状态码。`0` = 成功，`500` = 失败 |
| `data` | array | 打标结果数组，每位基金经理一条记录 |
| `msg` | string | 错误信息，成功时为空字符串 |

`data` 数组中每条记录的字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `manager_name` | string | 基金经理姓名 |
| `fund_company` | string | 基金公司名称 |
| `original_view` | string | 该基金经理的原始观点（从原文提取） |
| `sectors` | string[] | 涉及的板块（可多选，无则为空数组） |
| `industries` | string[] | 涉及的申万一级行业（可多选，无则为空数组） |
| `concepts` | string[] | 涉及的概念/主题（可多选，无则为空数组） |
| `sentiment` | string | 情感倾向 |

#### 枚举值列表

**sentiment（情感倾向）**：正面、中性、负面

**sectors（板块）**：消费、科技、金融、制造、周期、基建

**industries（申万一级行业）**：农林牧渔、基础化工、钢铁、有色金属、电子、家用电器、食品饮料、纺织服饰、轻工制造、医药生物、公用事业、交通运输、房地产、商贸零售、社会服务、综合、建筑材料、建筑装饰、电力设备、国防军工、计算机、传媒、通信、银行、非银金融、汽车、机械设备、煤炭、石油石化、环保、美容护理

**concepts（概念）**：新能源、芯片半导体、互联网、光伏、创新药、云计算、风电、保险、碳中和、消费电子、人工智能、黄金、生物科技、卫星&航天、低空经济、算力、机器人、脑机接口、游戏、稀土、养殖、电池、智能驾驶、电网设备

#### 响应示例

**成功（有基金经理观点）**：

```json
{
  "code": 0,
  "data": [
    {
      "manager_name": "张三",
      "fund_company": "XX基金",
      "original_view": "以中证指数为代表的纯固收资产持仓比例较高...",
      "sectors": [],
      "industries": [],
      "concepts": [],
      "sentiment": "中性"
    },
    {
      "manager_name": "李四",
      "fund_company": "YY基金",
      "original_view": "经济预计将温和修复，聚焦成长赛道中的AI软硬件...",
      "sectors": ["科技", "金融", "制造", "医药"],
      "industries": ["电子", "非银金融", "机械设备", "医药生物"],
      "concepts": ["人工智能", "芯片半导体", "新能源", "创新药", "生物科技"],
      "sentiment": "正面"
    }
  ],
  "msg": ""
}
```

**成功（无基金经理观点）**：

```json
{
  "code": 0,
  "data": [],
  "msg": ""
}
```

**失败**：

```json
{
  "code": 500,
  "data": [],
  "msg": "失败原因"
}
```

### 调用示例（curl）

```bash
curl -X POST http://localhost:8000/api/fund-manager/label \
  -H "Content-Type: application/json" \
  -d '{"queryContent": "某基金经理表示，看好AI和新能源板块..."}'
```

### 调用示例（Java / OkHttp）

```java
OkHttpClient client = new OkHttpClient();
MediaType JSON = MediaType.get("application/json; charset=utf-8");
String body = "{\"queryContent\": \"文章内容...\"}";
Request request = new Request.Builder()
    .url("http://<服务器IP>:8000/api/fund-manager/label")
    .post(RequestBody.create(body, JSON))
    .build();
Response response = client.newCall(request).execute();
System.out.println(response.body().string());
```

---

## 部署

核心步骤：

1. 阿里云 ECS（Ubuntu 22.04，2核4G即可），安全组开放 **8000**（API）和 **8501**（Streamlit）端口
2. 上传代码，安装依赖：`pip install -r requirements.txt`
3. 设置环境变量 `LLM_API_KEY`
4. 用 systemd 持久运行服务
5. 访问 `http://<服务器公网IP>:8000/docs` 查看 API 文档
