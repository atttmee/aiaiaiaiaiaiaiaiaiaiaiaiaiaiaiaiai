from pathlib import Path
import re

import pandas as pd
import streamlit as st
import plotly.express as px

# ======================================
# 1. 기본 설정
# ======================================
st.set_page_config(
    page_title="철도 데이터 분석 대시보드",
    page_icon="🚆",
    layout="wide"
)

DATA_PATH = Path(
    "/content/drive/MyDrive/"
    "데이터분석 엔지니어링(26.10.19)/"
    "analysis_result.csv"
)

# ======================================
# 2. 데이터 읽기 및 정리
# ======================================
@st.cache_data(show_spinner=False)
def load_data(path, modified_time):
    data = pd.read_csv(
        path,
        dtype={"설비ID": "string"}
    )

    required = [
        "설비ID", "측정시각", "목표시각",
        "온도_C", "Ai결과",
        "다음온도_C", "AI예측온도_C"
    ]

    missing = [
        column for column in required
        if column not in data.columns
    ]

    if missing:
        raise ValueError(
            "필수 열 누락: " + ", ".join(missing)
        )

    data["설비ID"] = (
        data["설비ID"]
        .str.strip()
        .replace("", pd.NA)
    )

    data["Ai결과"] = (
        data["Ai결과"]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

    for column in ["측정시각", "목표시각"]:
        data[column] = pd.to_datetime(
            data[column],
            errors="coerce"
        )

    for column in [
        "온도_C",
        "다음온도_C",
        "AI예측온도_C"
    ]:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        ).replace(
            [float("inf"), float("-inf")],
            float("nan")
        )

    valid = (
        data["설비ID"].notna()
        & data["측정시각"].notna()
    )

    excluded_count = int((~valid).sum())

    return (
        data.loc[valid]
        .sort_values("측정시각")
        .copy(),
        excluded_count
    )


def csv_bytes(data):
    return data.to_csv(index=False).encode("utf-8-sig")


def display_chart(fig):
    fig.update_layout(
        height=380,
        hovermode="x unified",
        legend_title_text="",
        margin=dict(l=10, r=10, t=25, b=10)
    )
    st.plotly_chart(fig, width="stretch")


def save_note(saved_key, input_key):
    st.session_state[saved_key] = (
        st.session_state[input_key]
    )


# ======================================
# 3. 제목
# ======================================
st.title("철도 데이터 분석 대시보드")
st.caption(
    "교육용 가상 자료입니다. "
    "AI 확인후보는 고장 확정이 아니며 담당자 검토가 필요합니다."
)

try:
    df, excluded_count = load_data(
        str(DATA_PATH),
        DATA_PATH.stat().st_mtime_ns
    )
except Exception as error:
    st.error(f"데이터를 불러오지 못했습니다: {error}")
    st.info(
        "Google Drive 연결 상태와 "
        "DATA_PATH의 CSV 경로를 확인하세요."
    )
    st.stop()

if df.empty:
    st.warning("조회 가능한 설비·측정시각 자료가 없습니다.")
    st.stop()

# ======================================
# 4. 조회 조건
# 달력을 항상 표시
# ======================================
with st.container(border=True):
    st.subheader("조회 조건")

    equipment_col, start_col, end_col = st.columns(
        [1.2, 1, 1]
    )

    with equipment_col:
        equipment = st.selectbox(
            "설비 선택",
            sorted(
                df["설비ID"].dropna().unique().tolist()
            )
        )

    equipment_df = df.loc[
        df["설비ID"] == equipment
    ].copy()

    min_date = equipment_df["측정시각"].min().date()
    max_date = equipment_df["측정시각"].max().date()

    # 설비·데이터 기간이 변경되면 날짜 상태를 초기화
    scope = f"{equipment}_{min_date}_{max_date}"
    start_key = f"start_{scope}"
    end_key = f"end_{scope}"

    if start_key not in st.session_state:
        st.session_state[start_key] = min_date

    if end_key not in st.session_state:
        st.session_state[end_key] = max_date

    # 시작일 달력
    with start_col:
        start = st.date_input(
            "시작일",
            min_value=min_date,
            max_value=max_date,
            key=start_key,
            format="YYYY/MM/DD"
        )

    if start is None:
        st.info("시작일을 선택하세요.")
        st.stop()

    # 시작일을 종료일보다 뒤로 옮긴 경우 종료일 보정
    if (
        st.session_state[end_key] is None
        or st.session_state[end_key] < start
    ):
        st.session_state[end_key] = start

    # 종료일 달력
    with end_col:
        end = st.date_input(
            "종료일",
            min_value=start,
            max_value=max_date,
            key=end_key,
            format="YYYY/MM/DD"
        )

    if end is None:
        st.info("종료일을 선택하세요.")
        st.stop()

    info_col, refresh_col = st.columns([4, 1])

    info_col.caption(
        f"선택 설비의 데이터 기간: "
        f"{min_date:%Y-%m-%d} ~ {max_date:%Y-%m-%d} "
        "｜ 이 범위 밖 날짜는 선택할 수 없습니다."
    )

    if refresh_col.button(
        "데이터 새로고침",
        width="stretch"
    ):
        load_data.clear()
        st.rerun()

