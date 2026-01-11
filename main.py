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

# MANUEL YIL SEÇİMİ
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
    idx_ulke = 0
    
    for i, c in enumerate(cols):
        c_low = c.lower()
        # Ciro Tahminleri
        if (str(rapor_yili) in c) or (rapor_ayi.lower() in c_low and str(karsilastirma_yili) not in c):
            if 'ciro' in c_low or 'tutar' in c_low: idx_current = i
        if (str(karsilastirma_yili) in c) or ('geçen' in c_low) or ('2024' in c):
            if 'ciro' in c_low or 'tutar' in c_low: idx_prev = i
        
        # Hesap ve Ülke Tahminleri
        if any(x in c_low for x in ['hesap', 'account', 'mağaza', 'firma']): idx_hesap = i
        if any(x in c_low for x in ['ülke', 'country', 'region', 'bölge']): idx_ulke = i

    # --- KULLANICI SEÇİMİ (EŞLEŞTİRME) ---
    st.sidebar.subheader("3. Sütun Eşleştirme")
    col_hesap = st.sidebar.selectbox("Firma/Hesap Sütunu", cols, index=idx_hesap)
    col_ulke = st.sidebar.selectbox("Ülke Sütunu", cols, index=idx_ulke) # Yeni Eklendi
    
    col_ciro_guncel = st.sidebar.selectbox(f"📅 {rapor_yili} Ciro Sütunu", cols, index=idx_current)
    col_ciro_gecen = st.sidebar.selectbox(f"⏮️ {karsilastirma_yili} Ciro Sütunu", cols, index=idx_prev)

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
# 4. ÇİFT KATMANLI FİLTRELEME
# ---------------------------------------------------------
st.sidebar.divider()
st.sidebar.subheader("4. Filtreleme Seçenekleri")

# --- HESAP LİSTESİ ---
try:
    unique_accounts = sorted(df[col_hesap].dropna().astype(str).unique())
    hesap_listesi = ["Tümü"] + unique_accounts
except:
    hesap_listesi = ["Tümü"]

# --- ÜLKE LİSTESİ (Yeni) ---
try:
    unique_countries = sorted(df[col_ulke].dropna().astype(str).unique())
    ulke_listesi = ["Tümü"] + unique_countries
except:
    ulke_listesi = ["Tümü"]

# Seçim Kutuları
secilen_hesap = st.sidebar.selectbox("Hesap Seç:", hesap_listesi)
secilen_ulke = st.sidebar.selectbox("Ülke Seç:", ulke_listesi)

# --- FİLTRELEME MANTIĞI ---
df_filtered = df.copy()

# 1. Hesap Filtresi Uygula
if secilen_hesap != "Tümü":
    df_filtered = df_filtered[df_filtered[col_hesap].astype(str) == secilen_hesap]

# 2. Ülke Filtresi Uygula (Mevcut filtrelenmiş veri üzerinden devam eder)
if secilen_ulke != "Tümü":
    df_filtered = df_filtered[df_filtered[col_ulke].astype(str) == secilen_ulke]


# KPI Hesaplamaları
toplam_guncel = df_filtered[col_ciro_guncel].sum()
toplam_gecen = df_filtered[col_ciro_gecen].sum()
fark = toplam_guncel - toplam_gecen
degisim = (fark / toplam_gecen * 100) if toplam_gecen > 0 else 0

# ---------------------------------------------------------
# 5. GÖRSELLEŞTİRME
# ---------------------------------------------------------
baslik_text = f"{rapor_yili} vs {karsilastirma_yili} Satış Karşılaştırması"
filtre_ozeti = f"Hesap: {secilen_hesap} | Ülke: {secilen_ulke}"

st.title(f"📊 {baslik_text}")
st.markdown(f"**Dönem:** {rapor_ayi} | **{filtre_ozeti}**")

# Metrik Kartları
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(f"{rapor_yili} Ciro", f"{toplam_guncel:,.0f} TL", f"{degisim:.1f}%")
with col2:
    st.metric(f"{karsilastirma_yili} Ciro", f"{toplam_gecen:,.0f} TL", f"{fark:,.0f} TL", delta_color="normal")
with col3:
    if not df_filtered.empty:
        # Filtreye göre en iyiyi dinamik belirle
        group_col = col_hesap if secilen_hesap == "Tümü" else col_ulke
        
        # Eğer hem hesap hem ülke seçiliyse tek satır kalır, gruplamaya gerek kalmaz
        if secilen_hesap != "Tümü" and secilen_ulke != "Tümü":
             st.metric("Durum", "Tek Kayıt Görüntüleniyor")
        else:
            try:
                df_grp = df_filtered.groupby(group_col)[col_ciro_guncel].sum()
                if not df_grp.empty:
                    best = df_grp.idxmax()
                    st.metric("Lider (Seçime Göre)", str(best))
            except:
                st.metric("Durum", "-")
    else:
        st.metric("Durum", "Veri Yok")

st.divider()

# Grafikler
if not df_filtered.empty:
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
        # Eğer Hesap seçili değilse Hesaba göre pasta grafik
        # Eğer Hesap seçili ama Ülke seçili değilse Ülkeye göre pasta grafik
        if secilen_hesap == "Tümü":
            st.subheader("🏆 Mağaza Bazlı Dağılım")
            pie_col = col_hesap
        elif secilen_ulke == "Tümü":
            st.subheader("🌍 Ülke Bazlı Dağılım")
            pie_col = col_ulke
        else:
            pie_col = None # İkisi de seçiliyse pasta grafiğe gerek yok
            
        if pie_col:
            pie_data = df_filtered[df_filtered[col_ciro_guncel] > 0]
            fig2 = px.pie(pie_data, values=col_ciro_guncel, names=pie_col, hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)

    # Detay Tablo
    st.subheader("📋 Detaylı Veri")
    st.dataframe(df_filtered[[col_hesap, col_ulke, col_ciro_gecen, col_ciro_guncel]], use_container_width=True)

else:
    st.warning("⚠️ Seçilen filtrelere uygun veri bulunamadı.")
