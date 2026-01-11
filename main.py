import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dönemsel Satış Analizi", layout="wide")

# ---------------------------------------------------------
# 1. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------
@st.cache_data
def load_data(uploaded_file):
    """Excel veya CSV dosyasını okur ve temizler."""
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # Sütun başlıklarındaki boşlukları temizle
    df.columns = df.columns.str.strip()
    
    # "Unnamed" gibi boş sütunları at
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    return df

def clean_currency(x):
    """Excel'den gelen '1.250 TL' gibi metinleri sayıya çevirir."""
    if isinstance(x, str):
        # TL, boşluk ve noktaları temizle, virgülü noktaya çevir
        clean_str = x.replace('TL', '').replace('₺', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(clean_str)
        except:
            return 0.0
    return x

# ---------------------------------------------------------
# 2. SIDEBAR: MANUEL DÖNEM VE DOSYA AYARLARI
# ---------------------------------------------------------
st.sidebar.title("🎛️ Rapor Ayarları")

st.sidebar.subheader("1. Rapor Dönemi (Manuel)")
# 2026 yılındayız ama 2025 verisini işliyor olabiliriz.
rapor_yili = st.sidebar.number_input("Raporlanacak Yıl (Ana Veri)", min_value=2020, max_value=2030, value=2025)
karsilastirma_yili = rapor_yili - 1  # Otomatik olarak bir önceki yıl (Örn: 2024)

aylar_listesi = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", 
                 "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık", "Tümü"]
rapor_ayi = st.sidebar.selectbox("Raporlanan Ay", aylar_listesi, index=0)

st.sidebar.info(f"📌 Analiz: **{rapor_yili}** vs **{karsilastirma_yili}** ({rapor_ayi})")

st.sidebar.divider()

# Dosya Yükleme
uploaded_file = st.sidebar.file_uploader("2. Excel Dosyasını Yükle", type=["xlsx", "xls", "csv"])

