import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Yönetim Paneli (V3)", layout="wide", page_icon="📈")

# Veritabanı Dosya Adı
DB_FILE = 'eticaret_db.csv'

# ---------------------------------------------------------
# 1. HESAPLAMA VE VERİTABANI MOTORU
# ---------------------------------------------------------
def init_db():
    """Veritabanı dosyasını başlatır veya yükler."""
    # Veritabanında tutacağımız standart sütunlar
    columns = [
        'KayitTarihi', 'Ay', 'Firma', 'Ulke', 
        'Sales', 'Unit', 'AdsSpend', 'AdsSales', # Bu Yılın Verileri
        'PrevSales', 'PrevUnit', 'PrevAdsSpend', # Geçen Yılın Verileri
        'ACOS', 'TACOS', 'AOV' # Otomatik Hesaplanacaklar
    ]
    
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=columns)
        df.to_csv(DB_FILE, index=False)
        return df
    else:
        return pd.read_csv(DB_FILE)

def calculate_metrics(df):
    """
    Otomatik Hesaplama Motoru:
    Verilen dataframe içindeki ham verilerden oranları hesaplar.
    """
    # Veri tiplerini garantiye al
    cols_to_numeric = ['Sales', 'Unit', 'AdsSpend', 'AdsSales', 'PrevSales', 'PrevUnit', 'PrevAdsSpend']
    for col in cols_to_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 1. ACOS = Ads Spend / Ads Sales
    df['ACOS'] = df.apply(lambda x: (x['AdsSpend'] / x['AdsSales']) if x['AdsSales'] > 0 else 0, axis=1)
    
    # 2. TACOS = Ads Spend / Total Sales
    df['TACOS'] = df.apply(lambda x: (x['AdsSpend'] / x['Sales']) if x['Sales'] > 0 else 0, axis=1)
    
    # 3. AOV = Sales / Unit
    df['AOV'] = df.apply(lambda x: (x['Sales'] / x['Unit']) if x['Unit'] > 0 else 0, axis=1)
    
    return df

def save_to_db(new_data):
    """Veriyi hesaplar ve veritabanına ekler."""
    # Önce hesaplamaları yap
    new_data = calculate_metrics(new_data)
    
    # Mevcut veritabanını oku ve birleştir
    current_db = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else init_db()
    updated_db = pd.concat([current_db, new_data], ignore_index=True)
    
    # Kaydet
    updated_db.to_csv(DB_FILE, index=False)
    return updated_db

def clean_currency(x):
    """Excel'den gelen kirli veriyi (1.200 TL vb.) temizler."""
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
menu = st.sidebar.radio("Seçim Yapınız:", 
    ["📊 Dashboard (Analiz)", "📤 Excel Yükle (Toplu)", "📝 Manuel Giriş (Tekli)", "⚙️ Ayarlar"]
)

