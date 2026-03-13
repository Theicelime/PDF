import streamlit as st
import os
import time
import shutil
import hashlib
from datetime import datetime

# --- 1. 配置与安全 ---
BASE_DIR = "data_store"
EXPIRY_HOURS = 72  
# 小红书原笔记链接
XHS_LINK = "https://www.xiaohongshu.com/explore/696f27e7000000000a03ee45?xsec_token=ABft3QO37w_LDTt8J5zePSaog2TSYY1qVxGckdEZeuUpc=&xsec_source=pc_user"

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

def get_file_time(file_path):
    """获取并格式化文件时间"""
    if os.path.exists(file_path):
        ts = os.path.getmtime(file_path)
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
    return "未知时间"

def get_comment_code(user_code):
    """通过真实口令生成4位安全的公开留言码"""
    return hashlib.md5(user_code.encode('utf-8')).hexdigest()[:4].upper()

def cleanup_expired_data():
    """清理过期文件"""
    now = time.time()
    if os.path.exists(BASE_DIR):
        for code_folder in os.listdir(BASE_DIR):
            dir_path = os.path.join(BASE_DIR, code_folder)
            if os.path.isdir(dir_path):
                # 检查文件夹本身的修改时间（或检查内部文件）
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
    st.title("🛡️ 管理后台 (72h保留)")
    pwd_input = st.text_input("认证密钥", type="password")
    
    if pwd_input == ADMIN_PWD:
        st.success("认证成功")
        
        if os.path.exists(BASE_DIR):
            raw_codes = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
        else:
            raw_codes = []

        if not raw_codes:
            st.info("当前暂无用户数据")
        
        # 数据预处理与排序
        user_data_list = []
        for code in raw_codes:
            ppt_dir = get_user_path(code, "ppts")
            has_ppt = len(os.listdir(ppt_dir)) > 0
            user_data_list.append({"code": code, "processed": has_ppt})
        
        # 排序：未处理 (False) 排在前面，已处理 (True) 排在后面
        user_data_list.sort(key=lambda x: x["processed"])

        # 统计信息
        pending_count = sum(1 for x in user_data_list if not x["processed"])
        st.markdown(f"📊 **任务统计**：待处理 `{pending_count}` | 已完成 `{len(user_data_list) - pending_count}`")
        st.divider()

        for item in user_data_list:
            code = item["code"]
            is_done = item["processed"]
            
            # 视觉区分状态
            status_icon = "✅" if is_done else "⏳"
            status_label = "已回传" if is_done else "待处理"
            
            # 【核心修改点】：在管理员后台展示对应的“留言码”，方便你和小红书评论区对号入座！
            comment_code = get_comment_code(code)
            
            with st.expander(f"{status_icon} [{status_label}] 提取码: {code}  |  📢 对应留言码: {comment_code}", expanded=not is_done):
                col_a, col_b = st.columns(2)
                
                # 左列：用户上传的 PDF
                with col_a:
                    st.markdown("**📥 用户 PDF:**")
                    pdf_dir = get_user_path(code, "pdfs")
                    pdf_files = os.listdir(pdf_dir)
                    
                    if not pdf_files:
                        st.caption("无文件")
                    
                    for f_name in pdf_files:
                        full_path = os.path.join(pdf_dir, f_name)
                        upload_time = get_file_time(full_path) 
                        
                        st.markdown(f"📄 `{f_name}`")
                        st.caption(f"🕒 上传于: {upload_time}") 
                        
                        with open(full_path, "rb") as f:
                            st.download_button(
                                label="⬇️ 下载查看",
                                data=f,
                                file_name=f"{code}_{f_name}",
                                mime="application/pdf",
                                key=f"dl_{code}_{f_name}"
                            )
                        st.markdown("---")
                
                # 右列：回传 PPT
                with col_b:
                    st.markdown(f"**📤 回传结果 ({'已存在' if is_done else '空'}):**")
                    
                    # 如果已存在文件，先列出来
                    ppt_dir = get_user_path(code, "ppts")
                    existing_ppts = os.listdir(ppt_dir)
                    for ppt in existing_ppts:
                        ppt_path = os.path.join(ppt_dir, ppt)
                        ppt_time = get_file_time(ppt_path)
                        st.info(f"💾 已存在: {ppt}\n\n🕒 {ppt_time}")

                    # 上传新文件
                    new_ppt = st.file_uploader(f"上传 PPT ({code})", type=["pptx", "ppt"], key=f"up_{code}")
                    if new_ppt:
                        with open(os.path.join(ppt_dir, new_ppt.name), "wb") as f:
                            f.write(new_ppt.getbuffer())
                        st.toast(f"✅ 发送成功: {code}")
                        time.sleep(1)
                        st.rerun()

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
    
    with st.expander("📢 使用前必读：免责声明与隐私提醒", expanded=True):
        st.markdown(f"""
        1. **互助性质**：本站为人工公益演示，**严禁上传敏感、保密、非法文件**。
        2. **隐私提醒**：请设置**复杂口令**。
        3. **保留时长**：文件将在服务器保留 **{EXPIRY_HOURS}小时**，过期自动销毁。
        4. **免责**：管理员不存档文件，因弱口令导致的文件泄漏风险由用户自负。
        """)
    
    st.markdown("---")
    user_code = st.text_input("🔑 请输入您的专属提取码", placeholder="例如：Alex8899", type="default")
    
    if user_code:
        if len(user_code) < 4:
            st.warning("⚠️ 提取码过短，为了您的文件安全，请设置至少4位。")
        else:
            # 动态生成该用户的专属公开留言码
            public_comment_code = get_comment_code(user_code)
            
            t1, t2 = st.tabs(["📤 上传 PDF", "📥 提取 PPT"])
            
            with t1:
                st.warning("🚀 请确保文件不含个人敏感信息。")
                
                # 显示已上传的文件列表
                current_pdfs_dir = get_user_path(user_code, "pdfs")
                existing_pdfs = os.listdir(current_pdfs_dir)
                
                # === 核心修改点：保护隐私的同时，提供专属留言码 ===
                if existing_pdfs:
                    st.success(f"""
                    **📢 提醒：文件已成功上传！**  
                    为了保护您的文件隐私，**千万不要泄露真实提取码！**  
                    系统为您生成了安全的专属公开留言码：`{public_comment_code}`  
                    
                    👉 [点击跳转小红书原笔记]({XHS_LINK})，并在评论区留言：**已上传，留言码 {public_comment_code}**。  
                    管理员看到对应的留言码后，会更快速地为您在后台对号入座并处理！
                    """)
                    
                    st.write("📋 **已上传文件记录：**")
                    for ep in existing_pdfs:
                        ep_time = get_file_time(os.path.join(current_pdfs_dir, ep))
                        st.caption(f"📄 {ep} (🕒 {ep_time})")
                    st.divider()

                pdf_file = st.file_uploader("选择 PDF 文件 (Max: 200MB)", type=["pdf"])
                if pdf_file:
                    pdf_save_path = os.path.join(current_pdfs_dir, pdf_file.name)
                    with open(pdf_save_path, "wb") as f:
                        f.write(pdf_file.getbuffer())
                    st.success(f"✅ 文件 {pdf_file.name} 已上传！")
                    time.sleep(1)
                    st.rerun()
            
            with t2:
                ppt_dir = get_user_path(user_code, "ppts")
                ppt_files = os.listdir(ppt_dir)
                if ppt_files:
                    st.write("✨ 转换已完成，请及时下载：")
                    for pf in ppt_files:
                        pf_path = os.path.join(ppt_dir, pf)
                        pf_time = get_file_time(pf_path) 
                        
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"💾 **{pf}**")
                            st.caption(f"🕒 处理时间: {pf_time}")
                        with col2:
                            with open(pf_path, "rb") as f:
                                st.download_button(
                                    label="下载",
                                    data=f,
                                    file_name=pf,
                                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                    key=f"user_dl_{pf}"
                                )
                else:
                    st.info("⌛ 暂无处理好的 PPT。")
                    
                    # === 核心修改点：等待页面也展示留言码提醒 ===
                    st.info(f"""
                    **📢 提醒：**  
                    如果您刚上传了文件，请[前往小红书笔记]({XHS_LINK}) 评论区留言：**已上传，留言码 {public_comment_code}**。  
                    *不要发送您的真实提取码，留言这个安全的公开码，管理员就能更快速地定位处理哦。*
                    """)
                    st.caption(f"数据保留 {EXPIRY_HOURS} 小时。处理完成后请刷新页面下载。")
                    
    else:
        st.info("💡 在上方输入提取码即可开始。")

    st.markdown("---")
    st.caption(f"🔒 安全模式 | {EXPIRY_HOURS}小时自动销毁记录")
