import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime
from dateutil.relativedelta import relativedelta

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Yönetim Paneli V10", layout="wide", page_icon="🚀")

DB_FILE = 'eticaret_db_pro_v10.csv'

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
    """Otomatik Hesaplama"""
    cols = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder']
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Yüzdelik Hesaplar
    df['ACOS'] = df.apply(lambda x: ((x['AdsSpend'] / x['AdsSales']) * 100) if x['AdsSales'] > 0 else 0, axis=1)
    df['TACOS'] = df.apply(lambda x: ((x['AdsSpend'] / x['Sales']) * 100) if x['Sales'] > 0 else 0, axis=1)
    df['AOV'] = df.apply(lambda x: (x['Sales'] / x['Unit']) if x['Unit'] > 0 else 0, axis=1)
    
    # Tarih Türetme
    df['Tarih'] = pd.to_datetime(df['Tarih'])
    df['Yil'] = df['Tarih'].dt.year
    
    return df

def update_database(new_df):
    """
    UPSERT: Aynı Tarih+Firma+Ülke varsa eskisini sil, yenisini yaz.
    """
    if new_df.empty: return st.session_state.main_df

    current_df = st.session_state.main_df.copy()
    current_df['Tarih'] = pd.to_datetime(current_df['Tarih'])
    new_df['Tarih'] = pd.to_datetime(new_df['Tarih'])
    
    # Benzersiz Anahtar Oluştur
    def create_key(df):
        return df['Tarih'].dt.strftime('%Y-%m-%d') + "_" + df['Firma'].astype(str) + "_" + df['Ulke'].astype(str)

    current_df['unique_key'] = create_key(current_df)
    new_df['unique_key'] = create_key(new_df)
    
    # Çakışanları Sil
    keys_to_remove = new_df['unique_key'].unique()
    current_df_cleaned = current_df[~current_df['unique_key'].isin(keys_to_remove)].copy()
    
    # Temizlik
    if 'unique_key' in current_df_cleaned.columns: current_df_cleaned = current_df_cleaned.drop(columns=['unique_key'])
    if 'unique_key' in new_df.columns: new_df = new_df.drop(columns=['unique_key'])
        
    final_df = pd.concat([current_df_cleaned, new_df], ignore_index=True)
    final_df['id'] = range(1, len(final_df) + 1)
    
    final_df = calculate_metrics(final_df)
    final_df.to_csv(DB_FILE, index=False)
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
menu = st.sidebar.radio("Seçim:", ["📊 Dönemsel Karşılaştırma", "📤 Excel Yükle", "📝 Manuel Giriş", "⚙️ Ayarlar"])

