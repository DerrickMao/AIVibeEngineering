# 基金经理观点数据打标接口文档

## 基本信息

| 项目 | 说明 |
|------|------|
| 接口名称 | 基金经理观点数据打标 |
| 请求地址 | `http://124.223.42.93:8000/api/fund-manager/label` |
| 请求方式 | POST |
| Content-Type | application/json |
| 交互式文档 | `http://124.223.42.93:8000/docs` |

---

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `queryContent` | string | 是 | 待分析的文章内容（支持纯文本，也支持包含 `<p>` 等 HTML 标签） |

### 请求示例

```json
{
  "queryContent": "在信息过载、风格轮动加速的当下，投资似乎变得越来越\"难\"。当一个产业的变革周期从一年缩短至一个月，当市场的每一次情绪波动都能在交易层面被迅速放大，如何持续捕获超额收益？"
}
```

### 长文本转义注意事项

`queryContent` 的值是 JSON 字符串，当文章内容较长或包含特殊字符时，**必须进行正确的 JSON 转义**，否则会导致请求解析失败（HTTP 422）。

| 原始字符 | JSON 中必须转义为 | 说明 |
|----------|-------------------|------|
| `"` (双引号) | `\"` | 最常见，文章中的引用、书名号内容等 |
| `\` (反斜杠) | `\\` | 如路径、转义序列 |
| 换行符 | `\n` | 文章分段时使用 `\n` 代替真实换行 |
| 制表符 | `\t` | 表格类内容 |
| HTML 标签 | 原样传入即可 | `<p>`、`<br>` 等无需额外转义 |

**Java 示例**（使用 Jackson 自动处理转义）：
```java
ObjectMapper mapper = new ObjectMapper();
Map<String, String> body = Map.of("queryContent", articleContent);
String json = mapper.writeValueAsString(body);  // 自动转义所有特殊字符
```

**Python 示例**（使用 requests 库自动处理）：
```python
import requests
# json 参数会自动序列化，无需手动转义
resp = requests.post(url, json={"queryContent": article_content})
```

**curl 示例**（长文本建议从文件读取，避免手动转义）：
```bash
# 将文章内容写入 JSON 文件
echo '{"queryContent": "文章内容..."}' > request.json
curl -X POST http://124.223.42.93:8000/api/fund-manager/label \
  -H "Content-Type: application/json" \
  -d @request.json
