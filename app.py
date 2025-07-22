import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table
import plotly.express as px
import dash
import re

# Fungsi untuk load & proses data
def load_and_process(filepath, tahun, jenis):
    df = pd.read_excel(filepath, header=2)
    df.columns = df.columns.map(lambda x: str(x).strip() if not pd.isna(x) else x)

    nama_guru_col = df.columns[1]
    df.rename(columns={nama_guru_col: "Nama Guru"}, inplace=True)
    df = df.dropna(subset=["Nama Guru"]).reset_index(drop=True)
    df["Nama Guru"] = df["Nama Guru"].astype(str)
    df["Nama Guru"] = df["Nama Guru"].str.replace(r",.*", "", regex=True)  # Hilangkan gelar
    df["Nama Guru"] = df["Nama Guru"].str.strip()
    # print("Sample Nama Guru:", df["Nama Guru"].unique()[:10])

    invalid_nama = {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K",
                    "Jumlah", "Total", "Ban", "25%", "0.25", "0.75", "", "SB"}
    df = df[~df["Nama Guru"].isin(invalid_nama)]
    df = df[df["Nama Guru"].str.len() > 2]

    if jenis == "Penilaian Rencana Pelaksanaan Pembelajaran":
        indikator_all = list("ABCDEFG")
        indikator_1st = [i for i in indikator_all if i in df.columns]
        indikator_2nd_raw = [f"{i}.1" for i in indikator_1st if f"{i}.1" in df.columns]
        indikator = indikator_1st  # Ini dipakai untuk periode ke-2 juga

    elif jenis == "Penilaian Pelaksanaan Pembelajaran":
        indikator_1st = list("ABCDEFGHIJ")
        indikator_2nd_raw = [f"{c}.1" for c in indikator_1st]
        if 'K' in df.columns:
            indikator_2nd_raw.append('K')
        elif 'K.1' in df.columns:
            indikator_2nd_raw.append('K.1')
        indikator = list("ABCDEFGHIJK")

    else:
        raise ValueError("Jenis penilaian tidak dikenali")

    for col in indikator_1st + indikator_2nd_raw:
        if col not in df.columns:
            raise ValueError(f"Kolom indikator '{col}' tidak ditemukan di file {filepath}")

    df[indikator_1st + indikator_2nd_raw] = df[indikator_1st + indikator_2nd_raw].apply(pd.to_numeric, errors='coerce')

    df_1st = df[["Nama Guru"] + indikator_1st].copy()
    df_1st["Periode"] = "1st"
    df_1st["Tahun"] = tahun
    df_1st = df_1st.melt(id_vars=["Nama Guru", "Periode", "Tahun"],
                         var_name="Indikator", value_name="Nilai")

    df_2nd = df[["Nama Guru"] + indikator_2nd_raw].copy()
    df_2nd.columns = ["Nama Guru"] + indikator
    df_2nd["Periode"] = "2nd"
    df_2nd["Tahun"] = tahun
    df_2nd = df_2nd.melt(id_vars=["Nama Guru", "Periode", "Tahun"],
                         var_name="Indikator", value_name="Nilai")

    return pd.concat([df_1st, df_2nd], ignore_index=True)

# Load semua dataset
datasets = {
    "Penilaian Rencana Pelaksanaan Pembelajaran": {
        "2020-2021": load_and_process("Penilaian Rencana Pelaksanaan Pembelajaran 2020-2021.xlsx", "2020-2021", "Penilaian Rencana Pelaksanaan Pembelajaran"),
        "2022-2023": load_and_process("Penilaian Rencana Pelaksanaan Pembelajaran 2022-2023.xlsx", "2022-2023", "Penilaian Rencana Pelaksanaan Pembelajaran"),
        "2023-2024": load_and_process("Penilaian Rencana Pelaksanaan Pembelajaran 2023-2024.xlsx", "2023-2024", "Penilaian Rencana Pelaksanaan Pembelajaran")
    },
    "Penilaian Pelaksanaan Pembelajaran": {
        "2020-2021": load_and_process("Penilaian Pelaksanaan Pembelajaran 2020-2021.xlsx", "2020-2021", "Penilaian Pelaksanaan Pembelajaran"),
        "2022-2023": load_and_process("Penilaian Pelaksanaan Pembelajaran 2022-2023.xlsx", "2022-2023", "Penilaian Pelaksanaan Pembelajaran"),
        "2023-2024": load_and_process("Penilaian Pelaksanaan Pembelajaran 2023-2024.xlsx", "2023-2024", "Penilaian Pelaksanaan Pembelajaran")
    }
}

