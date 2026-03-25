"""
通用结构化输出智能体 (Generic Structured Output Agent)
=====================================================
用户可自定义输出 JSON 的字段（字段名、类型、描述、枚举值），
智能体根据输入文档，按用户定义的 schema 输出结构化 JSON。

支持的字段类型：
- string：自由文本
- enum：枚举值（用户提供可选值列表）
- float：浮点数（可选 min/max）
- int：整数（可选 min/max）
- bool：布尔值
- list[enum]：枚举值列表（多选）
"""

from typing import Literal

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, create_model


# ──────────────────────────────────────────────
# 1. 字段定义结构
# ──────────────────────────────────────────────

class FieldDefinition(BaseModel):
    """用户定义的单个输出字段"""
    name: str = Field(description="字段名称（英文，作为 JSON key）")
    display_name: str = Field(description="字段显示名称（中文）")
    field_type: Literal["string", "enum", "float", "int", "bool", "list[enum]"] = Field(
        description="字段类型"
    )
    description: str = Field(description="字段含义描述，指导模型理解该字段应填什么")
    enum_values: list[str] | None = Field(
        default=None,
        description="当 field_type 为 enum 或 list[enum] 时，可选的枚举值列表",
    )
    min_value: float | None = Field(default=None, description="数值类型的最小值")
    max_value: float | None = Field(default=None, description="数值类型的最大值")


# ──────────────────────────────────────────────
# 2. 动态 Pydantic 模型构建
# ──────────────────────────────────────────────

def build_dynamic_model(fields: list[FieldDefinition]):
    """根据用户定义的字段列表，动态创建 Pydantic 输出模型。"""
    field_kwargs = {}

    for f in fields:
        if f.field_type == "string":
            field_kwargs[f.name] = (str, Field(description=f.description))

        elif f.field_type == "enum":
            if not f.enum_values:
                raise ValueError(f"字段 '{f.name}' 类型为 enum，但未提供枚举值列表")
            enum_literal = Literal[tuple(f.enum_values)]  # type: ignore[valid-type]
            field_kwargs[f.name] = (enum_literal, Field(description=f.description))

        elif f.field_type == "list[enum]":
            if not f.enum_values:
                raise ValueError(f"字段 '{f.name}' 类型为 list[enum]，但未提供枚举值列表")
            enum_literal = Literal[tuple(f.enum_values)]  # type: ignore[valid-type]
            field_kwargs[f.name] = (list[enum_literal], Field(description=f.description))

        elif f.field_type == "float":
            constraints = {}
            if f.min_value is not None:
                constraints["ge"] = f.min_value
            if f.max_value is not None:
                constraints["le"] = f.max_value
            field_kwargs[f.name] = (
                float,
                Field(description=f.description, **constraints),
            )

        elif f.field_type == "int":
            constraints = {}
            if f.min_value is not None:
                constraints["ge"] = int(f.min_value)
            if f.max_value is not None:
                constraints["le"] = int(f.max_value)
            field_kwargs[f.name] = (
                int,
                Field(description=f.description, **constraints),
            )

        elif f.field_type == "bool":
            field_kwargs[f.name] = (bool, Field(description=f.description))

        else:
            raise ValueError(f"不支持的字段类型: {f.field_type}")

    DynamicOutput = create_model("StructuredOutput", **field_kwargs)
    return DynamicOutput


# ──────────────────────────────────────────────
# 3. Prompt 构建
# ──────────────────────────────────────────────

def build_field_desc_block(fields: list[FieldDefinition]) -> str:
    """将字段定义渲染为 Prompt 中的描述块。"""
    lines = []
    for f in fields:
        type_info = f.field_type
        if f.field_type in ("enum", "list[enum]") and f.enum_values:
            type_info += f"，可选值：{f.enum_values}"
        if f.field_type in ("float", "int"):
            bounds = []
            if f.min_value is not None:
                bounds.append(f"最小值 {f.min_value}")
            if f.max_value is not None:
                bounds.append(f"最大值 {f.max_value}")
            if bounds:
                type_info += f"，{'，'.join(bounds)}"
        lines.append(
            f"  - **{f.name}**（{f.display_name}）：{f.description}  \n"
            f"    类型：{type_info}"
        )
    return "\n".join(lines)


