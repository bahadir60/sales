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
st.set_page_config(page_title="E-Ticaret Paneli V14.1", layout="wide", page_icon="✅")

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
    """
    Aynı Tarih + Firma + Ülke varsa üzerine yazar.
    """
    if new_df.empty: return st.session_state.main_df

    current_df = st.session_state.main_df.copy()
    current_df['Tarih'] = pd.to_datetime(current_df['Tarih'])
    new_df['Tarih'] = pd.to_datetime(new_df['Tarih'])
    
    # Anahtar oluştur
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

AYLAR_TR = {
    'OCAK': 1, 'SUBAT': 2, 'MART': 3, 'NISAN': 4, 'MAYIS': 5, 'HAZIRAN': 6,
    'TEMMUZ': 7, 'AGUSTOS': 8, 'EYLUL': 9, 'EKIM': 10, 'KASIM': 11, 'ARALIK': 12
}

if 'main_df' not in st.session_state:
    st.session_state.main_df = init_db()

# ---------------------------------------------------------
# 2. MENÜ
# ---------------------------------------------------------
st.sidebar.title("🎛️ Menü")
menu = st.sidebar.radio("Seçim:", ["📊 Dashboard & Düzenleme", "📤 Excel Yükle (Aylık)", "📝 Manuel Giriş (Haftalık/Aylık)", "⚙️ Ayarlar"])

