import streamlit as st
import os
import time
import shutil
from datetime import datetime

# --- 1. 配置与安全 ---
BASE_DIR = "data_store"
EXPIRY_HOURS = 24 

# 从 Streamlit Cloud 的 Secrets 中读取安全配置
try:
    ADMIN_PWD = st.secrets["admin_password"]
    ADMIN_URL_KEY = st.secrets["admin_url_key"]
except Exception:
    ADMIN_PWD = "admin" # 仅用于本地调试
    ADMIN_URL_KEY = "admin"

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# --- 2. 工具函数 ---

def get_user_path(code, folder_type):
    """为每个口令创建独立子目录"""
    safe_code = "".join([c for c in code if c.isalnum()])
    path = os.path.join(BASE_DIR, safe_code, folder_type)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def cleanup_expired_data():
    """清理过期文件 (24小时)"""
    now = time.time()
    if os.path.exists(BASE_DIR):
        for code_folder in os.listdir(BASE_DIR):
            dir_path = os.path.join(BASE_DIR, code_folder)
            if os.path.isdir(dir_path):
                if os.path.getmtime(dir_path) < now - (EXPIRY_HOURS * 3600):
                    shutil.rmtree(dir_path)

cleanup_expired_data()

# --- 3. 页面配置 ---
st.set_page_config(page_title="PDF-PPT 互助交换站", layout="centered")

# 获取 URL 参数
query_params = st.query_params
view_mode = query_params.get("view", "user")

# --- 4. 界面逻辑 ---

# A. 管理员后台
if view_mode == ADMIN_URL_KEY:
    st.title("🛡️ 管理后台")
    pwd_input = st.text_input("认证密钥", type="password")
    
    if pwd_input == ADMIN_PWD:
        st.success("认证成功")
        
        if os.path.exists(BASE_DIR):
            all_codes = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
        else:
            all_codes = []

        if not all_codes:
            st.info("当前暂无用户数据")
        
        for code in all_codes:
            with st.expander(f"📦 用户口令: {code}", expanded=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("**📥 待处理 PDF:**")
                    pdf_dir = get_user_path(code, "pdfs")
                    pdf_files = os.listdir(pdf_dir)
                    for f_name in pdf_files:
                        download_name = f"{code}_{f_name}"
                        with open(os.path.join(pdf_dir, f_name), "rb") as f:
                            st.download_button(
                                label=f"下载 {f_name}",
                                data=f,
                                file_name=download_name,
                                mime="application/pdf",
                                key=f"dl_{code}_{f_name}"
                            )
                
                with col_b:
                    st.write("**📤 回传 PPT:**")
                    new_ppt = st.file_uploader(f"上传结果 ({code})", type=["pptx", "ppt"], key=f"up_{code}")
                    if new_ppt:
                        ppt_dir = get_user_path(code, "ppts")
                        with open(os.path.join(ppt_dir, new_ppt.name), "wb") as f:
                            f.write(new_ppt.getbuffer())
                        st.success(f"已发送 PPT")

        st.sidebar.markdown("---")
        if st.sidebar.button("🔴 清空所有服务器文件"):
            shutil.rmtree(BASE_DIR)
            os.makedirs(BASE_DIR)
            st.rerun()
            
    elif pwd_input != "":
        st.error("密钥无效")

# B. 普通用户页面
else:
    st.title("📂 PDF-PPT 互助交换站")
    
    # --- 免责声明模块 ---
    with st.expander("📢 使用前必读：免责声明与隐私提醒", expanded=True):
        st.markdown("""
        1. **互助性质**：本站仅为公益互助演示，旨在利用闲置会员资源帮助有需要的同学，**严禁上传敏感、保密、非法或高度隐私的文件**。
        2. **隐私提醒**：请设置**复杂口令**（如：字母+数字）以防文件被他人误领。请勿使用过于简单的数字口令。
        3. **自动销毁**：所有文件仅在服务器保留 **24小时**，过期将自动物理粉碎。请及时提取转换结果。
        4. **责任界定**：管理员承诺不存档、不外传文件。如因用户设置弱口令导致文件被第三方截获，或因不可抗力导致数据丢失，本站不承担相关责任。
        5. **手动删除**：提取完成后，建议联系管理员或等待系统自动清理。
        """)
    
    st.markdown("---")
    user_code = st.text_input("🔑 请输入您的专属提取码（建议使用字母+数字）", placeholder="例如：Alex8899", type="default")
    
    if user_code:
        if len(user_code) < 4:
            st.warning("⚠️ 提取码过短，为了您的文件安全，请设置至少4位。")
        else:
            t1, t2 = st.tabs(["📤 上传 PDF", "📥 提取 PPT"])
            
            with t1:
                st.warning("🚀 请确保文件不含个人敏感信息（如身份证号、财务报表等）。")
                pdf_file = st.file_uploader("选择 PDF 文件 (Max: 200MB)", type=["pdf"])
                if pdf_file:
                    pdf_save_path = os.path.join(get_user_path(user_code, "pdfs"), pdf_file.name)
                    with open(pdf_save_path, "wb") as f:
                        f.write(pdf_file.getbuffer())
                    st.success(f"✅ 文件 {pdf_file.name} 已上传！请等待管理员处理。")
                    st.balloons()
            
            with t2:
                ppt_dir = get_user_path(user_code, "ppts")
                ppt_files = os.listdir(ppt_dir)
                if ppt_files:
                    st.write("✨ 转换已完成，请及时下载：")
                    for pf in ppt_files:
                        with open(os.path.join(ppt_dir, pf), "rb") as f:
                            st.download_button(
                                label=f"💾 点击下载 {pf}",
                                data=f,
                                file_name=pf,
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                key=f"user_dl_{pf}"
                            )
                else:
                    st.info("⌛ 暂无处理好的 PPT。如果刚刚上传，请稍等或稍后刷新页面。")
    else:
        st.info("💡 在上方输入提取码即可开始。请记住您的提取码，它是找回文件的唯一凭证。")

    st.markdown("---")
    st.caption("🔒 安全模式已开启：所有传输均经过 HTTPS 加密 | 24小时自动销毁记录")