# Harus setelah datasets selesai dibuat
def get_all_guru_usernames():
    usernames = set()

    # Daftar gelar akademik (tanpa titik, untuk pencocokan kasar)
    gelar_keywords = [
        "spd", "ssi", "ssn", "ssos", "shum", "sip", "skom", "sh", "se",
        "mpd", "mhum", "msn", "msi", "mkom", "mh", "ss"
    ]

    def hapus_gelar(nama):
        # Bersihkan nama: lowercase, hilangkan spasi, koma, titik
        nama = re.sub(r"[\s.,]", "", nama.lower())

        # Hilangkan semua gelar yang ada di akhir nama
        for gelar in gelar_keywords:
            nama = re.sub(rf"{gelar}$", "", nama)
        # Ulangi untuk kasus dua gelar berturut-turut
        for gelar in gelar_keywords:
            nama = re.sub(rf"{gelar}$", "", nama)
        return nama

    for jenis_data in datasets.values():
        for df in jenis_data.values():
            cleaned = df["Nama Guru"].dropna().astype(str).apply(hapus_gelar)
            usernames.update(cleaned.unique())

    return usernames

valid_usernames = get_all_guru_usernames()
# print("==== Daftar username valid ====")
# print(sorted(valid_usernames))

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Supervisi Guru Dashboard"

card_style = lambda color: {
    "flex": "1", "backgroundColor": color, "color": "white", "padding": "20px",
    "borderRadius": "10px", "boxShadow": "0px 4px 8px rgba(0,0,0,0.2)",
    "textAlign": "center", "marginRight": "10px", "marginBottom": "10px"
}

