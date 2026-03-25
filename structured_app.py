"""
通用结构化输出智能体 — Streamlit 前端
=====================================
用户可在界面上自由定义输出字段（名称、类型、描述、枚举值等），
输入文档后，智能体按定义的 schema 输出结构化 JSON。
"""

import json
import streamlit as st
from structured_agent import EnumValueDefinition, FieldDefinition, StructuredAgent

# ──────────────────────────────────────────────
# 页面设置
# ──────────────────────────────────────────────
st.set_page_config(page_title="通用结构化输出", page_icon="🧩", layout="wide")
st.title("🧩 通用结构化输出智能体")
st.caption("自定义输出字段 → 输入文档 → 获得结构化 JSON")

# ──────────────────────────────────────────────
# 初始化 session_state
# ──────────────────────────────────────────────
if "fields" not in st.session_state:
    # 预置一个示例 schema
    st.session_state.fields: list[dict] = [
        {
            "name": "label",
            "display_name": "标签",
            "field_type": "enum",
            "description": "文章最匹配的标签",
            "enum_values": ["宏观经济", "行业研究", "个股分析"],
            "enum_definitions": [
                {"value": "宏观经济", "description": "讨论GDP、货币政策、财政政策、通胀等宏观层面话题",
                 "positive_examples": ["央行宣布降息25个基点"], "negative_examples": ["某公司发布新产品（应归为个股分析）"]},
                {"value": "行业研究", "description": "分析某一行业整体趋势、竞争格局、政策影响",
                 "positive_examples": ["新能源行业2024年展望"], "negative_examples": ["某公司财报解读（应归为个股分析）"]},
                {"value": "个股分析", "description": "针对单一公司的基本面、估值、业绩分析",
                 "positive_examples": ["某公司Q3营收同比增长30%"], "negative_examples": ["半导体行业整体景气度回升（应归为行业研究）"]},
            ],
            "min_value": None,
            "max_value": None,
        },
        {
            "name": "confidence",
            "display_name": "置信度",
            "field_type": "float",
            "description": "模型对该标签判断的置信度",
            "enum_values": None,
            "enum_definitions": None,
            "min_value": 0.0,
            "max_value": 1.0,
        },
        {
            "name": "reason",
            "display_name": "判定理由",
            "field_type": "string",
            "description": "判定该标签的理由，50字以内",
            "enum_values": None,
            "enum_definitions": None,
            "min_value": None,
            "max_value": None,
        },
    ]

if "result" not in st.session_state:
    st.session_state.result = None

# ──────────────────────────────────────────────
# 侧边栏：模型配置
# ──────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 模型配置")
    api_key = st.text_input("API Key", value="请输入您的deepseek API", type="password")
    model_name = st.text_input("模型名称", value="deepseek-chat")
    base_url = st.text_input("Base URL", value="https://api.deepseek.com")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.0, 0.05)

    st.divider()
    st.header("📊 当前 Schema 预览")
    if st.session_state.fields:
        preview = {}
        for f in st.session_state.fields:
            ft = f["field_type"]
            if ft == "string":
                preview[f["name"]] = "string"
            elif ft == "enum":
                preview[f["name"]] = f.get("enum_values", [])
            elif ft == "list[enum]":
                preview[f["name"]] = [f"list: {f.get('enum_values', [])}"]
            elif ft == "float":
                preview[f["name"]] = "float"
            elif ft == "int":
                preview[f["name"]] = "int"
            elif ft == "bool":
                preview[f["name"]] = "bool"
        st.json(preview)
    else:
        st.info("暂无字段，请在主区域添加。")

# ──────────────────────────────────────────────
# 主区域
# ──────────────────────────────────────────────
tab_schema, tab_extract = st.tabs(["📐 字段定义", "📄 文档提取"])

FIELD_TYPES = ["string", "enum", "float", "int", "bool", "list[enum]"]

