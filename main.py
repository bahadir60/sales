import streamlit as st
import pandas as pd
from datetime import timedelta
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="Satış Analiz Paneli", layout="wide")

# ---------------------------------------------------------
# 1. VERİ YÜKLEME VE İŞLEME FONKSİYONLARI
# ---------------------------------------------------------

@st.cache_data
def load_data(uploaded_file):
    """
    Kullanıcı dosya yüklediğinde çalışır.
    """
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # Sütun isimlerini standartlaştıralım (Boşlukları temizle)
    df.columns = df.columns.str.strip()
    
    # Tarih sütununu datetime'a çevir
    # Not: Excel'de sütun adınızın 'Tarih' olduğundan emin olun.
    if 'Tarih' in df.columns:
        df['Tarih'] = pd.to_datetime(df['Tarih'])
    
    return df

@st.cache_data
def create_sample_data():
    """
    Dosya yüklenmediyse test amaçlı sanal veri üretir.
    """
    dates = pd.date_range(start='2024-01-01', end='2025-12-31', freq='D')
    n = len(dates)
    
    hesaplar = (['HomeByHome', 'CarpetSale24'] * n)[:n]
    satislar = ([5, 10, 2, 8, 15, 3] * n)[:n]
    cirolar = ([500, 1000, 200, 800, 1500, 300] * n)[:n]

    data = {
        'Tarih': dates,
        'Hesap': hesaplar,
        'Satis_Adedi': satislar,
        'Ciro': cirolar
    }
    return pd.DataFrame(data)

# ---------------------------------------------------------
# 2. SIDEBAR - YÖNETİM PANELİ
# ---------------------------------------------------------
st.sidebar.title("🎛️ Yönetim Paneli")

# A) DOSYA YÜKLEME ALANI
st.sidebar.subheader("1. Veri Kaynağı")
uploaded_file = st.sidebar.file_uploader("Excel veya CSV Yükle", type=["xlsx", "xls", "csv"])

# B) HESAP SEÇİMİ
st.sidebar.subheader("2. Filtreleme")
hesap_secimi = st.sidebar.selectbox(
    "Hesap Seçin:",
    ("Tümü", "HomeByHome", "CarpetSale24")
)

# C) TARİH SEÇİMİ
secilen_tarih = st.sidebar.date_input(
    "3. Analiz Tarihi (Referans)", 
    value=pd.to_datetime("2025-01-01")
)

# D) SIFIRLAMA BUTONU
st.sidebar.markdown("---")
if st.sidebar.button("⚠️ Veritabanını Sıfırla / Temizle"):
    st.cache_data.clear()
    st.toast("Önbellek temizlendi, sistem sıfırlandı!", icon="✅")
    st.rerun()

# ---------------------------------------------------------
# 3. VERİ AKIŞI KONTROLÜ
# ---------------------------------------------------------
try:
    if uploaded_file is not None:
        # Dosya yüklendiyse onu oku
        df = load_data(uploaded_file)
        st.success(f"✅ Dosya başarıyla yüklendi: {uploaded_file.name}")
    else:
        # Yüklenmediyse örnek veri kullan
        df = create_sample_data()
        st.info("ℹ️ Dosya yüklenmediği için **Örnek Veri (Demo Modu)** gösteriliyor.")

    # Gerekli sütun kontrolü
    required_cols = ['Tarih', 'Hesap', 'Ciro', 'Satis_Adedi']
    if not all(col in df.columns for col in required_cols):
        st.error(f"Hata: Yüklenen dosyada şu sütunlar mutlaka olmalı: {required_cols}")
        st.stop()

except Exception as e:
    st.error(f"Veri okunurken bir hata oluştu: {e}")
    st.stop()

# ---------------------------------------------------------
# 4. FİLTRE