app.layout = html.Div([
    dcc.Store(id='session-store', storage_type='session'),

    html.Div(id='login-section', children=[
        html.H2("🔐 Login Dashboard", style={"textAlign": "center", "color": "#2c3e50", "marginTop": "40px"}),
        html.Div([
            dcc.Input(id='input-username', type='text', placeholder='Username (e.g. nama@ses.com)',
                      style={"width": "100%", "padding": "12px", "marginBottom": "15px", "borderRadius": "8px", "border": "1px solid #ccc"}),
            dcc.Input(id='input-password', type='password', placeholder='Password',
                      style={"width": "100%", "padding": "12px", "marginBottom": "15px", "borderRadius": "8px", "border": "1px solid #ccc"}),
            html.Button("Login", id='btn-login', n_clicks=0,
                        style={"width": "100%", "padding": "12px", "backgroundColor": "#2980b9", "color": "white",
                               "border": "none", "borderRadius": "8px", "fontWeight": "bold"}),
            html.Div(id='login-message', style={"color": "red", "marginTop": "10px", "textAlign": "center"})
        ], style={"maxWidth": "400px", "margin": "auto", "padding": "20px", "border": "1px solid #ddd", "borderRadius": "10px", "boxShadow": "0px 4px 12px rgba(0,0,0,0.1)"})
    ]),

    html.Div(id="app-layout", style={"display": "none"}, children=[
        html.Button("Logout", id='btn-logout', n_clicks=0,
                    style={"float": "right", "margin": "20px", "backgroundColor": "#bdc3c7", "border": "none",
                           "padding": "10px 15px", "borderRadius": "8px"}),

    html.Div(id="tambah-data-wrapper", children=[
        html.Button("Tambah Data", id="btn-tambah", n_clicks=0)
    ], style={"display": "none"}),

    html.Div(id="hapus-data-wrapper", children=[
        html.Button("Hapus Data", id="btn-hapus", n_clicks=0)
    ], style={"display": "none"}),

        html.H1("📊 Dashboard Supervisi Guru", style={"textAlign": "center", "color": "#2c3e50", "marginTop": "20px"}),

        html.Div([
            html.Div([html.H3("👩‍🏫 Jumlah Guru Aktif"), html.Div(id="card-primary")], style=card_style("#3498db")),
            html.Div([html.H3("📈 Rata-rata Nilai Supervisi"), html.Div(id="card-avg")], style=card_style("#27ae60")),
            html.Div([html.H3("🏆 Indikator Tertinggi"), html.Div(id="card-top-indikator")], style=card_style("#9b59b6")),
            html.Div([html.H3("🎖️ Nilai Tertinggi Guru"), html.Div(id="card-top-guru")], style=card_style("#e67e22")),
            html.Div([html.H3("📈 Peningkatan Guru Tertinggi"), html.Div(id="card-best-improve")], style=card_style("#1abc9c")),
            html.Div([html.H3("📉 Indikator Terendah"), html.Div(id="card-bottom-indikator")], style=card_style("#e74c3c")),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "20px", "justifyContent": "space-between", "padding": "20px"}),

        html.Div([
            html.Label("📂 Pilih Jenis Penilaian:", style={"fontWeight": "bold", "marginTop": "10px"}),
            dcc.Dropdown(id='jenis-dropdown', options=[{'label': k, 'value': k} for k in datasets.keys()],
                         value='Penilaian Rencana Pelaksanaan Pembelajaran', style={"marginBottom": "20px"}),
            html.Label("📅 Pilih Tahun Supervisi:", style={"fontWeight": "bold"}),
            dcc.RadioItems(id='tahun-radio', inline=True, style={"marginBottom": "20px"}),
            html.Label("🔍 Pilih Guru:", style={"fontWeight": "bold"}),
            dcc.Dropdown(id='guru-dropdown', placeholder="Pilih Nama Guru", style={"marginBottom": "30px"})
        ], style={"padding": "0px 30px"}),

        dcc.Graph(id='bar-chart'),

        html.H3("📝 Edit Data Nilai (Admin Only):", style={"marginTop": "40px", "marginBottom": "20px", "color": "#2c3e50"}),

        dcc.Input(
            id="search-guru",
            type="text",
            placeholder="🔍 Cari Nama Guru",
            style={"marginBottom": "20px", "padding": "12px", "width": "100%", "borderRadius": "8px", "border": "1px solid #ccc"}
        ),

        dash_table.DataTable(
            id="editable-table",
            editable=True,
            row_selectable="single",
            selected_rows=[],
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={"padding": "10px", "textAlign": "left"},
            style_header={"backgroundColor": "#ecf0f1", "fontWeight": "bold"}
        ),

        

        html.Div(
    id="admin-controls",  # ⬅️ tambahkan id di sini
    children=[
        html.H4("➕ Tambah Data Guru Baru", style={"marginTop": "40px", "color": "#2c3e50"}),
        html.Div([
            dcc.Input(id='input-nama-guru', type='text', placeholder='Nama Guru',
                      style={"height": "40px", 'width': '100%', 'margin': '5px 0', "padding": "10px", "borderRadius": "8px"}),
            dcc.Input(id='input-indikator', type='text', placeholder='Indikator',
                      style={"height": "40px", 'width': '100%', 'margin': '5px 0', "padding": "10px", "borderRadius": "8px"}),
            dcc.Input(id='input-nilai', type='number', placeholder='Nilai',
                      style={"height": "40px", 'width': '100%', 'margin': '5px 0', "padding": "10px", "borderRadius": "8px"}),

            dcc.Dropdown(
                id='input-periode',
                options=[
                    {'label': '1st', 'value': '1st'},
                    {'label': '2nd', 'value': '2nd'}
                ],
                placeholder='Pilih Periode',
                style={'width': '100%', 'margin': '5px 0', "padding": "10px"}
            ),

            dcc.Dropdown(
                id="input-jenis",
                options=[
                    {"label": "Penilaian Rencana Pelaksanaan Pembelajaran", "value": "Penilaian Rencana Pelaksanaan Pembelajaran"},
                    {"label": "Penilaian Pelaksanaan Pembelajaran", "value": "Penilaian Pelaksanaan Pembelajaran"},
                ],
                placeholder="Pilih Jenis Penilaian",
                style={'width': '100%', 'margin': '5px 0', "padding": "10px"}
            ),

            dcc.RadioItems(
                id="input-tahun",
                options=[
                    {"label": "2020-2021", "value": "2020-2021"},
                    {"label": "2022-2023", "value": "2022-2023"},
                    {"label": "2023-2024", "value": "2023-2024"},
                ],
                labelStyle={'display': 'inline-block', 'marginRight': '15px'},
                inputStyle={"margin-right": "5px"},
                style={"marginTop": "10px", "marginBottom": "15px"}
            ),

            html.Div([
                html.Button("Tambah Data", id="add-row-button", n_clicks=0,
                            style={"height": "40px", 'width': '160px', 'marginRight': '10px', "backgroundColor": "#2980b9",
                                   "color": "white", "border": "none", "borderRadius": "6px"}),
                html.Button("❌ Hapus Baris Terpilih", id="delete-row-button", n_clicks=0,
                            style={"height": "40px", 'width': '200px', "backgroundColor": "#c0392b", "color": "white",
                                   "border": "none", "borderRadius": "6px"}),
                html.Button("💾 Simpan Perubahan", id="save-button", n_clicks=0,
                            style={"height": "40px", 'width': '200px', "backgroundColor": "#2ecc71", "color": "white",
                                   "border": "none", "borderRadius": "6px", "float": "right"})
            ], style={"marginTop": "20px", "marginBottom": "30px"}),

            html.Div(id="save-status", style={"marginTop": "10px", "color": "green"})
        ], style={"maxWidth": "600px", "margin": "auto"})
    ]
)
    ])
])

