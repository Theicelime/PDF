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
    # 如果没设置 Secrets，给一个非常复杂的随机默认值，确保安全
    ADMIN_PWD = "STRICT_LOCK_MODE_ENABLED_123456789"
    ADMIN_URL_KEY = "NOT_SET_YET"

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# --- 2. 工具函数 ---

def get_user_path(code, folder_type):
    """为每个口令创建独立子目录"""
    # 仅保留字母和数字，防止路径注入攻击
    safe_code = "".join([c for c in code if c.isalnum()])
    path = os.path.join(BASE_DIR, safe_code, folder_type)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def cleanup_expired_data():
    """清理过期文件"""
    now = time.time()
    if os.path.exists(BASE_DIR):
        for code_folder in os.listdir(BASE_DIR):
            dir_path = os.path.join(BASE_DIR, code_folder)
            if os.path.isdir(dir_path):
                # 如果文件夹创建时间超过 24 小时
                if os.path.getmtime(dir_path) < now - (EXPIRY_HOURS * 3600):
                    shutil.rmtree(dir_path)

# 自动执行清理
cleanup_expired_data()

# --- 3. 路由逻辑 ---
# 获取 URL 参数，例如 ?view=xxx
query_params = st.query_params
view_mode = query_params.get("view", "user")

# --- 4. 界面逻辑 ---
st.set_page_config(page_title="私人文件交换系统", layout="centered")

# 管理员视图：只有 URL 匹配 admin_url_key 时才激活
if view_mode == ADMIN_URL_KEY and ADMIN_URL_KEY != "NOT_SET_YET":
    st.title("🛡️ 管理后台")
    pwd_input = st.text_input("认证密钥", type="password")
    
    if pwd_input == ADMIN_PWD:
        st.success("认证成功，欢迎回来。")
        
        if os.path.exists(BASE_DIR):
            all_codes = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
        else:
            all_codes = []

        if not all_codes:
            st.info("当前暂无用户上传数据。")
        
        for code in all_codes:
            with st.expander(f"📦 用户口令: {code}", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("**客户上传的 PDF:**")
                    pdf_dir = get_user_path(code, "pdfs")
                    files = os.listdir(pdf_dir)
                    for f_name in files:
                        with open(os.path.join(pdf_dir, f_name), "rb") as f:
                            st.download_button(f"下载 {f_name}", f, key=f"dl_{code}_{f_name}")
                
                with col_b:
                    st.write("**回传 PPT 给客户:**")
                    new_ppt = st.file_uploader(f"上传 PPT ({code})", type=["pptx", "ppt"], key=f"up_{code}")
                    if new_ppt:
                        ppt_dir = get_user_path(code, "ppts")
                        with open(os.path.join(ppt_dir, new_ppt.name), "wb") as f:
                            f.write(new_ppt.getbuffer())
                        st.success(f"已存入 {code}")

        st.sidebar.markdown("---")
        if st.sidebar.button("🔴 清空所有服务器文件"):
            shutil.rmtree(BASE_DIR)
            os.makedirs(BASE_DIR)
            st.rerun()
    elif pwd_input != "":
        st.error("密钥无效")

# 普通用户视图
else:
    st.title("📂 PDF-PPT 交换中心")
    st.write("请在下方输入提取码，上传 PDF 或提取转换好的 PPT。")
    
    user_code = st.text_input("🔑 输入您的专属提取码", placeholder="例如: abc123", type="default")
    
    if user_code:
        if len(user_code) < 3:
            st.warning("提取码太短，请设置 3 位以上。")
        else:
            t1, t2 = st.tabs(["📤 上传 PDF", "📥 提取 PPT"])
            
            with t1:
                pdf_file = st.file_uploader("选择要转换的 PDF", type=["pdf"])
                if pdf_file:
                    save_path = os.path.join(get_user_path(user_code, "pdfs"), pdf_file.name)
                    with open(save_path, "wb") as f:
                        f.write(pdf_file.getbuffer())
                    st.success("上传成功！请告知管理员进行处理。")
            
            with t2:
                ppt_dir = get_user_path(user_code, "ppts")
                ppt_files = os.listdir(ppt_dir)
                if ppt_files:
                    for pf in ppt_files:
                        with open(os.path.join(ppt_dir, pf), "rb") as f:
                            st.download_button(f"💾 下载 {pf}", f, file_name=pf, key=f"user_dl_{pf}")
                else:
                    st.info("此处暂无文件。如果刚上传，请等待管理员处理。")
    else:
        st.info("请输入提取码以进入您的私人空间。")

    st.markdown("---")
    st.caption("隐私保护：文件将在 24 小时后自动销毁。")
