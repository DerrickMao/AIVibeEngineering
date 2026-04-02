"""
基金经理观点数据打标接口
=======================
接收一段包含基金经理观点的文章，提取每位基金经理的观点并进行结构化打标。
输出包括：基金经理姓名、基金公司、原始观点、板块、行业、概念、情感倾向。
"""

import json
import logging
import os
from typing import Literal

import uvicorn
from fastapi import FastAPI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# ──────────────────────────────────────────────
# 配置（优先读环境变量，否则用默认值）
# ──────────────────────────────────────────────

LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-xxx")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 枚举值定义
# ──────────────────────────────────────────────

SENTIMENT_VALUES = ["正面", "中性", "负面"]

SECTOR_VALUES = ["消费", "科技", "金融", "制造", "周期", "基建"]

INDUSTRY_VALUES = [
    "农林牧渔", "基础化工", "钢铁", "有色金属", "电子", "家用电器",
    "食品饮料", "纺织服饰", "轻工制造", "医药生物", "公用事业", "交通运输",
    "房地产", "商贸零售", "社会服务", "综合", "建筑材料", "建筑装饰",
    "电力设备", "国防军工", "计算机", "传媒", "通信", "银行",
    "非银金融", "汽车", "机械设备", "煤炭", "石油石化", "环保", "美容护理",
]

CONCEPT_VALUES = [
    "新能源", "芯片半导体", "互联网", "光伏", "创新药", "云计算",
    "风电", "保险", "碳中和", "消费电子", "人工智能", "黄金",
    "生物科技", "卫星&航天", "低空经济", "算力", "机器人", "脑机接口",
    "游戏", "稀土", "养殖", "电池", "智能驾驶", "电网设备",
]

SentimentType = Literal["正面", "中性", "负面"]

SectorType = Literal[
    "消费", "科技", "金融", "制造", "周期", "基建",
]

IndustryType = Literal[
    "农林牧渔", "基础化工", "钢铁", "有色金属", "电子", "家用电器",
    "食品饮料", "纺织服饰", "轻工制造", "医药生物", "公用事业", "交通运输",
    "房地产", "商贸零售", "社会服务", "综合", "建筑材料", "建筑装饰",
    "电力设备", "国防军工", "计算机", "传媒", "通信", "银行",
    "非银金融", "汽车", "机械设备", "煤炭", "石油石化", "环保", "美容护理",
]

ConceptType = Literal[
    "新能源", "芯片半导体", "互联网", "光伏", "创新药", "云计算",
    "风电", "保险", "碳中和", "消费电子", "人工智能", "黄金",
    "生物科技", "卫星&航天", "低空经济", "算力", "机器人", "脑机接口",
    "游戏", "稀土", "养殖", "电池", "智能驾驶", "电网设备",
]


# ──────────────────────────────────────────────
# Pydantic 模型：LLM 输出结构
# ──────────────────────────────────────────────

class FundManagerView(BaseModel):
    """单个基金经理的观点打标结果（宽松类型，避免 LLM 输出非标值时解析失败）"""
    manager_name: str = Field(description="基金经理姓名")
    fund_company: str = Field(description="基金公司名称")
    original_view: str = Field(description="该基金经理的原始观点文本，从原文中提取")
    sectors: list[str] = Field(description="涉及的板块，从可选值中选取，可多选，无则为空数组")
    industries: list[str] = Field(description="涉及的申万一级行业，从可选值中选取，可多选，无则为空数组")
    concepts: list[str] = Field(description="涉及的概念/主题，从可选值中选取，可多选，无则为空数组")
    sentiment: str = Field(description="该基金经理观点的情感倾向：正面、中性、负面")


class FundManagerViewList(BaseModel):
    """基金经理观点列表（LLM 输出的顶层结构）"""
    views: list[FundManagerView] = Field(description="从文章中提取的所有基金经理观点列表，如果文章中没有基金经理观点则为空数组")


# ──────────────────────────────────────────────
# Pydantic 模型：API 请求 & 响应
# ──────────────────────────────────────────────

class ApiRequest(BaseModel):
    queryContent: str = Field(description="待分析的文章内容")


class FundManagerViewResponse(BaseModel):
    """单条记录（对外接口格式，与 FundManagerView 字段一致）"""
    manager_name: str
    fund_company: str
    original_view: str
    sectors: list[str]
    industries: list[str]
    concepts: list[str]
    sentiment: str


class ApiResponse(BaseModel):
    code: int = Field(description="状态码，0 表示成功，500 表示失败")
    data: list[FundManagerViewResponse] = Field(description="打标结果数组")
    msg: str = Field(description="错误信息，成功时为空字符串")


