"""
通用结构化输出智能体 — Streamlit 前端
=====================================
用户可在界面上自由定义输出字段（名称、类型、描述、枚举值等），
输入文档后，智能体按定义的 schema 输出结构化 JSON。
"""

import json
import streamlit as st
from structured_agent import FieldDefinition, StructuredAgent

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
        },
        {
            "name": "confidence",
            "display_name": "置信度",
            "field_type": "float",
            "description": "模型对该标签判断的置信度",
            "min_value": 0.0,
            "max_value": 1.0,
        },
        {
            "name": "reason",
            "display_name": "判定理由",
            "field_type": "string",
            "description": "判定该标签的理由，50字以内",
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

    if new_type in ("enum", "list[enum]"):
        enum_input = st.text_input(
            "枚举值（逗号分隔）",
            placeholder="例如：正面, 中性, 负面",
        )
        if enum_input:
            new_enum_values = [v.strip() for v in enum_input.split(",") if v.strip()]

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
                 "min_value": None, "max_value": None},
                {"name": "sentiment", "display_name": "情感倾向", "field_type": "enum",
                 "description": "文章对所属行业的情感倾向",
                 "enum_values": ["正面", "中性", "负面"],
                 "min_value": None, "max_value": None},
                {"name": "confidence", "display_name": "置信度", "field_type": "float",
                 "description": "模型对判断结果的置信度",
                 "enum_values": None, "min_value": 0.0, "max_value": 1.0},
                {"name": "summary", "display_name": "摘要", "field_type": "string",
                 "description": "用一句话概括文章核心观点，50字以内",
                 "enum_values": None, "min_value": None, "max_value": None},
            ]
            st.rerun()

    with col_t2:
        if st.button("💬 基金经理发言模板"):
            st.session_state.fields = [
                {"name": "is_fund_manager", "display_name": "是否基金经理发言", "field_type": "bool",
                 "description": "判断文章是否为基金经理的观点发言",
                 "enum_values": None, "min_value": None, "max_value": None},
                {"name": "sectors", "display_name": "涉及板块", "field_type": "list[enum]",
                 "description": "文章涉及的板块（可多选）",
                 "enum_values": ["消费", "科技", "金融", "制造", "周期", "基建"],
                 "min_value": None, "max_value": None},
                {"name": "sentiment", "display_name": "情感倾向", "field_type": "enum",
                 "description": "基金经理对所提板块的整体态度",
                 "enum_values": ["正面", "中性", "负面"],
                 "min_value": None, "max_value": None},
                {"name": "key_opinion", "display_name": "核心观点", "field_type": "string",
                 "description": "提取基金经理的核心观点，100字以内",
                 "enum_values": None, "min_value": None, "max_value": None},
            ]
            st.rerun()

    with col_t3:
        if st.button("📊 新闻情感分析模板"):
            st.session_state.fields = [
                {"name": "topic", "display_name": "主题", "field_type": "string",
                 "description": "新闻的核心主题，10字以内",
                 "enum_values": None, "min_value": None, "max_value": None},
                {"name": "sentiment_score", "display_name": "情感分数", "field_type": "float",
                 "description": "情感倾向分数，-1为极度负面，0为中性，1为极度正面",
                 "enum_values": None, "min_value": -1.0, "max_value": 1.0},
                {"name": "urgency", "display_name": "紧急程度", "field_type": "enum",
                 "description": "该新闻的紧急/重要程度",
                 "enum_values": ["高", "中", "低"],
                 "min_value": None, "max_value": None},
                {"name": "entities", "display_name": "相关实体", "field_type": "string",
                 "description": "新闻中提到的关键实体（公司、人物、机构），逗号分隔",
                 "enum_values": None, "min_value": None, "max_value": None},
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