# ======================================
# 5. 조회 데이터 생성
# ======================================
view = equipment_df.loc[
    (
        equipment_df["측정시각"]
        >= pd.Timestamp(start)
    )
    & (
        equipment_df["측정시각"]
        < pd.Timestamp(end) + pd.Timedelta(days=1)
    )
].copy()

if view.empty:
    st.warning(
        "선택한 기간에는 측정 자료가 없습니다. "
        "달력에서 조회 기간을 변경하세요."
    )
    st.stop()

candidate_mask = (
    view["Ai결과"]
    .eq("확인후보")
    .fillna(False)
)

candidates = view.loc[candidate_mask].copy()
candidate_rate = len(candidates) / len(view) * 100

latest = view.iloc[-1]

latest_temperature = (
    f"{latest['온도_C']:.1f} ℃"
    if pd.notna(latest["온도_C"])
    else "결측"
)

# 정확히 1시간 뒤의 예측만 분석
one_hour_mask = (
    view["목표시각"] - view["측정시각"]
).eq(pd.Timedelta(hours=1))

forecast = (
    view.loc[
        one_hour_mask
        & view["AI예측온도_C"].notna()
    ]
    .sort_values("목표시각")
    .copy()
)

pred = forecast.dropna(
    subset=["다음온도_C", "AI예측온도_C"]
).copy()

if not pred.empty:
    absolute_error = (
        pred["다음온도_C"]
        - pred["AI예측온도_C"]
    ).abs()

    mae_text = f"{absolute_error.mean():.2f} ℃"
else:
    mae_text = "산출 불가"

invalid_forecast_count = int(
    (
        view["AI예측온도_C"].notna()
        & ~one_hour_mask
    ).sum()
)

# ======================================
# 6. 조회 요약
# ======================================
st.caption(
    f"조회 중: {equipment} "
    f"｜ {start:%Y-%m-%d} ~ {end:%Y-%m-%d}"
)

with st.container(border=True):
    k1, k2, k3, k4 = st.columns(4)

    k1.metric("조회 자료", f"{len(view):,}행")
    k2.metric("AI 확인후보", f"{len(candidates):,}건")
    k3.metric("확인후보 비율", f"{candidate_rate:.1f}%")
    k4.metric("마지막 측정 온도", latest_temperature)

    st.caption(
        f"마지막 측정: "
        f"{latest['측정시각']:%Y-%m-%d %H:%M} "
        "｜ 확인후보 건수·비율은 행 기준입니다."
    )

# ======================================
# 7. 기존 3개 탭 유지
# ======================================
tab1, tab2, tab3 = st.tabs([
    "AI 점검 후보",
    "다음 1시간 온도 예측",
    "업무 검토 및 저장"
])

# ======================================
# TAB 1. AI 점검 후보
# ======================================
with tab1:
    if candidates.empty:
        st.info("선택 기간에 AI 확인후보가 없습니다.")
    else:
        st.warning(
            f"확인후보 {len(candidates):,}건이 있습니다. "
            "아래 그래프와 상세 목록을 확인하세요."
        )

    st.subheader("온도 추이와 AI 확인후보")

    fig = px.line(
        view,
        x="측정시각",
        y="온도_C",
        labels={"온도_C": "온도 (℃)"}
    )

    fig.update_traces(
        line_color="#2563EB",
        name="측정 온도",
        showlegend=True
    )

    fig.add_scatter(
        x=candidates["측정시각"],
        y=candidates["온도_C"],
        mode="markers",
        name="확인후보",
        marker=dict(
            color="#DC2626",
            size=10,
            symbol="diamond"
        )
    )

    display_chart(fig)

    st.subheader("점검 후보 상세")

    candidate_columns = [
        "측정시각", "설비ID", "온도_C",
        "Ai결과", "목표시각", "AI예측온도_C"
    ]

    st.dataframe(
        candidates.sort_values(
            "측정시각",
            ascending=False
        )[candidate_columns],
        hide_index=True,
        width="stretch",
        height=280
    )

    st.caption(
        "최근 측정순으로 표시합니다. "
        "온도가 없는 후보는 표에 포함되지만 "
        "그래프의 점으로 표시되지 않습니다."
    )

    with st.expander("AI 분석 결과별 건수"):
        counts = (
            view["Ai결과"]
            .fillna("미기록")
            .value_counts()
            .rename_axis("AI 결과")
            .reset_index(name="건수")
        )

        st.dataframe(
            counts,
            hide_index=True,
            width="stretch"
        )

