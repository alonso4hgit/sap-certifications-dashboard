import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import requests
import io

st.set_page_config(
    page_title="SAP Partner Certification Monitor — Enable Group",
    page_icon="📊",
    layout="wide",
)

DATA_DIR    = Path(__file__).parent / "data"
CSV_FILE    = DATA_DIR / "sap_certifications.csv"
ASSETS_DIR  = Path(__file__).parent / "assets"

FILIAL_COLORS = {
    "Enable, S.C.": "#0070F3",
    "ENABLE EUROPA SL": "#FF6B35",
    "Enable Peru S.A.C.": "#7C3AED",
    "Enable Chile SPA": "#059669",
}

# Requisitos SAP Competency Framework (Solution Consultants)
# Fuente: competency_specialization_requirements, January 2026
COMP_REQUIREMENTS = {
    "SAP Cloud ERP":                      {"essential": 3, "advanced": 5, "expert": 10},
    "SAP Cloud ERP Private":              {"essential": 3, "advanced": 5, "expert": 10},
    "ERP for Small & Midsize Enterprises":{"essential": 3, "advanced": 5, "expert": 10},
    "SAP Business Technology Platform":   {"essential": 3, "advanced": 5, "expert": 10},
    "Human Capital Management":           {"essential": 3, "advanced": 5, "expert": 10},
    "Customer Relationship Management":   {"essential": 3, "advanced": 5, "expert": 10},
    "Business Transformation Management": {"essential": 3, "advanced": 5, "expert": 10},
}

GITHUB_RAW_URL = "https://raw.githubusercontent.com/alonso4hgit/sap-certifications-dashboard/main/data/sap_certifications.csv"

