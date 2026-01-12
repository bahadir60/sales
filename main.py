import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime
from dateutil.relativedelta import relativedelta

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Paneli V13", layout="wide", page_icon="📊")

DB_FILE = 'eticaret_db_pro_v13.csv'

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

# Türkçe Ay Mapping
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
# YARDIMCI FONKSİYON: TARİH FİLTRESİ
# ---------------------------------------------------------
def get_date_range(preset):
    today = datetime.date.today()
    if preset == "Last 7 Days":
        return today - datetime.timedelta(days=7), today
    elif preset == "Last 30 Days":
        return today - datetime.timedelta(days=30), today
    elif preset == "This Month":
        start = today.replace(day=1)
        return start, today
    elif preset == "Last Month":
        last_month_end = today.replace(day=1) - datetime.timedelta(days=1)
        start = last_month_end.replace(day=1)
        return start, last_month_end
    elif preset == "Last 3 Months":
        start = today - relativedelta(months=3)
        return start, today
    elif preset == "This Year":
        start = today.replace(month=1, day=1)
        return start, today
    elif preset == "Last Year":
        start = today.replace(year=today.year-1, month=1, day=1)
        end = today.replace(year=today.year-1, month=12, day=31)
        return start, end
    elif preset == "Lifetime":
        return None, None 
    return today, today

