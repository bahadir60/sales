import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import datetime
from dateutil.relativedelta import relativedelta

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Yönetim Paneli V12", layout="wide", page_icon="💎")

DB_FILE = 'eticaret_db_pro_v12.csv'

# ---------------------------------------------------------
# 1. VERİTABANI MOTORU
# ---------------------------------------------------------
def init_db():
    columns = [
        'id', 'Tarih', 'Yil', 'Ay', 'Firma', 'Ulke', 
        'Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder',
        'ACOS', 'TACOS', 'AOV'
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
    final_df.to_csv(DB_FILE, index=False)
    st.session_state.main_df = final_df
    return len(keys_to_remove)

def save_db(df):
    df.to_csv(DB_FILE, index=False)

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
menu = st.sidebar.radio("Seçim:", ["📊 Dashboard & Düzenleme", "📤 Excel Yükle", "📝 Manuel Giriş", "⚙️ Ayarlar"])

# ---------------------------------------------------------
# YARDIMCI: TARİH VE GRAFİK STİLİ
# ---------------------------------------------------------
def get_date_range(preset):
    today = datetime.date.today()
    if preset == "Last 7 Days": return today - datetime.timedelta(days=7), today
    elif preset == "Last 30 Days": return today - datetime.timedelta(days=30), today
    elif preset == "This Month": return today.replace(day=1), today
    elif preset == "Last Month":
        last_month_end = today.replace(day=1) - datetime.timedelta(days=1)
        return last_month_end.replace(day=1), last_month_end
    elif preset == "Last 3 Months": return today - relativedelta(months=3), today
    elif preset == "This Year": return today.replace(month=1, day=1), today
    elif preset == "Last Year":
        return today.replace(year=today.year-1, month=1, day=1), today.replace(year=today.year-1, month=12, day=31)
    elif preset == "Lifetime": return None, None
    return today, today

def style_figure(fig, title):
    """Grafik Kalitesini Artıran Fonksiyon"""
    fig.update_layout(
        title={
            'text': title,
            'y':0.95, 'x':0.5,
            'xanchor': 'center', 'yanchor': 'top',
            'font': dict(size=20, color='black')
        },
        font=dict(family="Arial, sans-serif", size=14, color="black"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=20),
        # Arka planı temizle
        paper_bgcolor='white',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    return fig

# ---------------------------------------------------------
# MODÜL 1: DASHBOARD
# ---------------------------------------------------------
if menu == "📊 Dashboard & Düzenleme":
    st.title("📊 Yönetim Paneli")
    df = st.session_state.main_df.copy()
    
    if df.empty:
        st.warning("Veritabanı boş.")
    else:
        # --- SOL FİLTRELER ---
        st.sidebar.markdown("---")
        st.sidebar.header("🗓️ Filtreler")
        
        date_presets = ["This Month", "Last Month", "Last 7 Days", "Last 30 Days", "Last 3 Months", "This Year", "Last Year", "Lifetime", "Custom Range"]
        selected_preset = st.sidebar.selectbox("Dönem:", date_presets, index=0)
        
        if selected_preset == "Custom Range":
            custom_dates = st.sidebar.date_input("Tarih Aralığı", (datetime.date.today(), datetime.date.today()))
            start_date, end_date = custom_dates if len(custom_dates)==2 else (datetime.date.today(), datetime.date.today())
        else:
            s_temp, e_temp = get_date_range(selected_preset)
            if s_temp is None:
                start_date, end_date = df['Tarih'].min().date(), df['Tarih'].max().date()
            else:
                start_date, end_date = s_temp, e_temp
        
        comp_mode = st.sidebar.radio("Karşılaştırma:", ["Yok", "MoM (Önceki Dönem)", "YoY (Geçen Yıl)"])
        
        prev_start, prev_end = None, None
        label_prev = ""
        if comp_mode != "Yok":
            if comp_mode == "YoY (Geçen Yıl)":
                prev_start, prev_end = start_date - relativedelta(years=1), end_date - relativedelta(years=1)
                label_prev = "Geçen Yıl"
            else:
                delta = end_date - start_date + datetime.timedelta(days=1)
                prev_end = start_date - datetime.timedelta(days=1)
                prev_start = prev_end - delta + datetime.timedelta(days=1)
                label_prev = "Önceki Dönem"
            st.sidebar.caption(f"Kıyas: {prev_start} / {prev_end}")

        firms = ["Tümü"] + sorted(list(df['Firma'].unique()))
        countries = ["Tümü"] + sorted(list(df['Ulke'].unique()))
        sel_firm = st.sidebar.selectbox("Firma", firms, key="sf_dash")
        sel_country = st.sidebar.selectbox("Ülke", countries, key="sc_dash")
        
        # Veri Süzme
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

        # --- KPI KARTLARI ---
        st.markdown(f"### 📈 Özet: {start_date} - {end_date}")
        
        cols = st.columns(5)
        kpi_metrics = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'TACOS']
        
        def get_val(d, m):
            if d.empty: return 0
            if m == 'TACOS': return (d['AdsSpend'].sum() / d['Sales'].sum() * 100) if d['Sales'].sum() > 0 else 0
            return d[m].sum()

        for i, m in enumerate(kpi_metrics):
            curr = get_val(df_curr, m)
            prev = get_val(df_prev, m) if not df_prev.empty else 0
            
            delta_str = None
            if comp_mode != "Yok":
                diff = curr - prev
                pct = (diff / prev * 100) if prev > 0 else 0
                delta_str = f"{pct:.1f}%"
            
            fmt = "%.2f%%" if m=='TACOS' else ("%.0f €" if m in ['Sales','AdsSpend','AdsSales'] else "%.0f")
            color = "inverse" if m=='TACOS' else "normal"
            cols[i].metric(m, fmt % curr, delta_str, delta_color=color)
            
        st.markdown("---")

        # --- GELİŞMİŞ GRAFİK ALANI ---
        if comp_mode != "Yok":
            c_g1, c_g2 = st.columns([2, 1])
            with c_g1:
                plot_m = st.selectbox("Grafik Verisi:", ['Sales', 'Unit', 'AdsSpend', 'TACOS', 'ACOS', 'AOV'])
                grp = 'Ulke' if sel_firm != "Tümü" else 'Firma'
                
                # Grafik Verisi
                def prep_data(d, lbl):
                    if d.empty: return pd.DataFrame()
                    if plot_m in ['TACOS','ACOS','AOV']:
                        # Weighted Avg
                        g = d.groupby(grp).apply(lambda x: get_val(x, plot_m)).reset_index(name='Value')
                    else:
                        g = d.groupby(grp)[plot_m].sum().reset_index().rename(columns={plot_m:'Value'})
                    g['Dönem'] = lbl
                    return g
                
                d_chart = pd.concat([prep_data(df_curr,"Bu Dönem"), prep_data(df_prev,label_prev)], ignore_index=True)
                
                if not d_chart.empty:
                    fig = px.bar(d_chart, x=grp, y='Value', color='Dönem', barmode='group',
                                 text_auto='.2s', color_discrete_map={"Bu Dönem": "#00CC96", label_prev: "#EF553B"})
                    fig = style_figure(fig, f"{grp} Bazlı {plot_m} Karşılaştırması")
                    st.plotly_chart(fig, use_container_width=True)
            
            with c_g2:
                # 3D GRAFİK SEÇENEĞİ
                chart_type = st.radio("Grafik Türü:", ["2D Scatter", "3D Scatter"], horizontal=True)
                
                if not df_curr.empty:
                    if chart_type == "3D Scatter":
                        fig2 = px.scatter_3d(df_curr, x='AdsSpend', y='Sales', z='AdsOrder', color='Ulke',
                                             size='Unit', hover_name='Firma', opacity=0.8)
                        fig2.update_layout(title="3D Analiz: Harcama - Ciro - Sipariş", margin=dict(l=0, r=0, b=0, t=30))
                    else:
                        fig2 = px.scatter(df_curr, x="AdsSpend", y="Sales", size="AdsOrder", color="Ulke", 
                                          hover_name="Firma", title="Harcama vs Ciro (2D)")
                        fig2 = style_figure(fig2, "Harcama vs Ciro")
                    
                    st.plotly_chart(fig2, use_container_width=True)
        
        else:
            # Trend Grafiği (Zaman İçinde)
            if not df_curr.empty:
                trend_data = df_curr.groupby('Tarih')['Sales'].sum().reset_index()
                fig = px.line(trend_data, x='Tarih', y='Sales', markers=True, line_shape='spline')
                fig = style_figure(fig, "Zaman İçinde Satış Trendi")
                fig.update_traces(line_color='#636EFA', line_width=3)
                st.plotly_chart(fig, use_container_width=True)

        # --- DÜZENLENEBİLİR TABLO ---
        st.subheader("📝 Veri Detayları ve Düzenleme")
        
        edit_cols = ['id', 'Tarih', 'Firma', 'Ulke', 'Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'ACOS', 'TACOS', 'AOV']
        df_edit = df_curr[edit_cols].copy()
        
        # TOPLAM SATIRI
        if not df_edit.empty:
            s = df_edit[['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder']].sum()
            t_row = pd.DataFrame([{
                'id': -1, 'Tarih': end_date, 'Firma': 'TOPLAM', 'Ulke': '-',
                'Sales': s['Sales'], 'Unit': s['Unit'], 'AdsSpend': s['AdsSpend'], 
                'AdsSales': s['AdsSales'], 'AdsOrder': s['AdsOrder'],
                'ACOS': (s['AdsSpend']/s['AdsSales']*100) if s['AdsSales']>0 else 0,
                'TACOS': (s['AdsSpend']/s['Sales']*100) if s['Sales']>0 else 0,
                'AOV': (s['Sales']/s['Unit']) if s['Unit']>0 else 0
            }])
            df_show = pd.concat([df_edit, t_row], ignore_index=True)
        else:
            df_show = df_edit

        # Karşılaştırma varsa değişim sütunu ekle (Bilgi amaçlı, basit fark)
        # Tablo yapısını bozmamak için sadece mevcut veriyi gösterip düzenletiyoruz.
        
        edited_data = st.data_editor(
            df_show,
            column_config={
                "id": st.column_config.NumberColumn(disabled=True),
                "ACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                "TACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                "AOV": st.column_config.NumberColumn(format="%.2f €", disabled=True),
                "Sales": st.column_config.NumberColumn(format="%.2f €"),
                "AdsSpend": st.column_config.NumberColumn(format="%.2f €"),
                "Tarih": st.column_config.DateColumn(format="DD.MM.YYYY")
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="main_editor"
        )
        
        if st.button("💾 Tabloyu Kaydet"):
            try:
                master = st.session_state.main_df.copy()
                for idx, row in edited_data.iterrows():
                    rid = row['id']
                    if rid == -1 or pd.isna(rid): continue
                    
                    mask = master['id'] == rid
                    if mask.any():
                        cols_upd = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'Firma', 'Ulke', 'Tarih']
                        for c in cols_upd:
                            master.loc[mask, c] = row[c]
                
                master = calculate_metrics(master)
                save_db(master)
                st.session_state.main_df = master
                st.success("Veriler Güncellendi!")
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

# ---------------------------------------------------------
# MODÜL 2: EXCEL YÜKLEME
# ---------------------------------------------------------
elif menu == "📤 Excel Yükle":
    st.title("📤 Excel Verisi Yükle")
    st.info("Aynı Tarih + Firma + Ülke kombinasyonundaki veriler güncellenir.")
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
                c2.success(f"Ay: {month_num}")

            df_temp = xls[selected_sheet].copy()
            header_row = 0
            for i, row in df_temp.head(10).iterrows():
                row_str = row.astype(str).str.lower().tolist()
                if any('firm' in s or 'country' in s for s in row_str):
                    header_row = i + 1
                    break
            if header_row > 0:
                df_temp = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=header_row)
            
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

            if st.button("💾 Kaydet"):
                # 2025
                d1 = pd.DataFrame()
                d1['Firma'] = df_temp[map_firm]
                d1['Ulke'] = df_temp[map_country]
                d1['Tarih'] = pd.to_datetime(f"2025-{month_num}-01")
                for c,m in zip(['Sales','Unit','AdsSpend','AdsSales','AdsOrder'],[map_s25,map_u25,map_sp25,map_as25,map_ao25]):
                    d1[c] = df_temp[m].apply(clean_currency)
                
                # 2024
                d2 = pd.DataFrame()
                d2['Firma'] = df_temp[map_firm]
                d2['Ulke'] = df_temp[map_country]
                d2['Tarih'] = pd.to_datetime(f"2024-{month_num}-01")
                for c,m in zip(['Sales','Unit','AdsSpend','AdsSales','AdsOrder'],[map_s24,map_u24,map_sp24,map_as24,map_ao24]):
                    d2[c] = df_temp[m].apply(clean_currency)
                
                comb = pd.concat([d1, d2], ignore_index=True)
                comb = comb.dropna(subset=['Firma'])
                comb = comb[comb['Sales'] > 0]
                comb = comb[~comb['Firma'].astype(str).str.contains('Toplam', case=False)]
                
                cnt = update_database(comb)
                st.success(f"Başarılı! {len(comb)} satır işlendi. ({cnt} güncelleme)")

        except Exception as e:
            st.error(f"Hata: {e}")

# ---------------------------------------------------------
# MODÜL 3: MANUEL GİRİŞ
# ---------------------------------------------------------
elif menu == "📝 Manuel Giriş":
    st.title("📝 Manuel Giriş")
    with st.form("manuel"):
        c1, c2, c3 = st.columns(3)
        d = c1.date_input("Tarih")
        f = c2.text_input("Firma", "HomeByHome")
        cnt = c3.text_input("Ülke", "DE")
        c4, c5, c6 = st.columns(3)
        s = c4.number_input("Sales", min_value=0.0)
        u = c5.number_input("Unit", min_value=0)
        sp = c6.number_input("Spend", min_value=0.0)
        c7, c8 = st.columns(2)
        asl = c7.number_input("Ads Sales", min_value=0.0)
        ao = c8.number_input("Ads Order", min_value=0)
        
        if st.form_submit_button("Kaydet"):
            row = {'Tarih': pd.to_datetime(d), 'Firma': f, 'Ulke': cnt, 'Sales': s, 'Unit': u, 'AdsSpend': sp, 'AdsSales': asl, 'AdsOrder': ao}
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
        st.success("Sıfırlandı.")
        st.rerun()