@st.cache_data(ttl=300)
def load_data():
    # Intenta leer desde GitHub (producción)
    try:
        token = st.secrets["GITHUB_TOKEN"]
        headers = {"Authorization": f"token {token}"}
        resp = requests.get(GITHUB_RAW_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
    except Exception:
        # Fallback: archivo local (desarrollo)
        if CSV_FILE.exists():
            df = pd.read_csv(CSV_FILE)
        else:
            return None
    df["dateIssued"]     = pd.to_datetime(df["dateIssued"],     errors="coerce")
    df["dateExpiration"] = pd.to_datetime(df["dateExpiration"], errors="coerce")
    df["subSolutionAreaName"] = df["subSolutionAreaName"].fillna("Other")
    df["competencyName"]      = df["competencyName"].fillna("Other")
    df["partnerAccountName"]  = df["partnerAccountName"].str.strip()
    return df

# ── Carga de datos ────────────────────────────────────────────────────────────
df = load_data()
if df is None:
    st.error("No se pudo cargar el archivo de datos. Verifica el token de GitHub en Secrets.")
    st.stop()

# ── Sidebar filters ──────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Filtros")

    filiales = ["Todas"] + sorted(df["partnerAccountName"].dropna().unique().tolist())
    selected_filial = st.selectbox("Filial", filiales)

    competencies = ["Todas"] + sorted(df["competencyName"].dropna().unique().tolist())
    selected_comp = st.selectbox("Competency", competencies)

    areas = ["Todas"] + sorted(df["subSolutionAreaName"].dropna().unique().tolist())
    selected_area = st.selectbox("Sub-Solution Area", areas)

    st.markdown("---")
    _mtime_cst = pd.Timestamp(CSV_FILE.stat().st_mtime, unit="s", tz="UTC").tz_convert("America/Mexico_City")
    st.caption(f"Datos al: {_mtime_cst.strftime('%d/%m/%Y %H:%M')} CST")
    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

# ── Apply filters ────────────────────────────────────────────────────────────
filtered = df.copy()
if selected_filial != "Todas":
    filtered = filtered[filtered["partnerAccountName"] == selected_filial]
if selected_comp != "Todas":
    filtered = filtered[filtered["competencyName"] == selected_comp]
if selected_area != "Todas":
    filtered = filtered[filtered["subSolutionAreaName"] == selected_area]

# ── Header ───────────────────────────────────────────────────────────────────
import base64 as _b64
_logo_b64 = _b64.b64encode((ASSETS_DIR / "enable_logo.png").read_bytes()).decode()
_sap_svg   = "https://upload.wikimedia.org/wikipedia/commons/5/59/SAP_2011_logo.svg"

st.markdown(
    f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                padding:16px 0 8px 0;border-bottom:2px solid #E5E7EB;margin-bottom:16px">
      <img src="data:image/png;base64,{_logo_b64}" style="height:56px;object-fit:contain">
      <div style="text-align:center">
        <div style="font-size:30px;font-weight:800;color:#1F2937;letter-spacing:-0.5px">
          SAP Partner Certification Monitor
        </div>
        <div style="font-size:13px;color:#6B7280;margin-top:2px">
          Enable Group &nbsp;·&nbsp; 4 filiales &nbsp;·&nbsp; Competency Framework Status
        </div>
      </div>
      <img src="{_sap_svg}" style="height:44px;object-fit:contain">
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(f"Mostrando {len(filtered)} de {len(df)} certificaciones totales")

# ── KPI Cards ────────────────────────────────────────────────────────────────
today = pd.Timestamp.today()
exp_soon = filtered[(filtered["dateExpiration"].notna()) & ((filtered["dateExpiration"] - today).dt.days < 30) & ((filtered["dateExpiration"] - today).dt.days >= 0)]

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Certifications", len(filtered))
with col2:
    st.metric("Personas Certificadas", filtered["certifiedUserName"].nunique())
with col3:
    st.metric("Áreas de Solución", filtered["subSolutionAreaName"].nunique())
with col4:
    st.metric("Filiales", filtered["partnerAccountName"].nunique())
with col5:
    st.metric("🔴 Por vencer (<30d)", len(exp_soon), delta=None)

st.markdown("---")

# ── Charts Row 1 ─────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Certificaciones por Filial")
    filial_data = filtered.groupby("partnerAccountName").size().reset_index(name="count")
    filial_data = filial_data.sort_values("count", ascending=True)
    colors = [FILIAL_COLORS.get(f, "#6B7280") for f in filial_data["partnerAccountName"]]
    fig_filial = go.Figure(go.Bar(
        x=filial_data["count"],
        y=filial_data["partnerAccountName"],
        orientation="h",
        marker_color=colors,
        text=filial_data["count"],
        textposition="auto",
    ))
    fig_filial.update_layout(
        margin=dict(l=0, r=50, t=10, b=0),
        height=300,
        xaxis_title="",
        yaxis_title="",
        plot_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#F3F4F6"),
    )
    st.plotly_chart(fig_filial, use_container_width=True)

with col_right:
    st.subheader("Próximas a vencer por persona")
    expiring = filtered[filtered["dateExpiration"].notna()].copy()
    expiring["days_left"] = (expiring["dateExpiration"] - today).dt.days
    expiring = expiring.sort_values("days_left")
    expiring = expiring[expiring["days_left"] <= 365].head(10)

    if len(expiring) == 0:
        st.info("No hay certificaciones venciendo en los próximos 12 meses.")
    else:
        for _, row in expiring.iterrows():
            d = int(row["days_left"])
            color = "#DC2626" if d < 30 else ("#D97706" if d < 90 else "#059669")
            label = "Vencida" if d < 0 else f"{d}d"
            badge_bg = "#FEE2E2" if d < 30 else ("#FEF3C7" if d < 90 else "#D1FAE5")
            name = str(row["certifiedUserName"]).title()
            cert = row["certificationId"]
            filial = row["partnerAccountName"].replace("Enable, S.C.", "S.C.").replace("ENABLE EUROPA SL", "Europa").replace("Enable Peru S.A.C.", "Perú").replace("Enable Chile SPA", "Chile")
            st.markdown(
                f"""<div style="display:flex;justify-content:space-between;align-items:center;
                padding:6px 8px;margin-bottom:4px;border-radius:6px;background:#F9FAFB;border-left:3px solid {color}">
                <div style="font-size:13px"><b>{name}</b><br>
                <span style="color:#6B7280;font-size:11px">{cert} · {filial}</span></div>
                <span style="background:{badge_bg};color:{color};font-weight:700;font-size:12px;
                padding:2px 8px;border-radius:12px">{label}</span></div>""",
                unsafe_allow_html=True
            )

# ── Charts Row 2 ─────────────────────────────────────────────────────────────
st.subheader("Certificaciones por Sub-Solution Area y Filial")
area_filial = filtered.groupby(["subSolutionAreaName", "partnerAccountName"]).size().reset_index(name="count")
area_filial = area_filial.sort_values("count", ascending=False)
fig_area = px.bar(
    area_filial,
    x="subSolutionAreaName",
    y="count",
    color="partnerAccountName",
    color_discrete_map=FILIAL_COLORS,
    text="count",
    barmode="stack",
    labels={"subSolutionAreaName": "", "count": "Certificaciones", "partnerAccountName": "Filial"},
)
fig_area.update_layout(
    margin=dict(l=0, r=0, t=10, b=120),
    height=380,
    xaxis_tickangle=-35,
    plot_bgcolor="white",
    yaxis=dict(showgrid=True, gridcolor="#F3F4F6"),
)
fig_area.update_traces(textposition="inside")
st.plotly_chart(fig_area, use_container_width=True)

# ── Expiration section ────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Estado de Vencimiento")
exp = filtered[filtered["dateExpiration"].notna()].copy()
exp["days_left"] = (exp["dateExpiration"] - today).dt.days
exp["status"] = exp["days_left"].apply(
    lambda d: "🔴 Vencida / <30d" if d < 30 else ("🟡 Por vencer (<90d)" if d < 90 else "🟢 Vigente")
)
status_counts = exp["status"].value_counts().reset_index()
status_counts.columns = ["status", "count"]

c1, c2, c3 = st.columns(3)
for col, label in zip([c1, c2, c3], ["🟢 Vigente", "🟡 Por vencer (<90d)", "🔴 Vencida / <30d"]):
    val = status_counts[status_counts["status"] == label]["count"].sum() if len(status_counts) else 0
    col.metric(label, int(val))

# Tabla de las que vencen pronto
if len(exp_soon) > 0:
    st.markdown("**Certificaciones próximas a vencer:**")
    exp_table = exp_soon[["partnerAccountName", "certifiedUserName", "certificationId",
                            "certificationName", "dateExpiration"]].copy()
    exp_table = exp_table.rename(columns={
        "partnerAccountName": "Filial", "certifiedUserName": "Nombre",
        "certificationId": "Cert ID", "certificationName": "Nombre Certificación",
        "dateExpiration": "Vence"
    })
    exp_table = exp_table.sort_values("Vence")
    st.dataframe(
        exp_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Vence": st.column_config.DateColumn("Vence", format="DD/MM/YYYY"),
        },
    )

# ── Competency Framework ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Competency Framework — Personas certificadas por competencia")
st.caption("Requisito SAP: Essential = 3 · Advanced = 5 · Expert = 10 consultores únicos  ·  Conteo global: un consultor en varias filiales = 1 persona")

# Certs válidas por competencia — Fuente: partneredge.sap.com/en/partnership/manage/competency/requirements.html
# Rol: Solution Consultant · Extraído marzo 2026
VALID_CERTS = {
    "SAP Cloud ERP": {
        "C_S4CPR", "C_S4CS", "C_S4CFI", "C_S4CCO", "C_S4CPB",
    },
    "SAP Cloud ERP Private": {
        "C_TS412", "C_IEE2E", "C_S43", "C_TS422", "C_TS452",
        "C_TS462", "C_TS4CO", "C_TS4FI", "C_TS470",
    },
    "ERP for Small & Midsize Enterprises": set(),  # Not available at present
    "Supply Chain Management": {
        "C_FSM", "C_IBP", "C_S4EWM", "C_S4TM", "C_ARCIG", "C_ARSCC",
    },
    "Human Capital Management": {
        "C_THR86", "C_THR87", "C_THR70", "C_THR81", "C_HRHPC",
        "C_THR94", "C_THR92", "C_THR88", "C_THR95", "C_THR97",
        "C_THR84", "C_THR83", "C_THR82", "C_THR85",
    },
    "Customer Relationship Management": {
        "C_C4H32", "P_C4H34", "C_C4H62", "C_C4H63",
        "C_C4H22", "C_C4H47", "C_C4H56",
    },
    "Spend Management": {
        "C_ARP2P", "C_ARSOR", "C_ARCON", "C_ARSUM", "C_TFG51", "C_TFG61",
    },
    "SAP Business Technology Platform": {
        "C_SAC", "C_CPI", "C_CPE", "C_ABAPD", "C_LCNC",
        "P_BTPA", "C_FIORD", "C_DBADM", "C_HAMOD", "C_BW4H", "C_BCBDC",
    },
    "Business Transformation Management": {
        "C_SIGDA", "C_SIGPM", "C_LIXEA", "C_WME",
    },
}

ALL_VALID_CERTS = set().union(*VALID_CERTS.values())

# Personas únicas por competency — dataset COMPLETO, usando IDs exactos del portal SAP
df_comp = df[df["certificationId"].isin(ALL_VALID_CERTS)]
# Contar personas únicas por competencia usando los cert IDs exactos del portal
comp_rows = []
for comp_name, cert_ids in VALID_CERTS.items():
    if not cert_ids:
        continue
    people = (
        df[df["certificationId"].isin(cert_ids)]["certifiedUserName"]
        .str.upper().str.strip().nunique()
    )
    comp_rows.append({"competency": comp_name, "people": people})
comp_people = pd.DataFrame(comp_rows)

for _, row in comp_people.sort_values("people", ascending=False).iterrows():
    comp = row["competency"]
    count = int(row["people"])
    req = COMP_REQUIREMENTS.get(comp)
    if req is None:
        continue

    req_ess = req["essential"]
    req_adv = req["advanced"]
    req_exp = req["expert"]

    if count >= req_exp:
        level, level_color, level_bg = "EXPERT",    "#059669", "#D1FAE5"
    elif count >= req_adv:
        level, level_color, level_bg = "ADVANCED",  "#2563EB", "#DBEAFE"
    elif count >= req_ess:
        level, level_color, level_bg = "ESSENTIAL", "#D97706", "#FEF3C7"
    else:
        level, level_color, level_bg = f"Faltan {req_ess - count}", "#DC2626", "#FEE2E2"

    pct = min(count / req_exp * 100, 100)

    # Cert ID badges para mostrar en la card
    cert_ids_sorted = sorted(VALID_CERTS.get(comp, set()))
    cert_tags = " ".join([
        f'<span style="background:#E5E7EB;color:#374151;font-size:10px;'
        f'padding:1px 7px;border-radius:4px;font-family:monospace;white-space:nowrap">{c}</span>'
        for c in cert_ids_sorted
    ])

    st.markdown(
        f"""<div style="margin-bottom:4px;padding:10px 14px;background:#F9FAFB;border-radius:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span style="font-weight:600;font-size:14px">{comp}</span>
          <div style="display:flex;align-items:center;gap:10px">
            <span style="font-size:13px;color:#374151"><b>{count}</b> personas</span>
            <span style="background:{level_bg};color:{level_color};font-weight:700;
              font-size:11px;padding:2px 10px;border-radius:12px">{level}</span>
          </div>
        </div>
        <div style="background:#E5E7EB;border-radius:4px;height:8px">
          <div style="background:{level_color};width:{pct:.0f}%;height:8px;border-radius:4px"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:3px;font-size:10px;color:#9CA3AF">
          <span>0</span><span>Essential {req_ess}</span><span>Advanced {req_adv}</span><span>Expert {req_exp}</span>
        </div>
        <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px">{cert_tags}</div>
        </div>""",
        unsafe_allow_html=True
    )

    # Popup de consultores
    comp_cert_ids = VALID_CERTS.get(comp, set())
    comp_consultants = df[df["certificationId"].isin(comp_cert_ids)].copy()
    comp_consultants["_name_key"] = comp_consultants["certifiedUserName"].str.upper().str.strip()

    consultant_rows = []
    for name_key, grp in comp_consultants.groupby("_name_key"):
        display_name = grp["certifiedUserName"].iloc[0]
        certs_held   = ", ".join(sorted(grp["certificationId"].unique()))
        filiales     = ", ".join(sorted(grp["partnerAccountName"].unique()))
        # fecha de vencimiento más próxima de sus certs en esta competencia
        next_exp = grp["dateExpiration"].dropna().min()
        if pd.notna(next_exp):
            days_left = (next_exp - today).days
            if days_left < 0:
                semaforo = "🔴"
            elif days_left < 30:
                semaforo = "🔴"
            elif days_left < 90:
                semaforo = "🟡"
            else:
                semaforo = "🟢"
            exp_str = next_exp.strftime("%d/%m/%Y")
        else:
            semaforo, exp_str = "🟢", "—"

        consultant_rows.append({
            " ": semaforo,
            "Consultor":   display_name,
            "Cert ID(s)":  certs_held,
            "Filial(es)":  filiales,
            "Vence":       exp_str,
        })

    with st.expander(f"👥 Ver {count} consultores — {comp}"):
        if consultant_rows:
            st.dataframe(
                pd.DataFrame(consultant_rows),
                hide_index=True,
                use_container_width=True,
                column_config={" ": st.column_config.TextColumn(" ", width=30)},
            )
        else:
            st.info("Sin consultores registrados.")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── Data Table ────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Detalle de Certificaciones")

search = st.text_input("🔍 Buscar (nombre, certificación, producto...)", "")
display_cols = ["partnerAccountName", "certifiedUserName", "subSolutionAreaName",
                "logicalProductName", "certificationId", "certificationName",
                "competencyName", "dateIssued", "dateExpiration"]
show_df = filtered[display_cols].copy()

def _semaforo(exp_date):
    if pd.isna(exp_date):
        return "🟢"
    d = (exp_date - today).days
    if d < 30:
        return "🔴"
    elif d < 90:
        return "🟡"
    return "🟢"

show_df.insert(0, "🚦", show_df["dateExpiration"].apply(_semaforo))
show_df = show_df.rename(columns={
    "partnerAccountName": "Filial", "certifiedUserName": "Nombre",
    "subSolutionAreaName": "Área", "logicalProductName": "Producto",
    "certificationId": "Cert ID", "certificationName": "Nombre Certificación",
    "competencyName": "Competency", "dateIssued": "Fecha Emisión",
    "dateExpiration": "Fecha Vencimiento"
})

if search:
    mask = show_df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
    show_df = show_df[mask]

st.dataframe(
    show_df,
    use_container_width=True,
    height=400,
    hide_index=True,
    column_config={
        "🚦":                st.column_config.TextColumn("🚦", width=30),
        "Fecha Emisión":     st.column_config.DateColumn("Fecha Emisión",     format="DD/MM/YYYY"),
        "Fecha Vencimiento": st.column_config.DateColumn("Fecha Vencimiento", format="DD/MM/YYYY"),
    },
)
st.caption(f"{len(show_df)} registros mostrados")