def build_json_example(fields: list[FieldDefinition]) -> str:
    """生成 JSON 输出示例。"""
    example = {}
    for f in fields:
        if f.field_type == "string":
            example[f.name] = "..."
        elif f.field_type == "enum":
            example[f.name] = f.enum_values[0] if f.enum_values else "..."
        elif f.field_type == "list[enum]":
            example[f.name] = f.enum_values[:2] if f.enum_values else ["..."]
        elif f.field_type == "float":
            example[f.name] = 0.0
        elif f.field_type == "int":
            example[f.name] = 0
        elif f.field_type == "bool":
            example[f.name] = True
    import json
    return json.dumps(example, ensure_ascii=False, indent=2)


SYSTEM_TEMPLATE = """\
你是一个专业的文本结构化提取智能体。请严格按照 json 格式输出结果。

## 需要提取的字段

{field_descriptions}

## 任务要求

请根据输入的文档内容，提取并填充上述所有字段。

## 注意事项
- 每个字段必须严格按照指定的类型输出
- 枚举类型字段只能使用给定的可选值，不得自行创造
- list[enum] 类型字段输出一个数组，元素只能来自给定的可选值
- 如果文档中没有明确信息来填充某个字段，请根据文档内容做出最合理的推断
- 浮点数和整数字段需遵守给定的取值范围

## 输出格式

请严格按以下 json 格式输出，不要输出任何其他内容：

EXAMPLE JSON OUTPUT:
{json_example}
"""

USER_TEMPLATE = "请对以下文档进行结构化提取：\n\n{content}"


# ──────────────────────────────────────────────
# 4. StructuredAgent 核心类
# ──────────────────────────────────────────────

class StructuredAgent:
    """
    通用结构化输出智能体。
    根据用户定义的字段 schema，从文档中提取结构化信息。
    """

    def __init__(
        self,
        fields: list[FieldDefinition],
        model_name: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        api_key: str = "sk-xxx",
        temperature: float = 0.0,
    ):
        self.fields = fields

        self.llm = ChatOpenAI(
            model=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            model_kwargs={"response_format": {"type": "json_object"}},
        )

        # 动态构建 Pydantic 模型
        self.output_model = build_dynamic_model(fields)
        self.parser = PydanticOutputParser(pydantic_object=self.output_model)

        # 构建 Prompt
        field_desc = build_field_desc_block(fields)
        json_example = build_json_example(fields)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_TEMPLATE),
            ("human", USER_TEMPLATE),
        ]).partial(
            field_descriptions=field_desc,
            json_example=json_example,
        )

        self.chain = self.prompt | self.llm | self.parser

    def run(self, content: str) -> dict:
        """对一篇文档进行结构化提取，返回字典。"""
        output = self.chain.invoke({"content": content})
        return output.model_dump()

    def run_batch(self, contents: list[str]) -> list[dict]:
        """批量提取。"""
        inputs = [{"content": c} for c in contents]
        outputs = self.chain.batch(inputs)
        return [o.model_dump() for o in outputs]


# ──────────────────────────────────────────────
# 5. 运行示例
# ──────────────────────────────────────────────

if __name__ == "__main__":
    # 示例：定义一个"研报打标"的 schema
    fields = [
        FieldDefinition(
            name="industry",
            display_name="行业",
            field_type="enum",
            description="文章所属的申万一级行业",
            enum_values=["银行", "非银金融", "医药生物", "电子", "计算机", "食品饮料"],
        ),
        FieldDefinition(
            name="sentiment",
            display_name="正负面",
            field_type="enum",
            description="文章对该行业的情感倾向",
            enum_values=["正面", "中性", "负面"],
        ),
        FieldDefinition(
            name="confidence",
            display_name="置信度",
            field_type="float",
            description="模型对以上判断的置信度",
            min_value=0.0,
            max_value=1.0,
        ),
        FieldDefinition(
            name="summary",
            display_name="摘要",
            field_type="string",
            description="用一句话概括文章核心观点，50字以内",
        ),
        FieldDefinition(
            name="is_fund_manager_speech",
            display_name="是否基金经理发言",
            field_type="bool",
            description="判断文章是否为基金经理的观点发言",
        ),
    ]

    agent = StructuredAgent(
        fields=fields,
        model_name="deepseek-chat",
        base_url="https://api.deepseek.com",
        api_key="sk-",
    )

    test_article = """
    央行今日宣布下调存款准备金率 0.5 个百分点，释放长期资金约 1 万亿元。
    某知名基金经理表示，降准对银行板块形成利好，预计将带动银行股估值修复。
    他认为当前银行股 PB 普遍在 0.5-0.7 倍，具有较高的安全边际。
    """

    try:
        result = agent.run(test_article)
        print("=" * 50)
        print("结构化输出结果：")
        print("=" * 50)
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"运行失败: {e}")
