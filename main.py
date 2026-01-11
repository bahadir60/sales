import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Satış Performans Raporu", layout="wide")

# ---------------------------------------------------------
# 1. VERİ YÜKLEME VE TEMİZLEME
# ---------------------------------------------------------
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # Boşlukları temizle
    df.columns = df.columns.str.strip()
    
    # Unnamed (isimsiz) boş sütunları sil
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    return df

# Sayısal veriye çevirme fonksiyonu (TL simgesi veya virgül hatalarını düzeltir)
def clean_currency(x):
    if isinstance(x, str):
        # TL, boşluk ve harfleri temizle
        clean_str = x.replace('TL', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(clean_str)
        except:
            return 0.0
    return x

# ---------------------------------------------------------
# 2. SIDEBAR - DOSYA VE EŞLEŞTİRME
# ---------------------------------------------------------
st.sidebar.title("🎛️ Rapor Ayarları")

uploaded_file = st.sidebar.file_uploader("Excel Dosyanızı Yükleyin", type=["xlsx", "xls", "csv"])

if st.sidebar.button("⚠️ Sıfırla"):
    st.cache_data.clear()
    st.rerun()

# --- VERİ YÜKLEME KONTROLÜ ---
if uploaded_file:
    try:
        df = load_data(uploaded_file)
        st.sidebar.success("✅ Dosya Okundu")
    except Exception as e:
        st.error(f"Dosya okunamadı: {e}")
        st.stop()
else:
    # Dosya yoksa demo verisi oluşturmuyoruz, kullanıcıdan dosya bekliyoruz
    st.info("Lütfen sol menüden Excel dosyanızı yükleyiniz.")
    st.stop()

st.sidebar.divider()
st.sidebar.subheader("Sütun Eşleştirme")
st.sidebar.info("Excel'inizdeki sütun isimlerini aşağıdan seçiniz:")

# --- KOLON SEÇİMLERİ (Sizin Data Yapınıza Göre) ---
# Otomatik seçmesi için varsayılan değerleri tahmin etmeye çalışıyoruz
all_columns = df.columns.tolist()

# 1. Bu Ayın Cirosu (Örn: 1-31 Ocak Ciro)
index_ciro_guncel = next((i for i, c in enumerate(all_columns) if 'Ciro' in c and '2024' not in c and 'artışı' not in c), 0)
col_ciro_guncel = st.sidebar.selectbox("📅 BU YIL CİRO Sütunu Hangisi?", all_columns, index=index_ciro_guncel)

# 2. Geçen Yıl Cirosu (Örn: 2024 Ciro)
index_ciro_gecen = next((i for i, c in enumerate(all_columns) if '2024 Ciro' in c), 0)
col_ciro_gecen = st.sidebar.selectbox("⏮️ GEÇEN YIL CİRO Sütunu Hangisi?", all_columns, index=index_ciro_gecen)

# 3. Sipariş Adedi (Örn: 1-31 Ocak Total Order)
index_order = next((i for i, c in enumerate(all_columns) if 'Total Order' in c and '.1' not in c), 0)
col_order = st.sidebar.selectbox("📦 SİPARİŞ ADEDİ Sütunu Hangisi?", all_columns, index=index_order)

# 4. Hesap Sütunu
index_hesap = next((i for i, c in enumerate(all_columns) if 'Hesap' in c or 'Account' in c), 0)
col_hesap = st.sidebar.selectbox("👤 HESAP İSMİ Sütunu Hangisi?", all_columns, index=index_hesap)

# Verileri Sayısal Formata Çevir (Garantiye al)
df[col_ciro_guncel] = pd.to_numeric(df[col_ciro_guncel].apply(clean_currency), errors='coerce').fillna(0)
df[col_ciro_gecen] = pd.to_numeric(df[col_ciro_gecen].apply(clean_currency), errors='coerce').fillna(0)
df[col_order] = pd.to_numeric(df[col_order], errors='coerce').fillna(0)

# ---------------------------------------------------------
# 3. HESAP FİLTRELEME
# ---------------------------------------------------------
st.sidebar.divider()
hesaplar = ["Tümü"] + list(df[col_hesap].unique())
secilen_hesap = st.sidebar.selectbox("Hesap Filtrele:", hesaplar)

if secilen_hesap != "Tümü":
    df_analiz = df[df[col_hesap] == secilen_hesap]
else:
    df_analiz = df.copy()

# ---------------------------------------------------------
# 4. ANALİZ VE GÖRSELLEŞTİRME
# ---------------------------------------------------------
st.title(f"📊 Performans Raporu: {secilen_hesap}")

# Toplamları Hesapla
toplam_ciro_guncel = df_analiz[col_ciro_guncel].sum()
toplam_ciro_gecen = df_analiz[col_ciro_gecen].sum()
toplam_order = df_analiz[col_order].sum()

fark_tl = toplam_ciro_guncel - toplam_ciro_gecen
degisim_yuzde = ((toplam_ciro_guncel - toplam_ciro_gecen) / toplam_ciro_gecen * 100) if toplam_ciro_gecen != 0 else 0

# --- KPI KARTLARI ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label=f"Bu Dönem Ciro ({col_ciro_guncel})",
        value=f"{toplam_ciro_guncel:,.0f} TL",
        delta=f"{degisim_yuzde:.1f}%"
    )

with col2:
    st.metric(
        label=f"Geçen Yıl Aynı Dönem ({col_ciro_gecen})",
        value=f"{toplam_ciro_gecen:,.0f} TL",
        delta=f"{fark_tl:,.0f} TL Fark",
        delta_color="normal"
    )

with col3:
    st.metric(
        label="Toplam Sipariş (Order)",
        value=f"{toplam_order:,.0f} Adet",
        delta="Bu Ay"
    )

# --- GRAFİKSEL KARŞILAŞTIRMA ---
st.divider()
st.subheader("📈 Karşılaştırmalı Analiz")

chart_data = pd.DataFrame({
    'Dönem': ['Geçen Yıl', 'Bu Yıl'],
    'Ciro': [toplam_ciro_gecen, toplam_ciro_guncel]
})

fig = px.bar(chart_data, x='Dönem', y='Ciro', text='Ciro', 
             color='Dönem', color_discrete_sequence=['#bdc3c7', '#2ecc71'])
fig.update_traces(texttemplate='%{text:,.0f} TL', textposition='outside')
st.plotly_chart(fig, use_container_width=True)

# --- DETAYLI TABLO ---
st.subheader("📋 Detaylı Veri Listesi")
# Sadece önemli sütunları gösterelim
gosterilecek_kolonlar = [col_hesap, 'Ülke', col_ciro_guncel, col_ciro_gecen, col_order]
# Eğer tabloda 'Reklam Harcaması' varsa onu da ekleyelim
if 'Reklam Harcaması' in df.columns:
    gosterilecek_kolonlar.append('Reklam Harcaması')

st.dataframe(df_analiz[gosterilecek_kolonlar], use_container_width=True)
