import streamlit as st
import os
import time
import shutil
from datetime import datetime

# --- 配置 ---
BASE_DIR = "data_store"  # 所有数据的根目录
ADMIN_PASSWORD = "boss666"  # 管理员进入后台的密码
EXPIRY_HOURS = 24  # 文件保留时间

# 确保根目录存在
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# --- 工具函数 ---

def get_user_path(code, folder_type):
    """根据口令生成路径: data_store/口令/pdfs 或 ppts"""
    path = os.path.join(BASE_DIR, code, folder_type)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def cleanup_expired_data():
    """清理超过24小时的文件夹"""
    now = time.time()
    if os.path.exists(BASE_DIR):
        for code_folder in os.listdir(BASE_DIR):
            dir_path = os.path.join(BASE_DIR, code_folder)
            if os.path.isdir(dir_path):
                # 检查文件夹的最后修改时间
                if os.path.getmtime(dir_path) < now - (EXPIRY_HOURS * 3600):
                    shutil.rmtree(dir_path)

# 每次运行先清理旧数据
cleanup_expired_data()

# --- 界面排版 ---
st.set_page_config(page_title="私人文件交换站", layout="wide")
st.title("🔐 私人 PDF-PPT 文件交换站")

# 侧边栏
st.sidebar.header("身份验证")
role = st.sidebar.radio("选择角色", ["我是客户", "我是管理员"])

# --------------------------
# 角色 1：客户界面
# --------------------------
if role == "我是客户":
    user_code = st.text_input("请输入您的专属口令 (用于区分彼此的文件):", type="password")
    
    if user_code:
        st.info(f"当前口令：{user_code} (请牢记，下次凭此口令取回 PPT)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📤 上传 PDF")
            uploaded_pdf = st.file_uploader("上传需要转换的 PDF", type=["pdf"])
            if uploaded_pdf:
                save_path = get_user_path(user_code, "pdfs")
                # 文件名增加时间戳，防止重名
                timestamp = datetime.now().strftime("%H%M%S_")
                final_name = timestamp + uploaded_pdf.name
                full_path = os.path.join(save_path, final_name)
                
                with open(full_path, "wb") as f:
                    f.write(uploaded_pdf.getbuffer())
                st.success(f"上传成功！文件名：{final_name}")

        with col2:
            st.subheader("📥 提取 PPT")
            ppt_path = get_user_path(user_code, "ppts")
            ppt_files = os.listdir(ppt_path)
            
            if ppt_files:
                for ppt_file in ppt_files:
                    with open(os.path.join(ppt_path, ppt_file), "rb") as f:
                        st.download_button(label=f"💾 下载 {ppt_file}", data=f, file_name=ppt_file)
            else:
                st.warning("暂无可下载的 PPT，请等待管理员处理。")
    else:
        st.warning("请输入口令以开启您的私人空间。")

# --------------------------
# 角色 2：管理员界面
# --------------------------
else:
    admin_pwd = st.sidebar.text_input("管理员密码", type="password")
    if admin_pwd == ADMIN_PASSWORD:
        st.header("⚡ 管理员工作台")
        
        # 获取所有有数据的口令文件夹
        all_codes = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
        
        if not all_codes:
            st.write("目前没有任何客户上传文件。")
        
        for code in all_codes:
            with st.expander(f"口令【{code}】的文件列表", expanded=True):
                c1, c2 = st.columns(2)
                
                # 待处理区域
                with c1:
                    st.write("📄 待下载 PDF:")
                    pdf_dir = get_user_path(code, "pdfs")
                    pdfs = os.listdir(pdf_dir)
                    for pdf in pdfs:
                        with open(os.path.join(pdf_dir, pdf), "rb") as f:
                            st.download_button(f"下载 {pdf}", f, file_name=pdf, key=f"dl_{pdf}")
                
                # 回传区域
                with c2:
                    st.write("📤 回传 PPT:")
                    new_ppt = st.file_uploader(f"上传 PPT 到口令【{code}】", type=["pptx", "ppt"], key=f"up_{code}")
                    if new_ppt:
                        ppt_save_dir = get_user_path(code, "ppts")
                        with open(os.path.join(ppt_save_dir, new_ppt.name), "wb") as f:
                            f.write(new_ppt.getbuffer())
                        st.success(f"已发送给客户【{code}】")
                        
        st.divider()
        if st.button("🔴 强制清空所有服务器文件"):
            shutil.rmtree(BASE_DIR)
            os.makedirs(BASE_DIR)
            st.rerun()

    elif admin_pwd != "":
        st.error("管理员密码错误")