# ────── Tab 1: 字段定义 ──────
with tab_schema:
    st.subheader("已定义的字段")

    if not st.session_state.fields:
        st.info("暂无字段，请在下方添加。")

    fields_to_delete = []
    for idx, f in enumerate(st.session_state.fields):
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 2, 1.5, 0.5])
            with col1:
                st.markdown(f"**`{f['name']}`**")
                st.caption(f["display_name"])
            with col2:
                st.caption(f"📝 {f['description']}")
            with col3:
                type_label = f["field_type"]
                if f["field_type"] in ("enum", "list[enum]") and f.get("enum_values"):
                    type_label += f": {', '.join(f['enum_values'])}"
                elif f["field_type"] in ("float", "int"):
                    bounds = []
                    if f.get("min_value") is not None:
                        bounds.append(f"≥{f['min_value']}")
                    if f.get("max_value") is not None:
                        bounds.append(f"≤{f['max_value']}")
                    if bounds:
                        type_label += f" ({', '.join(bounds)})"
                st.caption(f"类型：{type_label}")
            with col4:
                if st.button("🗑️", key=f"del_field_{idx}"):
                    fields_to_delete.append(idx)

            # 展示枚举值定义（描述 + 正反例）
            if f["field_type"] in ("enum", "list[enum]") and f.get("enum_definitions"):
                with st.expander(f"查看「{f['display_name']}」各枚举值的判定标准", expanded=False):
                    for ed in f["enum_definitions"]:
                        st.markdown(f"**{ed['value']}**")
                        if ed.get("description"):
                            st.markdown(f"  定义：{ed['description']}")
                        if ed.get("positive_examples"):
                            st.markdown(f"  正例：{'；'.join(ed['positive_examples'])}")
                        if ed.get("negative_examples"):
                            st.markdown(f"  反例：{'；'.join(ed['negative_examples'])}")

    for idx in sorted(fields_to_delete, reverse=True):
        st.session_state.fields.pop(idx)
        st.rerun()

    st.divider()
    st.subheader("添加新字段")

    col_a, col_b, col_c = st.columns([1.5, 1.5, 1])
    with col_a:
        new_name = st.text_input("字段名（英文，JSON key）", placeholder="例如：industry")
    with col_b:
        new_display = st.text_input("显示名（中文）", placeholder="例如：行业分类")
    with col_c:
        new_type = st.selectbox("字段类型", FIELD_TYPES)

    new_desc = st.text_input("字段描述（指导模型理解该字段含义）", placeholder="例如：文章所属的行业分类")

    # 根据类型显示额外配置
    new_enum_values = None
    new_min = None
    new_max = None

    new_enum_definitions = None

    if new_type in ("enum", "list[enum]"):
        enum_input = st.text_input(
            "枚举值（逗号分隔）",
            placeholder="例如：正面, 中性, 负面",
        )
        if enum_input:
            new_enum_values = [v.strip() for v in enum_input.split(",") if v.strip()]

        # 为每个枚举值添加详细定义
        if new_enum_values:
            st.markdown("**为每个枚举值添加判定标准（可选，提升标注准确率）：**")
            new_enum_definitions = []
            for ev_idx, ev in enumerate(new_enum_values):
                with st.expander(f"定义「{ev}」", expanded=False):
                    ev_desc = st.text_input(
                        "定义描述",
                        key=f"ev_desc_{ev_idx}",
                        placeholder=f"什么样的内容应归为「{ev}」",
                    )
                    ev_pos = st.text_input(
                        "正例（分号分隔，可选）",
                        key=f"ev_pos_{ev_idx}",
                        placeholder="典型的属于该标签的文本片段",
                    )
                    ev_neg = st.text_input(
                        "反例（分号分隔，可选）",
                        key=f"ev_neg_{ev_idx}",
                        placeholder="容易误判为该标签但实际不属于的文本片段",
                    )
                    pos_list = [x.strip() for x in ev_pos.split("；") if x.strip()] if ev_pos else []
                    neg_list = [x.strip() for x in ev_neg.split("；") if x.strip()] if ev_neg else []
                    if ev_desc or pos_list or neg_list:
                        new_enum_definitions.append({
                            "value": ev,
                            "description": ev_desc,
                            "positive_examples": pos_list,
                            "negative_examples": neg_list,
                        })
            if not new_enum_definitions:
                new_enum_definitions = None

    if new_type in ("float", "int"):
        col_min, col_max = st.columns(2)
        with col_min:
            min_input = st.text_input("最小值（可选）", placeholder="例如：0")
            new_min = float(min_input) if min_input else None
        with col_max:
            max_input = st.text_input("最大值（可选）", placeholder="例如：1")
            new_max = float(max_input) if max_input else None

    if st.button("➕ 添加字段", type="primary"):
        if not new_name or not new_desc:
            st.error("请填写字段名和描述。")
        elif new_type in ("enum", "list[enum]") and not new_enum_values:
            st.error("枚举类型必须提供至少一个可选值。")
        elif any(f["name"] == new_name for f in st.session_state.fields):
            st.error(f"字段名 `{new_name}` 已存在。")
        else:
            new_field = {
                "name": new_name,
                "display_name": new_display or new_name,
                "field_type": new_type,
                "description": new_desc,
                "enum_values": new_enum_values,
                "enum_definitions": new_enum_definitions,
                "min_value": new_min,
                "max_value": new_max,
            }
            st.session_state.fields.append(new_field)
            st.success(f"字段 `{new_name}` 已添加！")
            st.rerun()

    # 快速模板
    st.divider()
    st.subheader("快速模板")
    col_t1, col_t2, col_t3 = st.columns(3)

    with col_t1:
        if st.button("📌 研报打标模板"):
            st.session_state.fields = [
                {"name": "industry", "display_name": "行业", "field_type": "enum",
                 "description": "文章所属的行业分类",
                 "enum_values": ["银行", "非银金融", "医药生物", "电子", "计算机", "食品饮料", "电力设备", "国防军工"],
                 "enum_definitions": [
                     {"value": "计算机", "description": "涉及软件开发、IT服务、云计算、信息安全、人工智能等计算机软硬件领域",
                      "positive_examples": ["某国产数据库厂商获得大额政府订单", "AI大模型在金融风控中的应用"],
                      "negative_examples": ["消费电子芯片出货量下滑（应归为电子）", "互联网平台广告收入增长（应归为传媒）"]},
                     {"value": "电子", "description": "涉及半导体、消费电子、元器件、光学光电子等电子硬件领域",
                      "positive_examples": ["某芯片公司量产28nm制程", "面板价格持续上涨"],
                      "negative_examples": ["软件SaaS公司营收增长（应归为计算机）"]},
                     {"value": "银行", "description": "涉及商业银行、政策性银行的信贷、存款、利率等业务",
                      "positive_examples": ["央行降准释放流动性利好银行板块", "某银行不良贷款率下降"],
                      "negative_examples": ["券商经纪业务收入增长（应归为非银金融）"]},
                 ],
                 "min_value": None, "max_value": None},
                {"name": "sentiment", "display_name": "情感倾向", "field_type": "enum",
                 "description": "文章对所属行业的情感倾向",
                 "enum_values": ["正面", "中性", "负面"],
                 "enum_definitions": [
                     {"value": "正面", "description": "文章整体看好该行业前景或报道利好消息",
                      "positive_examples": ["预计行业增速将超预期", "龙头公司业绩大幅增长"],
                      "negative_examples": ["客观陈述行业数据但无明确看法（应归为中性）"]},
                     {"value": "负面", "description": "文章对该行业前景悲观或报道利空消息",
                      "positive_examples": ["行业面临政策收紧风险", "多家公司业绩不及预期"],
                      "negative_examples": ["提到短期调整但长期看好（应归为正面）"]},
                 ],
                 "min_value": None, "max_value": None},
                {"name": "confidence", "display_name": "置信度", "field_type": "float",
                 "description": "模型对判断结果的置信度",
                 "enum_values": None, "enum_definitions": None, "min_value": 0.0, "max_value": 1.0},
                {"name": "summary", "display_name": "摘要", "field_type": "string",
                 "description": "用一句话概括文章核心观点，50字以内",
                 "enum_values": None, "enum_definitions": None, "min_value": None, "max_value": None},
            ]
            st.rerun()

    with col_t2:
        if st.button("💬 基金经理发言模板"):
            st.session_state.fields = [
                {"name": "is_fund_manager", "display_name": "是否基金经理发言", "field_type": "bool",
                 "description": "判断文章是否为基金经理的观点发言",
                 "enum_values": None, "enum_definitions": None, "min_value": None, "max_value": None},
                {"name": "sectors", "display_name": "涉及板块", "field_type": "list[enum]",
                 "description": "文章涉及的板块（可多选）",
                 "enum_values": ["消费", "科技", "金融", "制造", "周期", "基建"],
                 "enum_definitions": None, "min_value": None, "max_value": None},
                {"name": "sentiment", "display_name": "情感倾向", "field_type": "enum",
                 "description": "基金经理对所提板块的整体态度",
                 "enum_values": ["正面", "中性", "负面"],
                 "enum_definitions": None, "min_value": None, "max_value": None},
                {"name": "key_opinion", "display_name": "核心观点", "field_type": "string",
                 "description": "提取基金经理的核心观点，100字以内",
                 "enum_values": None, "enum_definitions": None, "min_value": None, "max_value": None},
            ]
            st.rerun()

    with col_t3:
        if st.button("📊 新闻情感分析模板"):
            st.session_state.fields = [
                {"name": "topic", "display_name": "主题", "field_type": "string",
                 "description": "新闻的核心主题，10字以内",
                 "enum_values": None, "enum_definitions": None, "min_value": None, "max_value": None},
                {"name": "sentiment_score", "display_name": "情感分数", "field_type": "float",
                 "description": "情感倾向分数，-1为极度负面，0为中性，1为极度正面",
                 "enum_values": None, "enum_definitions": None, "min_value": -1.0, "max_value": 1.0},
                {"name": "urgency", "display_name": "紧急程度", "field_type": "enum",
                 "description": "该新闻的紧急/重要程度",
                 "enum_values": ["高", "中", "低"],
                 "enum_definitions": None, "min_value": None, "max_value": None},
                {"name": "entities", "display_name": "相关实体", "field_type": "string",
                 "description": "新闻中提到的关键实体（公司、人物、机构），逗号分隔",
                 "enum_values": None, "enum_definitions": None, "min_value": None, "max_value": None},
            ]
            st.rerun()

