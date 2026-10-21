from pathlib import Path
import hashlib
import re
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v2 as components
st.set_page_config(page_title='철도 데이터 분석 대시보드', page_icon='🚆', layout='wide', initial_sidebar_state='expanded')
DATA_PATH = Path('analysis_result.csv')
CALENDAR_CSS = '\n.cal {\n    font-family: inherit;\n    color: var(--st-text-color);\n    font-size: 14px;\n}\n.bar, .choices {\n    display: flex;\n    gap: 6px;\n    align-items: center;\n    margin: 8px 0;\n}\nbutton, select {\n    font: inherit;\n    color: inherit;\n    border: 1px solid #94a3b866;\n    background: var(--st-secondary-background-color);\n    border-radius: 7px;\n    padding: 7px;\n    cursor: pointer;\n}\n.choices button {\n    flex: 1;\n    font-size: 12px;\n}\n.active {\n    outline: 2px solid #2563eb;\n}\nselect {\n    flex: 1;\n    min-width: 0;\n}\n.grid {\n    display: grid;\n    grid-template-columns: repeat(7, 1fr);\n    gap: 4px;\n}\n.grid button {\n    padding: 7px 0;\n    min-width: 0;\n}\n.week {\n    text-align: center;\n    font-size: 12px;\n    opacity: .7;\n    padding: 5px 0;\n}\n.grid button:disabled {\n    opacity: .25;\n    cursor: not-allowed;\n    background: transparent;\n}\n.grid .inside {\n    background: #2563eb20;\n}\n.grid .selected {\n    background: #2563eb;\n    color: white;\n    border-color: #2563eb;\n}\n.help {\n    font-size: 12px;\n    opacity: .75;\n    margin-top: 8px;\n    line-height: 1.5;\n}\n'
CALENDAR_JS = "\nexport default function({\n    parentElement, data, setTriggerValue\n}) {\n    const root = parentElement.querySelector('.cal');\n    const valid = new Set(data.dates);\n    const months = [];\n\n    let cursor = data.dates[0].slice(0, 7);\n    const last = data.dates.at(-1).slice(0, 7);\n\n    while (cursor <= last) {\n        months.push(cursor);\n        let [y, m] = cursor.split('-').map(Number);\n        m++;\n        if (m === 13) {\n            y++;\n            m = 1;\n        }\n        cursor = `${y}-${String(m).padStart(2, '0')}`;\n    }\n\n    let month = months.includes(root._month)\n        ? root._month\n        : data.start.slice(0, 7);\n\n    let mode = root._mode || 'start';\n\n    function draw() {\n        root._month = month;\n        root._mode = mode;\n        root.replaceChildren();\n\n        const choices = document.createElement('div');\n        choices.className = 'choices';\n\n        for (const [value, label] of [\n            ['start', '시작일'],\n            ['end', '종료일']\n        ]) {\n            const button = document.createElement('button');\n            button.type = 'button';\n            button.textContent = label + ' ' + data[value];\n            button.className = mode === value ? 'active' : '';\n            button.onclick = () => {\n                mode = value;\n                draw();\n            };\n            choices.append(button);\n        }\n\n        root.append(choices);\n\n        const bar = document.createElement('div');\n        bar.className = 'bar';\n\n        const prev = document.createElement('button');\n        prev.textContent = '‹';\n        prev.ariaLabel = '이전 달';\n\n        const next = document.createElement('button');\n        next.textContent = '›';\n        next.ariaLabel = '다음 달';\n\n        const select = document.createElement('select');\n        select.ariaLabel = '표시할 월';\n\n        months.forEach(value => {\n            const option = document.createElement('option');\n            option.value = value;\n            option.textContent =\n                value.replace('-', '년 ') + '월';\n            select.append(option);\n        });\n\n        select.value = month;\n        select.onchange = () => {\n            month = select.value;\n            draw();\n        };\n\n        const index = months.indexOf(month);\n        prev.disabled = index === 0;\n        next.disabled = index === months.length - 1;\n\n        prev.onclick = () => {\n            month = months[index - 1];\n            draw();\n        };\n        next.onclick = () => {\n            month = months[index + 1];\n            draw();\n        };\n\n        bar.append(prev, select, next);\n        root.append(bar);\n\n        const grid = document.createElement('div');\n        grid.className = 'grid';\n\n        ['일', '월', '화', '수', '목', '금', '토']\n            .forEach(label => {\n                const cell = document.createElement('div');\n                cell.className = 'week';\n                cell.textContent = label;\n                grid.append(cell);\n            });\n\n        const [year, monthNumber] = month.split('-').map(Number);\n        const offset = new Date(\n            year, monthNumber - 1, 1\n        ).getDay();\n        const count = new Date(\n            year, monthNumber, 0\n        ).getDate();\n\n        for (let i = 0; i < offset; i++) {\n            grid.append(document.createElement('span'));\n        }\n\n        for (let day = 1; day <= count; day++) {\n            const iso =\n                month + '-' + String(day).padStart(2, '0');\n\n            const button = document.createElement('button');\n            button.type = 'button';\n            button.textContent = day;\n\n            // 미측정일 및 시작일 이전의 종료일 선택 차단\n            button.disabled =\n                !valid.has(iso)\n                || (mode === 'end' && iso < data.start);\n\n            button.title = !valid.has(iso)\n                ? iso + ' · 측정 자료 없음'\n                : iso;\n            button.ariaLabel = button.title;\n\n            if (iso >= data.start && iso <= data.end) {\n                button.classList.add('inside');\n            }\n            if (iso === data.start || iso === data.end) {\n                button.classList.add('selected');\n            }\n\n            button.onclick = () => {\n                let start = data.start;\n                let end = data.end;\n\n                if (mode === 'start') {\n                    start = iso;\n                    if (end < start) end = start;\n                    root._mode = 'end';\n                } else {\n                    end = iso;\n                    root._mode = 'start';\n                }\n\n                setTriggerValue('selection', {start, end});\n            };\n\n            grid.append(button);\n        }\n\n        root.append(grid);\n\n        const help = document.createElement('div');\n        help.className = 'help';\n        help.textContent =\n            '시작일·종료일 버튼을 누른 뒤 날짜를 선택하세요. ' +\n            '흐린 날짜는 측정 자료가 없어 선택할 수 없습니다.';\n        root.append(help);\n    }\n\n    draw();\n}\n"
calendar = components.component('rail_data_calendar', html='<div class="cal"></div>', css=CALENDAR_CSS, js=CALENDAR_JS)

