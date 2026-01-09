"""
Business Card Recognition App
使用 Google Gemini API 识别名片并导出为多种格式
"""
import streamlit as st
from PIL import Image
import os
from datetime import datetime

from card_recognizer import CardRecognizer, BusinessCardInfo, test_api_connection
from export_utils import (
    export_to_csv,
    export_to_excel,
    export_to_json,
    export_to_vcard,
    cards_to_dataframe
)

# Page configuration
st.set_page_config(
    page_title="名片识别 | Business Card Scanner",
    page_icon="📇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .card-container {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #f9f9f9;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    .info-label {
        font-weight: bold;
        color: #555;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables"""
    if "cards" not in st.session_state:
        st.session_state.cards = []
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    if "api_validated" not in st.session_state:
        st.session_state.api_validated = False


def render_sidebar():
    """Render the sidebar with settings"""
    with st.sidebar:
        st.header("⚙️ 设置 / Settings")

        # API Key input
        st.subheader("🔑 API 密钥")
        api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.api_key,
            type="password",
            help="从 https://makersuite.google.com/app/apikey 获取"
        )

        if api_key != st.session_state.api_key:
            st.session_state.api_key = api_key
            st.session_state.api_validated = False

        # Validate API button
        if st.button("验证 API / Validate API", use_container_width=True):
            if api_key:
                with st.spinner("正在验证..."):
                    success, message = test_api_connection(api_key)
                    if success:
                        st.session_state.api_validated = True
                        st.success("✅ API 连接成功!")
                    else:
                        st.session_state.api_validated = False
                        st.error(f"❌ {message}")
            else:
                st.warning("请输入 API Key")

        # API status
        if st.session_state.api_validated:
            st.success("🟢 API 已连接")
        else:
            st.info("🔴 API 未验证")

        st.divider()

        # Statistics
        st.subheader("📊 统计 / Statistics")
        st.metric("已识别名片", len(st.session_state.cards))

        # Clear all button
        if st.session_state.cards:
            if st.button("🗑️ 清空所有名片", use_container_width=True):
                st.session_state.cards = []
                st.rerun()

        st.divider()

        # About section
        st.subheader("ℹ️ 关于 / About")
        st.markdown("""
        **名片识别助手**

        使用 Google Gemini AI 自动识别名片信息。

        功能特点:
        - 📷 支持多种图片格式
        - 🌍 支持中英文名片
        - 📊 批量处理
        - 📁 多格式导出
        """)


def render_upload_section():
    """Render the image upload section"""
    st.header("📷 上传名片 / Upload Business Cards")

    uploaded_files = st.file_uploader(
        "选择名片图片（支持多选）",
        type=["jpg", "jpeg", "png", "webp", "gif", "bmp"],
        accept_multiple_files=True,
        help="支持 JPG, PNG, WebP, GIF, BMP 格式"
    )

    if uploaded_files:
        # Check API key
        if not st.session_state.api_key:
            st.warning("⚠️ 请先在侧边栏设置 API Key")
            return

        # Display uploaded images
        st.subheader(f"已上传 {len(uploaded_files)} 张图片")

        # Create columns for preview
        cols = st.columns(min(len(uploaded_files), 4))
        for idx, file in enumerate(uploaded_files):
            with cols[idx % 4]:
                image = Image.open(file)
                st.image(image, caption=file.name, use_container_width=True)

        # Recognize button
        if st.button("🔍 开始识别 / Start Recognition", type="primary", use_container_width=True):
            recognize_cards(uploaded_files)