```

> **建议**：不要手动拼接 JSON 字符串，使用语言自带的 JSON 序列化库（Java 的 Jackson/Gson、Python 的 json 模块）可以自动处理所有转义问题。

---

## 响应参数

### 顶层结构

| 参数 | 类型 | 说明 |
|------|------|------|
| `code` | int | 状态码。`0` = 成功，`500` = 失败 |
| `data` | array | 打标结果数组，每位基金经理一条记录；无基金经理观点时为空数组 |
| `msg` | string | 错误信息，成功时为空字符串 |

### data 数组中每条记录

| 字段 | 类型 | 说明 |
|------|------|------|
| `manager_name` | string | 基金经理姓名 |
| `fund_company` | string | 基金公司名称 |
| `original_view` | string | 该基金经理的原始观点文本（从原文中提取） |
| `sectors` | string[] | 涉及的板块（可多选，无则为 `[]`） |
| `industries` | string[] | 涉及的申万一级行业（可多选，无则为 `[]`） |
| `concepts` | string[] | 涉及的概念/主题（可多选，无则为 `[]`） |
| `sentiment` | string | 情感倾向 |

---

## 枚举值列表

### sentiment（情感倾向）

| 可选值 |
|--------|
| 正面 |
| 中性 |
| 负面 |

### sectors（板块）

| 可选值 |
|--------|
| 消费 |
| 科技 |
| 金融 |
| 制造 |
| 周期 |
| 基建 |

### industries（申万一级行业）

| 可选值 |
|--------|
| 农林牧渔 |
| 基础化工 |
| 钢铁 |
| 有色金属 |
| 电子 |
| 家用电器 |
| 食品饮料 |
| 纺织服饰 |
| 轻工制造 |
| 医药生物 |
| 公用事业 |
| 交通运输 |
| 房地产 |
| 商贸零售 |
| 社会服务 |
| 综合 |
| 建筑材料 |
| 建筑装饰 |
| 电力设备 |
| 国防军工 |
| 计算机 |
| 传媒 |
| 通信 |
| 银行 |
| 非银金融 |
| 汽车 |
| 机械设备 |
| 煤炭 |
| 石油石化 |
| 环保 |
| 美容护理 |

### concepts（概念）

| 可选值 |
|--------|
| 新能源 |
| 芯片半导体 |
| 互联网 |
| 光伏 |
| 创新药 |
| 云计算 |
| 风电 |
| 保险 |
| 碳中和 |
| 消费电子 |
| 人工智能 |
| 黄金 |
| 生物科技 |
| 卫星&航天 |
| 低空经济 |
| 算力 |
| 机器人 |
| 脑机接口 |
| 游戏 |
| 稀土 |
| 养殖 |
| 电池 |
| 智能驾驶 |
| 电网设备 |

---

## 响应示例

### 成功 — 提取到基金经理观点

```json
{
  "code": 0,
  "data": [
    {
      "manager_name": "卡麦",
      "fund_company": "财通基金",
      "original_view": "以中证指数为代表的纯固收资产持仓比例较高、持续体验感相对较好，但长期来看，收益有一定的上限，股票基金长期年化收益具备一定优势，但阶段性波动较大。随着股市持仓比例的逐步收敛，中间地带存在很大的空间，这正是'固收+'策略希望填补的领域。",
      "sectors": [],
      "industries": [],
      "concepts": [],
      "sentiment": "中性"
    },
    {
      "manager_name": "鹏维周",
      "fund_company": "南安基金",
      "original_view": "经济预计将温和修复，外需整体保持平稳，内需的走势较为关键，宏观政策预计将维持积极取向以支持内需修复。从资产性价角度看，股票略优于债市。聚焦成长赛道中的AI软硬件、化工和新能源、非银和周期股，以及创新药、创新器械等结构机会。",
      "sectors": ["科技", "金融", "制造", "医药"],
      "industries": ["电子", "非银金融", "机械设备", "医药生物"],
      "concepts": ["人工智能", "芯片半导体", "新能源", "创新药", "生物科技"],
      "sentiment": "正面"
    }
  ],
  "msg": ""
}
```

### 成功 — 未提取到基金经理观点

```json
{
  "code": 0,
  "data": [],
  "msg": ""
}
```

### 失败

```json
{
  "code": 500,
  "data": [],
  "msg": "失败原因描述"
}
```

---

## 调用示例

### curl

```bash
curl -X POST http://124.223.42.93:8000/api/fund-manager/label \
  -H "Content-Type: application/json" \
  -d '{
    "queryContent": "在信息过载、风格轮动加速的当下，投资似乎变得越来越难。某基金经理张三来自XX基金表示，看好科技板块，尤其是人工智能和芯片半导体方向。"
  }'
```

### Java（OkHttp）

```java
OkHttpClient client = new OkHttpClient();
MediaType JSON = MediaType.get("application/json; charset=utf-8");

String json = "{\"queryContent\": \"文章内容...\"}";

Request request = new Request.Builder()
    .url("http://124.223.42.93:8000/api/fund-manager/label")
    .post(RequestBody.create(json, JSON))
    .build();

try (Response response = client.newCall(request).execute()) {
    System.out.println(response.body().string());
}
```

### Python（requests）

```python
import requests

resp = requests.post(
    "http://124.223.42.93:8000/api/fund-manager/label",
    json={"queryContent": "文章内容..."},
)
print(resp.json())
```