# ────── Tab 2: 文档提取 ──────
with tab_extract:
    if not st.session_state.fields:
        st.warning("请先在「字段定义」中添加至少一个字段。")
    else:
        with st.expander("当前 Schema", expanded=False):
            for f in st.session_state.fields:
                type_info = f["field_type"]
                if f["field_type"] in ("enum", "list[enum]") and f.get("enum_values"):
                    type_info += f" → {f['enum_values']}"
                st.markdown(f"- **`{f['name']}`**（{f['display_name']}）：{f['description']}　[{type_info}]")

        st.subheader("输入文档")
        content = st.text_area(
            "请输入待提取的文档内容",
            height=250,
            placeholder="在此粘贴或输入文档内容...",
        )

        if st.button("🚀 开始提取", type="primary", disabled=not content):
            with st.spinner("正在调用模型进行结构化提取..."):
                try:
                    field_defs = [
                        FieldDefinition(**f) for f in st.session_state.fields
                    ]
                    agent = StructuredAgent(
                        fields=field_defs,
                        model_name=model_name,
                        base_url=base_url,
                        api_key=api_key,
                        temperature=temperature,
                    )
                    result = agent.run(content)
                    st.session_state.result = result
                except Exception as e:
                    st.error(f"提取失败：{e}")
                    st.session_state.result = None

        if st.session_state.result:
            st.divider()
            st.subheader("结构化输出结果")

            # 卡片式展示每个字段
            result = st.session_state.result
            field_map = {f["name"]: f for f in st.session_state.fields}

            for key, value in result.items():
                f_info = field_map.get(key, {})
                display = f_info.get("display_name", key)
                ftype = f_info.get("field_type", "string")

                with st.container(border=True):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.markdown(f"**{display}**")
                        st.caption(f"`{key}` · {ftype}")
                    with col2:
                        if ftype == "float" and isinstance(value, (int, float)):
                            min_v = f_info.get("min_value", 0) or 0
                            max_v = f_info.get("max_value", 1) or 1
                            if max_v > min_v:
                                normalized = (value - min_v) / (max_v - min_v)
                                normalized = max(0.0, min(1.0, normalized))
                                st.progress(normalized, text=f"{value}")
                            else:
                                st.markdown(f"`{value}`")
                        elif ftype == "bool":
                            st.markdown(f"{'✅ 是' if value else '❌ 否'}")
                        elif ftype == "list[enum]" and isinstance(value, list):
                            for v in value:
                                st.markdown(f"  `{v}`", unsafe_allow_html=True)
                        else:
                            st.markdown(f"{value}")

            # JSON 原始输出
            with st.expander("查看原始 JSON", expanded=False):
                st.json(result)
