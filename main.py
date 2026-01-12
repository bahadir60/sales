import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime
from dateutil.relativedelta import relativedelta
from pandas.tseries.offsets import MonthEnd

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Paneli V15 (Paylaşımlı)", layout="wide", page_icon="🔒")

DB_FILE = 'eticaret_db_pro_v14.csv'

# ---------------------------------------------------------
# 1. VERİTABANI MOTORU
# ---------------------------------------------------------
def init_db():
    columns = [
        'id', 'Tarih', 'Yil', 'Ay', 'Firma', 'Ulke', 
        'Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder',
        'ACOS', 'TACOS', 'AOV', 'VeriTipi'
    ]
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=columns)
        df.to_csv(DB_FILE, index=False)
        return df
    else:
        df = pd.read_csv(DB_FILE)
        df['Tarih'] = pd.to_datetime(df['Tarih'])
        if 'id' not in df.columns:
            df['id'] = range(1, len(df) + 1)
        if 'VeriTipi' not in df.columns:
            df['VeriTipi'] = 'Bilinmiyor'
        return df

def calculate_metrics(df):
    cols = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder']
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['ACOS'] = df.apply(lambda x: ((x['AdsSpend'] / x['AdsSales']) * 100) if x['AdsSales'] > 0 else 0, axis=1)
    df['TACOS'] = df.apply(lambda x: ((x['AdsSpend'] / x['Sales']) * 100) if x['Sales'] > 0 else 0, axis=1)
    df['AOV'] = df.apply(lambda x: (x['Sales'] / x['Unit']) if x['Unit'] > 0 else 0, axis=1)
    
    df['Tarih'] = pd.to_datetime(df['Tarih'])
    df['Yil'] = df['Tarih'].dt.year
    return df

def save_db(df):
    df.to_csv(DB_FILE, index=False)

def update_database(new_df):
    if new_df.empty: return st.session_state.main_df
    current_df = st.session_state.main_df.copy()
    current_df['Tarih'] = pd.to_datetime(current_df['Tarih'])
    new_df['Tarih'] = pd.to_datetime(new_df['Tarih'])
    
    def create_key(df):
        return df['Tarih'].dt.strftime('%Y-%m-%d') + "_" + df['Firma'].astype(str) + "_" + df['Ulke'].astype(str)

    current_df['unique_key'] = create_key(current_df)
    new_df['unique_key'] = create_key(new_df)
    
    keys_to_remove = new_df['unique_key'].unique()
    current_df_cleaned = current_df[~current_df['unique_key'].isin(keys_to_remove)].copy()
    
    if 'unique_key' in current_df_cleaned.columns: current_df_cleaned = current_df_cleaned.drop(columns=['unique_key'])
    if 'unique_key' in new_df.columns: new_df = new_df.drop(columns=['unique_key'])
        
    final_df = pd.concat([current_df_cleaned, new_df], ignore_index=True)
    final_df['id'] = range(1, len(final_df) + 1)
    final_df = calculate_metrics(final_df)
    save_db(final_df)
    st.session_state.main_df = final_df
    return len(keys_to_remove)

