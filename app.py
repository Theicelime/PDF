import streamlit as st
import os
import time
import shutil
from datetime import datetime

# --- 1. 配置与安全 ---
BASE_DIR = "data_store"
EXPIRY_HOURS = 24 

# 从 Secrets 获取安全配置
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
    # 仅保留字母和数字
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
st.set_page_config(page_title="PDF-PPT 交换系统", layout="centered")

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
                        # 优化点 1：管理员下载时，文件名自动变为 "口令_原文件名.pdf"
                        download_name = f"{code}_{f_name}"
                        with open(os.path.join(pdf_dir, f_name), "rb") as f:
                            st.download_button(
                                label=f"下载 {f_name}",
                                data=f,
                                file_name=download_name,  # 这里的 file_name 决定了你保存到本地的名字
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
                        st.success(f"已发送 PPT: {new_ppt.name}")

        st.sidebar.markdown("---")
        if st.sidebar.button("🔴 清空服务器所有数据"):
            shutil.rmtree(BASE_DIR)
            os.makedirs(BASE_DIR)
            st.rerun()
            
    elif pwd_input != "":
        st.error("密钥无效")

# B. 普通用户页面
else:
    st.title("📂 PDF-PPT 交换中心")
    user_code = st.text_input("🔑 请输入您的专属提取码", placeholder="在此输入口令", type="default")
    
    if user_code:
        if len(user_code) < 3:
            st.warning("提取码过短。")
        else:
            t1, t2 = st.tabs(["📤 我要上传", "📥 我要提取"])
            
            with t1:
                st.info("上传 PDF 后，请告知管理员处理。")
                pdf_file = st.file_uploader("选择 PDF 文件", type=["pdf"])
                if pdf_file:
                    pdf_save_path = os.path.join(get_user_path(user_code, "pdfs"), pdf_file.name)
                    with open(pdf_save_path, "wb") as f:
                        f.write(pdf_file.getbuffer())
                    st.success(f"文件 {pdf_file.name} 上传成功！")
            
            with t2:
                ppt_dir = get_user_path(user_code, "ppts")
                ppt_files = os.listdir(ppt_dir)
                if ppt_files:
                    st.write("✅ 转换完成，请下载：")
                    for pf in ppt_files:
                        with open(os.path.join(ppt_dir, pf), "rb") as f:
                            # 优化点 2：用户下载时保持 PPT 原名，并明确指定 PPTX 的 MIME 类型
                            st.download_button(
                                label=f"点击下载 {pf}",
                                data=f,
                                file_name=pf,
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                key=f"user_dl_{pf}"
                            )
                else:
                    st.info("暂未发现处理好的 PPT，请稍后再来。")
    else:
        st.info("请输入提取码以开始。")

    st.markdown("---")
    st.caption("隐私保护：文件将在 24 小时后自动销毁。")