# ======================================
# TAB 2. 다음 1시간 온도 예측
# ======================================
with tab2:
    st.subheader("실제 온도와 AI 예측 온도")

    if invalid_forecast_count:
        st.warning(
            f"목표시각이 없거나 예측 간격이 1시간이 아닌 "
            f"{invalid_forecast_count:,}건은 분석에서 제외했습니다. "
            "추가 확인 필요."
        )

    if forecast.empty:
        st.info(
            "선택 기간에 유효한 1시간 예측 자료가 없습니다."
        )
    else:
        with st.container(border=True):
            p1, p2, p3 = st.columns(3)

            p1.metric("평균 절대 오차(MAE)", mae_text)
            p2.metric("실제값 비교 가능", f"{len(pred):,}건")
            p3.metric(
                "실제값 없음",
                f"{len(forecast) - len(pred):,}건"
            )

        chart_data = forecast.rename(columns={
            "다음온도_C": "실제 온도",
            "AI예측온도_C": "AI 예측 온도"
        })

        fig2 = px.line(
            chart_data,
            x="목표시각",
            y=["실제 온도", "AI 예측 온도"],
            markers=True,
            labels={
                "value": "온도 (℃)",
                "variable": "구분"
            },
            color_discrete_map={
                "실제 온도": "#2563EB",
                "AI 예측 온도": "#F59E0B"
            }
        )

        display_chart(fig2)

        st.caption(
            "조회 기간은 측정시각 기준, 그래프는 목표시각 기준입니다. "
            "실제값이 없는 예측도 표시하며, "
            "MAE는 실제값과 예측값이 모두 있는 자료로 계산합니다."
        )

        with st.expander("예측 상세 및 오차"):
            detail = forecast[[
                "측정시각", "목표시각",
                "다음온도_C", "AI예측온도_C"
            ]].copy()

            detail["절대오차_C"] = (
                detail["다음온도_C"]
                - detail["AI예측온도_C"]
            ).abs()

            st.dataframe(
                detail.sort_values(
                    "목표시각",
                    ascending=False
                ),
                hide_index=True,
                width="stretch"
            )

# ======================================
# TAB 3. 업무 검토 및 저장
# ======================================
with tab3:
    memo_col, preview_col = st.columns([1, 1.2])

    note_scope = f"{equipment}_{start}_{end}"
    saved_key = f"saved_note_{note_scope}"
    input_key = f"input_note_{note_scope}"

    if saved_key not in st.session_state:
        st.session_state[saved_key] = (
            "센서 상태와 운전 조건을 확인한 후 "
            "담당자 검토가 필요합니다."
        )

    if input_key not in st.session_state:
        st.session_state[input_key] = (
            st.session_state[saved_key]
        )

    with memo_col:
        st.subheader("업무 검토")

        note = st.text_area(
            "확인할 사항 및 조치 제안",
            key=input_key,
            height=220,
            on_change=save_note,
            args=(saved_key, input_key)
        )

        st.caption(
            "메모는 현재 접속 세션에서 설비·기간별로 유지됩니다. "
            "보관하려면 보고서 TXT를 내려받으세요."
        )

    report = f"""철도 데이터 분석 검토 보고서

설비: {equipment}
조회 기간(측정일 기준): {start} ~ {end}
조회 자료: {len(view):,}행
마지막 측정: {latest['측정시각']:%Y-%m-%d %H:%M}
마지막 측정 온도: {latest_temperature}

AI 확인후보: {len(candidates):,}건 (행 기준)
확인후보 비율: {candidate_rate:.1f}%

1시간 온도 예측 MAE: {mae_text}
실제값 비교 자료: {len(pred):,}건
실제값 없는 예측: {len(forecast) - len(pred):,}건
예측 간격 확인 필요: {invalid_forecast_count:,}건 (분석 제외)

업무 메모:
{note}

교육용 가상 자료입니다.
AI 확인후보는 고장 확정이 아니며 담당자 검토가 필요합니다.
"""

    with preview_col:
        st.subheader("보고서 미리보기")

        with st.container(border=True):
            st.text(report)

    safe_equipment = re.sub(
        r"[^\w가-힣.-]+",
        "_",
        str(equipment)
    )[:80]

    suffix = (
        f"{safe_equipment}_"
        f"{start:%Y%m%d}_{end:%Y%m%d}"
    )

    with memo_col:
        st.subheader("파일 다운로드")

        st.download_button(
            "조회 결과 CSV",
            data=csv_bytes(view),
            file_name=f"dashboard_{suffix}.csv",
            mime="text/csv",
            width="stretch"
        )

        st.download_button(
            "점검 후보 CSV",
            data=csv_bytes(candidates),
            file_name=f"candidates_{suffix}.csv",
            mime="text/csv",
            width="stretch"
        )

        st.download_button(
            "보고서 TXT",
            data=report.encode("utf-8-sig"),
            file_name=f"report_{suffix}.txt",
            mime="text/plain",
            width="stretch"
        )

# ======================================
# 8. 전체 조회 자료
# ======================================
st.divider()

with st.expander(
    f"전체 조회 데이터 확인 · {len(view):,}행"
):
    st.dataframe(
        view.sort_values(
            "측정시각",
            ascending=False
        ),
        hide_index=True,
        width="stretch",
        height=350
    )

    st.caption(
        "분석 지표는 전체 조회 자료로 계산합니다. "
        "중복 행은 임의로 제거하지 않습니다."
    )

if excluded_count:
    st.caption(
        f"원본 중 설비ID 또는 측정시각이 없는 "
        f"{excluded_count:,}행은 조회에서 제외했습니다."
    )
