import streamlit as st
import pandas as pd
from datetime import timedelta
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="Satış Analiz Paneli", layout="wide")

# ---------------------------------------------------------
# 1. VERİ YÜKLEME VE İŞLEME MOTORU
# ---------------------------------------------------------
@st.cache_data
def load_data(uploaded_file):
    """
    Excel/CSV dosyasını okur, sütun isimlerini standartlaştırır
    ve tarih formatını düzenler.
    """
    # Dosya tipine göre okuma
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # Sütun adlarındaki boşlukları temizle
    df.columns = df.columns.str.strip()
    
    # --- AKILLI SÜTUN EŞLEŞTİRME ---
    # Sizin Excel'deki olası isimler -> Kodun anladığı isimler
    rename_map = {
        # Ciro varyasyonları
        'Tutar': 'Ciro', 'Satış Tutarı': 'Ciro', 'Amount': 'Ciro', 'Total': 'Ciro', 'Satis Tutari': 'Ciro',
        # Adet varyasyonları
        'Adet': 'Satis_Adedi', 'Miktar': 'Satis_Adedi', 'Quantity': 'Satis_Adedi', 'Qty': 'Satis_Adedi', 'Satis Adedi': 'Satis_Adedi',
        # Hesap varyasyonları
        'Account': 'Hesap', 'Firma': 'Hesap', 'Mağaza': 'Hesap', 'Magaza': 'Hesap', 'Platform': 'Hesap',
        # Tarih varyasyonları
        'Date': 'Tarih', 'Siparis Tarihi': 'Tarih', 'İşlem Tarihi': 'Tarih'
    }
    df.rename(columns=rename_map, inplace=True)
    
    # --- TARİH OLUŞTURMA MANTIĞI ---
    # Eğer 'Tarih' sütunu yoksa ama 'Yıl' ve 'Ay' varsa bunları birleştir
    col_yil = next((c for c in ['Yıl', 'Year', 'Yil'] if c in df.columns), None)
    col_ay = next((c for c in ['Ay', 'Month', 'Donem', 'Dönem'] if c in df.columns), None)

    if 'Tarih' not in df.columns and col_yil and col_ay:
        try:
            # Türkçe Ay isimlerini sayıya çevir
            ay_map = {
                'Ocak':1, 'Şubat':2, 'Mart':3, 'Nisan':4, 'Mayıs':5, 'Haziran':6,
                'Temmuz':7, 'Ağustos':8, 'Eylül':9, 'Ekim':10, 'Kasım':11, 'Aralık':12,
                'January':1, 'February':2, 'March':3, 'April':4, 'May':5, 'June':6,
                'July':7, 'August':8, 'September':9, 'October':10, 'November':11, 'December':12
            }
            
            # Eğer ay sütunu metinse (Ocak vb.) sayıya çevir
            if df[col_ay].dtype == 'O':
                df['Ay_Num'] = df[col_ay].map(ay_map).fillna(1).astype(int)
            else:
                df['Ay_Num'] = df[col_ay].astype(int)
            
            # Yıl ve Ay'ı birleştirip gün olarak 1 veriyoruz (Örn: 2025-01-01)
            df['Tarih'] = pd.to_datetime(df[col_yil].astype(str) + '-' + df['Ay_Num'].astype(str) + '-01')
            
        except Exception as e:
            st.warning(f"Tarih oluşturulurken hata oluştu: {e}")

    # Tarih sütunu varsa datetime formatına zorla
    if 'Tarih' in df.columns:
        df['Tarih'] = pd.to_datetime(df['Tarih'], errors='coerce')
        
    return df

@st.cache_data
def create_sample_data():
    """Dosya yoksa hatasız örnek veri oluşturur"""
    dates = pd.date_range(start='2024-01-01', end='2025-12-31', freq='D')
    n = len(dates)
    
    # Dizileri eşit uzunlukta kesiyoruz (Hata önleyici)
    hesaplar = (['HomeByHome', 'CarpetSale24'] * n)[:n]
    satislar = ([5, 10, 2, 8, 15, 3] * n)[:n]
    cirolar = ([500, 1000, 200, 800, 1500, 300] * n)[:n]

    return pd.DataFrame({
        'Tarih': dates,
        'Hesap': hesaplar,
        'Satis_Adedi': satislar,
        'Ciro': cirolar
    })

# ---------------------------------------------------------
# 2. SIDEBAR - YÖNETİM PANELİ
# ---------------------------------------------------------
st.sidebar.title("🎛️ Yönetim Paneli")

# A. Dosya Yükleme
uploaded_file = st.sidebar.file_uploader("Excel veya CSV Yükle", type=["xlsx", "xls", "csv"])

# B. Sıfırlama Butonu
if st.sidebar.button("⚠️ Veritabanını Sıfırla / Temizle"):
    st.cache_data.clear()
    st.toast("Veri önbelleği temizlendi!", icon="🧹")
    st.rerun()

st.sidebar.divider()

