import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime
from dateutil.relativedelta import relativedelta

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Yönetim Paneli V5", layout="wide", page_icon="📈")

DB_FILE = 'eticaret_db_pro_v5.csv'

# ---------------------------------------------------------
# 1. HESAPLAMA VE VERİTABANI MOTORU
# ---------------------------------------------------------
def init_db():
    columns = [
        'id', 
        'Tarih', 'Firma', 'Ulke', 
        'Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 
        'PrevSales', 'PrevUnit', 'PrevAdsSpend', 'PrevAdsOrder', 'PrevAdsSales',
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
        
        # Eksik sütunları tamamla
        for col in columns:
            if col not in df.columns:
                df[col] = 0
                
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
    
    return df

def save_db(df):
    """Veritabanını CSV'ye yazar"""
    df.to_csv(DB_FILE, index=False)

def clean_currency(x):
    if isinstance(x, str):
        clean = x.replace('TL', '').replace('₺', '').replace('%', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(clean)
        except:
            return 0.0
    return x

# Session State Başlatma
if 'main_df' not in st.session_state:
    st.session_state.main_df = init_db()

# ---------------------------------------------------------
# 2. SIDEBAR MENÜ
# ---------------------------------------------------------
st.sidebar.title("🎛️ Menü")
menu = st.sidebar.radio("Seçim:", ["📊 Dashboard & Düzenleme", "📤 Excel Yükle", "📝 Manuel Giriş", "⚙️ Ayarlar"])

# ---------------------------------------------------------
# MODÜL 1: EXCEL YÜKLEME
# ---------------------------------------------------------
if menu == "📤 Excel Yükle":
    st.title("📤 Excel Verisi Yükle")
    st.info("Yükleme sırasında 'Toplam' satırları otomatik temizlenir ve sistem tarafından dinamik hesaplanır.")
    
    uploaded_file = st.file_uploader("Dosya Seç", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            xls = pd.read_excel(uploaded_file, sheet_name=None)
            sheet_names = list(xls.keys())
            
            st.divider()
            c1, c2 = st.columns(2)
            selected_sheet = c1.selectbox("Sekme Seçin", sheet_names)
            
            default_date = datetime.date.today().replace(day=1)
            ref_date = c2.date_input("Bu verilerin ait olduğu tarih:", default_date)
            
            df_temp = xls[selected_sheet].copy()
            
            # Başlık bulma
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

            col1, col2, col3 = st.columns(3)
            with col1:
                map_firm = st.selectbox("Firma", cols, index=get_col(['firm'], cols))
                map_country = st.selectbox("Ülke", cols, index=get_col(['country', 'ulke'], cols))
            with col2:
                map_sales = st.selectbox("Sales", cols, index=get_col(['sales', 'ciro'], cols))
                map_unit = st.selectbox("Unit", cols, index=get_col(['unit', 'order'], cols))
                map_spend = st.selectbox("Ads Spend", cols, index=get_col(['spend'], cols))
                map_asales = st.selectbox("Ads Sales", cols, index=get_col(['ads sales'], cols))
                map_aorder = st.selectbox("Ads Order", cols, index=get_col(['ads order', 'reklam order'], cols))
            with col3:
                map_psales = st.selectbox("2024 Sales", cols, index=get_col(['2024 sales'], cols))
                map_punit = st.selectbox("2024 Unit", cols, index=get_col(['2024 unit'], cols))
                map_pspend = st.selectbox("2024 Ads Spend", cols, index=get_col(['2024 ads'], cols))
                map_pasales = st.selectbox("2024 Ads Sales", cols, index=get_col(['2024 ads sales'], cols))

            if st.button("💾 Kaydet"):
                new_data = pd.DataFrame()
                new_data['Firma'] = df_temp[map_firm]
                new_data['Ulke'] = df_temp[map_country]
                new_data['Tarih'] = pd.to_datetime(ref_date)
                
                # ID Oluştur
                start_id = st.session_state.main_df['id'].max() if not st.session_state.main_df.empty else 0
                if pd.isna(start_id): start_id = 0
                new_data['id'] = range(int(start_id) + 1, int(start_id) + 1 + len(new_data))
                
                col_mappings = [
                    ('Sales', map_sales), ('Unit', map_unit), ('AdsSpend', map_spend), 
                    ('AdsSales', map_asales), ('AdsOrder', map_aorder),
                    ('PrevSales', map_psales), ('PrevUnit', map_punit), 
                    ('PrevAdsSpend', map_pspend), ('PrevAdsSales', map_pasales)
                ]
                
                for c, m in col_mappings:
                    new_data[c] = df_temp[m].apply(clean_currency)

                # --- TEMİZLİK ---
                # 1. Boş Firma kayıtlarını sil
                new_data = new_data.dropna(subset=['Firma'])
                # 2. Ciro 0 olanları sil
                new_data = new_data[new_data['Sales'] > 0]
                # 3. Excel'deki "Toplam" satırlarını sil (Çifte sayımı önlemek için)
                new_data = new_data[~new_data['Ulke'].str.contains('Toplam', case=False, na=False)]
                new_data = new_data[~new_data['Ulke'].str.contains('Total', case=False, na=False)]
                
                # Hesapla ve Ekle
                new_data = calculate_metrics(new_data)
                
                if 'PrevAdsOrder' not in new_data.columns: new_data['PrevAdsOrder'] = 0
                
                st.session_state.main_df = pd.concat([st.session_state.main_df, new_data], ignore_index=True)
                save_db(st.session_state.main_df)
                st.success(f"{len(new_data)} satır başarıyla kaydedildi. ('Toplam' satırları hariç tutuldu)")

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
        inp_country = c3.text_input("Ülke", "DE")
        
        st.markdown("---")
        c4, c5, c6 = st.columns(3)
        s = c4.number_input("Sales (Ciro)", min_value=0.0)
        u = c5.number_input("Total Unit (Order)", min_value=0)
        sp = c6.number_input("Ads Spend", min_value=0.0)
        
        c7, c8 = st.columns(2)
        asales = c7.number_input("Ads Sales", min_value=0.0)
        aorder = c8.number_input("Ads Order", min_value=0)
        
        if st.form_submit_button("Kaydet"):
            max_id = st.session_state.main_df['id'].max()
            new_id = 1 if pd.isna(max_id) else max_id + 1
            
            row = {
                'id': new_id, 'Tarih': pd.to_datetime(inp_date),
                'Firma': inp_firm, 'Ulke': inp_country,
                'Sales': s, 'Unit': u, 'AdsSpend': sp, 
                'AdsSales': asales, 'AdsOrder': aorder,
                'PrevSales': 0, 'PrevUnit': 0, 'PrevAdsSpend': 0, 'PrevAdsOrder': 0, 'PrevAdsSales': 0
            }
            new_df = calculate_metrics(pd.DataFrame([row]))
            st.session_state.main_df = pd.concat([st.session_state.main_df, new_df], ignore_index=True)
            save_db(st.session_state.main_df)
            st.success("Kayıt Başarılı.")

# ---------------------------------------------------------
# MODÜL 3: DASHBOARD & DÜZENLEME
# ---------------------------------------------------------
elif menu == "📊 Dashboard & Düzenleme":
    st.title("📊 Yönetim Paneli")
    df = st.session_state.main_df.copy()
    
    if df.empty:
        st.warning("Veri yok.")
    else:
        # FİLTRELER
        st.sidebar.markdown("---")
        st.sidebar.header("🗓️ Tarih & Filtre")
        
        today = datetime.date.today()
        start_month = today.replace(day=1)
        date_range = st.sidebar.date_input("Analiz Dönemi", (start_month, today))
        
        if len(date_range) == 2:
            start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            comp_type = st.sidebar.radio("Karşılaştırma:", ["Geçen Yıl (YoY)", "Bir Önceki Dönem (MoM)"])
            
            if comp_type == "Geçen Yıl (YoY)":
                prev_start = start_date - relativedelta(years=1)
                prev_end = end_date - relativedelta(years=1)
                comp_label = "Geçen Yıl"
            else:
                delta = end_date - start_date
                prev_end = start_date - datetime.timedelta(days=1)
                prev_start = prev_end - delta
                comp_label = "Önceki Dönem"
            
            firms = ["Tümü"] + list(df['Firma'].unique())
            countries = ["Tümü"] + list(df['Ulke'].unique())
            sel_firm = st.sidebar.selectbox("Firma", firms)
            sel_country = st.sidebar.selectbox("Ülke", countries)
            
            # Veri Süzme
            mask_current = (df['Tarih'] >= start_date) & (df['Tarih'] <= end_date)
            df_curr = df.loc[mask_current].copy()
            
            mask_prev = (df['Tarih'] >= prev_start) & (df['Tarih'] <= prev_end)
            df_prev_period = df.loc[mask_prev].copy()
            
            if sel_firm != "Tümü":
                df_curr = df_curr[df_curr['Firma'] == sel_firm]
                df_prev_period = df_prev_period[df_prev_period['Firma'] == sel_firm]
            if sel_country != "Tümü":
                df_curr = df_curr[df_curr['Ulke'] == sel_country]
                df_prev_period = df_prev_period[df_prev_period['Ulke'] == sel_country]
            
            # --- KPI HESAPLAMA (Dinamik Toplam) ---
            curr_sales = df_curr['Sales'].sum()
            curr_ads_order = df_curr['AdsOrder'].sum()
            
            if comp_type == "Bir Önceki Dönem (MoM)":
                prev_sales_total = df_prev_period['Sales'].sum()
                prev_ads_order = df_prev_period['AdsOrder'].sum()
            else:
                if not df_prev_period.empty:
                    prev_sales_total = df_prev_period['Sales'].sum()
                    prev_ads_order = df_prev_period['AdsOrder'].sum()
                else:
                    prev_sales_total = df_curr['PrevSales'].sum()
                    prev_ads_order = df_curr['PrevAdsOrder'].sum()
            
            diff_sales = curr_sales - prev_sales_total
            diff_ads_order = curr_ads_order - prev_ads_order
            growth_sales = (diff_sales / prev_sales_total * 100) if prev_sales_total > 0 else 0
            
            # KPI KARTLARI
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Toplam Ciro", f"{curr_sales:,.0f} €", f"%{growth_sales:.1f}")
            c2.metric("Ads Order", f"{curr_ads_order:,.0f}", f"{diff_ads_order:,.0f} Adet")
            
            tacos = (df_curr['AdsSpend'].sum() / curr_sales * 100) if curr_sales > 0 else 0
            acos = (df_curr['AdsSpend'].sum() / df_curr['AdsSales'].sum() * 100) if df_curr['AdsSales'].sum() > 0 else 0
            
            c3.metric("Genel TACOS", f"%{tacos:.1f}")
            c4.metric("Genel ACOS", f"%{acos:.1f}")
            c5.metric("Seçili Kayıt", f"{len(df_curr)}")
            
            st.divider()
            
            # GRAFİKLER
            cg1, cg2 = st.columns([2, 1])
            with cg1:
                grp = 'Ulke' if sel_firm != "Tümü" else 'Firma'
                metric_view = st.radio("Grafik Verisi:", ["Ciro (Sales)", "Ads Order"], horizontal=True)
                y_col = 'Sales' if metric_view == "Ciro (Sales)" else 'AdsOrder'
                bar_data = df_curr.groupby(grp)[y_col].sum().reset_index()
                fig = px.bar(bar_data, x=grp, y=y_col, title=f"{grp} Bazlı {metric_view}", text_auto='.2s')
                st.plotly_chart(fig, use_container_width=True)
                
            with cg2:
                fig2 = px.scatter(df_curr, x="AdsSpend", y="AdsOrder", size="Sales", color="Ulke", title="Spend vs Ads Order")
                st.plotly_chart(fig2, use_container_width=True)

            # --- DETAY TABLO & DÜZENLEME ---
            st.subheader("📝 Detaylı Verileri Düzenle")
            
            show_growth = st.multiselect(
                "Tabloya % Değişim Sütunu Ekle:",
                ["Ciro Büyüme (Sales %)", "Adet Büyüme (Unit %)", "Reklam Büyüme (Spend %)"]
            )
            
            # Tablo Hazırlığı
            df_edit = df_curr.copy()
            
            # Toplam Satırı Ekleme (Dinamik)
            # Sadece görüntüleme amaçlı olduğu için veritabanına kaydedilmez.
            if not df_edit.empty:
                total_row = pd.DataFrame(df_edit[[
                    'Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 
                    'PrevSales', 'PrevUnit', 'PrevAdsSpend', 'PrevAdsSales'
                ]].sum()).T
                
                # Ağırlıklı Ortalamalar
                total_row['ACOS'] = (total_row['AdsSpend'] / total_row['AdsSales'] * 100) if total_row['AdsSales'].iloc[0] > 0 else 0
                total_row['TACOS'] = (total_row['AdsSpend'] / total_row['Sales'] * 100) if total_row['Sales'].iloc[0] > 0 else 0
                total_row['AOV'] = (total_row['Sales'] / total_row['Unit']) if total_row['Unit'].iloc[0] > 0 else 0
                
                total_row['Firma'] = "TOPLAM"
                total_row['Ulke'] = "-"
                total_row['Tarih'] = end_date
                total_row['id'] = -1 # Geçersiz ID
                
                # Toplam satırını en alta ekle
                df_edit = pd.concat([df_edit, total_row], ignore_index=True)

            # Büyüme hesaplamaları
            if "Ciro Büyüme (Sales %)" in show_growth:
                df_edit['Sales Growth %'] = df_edit.apply(lambda x: ((x['Sales'] - x['PrevSales']) / x['PrevSales'] * 100) if x['PrevSales'] > 0 else 0, axis=1)
            if "Adet Büyüme (Unit %)" in show_growth:
                df_edit['Unit Growth %'] = df_edit.apply(lambda x: ((x['Unit'] - x['PrevUnit']) / x['PrevUnit'] * 100) if x['PrevUnit'] > 0 else 0, axis=1)
            if "Reklam Büyüme (Spend %)" in show_growth:
                df_edit['Spend Growth %'] = df_edit.apply(lambda x: ((x['AdsSpend'] - x['PrevAdsSpend']) / x['PrevAdsSpend'] * 100) if x['PrevAdsSpend'] > 0 else 0, axis=1)
            
            base_cols = ['id', 'Tarih', 'Firma', 'Ulke', 'Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'ACOS', 'TACOS']
            growth_cols = [c for c in df_edit.columns if 'Growth %' in c]
            final_cols = base_cols + growth_cols
            
            edited_df = st.data_editor(
                df_edit[final_cols],
                column_config={
                    "id": st.column_config.NumberColumn(disabled=True),
                    "ACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                    "TACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                    "Tarih": st.column_config.DateColumn(format="DD.MM.YYYY"),
                    "Sales Growth %": st.column_config.NumberColumn(format="%.1f%%", disabled=True),
                    "Unit Growth %": st.column_config.NumberColumn(format="%.1f%%", disabled=True),
                    "Spend Growth %": st.column_config.NumberColumn(format="%.1f%%", disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                num_rows="dynamic",
                key="data_editor"
            )
            
            if st.button("💾 Değişiklikleri Kaydet"):
                try:
                    master_df = st.session_state.main_df.copy()
                    
                    for index, row in edited_df.iterrows():
                        row_id = row['id']
                        # ID'si -1 olan (Toplam satırı) veya yeni eklenen boş satırları atla
                        if row_id == -1 or pd.isna(row_id):
                            continue
                            
                        mask = master_df['id'] == row_id
                        
                        if mask.any():
                            cols_to_update = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'AdsOrder', 'Firma', 'Ulke', 'Tarih']
                            for c in cols_to_update:
                                master_df.loc[mask, c] = row[c]
                    
                    master_df = calculate_metrics(master_df)
                    st.session_state.main_df = master_df
                    save_db(master_df)
                    st.success("✅ Veriler Güncellendi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")

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