# ---------------------------------------------------------
# MODÜL 1: EXCEL YÜKLEME (Yeni Formata Uygun)
# ---------------------------------------------------------
if menu == "📤 Excel Yükle (Toplu)":
    st.title("📤 Excel Verisi Yükle")
    st.info("Yeni basitleştirilmiş Excel formatınıza göre yükleme yapabilirsiniz.")

    uploaded_file = st.file_uploader("Excel Dosyası Seçin (.xlsx)", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            # Tüm sekmeleri oku
            xls = pd.read_excel(uploaded_file, sheet_name=None)
            sheet_names = list(xls.keys())
            
            st.divider()
            c1, c2 = st.columns(2)
            selected_sheet = c1.selectbox("Hangi Ay/Sekme Yüklenecek?", sheet_names)
            
            # Seçilen sekmeyi dataframe'e çevir
            df_temp = xls[selected_sheet].copy()
            
            # --- AKILLI BAŞLIK BULMA ---
            # Bazen başlıklar 1. satırda değil 3. satırda olabiliyor.
            # 'Firm' veya 'Country' kelimesini arayıp başlık satırını set ediyoruz.
            header_row = 0
            for i, row in df_temp.head(10).iterrows():
                row_str = row.astype(str).str.lower().tolist()
                if any('firm' in s or 'country' in s for s in row_str):
                    header_row = i + 1 # Pandas header indexi (0-based olduğu için +1 satır numarası değil)
                    break
            
            # Dosyayı doğru başlık satırı ile tekrar oku
            if header_row > 0:
                df_temp = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=header_row)
            
            # Boş satırları temizle
            df_temp = df_temp.dropna(how='all')
            cols = df_temp.columns.tolist()
            
            # --- SÜTUN EŞLEŞTİRME (Otomatik Tanıma) ---
            st.subheader("🔗 Sütun Eşleştirme")
            st.caption("Otomatik seçilen sütunları kontrol ediniz.")

            def get_col_index(keywords, columns):
                for i, c in enumerate(columns):
                    if any(k in str(c).lower() for k in keywords): return i
                return 0

            col1, col2, col3 = st.columns(3)
            
            # Yeni dosya formatına uygun anahtar kelimeler
            with col1:
                st.markdown("##### 📍 Kimlik")
                map_firm = st.selectbox("Firma (Firm)", cols, index=get_col_index(['firm', 'firma'], cols))
                map_country = st.selectbox("Ülke (Country)", cols, index=get_col_index(['country', 'ulke', 'ülke'], cols))
                input_ay = st.text_input("Dönem/Ay İsmi", value=selected_sheet)

            with col2:
                st.markdown("##### 📅 Bu Yıl (2025)")
                map_sales = st.selectbox("Sales (Ciro)", cols, index=get_col_index(['sales', 'ciro'], cols))
                map_unit = st.selectbox("Unit (Adet)", cols, index=get_col_index(['unit', 'order', 'adet'], cols))
                map_spend = st.selectbox("Ads Spend", cols, index=get_col_index(['ads spend', 'reklam', 'spend'], cols))
                map_ads_sales = st.selectbox("Ads Sales", cols, index=get_col_index(['ads sales', 'reklam ciro'], cols))

            with col3:
                st.markdown("##### ⏮️ Geçen Yıl (2024)")
                # "2024 Sales" gibi sütunları bulmaya çalış
                map_prev_sales = st.selectbox("2024 Sales", cols, index=get_col_index(['2024 sales', 'geçen yıl ciro'], cols))
                map_prev_unit = st.selectbox("2024 Unit", cols, index=get_col_index(['2024 unit', '2024 order'], cols))
                map_prev_spend = st.selectbox("2024 Ads Spend", cols, index=get_col_index(['2024 ads spend'], cols))

            st.divider()
            
            if st.button("💾 Verileri Kaydet"):
                # Yeni veriyi standart formata dök
                new_db_entry = pd.DataFrame()
                new_db_entry['Firma'] = df_temp[map_firm]
                new_db_entry['Ulke'] = df_temp[map_country]
                new_db_entry['Ay'] = input_ay
                new_db_entry['KayitTarihi'] = datetime.date.today()
                
                # Sayısal verileri temizle
                new_db_entry['Sales'] = df_temp[map_sales].apply(clean_currency)
                new_db_entry['Unit'] = df_temp[map_unit].apply(clean_currency)
                new_db_entry['AdsSpend'] = df_temp[map_spend].apply(clean_currency)
                new_db_entry['AdsSales'] = df_temp[map_ads_sales].apply(clean_currency)
                
                # Geçen yıl verileri
                new_db_entry['PrevSales'] = df_temp[map_prev_sales].apply(clean_currency)
                new_db_entry['PrevUnit'] = df_temp[map_prev_unit].apply(clean_currency)
                new_db_entry['PrevAdsSpend'] = df_temp[map_prev_spend].apply(clean_currency)
                
                # Boş veya 0 cirolu satırları at (Firma adı olmayanlar vb.)
                new_db_entry = new_db_entry.dropna(subset=['Firma'])
                new_db_entry = new_db_entry[new_db_entry['Sales'] > 0]
                
                # Kaydet (Hesaplama fonksiyonu save_to_db içinde çalışır)
                updated_df = save_to_db(new_db_entry)
                st.session_state.main_df = updated_df
                
                st.success(f"✅ {len(new_db_entry)} satır veri başarıyla işlendi, hesaplandı ve kaydedildi!")
                st.dataframe(new_db_entry.head())

        except Exception as e:
            st.error(f"Dosya işlenirken hata oluştu: {e}")

# ---------------------------------------------------------
# MODÜL 2: MANUEL GİRİŞ
# ---------------------------------------------------------
elif menu == "📝 Manuel Giriş (Tekli)":
    st.title("📝 Manuel Veri Girişi")
    st.info("Excel olmadan tek bir kayıt ekleyin. Oranlar otomatik hesaplanır.")

    with st.form("manuel_entry"):
        col1, col2 = st.columns(2)
        inp_ay = col1.selectbox("Ay", ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])
        inp_firma = col2.text_input("Firma Adı", "HomeByHome")
        inp_ulke = st.text_input("Ülke", "DE")
        
        st.markdown("---")
        st.subheader("Bu Yıl Verileri")
        c1, c2, c3, c4 = st.columns(4)
        inp_sales = c1.number_input("Sales (Ciro)", min_value=0.0)
        inp_unit = c2.number_input("Unit (Adet)", min_value=0)
        inp_spend = c3.number_input("Ads Spend", min_value=0.0)
        inp_ads_sales = c4.number_input("Ads Sales", min_value=0.0)
        
        st.subheader("Geçen Yıl (2024) Verileri (Opsiyonel)")
        c5, c6, c7 = st.columns(3)
        inp_prev_sales = c5.number_input("2024 Sales", min_value=0.0)
        inp_prev_unit = c6.number_input("2024 Unit", min_value=0)
        inp_prev_spend = c7.number_input("2024 Ads Spend", min_value=0.0)
        
        submitted = st.form_submit_button("💾 Kaydet")
        
        if submitted:
            row = {
                'KayitTarihi': datetime.date.today(),
                'Ay': inp_ay,
                'Firma': inp_firma,
                'Ulke': inp_ulke,
                'Sales': inp_sales,
                'Unit': inp_unit,
                'AdsSpend': inp_spend,
                'AdsSales': inp_ads_sales,
                'PrevSales': inp_prev_sales,
                'PrevUnit': inp_prev_unit,
                'PrevAdsSpend': inp_prev_spend
            }
            new_df = pd.DataFrame([row])
            updated_df = save_to_db(new_df)
            st.session_state.main_df = updated_df
            st.success("✅ Kayıt eklendi! Metrikler otomatik hesaplandı.")

