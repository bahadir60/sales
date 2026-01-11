import streamlit as st
import pandas as pd
from datetime import timedelta
import plotly.express as px

# ---------------------------------------------------------
# 1. VERİ YÜKLEME VE HAZIRLIK (Örnek Veri Seti)
# ---------------------------------------------------------
# Not: Gerçek projenizde burayı pd.read_excel veya pd.read_csv ile değiştirin.
@st.cache_data
def load_data():
    # ÖRNEK DATADIR - Kendi dosyanızla değiştirdiğinizde sütun isimlerine dikkat edin.
    data = {
        'Tarih': pd.date_range(start='2024-01-01', end='2025-12-31', freq='D'),
        'Hesap': ['HomeByHome', 'CarpetSale24'] * 365 + ['HomeByHome'], # 731 kayıt
        'Satis_Adedi': [5, 10, 2, 8, 15, 3] * 121 + [5], # Rastgele sayılar
        'Ciro': [500, 1000, 200, 800, 1500, 300] * 121 + [500]
    }
    df = pd.DataFrame(data)
    # Tarih sütununu datetime formatına çevirelim
    df['Tarih'] = pd.to_datetime(df['Tarih'])
    return df

df = load_data()

# ---------------------------------------------------------
# 2. SIDEBAR - FİLTRELEME ALANI
# ---------------------------------------------------------
st.sidebar.header("Filtreleme Seçenekleri")

# A) HESAP SEÇİMİ (İsteğiniz üzerine ayrıldı)
hesap_secimi = st.sidebar.selectbox(
    "Hesap Seçin:",
    ("Tümü", "HomeByHome", "CarpetSale24")
)

# Veriyi hesaba göre filtrele
if hesap_secimi != "Tümü":
    df_filtered = df[df['Hesap'] == hesap_secimi]
else:
    df_filtered = df.copy()

# B) TARİH SEÇİMİ (Analiz edilecek ay/yıl)
st.sidebar.write("---")
st.sidebar.subheader("Dönem Seçimi")
# Kullanıcıdan bir tarih alalım (Genelde raporlar aylık bakıldığı için ay sonunu seçtirmek mantıklıdır)
secilen_tarih = st.sidebar.date_input("Analiz Tarihi (Referans)", value=pd.to_datetime("2025-01-01"))

# ---------------------------------------------------------
# 3. ANA EKRAN VE KPI HESAPLAMALARI
# ---------------------------------------------------------
st.title(f"📊 Satış Analizi: {hesap_secimi}")

# Karşılaştırma Fonksiyonu
def get_metrics(dataframe, target_date):
    """
    Seçilen aya ait, bir önceki aya ait ve geçen yılın aynı ayına ait toplamları döndürür.
    """
    # Seçilen Ayın Başlangıcı ve Bitişi
    current_month_start = target_date.replace(day=1)
    # Bir sonraki ayın ilk gününden 1 çıkararak ay sonunu bulma (Basit yöntem)
    next_month = current_month_start.replace(day=28) + timedelta(days=4)
    current_month_end = next_month - timedelta(days=next_month.day)

    # 1. Mevcut Dönem Verisi
    current_data = dataframe[(dataframe['Tarih'] >= pd.to_datetime(current_month_start)) & 
                             (dataframe['Tarih'] <= pd.to_datetime(current_month_end))]
    
    # 2. Bir Önceki Ay (MoM)
    prev_month_end = current_month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    prev_month_data = dataframe[(dataframe['Tarih'] >= pd.to_datetime(prev_month_start)) & 
                                (dataframe['Tarih'] <= pd.to_datetime(prev_month_end))]

    # 3. Geçen Yıl Aynı Ay (YoY)
    prev_year_start = current_month_start.replace(year=current_month_start.year - 1)
    # Şubat ayı kontrolü (Artık yıl)
    try:
        prev_year_end = current_month_end.replace(year=current_month_end.year - 1)
    except ValueError:
        prev_year_end = current_month_end.replace(year=current_month_end.year - 1, day=28)
        
    prev_year_data = dataframe[(dataframe['Tarih'] >= pd.to_datetime(prev_year_start)) & 
                               (dataframe['Tarih'] <= pd.to_datetime(prev_year_end))]

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
# 4. "KARŞILAŞTIR" SEÇENEĞİ VE GÖSTERİM
# ---------------------------------------------------------

st.write(f"Seçilen Dönem: **{metrics['date_label']}**")

# Kullanıcı "Verileri Karşılaştır" onay kutusunu işaretlerse detayları göster
karsilastir_aktif = st.checkbox("🔄 Dönemleri Karşılaştır (Geçen Ay ve Geçen Yıl)")

if karsilastir_aktif:
    st.markdown("### Performans Karşılaştırması")
    
    col1, col2, col3 = st.columns(3)
    
    # Ciro Hesaplamaları
    ciro_fark_ay = metrics['current_sum'] - metrics['prev_month_sum']
    ciro_fark_yil = metrics['current_sum'] - metrics['prev_year_sum']
    
    with col1:
        st.metric(
            label="Mevcut Ciro", 
            value=f"{metrics['current_sum']:,.2f} TL",
            delta="Güncel Veri"
        )
        
    with col2:
        st.metric(
            label="Önceki Ay'a Göre", 
            value=f"{metrics['prev_month_sum']:,.2f} TL", 
            delta=f"{ciro_fark_ay:,.2f} TL",
            delta_color="normal" # Artış yeşil, azalış kırmızı olur otomatik
        )
        
    with col3:
        st.metric(
            label="Geçen Yıl Aynı Ay'a Göre", 
            value=f"{metrics['prev_year_sum']:,.2f} TL", 
            delta=f"{ciro_fark_yil:,.2f} TL",
            delta_color="normal"
        )
    
    st.info(f"💡 Not: Bu ay toplam **{metrics['current_count']}** adet satış yapılmıştır.")

    # Grafiksel Karşılaştırma
    st.subheader("Grafiksel Görünüm")
    comp_df = pd.DataFrame({
        'Dönem': ['Geçen Yıl Aynı Ay', 'Geçen Ay', 'Bu Ay'],
        'Ciro': [metrics['prev_year_sum'], metrics['prev_month_sum'], metrics['current_sum']]
    })
    
    fig = px.bar(comp_df, x='Dönem', y='Ciro', text='Ciro', 
                 title="Dönemsel Ciro Karşılaştırması", color='Dönem')
    fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

else:
    # Karşılaştırma kapalıysa sadece mevcut veriyi tablo olarak göster
    st.dataframe(df_filtered.tail(10)) # Son 10 veri
    st.write("Karşılaştırma detaylarını görmek için yukarıdaki kutucuğu işaretleyin.")