# ---------------------------------------------------------
# MODÜL 1: EXCEL YÜKLEME
# ---------------------------------------------------------
if menu == "📤 Excel Yükle":
    st.title("📤 Akıllı Excel Yükleyici")
    st.info("ℹ️ Aynı tarih ve firma verisi yüklenirse, eski veri güncellenir (Overwrite).")
    
    uploaded_file = st.file_uploader("Dosya Seç", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            xls = pd.read_excel(uploaded_file, sheet_name=None)
            sheet_names = list(xls.keys())
            
            st.divider()
            c1, c2 = st.columns(2)
            selected_sheet = c1.selectbox("Sekme (Ay)", sheet_names)
            
            # Ayı Bul
            sheet_clean = selected_sheet.upper().replace('İ','I').replace('Ş','S').replace('Ç','C').replace('Ğ','G').replace('Ü','U').replace('Ö','O')
            month_num = 0
            for ay_ad, ay_no in AYLAR_TR.items():
                if ay_ad in sheet_clean:
                    month_num = ay_no
                    break
            if month_num == 0:
                month_num = c2.number_input("Ay No (1-12):", min_value=1, max_value=12)
            else:
                c2.success(f"Ay Tespit Edildi: {month_num}. Ay")

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
                map_s25 = st.selectbox("Sales", cols, index=get_col(['2025 sales', 'sales'], cols))
                map_u25 = st.selectbox("Unit", cols, index=get_col(['2025 unit', 'unit'], cols))
                map_sp25 = st.selectbox("Ads Spend", cols, index=get_col(['2025 ads spend', 'ads spend'], cols))
                map_as25 = st.selectbox("Ads Sales", cols, index=get_col(['2025 ads sales', 'ads sales'], cols))
                map_ao25 = st.selectbox("Ads Order", cols, index=get_col(['2025 ads order', 'ads order'], cols))
            with c_24:
                st.markdown("**2024 Verileri**")
                map_s24 = st.selectbox("2024 Sales", cols, index=get_col(['2024 sales'], cols))
                map_u24 = st.selectbox("2024 Unit", cols, index=get_col(['2024 unit'], cols))
                map_sp24 = st.selectbox("2024 Ads Spend", cols, index=get_col(['2024 ads spend'], cols))
                map_as24 = st.selectbox("2024 Ads Sales", cols, index=get_col(['2024 ads sales'], cols))
                map_ao24 = st.selectbox("2024 Ads Order", cols, index=get_col(['2024 ads order'], cols))

            if st.button("💾 Veritabanını Güncelle"):
                # 2025
                df_2025 = pd.DataFrame()
                df_2025['Firma'] = df_temp[map_firm]
                df_2025['Ulke'] = df_temp[map_country]
                df_2025['Tarih'] = pd.to_datetime(f"2025-{month_num}-01")
                for c, m in zip(['Sales','Unit','AdsSpend','AdsSales','AdsOrder'], [map_s25, map_u25, map_sp25, map_as25, map_ao25]):
                    df_2025[c] = df_temp[m].apply(clean_currency)
                
                # 2024
                df_2024 = pd.DataFrame()
                df_2024['Firma'] = df_temp[map_firm]
                df_2024['Ulke'] = df_temp[map_country]
                df_2024['Tarih'] = pd.to_datetime(f"2024-{month_num}-01")
                for c, m in zip(['Sales','Unit','AdsSpend','AdsSales','AdsOrder'], [map_s24, map_u24, map_sp24, map_as24, map_ao24]):
                    df_2024[c] = df_temp[m].apply(clean_currency)
                
                combined = pd.concat([df_2025, df_2024], ignore_index=True)
                combined = combined.dropna(subset=['Firma'])
                combined = combined[combined['Sales'] > 0]
                combined = combined[~combined['Firma'].astype(str).str.contains('Toplam', case=False)]
                
                updated_count = update_database(combined)
                
                st.success(f"✅ İşlem Tamamlandı! {len(combined)} satır işlendi.")
                if updated_count > 0:
                    st.warning(f"⚠️ {updated_count} adet eski kayıt güncellendi.")

        except Exception as e:
            st.error(f"Hata: {e}")

# ---------------------------------------------------------
# MODÜL 2: MANUEL GİRİŞ
# ---------------------------------------------------------
elif menu == "📝 Manuel Giriş":
    st.title("📝 Manuel Giriş")
    with st.form("manuel"):
        c1, c2, c3 = st.columns(3)
        inp_date = c1.date_input("Tarih", datetime.date.today())
        inp_firm = c2.text_input("Firma", "HomeByHome")
        inp_cntry = c3.text_input("Ülke", "DE")
        
        c4, c5, c6 = st.columns(3)
        s = c4.number_input("Sales", min_value=0.0)
        u = c5.number_input("Unit", min_value=0)
        sp = c6.number_input("Ads Spend", min_value=0.0)
        
        c7, c8 = st.columns(2)
        asales = c7.number_input("Ads Sales", min_value=0.0)
        aorder = c8.number_input("Ads Order", min_value=0)
        
        if st.form_submit_button("Kaydet / Güncelle"):
            row = {
                'Tarih': pd.to_datetime(inp_date),
                'Firma': inp_firm, 'Ulke': inp_cntry,
                'Sales': s, 'Unit': u, 'AdsSpend': sp, 'AdsSales': asales, 'AdsOrder': aorder
            }
            update_database(pd.DataFrame([row]))
            st.success("Veritabanı güncellendi.")

# ---------------------------------------------------------
# MODÜL 3: DÖNEMSEL KARŞILAŞTIRMA (DASHBOARD)
# ---------------------------------------------------------
elif menu == "📊 Dönemsel Karşılaştırma":
    st.title("📊 Dönemsel Performans Analizi")
    df = st.session_state.main_df.copy()
    
    if df.empty:
        st.warning("Veritabanı boş.")
    else:
        # FİLTRELER
        st.sidebar.markdown("---")
        st.sidebar.header("🗓️ Filtreler")
        
        today = datetime.date.today()
        start_month = today.replace(day=1)
        
        # Filtrelerin hafızada kalması için 'key' parametreleri eklendi
        date_range = st.sidebar.date_input("Dönem", (start_month, today), key='filter_date')
        
        if len(date_range) == 2:
            start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            comp_mode = st.sidebar.radio("Karşılaştırma:", ["Geçen Yıl (YoY)", "Geçen Ay (MoM)"], key='filter_comp_mode')
            
            if comp_mode == "Geçen Yıl (YoY)":
                prev_start = start_date - relativedelta(years=1)
                prev_end = end_date - relativedelta(years=1)
                label_prev = "Geçen Yıl"
            else:
                delta = end_date - start_date
                prev_end = start_date - datetime.timedelta(days=1)
                prev_start = prev_end - delta
                label_prev = "Önceki Dönem"
            
            firms = ["Tümü"] + list(df['Firma'].unique())
            sel_firm = st.sidebar.selectbox("Firma", firms, key='filter_firm') # Key eklendi
            
            countries = ["Tümü"] + list(df['Ulke'].unique())
            sel_country = st.sidebar.selectbox("Ülke", countries, key='filter_country') # Key eklendi
            
            # Veri Süzme
            mask_curr = (df['Tarih'] >= start_date) & (df['Tarih'] <= end_date)
            df_curr = df.loc[mask_curr].copy()
            
            mask_prev = (df['Tarih'] >= prev_start) & (df['Tarih'] <= prev_end)
            df_prev = df.loc[mask_prev].copy()
            
            if sel_firm != "Tümü":
                df_curr = df_curr[df_curr['Firma'] == sel_firm]
                df_prev = df_prev[df_prev['Firma'] == sel_firm]
            if sel_country != "Tümü":
                df_curr = df_curr[df_curr['Ulke'] == sel_country]
                df_prev = df_prev[df_prev['Ulke'] == sel_country]
            
            # KARŞILAŞTIRMA SEÇİCİSİ
            st.divider()
            st.subheader("🛠️ Karşılaştırma Paneli")
            
            metrics_options = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'TACOS', 'ACOS', 'AOV']
            # Default değerler güncellendi
            selected_metrics = st.multiselect(
                "Metrikleri Seçin:",
                metrics_options,
                default=['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'TACOS']
            )
            
            if selected_metrics:
                st.markdown(f"**{start_date.date()} - {end_date.date()}** vs **{prev_start.date()} - {prev_end.date()}**")
                cols = st.columns(len(selected_metrics))
                
                for idx, metric in enumerate(selected_metrics):
                    with cols[idx]:
                        # Hesaplama
                        curr_val = 0
                        prev_val = 0
                        
                        if metric in ['TACOS', 'ACOS', 'AOV']:
                            # Ağırlıklı Ortalama
                            if metric == 'TACOS':
                                curr_val = (df_curr['AdsSpend'].sum() / df_curr['Sales'].sum() * 100) if df_curr['Sales'].sum() > 0 else 0
                                prev_val = (df_prev['AdsSpend'].sum() / df_prev['Sales'].sum() * 100) if df_prev['Sales'].sum() > 0 else 0
                                fmt = "%.2f%%"
                            elif metric == 'ACOS':
                                curr_val = (df_curr['AdsSpend'].sum() / df_curr['AdsSales'].sum() * 100) if df_curr['AdsSales'].sum() > 0 else 0
                                prev_val = (df_prev['AdsSpend'].sum() / df_prev['AdsSales'].sum() * 100) if df_prev['AdsSales'].sum() > 0 else 0
                                fmt = "%.2f%%"
                            elif metric == 'AOV':
                                curr_val = (df_curr['Sales'].sum() / df_curr['Unit'].sum()) if df_curr['Unit'].sum() > 0 else 0
                                prev_val = (df_prev['Sales'].sum() / df_prev['Unit'].sum()) if df_prev['Unit'].sum() > 0 else 0
                                fmt = "%.2f €"
                        else:
                            # Toplam
                            curr_val = df_curr[metric].sum()
                            prev_val = df_prev[metric].sum()
                            fmt = "%d €" if metric in ['Sales','AdsSpend','AdsSales'] else "%d"
                        
                        percent_change = ((curr_val - prev_val) / prev_val * 100) if prev_val > 0 else 0
                        delta_color = "inverse" if metric in ['TACOS', 'ACOS'] else "normal"
                        
                        st.metric(metric, fmt % curr_val, f"{percent_change:.1f}%", delta_color=delta_color)

            # GRAFİK
            if selected_metrics:
                st.divider()
                st.subheader("📈 Grafiksel Analiz")
                plot_metric = st.radio("Grafik Verisi:", selected_metrics, horizontal=True)
                
                grp = 'Ulke' if sel_firm != "Tümü" else 'Firma'
                
                # Grafik Verisi Hazırla
                def get_grp_data(d, m, lbl):
                    if d.empty: return pd.DataFrame(columns=[grp, 'Value', 'Dönem'])
                    
                    if m == 'TACOS':
                        g = d.groupby(grp)[['Sales', 'AdsSpend']].sum().reset_index()
                        g['Value'] = (g['AdsSpend'] / g['Sales'] * 100).fillna(0)
                    elif m == 'ACOS':
                        g = d.groupby(grp)[['AdsSales', 'AdsSpend']].sum().reset_index()
                        g['Value'] = (g['AdsSpend'] / g['AdsSales'] * 100).fillna(0)
                    elif m == 'AOV':
                        g = d.groupby(grp)[['Sales', 'Unit']].sum().reset_index()
                        g['Value'] = (g['Sales'] / g['Unit']).fillna(0)
                    else:
                        g = d.groupby(grp)[m].sum().reset_index()
                        g.rename(columns={m: 'Value'}, inplace=True)
                    g['Dönem'] = lbl
                    return g[[grp, 'Value', 'Dönem']]

                df_chart = pd.concat([
                    get_grp_data(df_curr, plot_metric, "Bu Dönem"),
                    get_grp_data(df_prev, plot_metric, label_prev)
                ], ignore_index=True)
                
                color_map = {"Bu Dönem": "#00CC96", label_prev: "#EF553B"}
                fig = px.bar(df_chart, x=grp, y='Value', color='Dönem', barmode='group', 
                             title=f"{grp} Bazlı {plot_metric}", text_auto='.2s', 
                             color_discrete_map=color_map)
                
                if plot_metric in ['TACOS', 'ACOS']: fig.update_layout(yaxis_title="%")
                st.plotly_chart(fig, use_container_width=True)

            # DÜZENLEME
            st.divider()
            st.subheader("📝 Veri Düzenleme")
            
            edit_cols = ['id', 'Tarih', 'Firma', 'Ulke', 'Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'ACOS', 'TACOS', 'AOV']
            edited_df = st.data_editor(
                df_curr[edit_cols],
                column_config={
                    "id": st.column_config.NumberColumn(disabled=True),
                    "ACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                    "TACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                    "AOV": st.column_config.NumberColumn(format="%.2f €", disabled=True),
                    "Tarih": st.column_config.DateColumn(format="DD.MM.YYYY"),
                },
                hide_index=True,
                use_container_width=True,
                num_rows="dynamic",
                key="editor"
            )
            
            if st.button("💾 Değişiklikleri Kaydet"):
                try:
                    master_df = st.session_state.main_df.copy()
                    for index, row in edited_df.iterrows():
                        row_id = row['id']
                        if pd.isna(row_id): continue 
                        
                        mask = master_df['id'] == row_id
                        if mask.any():
                            cols_upd = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'Firma', 'Ulke', 'Tarih']
                            for c in cols_upd:
                                master_df.loc[mask, c] = row[c]
                    
                    master_df = calculate_metrics(master_df)
                    master_df.to_csv(DB_FILE, index=False)
                    st.session_state.main_df = master_df
                    st.success("Güncellendi!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

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