# ---------------------------------------------------------
# MODÜL 1: DASHBOARD
# ---------------------------------------------------------
if menu == "📊 Dashboard & Düzenleme":
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
            
        # Karşılaştırma Modu
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

        # Firma/Ülke
        firms = ["Tümü"] + sorted(list(df['Firma'].unique()))
        sel_firm = st.sidebar.selectbox("Firma", firms, key="sf")
        countries = ["Tümü"] + sorted(list(df['Ulke'].unique()))
        sel_country = st.sidebar.selectbox("Ülke", countries, key="sc")
        
        # SÜZME
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

        # --- KPI ---
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

        # --- GRAFİK ---
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
                if not df_curr.empty:
                    st.subheader("💡 3D Analiz")
                    fig3d = px.scatter_3d(df_curr, x='AdsSpend', y='Sales', z='AdsOrder', color='Ulke', size='Unit', opacity=0.8)
                    fig3d.update_layout(margin=dict(l=0,r=0,b=0,t=0))
                    st.plotly_chart(fig3d, use_container_width=True)
        else:
            if not df_curr.empty:
                st.subheader("📈 Zaman İçinde Satış Trendi (Günlük/Aylık)")
                trend = df_curr.groupby('Tarih')['Sales'].sum().reset_index()
                fig = px.bar(trend, x='Tarih', y='Sales', title="Satış Trendi")
                st.plotly_chart(fig, use_container_width=True)

        # --- TABLO ---
        st.subheader("📝 Veri Detayları ve Düzenleme")
        
        edit_cols = ['id', 'Tarih', 'Firma', 'Ulke', 'Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'ACOS', 'TACOS', 'AOV', 'VeriTipi']
        df_edit = df_curr[edit_cols].copy()
        
        # Toplam Satırı
        if not df_edit.empty:
            s = df_edit[['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder']].sum()
            t_row = pd.DataFrame([{
                'id': -1, 'Tarih': pd.to_datetime(end_date), 'Firma': 'TOPLAM', 'Ulke': '-',
                'Sales': s['Sales'], 'Unit': s['Unit'], 'AdsSpend': s['AdsSpend'], 
                'AdsSales': s['AdsSales'], 'AdsOrder': s['AdsOrder'],
                'ACOS': (s['AdsSpend']/s['AdsSales']*100) if s['AdsSales']>0 else 0,
                'TACOS': (s['AdsSpend']/s['Sales']*100) if s['Sales']>0 else 0,
                'AOV': (s['Sales']/s['Unit']) if s['Unit']>0 else 0,
                'VeriTipi': '-'
            }])
            df_show = pd.concat([df_edit, t_row], ignore_index=True)
        else:
            df_show = df_edit

        edited = st.data_editor(
            df_show,
            column_config={
                "id": st.column_config.NumberColumn(disabled=True),
                "Tarih": st.column_config.DateColumn(format="DD.MM.YYYY"),
                "ACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                "TACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                "AOV": st.column_config.NumberColumn(format="%.2f €", disabled=True),
                "Sales": st.column_config.NumberColumn(format="%.2f €"),
                "AdsSpend": st.column_config.NumberColumn(format="%.2f €")
            },
            hide_index=True, use_container_width=True, num_rows="dynamic"
        )
        
        if st.button("💾 Kaydet"):
            try:
                master = st.session_state.main_df.copy()
                for i, r in edited.iterrows():
                    if r['id'] == -1 or pd.isna(r['id']): continue
                    mask = master['id'] == r['id']
                    if mask.any():
                        for c in ['Sales','Unit','AdsSpend','AdsSales','AdsOrder','Firma','Ulke','Tarih','VeriTipi']:
                            master.loc[mask, c] = r[c]
                
                master = calculate_metrics(master)
                save_db(master)
                st.session_state.main_df = master
                st.success("Veritabanı güncellendi.")
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

# ---------------------------------------------------------
# MODÜL 2: EXCEL YÜKLEME (AY SONUNA KAYIT - DÜZELTİLDİ)
# ---------------------------------------------------------
elif menu == "📤 Excel Yükle (Aylık)":
    st.title("📤 Aylık Excel Verisi Yükle")
    st.info("⚠️ DİKKAT: Excel'den yüklenen veriler otomatik olarak **Ayın Son Gününe** (Örn: 31 Ocak) kaydedilir.")
    
    uploaded_file = st.file_uploader("Dosya Seç", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            xls = pd.read_excel(uploaded_file, sheet_name=None)
            sheet_names = list(xls.keys())
            st.divider()
            c1, c2 = st.columns(2)
            selected_sheet = c1.selectbox("Sekme (Ay)", sheet_names)
            
            sheet_clean = selected_sheet.upper().replace('İ','I').replace('Ş','S').replace('Ç','C').replace('Ğ','G').replace('Ü','U').replace('Ö','O')
            month_num = 0
            for ay_ad, ay_no in AYLAR_TR.items():
                if ay_ad in sheet_clean:
                    month_num = ay_no
                    break
            if month_num == 0:
                month_num = c2.number_input("Ay No (1-12):", 1, 12)
            else:
                c2.success(f"Algılanan Ay: {month_num}")

            df_temp = xls[selected_sheet].copy()
            # --- HATA DÜZELTMESİ (any() kullanımı) ---
            h_row = 0
            for i, row in df_temp.head(10).iterrows():
                # Satırdaki tüm değerleri string listesine çevirip kontrol et
                row_str_list = row.astype(str).str.lower().tolist()
                if any('firm' in s for s in row_str_list):
                    h_row = i + 1
                    break
            
            if h_row > 0: 
                df_temp = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=h_row)
            
            df_temp = df_temp.dropna(how='all')
            cols = df_temp.columns.tolist()
            
            st.subheader("🔗 Sütun Eşleştirme")
            def get_col(keys, cols):
                for i, c in enumerate(cols):
                    if any(k in str(c).lower() for k in keys): return i
                return 0

            c_id, c_25, c_24 = st.columns(3)
            with c_id:
                map_firm = st.selectbox("Firma", cols, index=get_col(['firm'], cols))
                map_country = st.selectbox("Ülke", cols, index=get_col(['country', 'ulke'], cols))
            with c_25:
                st.markdown("**2025**")
                map_s25 = st.selectbox("Sales 25", cols, index=get_col(['2025 sales', 'sales'], cols))
                map_u25 = st.selectbox("Unit 25", cols, index=get_col(['2025 unit', 'unit'], cols))
                map_sp25 = st.selectbox("Spend 25", cols, index=get_col(['2025 ads spend', 'ads spend'], cols))
                map_as25 = st.selectbox("Ad Sales 25", cols, index=get_col(['2025 ads sales', 'ads sales'], cols))
                map_ao25 = st.selectbox("Ad Order 25", cols, index=get_col(['2025 ads order', 'ads order'], cols))
            with c_24:
                st.markdown("**2024**")
                map_s24 = st.selectbox("Sales 24", cols, index=get_col(['2024 sales'], cols))
                map_u24 = st.selectbox("Unit 24", cols, index=get_col(['2024 unit'], cols))
                map_sp24 = st.selectbox("Spend 24", cols, index=get_col(['2024 ads spend'], cols))
                map_as24 = st.selectbox("Ad Sales 24", cols, index=get_col(['2024 ads sales'], cols))
                map_ao24 = st.selectbox("Ad Order 24", cols, index=get_col(['2024 ads order'], cols))

            if st.button("💾 Veritabanını Güncelle"):
                # 2025 -> AY SONU TARİHİ HESAPLA
                date_2025 = pd.to_datetime(f"2025-{month_num}-01") + MonthEnd(0)
                
                d1 = pd.DataFrame()
                d1['Firma'] = df_temp[map_firm]
                d1['Ulke'] = df_temp[map_country]
                d1['Tarih'] = date_2025
                d1['VeriTipi'] = 'Aylık'
                for c,m in zip(['Sales','Unit','AdsSpend','AdsSales','AdsOrder'],[map_s25,map_u25,map_sp25,map_as25,map_ao25]):
                    d1[c] = df_temp[m].apply(clean_currency)
                
                # 2024 -> AY SONU TARİHİ HESAPLA
                date_2024 = pd.to_datetime(f"2024-{month_num}-01") + MonthEnd(0)
                
                d2 = pd.DataFrame()
                d2['Firma'] = df_temp[map_firm]
                d2['Ulke'] = df_temp[map_country]
                d2['Tarih'] = date_2024
                d2['VeriTipi'] = 'Aylık'
                for c,m in zip(['Sales','Unit','AdsSpend','AdsSales','AdsOrder'],[map_s24,map_u24,map_sp24,map_as24,map_ao24]):
                    d2[c] = df_temp[m].apply(clean_currency)
                
                comb = pd.concat([d1, d2], ignore_index=True)
                comb = comb.dropna(subset=['Firma'])
                comb = comb[comb['Sales'] > 0]
                comb = comb[~comb['Firma'].astype(str).str.contains('Toplam', case=False)]
                
                cnt = update_database(comb)
                st.success(f"Başarılı! {len(comb)} satır işlendi. ({cnt} kayıt güncellendi)")

        except Exception as e:
            st.error(f"Hata: {e}")

# ---------------------------------------------------------
# MODÜL 3: MANUEL GİRİŞ
# ---------------------------------------------------------
elif menu == "📝 Manuel Giriş (Haftalık/Aylık)":
    st.title("📝 Manuel Giriş")
    st.info("Haftalık veri giriyorsanız, lütfen **haftanın son gününü** tarih olarak seçiniz.")
    
    with st.form("man"):
        c1, c2, c3 = st.columns(3)
        d = c1.date_input("Veri Tarihi", datetime.date.today())
        f = c2.text_input("Firma", "HomeByHome")
        cnt = c3.text_input("Ülke", "DE")
        
        c_type = st.selectbox("Veri Tipi:", ["Haftalık", "Aylık", "Günlük"])
        
        st.markdown("---")
        c4, c5, c6 = st.columns(3)
        s = c4.number_input("Sales", min_value=0.0)
        u = c5.number_input("Unit", min_value=0)
        sp = c6.number_input("Ads Spend", min_value=0.0)
        
        c7, c8 = st.columns(2)
        asl = c7.number_input("Ads Sales", min_value=0.0)
        ao = c8.number_input("Ads Order", min_value=0)
        
        if st.form_submit_button("Kaydet"):
            row = {
                'Tarih': pd.to_datetime(d), 'Firma': f, 'Ulke': cnt, 
                'Sales': s, 'Unit': u, 'AdsSpend': sp, 'AdsSales': asl, 'AdsOrder': ao,
                'VeriTipi': c_type
            }
            update_database(pd.DataFrame([row]))
            st.success("Kaydedildi.")

# ---------------------------------------------------------
# MODÜL 4: AYARLAR
# ---------------------------------------------------------
elif menu == "⚙️ Ayarlar":
    st.title("⚙️ Ayarlar")
    if st.button("🗑️ Veritabanını SIFIRLA"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.session_state.main_df = init_db()
        st.success("Veritabanı tamamen temizlendi.")
        st.rerun()