# C. Veri Yükleme Kontrolü
try:
    if uploaded_file:
        df = load_data(uploaded_file)
        st.sidebar.success("✅ Dosya Yüklendi")
    else:
        df = create_sample_data()
        st.sidebar.info("ℹ️ Demo Modu (Örnek Veri)")

    # Zorunlu Sütun Kontrolü
    required = ['Tarih', 'Hesap', 'Ciro', 'Satis_Adedi']
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        st.error(f"❌ Hata: Dosyanızda şu sütunlar bulunamadı veya oluşturulamadı: {missing}")
        st.warning(f"Dosyanızdaki sütunlar: {list(df.columns)}")
        st.stop()
        
except Exception as e:
    st.error(f"Bir hata oluştu: {e}")
    st.stop()

# D. Filtreleme Seçenekleri
hesap_listesi = ["Tümü"] + sorted(list(df['Hesap'].unique()))
hesap_secimi = st.sidebar.selectbox("Hesap Seçin:", hesap_listesi)

secilen_tarih = st.sidebar.date_input("Analiz Tarihi", value=pd.to_datetime("2025-01-01"))

# ---------------------------------------------------------
# 3. ANALİZ MOTORU VE KPI HESAPLAMALARI
# ---------------------------------------------------------

# Veriyi Hesaba Göre Filtrele
if hesap_secimi != "Tümü":
    df_filtered = df[df['Hesap'] == hesap_secimi]
else:
    df_filtered = df.copy()

def get_metrics(dataframe, target_date):
    """Seçilen aya göre Geçen Ay ve Geçen Yıl verilerini hesaplar"""
    t_date = pd.to_datetime(target_date)
    
    # Dönem: Bu Ay
    curr_start = t_date.replace(day=1)
    curr_end = (curr_start + pd.DateOffset(months=1)) - timedelta(days=1)
    
    # Dönem: Geçen Ay
    prev_m_end = curr_start - timedelta(days=1)
    prev_m_start = prev_m_end.replace(day=1)
    
    # Dönem: Geçen Yıl Aynı Ay
    prev_y_start = curr_start - pd.DateOffset(years=1)
    prev_y_end = curr_end - pd.DateOffset(years=1)

    # Verileri Süz
    curr_df = dataframe[(dataframe['Tarih'] >= curr_start) & (dataframe['Tarih'] <= curr_end)]
    prev_m_df = dataframe[(dataframe['Tarih'] >= prev_m_start) & (dataframe['Tarih'] <= prev_m_end)]
    prev_y_df = dataframe[(dataframe['Tarih'] >= prev_y_start) & (dataframe['Tarih'] <= prev_y_end)]

    return {
        "cur_ciro": curr_df['Ciro'].sum(),
        "prev_m_ciro": prev_m_df['Ciro'].sum(),
        "prev_y_ciro": prev_y_df['Ciro'].sum(),
        "cur_adet": curr_df['Satis_Adedi'].sum(),
        "label": curr_start.strftime("%B %Y")
    }

metrics = get_metrics(df_filtered, secilen_tarih)

# ---------------------------------------------------------
# 4. GÖRSELLEŞTİRME VE EKRAN ÇIKTISI
# ---------------------------------------------------------
st.title(f"📊 Satış Analizi: {hesap_secimi}")
st.markdown(f"### 📅 Dönem: {metrics['label']}")

# Karşılaştırma Seçeneği
karsilastir = st.checkbox("🔄 Karşılaştırmalı Analizi Göster", value=True)

if karsilastir:
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    # Farklar
    fark_ay = metrics['cur_ciro'] - metrics['prev_m_ciro']
    fark_yil = metrics['cur_ciro'] - metrics['prev_y_ciro']
    
    with col1:
        st.metric("Mevcut Ciro", f"{metrics['cur_ciro']:,.2f} TL", "Güncel")
    with col2:
        st.metric("Geçen Ay", f"{metrics['prev_m_ciro']:,.2f} TL", f"{fark_ay:,.2f} TL")
    with col3:
        st.metric("Geçen Yıl Aynı Ay", f"{metrics['prev_y_ciro']:,.2f} TL", f"{fark_yil:,.2f} TL")
    
    st.info(f"📦 Bu dönemde toplam **{metrics['cur_adet']}** adet satış işlemi gerçekleşmiştir.")
    
    # Grafik
    st.subheader("📈 Dönemsel Ciro Grafiği")
    chart_data = pd.DataFrame({
        'Dönem': ['Geçen Yıl', 'Geçen Ay', 'Bu Ay'],
        'Ciro': [metrics['prev_y_ciro'], metrics['prev_m_ciro'], metrics['cur_ciro']]
    })
    
    fig = px.bar(
        chart_data, x='Dönem', y='Ciro', text='Ciro', color='Dönem',
        color_discrete_sequence=['#ff9f43', '#54a0ff', '#1dd1a1']
    )
    fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

else:
    st.subheader("📋 Veri Listesi (Son 15 İşlem)")
    st.dataframe(df_filtered.tail(15), use_container_width=True)