@st.cache_data(show_spinner=False)
def load_data(paths, signatures):
    frames = []
    for path in paths:
        data = pd.read_csv(path, dtype={'설비ID': 'string'})
        if 'AI결과' in data.columns:
            if 'Ai결과' in data.columns:
                raise ValueError(f'{Path(path).name}: AI결과와 Ai결과가 동시에 존재합니다. 확인 필요.')
            data = data.rename(columns={'AI결과': 'Ai결과'})
        required = ['설비ID', '측정시각', '목표시각', '온도_C', 'Ai결과', '다음온도_C']
        missing = [column for column in required if column not in data.columns]
        if missing:
            raise ValueError(f'{Path(path).name} 필수 열 누락: ' + ', '.join(missing))
        if 'AI예측온도_C' not in data.columns:
            data['AI예측온도_C'] = float('nan')
        data['원본파일'] = Path(path).name
        data['설비ID'] = data['설비ID'].str.strip().replace('', pd.NA)
        data['Ai결과'] = data['Ai결과'].astype('string').str.strip().replace('', pd.NA)
        for column in ['측정시각', '목표시각']:
            data[column] = pd.to_datetime(data[column], errors='coerce')
        for column in ['온도_C', '다음온도_C', 'AI예측온도_C', '부하율_pct', '전압_V']:
            if column in data.columns:
                data[column] = pd.to_numeric(data[column], errors='coerce').replace([float('inf'), float('-inf')], float('nan'))
        frames.append(data)
    combined = pd.concat(frames, ignore_index=True, sort=False)
    valid = combined['설비ID'].notna() & combined['측정시각'].notna()
    excluded = int((~valid).sum())
    combined = combined.loc[valid].sort_values(['설비ID', '측정시각']).reset_index(drop=True)
    file_counts = combined.groupby('설비ID')['원본파일'].nunique()
    overlapping = file_counts[file_counts > 1].index.tolist()
    if overlapping:
        raise ValueError('여러 파일에 동일 설비ID가 있습니다. 같은 설비인지 확인 필요: ' + ', '.join(map(str, overlapping)))
    return (combined, excluded)
