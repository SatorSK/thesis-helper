"""M4. 데이터 분석 (혼합형 보조).

CSV 업로드 → 기초통계·추세·비교 그래프. 그래프를 figures/ 에 저장하고
"데이터가 말하는 사실" 요약을 자동 생성(해석은 사용자 몫).
본인이 직접 돌린 분석 = 표절률 0 구간.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")  # 서버 환경용 비대화형 백엔드
import matplotlib.pyplot as plt  # noqa: E402

# 한글 폰트(있으면 사용, 없으면 기본)
for _f in ["Malgun Gothic", "AppleGothic", "NanumGothic"]:
    try:
        matplotlib.rcParams["font.family"] = _f
        break
    except Exception:
        continue
matplotlib.rcParams["axes.unicode_minus"] = False


def auto_summary(df, x_col, y_cols) -> str:
    """데이터 사실 요약(해석 아님). 첫 y열의 변화율·최대최소만 사실로 기술."""
    lines = []
    for y in y_cols:
        s = df[y].dropna()
        if len(s) < 2:
            continue
        first, last = s.iloc[0], s.iloc[-1]
        if first != 0:
            chg = (last - first) / abs(first) * 100
            lines.append(
                f"{y}: 기간 처음 {first:,.1f} → 마지막 {last:,.1f} ({chg:+.1f}%), "
                f"최대 {s.max():,.1f} / 최소 {s.min():,.1f}."
            )
        else:
            lines.append(f"{y}: 최대 {s.max():,.1f} / 최소 {s.min():,.1f}.")
    return "\n".join(lines) or "요약할 수치 없음."


def render(project, cfg):
    import streamlit as st
    import pandas as pd
    from core import project as P

    st.header("④ 데이터 분석 (보조)")
    st.caption("본인이 직접 돌린 분석은 표절률 0입니다. 그래프의 '사실'은 도구가, '해석'은 본인이.")
    st.info("추천 출처: UN Comtrade(품목별 무역), KITA 무역통계, 한국은행 ECOS(환율). 모두 공개·합법.")

    up = st.file_uploader("CSV 업로드", type=["csv"])
    if up is None:
        st.stop()

    try:
        df = pd.read_csv(up)
    except Exception:
        up.seek(0)
        df = pd.read_csv(up, encoding="cp949")  # 국내 데이터 흔한 인코딩

    st.subheader("미리보기")
    st.dataframe(df.head(20), use_container_width=True)
    st.markdown("**기초 통계**")
    st.dataframe(df.describe(include="all").T, use_container_width=True)

    cols = list(df.columns)
    x_col = st.selectbox("X축 (예: 연도)", cols)
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    y_cols = st.multiselect("Y축 (수치, 복수 선택 가능)", num_cols, default=num_cols[:1])
    chart = st.selectbox("그래프", ["line", "bar"])

    if y_cols and st.button("그래프 생성", type="primary"):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for y in y_cols:
            if chart == "line":
                ax.plot(df[x_col], df[y], marker="o", label=y)
            else:
                ax.bar(df[x_col].astype(str), df[y], label=y, alpha=0.7)
        ax.set_xlabel(x_col)
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        st.pyplot(fig)

        fdir = P.figures_dir(project["name"], project.get("space", "_default"))
        idx = len(project.get("data_notes", [])) + 1
        fpath = os.path.join(fdir, f"figure_{idx}.png")
        fig.savefig(fpath, dpi=150, bbox_inches="tight")
        plt.close(fig)

        summary = auto_summary(df, x_col, y_cols)
        st.markdown("**데이터가 말하는 사실 (해석 아님):**")
        st.code(summary)

        caption = st.text_input("그림 캡션", value=f"[그림 {idx}] {', '.join(y_cols)}의 {x_col}별 추이")
        if st.button("이 그림을 논문에 저장"):
            project.setdefault("data_notes", []).append({
                "title": caption,
                "caption": caption,
                "figure_file": fpath,
                "summary": summary,
            })
            P.save(project)
            st.success("저장됨 (M7 내보내기에 포함)")

    notes = project.get("data_notes", [])
    if notes:
        st.divider()
        st.subheader(f"저장된 그림/표 {len(notes)}개")
        for i, n in enumerate(notes):
            st.markdown(f"**{n['caption']}**")
            if os.path.isfile(n.get("figure_file", "")):
                st.image(n["figure_file"], width=400)
            st.code(n.get("summary", ""))
            if st.button("삭제", key=f"del_fig_{i}"):
                project["data_notes"].pop(i)
                P.save(project)
                st.rerun()
