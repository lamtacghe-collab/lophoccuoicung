import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import random
import time
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. KẾT NỐI FIREBASE ---
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://hoc-tap-58166-default-rtdb.asia-southeast1.firebasedatabase.app/'
    })

st.title("🖤 Lớp học Hắc Ám")

# --- LẤY MẬT KHẨU TỪ FIREBASE SERVER ---
try:
    server_pass_ref = db.reference('settings/teacher_password')
    SERVER_TEACHER_PASS = server_pass_ref.get()
    if not SERVER_TEACHER_PASS:
        SERVER_TEACHER_PASS = "12345"
        server_pass_ref.set(SERVER_TEACHER_PASS)
except Exception:
    SERVER_TEACHER_PASS = "12345"

# --- PHẦN ĐĂNG NHẬP VAI TRÒ & BẢO MẬT ---
role = st.sidebar.selectbox("Chọn vai trò của bạn", ["Học sinh", "Thầy giáo"])

access_granted = True

if role == "Thầy giáo":
    if 'teacher_logged_in' not in st.session_state:
        st.session_state.teacher_logged_in = False
        
    if not st.session_state.teacher_logged_in:
        access_granted = False
        st.subheader("🔒 Đăng nhập Bảng điều khiển Thầy giáo")
        
        teacher_pass = st.text_input("Nhập mật khẩu thầy giáo:", type="password")
        
        col_lg1, col_lg2 = st.columns(2)
        with col_lg1:
            if st.button("Xác nhận đăng nhập", type="primary"):
                if teacher_pass == SERVER_TEACHER_PASS:  
                    st.session_state.teacher_logged_in = True
                    st.success("Đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error("Sai mật khẩu!")
        
        st.markdown("---")
        with st.expander("🔑 Bạn muốn đổi mật khẩu mới?"):
            new_p1 = st.text_input("Mật khẩu hiện tại:", type="password", key="np1")
            new_p2 = st.text_input("Mật khẩu mới:", type="password", key="np2")
            if st.button("Lưu mật khẩu mới"):
                if new_p1 == SERVER_TEACHER_PASS:
                    if new_p2.strip():
                        db.reference('settings/teacher_password').set(new_p2.strip())
                        st.success("Đã đổi mật khẩu thành công! Hãy dùng mật khẩu mới để đăng nhập.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("Mật khẩu mới không được để trống.")
                else:
                    st.error("Mật khẩu hiện tại không đúng.")
    else:
        if st.sidebar.button("Đăng xuất Thầy giáo"):
            st.session_state.teacher_logged_in = False
            st.rerun()

# ================= VAI TRÒ: THẦY GIÁO =================
if role == "Thầy giáo" and access_granted:
    st.header("🎛️ Bảng điều khiển của Thầy giáo")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎮 Điều khiển phòng thi", "✍️ Kho câu hỏi", "📋 Tạo & Chọn bài thi", "👥 Quản lý học sinh", "📈 Biểu đồ kết cấu"])
    
    try:
        questions_raw = db.reference('questions').get()
    except Exception:
        questions_raw = None

    if isinstance(questions_raw, list):
        all_questions = [q for q in questions_raw if q is not None and isinstance(q, dict)]
    elif isinstance(questions_raw, dict):
        all_questions = [v for v in questions_raw.values() if isinstance(v, dict)]
    else:
        all_questions = []

    try:
        exam_raw = db.reference('current_exam').get()
    except Exception:
        exam_raw = None

    if isinstance(exam_raw, dict):
        current_exam = [q for q in exam_raw.get("questions", []) if q is not None and isinstance(q, dict)]
        total_time_limit = exam_raw.get("total_time_limit", 300)
    elif isinstance(exam_raw, list):
        current_exam = [q for q in exam_raw if q is not None and isinstance(q, dict)]
        total_time_limit = 300
    else:
        current_exam = []
        total_time_limit = 300
    
    ref_state = db.reference('game_state')
    try:
        current_state = ref_state.get() or {"status": "waiting", "start_time": 0}
    except Exception:
        current_state = {"status": "waiting", "start_time": 0}
        
    status = current_state.get("status", "waiting")
    start_time = current_state.get("start_time", 0)

    # --- TAB 1: ĐIỀU KHIỂN PHÒNG THI & KIỂM TRA BÀI HỌC SINH ---
    with tab1:
        st.write(f"**Số câu hỏi trong bài thi:** {len(current_exam)} | **Tổng thời gian bài thi cài đặt:** {total_time_limit} giây")
        st.write(f"**Trạng thái phòng:** {status.upper()}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Bắt đầu bài thi"):
                if current_exam:
                    ref_state.set({"status": "active", "start_time": time.time()})
                    db.reference('answers').delete()
                    db.reference('student_times').delete()
                    st.success("Đã bắt đầu bài thi cho toàn lớp!")
                    st.rerun()
                else:
                    st.warning("Chưa có bài thi nào được chọn!")
                
        with col2:
            if st.button("🔄 Reset / Dừng phòng thi"):
                ref_state.set({"status": "waiting", "start_time": 0})
                db.reference('answers').delete()
                db.reference('student_times').delete()
                st.success("Đã reset phòng thi và làm sạch kết quả trực tiếp ở Tab 1!")
                st.rerun()

        st.markdown("---")
        st.subheader("📊 Tổng kết chi tiết kết quả toàn bài của lớp")
        
        try:
            all_answers = db.reference('answers').get() or {}
            student_times = db.reference('student_times').get() or {}
        except Exception:
            all_answers = {}
            student_times = {}
        
        if current_exam:
            all_students = set()
            for c_key, c_val in all_answers.items():
                if isinstance(c_val, dict):
                    for s_name in c_val.keys():
                        all_students.add(s_name.strip())
            
            if not all_students:
                st.info("Chưa có học sinh nào nộp bài.")
            else:
                summary_rows = []
                student_detail_map = {}
                
                for s_name in sorted(all_students):
                    correct_count = 0
                    wrong_count = 0
                    s_details = []
                    
                    for idx, q in enumerate(current_exam):
                        correct_ans = str(q.get('dap_an_dung', '')).strip().lower()
                        cau_ans_dict = all_answers.get(f'cau_{idx}', {})
                        
                        ans_chosen = "Chưa làm"
                        if isinstance(cau_ans_dict, dict):
                            for db_s_name, db_s_ans in cau_ans_dict.items():
                                if db_s_name.strip() == s_name:
                                    ans_chosen = db_s_ans
                                    break
                        
                        ans_chosen_str = str(ans_chosen).strip().lower()
                        
                        is_correct = False
                        if ans_chosen != "Chưa làm":
                            if "Viết" in str(q.get('loai_cau_hoi', '')):
                                if ans_chosen_str in correct_ans or correct_ans in ans_chosen_str:
                                    is_correct = True
                            elif ans_chosen_str == correct_ans:
                                is_correct = True
                        
                        if is_correct:
                            correct_count += 1
                        else:
                            wrong_count += 1
                            
                        s_details.append({
                            "cau_so": idx + 1,
                            "loai": q.get('loai_cau_hoi'),
                            "noi_dung": q.get('noi_dung'),
                            "chon": ans_chosen,
                            "dap_an": q.get('dap_an_dung'),
                            "dung": is_correct
                        })
                    
                    finish_timestamp = student_times.get(s_name, start_time)
                    duration = int(finish_timestamp - start_time)
                    if duration < 0: 
                        duration = 0
                    mins = duration // 60
                    secs = duration % 60
                    time_str = f"{mins} phút {secs} giây" if mins > 0 else f"{secs} giây"
                    
                    summary_rows.append({
                        "Học sinh": s_name,
                        "Thời gian hoàn thành": time_str,
                        "Số câu Đúng": correct_count,
                        "Số câu Sai": wrong_count,
                        "Tổng số câu": len(current_exam)
                    })
                    student_detail_map[s_name] = s_details

                st.table(summary_rows)
                
                st.markdown("---")
                st.subheader("🔍 Kiểm tra chi tiết bài làm của từng học sinh (Trắc nghiệm sai & Tự luận)")
                selected_student = st.selectbox("Chọn tên học sinh để kiểm tra:", list(student_detail_map.keys()))
                
                if selected_student:
                    st.markdown(f"**Bài làm chi tiết của học sinh: `{selected_student}`**")
                    detail_data = student_detail_map[selected_student]
                    
                    # 1. PHẦN TRẮC NGHIỆM SAI ĐỂ THẦY CÔ SỬA BÀI
                    st.markdown("### ❌ Các câu trắc nghiệm làm sai (Cần giảng lại)")
                    mc_wrong_items = [item for item in detail_data if "Viết" not in str(item['loai']) and not item['dung']]
                    
                    if not mc_wrong_items:
                        st.success("Tuyệt vời! Học sinh này không làm sai câu trắc nghiệm nào.")
                    else:
                        for item in mc_wrong_items:
                            st.warning(f"**Câu {item['cau_so']} [{item['loai']}]**: {item['noi_dung']}")
                            st.write(f"- Học sinh chọn: `{item['chon']}` | ❌ **Đáp án đúng chuẩn**: `{item['dap_an']}`")
                    
                    st.markdown("---")

                    # 2. PHẦN TỰ LUẬN (VIẾT) ĐỂ CHẤM ĐIỂM THỦ CÔNG
                    st.markdown("### ✍️ Phần Tự luận (Viết) cần chấm điểm")
                    essay_items = [item for item in detail_data if "Viết" in str(item['loai'])]
                    
                    if not essay_items:
                        st.info("Bài thi này không có câu tự luận nào.")
                    else:
                        for item in essay_items:
                            st.write(f"**Câu {item['cau_so']} [{item['loai']}]**: {item['noi_dung']}")
                            st.write(f"- Học sinh trả lời: `{item['chon']}` | Đáp án mẫu: `{item['dap_an']}`")
                            
                            current_status = item["dung"]
                            new_status = st.radio(
                                f"Đánh giá điểm câu {item['cau_so']}:",
                                ["Đúng", "Sai"],
                                index=0 if current_status else 1,
                                key=f"override_{selected_student}_{item['cau_so']}",
                                horizontal=True
                            )
                            if new_status == "Đúng" and not current_status:
                                st.success("Đã ghi nhận chỉnh sửa điểm thủ công thành công!")
                            st.markdown("---")
        else:
            st.info("Chưa có bài thi nào được kích hoạt.")

    # --- TAB 2: KHO CÂU HỎI ---
    with tab2:
        st.subheader("📦 Quản lý Kho Câu Hỏi")
        
        if 'edit_index' not in st.session_state:
            st.session_state.edit_index = None

        is_editing = st.session_state.edit_index is not None
        
        if is_editing:
            st.warning(f"Đang chỉnh sửa câu hỏi số {st.session_state.edit_index + 1}")
            q_edit = all_questions[st.session_state.edit_index]
            default_dm_idx = 0
            if "Viết" in q_edit.get('loai_cau_hoi', ''):
                default_dm_idx = 1
            elif q_edit.get('loai_cau_hoi', '') == "Nhớ hán tự":
                default_dm_idx = 2
        else:
            q_edit = {}
            default_dm_idx = 0

        danh_muc = st.selectbox("Chọn mục câu hỏi:", ["1. Nghe", "2. Viết", "3. Nhớ hán tự"], index=default_dm_idx, key="dm_kho")
        
        if danh_muc == "1. Nghe":
            loai_cau_hoi = "Nghe"
            noi_dung = st.text_area("Nội dung / Yêu cầu bài nghe:", value=q_edit.get('noi_dung', '') if is_editing else "", key="nd_nghe")
            opt_a = st.text_input("Phương án A:", value=q_edit.get('A', '') if is_editing else "", key="oa_n")
            opt_b = st.text_input("Phương án B:", value=q_edit.get('B', '') if is_editing else "", key="ob_n")
            opt_c = st.text_input("Phương án C:", value=q_edit.get('C', '') if is_editing else "", key="oc_n")
            opt_d = st.text_input("Phương án D:", value=q_edit.get('D', '') if is_editing else "", key="od_n")
            
            da_list = ["A", "B", "C", "D"]
            cur_da = q_edit.get('dap_an_dung', 'A')
            da_idx = da_list.index(cur_da) if cur_da in da_list else 0
            dap_an_dung = st.selectbox("Đáp án đúng:", da_list, index=da_idx, key="da_n")
            
        elif danh_muc == "2. Viết":
            loai_viet = st.selectbox("Chọn phân mục Viết:", ["Điền vào chỗ trống", "Trả lời câu hỏi"], key="lv_viet")
            loai_cau_hoi = f"Viết - {loai_viet}"
            noi_dung = st.text_area("Nội dung câu hỏi / Câu chứa chỗ trống:", value=q_edit.get('noi_dung', '') if is_editing else "", key="nd_viet")
            opt_a, opt_b, opt_c, opt_d = "", "", "", ""
            dap_an_dung = st.text_input("Đáp án đúng:", value=q_edit.get('dap_an_dung', '') if is_editing else "", key="da_viet")
            
        else:
            loai_cau_hoi = "Nhớ hán tự"
            noi_dung = st.text_input("Hán tự cần kiểm tra:", value=q_edit.get('noi_dung', '') if is_editing else "", key="nd_han")
            dap_an_dung = st.text_input("Nghĩa đúng:", value=q_edit.get('dap_an_dung', '') if is_editing else "", key="da_han")
            opt_a, opt_b, opt_c, opt_d = "", "", "", ""

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            btn_label = "💾 Lưu thay đổi" if is_editing else "➕ Thêm vào kho"
            if st.button(btn_label, type="primary"):
                if noi_dung and dap_an_dung:
                    new_q = {
                        "loai_cau_hoi": loai_cau_hoi,
                        "noi_dung": noi_dung.strip(),
                        "A": opt_a, "B": opt_b, "C": opt_c, "D": opt_d,
                        "dap_an_dung": dap_an_dung.strip()
                    }
                    if is_editing:
                        all_questions[st.session_state.edit_index] = new_q
                        st.session_state.edit_index = None
                        st.success("Đã cập nhật câu hỏi thành công!")
                    else:
                        all_questions.append(new_q)
                        st.success("Đã thêm vào kho thành công!")
                    
                    db.reference('questions').set(all_questions)
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Vui lòng điền đầy đủ nội dung và đáp án.")
        
        with col_btn2:
            if is_editing:
                if st.button("❌ Hủy sửa"):
                    st.session_state.edit_index = None
                    st.rerun()

        st.markdown("---")
        st.subheader("📚 Danh sách câu hỏi trong kho (Lọc theo mục)")
        
        if not all_questions:
            st.info("Kho câu hỏi đang trống.")
        else:
            filter_category = st.selectbox("📂 Chọn mục muốn xem:", ["Tất cả", "1. Nghe", "2. Viết", "3. Nhớ hán tự"])
            
            filtered_questions = []
            for original_idx, q in enumerate(all_questions):
                q_type = q.get('loai_cau_hoi', '')
                if filter_category == "Tất cả":
                    filtered_questions.append((original_idx, q))
                elif filter_category == "1. Nghe" and q_type == "Nghe":
                    filtered_questions.append((original_idx, q))
                elif filter_category == "2. Viết" and "Viết" in q_type:
                    filtered_questions.append((original_idx, q))
                elif filter_category == "3. Nhớ hán tự" and q_type == "Nhớ hán tự":
                    filtered_questions.append((original_idx, q))
            
            if not filtered_questions:
                st.info(f"Không có câu hỏi nào trong mục '{filter_category}'.")
            else:
                st.write(f"Tìm thấy **{len(filtered_questions)}** câu hỏi trong mục này:")
                for idx, q in filtered_questions:
                    nd = q.get('noi_dung') or ""
                    with st.expander(f"Câu {idx + 1} [{q.get('loai_cau_hoi')}] — {nd[:40]}..."):
                        st.write(f"**Loại:** {q.get('loai_cau_hoi')}")
                        st.write(f"**Nội dung:** {nd}")
                        if q.get('loai_cau_hoi') == "Nghe":
                            st.write(f"A. {q.get('A')} | B. {q.get('B')} | C. {q.get('C')} | D. {q.get('D')}")
                        st.write(f"**Đáp án đúng:** `{q.get('dap_an_dung')}`")
                        
                        col_q1, col_q2 = st.columns(2)
                        with col_q1:
                            if st.button("✏️ Sửa câu này", key=f"edit_btn_{idx}"):
                                st.session_state.edit_index = idx
                                st.rerun()
                        with col_q2:
                            if st.button("🗑️ Xóa câu này", key=f"del_btn_{idx}"):
                                all_questions.pop(idx)
                                db.reference('questions').set(all_questions)
                                st.success(f"Đã xóa câu hỏi số {idx + 1}!")
                                time.sleep(0.5)
                                st.rerun()

    # --- TAB 3: TẠO & CHỌN BÀI THI ---
    with tab3:
        st.subheader("📋 Tạo & Chọn bài thi từ kho câu hỏi")
        set_total_time = st.number_input("⏱️ Cài đặt tổng thời gian cho toàn bộ bài thi (giây):", min_value=30, max_value=3600, value=total_time_limit)
        
        if current_exam:
            st.success(f"✅ Đang có bài thi hiện hành gồm **{len(current_exam)} câu hỏi** (Tổng thời gian: {total_time_limit}s):")
            
            with st.expander("👁️ Xem trước chi tiết đề thi hiện tại"):
                for i, eq in enumerate(current_exam):
                    st.write(f"**Câu {i+1} [{eq.get('loai_cau_hoi')}]**: {eq.get('noi_dung')}")
                    if eq.get('loai_cau_hoi') == "Nghe":
                        st.write(f"A. {eq.get('A')} | B. {eq.get('B')} | C. {eq.get('C')} | D. {eq.get('D')}")
                    st.write(f"👉 Đáp án đúng: `{eq.get('dap_an_dung')}`")
                    st.markdown("---")
            
            for i, eq in enumerate(current_exam):
                st.write(f"{i+1}. [{eq.get('loai_cau_hoi')}] {eq.get('noi_dung')} (Đáp án: {eq.get('dap_an_dung')})")
            st.markdown("---")

        st.subheader("Chọn câu hỏi từ kho:")
        if not all_questions:
            st.info("Kho câu hỏi đang trống. Hãy thêm câu hỏi ở tab 'Kho câu hỏi' trước.")
        else:
            filter_exam_cat = st.selectbox("📂 Lọc mục để chọn câu hỏi:", ["Tất cả", "1. Nghe", "2. Viết", "3. Nhớ hán tự"], key="filter_exam_tab")
            
            selected_indices = []
            for idx, q in enumerate(all_questions):
                q_type = q.get('loai_cau_hoi', '')
                show_cond = False
                if filter_exam_cat == "Tất cả":
                    show_cond = True
                elif filter_exam_cat == "1. Nghe" and q_type == "Nghe":
                    show_cond = True
                elif filter_exam_cat == "2. Viết" and "Viết" in q_type:
                    show_cond = True
                elif filter_exam_cat == "3. Nhớ hán tự" and q_type == "Nhớ hán tự":
                    show_cond = True
                
                if show_cond:
                    nd = q.get('noi_dung') or ""
                    label = f"Câu {idx + 1} [{q_type}] — {nd[:50]}... (Đáp án: {q.get('dap_an_dung')})"
                    if st.checkbox(label, key=f"q_select_{idx}"):
                        selected_indices.append(idx)
            
            if st.button("🚀 Lưu danh sách và Tổng thời gian bài thi"):
                if selected_indices:
                    exam_list = [all_questions[i] for i in selected_indices]
                    db.reference('current_exam').set({"questions": exam_list, "total_time_limit": set_total_time})
                    ref_state.set({"status": "waiting", "start_time": 0})
                    db.reference('answers').delete()
                    db.reference('student_times').delete()
                    st.success("Đã lưu bài thi thành công!")
                    st.rerun()
                else:
                    st.warning("Vui lòng chọn ít nhất 1 câu hỏi.")

    # --- TAB 4: QUẢN LÝ HỌC SINH ---
    with tab4:
        st.subheader("👥 Quản lý danh sách học sinh được phép vào phòng")
        
        try:
            student_list_raw = db.reference('students_list').get()
        except Exception:
            student_list_raw = None
            
        if not student_list_raw:
            default_students = ["Vũ Thành Đạt"]
            db.reference('students_list').set(default_students)
            student_list = default_students
        else:
            student_list = student_list_raw

        st.write(f"Hiện tại có **{len(student_list)} học sinh** trong danh sách:")
        
        new_student_name = st.text_input("Nhập tên học sinh mới cần thêm:")
        if st.button("➕ Thêm học sinh"):
            if new_student_name.strip():
                if new_student_name.strip() not in student_list:
                    student_list.append(new_student_name.strip())
                    db.reference('students_list').set(student_list)
                    st.success(f"Đã thêm học sinh: {new_student_name.strip()}")
                    st.rerun()
                else:
                    st.warning("Học sinh này đã có trong danh sách rồi!")
            else:
                st.error("Vui lòng nhập tên hợp lệ.")
                
        st.markdown("---")
        st.write("### Danh sách hiện tại (Bấm xóa nếu muốn bớt):")
        for s_idx, s_item in enumerate(student_list):
            c_s1, c_s2 = st.columns([4, 1])
            with c_s1:
                st.write(f"- **{s_item}**")
            with c_s2:
                if st.button("🗑️ Xóa", key=f"del_student_{s_idx}"):
                    student_list.pop(s_idx)
                    db.reference('students_list').set(student_list)
                    st.success(f"Đã xóa học sinh {s_item}!")
                    time.sleep(0.3)
                    st.rerun()

    # --- TAB 5: BIỂU ĐỒ KẾT CẤU THEO TỪNG PHIÊN BÀI THI ---
    with tab5:
        st.subheader("📈 Phân tích kết cấu kết quả bài thi theo từng phiên")
        
        try:
            all_history_data = db.reference('exam_history').get() or {}
        except Exception:
            all_history_data = {}
            
        try:
            current_answers_live = db.reference('answers').get() or {}
        except Exception:
            current_answers_live = {}

        now_session_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        
        if current_answers_live and now_session_str not in all_history_data:
            all_history_data[now_session_str] = {
                "answers": current_answers_live,
                "exam": current_exam
            }

        if not all_history_data:
            st.info("Chưa có dữ liệu lịch sử bài thi nào.")
        else:
            available_sessions = sorted(list(all_history_data.keys()), reverse=True)
            selected_session = st.selectbox("📅 Chọn phiên bài thi muốn xem thống kê (Ngày_Giờ):", available_sessions)
            
            session_data = all_history_data.get(selected_session, {})
            day_answers = session_data.get("answers", {})
            day_exam = session_data.get("exam", current_exam)
            
            if not day_exam:
                st.info(f"Phiên {selected_session} không có dữ liệu đề thi cấu trúc.")
            else:
                chart_students = set()
                for c_key, c_val in day_answers.items():
                    if isinstance(c_val, dict):
                        for s_name in c_val.keys():
                            chart_students.add(s_name.strip())
                
                if not chart_students:
                    st.info(f"Không có học sinh nào nộp bài trong phiên {selected_session}.")
                else:
                    chart_data_list = []
                    for s_name in sorted(chart_students):
                        correct_c = 0
                        wrong_c = 0
                        for idx, q in enumerate(day_exam):
                            correct_ans = str(q.get('dap_an_dung', '')).strip().lower()
                            cau_ans_dict = day_answers.get(f'cau_{idx}', {})
                            
                            ans_chosen = "Chưa làm"
                            if isinstance(cau_ans_dict, dict):
                                for db_s_name, db_s_ans in cau_ans_dict.items():
                                    if db_s_name.strip() == s_name:
                                        ans_chosen = db_s_ans
                                        break
                                        
                            is_c = False
                            if ans_chosen != "Chưa làm":
                                if "Viết" in str(q.get('loai_cau_hoi', '')):
                                    if str(ans_chosen).strip().lower() in correct_ans or correct_ans in str(ans_chosen).strip().lower():
                                        is_c = True
                                elif str(ans_chosen).strip().lower() == correct_ans:
                                    is_c = True
                                    
                            if is_c:
                                correct_c += 1
                            else:
                                wrong_c += 1
                        
                        chart_data_list.append({
                            "Học sinh": s_name,
                            "Trạng thái": "Số câu Đúng",
                            "Số lượng": correct_c
                        })
                        chart_data_list.append({
                            "Học sinh": s_name,
                            "Trạng thái": "Số câu Sai",
                            "Số lượng": wrong_c
                        })
                    
                    df_plotly = pd.DataFrame(chart_data_list)
                    
                    fig = px.bar(
                        df_plotly,
                        x="Học sinh",
                        y="Số lượng",
                        color="Trạng thái",
                        barmode="group",
                        text="Số lượng",
                        color_discrete_map={"Số câu Đúng": "#2ecc71", "Số câu Sai": "#e74c3c"},
                        title=f"Kết quả phiên kiểm tra: {selected_session}"
                    )
                    fig.update_layout(
                        xaxis_title="Học sinh",
                        yaxis_title="Số câu",
                        legend_title="Kết quả",
                        font=dict(size=14)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")
                    st.subheader(f"📋 Bảng tỷ lệ chi tiết phiên {selected_session}")
                    
                    summary_table = []
                    for s_name in sorted(chart_students):
                        c_cnt = 0
                        w_cnt = 0
                        for idx, q in enumerate(day_exam):
                            correct_ans = str(q.get('dap_an_dung', '')).strip().lower()
                            cau_ans_dict = day_answers.get(f'cau_{idx}', {})
                            ans_chosen = "Chưa làm"
                            if isinstance(cau_ans_dict, dict):
                                for db_s_name, db_s_ans in cau_ans_dict.items():
                                    if db_s_name.strip() == s_name:
                                        ans_chosen = db_s_ans
                                        break
                            is_c = False
                            if ans_chosen != "Chưa làm":
                                if "Viết" in str(q.get('loai_cau_hoi', '')):
                                    if str(ans_chosen).strip().lower() in correct_ans or correct_ans in str(ans_chosen).strip().lower():
                                        is_c = True
                                elif str(ans_chosen).strip().lower() == correct_ans:
                                    is_c = True
                                    
                            if is_c:
                                c_cnt += 1
                            else:
                                w_cnt += 1
                        total_q = len(day_exam)
                        pct = round(c_cnt / total_q * 100, 1) if total_q > 0 else 0
                        summary_table.append({
                            "Học sinh": s_name,
                            "Số câu Đúng": c_cnt,
                            "Số câu Sai": w_cnt,
                            "Tổng câu": total_q,
                            "Tỷ lệ Đúng (%)": f"{pct}%"
                        })
                    st.dataframe(pd.DataFrame(summary_table), use_container_width=True)
            
            with st.expander("⚙️ Tùy chọn quản lý dữ liệu lịch sử"):
                if st.button("🔄 Xóa sạch phiên bài thi đang chọn"):
                    db.reference(f'exam_history/{selected_session}').delete()
                    st.success(f"Đã xóa dữ liệu của phiên {selected_session}!")
                    st.rerun()

# ================= VAI TRÒ: HỌC SINH =================
elif role == "Học sinh":
    st.header("📱 Màn hình làm bài của Học sinh")
    
    try:
        student_list_db = db.reference('students_list').get()
    except Exception:
        student_list_db = None
        
    VALID_STUDENTS = student_list_db if student_list_db else ["Vũ Thành Đạt"]

    if 'student_name' not in st.session_state:
        st.session_state.student_name = ""

    if not st.session_state.student_name:
        st.info("Vui lòng chọn đúng họ và tên của bạn trong danh sách để vào phòng thi.")
        
        selected_input_name = st.selectbox("Chọn họ và tên của em:", ["-- Chọn tên của bạn --"] + VALID_STUDENTS)
        
        if st.button("🚪 Vào phòng"):
            if selected_input_name != "-- Chọn tên của bạn --":
                st.session_state.student_name = selected_input_name
                st.rerun()
            else:
                st.warning("Vui lòng chọn đúng tên của bạn trong danh sách!")
    else:
        student_name = st.session_state.student_name
        
        col_name, col_btn = st.columns([3, 1])
        with col_name:
            st.success(f"Xin chào học sinh: **{student_name}**")
        with col_btn:
            if st.button("🔄 Đổi tên"):
                st.session_state.student_name = ""
                st.rerun()

        try:
            exam_raw = db.reference('current_exam').get()
        except Exception:
            exam_raw = None

        if isinstance(exam_raw, dict):
            current_exam = [q for q in exam_raw.get("questions", []) if q is not None and isinstance(q, dict)]
            total_time_limit = exam_raw.get("total_time_limit", 300)
        elif isinstance(exam_raw, list):
            current_exam = [q for q in exam_raw if q is not None and isinstance(q, dict)]
            total_time_limit = 300
        else:
            current_exam = []
            total_time_limit = 300
            
        try:
            questions_raw = db.reference('questions').get()
        except Exception:
            questions_raw = None

        if isinstance(questions_raw, list):
            all_questions = [q for q in questions_raw if q is not None and isinstance(q, dict)]
        elif isinstance(questions_raw, dict):
            all_questions = [v for v in questions_raw.values() if isinstance(v, dict)]
        else:
            all_questions = []
            
        ref_state = db.reference('game_state')
        try:
            current_state = ref_state.get() or {"status": "waiting", "start_time": 0}
        except Exception:
            current_state = {"status": "waiting", "start_time": 0}
            
        status = current_state.get("status", "waiting")
        start_time = current_state.get("start_time", 0)
        
        session_key_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        
        if not current_exam:
            st.warning("⏳ Thầy giáo chưa mở bài thi nào.")
        elif status == "waiting":
            st.info("⏳ Thầy giáo chưa bắt đầu bài thi. Hãy đợi chút nhé...")
        elif status == "finished":
            st.success("🎉 Bài kiểm tra đã kết thúc! Cảm ơn các em.")
        else:
            elapsed = time.time() - start_time
            remaining = int(total_time_limit - elapsed)
            
            if remaining <= 0:
                st.warning("⏰ Đã hết tổng thời gian làm bài!")
            else:
                st.info(f"⏱️ Tổng thời gian còn lại của bài thi: khoảng {remaining // 60} phút {remaining % 60} giây")
                st.markdown("---")
                
                if 'student_han_tu_options_dict' not in st.session_state:
                    st.session_state.student_han_tu_options_dict = {}

                if 'saved_student_answers' not in st.session_state:
                    st.session_state.saved_student_answers = {}

                ITEMS_PER_PAGE = 5
                total_questions = len(current_exam)
                total_pages = (total_questions - 1) // ITEMS_PER_PAGE + 1

                if 'current_page' not in st.session_state:
                    st.session_state.current_page = 0

                st.markdown(f"<h4 style='text-align: center;'>Trang {st.session_state.current_page + 1} / {total_pages}</h4>", unsafe_allow_html=True)
                
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    if st.button("⬅️ Trang trước", use_container_width=True, key="top_prev") and st.session_state.current_page > 0:
                        st.session_state.current_page -= 1
                        st.rerun()
                with col_p2:
                    if st.button("Trang sau ➡️", use_container_width=True, key="top_next") and st.session_state.current_page < total_pages - 1:
                        st.session_state.current_page += 1
                        st.rerun()

                st.markdown("---")

                start_idx = st.session_state.current_page * ITEMS_PER_PAGE
                end_idx = min(start_idx + ITEMS_PER_PAGE, total_questions)

                page_questions = current_exam[start_idx:end_idx]

                for i, q in enumerate(page_questions):
                    q_idx = start_idx + i
                    loai = q.get('loai_cau_hoi', '')
                    st.markdown(f"#### Câu hỏi {q_idx + 1} / {total_questions} [{loai}]")
                    
                    if loai == "Nhớ hán tự" and q_idx not in st.session_state.student_han_tu_options_dict:
                        wrong_options = [item.get('dap_an_dung') for item in all_questions if item.get('loai_cau_hoi') == "Nhớ hán tự" and item.get('dap_an_dung') != q.get('dap_an_dung')]
                        if len(wrong_options) < 3:
                            extra_options = [item.get('dap_an_dung') for item in all_questions if item.get('dap_an_dung') != q.get('dap_an_dung')]
                            wrong_options.extend(extra_options)
                        
                        selected_wrongs = random.sample(wrong_options, min(3, len(wrong_options))) if wrong_options else ["Sai 1", "Sai 2", "Sai 3"]
                        options = selected_wrongs + [q.get('dap_an_dung', '')]
                        random.shuffle(options)
                        
                        st.session_state.student_han_tu_options_dict[q_idx] = {
                            "A": options[0] if len(options) > 0 else "",
                            "B": options[1] if len(options) > 1 else "",
                            "C": options[2] if len(options) > 2 else "",
                            "D": options[3] if len(options) > 3 else ""
                        }

                    previous_val = st.session_state.saved_student_answers.get(q_idx, None)

                    choice_value = None
                    if loai == "Nghe":
                        st.info(f"🎧 {q.get('noi_dung', '')}")
                        opt_list = ["A", "B", "C", "D"]
                        
                        default_idx = None
                        if previous_val in opt_list:
                            default_idx = opt_list.index(previous_val)
                            
                        choice_key = st.radio(
                            "Chọn đáp án:", 
                            opt_list, 
                            index=default_idx, 
                            key=f"s_ans_{q_idx}", 
                            format_func=lambda x: f"{x}. {q.get(x, '')}"
                        )
                        choice_value = choice_key if previous_val in opt_list or st.session_state.get(f"s_ans_{q_idx}") else None

                    elif loai.startswith("Viết"):
                        st.markdown(f"<h3 style='color: #b22222;'>{q.get('noi_dung', '')}</h3>", unsafe_allow_html=True)
                        default_text = previous_val if previous_val else ""
                        choice_value = st.text_input("Nhập câu trả lời của em:", value=default_text, key=f"s_ans_{q_idx}")

                    elif loai == "Nhớ hán tự":
                        st.markdown(f"<h1 style='text-align: center; color: #b22222; font-size: 50px;'>{q.get('noi_dung', '')}</h1>", unsafe_allow_html=True)
                        han_opts = st.session_state.student_han_tu_options_dict[q_idx]
                        
                        opt_keys = ["A", "B", "C", "D"]
                        default_han_idx = None
                        for k in opt_keys:
                            if han_opts[k] == previous_val:
                                default_han_idx = opt_keys.index(k)
                                break

                        choice_key = st.radio(
                            "Chọn nghĩa đúng của Hán tự:", 
                            opt_keys, 
                            index=default_han_idx, 
                            key=f"s_ans_{q_idx}", 
                            format_func=lambda x: f"{x}. {han_opts[x]}"
                        )
                        
                        selected_choice_key = st.session_state.get(f"s_ans_{q_idx}")
                        choice_value = han_opts[selected_choice_key] if selected_choice_key in opt_keys else None
                    
                    st.session_state.saved_student_answers[q_idx] = choice_value
                    st.markdown("---")

                # --- ĐIỀU HƯỚNG TRANG & NỘP BÀI Ở BÊN DƯỚI ---
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("⬅️ Trang trước", use_container_width=True, key="bot_prev") and st.session_state.current_page > 0:
                        st.session_state.current_page -= 1
                        st.rerun()
                with col_b2:
                    if st.button("Trang sau ➡️", use_container_width=True, key="bot_next") and st.session_state.current_page < total_pages - 1:
                        st.session_state.current_page += 1
                        st.rerun()

                st.markdown("---")

                if st.button("📤 Nộp bài chính thức", type="primary", use_container_width=True):
                    has_empty = False
                    for idx in range(total_questions):
                        val = st.session_state.saved_student_answers.get(idx, None)
                        if val is None or (isinstance(val, str) and not val.strip()):
                            has_empty = True
                            break
                    
                    for idx in range(total_questions):
                        val = st.session_state.saved_student_answers.get(idx, None)
                        if val is not None and str(val).strip():
                            db.reference(f'answers/cau_{idx}/{student_name}').set(str(val).strip())
                    
                    current_live_answers = db.reference('answers').get() or {}
                    db.reference(f'exam_history/{session_key_str}').set({
                        "answers": current_live_answers,
                        "exam": current_exam
                    })
                    
                    db.reference(f'student_times/{student_name}').set(time.time())
                    
                    st.balloons()
                    st.success("🎉 Bạn đã hoàn thành bài thi của lớp học Hắc Ám!")
                    if has_empty:
                        st.warning("⚠️ Lưu ý: Bài làm của em còn một số câu đang để trống. Em có thể bấm lật trang để kiểm tra và bổ sung nhé.")