if st.sidebar.button("⚠️ Ayarları Sıfırla"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------
# 3. VERİ İŞLEME VE SÜTUN EŞLEŞTİRME
# ---------------------------------------------------------
if uploaded_file:
    try:
        df = load_data(uploaded_file)
        st.sidebar.success("✅ Dosya Yüklendi")
        
        cols = df.columns.tolist()
        
        # --- AKILLI SÜTUN TAHMİN MEKANİZMASI ---
        # 1. Mevcut Yıl Cirosunu Bulmaya Çalış (Örn: "2025", "Ocak Ciro", "Bu Yıl")
        idx_current = 0
        for i, c in enumerate(cols):
            c_low = c.lower()
            # Eğer seçilen ay isminde geçiyorsa ve "2024" (önceki yıl) yazmıyorsa
            if (str(rapor_yili) in c) or (rapor_ayi.lower() in c_low and str(karsilastirma_yili) not in c):
                if 'ciro' in c_low or 'tutar' in c_low:
                    idx_current = i
                    break
        
        # 2. Geçen Yıl Cirosunu Bulmaya Çalış (Örn: "2024", "Geçen Yıl")
        idx_prev = 0
        for i, c in enumerate(cols):
            c_low = c.lower()
            # "2024" geçiyorsa veya "geçen yıl" diyorsa
            if (str(karsilastirma_yili) in c) or ('geçen' in c_low) or ('2024' in c):
                if 'ciro' in c_low or 'tutar' in c_low:
                    idx_prev = i
                    break
        
        # 3. Hesap/Mağaza Sütununu Bul
        idx_hesap = 0
        for i, c in enumerate(cols):
            if any(x in c.lower() for x in ['hesap', 'account', 'mağaza', 'store', 'firma']):
                idx_hesap = i
                break

        # --- KULLANICIYA ONAYLATMA ---
        st.sidebar.subheader("3. Sütun Eşleştirme")
        col_hesap = st.sidebar.selectbox("Firma/Hesap Sütunu", cols, index=idx_hesap)
        
        col_ciro_guncel = st.sidebar.selectbox(
            f"📅 {rapor_yili} Ciro Sütunu (Seçilen Ay)", 
            cols, 
            index=idx_current,
            help="Bu yıla ait ciro verisi"
        )
        
        col_ciro_gecen = st.sidebar.selectbox(
            f"⏮️ {karsilastirma_yili} Ciro Sütunu (Geçen Yıl)", 
            cols, 
            index=idx_prev,
            help="Karşılaştırma yapılacak geçen yıl verisi"
        )

        # Veri Temizliği (TL ikonlarını sil, sayıya çevir)
        df[col_ciro_guncel] = pd.to_numeric(df[col_ciro_guncel].apply(clean_currency), errors='coerce').fillna(0)
        df[col_ciro_gecen] = pd.to_numeric(df[col_ciro_gecen].apply(clean_currency), errors='coerce').fillna(0)

    except Exception as e:
        st.error(f"Veri işlenirken hata: {e}")
        st.stop()
else:
    st.info("👋 Lütfen sol menüden Excel dosyanızı yükleyiniz.")
    st.stop()

# ---------------------------------------------------------
# 4. FİLTRELEME VE ANALİZ
# ---------------------------------------------------------

# Hesap Filtresi
hesap_listesi = ["Tümü"] + sorted(list(df[col_hesap].unique()))
secilen_hesap = st.sidebar.selectbox("4. Hesap Filtrele", hesap_listesi)

if secilen_hesap != "Tümü":
    df_filtered = df[df[col_hesap] == secilen_hesap]
else:
    df_filtered = df.copy()

# KPI Hesaplamaları
toplam_guncel = df_filtered[col_ciro_guncel].sum()
toplam_gecen = df_filtered[col_ciro_gecen].sum()
fark = toplam_guncel - toplam_gecen
degisim = (fark / toplam_gecen * 100) if toplam_gecen > 0 else 0

# ---------------------------------------------------------
# 5. GÖRSELLEŞTİRME
# ---------------------------------------------------------
st.title(f"📊 {rapor_yili} vs {karsilastirma_yili} Satış Karşılaştırması")
st.markdown(f"**Dönem:** {rapor_ayi} | **Filtre:** {secilen_hesap}")

# Metrik Kartları
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label=f"{rapor_yili} Toplam Ciro",
        value=f"{toplam_guncel:,.0f} TL",
        delta=f"{degisim:.1f}% (Yıllık Değişim)"
    )

with col2:
    st.metric(
        label=f"{karsilastirma_yili} Toplam Ciro",
        value=f"{toplam_gecen:,.0f} TL",
        delta=f"{fark:,.0f} TL (Net Fark)",
        delta_color="normal"
    )

with col3:
    if secilen_hesap == "Tümü":
        en_iyi_hesap = df_filtered.set_index(col_hesap)[col_ciro_guncel].idxmax()
        st.metric(label="En İyi Performans", value=en_iyi_hesap)
    else:
        st.metric(label="Durum", value="Veri Analizi", delta="Aktif")

st.divider()

# Grafik Alanı
col_grafik1, col_grafik2 = st.columns([2, 1])

with col_grafik1:
    st.subheader("📈 Genel Karşılaştırma")
    chart_data = pd.DataFrame({
        'Yıl': [str(karsilastirma_yili), str(rapor_yili)],
        'Ciro': [toplam_gecen, toplam_guncel]
    })
    
    fig = px.bar(chart_data, x='Yıl', y='Ciro', text='Ciro', 
                 color='Yıl', 
                 color_discrete_map={str(karsilastirma_yili): '#95a5a6', str(rapor_yili): '#27ae60'},
                 title=f"{rapor_ayi} Ayı Ciro Karşılaştırması")
    fig.update_traces(texttemplate='%{text:,.0f} TL', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

with col_grafik2:
    if secilen_hesap == "Tümü":
        st.subheader("🏆 Mağaza Bazlı Dağılım")
        fig2 = px.pie(df_filtered, values=col_ciro_guncel, names=col_hesap, hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

# Detay Tablo
st.subheader("📋 Detaylı Veri Tablosu")
st.dataframe(df_filtered[[col_hesap, col_ciro_gecen, col_ciro_guncel]], use_container_width=True)
