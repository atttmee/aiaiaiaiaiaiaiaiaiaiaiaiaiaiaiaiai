from pathlib import Path
import hashlib
import re

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v2 as components

# ======================================
# 1. 화면 설정
# ======================================
st.set_page_config(
    page_title="철도 데이터 분석 대시보드",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_PATH = Path(
    "analysis_result.csv"
)

# ======================================
# 2. 전용 달력
# 데이터가 있는 날짜만 클릭 가능
# 외부 달력 패키지나 CDN을 사용하지 않음
# ======================================
CALENDAR_CSS = """
.cal {
    font-family: inherit;
    color: var(--st-text-color);
    font-size: 14px;
}
.bar, .choices {
    display: flex;
    gap: 6px;
    align-items: center;
    margin: 8px 0;
}
button, select {
    font: inherit;
    color: inherit;
    border: 1px solid #94a3b866;
    background: var(--st-secondary-background-color);
    border-radius: 7px;
    padding: 7px;
    cursor: pointer;
}
.choices button {
    flex: 1;
    font-size: 12px;
}
.active {
    outline: 2px solid #2563eb;
}
select {
    flex: 1;
    min-width: 0;
}
.grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
}
.grid button {
    padding: 7px 0;
    min-width: 0;
}
.week {
    text-align: center;
    font-size: 12px;
    opacity: .7;
    padding: 5px 0;
}
.grid button:disabled {
    opacity: .25;
    cursor: not-allowed;
    background: transparent;
}
.grid .inside {
    background: #2563eb20;
}
.grid .selected {
    background: #2563eb;
    color: white;
    border-color: #2563eb;
}
.help {
    font-size: 12px;
    opacity: .75;
    margin-top: 8px;
    line-height: 1.5;
}
"""

CALENDAR_JS = """
export default function({
    parentElement, data, setTriggerValue
}) {
    const root = parentElement.querySelector('.cal');
    const valid = new Set(data.dates);
    const months = [];

    let cursor = data.dates[0].slice(0, 7);
    const last = data.dates.at(-1).slice(0, 7);

    while (cursor <= last) {
        months.push(cursor);
        let [y, m] = cursor.split('-').map(Number);
        m++;
        if (m === 13) {
            y++;
            m = 1;
        }
        cursor = `${y}-${String(m).padStart(2, '0')}`;
    }

    let month = months.includes(root._month)
        ? root._month
        : data.start.slice(0, 7);

    let mode = root._mode || 'start';

    function draw() {
        root._month = month;
        root._mode = mode;
        root.replaceChildren();

        const choices = document.createElement('div');
        choices.className = 'choices';

        for (const [value, label] of [
            ['start', '시작일'],
            ['end', '종료일']
        ]) {
            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = label + ' ' + data[value];
            button.className = mode === value ? 'active' : '';
            button.onclick = () => {
                mode = value;
                draw();
            };
            choices.append(button);
        }

        root.append(choices);

        const bar = document.createElement('div');
        bar.className = 'bar';

        const prev = document.createElement('button');
        prev.textContent = '‹';
        prev.ariaLabel = '이전 달';

        const next = document.createElement('button');
        next.textContent = '›';
        next.ariaLabel = '다음 달';

        const select = document.createElement('select');
        select.ariaLabel = '표시할 월';

        months.forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent =
                value.replace('-', '년 ') + '월';
            select.append(option);
        });

        select.value = month;
        select.onchange = () => {
            month = select.value;
            draw();
        };

        const index = months.indexOf(month);
        prev.disabled = index === 0;
        next.disabled = index === months.length - 1;

        prev.onclick = () => {
            month = months[index - 1];
            draw();
        };
        next.onclick = () => {
            month = months[index + 1];
            draw();
        };

        bar.append(prev, select, next);
        root.append(bar);

        const grid = document.createElement('div');
        grid.className = 'grid';

        ['일', '월', '화', '수', '목', '금', '토']
            .forEach(label => {
                const cell = document.createElement('div');
                cell.className = 'week';
                cell.textContent = label;
                grid.append(cell);
            });

        const [year, monthNumber] = month.split('-').map(Number);
        const offset = new Date(
            year, monthNumber - 1, 1
        ).getDay();
        const count = new Date(
            year, monthNumber, 0
        ).getDate();

        for (let i = 0; i < offset; i++) {
            grid.append(document.createElement('span'));
        }

        for (let day = 1; day <= count; day++) {
            const iso =
                month + '-' + String(day).padStart(2, '0');

            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = day;

            // 미측정일 및 시작일 이전의 종료일 선택 차단
            button.disabled =
                !valid.has(iso)
                || (mode === 'end' && iso < data.start);

            button.title = !valid.has(iso)
                ? iso + ' · 측정 자료 없음'
                : iso;
            button.ariaLabel = button.title;

            if (iso >= data.start && iso <= data.end) {
                button.classList.add('inside');
            }
            if (iso === data.start || iso === data.end) {
                button.classList.add('selected');
            }

            button.onclick = () => {
                let start = data.start;
                let end = data.end;

                if (mode === 'start') {
                    start = iso;
                    if (end < start) end = start;
                    root._mode = 'end';
                } else {
                    end = iso;
                    root._mode = 'start';
                }

                setTriggerValue('selection', {start, end});
            };

            grid.append(button);
        }

        root.append(grid);

        const help = document.createElement('div');
        help.className = 'help';
        help.textContent =
            '시작일·종료일 버튼을 누른 뒤 날짜를 선택하세요. ' +
            '흐린 날짜는 측정 자료가 없어 선택할 수 없습니다.';
        root.append(help);
    }

    draw();
}
"""

calendar = components.component(
    "rail_data_calendar",
    html='<div class="cal"></div>',
    css=CALENDAR_CSS,
    js=CALENDAR_JS
)

# ======================================
# 3. 데이터 읽기 및 정리
# ======================================
@st.cache_data(show_spinner=False)
def load_data(path, modified_ns):
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
        data["설비ID"].str.strip().replace("", pd.NA)
    )
    data["Ai결과"] = (
        data["Ai결과"]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

    for column in ["측정시각", "목표시각"]:
        data[column] = pd.to_datetime(
            data[column], errors="coerce"
        )

    for column in [
        "온도_C", "다음온도_C", "AI예측온도_C"
    ]:
        data[column] = pd.to_numeric(
            data[column], errors="coerce"
        ).replace(
            [float("inf"), float("-inf")],
            float("nan")
        )

    valid = (
        data["설비ID"].notna()
        & data["측정시각"].notna()
    )

    return (
        data.loc[valid].sort_values("측정시각").copy(),
        int((~valid).sum())
    )


st.title("철도 데이터 분석 대시보드")
st.caption(
    "교육용 가상 자료입니다. "
    "AI 확인후보는 고장 확정이 아니며 담당자 검토가 필요합니다."
)

try:
    df, excluded = load_data(
        str(DATA_PATH),
        DATA_PATH.stat().st_mtime_ns
    )
except Exception as error:
    st.error(f"데이터를 읽지 못했습니다: {error}")
    st.info(
        "Google Drive 연결 상태와 "
        "DATA_PATH의 CSV 경로를 확인하세요."
    )
    st.stop()

if df.empty:
    st.warning("조회 가능한 자료가 없습니다.")
    st.stop()

# ======================================
# 4. 사이드바
# ======================================
with st.sidebar:
    st.header("조회 조건")

    equipment = st.selectbox(
        "설비 선택",
        sorted(df["설비ID"].unique())
    )

    source = df.loc[
        df["설비ID"] == equipment
    ].copy()

    # 선택 설비에 실제 측정 자료가 있는 날짜만 추출
    dates = sorted(
        source["측정시각"]
        .dt.strftime("%Y-%m-%d")
        .unique()
        .tolist()
    )

    token = hashlib.sha256(
        (str(equipment) + "|".join(dates)).encode()
    ).hexdigest()[:16]

    range_key = f"range_{token}"

    if range_key not in st.session_state:
        st.session_state[range_key] = (
            dates[0], dates[-1]
        )

    a, b, c = st.columns(3)
    preset = None

    if a.button("전체", width="stretch"):
        preset = 0
    if b.button("최근 7일", width="stretch"):
        preset = 7
    if c.button("최근 30일", width="stretch"):
        preset = 30

    if preset is not None:
        threshold = (
            pd.Timestamp(dates[-1])
            - pd.Timedelta(days=max(preset - 1, 0))
        )
        selected = (
            dates if preset == 0 else [
                day for day in dates
                if pd.Timestamp(day) >= threshold
            ]
        )
        st.session_state[range_key] = (
            selected[0], selected[-1]
        )

    start, end = st.session_state[range_key]

    st.caption("조회 달력 · 선택 설비의 측정일만 활성화")

    result = calendar(
        data={
            "dates": dates,
            "start": start,
            "end": end
        },
        key=f"calendar_{token}",
        on_selection_change=lambda: None
    )

    # 달력에서 전달된 값도 서버에서 다시 검증
    if result.selection:
        picked = result.selection
        selected_start = picked.get("start")
        selected_end = picked.get("end")

        if (
            selected_start in dates
            and selected_end in dates
            and selected_start <= selected_end
            and (selected_start, selected_end) != (start, end)
        ):
            st.session_state[range_key] = (
                selected_start, selected_end
            )
            st.rerun()

    st.caption(
        "최근 기간은 마지막 측정일 기준입니다. "
        "기간 중 미측정일은 분석에 포함되지 않습니다."
    )

    with st.expander("화면·목록 설정", expanded=True):
        height = st.select_slider(
            "그래프 높이",
            [300, 380, 460],
            value=380
        )
        points = st.checkbox(
            "온도선에 측정점 표시",
            value=False
        )
        sort_order = st.radio(
            "목록 정렬",
            ["최신순", "과거순"],
            horizontal=True
        )
        limit = st.selectbox(
            "표 최대 표시 행",
            [50, 100, 300, "전체"],
            index=1
        )
        show_raw = st.checkbox(
            "전체 조회 데이터 표시",
            value=True
        )
        st.caption(
            "표시 설정은 분석 수치·다운로드 범위에 "
            "영향을 주지 않습니다."
        )

    with st.expander("데이터 정보"):
        st.write(
            f"설비 수: {df['설비ID'].nunique():,}개"
        )
        st.write(
            f"유효 자료: {len(df):,}행 / "
            f"제외 자료: {excluded:,}행"
        )
        st.caption(
            "제외 자료는 설비ID 또는 측정시각이 없는 행입니다."
        )

    if st.button("데이터 새로고침", width="stretch"):
        load_data.clear()
        st.rerun()

# ======================================
# 5. 조회 데이터 및 분석 지표
# ======================================
view = source.loc[
    (source["측정시각"] >= pd.Timestamp(start))
    & (
        source["측정시각"]
        < pd.Timestamp(end) + pd.Timedelta(days=1)
    )
].copy()

if view.empty:
    st.warning("선택한 기간에 자료가 없습니다.")
    st.stop()

candidates = view.loc[
    view["Ai결과"].eq("확인후보").fillna(False)
].copy()

rate = len(candidates) / len(view) * 100

one_hour = (
    view["목표시각"] - view["측정시각"]
).eq(pd.Timedelta(hours=1))

forecast = (
    view.loc[
        one_hour & view["AI예측온도_C"].notna()
    ]
    .sort_values("목표시각")
    .copy()
)

pred = forecast.dropna(subset=["다음온도_C"])

if len(pred):
    mae = (
        pred["다음온도_C"] - pred["AI예측온도_C"]
    ).abs().mean()
    mae_text = f"{mae:.2f} ℃"
else:
    mae_text = "산출 불가"

invalid = int(
    (
        view["AI예측온도_C"].notna()
        & ~one_hour
    ).sum()
)

latest = view.iloc[-1]

temp_text = (
    f"{latest['온도_C']:.1f} ℃"
    if pd.notna(latest["온도_C"])
    else "결측"
)

# ======================================
# 6. 공通表示関数
# ======================================
def table(frame, time_column="측정시각"):
    shown = frame.sort_values(
        time_column,
        ascending=sort_order == "과거순"
    )

    if limit != "전체":
        shown = shown.head(int(limit))

    st.caption(
        f"전체 {len(frame):,}행 중 "
        f"{len(shown):,}행 표시 · {sort_order}"
    )
    st.dataframe(
        shown,
        hide_index=True,
        width="stretch",
        height=280
    )


def chart(fig):
    fig.update_layout(
        height=height,
        hovermode="x unified",
        legend_title_text="",
        margin=dict(l=10, r=10, t=20, b=10)
    )
    st.plotly_chart(fig, width="stretch")

# ======================================
# 7. 상단 요약
# ======================================
st.caption(
    f"설비: {equipment} ｜ "
    f"측정일 기준: {start} ~ {end}"
)

with st.container(border=True):
    k1, k2, k3, k4 = st.columns(4)

    k1.metric("조회 자료", f"{len(view):,}행")
    k2.metric("AI 확인후보", f"{len(candidates):,}건")
    k3.metric("확인후보 비율", f"{rate:.1f}%")
    k4.metric("마지막 측정 온도", temp_text)

    st.caption(
        f"마지막 측정: "
        f"{latest['측정시각']:%Y-%m-%d %H:%M} "
        "· 후보는 행 기준 집계"
    )

tab1, tab2, tab3 = st.tabs([
    "AI 점검 후보",
    "다음 1시간 온도 예측",
    "업무 검토 및 저장"
])

# ======================================
# TAB 1. AI 점검 후보
# ======================================
with tab1:
    if len(candidates):
        st.warning(
            f"담당자 확인이 필요한 후보 "
            f"{len(candidates):,}건이 있습니다."
        )
    else:
        st.info("선택 기간에 AI 확인후보가 없습니다.")

    st.subheader("온도 추이와 AI 확인후보")

    fig = px.line(
        view,
        x="측정시각",
        y="온도_C",
        markers=points,
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

    chart(fig)

    st.subheader("점검 후보 상세")
    table(candidates)

    st.caption(
        "온도가 없는 후보는 상세표에는 포함되지만 "
        "그래프의 점으로 표시되지 않습니다."
    )

    with st.expander("AI 결과별 건수"):
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

    if invalid:
        st.warning(
            "예측 간격이 1시간이 아니거나 "
            f"목표시각이 없는 {invalid:,}건은 분석 제외. "
            "추가 확인 필요."
        )

    if forecast.empty:
        st.info("유효한 1시간 예측 자료가 없습니다.")

    else:
        p1, p2, p3 = st.columns(3)

        p1.metric("평균 절대 오차(MAE)", mae_text)
        p2.metric(
            "실제값 비교 가능",
            f"{len(pred):,}건"
        )
        p3.metric(
            "실제값 없음",
            f"{len(forecast) - len(pred):,}건"
        )

        data = forecast.rename(columns={
            "다음온도_C": "실제 온도",
            "AI예측온도_C": "AI 예측 온도"
        })

        fig2 = px.line(
            data,
            x="목표시각",
            y=["실제 온도", "AI 예측 온도"],
            markers=points,
            labels={
                "value": "온도 (℃)",
                "variable": "구분"
            },
            color_discrete_map={
                "실제 온도": "#2563EB",
                "AI 예측 온도": "#F59E0B"
            }
        )

        chart(fig2)

        st.caption(
            "그래프는 목표시각 기준입니다. "
            "실제값 없는 예측도 표시하며 "
            "MAE 계산에서는 제외합니다."
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

            table(detail, "목표시각")

# ======================================
# TAB 3. 업무 검토 및 저장
# ======================================
with tab3:
    memo_key = f"memo_{equipment}_{start}_{end}"
    widget_key = f"input_{memo_key}"

    if memo_key not in st.session_state:
        st.session_state[memo_key] = (
            "센서 상태와 운전 조건을 확인한 후 "
            "담당자 검토가 필요합니다."
        )

    if widget_key not in st.session_state:
        st.session_state[widget_key] = (
            st.session_state[memo_key]
        )

    def remember(saved, widget):
        st.session_state[saved] = st.session_state[widget]

    left, right = st.columns([1, 1.2])

    with left:
        st.subheader("업무 검토")

        note = st.text_area(
            "확인할 사항 및 조치 제안",
            key=widget_key,
            height=200,
            on_change=remember,
            args=(memo_key, widget_key)
        )

        st.caption(
            "메모는 현재 세션에서 유지됩니다. "
            "보관하려면 보고서 TXT를 내려받으세요."
        )

    report = f"""철도 데이터 분석 검토 보고서
설비: {equipment}
조회 기간(측정일 기준): {start} ~ {end}
조회 자료: {len(view):,}행
AI 확인후보: {len(candidates):,}건 (행 기준, {rate:.1f}%)
마지막 측정 온도: {temp_text}
1시간 온도 예측 MAE: {mae_text} ({len(pred):,}건 비교)
예측 간격 확인 필요: {invalid:,}건 (분석 제외)

업무 메모:
{note}

교육용 가상 자료이며, 확인후보는 고장 확정이 아닙니다.
"""

    with right:
        st.subheader("보고서 미리보기")
        with st.container(border=True):
            st.text(report)

    safe_equipment = re.sub(
        r"[^\w가-힣.-]+",
        "_",
        str(equipment)
    )[:80]

    suffix = f"{safe_equipment}_{start}_{end}"

    with left:
        st.subheader("파일 다운로드")

        st.download_button(
            "조회 결과 CSV",
            view.to_csv(index=False).encode("utf-8-sig"),
            f"dashboard_{suffix}.csv",
            mime="text/csv",
            width="stretch"
        )

        st.download_button(
            "점검 후보 CSV",
            candidates.to_csv(index=False).encode("utf-8-sig"),
            f"candidates_{suffix}.csv",
            mime="text/csv",
            width="stretch"
        )

        st.download_button(
            "보고서 TXT",
            report.encode("utf-8-sig"),
            f"report_{suffix}.txt",
            mime="text/plain",
            width="stretch"
        )

# ======================================
# 8. 전체 조회 데이터
# ======================================
if show_raw:
    st.divider()

    with st.expander("전체 조회 데이터"):
        table(view)
        st.caption(
            "분석 수치·다운로드는 전체 조회 자료 기준이며 "
            "중복 행은 임의로 제거하지 않습니다."
        )