@app.callback(
    Output('tahun-radio', 'options'),
    Output('tahun-radio', 'value'),
    Input('jenis-dropdown', 'value')
)
def update_tahun_dropdown(jenis):
    tahun_list = sorted(datasets[jenis].keys())
    return [{'label': t, 'value': t} for t in tahun_list], tahun_list[0]

@app.callback(
    Output('guru-dropdown', 'options'),
    Output('guru-dropdown', 'value'),
    Output('guru-dropdown', 'disabled'),
    Input('jenis-dropdown', 'value'),
    Input('tahun-radio', 'value'),
    Input('session-store', 'data')
)
def update_guru_dropdown(jenis, tahun, session_data):
    df_ori = datasets[jenis][tahun]

    if not session_data or not session_data.get("logged_in"):
        return [], None, True

    username = session_data["username"]
    role = session_data["role"]

    if role == "admin":
        options = [{'label': g, 'value': g} for g in sorted(df_ori["Nama Guru"].unique())]
        return options, None, False
    else:
        nama_user = username.replace("@ses.com", "").strip().lower()

        df = df_ori.copy()
        df["Nama Guru Normalized"] = df["Nama Guru"].str.replace(" ", "").str.lower().str.strip()

        match_row = df[df["Nama Guru Normalized"] == nama_user]
        if not match_row.empty:
            nama_asli = match_row["Nama Guru"].iloc[0]
            return [{'label': nama_asli, 'value': nama_asli}], nama_asli, True
        else:
            return [], None, True

import plotly.graph_objects as go