st.title('철도 데이터 분석 대시보드')
st.caption('교육용 가상 자료입니다. AI 확인후보는 고장 확정이 아니며 담당자 검토가 필요합니다.')
try:
    df, excluded = load_data((str(DATA_PATH), str(DATA_PATH.parent / 'power_analysis_result.csv')), tuple(((path.stat().st_mtime_ns, path.stat().st_size) for path in (DATA_PATH, DATA_PATH.parent / 'power_analysis_result.csv'))))
except Exception as error:
    st.error(f'데이터를 읽지 못했습니다: {error}')
    st.info('Google Drive 연결 상태와 DATA_PATH의 CSV 경로를 확인하세요.')
    st.stop()
if df.empty:
    st.warning('조회 가능한 자료가 없습니다.')
    st.stop()
with st.sidebar:
    st.header('조회 조건')
    equipment = st.selectbox('설비 선택', sorted(df['설비ID'].unique()))
    source = df.loc[df['설비ID'] == equipment].copy()
    dates = sorted(source['측정시각'].dt.strftime('%Y-%m-%d').unique().tolist())
    token = hashlib.sha256((str(equipment) + '|'.join(dates)).encode()).hexdigest()[:16]
    range_key = f'range_{token}'
    if range_key not in st.session_state:
        st.session_state[range_key] = (dates[0], dates[-1])
    a, b, c = st.columns(3)
    preset = None
    if a.button('전체', width='stretch'):
        preset = 0
    if b.button('최근 7일', width='stretch'):
        preset = 7
    if c.button('최근 30일', width='stretch'):
        preset = 30
    if preset is not None:
        threshold = pd.Timestamp(dates[-1]) - pd.Timedelta(days=max(preset - 1, 0))
        selected = dates if preset == 0 else [day for day in dates if pd.Timestamp(day) >= threshold]
        st.session_state[range_key] = (selected[0], selected[-1])
    start, end = st.session_state[range_key]
    st.caption('조회 달력 · 선택 설비의 측정일만 활성화')
    result = calendar(data={'dates': dates, 'start': start, 'end': end}, key=f'calendar_{token}', on_selection_change=lambda: None)
    if result.selection:
        picked = result.selection
        selected_start = picked.get('start')
        selected_end = picked.get('end')
        if selected_start in dates and selected_end in dates and (selected_start <= selected_end) and ((selected_start, selected_end) != (start, end)):
            st.session_state[range_key] = (selected_start, selected_end)
            st.rerun()
    st.caption('최근 기간은 마지막 측정일 기준입니다. 기간 중 미측정일은 분석에 포함되지 않습니다.')
    with st.expander('화면·목록 설정', expanded=True):
        height = st.select_slider('그래프 높이', [300, 380, 460], value=380)
        points = st.checkbox('온도선에 측정점 표시', value=False)
        sort_order = st.radio('목록 정렬', ['최신순', '과거순'], horizontal=True)
        limit = st.selectbox('표 최대 표시 행', [50, 100, 300, '전체'], index=1)
        show_raw = st.checkbox('전체 조회 데이터 표시', value=True)
        st.caption('표시 설정은 분석 수치·다운로드 범위에 영향을 주지 않습니다.')
    with st.expander('데이터 정보'):
        st.write(f"설비 수: {df['설비ID'].nunique():,}개")
        st.write(f'유효 자료: {len(df):,}행 / 제외 자료: {excluded:,}행')
        st.caption('제외 자료는 설비ID 또는 측정시각이 없는 행입니다.')
    if st.button('데이터 새로고침', width='stretch'):
        load_data.clear()
        st.rerun()
