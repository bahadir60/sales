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
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Sütun başlıklarındaki boşlukları temizle
        df.columns = df.columns.str.strip()
        
        # "Unnamed" gibi boş sütunları at
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Tamamen boş satırları sil
        df.dropna(how='all', inplace=True)
        
        return df
    except Exception as e:
        return pd.DataFrame()

def clean_currency(x):
    """Excel'den gelen '1.250 TL' gibi metinleri sayıya çevirir."""
    if isinstance(x, str):
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

# MANUEL YIL SEÇİMİ (2026 yılındayken 2025 verisine bakmak için)
st.sidebar.subheader("1. Rapor Dönemi")
rapor_yili = st.sidebar.number_input("Raporlanacak Yıl (Ana Veri)", min_value=2020, max_value=2030, value=2025)
karsilastirma_yili = rapor_yili - 1 

aylar_listesi = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", 
                 "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık", "Tümü"]
rapor_ayi = st.sidebar.selectbox("Raporlanan Ay", aylar_listesi, index=0)

st.sidebar.info(f"📌 Analiz: **{rapor_yili}** vs **{karsilastirma_yili}** ({rapor_ayi})")
st.sidebar.divider()

# DOSYA YÜKLEME
uploaded_file = st.sidebar.file_uploader("2. Excel Dosyasını Yükle", type=["xlsx", "xls", "csv"])

if st.sidebar.button("⚠️ Ayarları Sıfırla"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------
# 3. VERİ İŞLEME VE SÜTUN EŞLEŞTİRME
# ---------------------------------------------------------
if uploaded_file:
    df = load_data(uploaded_file)
    
    if df.empty:
        st.error("Dosya boş veya okunamadı.")
        st.stop()
        
    st.sidebar.success("✅ Dosya Yüklendi")
    
    cols = df.columns.tolist()
    
    # --- OTOMATİK SÜTUN TAHMİNİ ---
    idx_current = 0
    idx_prev = 0
    idx_hesap = 0
    
    # Basit kelime eşleştirme mantığı
    for i, c in enumerate(cols):
        c_low = c.lower()
        # Bu yıl tahmini
        if (str(rapor_yili) in c) or (rapor_ayi.lower() in c_low and str(karsilastirma_yili) not in c):
            if 'ciro' in c_low or 'tutar' in c_low:
                idx_current = i
        # Geçen yıl tahmini
        if (str(karsilastirma_yili) in c) or ('geçen' in c_low) or ('2024' in c):
            if 'ciro' in c_low or 'tutar' in c_low:
                idx_prev = i
        # Hesap tahmini
        if any(x in c.lower() for x in ['hesap', 'account', 'mağaza', 'store', 'firma']):
            idx_hesap = i

    # --- KULLANICI SEÇİMİ ---
    st.sidebar.subheader("3. Sütun Eşleştirme")
    col_hesap = st.sidebar.selectbox("Firma/Hesap Sütunu", cols, index=idx_hesap)
    
    col_ciro_guncel = st.sidebar.selectbox(
        f"📅 {rapor_yili} Ciro Sütunu", 
        cols, 
        index=idx_current
    )
    
    col_ciro_gecen = st.sidebar.selectbox(
        f"⏮️ {karsilastirma_yili} Ciro Sütunu", 
        cols, 
        index=idx_prev
    )

    # Verileri sayıya çevirme
    try:
        df[col_ciro_guncel] = pd.to_numeric(df[col_ciro_guncel].apply(clean_currency), errors='coerce').fillna(0)
        df[col_ciro_gecen] = pd.to_numeric(df[col_ciro_gecen].apply(clean_currency), errors='coerce').fillna(0)
    except Exception as e:
        st.error(f"Veri dönüşüm hatası: {e}")

else:
    st.info("👋 Lütfen sol menüden Excel dosyanızı yükleyiniz.")
    st.stop()

# ---------------------------------------------------------
# 4. FİLTRELEME VE ANALİZ
# ---------------------------------------------------------

# --- HATA DÜZELTME NOKTASI BURASI ---
try:
    # 1. Boş (NaN) değerleri at
    # 2. Hepsini String (Yazı) formatına çevir (Sayılar '123' olur)
    # 3. Benzersizleri bul ve sırala
    unique_accounts = sorted(df[col_hesap].dropna().astype(str).unique())
    hesap_listesi = ["Tümü"] + unique_accounts
except Exception as e:
    st.error(f"Hesap listesi oluşturulurken hata: {e}")
    st.stop()

secilen_hesap = st.sidebar.selectbox("4. Hesap Filtrele", hesap_listesi)

if secilen_hesap != "Tümü":
    # Karşılaştırma yaparken de sütunu string'e çeviriyoruz
    df_filtered = df[df[col_hesap].astype(str) == secilen_hesap]
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
st.markdown(f"**Dönem:** {rapor_ayi} | **Seçilen Hesap:** {secilen_hesap}")

# Metrikler
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(f"{rapor_yili} Ciro", f"{toplam_guncel:,.0f} TL", f"{degisim:.1f}%")
with col2:
    st.metric(f"{karsilastirma_yili} Ciro", f"{toplam_gecen:,.0f} TL", f"{fark:,.0f} TL", delta_color="normal")
with col3:
    if secilen_hesap == "Tümü" and not df_filtered.empty:
        # En iyi hesabı bul
        df_grouped = df_filtered.groupby(col_hesap)[col_ciro_guncel].sum()
        if not df_grouped.empty:
            en_iyi = df_grouped.idxmax()
            st.metric("Lider Mağaza", str(en_iyi))
    else:
        st.metric("Durum", "Filtreli Görünüm")

st.divider()

# Grafikler
col_g1, col_g2 = st.columns([2, 1])

with col_g1:
    st.subheader("📈 Genel Karşılaştırma")
    chart_data = pd.DataFrame({
        'Yıl': [str(karsilastirma_yili), str(rapor_yili)],
        'Ciro': [toplam_gecen, toplam_guncel]
    })
    fig = px.bar(chart_data, x='Yıl', y='Ciro', text='Ciro', color='Yıl',
                 color_discrete_map={str(karsilastirma_yili): '#95a5a6', str(rapor_yili): '#27ae60'})
    fig.update_traces(texttemplate='%{text:,.0f} TL', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

with col_g2:
    if secilen_hesap == "Tümü" and not df_filtered.empty:
        st.subheader("🏆 Mağaza Payları")
        # Negatif değerleri filtreleyerek pasta grafik çiz
        pie_data = df_filtered[df_filtered[col_ciro_guncel] > 0]
        fig2 = px.pie(pie_data, values=col_ciro_guncel, names=col_hesap, hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

# Tablo
st.subheader("📋 Detaylı Veri")
if not df_filtered.empty:
    st.dataframe(df_filtered[[col_hesap, col_ciro_gecen, col_ciro_guncel]], use_container_width=True)
