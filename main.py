import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime
from dateutil.relativedelta import relativedelta

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Yönetim Paneli Pro", layout="wide", page_icon="🚀")

DB_FILE = 'eticaret_db_pro.csv'

# ---------------------------------------------------------
# 1. HESAPLAMA VE VERİTABANI MOTORU
# ---------------------------------------------------------
def init_db():
    columns = [
        'id', # Satırları benzersiz tanımlamak için
        'Tarih', 'Firma', 'Ulke', 
        'Sales', 'Unit', 'AdsSpend', 'AdsSales', 
        'PrevSales', 'PrevUnit', 'PrevAdsSpend',
        'ACOS', 'TACOS', 'AOV'
    ]
    
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=columns)
        df.to_csv(DB_FILE, index=False)
        return df
    else:
        df = pd.read_csv(DB_FILE)
        # Tarih sütununu datetime yap
        df['Tarih'] = pd.to_datetime(df['Tarih'])
        # ID yoksa (eski veriler için) oluştur
        if 'id' not in df.columns:
            df['id'] = range(1, len(df) + 1)
        return df

def calculate_metrics(df):
    """Otomatik Hesaplama Motoru"""
    cols = ['Sales', 'Unit', 'AdsSpend', 'AdsSales']
    for col in cols:
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
# MODÜL 1: EXCEL YÜKLEME (Tarih Atamalı)
# ---------------------------------------------------------
if menu == "📤 Excel Yükle":
    st.title("📤 Excel Verisi Yükle")
    uploaded_file = st.file_uploader("Dosya Seç", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            xls = pd.read_excel(uploaded_file, sheet_name=None)
            sheet_names = list(xls.keys())
            
            st.divider()
            c1, c2 = st.columns(2)
            selected_sheet = c1.selectbox("Sekme Seçin", sheet_names)
            
            # Bu veriler hangi tarihe ait? (Örn: OCAK sekmesi ise 01.01.2025)
            # Takvim filtresi için bu tarih hayati önem taşır.
            default_date = datetime.date.today().replace(day=1)
            ref_date = c2.date_input("Bu verilerin ait olduğu tarih (Ayın 1'i önerilir):", default_date)
            
            df_temp = xls[selected_sheet].copy()
            # Başlık bulma mantığı
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
            
            # Helper
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
            with col3:
                map_psales = st.selectbox("2024 Sales", cols, index=get_col(['2024 sales'], cols))
                map_punit = st.selectbox("2024 Unit", cols, index=get_col(['2024 unit'], cols))
                map_pspend = st.selectbox("2024 Spend", cols, index=get_col(['2024 ads'], cols))

            if st.button("💾 Kaydet"):
                new_data = pd.DataFrame()
                new_data['Firma'] = df_temp[map_firm]
                new_data['Ulke'] = df_temp[map_country]
                new_data['Tarih'] = pd.to_datetime(ref_date)
                
                # ID Oluştur
                start_id = st.session_state.main_df['id'].max() if not st.session_state.main_df.empty else 0
                if pd.isna(start_id): start_id = 0
                new_data['id'] = range(int(start_id) + 1, int(start_id) + 1 + len(new_data))
                
                # Temizlik
                for c, m in [('Sales', map_sales), ('Unit', map_unit), ('AdsSpend', map_spend), 
                             ('AdsSales', map_asales), ('PrevSales', map_psales), 
                             ('PrevUnit', map_punit), ('PrevAdsSpend', map_pspend)]:
                    new_data[c] = df_temp[m].apply(clean_currency)

                new_data = new_data.dropna(subset=['Firma'])
                new_data = new_data[new_data['Sales'] > 0]
                
                # Hesapla ve Ekle
                new_data = calculate_metrics(new_data)
                st.session_state.main_df = pd.concat([st.session_state.main_df, new_data], ignore_index=True)
                save_db(st.session_state.main_df)
                st.success(f"{len(new_data)} satır kaydedildi.")

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
        
        c4, c5, c6, c7 = st.columns(4)
        s = c4.number_input("Sales", min_value=0.0)
        u = c5.number_input("Unit", min_value=0)
        sp = c6.number_input("Spend", min_value=0.0)
        asales = c7.number_input("Ads Sales", min_value=0.0)
        
        if st.form_submit_button("Kaydet"):
            # ID Bul
            max_id = st.session_state.main_df['id'].max()
            new_id = 1 if pd.isna(max_id) else max_id + 1
            
            row = {
                'id': new_id, 'Tarih': pd.to_datetime(inp_date),
                'Firma': inp_firm, 'Ulke': inp_country,
                'Sales': s, 'Unit': u, 'AdsSpend': sp, 'AdsSales': asales,
                'PrevSales': 0, 'PrevUnit': 0, 'PrevAdsSpend': 0
            }
            new_df = calculate_metrics(pd.DataFrame([row]))
            st.session_state.main_df = pd.concat([st.session_state.main_df, new_df], ignore_index=True)
            save_db(st.session_state.main_df)
            st.success("Kaydedildi.")

# ---------------------------------------------------------
# MODÜL 3: DASHBOARD & DÜZENLEME (CORE)
# ---------------------------------------------------------
elif menu == "📊 Dashboard & Düzenleme":
    st.title("📊 Yönetim Paneli")
    df = st.session_state.main_df.copy()
    
    if df.empty:
        st.warning("Veri yok.")
    else:
        # --- 1. FILTRELER ---
        st.sidebar.markdown("---")
        st.sidebar.header("🗓️ Tarih & Filtre")
        
        # Tarih Aralığı
        today = datetime.date.today()
        start_month = today.replace(day=1)
        date_range = st.sidebar.date_input("Analiz Dönemi", (start_month, today))
        
        if len(date_range) == 2:
            start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            
            # --- 2. KARŞILAŞTIRMA MANTIĞI (YoY vs MoM) ---
            comp_type = st.sidebar.radio("Karşılaştırma Tipi:", ["Geçen Yıl (YoY)", "Bir Önceki Dönem (MoM)"])
            
            if comp_type == "Geçen Yıl (YoY)":
                # Tarihleri 1 yıl geri al
                prev_start = start_date - relativedelta(years=1)
                prev_end = end_date - relativedelta(years=1)
                comp_label = "Geçen Yıl"
            else:
                # Seçilen gün sayısı kadar geri git
                delta = end_date - start_date
                prev_end = start_date - datetime.timedelta(days=1)
                prev_start = prev_end - delta
                comp_label = "Önceki Dönem"
            
            st.sidebar.info(f"Kıyaslanan: {prev_start.strftime('%d.%m.%Y')} - {prev_end.strftime('%d.%m.%Y')}")
            
            # Firma/Ülke Filtresi
            firms = ["Tümü"] + list(df['Firma'].unique())
            countries = ["Tümü"] + list(df['Ulke'].unique())
            sel_firm = st.sidebar.selectbox("Firma", firms)
            sel_country = st.sidebar.selectbox("Ülke", countries)
            
            # VERİYİ SÜZ (Tarih Bazlı)
            mask_current = (df['Tarih'] >= start_date) & (df['Tarih'] <= end_date)
            df_curr = df.loc[mask_current].copy()
            
            # Eğer MoM seçildiyse geçmiş veriyi tarih aralığından bulmalıyız
            # Eğer YoY seçildiyse veritabanındaki 'PrevSales' sütununu mu kullanalım yoksa tarihe mi bakalım?
            # En doğrusu: Eğer veritabanında tarih varsa tarihe bakmak.
            mask_prev = (df['Tarih'] >= prev_start) & (df['Tarih'] <= prev_end)
            df_prev_period = df.loc[mask_prev].copy()
            
            # Ek filtreler
            if sel_firm != "Tümü":
                df_curr = df_curr[df_curr['Firma'] == sel_firm]
                df_prev_period = df_prev_period[df_prev_period['Firma'] == sel_firm]
            if sel_country != "Tümü":
                df_curr = df_curr[df_curr['Ulke'] == sel_country]
                df_prev_period = df_prev_period[df_prev_period['Ulke'] == sel_country]
            
            # --- 3. KPI HESAPLAMA ---
            curr_sales = df_curr['Sales'].sum()
            curr_spend = df_curr['AdsSpend'].sum()
            
            # Karşılaştırma verisini belirle
            if comp_type == "Bir Önceki Dönem (MoM)":
                prev_sales_total = df_prev_period['Sales'].sum()
            else:
                # YoY ise: Veritabanında zaten "PrevSales" sütunu varsa onu kullanabiliriz (Excel'den gelmişse)
                # Yoksa tarih bazlı hesaplarız. Hibrit yaklaşım:
                if not df_prev_period.empty:
                    prev_sales_total = df_prev_period['Sales'].sum() # Veritabanında geçen yılın kaydı varsa
                else:
                    prev_sales_total = df_curr['PrevSales'].sum() # Yoksa Excel'den gelen '2024 Sales' sütununu kullan
            
            diff = curr_sales - prev_sales_total
            growth = (diff / prev_sales_total * 100) if prev_sales_total > 0 else 0
            
            # KPI Kartları
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Toplam Ciro", f"{curr_sales:,.0f} €", f"%{growth:.1f}")
            c2.metric(f"{comp_label} Ciro", f"{prev_sales_total:,.0f} €", f"{diff:,.0f} €")
            
            # Ağırlıklı Ortalamalar
            tacos = (curr_spend / curr_sales * 100) if curr_sales > 0 else 0
            c3.metric("Genel TACOS", f"%{tacos:.1f}")
            c4.metric("Seçili Kayıt", f"{len(df_curr)}")
            
            st.divider()
            
            # --- 4. GRAFİKLER ---
            cg1, cg2 = st.columns([2, 1])
            with cg1:
                grp = 'Ulke' if sel_firm != "Tümü" else 'Firma'
                bar_data = df_curr.groupby(grp)['Sales'].sum().reset_index()
                fig = px.bar(bar_data, x=grp, y='Sales', title=f"{grp} Bazlı Ciro", text_auto='.2s')
                st.plotly_chart(fig, use_container_width=True)
            with cg2:
                fig2 = px.scatter(df_curr, x="Sales", y="TACOS", size="AdsSpend", color="Ulke", title="Kârlılık Analizi")
                st.plotly_chart(fig2, use_container_width=True)

            # --- 5. DÜZENLENEBİLİR TABLO (EDITABLE DATAFRAME) ---
            st.subheader("📝 Detaylı Verileri Düzenle")
            st.info("Hücrelere tıklayarak verileri değiştirebilirsiniz. 'Kaydet' butonuna bastığınızda ACOS/TACOS otomatik hesaplanıp güncellenir.")
            
            # Gösterilecek ve düzenlenecek sütunlar
            edit_cols = ['id', 'Tarih', 'Firma', 'Ulke', 'Sales', 'Unit', 'AdsSpend', 'AdsSales', 'ACOS', 'TACOS', 'AOV']
            
            # Data Editor Konfigürasyonu
            edited_df = st.data_editor(
                df_curr[edit_cols],
                column_config={
                    "id": st.column_config.NumberColumn(disabled=True), # ID değiştirilemez
                    "ACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True), # Otomatik hesaplanır, elle girilmez
                    "TACOS": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                    "AOV": st.column_config.NumberColumn(format="%.2f €", disabled=True),
                    "Tarih": st.column_config.DateColumn(format="DD.MM.YYYY"),
                },
                hide_index=True,
                use_container_width=True,
                key="data_editor"
            )
            
            # KAYDETME MANTIĞI
            if st.button("💾 Değişiklikleri Kaydet ve Hesapla"):
                try:
                    # 1. Ana veritabanını al
                    master_df = st.session_state.main_df.copy()
                    
                    # 2. Düzenlenen satırları bul
                    # edited_df içindeki her satır için master_df'yi güncelle
                    for index, row in edited_df.iterrows():
                        row_id = row['id']
                        # İlgili ID'nin indexini bul
                        mask = master_df['id'] == row_id
                        
                        if mask.any():
                            # Sütunları güncelle (Sadece kullanıcı girdilerini)
                            master_df.loc[mask, 'Sales'] = row['Sales']
                            master_df.loc[mask, 'Unit'] = row['Unit']
                            master_df.loc[mask, 'AdsSpend'] = row['AdsSpend']
                            master_df.loc[mask, 'AdsSales'] = row['AdsSales']
                            master_df.loc[mask, 'Firma'] = row['Firma']
                            master_df.loc[mask, 'Ulke'] = row['Ulke']
                            master_df.loc[mask, 'Tarih'] = row['Tarih']
                    
                    # 3. Tüm veritabanı için metrikleri yeniden hesapla
                    # (Böylece değişen Sales/Spend değerleri TACOS'u günceller)
                    master_df = calculate_metrics(master_df)
                    
                    # 4. Kaydet
                    st.session_state.main_df = master_df
                    save_db(master_df)
                    st.success("✅ Veriler güncellendi, oranlar yeniden hesaplandı!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Kayıt sırasında hata: {e}")

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