def clean_currency(x):
    if isinstance(x, str):
        clean = x.replace('TL', '').replace('₺', '').replace('%', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(clean)
        except:
            return 0.0
    return x

AYLAR_TR = {'OCAK': 1, 'SUBAT': 2, 'MART': 3, 'NISAN': 4, 'MAYIS': 5, 'HAZIRAN': 6, 'TEMMUZ': 7, 'AGUSTOS': 8, 'EYLUL': 9, 'EKIM': 10, 'KASIM': 11, 'ARALIK': 12}

if 'main_df' not in st.session_state:
    st.session_state.main_df = init_db()

# ---------------------------------------------------------
# 2. GÜVENLİK VE MENÜ YÖNETİMİ
# ---------------------------------------------------------
st.sidebar.title("🔐 Yetkilendirme")

# Şifre Alanı
admin_password = st.sidebar.text_input("Yönetici Şifresi", type="password", placeholder="Misafirseniz boş bırakın")

# Yetki Kontrolü
IS_ADMIN = False
if admin_password == "admin123": # BURADAN ŞİFREYİ DEĞİŞTİREBİLİRSİNİZ
    IS_ADMIN = True
    st.sidebar.success("✅ Yönetici Modu Aktif")
else:
    st.sidebar.info("👁️ İzleyici Modu (Read-Only)")

st.sidebar.markdown("---")
st.sidebar.title("🎛️ Menü")

# Menü Seçeneklerini Yetkiye Göre Belirle
if IS_ADMIN:
    menu_options = ["📊 Dashboard & Düzenleme", "📤 Excel Yükle (Aylık)", "📝 Manuel Giriş (Haftalık/Aylık)", "⚙️ Ayarlar"]
else:
    # Admin değilse sadece Dashboard'u göster
    menu_options = ["📊 Dashboard"]

menu = st.sidebar.radio("Seçim:", menu_options)

# ---------------------------------------------------------
# MODÜL 1: DASHBOARD
# ---------------------------------------------------------
if menu == "📊 Dashboard" or menu == "📊 Dashboard & Düzenleme":
    st.title("📊 Yönetim Paneli")
    df = st.session_state.main_df.copy()
    
    if df.empty:
        st.warning("Veritabanı boş.")
    else:
        # FİLTRELER
        st.sidebar.markdown("---")
        st.sidebar.header("🗓️ Tarih & Kıyaslama")
        today = datetime.date.today()
        
        def get_date_range(preset):
            if preset == "Last 7 Days": return today - datetime.timedelta(days=7), today
            elif preset == "Last 30 Days": return today - datetime.timedelta(days=30), today
            elif preset == "This Month": return today.replace(day=1), today
            elif preset == "Last Month":
                end = today.replace(day=1) - datetime.timedelta(days=1)
                return end.replace(day=1), end
            elif preset == "Last 3 Months": return today - relativedelta(months=3), today
            elif preset == "This Year": return today.replace(month=1, day=1), today
            elif preset == "Last Year": return today.replace(year=today.year-1, month=1, day=1), today.replace(year=today.year-1, month=12, day=31)
            elif preset == "Lifetime": return df['Tarih'].min().date(), df['Tarih'].max().date()
            return today, today

        presets = ["This Month", "Last Month", "Last 7 Days", "Last 30 Days", "Last 3 Months", "This Year", "Last Year", "Lifetime", "Custom Range"]
        sel_preset = st.sidebar.selectbox("Dönem:", presets, index=0)
        
        if sel_preset == "Custom Range":
            dates = st.sidebar.date_input("Tarih Aralığı", (today, today))
            start_date, end_date = dates if len(dates)==2 else (today, today)
        else:
            start_date, end_date = get_date_range(sel_preset)
            
        comp_mode = st.sidebar.radio("Karşılaştırma:", ["Yok", "MoM (Önceki Dönem)", "YoY (Geçen Yıl)"])
        
        prev_start, prev_end, label_prev = None, None, ""
        if comp_mode != "Yok":
            if comp_mode == "YoY (Geçen Yıl)":
                prev_start = start_date - relativedelta(years=1)
                prev_end = end_date - relativedelta(years=1)
                label_prev = "Geçen Yıl"
            else:
                delta = end_date - start_date + datetime.timedelta(days=1)
                prev_end = start_date - datetime.timedelta(days=1)
                prev_start = prev_end - delta + datetime.timedelta(days=1)
                label_prev = "Önceki Dönem"
            st.sidebar.caption(f"Kıyas: {prev_start} - {prev_end}")

        firms = ["Tümü"] + sorted(list(df['Firma'].unique()))
        sel_firm = st.sidebar.selectbox("Firma", firms, key="sf")
        countries = ["Tümü"] + sorted(list(df['Ulke'].unique()))
        sel_country = st.sidebar.selectbox("Ülke", countries, key="sc")
        
        mask_curr = (df['Tarih'].dt.date >= start_date) & (df['Tarih'].dt.date <= end_date)
        df_curr = df.loc[mask_curr].copy()
        
        df_prev = pd.DataFrame()
        if comp_mode != "Yok" and prev_start:
            mask_prev = (df['Tarih'].dt.date >= prev_start) & (df['Tarih'].dt.date <= prev_end)
            df_prev = df.loc[mask_prev].copy()
            
        if sel_firm != "Tümü":
            df_curr = df_curr[df_curr['Firma'] == sel_firm]
            if not df_prev.empty: df_prev = df_prev[df_prev['Firma'] == sel_firm]
        if sel_country != "Tümü":
            df_curr = df_curr[df_curr['Ulke'] == sel_country]
            if not df_prev.empty: df_prev = df_prev[df_prev['Ulke'] == sel_country]

        st.markdown(f"### 🗓️ {start_date} - {end_date}")
        metrics_def = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'TACOS']
        selected_metrics = st.multiselect("Metrikler:", ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'TACOS', 'ACOS', 'AOV'], default=metrics_def)
        
        def get_kpi(d, m):
            if d.empty: return 0
            if m == 'TACOS': return (d['AdsSpend'].sum() / d['Sales'].sum() * 100) if d['Sales'].sum() > 0 else 0
            if m == 'ACOS': return (d['AdsSpend'].sum() / d['AdsSales'].sum() * 100) if d['AdsSales'].sum() > 0 else 0
            if m == 'AOV': return (d['Sales'].sum() / d['Unit'].sum()) if d['Unit'].sum() > 0 else 0
            return d[m].sum()

        if selected_metrics:
            cols = st.columns(len(selected_metrics))
            for i, m in enumerate(selected_metrics):
                c_val = get_kpi(df_curr, m)
                p_val = get_kpi(df_prev, m) if not df_prev.empty else 0
                delta = None
                if comp_mode != "Yok":
                    diff = c_val - p_val
                    pct = (diff / p_val * 100) if p_val > 0 else 0
                    delta = f"{pct:.1f}%"
                fmt = "%.2f%%" if m in ['TACOS', 'ACOS'] else ("%.0f" if m in ['Unit','AdsOrder'] else "%.0f €")
                color = "inverse" if m in ['TACOS', 'ACOS'] else "normal"
                cols[i].metric(m, fmt % c_val, delta, delta_color=color)

        st.markdown("---")

        if comp_mode != "Yok":
            c1, c2 = st.columns([3, 1])
            with c1:
                col_g1, col_g2 = st.columns(2)
                p_metric = col_g1.selectbox("Grafik Verisi:", selected_metrics if selected_metrics else metrics_def, index=0)
                g_mode = col_g2.radio("Gruplama:", ["Ülke", "Firma", "Genel Toplam"], horizontal=True, index=2)
                grp = 'Ulke' if g_mode == "Ülke" else ('Firma' if g_mode == "Firma" else None)
                
                def get_chart_data(d, lbl):
                    if d.empty: return pd.DataFrame()
                    if grp:
                        if p_metric in ['TACOS','ACOS','AOV']:
                            g = d.groupby(grp).apply(lambda x: get_kpi(x, p_metric)).reset_index(name='Value')
                        else:
                            g = d.groupby(grp)[p_metric].sum().reset_index().rename(columns={p_metric:'Value'})
                        g['Grup'] = g[grp]
                    else:
                        g = pd.DataFrame({'Grup': ['Toplam'], 'Value': [get_kpi(d, p_metric)]})
                    g['Dönem'] = lbl
                    return g
                
                d_ch = pd.concat([get_chart_data(df_curr, "Bu Dönem"), get_chart_data(df_prev, label_prev)], ignore_index=True)
                if not d_ch.empty:
                    fig = px.bar(d_ch, x='Grup', y='Value', color='Dönem', barmode='group', text_auto='.2s',
                                 color_discrete_map={"Bu Dönem": "#00CC96", label_prev: "#EF553B"},
                                 title=f"{p_metric} Karşılaştırması")
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