view = source.loc[(source['측정시각'] >= pd.Timestamp(start)) & (source['측정시각'] < pd.Timestamp(end) + pd.Timedelta(days=1))].copy()
if view.empty:
    st.warning('선택한 기간에 자료가 없습니다.')
    st.stop()
candidates = view.loc[view['Ai결과'].eq('확인후보').fillna(False)].copy()
rate = len(candidates) / len(view) * 100
one_hour = (view['목표시각'] - view['측정시각']).eq(pd.Timedelta(hours=1))
forecast = view.loc[one_hour & view['AI예측온도_C'].notna()].sort_values('목표시각').copy()
pred = forecast.dropna(subset=['다음온도_C'])
if len(pred):
    mae = (pred['다음온도_C'] - pred['AI예측온도_C']).abs().mean()
    mae_text = f'{mae:.2f} ℃'
else:
    mae_text = '산출 불가'
invalid = int((view['AI예측온도_C'].notna() & ~one_hour).sum())
latest = view.iloc[-1]
temp_text = f"{latest['온도_C']:.1f} ℃" if pd.notna(latest['온도_C']) else '결측'

def table(frame, time_column='측정시각'):
    shown = frame.sort_values(time_column, ascending=sort_order == '과거순')
    if limit != '전체':
        shown = shown.head(int(limit))
    st.caption(f'전체 {len(frame):,}행 중 {len(shown):,}행 표시 · {sort_order}')
    st.dataframe(shown, hide_index=True, width='stretch', height=280)

def chart(fig):
    fig.update_layout(height=height, hovermode='x unified', legend_title_text='', margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, width='stretch')
st.caption(f'설비: {equipment} ｜ 측정일 기준: {start} ~ {end}')
with st.container(border=True):
    k1, k2, k3, k4 = st.columns(4)
    k1.metric('조회 자료', f'{len(view):,}행')
    k2.metric('AI 확인후보', f'{len(candidates):,}건')
    k3.metric('확인후보 비율', f'{rate:.1f}%')
    k4.metric('마지막 측정 온도', temp_text)
    st.caption(f"마지막 측정: {latest['측정시각']:%Y-%m-%d %H:%M} · 후보는 행 기준 집계")
tab1, tab2, tab3 = st.tabs(['AI 점검 후보', '다음 1시간 온도 예측', '업무 검토 및 저장'])
with tab1:
    if len(candidates):
        st.warning(f'담당자 확인이 필요한 후보 {len(candidates):,}건이 있습니다.')
    else:
        st.info('선택 기간에 AI 확인후보가 없습니다.')
    st.subheader('온도 추이와 AI 확인후보')
    fig = px.line(view, x='측정시각', y='온도_C', markers=points, labels={'온도_C': '온도 (℃)'})
    fig.update_traces(line_color='#2563EB', name='측정 온도', showlegend=True)
    fig.add_scatter(x=candidates['측정시각'], y=candidates['온도_C'], mode='markers', name='확인후보', marker=dict(color='#DC2626', size=10, symbol='diamond'))
    chart(fig)
    st.subheader('점검 후보 상세')
    table(candidates)
    st.caption('온도가 없는 후보는 상세표에는 포함되지만 그래프의 점으로 표시되지 않습니다.')
    with st.expander('AI 결과별 건수'):
        counts = view['Ai결과'].fillna('미기록').value_counts().rename_axis('AI 결과').reset_index(name='건수')
        st.dataframe(counts, hide_index=True, width='stretch')