# ---------------------------------------------------------
# MODÜL 3: DASHBOARD
# ---------------------------------------------------------
elif menu == "📊 Dashboard (Analiz)":
    st.title("📊 Performans Analizi")
    
    df = st.session_state.main_df
    
    if df.empty:
        st.warning("Veritabanı boş. Lütfen veri yükleyin.")
    else:
        # FİLTRELER
        st.sidebar.markdown("---")
        st.sidebar.header("Filtreler")
        
        filter_ay = st.sidebar.multiselect("Ay Seçin", df['Ay'].unique(), default=df['Ay'].unique())
        filter_firma = st.sidebar.multiselect("Firma Seçin", df['Firma'].unique(), default=df['Firma'].unique())
        
        if not filter_ay: filter_ay = df['Ay'].unique()
        if not filter_firma: filter_firma = df['Firma'].unique()
        
        # Filtreleme
        df_viz = df[df['Ay'].isin(filter_ay) & df['Firma'].isin(filter_firma)]
        
        # --- KPI HESAPLAMA (Ağırlıklı Ortalama) ---
        total_sales = df_viz['Sales'].sum()
        total_prev_sales = df_viz['PrevSales'].sum()
        total_spend = df_viz['AdsSpend'].sum()
        total_ads_sales = df_viz['AdsSales'].sum()
        total_unit = df_viz['Unit'].sum()
        
        # Oranları toplamlar üzerinden hesapla (Doğrusu budur)
        kpi_acos = (total_spend / total_ads_sales * 100) if total_ads_sales > 0 else 0
        kpi_tacos = (total_spend / total_sales * 100) if total_sales > 0 else 0
        kpi_aov = (total_sales / total_unit) if total_unit > 0 else 0
        
        growth = ((total_sales - total_prev_sales) / total_prev_sales * 100) if total_prev_sales > 0 else 0
        
        # Kartlar
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Toplam Ciro (Sales)", f"{total_sales:,.0f} €", f"%{growth:.1f} Büyüme")
        k2.metric("Toplam Harcama (Spend)", f"{total_spend:,.0f} €")
        k3.metric("Genel ACOS", f"%{kpi_acos:.1f}")
        k4.metric("Genel TACOS", f"%{kpi_tacos:.1f}")
        k5.metric("Genel AOV", f"{kpi_aov:.1f} €")
        
        st.divider()
        
        # --- GRAFİKLER ---
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("📈 Satış Karşılaştırması (2024 vs 2025)")
            # Ülke veya Ay bazlı gruplama
            group_col = 'Ulke' if len(filter_ay) == 1 else 'Ay'
            
            chart_data = df_viz.groupby(group_col)[['Sales', 'PrevSales']].sum().reset_index()
            chart_melt = chart_data.melt(id_vars=group_col, var_name='Yıl', value_name='Ciro')
            
            fig = px.bar(chart_melt, x=group_col, y='Ciro', color='Yıl', barmode='group',
                         title=f"{group_col} Bazlı Ciro Kıyaslaması", text_auto='.2s',
                         color_discrete_map={'Sales': '#00CC96', 'PrevSales': '#EF553B'})
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("📉 Kârlılık (TACOS)")
            # Bubble chart: Ciro vs Tacos
            fig2 = px.scatter(df_viz, x="Sales", y="TACOS", size="AdsSpend", color="Ulke",
                              hover_name="Firma", title="Satış vs TACOS İlişkisi")
            st.plotly_chart(fig2, use_container_width=True)

        # DETAY TABLO
        with st.expander("📋 Detaylı Verileri Göster"):
            st.dataframe(df_viz)

# ---------------------------------------------------------
# MODÜL 4: AYARLAR
# ---------------------------------------------------------
elif menu == "⚙️ Ayarlar":
    st.title("⚙️ Ayarlar")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("Veritabanını indirip yedekleyebilirsiniz.")
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                st.download_button("📥 Veritabanını İndir (CSV)", f, "eticaret_yedek.csv", "text/csv")
    
    with col2:
        st.error("Dikkat: Tüm verileri siler!")
        if st.button("🗑️ Veritabanını SIFIRLA"):
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            st.session_state.main_df = init_db()
            st.success("Sistem sıfırlandı.")
            st.rerun()