# ---------------------------------------------------------
# MODÜL 1: DASHBOARD & DÜZENLEME
# ---------------------------------------------------------
if menu == "📊 Dashboard & Düzenleme":
    st.title("📊 Yönetim Paneli")
    df = st.session_state.main_df.copy()
    
    if df.empty:
        st.warning("Veritabanı boş.")
    else:
        # --- SOL TARAFTAKİ FİLTRELER ---
        st.sidebar.markdown("---")
        st.sidebar.header("🗓️ Tarih & Kıyaslama")
        
        # 1. Tarih Aralığı Seçimi (Preset)
        date_presets = [
            "This Month", "Last Month", "Last 7 Days", "Last 30 Days", 
            "Last 3 Months", "This Year", "Last Year", "Lifetime", "Custom Range"
        ]
        selected_preset = st.sidebar.selectbox("Dönem Seçimi:", date_presets, index=0)
        
        if selected_preset == "Custom Range":
            custom_dates = st.sidebar.date_input("Tarih Aralığı", (datetime.date.today(), datetime.date.today()))
            if len(custom_dates) == 2:
                start_date, end_date = custom_dates
            else:
                start_date, end_date = datetime.date.today(), datetime.date.today()
        else:
            s_temp, e_temp = get_date_range(selected_preset)
            if s_temp is None: # Lifetime
                start_date = df['Tarih'].min().date()
                end_date = df['Tarih'].max().date()
            else:
                start_date, end_date = s_temp, e_temp
        
        # 2. Karşılaştırma Modu
        comp_mode = st.sidebar.radio("Karşılaştırma:", ["Yok", "MoM (Önceki Dönem)", "YoY (Geçen Yıl)"])
        
        prev_start, prev_end = None, None
        label_prev = "Geçmiş Dönem"
        
        if comp_mode != "Yok":
            if comp_mode == "YoY (Geçen Yıl)":
                prev_start = start_date - relativedelta(years=1)
                prev_end = end_date - relativedelta(years=1)
                label_prev = "Geçen Yıl"
            elif comp_mode == "MoM (Önceki Dönem)":
                delta = end_date - start_date + datetime.timedelta(days=1)
                prev_end = start_date - datetime.timedelta(days=1)
                prev_start = prev_end - delta + datetime.timedelta(days=1)
                label_prev = "Önceki Dönem"
            
            st.sidebar.info(f"Kıyas: {prev_start} - {prev_end}")

        # 3. Firma ve Ülke Filtreleri
        firms = ["Tümü"] + sorted(list(df['Firma'].unique()))
        countries = ["Tümü"] + sorted(list(df['Ulke'].unique()))
        
        sel_firm = st.sidebar.selectbox("Firma", firms, key="sel_firm_dash")
        sel_country = st.sidebar.selectbox("Ülke", countries, key="sel_cntry_dash")
        
        # VERİ SÜZME
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

        # --- KARŞILAŞTIRMA & KPI KARTLARI ---
        st.markdown(f"### 🗓️ Dönem: {start_date} - {end_date}")
        
        metrics_options = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'TACOS', 'ACOS', 'AOV']
        
        # --- İSTEK: Varsayılan Olarak 5 Metrik Açık ---
        selected_metrics = st.multiselect(
            "Karşılaştırılacak Metrikler:",
            metrics_options,
            default=['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'TACOS']
        )
        
        # KPI Hesaplayıcı (Scalar)
        def get_total_metric(dframe, m):
            if dframe.empty: return 0
            if m == 'TACOS': return (dframe['AdsSpend'].sum() / dframe['Sales'].sum() * 100) if dframe['Sales'].sum() > 0 else 0
            if m == 'ACOS': return (dframe['AdsSpend'].sum() / dframe['AdsSales'].sum() * 100) if dframe['AdsSales'].sum() > 0 else 0
            if m == 'AOV': return (dframe['Sales'].sum() / dframe['Unit'].sum()) if dframe['Unit'].sum() > 0 else 0
            return dframe[m].sum()

        # Kartları Göster
        if selected_metrics:
            cols = st.columns(len(selected_metrics))
            for i, m in enumerate(selected_metrics):
                curr_val = get_total_metric(df_curr, m)
                prev_val = get_total_metric(df_prev, m) if not df_prev.empty else 0
                
                delta = None
                if comp_mode != "Yok":
                    diff = curr_val - prev_val
                    pct = (diff / prev_val * 100) if prev_val > 0 else 0
                    delta = f"{pct:.1f}%"
                
                fmt = "%.2f%%" if m in ['TACOS', 'ACOS'] else ("%.2f €" if m in ['Sales', 'AdsSpend', 'AdsSales', 'AOV'] else "%.0f")
                color = "inverse" if m in ['TACOS', 'ACOS'] else "normal"
                
                cols[i].metric(m, fmt % curr_val, delta, delta_color=color)
            
        st.markdown("---")

        # --- GRAFİK ALANI ---
        if comp_mode != "Yok":
            c_chart1, c_chart2 = st.columns([3, 1])
            with c_chart1:
                st.subheader("📈 Karşılaştırma Grafiği")
                
                # Grafik Ayarları
                col_g1, col_g2 = st.columns(2)
                plot_metric = col_g1.selectbox("Grafik Verisi:", metrics, index=0)
                
                # --- İSTEK: Toplam Gösterme Seçeneği ---
                group_mode = col_g2.radio("Gruplama:", ["Ülke", "Firma", "Genel Toplam"], horizontal=True, index=2)
                
                grp = 'Ulke' if group_mode == "Ülke" else ('Firma' if group_mode == "Firma" else None)
                
                # Grafik Verisi Hazırla (DataFrame)
                def prep_chart_data(d, lbl):
                    if d.empty: return pd.DataFrame()
                    
                    if grp: # Ülke veya Firma Bazlı
                        if plot_metric in ['TACOS', 'ACOS', 'AOV']:
                            g = d.groupby(grp).apply(lambda x: get_total_metric(x, plot_metric)).reset_index(name='Value')
                        else:
                            g = d.groupby(grp)[plot_metric].sum().reset_index().rename(columns={plot_metric:'Value'})
                        g['Grup'] = g[grp]
                    else: # Genel Toplam
                        val = get_total_metric(d, plot_metric)
                        g = pd.DataFrame({'Grup': ['Toplam'], 'Value': [val]})
                        
                    g['Dönem'] = lbl
                    return g
                
                d1 = prep_chart_data(df_curr, "Bu Dönem")
                d2 = prep_chart_data(df_prev, label_prev)
                d_chart = pd.concat([d1, d2], ignore_index=True)
                
                if not d_chart.empty:
                    fig = px.bar(d_chart, x='Grup', y='Value', color='Dönem', barmode='group', 
                                 text_auto='.2s', color_discrete_map={"Bu Dönem": "#00CC96", label_prev: "#EF553B"})
                    
                    if plot_metric in ['TACOS', 'ACOS']: fig.update_layout(yaxis_title="Oran (%)")
                    elif plot_metric in ['Sales', 'AdsSpend', 'AOV']: fig.update_layout(yaxis_title="Tutar (€)")
                    
                    st.plotly_chart(fig, use_container_width=True)
            
            with c_chart2:
                # Scatter
                if not df_curr.empty:
                    st.subheader("💡 İlişki Analizi")
                    fig2 = px.scatter(df_curr, x="AdsSpend", y="Sales", size="AdsOrder", color="Ulke", 
                                      hover_name="Firma", title="Spend vs Sales")
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            # Trend Grafiği
            if not df_curr.empty:
                st.subheader("📈 Zaman İçinde Satış Trendi")
                d_trend = df_curr.groupby('Tarih')['Sales'].sum().reset_index()
                fig = px.line(d_trend, x='Tarih', y='Sales', markers=True)
                st.plotly_chart(fig, use_container_width=True)

        # --- TABLO VE DÜZENLEME ---
        st.subheader("📝 Veri Detayları ve Düzenleme")
        
        edit_cols = ['id', 'Tarih', 'Firma', 'Ulke', 'Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'ACOS', 'TACOS', 'AOV']
        df_edit = df_curr[edit_cols].copy()
        
        # TOPLAM SATIRI
        if not df_edit.empty:
            s = df_edit[['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder']].sum()
            t_row = pd.DataFrame([{
                'id': -1, 'Tarih': pd.to_datetime(end_date), 'Firma': 'TOPLAM', 'Ulke': '-',
                'Sales': s['Sales'], 'Unit': s['Unit'], 'AdsSpend': s['AdsSpend'], 
                'AdsSales': s['AdsSales'], 'AdsOrder': s['AdsOrder'],
                'ACOS': (s['AdsSpend']/s['AdsSales']*100) if s['AdsSales']>0 else 0,
                'TACOS': (s['AdsSpend']/s['Sales']*100) if s['Sales']>0 else 0,
                'AOV': (s['Sales']/s['Unit']) if s['Unit']>0 else 0
            }])
            df_show = pd.concat([df_edit, t_row], ignore_index=True)
        else:
            df_show = df_edit

        column_cfg = {
            "id": st.column_config.NumberColumn(disabled=True),
            "Tarih": st.column_config.DateColumn(format="DD.MM.YYYY"),
            "ACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
            "TACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
            "AOV": st.column_config.NumberColumn(format="%.2f €", disabled=True),
            "Sales": st.column_config.NumberColumn(format="%.2f €"),
            "AdsSpend": st.column_config.NumberColumn(format="%.2f €")
        }

        edited_data = st.data_editor(
            df_show,
            column_config=column_cfg,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="data_editor_main"
        )
        
        if st.button("💾 Tabloyu Kaydet"):
            try:
                master_df = st.session_state.main_df.copy()
                for index, row in edited_data.iterrows():
                    row_id = row['id']
                    if row_id == -1 or pd.isna(row_id): continue
                    
                    mask = master_df['id'] == row_id
                    if mask.any():
                        cols_upd = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'Firma', 'Ulke', 'Tarih']
                        for c in cols_upd:
                            master_df.loc[mask, c] = row[c]
                
                master_df = calculate_metrics(master_df)
                save_db(master_df)
                st.session_state.main_df = master_df
                st.success("✅ Veriler Güncellendi!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Kayıt Hatası: {e}")

# ---------------------------------------------------------
# MODÜL 2: EXCEL YÜKLEME
# ---------------------------------------------------------
elif menu == "📤 Excel Yükle":
    st.title("📤 Excel Verisi Yükle")
    uploaded_file = st.file_uploader("Dosya Seç (.xlsx)", type=["xlsx", "xls"])

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
                month_num = c2.number_input("Ay No (1-12):", min_value=1, max_value=12)
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
                st.markdown("**2025 Verileri**")
                map_s25 = st.selectbox("Sales 25", cols, index=get_col(['2025 sales', 'sales'], cols))
                map_u25 = st.selectbox("Unit 25", cols, index=get_col(['2025 unit', 'unit'], cols))
                map_sp25 = st.selectbox("Spend 25", cols, index=get_col(['2025 ads spend', 'ads spend'], cols))
                map_as25 = st.selectbox("Ad Sales 25", cols, index=get_col(['2025 ads sales', 'ads sales'], cols))
                map_ao25 = st.selectbox("Ad Order 25", cols, index=get_col(['2025 ads order', 'ads order'], cols))
            with c_24:
                st.markdown("**2024 Verileri**")
                map_s24 = st.selectbox("Sales 24", cols, index=get_col(['2024 sales'], cols))
                map_u24 = st.selectbox("Unit 24", cols, index=get_col(['2024 unit'], cols))
                map_sp24 = st.selectbox("Spend 24", cols, index=get_col(['2024 ads spend'], cols))
                map_as24 = st.selectbox("Ad Sales 24", cols, index=get_col(['2024 ads sales'], cols))
                map_ao24 = st.selectbox("Ad Order 24", cols, index=get_col(['2024 ads order'], cols))

            if st.button("💾 Kaydet"):
                d1 = pd.DataFrame()
                d1['Firma'] = df_temp[map_firm]
                d1['Ulke'] = df_temp[map_country]
                d1['Tarih'] = pd.to_datetime(f"2025-{month_num}-01")
                for c, m in zip(['Sales','Unit','AdsSpend','AdsSales','AdsOrder'], [map_s25, map_u25, map_sp25, map_as25, map_ao25]):
                    d1[c] = df_temp[m].apply(clean_currency)
                
                d2 = pd.DataFrame()
                d2['Firma'] = df_temp[map_firm]
                d2['Ulke'] = df_temp[map_country]
                d2['Tarih'] = pd.to_datetime(f"2024-{month_num}-01")
                for c, m in zip(['Sales','Unit','AdsSpend','AdsSales','AdsOrder'], [map_s24, map_u24, map_sp24, map_as24, map_ao24]):
                    d2[c] = df_temp[m].apply(clean_currency)
                
                combined = pd.concat([d1, d2], ignore_index=True)
                combined = combined.dropna(subset=['Firma'])
                combined = combined[combined['Sales'] > 0]
                combined = combined[~combined['Firma'].astype(str).str.contains('Toplam', case=False)]
                
                # Overwrite Logic
                curr_db = st.session_state.main_df.copy()
                curr_db['unique_key'] = curr_db['Tarih'].dt.strftime('%Y-%m-%d') + curr_db['Firma'].astype(str) + curr_db['Ulke'].astype(str)
                combined['unique_key'] = combined['Tarih'].dt.strftime('%Y-%m-%d') + combined['Firma'].astype(str) + combined['Ulke'].astype(str)
                
                keys_remove = combined['unique_key'].unique()
                curr_db = curr_db[~curr_db['unique_key'].isin(keys_remove)].drop(columns=['unique_key'])
                combined = combined.drop(columns=['unique_key'])
                
                final = pd.concat([curr_db, combined], ignore_index=True)
                final['id'] = range(1, len(final)+1)
                final = calculate_metrics(final)
                save_db(final)
                st.session_state.main_df = final
                st.success(f"Başarılı! {len(combined)} satır işlendi.")

        except Exception as e:
            st.error(f"Hata: {e}")

# ---------------------------------------------------------
# MODÜL 3: MANUEL GİRİŞ
# ---------------------------------------------------------
elif menu == "📝 Manuel Giriş":
    st.title("📝 Manuel Giriş")
    with st.form("man"):
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
            new_df = pd.DataFrame([row])
            
            curr_db = st.session_state.main_df.copy()
            mask = (curr_db['Tarih'] == pd.to_datetime(d)) & (curr_db['Firma'] == f) & (curr_db['Ulke'] == cnt)
            curr_db = curr_db[~mask]
            
            final = pd.concat([curr_db, new_df], ignore_index=True)
            final['id'] = range(1, len(final)+1)
            final = calculate_metrics(final)
            save_db(final)
            st.session_state.main_df = final
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
