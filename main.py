import streamlit as st
import pandas as pd
from datetime import timedelta
import plotly.express as px

# ---------------------------------------------------------
# 1. VERİ YÜKLEME VE DATABASE SİMÜLASYONU
# ---------------------------------------------------------
@st.cache_data
def load_data():
    """
    Sanal veri seti oluşturur. 
    Gerçek projede burası: pd.read_excel('dosya.xlsx') olacaktır.
    """
    # Tarih aralığını oluştur (2 Yıllık Veri)
    dates = pd.date_range(start='2024-01-01', end='2025-12-31', freq='D')
    n = len(dates) # Toplam gün sayısı

    # Dizi uzunluğu hatasını önlemek için listeleri 'n' uzunluğunda kesiyoruz
    hesaplar = (['HomeByHome', 'CarpetSale24'] * n)[:n]
    satislar = ([5, 10, 2, 8, 15, 3] * n)[:n]
    cirolar = ([500, 1000, 200, 800, 1500, 300] * n)[:n]

    data = {
        'Tarih': dates,
        'Hesap': hesaplar,
        'Satis_Adedi': satislar,
        'Ciro': cirolar
    }
    
    df = pd.DataFrame(data)
    return df

# Veriyi yükle
try:
    df = load_data()
except Exception as e:
    st.error(f"Veri yüklenirken hata oluştu: {e}")
    st.stop()

# ---------------------------------------------------------
# 2. SIDEBAR (FİLTRELER VE AYARLAR)
# ---------------------------------------------------------
st.sidebar.title("Yönetim Paneli")

# A) HESAP SEÇİMİ
st.sidebar.subheader("Filtreleme")
hesap_secimi = st.sidebar.selectbox(
    "Hesap Seçin:",
    ("Tümü", "HomeByHome", "CarpetSale24")
)

# B) TARİH SEÇİMİ
secilen_tarih = st.sidebar.date_input(
    "Analiz Tarihi (Referans)", 
    value=pd.to_datetime("2025-01-01")
)

# C) DATABASE SIFIRLAMA (YENİ ÖZELLİK)
st.sidebar.markdown("---")
st.sidebar.subheader("Sistem Ayarları")

if st.sidebar.button("⚠️ Veritabanını Sıfırla / Yenile"):
    # Streamlit'in hafızasındaki veriyi temizler
    st.cache_data.clear()
    st.toast("Veritabanı önbelleği temizlendi ve veriler sıfırlandı!", icon="✅")
    st.rerun() # Sayfayı yenile

# ---------------------------------------------------------
# 3. VERİ FİLTRELEME MANTIĞI
# ---------------------------------------------------------
if hesap_secimi != "Tümü":
    df_filtered = df[df['Hesap'] == hesap_secimi]
else:
    df_filtered = df.copy()

# ---------------------------------------------------------
# 4. KPI HESAPLAMA FONKSİYONU (GEÇMİŞ DÖNEMLER)
# ---------------------------------------------------------
def get_metrics(dataframe, target_date):
    # Tarih formatını garantiye al
    target_date = pd.to_datetime(target_date)
    
    # Seçilen Ayın Başlangıcı
    current_month_start = target_date.replace(day=1)
    
    # Seçilen Ayın Bitişi
    next_month = (current_month_start + pd.DateOffset(months=1))
    current_month_end = next_month - timedelta(days=1)

    # 1. Mevcut Dönem (Current)
    current_data = dataframe[(dataframe['Tarih'] >= current_month_start) & 
                             (dataframe['Tarih'] <= current_month_end)]
    
    # 2. Bir Önceki Ay (Month-over-Month)
    prev_month_end = current_month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    prev_month_data = dataframe[(dataframe['Tarih'] >= prev_month_start) & 
                                (dataframe['Tarih'] <= prev_month_end)]

    # 3. Geçen Yıl Aynı Ay (Year-over-Year)
    prev_year_start = current_month_start - pd.DateOffset(years=1)
    prev_year_end = current_month_end - pd.DateOffset(years=1)
    prev_year_data = dataframe[(dataframe['Tarih'] >= prev_year_start) & 
                               (dataframe['Tarih'] <= prev_year_end)]

    return {
        "current_sum": current_data['Ciro'].sum(),
        "prev_month_sum": prev_month_data['Ciro'].sum(),
        "prev_year_sum": prev_year_data['Ciro'].sum(),
        "current_count": current_data['Satis_Adedi'].sum(),
        "date_label": current_month_start.strftime("%B %Y")
    }

# Metrikleri Hesapla
metrics = get_metrics(df_filtered, secilen_tarih)

# ---------------------------------------------------------
# 5. ARAYÜZ GÖSTERİMİ
# ---------------------------------------------------------
st.title(f"📊 Satış Analizi: {hesap_secimi}")
st.markdown(f"**Seçilen Dönem:** {metrics['date_label']}")

# Karşılaştırma Seçeneği
karsilastir_aktif = st.checkbox("🔄 Dönemleri Karşılaştır (Geçen Ay ve Geçen Yıl)")

if karsilastir_aktif:
    st.divider()
    st.subheader("Performans Karşılaştırması")
    
    col1, col2, col3 = st.columns(3)
    
    # Farklar
    fark_ay = metrics['current_sum'] - metrics['prev_month_sum']
    fark_yil = metrics['current_sum'] - metrics['prev_year_sum']
    
    with col1:
        st.metric(
            label="Mevcut Ay Ciro", 
            value=f"{metrics['current_sum']:,.2f} TL",
            delta="Güncel"
        )
        
    with col2:
        st.metric(
            label="Geçen Ay'a Göre", 
            value=f"{metrics['prev_month_sum']:,.2f} TL", 
            delta=f"{fark_ay:,.2f} TL",
            delta_color="normal"
        )
        
    with col3:
        st.metric(
            label="Geçen Yıl Aynı Ay'a Göre", 
            value=f"{metrics['prev_year_sum']:,.2f} TL", 
            delta=f"{fark_yil:,.2f} TL",
            delta_color="normal"
        )
    
    st.info(f"💡 Not: Bu ay toplam **{metrics['current_count']}** adet satış işlemi gerçekleşmiştir.")

    # Grafik
    st.subheader("Grafiksel Görünüm")
    comp_df = pd.DataFrame({
        'Dönem': ['Geçen Yıl Aynı Ay', 'Geçen Ay', 'Bu Ay'],
        'Ciro': [metrics['prev_year_sum'], metrics['prev_month_sum'], metrics['current_sum']]
    })
    
    fig = px.bar(comp_df, x='Dönem', y='Ciro', text='Ciro', 
                 title="Dönemsel Ciro Karşılaştırması", color='Dönem',
                 color_discrete_sequence=['#ff9f43', '#54a0ff', '#1dd1a1'])
    
    fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

else:
    # Özet Tablo
    st.subheader("Veri Önizleme (Son 10 Kayıt)")
    st.dataframe(df_filtered.tail(10), use_container_width=True)
    st.caption("Detaylı karşılaştırma görmek için yukarıdaki kutucuğu işaretleyiniz.")