@app.callback(
    Output('bar-chart', 'figure'),
    Input('editable-table', 'data'),
    Input('jenis-dropdown', 'value'),
    Input('tahun-radio', 'value'),
    Input('guru-dropdown', 'value'),
    Input('session-store', 'data')
)
def update_chart_from_table(table_data, jenis, tahun, guru, session_data):
    if not session_data or not session_data.get("logged_in"):
        return go.Figure().update_layout(title="Silakan login")

    df = pd.DataFrame(table_data)
    df.columns = [str(col).strip() for col in df.columns]  # Pastikan tidak ada spasi tersembunyi

    role = session_data["role"]
    username = session_data["username"]

    if "Nama Guru" not in df.columns:
        print("Kolom yang tersedia:", df.columns.tolist())
        return go.Figure().update_layout(title="Kolom 'Nama Guru' tidak ditemukan")

    if role == "admin":
        if not guru:
            return go.Figure().update_layout(title="Silakan pilih guru")
        filtered = df[df["Nama Guru"] == guru]
    else:
        nama_guru = username.replace("@ses.com", "").strip().lower()
        df["Nama Guru Normalized"] = df["Nama Guru"].astype(str).str.replace(" ", "").str.lower().str.strip()
        filtered = df[df["Nama Guru Normalized"] == nama_guru]


    # Filter berdasarkan jenis dan tahun
    if "Jenis" in filtered.columns and "Tahun" in filtered.columns:
        filtered = filtered[(filtered["Jenis"] == jenis) & (filtered["Tahun"] == tahun)]

    if filtered.empty:
        return go.Figure().update_layout(title="Tidak ditemukan data guru yang dipilih.")

    indikator_order = sorted(filtered["Indikator"].unique())
    filtered["Indikator"] = pd.Categorical(filtered["Indikator"], categories=indikator_order, ordered=True)
    filtered = filtered.sort_values("Indikator")

    fig = go.Figure()

    for periode in filtered["Periode"].unique():
        subset = filtered[filtered["Periode"] == periode]
        fig.add_trace(go.Bar(
            x=subset["Indikator"],
            y=subset["Nilai"],
            name=periode
        ))

    fig.update_layout(
        barmode='group',
        title=f"Nilai Indikator: {filtered['Nama Guru'].iloc[0]} ({tahun})",
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    return fig


@app.callback(
    Output("card-primary", "children"),
    Output("card-avg", "children"),
    Output("card-top-indikator", "children"),
    Output("card-top-guru", "children"),
    Output("card-best-improve", "children"),
    Output("card-bottom-indikator", "children"),
    Input("jenis-dropdown", "value"),
    Input("tahun-radio", "value")
)
def update_cards(jenis, tahun):
    df = datasets[jenis][tahun]
    
    # 🔒 Konversi kolom nilai ke numerik dulu
    if "Nilai" in df.columns:
        df["Nilai"] = pd.to_numeric(df["Nilai"], errors="coerce")
    else:
        return [dash.no_update] * 3  # atau sesuai jumlah Output di callback

    
    total_guru = df[["Nama Guru"]].drop_duplicates().shape[0]
    rata_rata = df["Nilai"].mean()
    top_indikator = df.groupby("Indikator")["Nilai"].mean().idxmax()
    bottom_indikator = df.groupby("Indikator")["Nilai"].mean().idxmin()
    top_guru = df.groupby("Nama Guru")["Nilai"].mean().idxmax()

    pivot = df.pivot_table(index="Nama Guru", columns="Periode", values="Nilai", aggfunc="mean")
    pivot["Peningkatan"] = pivot.get("2nd", 0) - pivot.get("1st", 0)
    best_improve = pivot["Peningkatan"].idxmax() if not pivot["Peningkatan"].isna().all() else "—"

    return (
        f"{total_guru} Guru",
        f"{rata_rata:.2f}",
        top_indikator,
        top_guru,
        best_improve,
        bottom_indikator
    )

@app.callback(
    Output("editable-table", "data"),
    Output("editable-table", "columns"),
    Output("editable-table", "style_data_conditional"),
    Input("jenis-dropdown", "value"),
    Input("tahun-radio", "value"),
    Input("session-store", "data"),
    Input("search-guru", "value")
)
def update_editable_table(jenis, tahun, session_data, search_value):
    if not session_data:
        return [], [], []

    username = session_data.get("username")
    role = session_data.get("role")

    df = pd.concat(datasets[jenis].values(), ignore_index=True)

    for col in ["Jenis", "Tahun"]:
        if col not in df.columns:
            df[col] = jenis if col == "Jenis" else tahun

    if role == "user":
        nama_user = username.replace("@ses.com", "").strip().lower()
        df["Nama Guru Normalized"] = df["Nama Guru"].astype(str).str.replace(" ", "").str.lower().str.strip()
        df = df[df["Nama Guru Normalized"] == nama_user]

    if role == "admin" and search_value:
        df = df[df["Nama Guru"].astype(str).str.lower().str.contains(search_value.strip().lower())]

    columns = [
        {"name": i, "id": i, "editable": True if role == "admin" else False}
        for i in df.columns if i != "Nama Guru Normalized"
    ]

    style_conditional = []
    if role == "admin":
        style_conditional = [{
            "if": {"column_id": "Nilai"},
            "backgroundColor": "#f9f9f9",
            "color": "#2c3e50",
            "fontWeight": "bold"
        }]

    return df.to_dict("records"), columns, style_conditional

@app.callback(
    Output('login-section', 'style'),
    Output('app-layout', 'style'),
    Input('session-store', 'data')
)
def toggle_layout(session_data):
    if session_data and session_data.get("logged_in"):
        return {"display": "none"}, {"display": "block"}
    return {"display": "block"}, {"display": "none"}

@app.callback(
    Output("admin-controls", "style"),
    Input("session-store", "data")
)
def toggle_admin_controls(session_data):
    if not session_data:
        raise dash.exceptions.PreventUpdate

    role = session_data.get("role", "")
    if role == "admin":
        return {"display": "block"}
    else:
        return {"display": "none"}


@app.callback(
    Output('session-store', 'data'),
    Output('login-message', 'children'),
    Input('btn-login', 'n_clicks'),
    State('input-username', 'value'),
    State('input-password', 'value'),
    prevent_initial_call=True
)
def login(n_clicks, username, password):
    if not username or not password:
        return dash.no_update, "Silakan isi semua kolom."

    if password != "testing123":
        return dash.no_update, "Username atau password salah."

    if username == "admin@ses.com":
        return {"logged_in": True, "username": username, "role": "admin"}, ""

    if username.endswith("@ses.com"):
        nama_user = username.replace("@ses.com", "").strip().lower()

        # ⬇️ Generate valid usernames saat login (bukan di awal)
        valid_usernames = get_all_guru_usernames()

        if nama_user in valid_usernames:
            return {"logged_in": True, "username": username, "role": "user"}, ""
        else:
            return dash.no_update, f"❌ Username '{nama_user}' tidak ditemukan dalam data guru."

    return dash.no_update, "❌ Format username salah. Gunakan format: namaguru@ses.com"

@app.callback(
    Output('session-store', 'clear_data'),
    Input('btn-logout', 'n_clicks'),
    prevent_initial_call=True
)
def logout(n_clicks):
    return True

@app.callback(
    Output("save-status", "children"),
    Input("save-button", "n_clicks"),
    State("editable-table", "data"),
    State("jenis-dropdown", "value"),
    State("tahun-radio", "value"),
    State("session-store", "data"),  # Tambahkan ini
    prevent_initial_call=True
)
def save_edited_data(n_clicks, rows, jenis, tahun, session_data):
    if not session_data or session_data.get("role") != "admin":
        return "❌ Akses ditolak. Hanya admin yang bisa menyimpan."

    if n_clicks == 0:
        raise dash.exceptions.PreventUpdate

    df_updated = pd.DataFrame(rows)
    df_updated["Nilai"] = pd.to_numeric(df_updated["Nilai"], errors="coerce")
    df_updated = df_updated.dropna(subset=["Nama Guru", "Indikator", "Periode"])

    datasets[jenis][tahun] = df_updated

    return "✅ Perubahan berhasil disimpan."

@app.callback(
    Output("editable-table", "data", allow_duplicate=True),
    Input("add-row-button", "n_clicks"),
    State("editable-table", "data"),
    State("input-nama-guru", "value"),
    State("input-indikator", "value"),
    State("input-nilai", "value"),
    State("input-periode", "value"),
    State("input-jenis", "value"),
    State("input-tahun", "value"),
    State("session-store", "data"),  # Tambahkan ini
    prevent_initial_call="initial_duplicate"
)
def tambah_data(n_clicks, data, nama_guru, indikator, nilai, periode, jenis, tahun, session_data):
    if not session_data or session_data.get("role") != "admin":
        raise dash.exceptions.PreventUpdate

    if not all([nama_guru, indikator, nilai, periode, jenis, tahun]):
        raise dash.exceptions.PreventUpdate

    new_row = {
        "Nama Guru": nama_guru,
        "Indikator": indikator,
        "Nilai": nilai,
        "Periode": periode,
        "Jenis": jenis,
        "Tahun": tahun
    }

    return data + [new_row]

@app.callback(
    Output("editable-table", "data", allow_duplicate=True),
    Input("delete-row-button", "n_clicks"),
    State("editable-table", "data"),
    State("editable-table", "selected_rows"),
    State("jenis-dropdown", "value"),
    State("tahun-radio", "value"),
    State("session-store", "data"),  # Tambahkan ini
    prevent_initial_call="initial_duplicate"
)
def delete_row(n_clicks, data, selected_rows, jenis, tahun, session_data):
    if not session_data or session_data.get("role") != "admin":
        raise dash.exceptions.PreventUpdate

    if n_clicks > 0 and selected_rows:
        for idx in sorted(selected_rows, reverse=True):
            data.pop(idx)
        df_updated = pd.DataFrame(data)
        datasets[jenis][tahun] = df_updated

    return data



if __name__ == '__main__':
    print("App dimulai...")
    app.run(debug=True)



