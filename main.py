import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import streamlit as st


STUDENT_ID = "2023204023"
STUDENT_NAME = "권기욱"
BASE_DIR = Path(__file__).resolve().parent
QUIZ_PATH = BASE_DIR / "data" / "quiz_data.json"


st.set_page_config(
    page_title="권기욱의 음악 퀴즈",
    page_icon="🎵",
    layout="centered",
)


st.markdown(
    """
    <style>
    .student-card {
        padding: 1.2rem 1.4rem;
        border: 1px solid #d8e2dc;
        border-radius: 8px;
        background: #f8fbfa;
        margin-bottom: 1.2rem;
    }
    .student-card h1 {
        font-size: 1.9rem;
        margin: 0 0 0.6rem 0;
        letter-spacing: 0;
    }
    .student-info {
        display: flex;
        gap: 0.7rem;
        flex-wrap: wrap;
        color: #234;
        font-weight: 600;
    }
    .student-info span {
        border: 1px solid #c8d6cf;
        border-radius: 6px;
        padding: 0.38rem 0.62rem;
        background: white;
    }
    .cache-note {
        border-left: 4px solid #4d908e;
        padding: 0.75rem 0.9rem;
        background: #f3faf8;
        border-radius: 6px;
        margin: 0.6rem 0 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@st.cache_resource
def get_user_store() -> dict:
    """앱 실행 중 회원 정보를 보관하는 캐시 저장소입니다."""
    return {"users": {}}


@st.cache_resource
def get_answer_cache() -> dict:
    """사용자가 문제를 이동해도 답안이 남아 있게 하는 캐시 저장소입니다."""
    return {}


@st.cache_data(show_spinner="퀴즈 데이터를 캐시로 불러오는 중입니다...")
def load_quiz_data(path_text: str, file_version: float) -> list[dict]:
    """JSON 퀴즈 데이터를 읽고 캐시에 저장합니다."""
    del file_version
    with open(path_text, "r", encoding="utf-8") as quiz_file:
        return json.load(quiz_file)


def init_session_state() -> None:
    defaults = {
        "logged_in": False,
        "username": "",
        "current_question": 0,
        "show_result": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def normalize_text(value: str) -> str:
    value = value.lower().strip()
    return re.sub(r"[\s,./\\|·ㆍ:;!?()\[\]{}]+", "", value)


def is_short_answer_correct(question: dict, user_answer: str) -> bool:
    normalized_answer = normalize_text(user_answer)
    if not normalized_answer:
        return False

    if "accepted_groups" in question:
        return all(
            any(normalize_text(keyword) in normalized_answer for keyword in group)
            for group in question["accepted_groups"]
        )

    accepted_answers = question.get("accepted_answers", [])
    return any(normalize_text(answer) == normalized_answer for answer in accepted_answers)


def is_multiple_choice_correct(question: dict, user_answer: str) -> bool:
    if not user_answer:
        return False
    selected_number = user_answer.split(".", 1)[0].strip()
    return selected_number == str(question["correct_option"])


def evaluate_answers(quiz_data: list[dict], user_answers: dict) -> list[dict]:
    results = []
    for question in quiz_data:
        user_answer = user_answers.get(question["id"], "")
        if question["type"] == "multiple_choice":
            is_correct = is_multiple_choice_correct(question, user_answer)
        else:
            is_correct = is_short_answer_correct(question, user_answer)

        results.append(
            {
                "문항": question["id"].upper(),
                "내 답안": user_answer if user_answer else "미응답",
                "정답": question["correct_display"],
                "점수": question["points"] if is_correct else 0,
                "결과": "정답" if is_correct else "오답",
            }
        )
    return results


def render_student_header() -> None:
    st.markdown(
        f"""
        <div class="student-card">
            <h1>음악 기초 상식 퀴즈</h1>
            <div class="student-info">
                <span>학번: {STUDENT_ID}</span>
                <span>이름: {STUDENT_NAME}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login_area() -> None:
    user_store = get_user_store()
    users = user_store["users"]

    if st.session_state.logged_in:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"{st.session_state.username}님으로 로그인 중입니다.")
        with col2:
            if st.button("로그아웃", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.current_question = 0
                st.session_state.show_result = False
                st.rerun()
        return

    login_tab, signup_tab = st.tabs(["로그인", "회원가입"])

    with login_tab:
        login_id = st.text_input("아이디", key="login_id")
        login_password = st.text_input("비밀번호", type="password", key="login_password")

        if st.button("로그인하기", use_container_width=True):
            saved_user = users.get(login_id)
            if saved_user and saved_user["password_hash"] == hash_password(login_password):
                st.session_state.logged_in = True
                st.session_state.username = login_id
                st.session_state.current_question = 0
                st.session_state.show_result = False
                st.success("로그인에 성공했습니다.")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

    with signup_tab:
        new_id = st.text_input("새 아이디", key="signup_id")
        new_password = st.text_input("새 비밀번호", type="password", key="signup_password")
        confirm_password = st.text_input(
            "비밀번호 확인", type="password", key="signup_password_confirm"
        )

        if st.button("회원가입하기", use_container_width=True):
            if len(new_id.strip()) < 3:
                st.warning("아이디는 3글자 이상 입력하세요.")
            elif new_id in users:
                st.warning("이미 존재하는 아이디입니다.")
            elif len(new_password) < 4:
                st.warning("비밀번호는 4글자 이상 입력하세요.")
            elif new_password != confirm_password:
                st.warning("비밀번호 확인이 일치하지 않습니다.")
            else:
                users[new_id] = {
                    "password_hash": hash_password(new_password),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                st.success("회원가입이 완료되었습니다. 로그인 탭에서 로그인하세요.")


def render_cache_explanation(username: str) -> None:
    answer_cache = get_answer_cache()
    saved_count = len(answer_cache.get(username, {}))

    st.markdown(
        f"""
        <div class="cache-note">
            <strong>캐싱 사용 위치</strong><br>
            퀴즈 데이터는 <code>st.cache_data</code>로 JSON 파일을 한 번 읽은 뒤 재사용합니다.<br>
            풀이 중 입력한 답안은 <code>st.cache_resource</code> 저장소에 임시 저장되어
            이전 문제로 돌아가도 유지됩니다. 현재 저장된 답안 수: <strong>{saved_count}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def save_current_answer(username: str, question_id: str, answer: str | None) -> None:
    answer_cache = get_answer_cache()
    user_answers = answer_cache.setdefault(username, {})
    user_answers[question_id] = answer or ""


def render_quiz(quiz_data: list[dict]) -> None:
    username = st.session_state.username
    answer_cache = get_answer_cache()
    user_answers = answer_cache.setdefault(username, {})
    question_index = st.session_state.current_question
    question = quiz_data[question_index]
    question_id = question["id"]

    render_cache_explanation(username)

    st.progress((question_index + 1) / len(quiz_data))
    st.subheader(f"{question_index + 1}번 문제")
    st.write(f"{question['question']} ({question['points']}점)")

    widget_key = f"answer_{username}_{question_id}"
    stored_answer = user_answers.get(question_id, "")

    if question["type"] == "multiple_choice":
        options = [
            f"{number}. {text}"
            for number, text in enumerate(question["options"], start=1)
        ]
        if widget_key not in st.session_state and stored_answer in options:
            st.session_state[widget_key] = stored_answer
        selected_answer = st.radio(
            "정답을 선택하세요.",
            options,
            key=widget_key,
            index=None,
        )
    else:
        if widget_key not in st.session_state:
            st.session_state[widget_key] = stored_answer
        selected_answer = st.text_input(
            "정답을 입력하세요.",
            key=widget_key,
            placeholder=question.get("placeholder", ""),
        )

    save_current_answer(username, question_id, selected_answer)

    left, center, right = st.columns(3)
    with left:
        if st.button("이전 문제", disabled=question_index == 0, use_container_width=True):
            st.session_state.current_question -= 1
            st.session_state.show_result = False
            st.rerun()
    with center:
        if st.button("답안 저장", use_container_width=True):
            st.toast("현재 답안이 캐시에 저장되었습니다.")
    with right:
        if st.button(
            "다음 문제",
            disabled=question_index == len(quiz_data) - 1,
            use_container_width=True,
        ):
            st.session_state.current_question += 1
            st.session_state.show_result = False
            st.rerun()

    st.divider()
    col1, col2 = st.columns([2, 1])
    with col1:
        answered_count = sum(1 for answer in user_answers.values() if answer)
        st.caption(f"답변 완료: {answered_count}/{len(quiz_data)}문항")
    with col2:
        if st.button("결과 확인", type="primary", use_container_width=True):
            st.session_state.show_result = True

    if st.session_state.show_result:
        render_result(quiz_data, user_answers)


def render_result(quiz_data: list[dict], user_answers: dict) -> None:
    details = evaluate_answers(quiz_data, user_answers)
    total_score = sum(item["점수"] for item in details)
    max_score = sum(question["points"] for question in quiz_data)

    st.subheader("최종 결과")
    st.metric("총점", f"{total_score} / {max_score}점")

    if total_score == max_score:
        st.success("만점입니다. 음악 기초 개념을 아주 정확히 알고 있습니다.")
    elif total_score >= 60:
        st.info("좋습니다. 틀린 문항만 다시 확인하면 더 탄탄해질 수 있습니다.")
    else:
        st.warning("기초 용어와 장르 개념을 한 번 더 복습해 보세요.")

    st.dataframe(details, hide_index=True, use_container_width=True)

    if st.button("처음부터 다시 풀기"):
        username = st.session_state.username
        answer_cache = get_answer_cache()
        answer_cache[username] = {}
        for question in quiz_data:
            widget_key = f"answer_{username}_{question['id']}"
            if widget_key in st.session_state:
                del st.session_state[widget_key]
        st.session_state.current_question = 0
        st.session_state.show_result = False
        st.rerun()


def main() -> None:
    init_session_state()
    render_student_header()

    quiz_version = QUIZ_PATH.stat().st_mtime
    quiz_data = load_quiz_data(str(QUIZ_PATH), quiz_version)

    st.write(
        "회원가입 후 로그인하면 5문항 음악 퀴즈를 풀 수 있습니다. "
        "각 문제는 20점이며 총점은 100점입니다."
    )

    render_login_area()

    if st.session_state.logged_in:
        st.divider()
        render_quiz(quiz_data)
    else:
        st.info("퀴즈를 시작하려면 먼저 회원가입 또는 로그인을 진행하세요.")


if __name__ == "__main__":
    main()
