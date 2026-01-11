import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime
from dateutil.relativedelta import relativedelta

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Yönetim Paneli V8", layout="wide", page_icon="📈")

DB_FILE = 'eticaret_db_pro_v8.csv'

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
menu = st.sidebar.radio("Seçim:", ["📊 Dönemsel Karşılaştırma", "📤 Excel Yükle", "📝 Manuel Giriş", "⚙️ Ayarlar"])

# ---------------------------------------------------------
# MODÜL 1: EXCEL YÜKLEME
# ---------------------------------------------------------
if menu == "📤 Excel Yükle":
    st.title("📤 Akıllı Excel Yükleyici")
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
                c2.success(f"Ay Tespit Edildi: {month_num}")

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

            if st.button("💾 Kaydet"):
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
                
                start_id = st.session_state.main_df['id'].max() if not st.session_state.main_df.empty else 0
                if pd.isna(start_id): start_id = 0
                combined['id'] = range(int(start_id) + 1, int(start_id) + 1 + len(combined))
                
                combined = calculate_metrics(combined)
                st.session_state.main_df = pd.concat([st.session_state.main_df, combined], ignore_index=True)
                save_db(st.session_state.main_df)
                st.success(f"Kayıt Başarılı: {len(combined)} satır.")

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
        
        if st.form_submit_button("Kaydet"):
            max_id = st.session_state.main_df['id'].max()
            new_id = 1 if pd.isna(max_id) else max_id + 1
            row = {
                'id': new_id, 'Tarih': pd.to_datetime(inp_date),
                'Firma': inp_firm, 'Ulke': inp_cntry,
                'Sales': s, 'Unit': u, 'AdsSpend': sp, 'AdsSales': asales, 'AdsOrder': aorder
            }
            new_df = calculate_metrics(pd.DataFrame([row]))
            st.session_state.main_df = pd.concat([st.session_state.main_df, new_df], ignore_index=True)
            save_db(st.session_state.main_df)
            st.success("Kaydedildi.")