# ──────────────────────────────────────────────
# Prompt
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """\
你是一个专业的金融文本分析智能体。你的任务是从文章中识别并提取每位基金经理的观点，并对其进行结构化打标。

## 提取规则

1. **识别基金经理**：找出文章中提到的每一位基金经理（或基金管理人），提取其姓名和所属基金公司。
2. **提取原始观点**：将该基金经理在文章中表达的所有观点**合并为一段文本**作为 original_view。即使同一位基金经理的观点散布在文章的多个段落中，也必须汇总到一条记录中输出。
3. **板块打标**：根据该基金经理的**全部观点**综合判断，从以下板块中选取涉及的板块（可多选，无则为空数组）：
   {sectors}
4. **行业打标**：根据该基金经理的**全部观点**综合判断，从以下申万一级行业中选取涉及的行业（可多选，无则为空数组）：
   {industries}
5. **概念打标**：根据该基金经理的**全部观点**综合判断，从以下概念/主题中选取涉及的概念（可多选，无则为空数组）：
   {concepts}
6. **情感判断**：根据该基金经理的**整体观点**判断其情感倾向，只能从以下值中选择一个：
   {sentiments}

## 关键原则：同一基金经理只输出一条记录
- **绝对不要**将同一位基金经理拆分为多条记录
- 同一位基金经理在文章中的所有发言、观点、分析，无论出现在多少个段落中，都必须合并到同一条记录
- original_view 应将该基金经理的核心观点概括为一段连贯的文本（保留关键原文表述，但不需要逐段复制）
- sectors、industries、concepts 应反映该基金经理全部观点中涉及的所有标签（取并集）

## 其他注意事项
- 如果文章中没有任何基金经理的观点，则 views 为空数组
- 板块、行业、概念必须且只能从给定的可选值中选取，不得自行创造
- 请严格按照 JSON 格式输出，不要输出任何其他内容

## 输出格式

请严格按以下 JSON 格式输出：

{{
  "views": [
    {{
      "manager_name": "基金经理姓名",
      "fund_company": "基金公司名称",
      "original_view": "原始观点文本",
      "sectors": ["板块1", "板块2"],
      "industries": ["行业1", "行业2"],
      "concepts": ["概念1", "概念2"],
      "sentiment": "正面"
    }}
  ]
}}
"""

USER_PROMPT = "请对以下文章进行基金经理观点提取与打标：\n\n{content}"


# ──────────────────────────────────────────────
# LLM Chain 构建
# ──────────────────────────────────────────────

def build_chain():
    """构建 LangChain 链"""
    llm = ChatOpenAI(
        model=LLM_MODEL,
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        temperature=LLM_TEMPERATURE,
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    parser = PydanticOutputParser(pydantic_object=FundManagerViewList)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ]).partial(
        sectors=json.dumps(SECTOR_VALUES, ensure_ascii=False),
        industries=json.dumps(INDUSTRY_VALUES, ensure_ascii=False),
        concepts=json.dumps(CONCEPT_VALUES, ensure_ascii=False),
        sentiments=json.dumps(SENTIMENT_VALUES, ensure_ascii=False),
    )

    return prompt | llm | parser


chain = build_chain()

# ──────────────────────────────────────────────
# FastAPI 应用
# ──────────────────────────────────────────────

app = FastAPI(
    title="基金经理观点数据打标接口",
    description="接收文章内容，提取基金经理观点并进行结构化打标（板块、行业、概念、情感）",
    version="1.0.0",
)


@app.post("/api/fund-manager/label", response_model=ApiResponse)
async def label_fund_manager_views(req: ApiRequest):
    """
    基金经理观点打标接口

    - 输入一段包含基金经理观点的文章
    - 输出每位基金经理的结构化打标结果
    """
    if not req.queryContent or not req.queryContent.strip():
        return ApiResponse(code=500, data=[], msg="queryContent 不能为空")

    try:
        result: FundManagerViewList = chain.invoke({"content": req.queryContent})
        data = []
        for view in result.views:
            d = view.model_dump()
            # 过滤不在枚举列表中的值，保留合法值
            d["sectors"] = [v for v in d["sectors"] if v in SECTOR_VALUES]
            d["industries"] = [v for v in d["industries"] if v in INDUSTRY_VALUES]
            d["concepts"] = [v for v in d["concepts"] if v in CONCEPT_VALUES]
            if d["sentiment"] not in SENTIMENT_VALUES:
                d["sentiment"] = "中性"  # 兜底
            data.append(FundManagerViewResponse(**d))
        return ApiResponse(code=0, data=data, msg="")

    except Exception as e:
        logger.exception("打标失败")
        return ApiResponse(code=500, data=[], msg=str(e))


# ──────────────────────────────────────────────
# 启动入口
# ──────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("fund_manager_api:app", host="0.0.0.0", port=8000, reload=True)
