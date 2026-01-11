import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime
from dateutil.relativedelta import relativedelta

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Yönetim Paneli V6", layout="wide", page_icon="📅")

DB_FILE = 'eticaret_db_pro_v6.csv'

# ---------------------------------------------------------
# 1. VERİTABANI MOTORU
# ---------------------------------------------------------
def init_db():
    # Yeni yapıda "PrevSales" vb. yok. Her veri kendi tarihinde tutulur.
    columns = [
        'id', 
        'Tarih', 'Yil', 'Ay', 'Firma', 'Ulke', 
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
    """Otomatik Hesaplama Motoru"""
    cols = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder']
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Yüzdelik Hesaplar (0-100)
    df['ACOS'] = df.apply(lambda x: ((x['AdsSpend'] / x['AdsSales']) * 100) if x['AdsSales'] > 0 else 0, axis=1)
    df['TACOS'] = df.apply(lambda x: ((x['AdsSpend'] / x['Sales']) * 100) if x['Sales'] > 0 else 0, axis=1)
    df['AOV'] = df.apply(lambda x: (x['Sales'] / x['Unit']) if x['Unit'] > 0 else 0, axis=1)
    
    # Tarihten Yıl ve Ay türetme
    df['Tarih'] = pd.to_datetime(df['Tarih'])
    df['Yil'] = df['Tarih'].dt.year
    df['Ay'] = df['Tarih'].dt.month_name() # January, February... (Türkçe için map gerekir)
    
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

# Türkçe Ay İsimleri Mapping
AYLAR_TR = {
    'OCAK': 1, 'SUBAT': 2, 'MART': 3, 'NISAN': 4, 'MAYIS': 5, 'HAZIRAN': 6,
    'TEMMUZ': 7, 'AGUSTOS': 8, 'EYLUL': 9, 'EKIM': 10, 'KASIM': 11, 'ARALIK': 12,
    'OCAK.csv': 1, 'SUBAT.csv': 2 # Dosya uzantılı gelirse diye
}

# Session State
if 'main_df' not in st.session_state:
    st.session_state.main_df = init_db()

# ---------------------------------------------------------
# 2. MENÜ
# ---------------------------------------------------------
st.sidebar.title("🎛️ Menü")
menu = st.sidebar.radio("Seçim:", ["📊 Dashboard", "📤 Excel Yükle (Akıllı)", "📝 Manuel Giriş", "⚙️ Ayarlar"])

# ---------------------------------------------------------
# MODÜL 1: AKILLI EXCEL YÜKLEME
# ---------------------------------------------------------
if menu == "📤 Excel Yükle (Akıllı)":
    st.title("📤 Akıllı Excel Yükleyici")
    st.info("Sistem; Sekme adından AYI, Sütun başlığından YILI (2024/2025) otomatik algılar ve veritabanına ayrı ayrı kaydeder.")
    
    uploaded_file = st.file_uploader("Dosya Seç", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            xls = pd.read_excel(uploaded_file, sheet_name=None)
            sheet_names = list(xls.keys())
            
            st.divider()
            c1, c2 = st.columns(2)
            selected_sheet = c1.selectbox("Yüklenecek Sekme (Ay)", sheet_names)
            
            # AYI BELİRLEME
            # Sekme isminden ayı bulmaya çalış (OCAK, SUBAT vb.)
            sheet_clean = selected_sheet.upper().replace('İ','I').replace('Ş','S').replace('Ç','C').replace('Ğ','G').replace('Ü','U').replace('Ö','O')
            month_num = 0
            for ay_ad, ay_no in AYLAR_TR.items():
                if ay_ad in sheet_clean:
                    month_num = ay_no
                    break
            
            if month_num == 0:
                month_num = c2.number_input("Ay Tespit Edilemedi, Manuel Girin (1-12):", min_value=1, max_value=12)
            else:
                c2.success(f"Algılanan Ay: {selected_sheet} ({month_num}. Ay)")

            # Veriyi Oku
            df_temp = xls[selected_sheet].copy()
            
            # Başlık Bulma
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

            # 3 ANA GRUP: Kimlik, 2025 Verisi, 2024 Verisi
            col_id, col_25, col_24 = st.columns(3)
            
            with col_id:
                st.markdown("**1. Kimlik Bilgileri**")
                map_firm = st.selectbox("Firma", cols, index=get_col(['firm'], cols))
                map_country = st.selectbox("Ülke", cols, index=get_col(['country', 'ulke'], cols))
            
            with col_25:
                st.markdown("**2. Bu Yıl (2025) Verileri**")
                map_s25 = st.selectbox("2025 Sales", cols, index=get_col(['2025 sales', 'sales'], cols))
                map_u25 = st.selectbox("2025 Unit", cols, index=get_col(['2025 unit', 'unit'], cols))
                map_sp25 = st.selectbox("2025 Ads Spend", cols, index=get_col(['2025 ads spend', 'ads spend'], cols))
                map_as25 = st.selectbox("2025 Ads Sales", cols, index=get_col(['2025 ads sales', 'ads sales'], cols))
                map_ao25 = st.selectbox("2025 Ads Order", cols, index=get_col(['2025 ads order', 'ads order'], cols))

            with col_24:
                st.markdown("**3. Geçen Yıl (2024) Verileri**")
                map_s24 = st.selectbox("2024 Sales", cols, index=get_col(['2024 sales'], cols))
                map_u24 = st.selectbox("2024 Unit", cols, index=get_col(['2024 unit'], cols))
                map_sp24 = st.selectbox("2024 Ads Spend", cols, index=get_col(['2024 ads spend'], cols))
                map_as24 = st.selectbox("2024 Ads Sales", cols, index=get_col(['2024 ads sales'], cols))
                map_ao24 = st.selectbox("2024 Ads Order", cols, index=get_col(['2024 ads order'], cols))

            if st.button("💾 Ayrıştır ve Kaydet"):
                # --- VERİ İŞLEME MANTIĞI ---
                
                # 1. 2025 Verilerini Hazırla
                df_2025 = pd.DataFrame()
                df_2025['Firma'] = df_temp[map_firm]
                df_2025['Ulke'] = df_temp[map_country]
                # Tarih oluştur: 2025-Ay-01
                df_2025['Tarih'] = pd.to_datetime(f"2025-{month_num}-01")
                
                df_2025['Sales'] = df_temp[map_s25].apply(clean_currency)
                df_2025['Unit'] = df_temp[map_u25].apply(clean_currency)
                df_2025['AdsSpend'] = df_temp[map_sp25].apply(clean_currency)
                df_2025['AdsSales'] = df_temp[map_as25].apply(clean_currency)
                df_2025['AdsOrder'] = df_temp[map_ao25].apply(clean_currency)
                
                # Temizlik
                df_2025 = df_2025.dropna(subset=['Firma'])
                df_2025 = df_2025[~df_2025['Firma'].astype(str).str.contains('Toplam', case=False)]
                df_2025 = df_2025[df_2025['Sales'] > 0] # Sadece satışı olanlar

                # 2. 2024 Verilerini Hazırla (AYRI KAYIT OLARAK)
                df_2024 = pd.DataFrame()
                df_2024['Firma'] = df_temp[map_firm]
                df_2024['Ulke'] = df_temp[map_country]
                # Tarih oluştur: 2024-Ay-01
                df_2024['Tarih'] = pd.to_datetime(f"2024-{month_num}-01")
                
                df_2024['Sales'] = df_temp[map_s24].apply(clean_currency)
                df_2024['Unit'] = df_temp[map_u24].apply(clean_currency)
                df_2024['AdsSpend'] = df_temp[map_sp24].apply(clean_currency)
                df_2024['AdsSales'] = df_temp[map_as24].apply(clean_currency)
                df_2024['AdsOrder'] = df_temp[map_ao24].apply(clean_currency)
                
                # Temizlik
                df_2024 = df_2024.dropna(subset=['Firma'])
                df_2024 = df_2024[~df_2024['Firma'].astype(str).str.contains('Toplam', case=False)]
                df_2024 = df_2024[df_2024['Sales'] > 0]

                # 3. Birleştir ve Kaydet
                combined_new = pd.concat([df_2025, df_2024], ignore_index=True)
                
                # ID Ata
                start_id = st.session_state.main_df['id'].max() if not st.session_state.main_df.empty else 0
                if pd.isna(start_id): start_id = 0
                combined_new['id'] = range(int(start_id) + 1, int(start_id) + 1 + len(combined_new))
                
                # Hesapla
                combined_new = calculate_metrics(combined_new)
                
                st.session_state.main_df = pd.concat([st.session_state.main_df, combined_new], ignore_index=True)
                save_db(st.session_state.main_df)
                
                st.success(f"✅ Başarılı! Toplam {len(combined_new)} satır eklendi.")
                st.info(f"- 2025 Verisi: {len(df_2025)} satır\n- 2024 Verisi: {len(df_2024)} satır")

        except Exception as e:
            st.error(f"Hata: {e}")

# ---------------------------------------------------------
# MODÜL 2: MANUEL GİRİŞ
# ---------------------------------------------------------
elif menu == "📝 Manuel Giriş":
    st.title("📝 Manuel Giriş")
    
    with st.form("manuel"):
        c1, c2, c3 = st.columns(3)
        inp_date = c1.date_input("Veri Tarihi", datetime.date.today())
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
                'Sales': s, 'Unit': u, 'AdsSpend': sp, 
                'AdsSales': asales, 'AdsOrder': aorder
            }
            new_df = calculate_metrics(pd.DataFrame([row]))
            st.session_state.main_df = pd.concat([st.session_state.main_df, new_df], ignore_index=True)
            save_db(st.session_state.main_df)
            st.success("Kaydedildi.")

# ---------------------------------------------------------
# MODÜL 3: DASHBOARD
# ---------------------------------------------------------
elif menu == "📊 Dashboard":
    st.title("📊 Yönetim Paneli")
    df = st.session_state.main_df.copy()
    
    if df.empty:
        st.warning("Veri yok.")
    else:
        # FİLTRELER
        st.sidebar.markdown("---")
        st.sidebar.header("🗓️ Filtreler")
        
        # Tarih Seçimi
        today = datetime.date.today()
        start_month = today.replace(day=1)
        date_range = st.sidebar.date_input("Dönem Seçimi", (start_month, today))
        
        if len(date_range) == 2:
            start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            
            # Kıyaslama Modu
            comp_mode = st.sidebar.radio("Karşılaştırma:", ["Geçen Yıl (YoY)", "Geçen Ay (MoM)"])
            
            if comp_mode == "Geçen Yıl (YoY)":
                prev_start = start_date - relativedelta(years=1)
                prev_end = end_date - relativedelta(years=1)
            else:
                delta = end_date - start_date
                prev_end = start_date - datetime.timedelta(days=1)
                prev_start = prev_end - delta
            
            st.sidebar.caption(f"Kıyaslanan: {prev_start.date()} - {prev_end.date()}")
            
            # Firma/Ülke
            firms = ["Tümü"] + list(df['Firma'].unique())
            sel_firm = st.sidebar.selectbox("Firma", firms)
            countries = ["Tümü"] + list(df['Ulke'].unique())
            sel_country = st.sidebar.selectbox("Ülke", countries)
            
            # SÜZME İŞLEMİ (BU YIL ve GEÇEN YIL AYRI AYRI)
            # 1. Mevcut Dönem Verisi
            mask_curr = (df['Tarih'] >= start_date) & (df['Tarih'] <= end_date)
            df_curr = df.loc[mask_curr].copy()
            
            # 2. Geçmiş Dönem Verisi
            mask_prev = (df['Tarih'] >= prev_start) & (df['Tarih'] <= prev_end)
            df_prev = df.loc[mask_prev].copy()
            
            # Ortak Filtreler
            if sel_firm != "Tümü":
                df_curr = df_curr[df_curr['Firma'] == sel_firm]
                df_prev = df_prev[df_prev['Firma'] == sel_firm]
            if sel_country != "Tümü":
                df_curr = df_curr[df_curr['Ulke'] == sel_country]
                df_prev = df_prev[df_prev['Ulke'] == sel_country]
            
            # --- KPI HESAPLAMA ---
            curr_sales = df_curr['Sales'].sum()
            prev_sales = df_prev['Sales'].sum()
            
            curr_ads_order = df_curr['AdsOrder'].sum()
            prev_ads_order = df_prev['AdsOrder'].sum()
            
            diff_sales = curr_sales - prev_sales
            growth_sales = (diff_sales / prev_sales * 100) if prev_sales > 0 else 0
            
            # Oranlar (Weighted Avg)
            tacos = (df_curr['AdsSpend'].sum() / curr_sales * 100) if curr_sales > 0 else 0
            acos = (df_curr['AdsSpend'].sum() / df_curr['AdsSales'].sum() * 100) if df_curr['AdsSales'].sum() > 0 else 0
            
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Ciro", f"{curr_sales:,.0f} €", f"%{growth_sales:.1f}")
            c2.metric("Kıyaslanan Ciro", f"{prev_sales:,.0f} €", f"{diff_sales:,.0f} €")
            c3.metric("Ads Order", f"{curr_ads_order:,.0f}", f"{curr_ads_order - prev_ads_order:,.0f}")
            c4.metric("TACOS", f"%{tacos:.1f}")
            c5.metric("ACOS", f"%{acos:.1f}")
            
            st.divider()
            
            # --- GRAFİKLER ---
            cg1, cg2 = st.columns([2, 1])
            with cg1:
                # Karşılaştırmalı Bar Chart Hazırlığı
                grp = 'Ulke' if sel_firm != "Tümü" else 'Firma'
                
                # Bu yıl ve Geçen yılı birleştirip grafiğe ver
                df_curr_grp = df_curr.groupby(grp)['Sales'].sum().reset_index()
                df_curr_grp['Dönem'] = 'Bu Dönem'
                
                df_prev_grp = df_prev.groupby(grp)['Sales'].sum().reset_index()
                df_prev_grp['Dönem'] = 'Geçmiş Dönem'
                
                df_chart = pd.concat([df_curr_grp, df_prev_grp])
                
                fig = px.bar(df_chart, x=grp, y='Sales', color='Dönem', barmode='group', title="Dönemsel Karşılaştırma", text_auto='.2s')
                st.plotly_chart(fig, use_container_width=True)
                
            with cg2:
                fig2 = px.scatter(df_curr, x="AdsSpend", y="Sales", size="AdsOrder", color="Ulke", title="Spend vs Sales (Bubble: AdsOrder)")
                st.plotly_chart(fig2, use_container_width=True)
            
            # --- EDITABLE TABLE ---
            st.subheader("📝 Veri Düzenleme")
            
            # Tabloya Previous Sales gibi kolonları merge etmek yerine, sadece Current Data'yı düzenletiyoruz.
            # Kullanıcı analiz yaparken zaten yukarıdaki grafikte geçmişi görüyor.
            
            edit_cols = ['id', 'Tarih', 'Firma', 'Ulke', 'Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'ACOS', 'TACOS']
            
            edited_df = st.data_editor(
                df_curr[edit_cols],
                column_config={
                    "id": st.column_config.NumberColumn(disabled=True),
                    "ACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                    "TACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                    "Tarih": st.column_config.DateColumn(format="DD.MM.YYYY"),
                },
                hide_index=True,
                use_container_width=True,
                key="editor"
            )
            
            if st.button("💾 Değişiklikleri Kaydet"):
                try:
                    master_df = st.session_state.main_df.copy()
                    for index, row in edited_df.iterrows():
                        row_id = row['id']
                        mask = master_df['id'] == row_id
                        if mask.any():
                            cols_upd = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'Firma', 'Ulke', 'Tarih']
                            for c in cols_upd:
                                master_df.loc[mask, c] = row[c]
                    
                    master_df = calculate_metrics(master_df)
                    st.session_state.main_df = master_df
                    save_db(master_df)
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