# ---------------------------------------------------------
# MODÜL 3: DÖNEMSEL KARŞILAŞTIRMA (DASHBOARD)
# ---------------------------------------------------------
elif menu == "📊 Dönemsel Karşılaştırma":
    st.title("📊 Dönemsel Performans Analizi")
    df = st.session_state.main_df.copy()
    
    if df.empty:
        st.warning("Henüz veri yok.")
    else:
        # --- TARİH VE FİLTRELER ---
        st.sidebar.markdown("---")
        st.sidebar.header("🗓️ Filtreler")
        
        today = datetime.date.today()
        start_month = today.replace(day=1)
        date_range = st.sidebar.date_input("Dönem Seçimi", (start_month, today))
        
        if len(date_range) == 2:
            start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            comp_mode = st.sidebar.radio("Karşılaştırma:", ["Geçen Yıl (YoY)", "Geçen Ay (MoM)"])
            
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
            sel_firm = st.sidebar.selectbox("Firma", firms)
            countries = ["Tümü"] + list(df['Ulke'].unique())
            sel_country = st.sidebar.selectbox("Ülke", countries)
            
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
            
            # --- ÖZELLEŞTİRİLEBİLİR KARŞILAŞTIRMA ---
            st.divider()
            st.subheader("🛠️ Karşılaştırma Paneli")
            st.caption(f"Seçilen Dönem: {start_date.date()} - {end_date.date()} | Karşılaştırılan: {prev_start.date()} - {prev_end.date()}")
            
            col_sel, col_empty = st.columns([4, 1])
            
            with col_sel:
                metrics_options = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'TACOS', 'ACOS', 'AOV']
                selected_metrics = st.multiselect(
                    "Metrikleri Seçin (Karşılaştır butonuna gerek yok, anlık güncellenir):",
                    metrics_options,
                    default=['Sales', 'AdsSpend', 'TACOS']
                )
            
            if selected_metrics:
                st.markdown("---")
                # Dinamik Kolonlar Oluştur
                cols = st.columns(len(selected_metrics))
                
                for idx, metric in enumerate(selected_metrics):
                    with cols[idx]:
                        # HESAPLAMA MANTIĞI
                        if metric in ['TACOS', 'ACOS', 'AOV']:
                            # Ağırlıklı Ortalama (Doğru Hesap)
                            curr_val = 0
                            prev_val = 0
                            
                            # Current
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
                            # Toplamsal Metrikler
                            curr_val = df_curr[metric].sum()
                            prev_val = df_prev[metric].sum()
                            
                            if metric in ['Sales', 'AdsSpend', 'AdsSales']:
                                fmt = "%d €"
                            else:
                                fmt = "%d" # Adetler için
                        
                        # Değişim Oranı
                        delta = curr_val - prev_val
                        percent_change = ((curr_val - prev_val) / prev_val * 100) if prev_val > 0 else 0
                        
                        # Rengi belirle (Tacos/Acos için düşüş iyidir)
                        if metric in ['TACOS', 'ACOS']:
                            delta_color = "inverse"
                        else:
                            delta_color = "normal"
                            
                        # Gösterim
                        st.metric(
                            label=metric,
                            value=fmt % curr_val,
                            delta=f"{percent_change:.1f}% ({label_prev})",
                            delta_color=delta_color
                        )

            # --- DİNAMİK GRAFİK ---
            if selected_metrics:
                st.divider()
                st.subheader("📈 Grafiksel Analiz")
                
                # Grafikte gösterilecek veriyi seçtirme
                plot_metric = st.radio("Grafikte Detaylandırılacak Veri:", selected_metrics, horizontal=True)
                
                grp = 'Ulke' if sel_firm != "Tümü" else 'Firma'
                
                # Veri Hazırlığı (Yardımcı Fonksiyon)
                def get_plot_data(dframe, metric, label):
                    if dframe.empty:
                        return pd.DataFrame(columns=[grp, 'Value', 'Dönem'])
                        
                    if metric == 'TACOS':
                        g = dframe.groupby(grp)[['Sales', 'AdsSpend']].sum().reset_index()
                        g['Value'] = (g['AdsSpend'] / g['Sales'] * 100).fillna(0)
                    elif metric == 'ACOS':
                        g = dframe.groupby(grp)[['AdsSales', 'AdsSpend']].sum().reset_index()
                        g['Value'] = (g['AdsSpend'] / g['AdsSales'] * 100).fillna(0)
                    elif metric == 'AOV':
                        g = dframe.groupby(grp)[['Sales', 'Unit']].sum().reset_index()
                        g['Value'] = (g['Sales'] / g['Unit']).fillna(0)
                    else:
                        g = dframe.groupby(grp)[metric].sum().reset_index()
                        g.rename(columns={metric: 'Value'}, inplace=True)
                    
                    g['Dönem'] = label
                    return g[[grp, 'Value', 'Dönem']]

                df_plot_curr = get_plot_data(df_curr, plot_metric, "Bu Dönem")
                df_plot_prev = get_plot_data(df_prev, plot_metric, label_prev)
                
                df_chart = pd.concat([df_plot_curr, df_plot_prev], ignore_index=True)
                
                color_map = {"Bu Dönem": "#00CC96", label_prev: "#EF553B"}
                
                fig = px.bar(df_chart, x=grp, y='Value', color='Dönem', barmode='group', 
                             title=f"{grp} Bazlı {plot_metric} Karşılaştırması",
                             text_auto='.2s', color_discrete_map=color_map)
                
                if plot_metric in ['TACOS', 'ACOS']:
                    fig.update_layout(yaxis_title="Yüzde (%)")
                else:
                    fig.update_layout(yaxis_title="Değer")
                    
                st.plotly_chart(fig, use_container_width=True)

            # --- DÜZENLENEBİLİR TABLO ---
            st.divider()
            st.subheader("📝 Veri Detayları ve Düzenleme")
            st.info("Değişiklik yapıp 'Kaydet' butonuna bastığınızda grafikler ve KPI'lar otomatik güncellenir.")
            
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
                        if pd.isna(row_id): continue # Yeni satır eklenirse
                        
                        mask = master_df['id'] == row_id
                        if mask.any():
                            cols_upd = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'Firma', 'Ulke', 'Tarih']
                            for c in cols_upd:
                                master_df.loc[mask, c] = row[c]
                    
                    master_df = calculate_metrics(master_df)
                    st.session_state.main_df = master_df
                    save_db(master_df)
                    st.success("Veriler ve Oranlar Güncellendi!")
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