with tab2:
    st.subheader('실제 온도와 AI 예측 온도')
    if invalid:
        st.warning(f'예측 간격이 1시간이 아니거나 목표시각이 없는 {invalid:,}건은 분석 제외. 추가 확인 필요.')
    if forecast.empty:
        st.info('유효한 1시간 예측 자료가 없습니다.')
    else:
        p1, p2, p3 = st.columns(3)
        p1.metric('평균 절대 오차(MAE)', mae_text)
        p2.metric('실제값 비교 가능', f'{len(pred):,}건')
        p3.metric('실제값 없음', f'{len(forecast) - len(pred):,}건')
        data = forecast.rename(columns={'다음온도_C': '실제 온도', 'AI예측온도_C': 'AI 예측 온도'})
        fig2 = px.line(data, x='목표시각', y=['실제 온도', 'AI 예측 온도'], markers=points, labels={'value': '온도 (℃)', 'variable': '구분'}, color_discrete_map={'실제 온도': '#2563EB', 'AI 예측 온도': '#F59E0B'})
        chart(fig2)
        st.caption('그래프는 목표시각 기준입니다. 실제값 없는 예측도 표시하며 MAE 계산에서는 제외합니다.')
        with st.expander('예측 상세 및 오차'):
            detail = forecast[['측정시각', '목표시각', '다음온도_C', 'AI예측온도_C']].copy()
            detail['절대오차_C'] = (detail['다음온도_C'] - detail['AI예측온도_C']).abs()
            table(detail, '목표시각')
with tab3:
    memo_key = f'memo_{equipment}_{start}_{end}'
    widget_key = f'input_{memo_key}'
    if memo_key not in st.session_state:
        st.session_state[memo_key] = '센서 상태와 운전 조건을 확인한 후 담당자 검토가 필요합니다.'
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state[memo_key]

    def remember(saved, widget):
        st.session_state[saved] = st.session_state[widget]
    left, right = st.columns([1, 1.2])
    with left:
        st.subheader('업무 검토')
        note = st.text_area('확인할 사항 및 조치 제안', key=widget_key, height=200, on_change=remember, args=(memo_key, widget_key))
        st.caption('메모는 현재 세션에서 유지됩니다. 보관하려면 보고서 TXT를 내려받으세요.')
    report = f'철도 데이터 분석 검토 보고서\n설비: {equipment}\n조회 기간(측정일 기준): {start} ~ {end}\n조회 자료: {len(view):,}행\nAI 확인후보: {len(candidates):,}건 (행 기준, {rate:.1f}%)\n마지막 측정 온도: {temp_text}\n1시간 온도 예측 MAE: {mae_text} ({len(pred):,}건 비교)\n예측 간격 확인 필요: {invalid:,}건 (분석 제외)\n\n업무 메모:\n{note}\n\n교육용 가상 자료이며, 확인후보는 고장 확정이 아닙니다.\n'
    with right:
        st.subheader('보고서 미리보기')
        with st.container(border=True):
            st.text(report)
    safe_equipment = re.sub('[^\\w가-힣.-]+', '_', str(equipment))[:80]
    suffix = f'{safe_equipment}_{start}_{end}'
    with left:
        st.subheader('파일 다운로드')
        st.download_button('조회 결과 CSV', view.to_csv(index=False).encode('utf-8-sig'), f'dashboard_{suffix}.csv', mime='text/csv', width='stretch')
        st.download_button('점검 후보 CSV', candidates.to_csv(index=False).encode('utf-8-sig'), f'candidates_{suffix}.csv', mime='text/csv', width='stretch')
        st.download_button('보고서 TXT', report.encode('utf-8-sig'), f'report_{suffix}.txt', mime='text/plain', width='stretch')
if show_raw:
    st.divider()
    with st.expander('전체 조회 데이터'):
        table(view)
        st.caption('분석 수치·다운로드는 전체 조회 자료 기준이며 중복 행은 임의로 제거하지 않습니다.')