def recognize_cards(uploaded_files):
    """Process and recognize uploaded business cards"""
    recognizer = CardRecognizer(st.session_state.api_key)

    progress_bar = st.progress(0)
    status_text = st.empty()

    new_cards = []

    for idx, file in enumerate(uploaded_files):
        status_text.text(f"正在识别: {file.name} ({idx + 1}/{len(uploaded_files)})")
        progress_bar.progress((idx + 1) / len(uploaded_files))

        try:
            image = Image.open(file)
            card_info, raw_response = recognizer.recognize(image)

            if not card_info.is_empty():
                new_cards.append(card_info)
                st.success(f"✅ {file.name} 识别成功!")
            else:
                st.warning(f"⚠️ {file.name} 未能识别到信息")

        except Exception as e:
            st.error(f"❌ {file.name} 识别失败: {str(e)}")

    progress_bar.empty()
    status_text.empty()

    # Add new cards to session state
    st.session_state.cards.extend(new_cards)

    if new_cards:
        st.success(f"🎉 成功识别 {len(new_cards)} 张名片!")
        st.rerun()


def render_results_section():
    """Render the recognition results section"""
    if not st.session_state.cards:
        st.info("📭 暂无识别结果，请上传名片开始识别")
        return

    st.header(f"📋 识别结果 / Results ({len(st.session_state.cards)} 张)")

    # Display as table
    df = cards_to_dataframe(st.session_state.cards)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Expandable details for each card
    st.subheader("📇 详细信息")
    for idx, card in enumerate(st.session_state.cards):
        with st.expander(f"名片 {idx + 1}: {card.name or '未知姓名'} - {card.company or '未知公司'}"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**👤 姓名:** {card.name or '-'}")
                st.markdown(f"**🏢 公司:** {card.company or '-'}")
                st.markdown(f"**💼 职位:** {card.title or '-'}")
                st.markdown(f"**📧 邮箱:** {card.email or '-'}")
                st.markdown(f"**📞 电话:** {card.phone or '-'}")
                st.markdown(f"**📱 手机:** {card.mobile or '-'}")

            with col2:
                st.markdown(f"**📠 传真:** {card.fax or '-'}")
                st.markdown(f"**📍 地址:** {card.address or '-'}")
                st.markdown(f"**🌐 网站:** {card.website or '-'}")
                st.markdown(f"**💼 LinkedIn:** {card.linkedin or '-'}")
                st.markdown(f"**💬 微信:** {card.wechat or '-'}")
                st.markdown(f"**📝 备注:** {card.notes or '-'}")

            # Delete button for individual card
            if st.button(f"🗑️ 删除此名片", key=f"delete_{idx}"):
                st.session_state.cards.pop(idx)
                st.rerun()


def render_export_section():
    """Render the export section"""
    if not st.session_state.cards:
        return

    st.header("📁 导出 / Export")

    col1, col2, col3, col4 = st.columns(4)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with col1:
        csv_data = export_to_csv(st.session_state.cards)
        st.download_button(
            label="📊 下载 CSV",
            data=csv_data,
            file_name=f"business_cards_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        excel_data = export_to_excel(st.session_state.cards)
        st.download_button(
            label="📗 下载 Excel",
            data=excel_data,
            file_name=f"business_cards_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col3:
        json_data = export_to_json(st.session_state.cards)
        st.download_button(
            label="📄 下载 JSON",
            data=json_data,
            file_name=f"business_cards_{timestamp}.json",
            mime="application/json",
            use_container_width=True
        )

    with col4:
        vcard_data = export_to_vcard(st.session_state.cards)
        st.download_button(
            label="👤 下载 vCard",
            data=vcard_data,
            file_name=f"business_cards_{timestamp}.vcf",
            mime="text/vcard",
            use_container_width=True
        )


def main():
    """Main application entry point"""
    init_session_state()

    # Header
    st.markdown('<h1 class="main-header">📇 名片识别助手</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">Business Card Recognition powered by Google Gemini AI</p>', unsafe_allow_html=True)

    # Render sidebar
    render_sidebar()

    # Main content
    tab1, tab2 = st.tabs(["📷 上传识别", "📋 结果管理"])

    with tab1:
        render_upload_section()

    with tab2:
        render_results_section()
        render_export_section()


if __name__ == "__main__":
    main()
