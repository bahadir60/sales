import streamlit as st
import pandas as pd
import plotly.express as px
import io
import datetime

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Analiz Paneli", layout="wide", page_icon="📅")

# ---------------------------------------------------------
# 0. OTURUM (SESSION) YÖNETİMİ
# ---------------------------------------------------------
# Manuel girilen verileri hafızada tutmak için
if 'manual_data' not in st.session_state:
    # Sütun yapısı: Tarih, Hesap, Ülke, ve Metrikler
    st.session_state.manual_data = pd.DataFrame(
        columns=['Tarih', 'Hesap', 'Ülke', 'Satış', 'Order', 'Reklam Harcaması', 'Reklamlı Satış', 'TACOS']
    )

# ---------------------------------------------------------
# 1. TEMEL FONKSİYONLAR
# ---------------------------------------------------------
@st.cache_data
def load_data(uploaded_file):
    """Excel/CSV okur ve temizler"""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        df.columns = df.columns.str.strip()
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.dropna(how='all', inplace=True)
        return df
    except Exception as e:
        return pd.DataFrame()

def clean_currency(x):
    """Metin (1.200 TL, %15) -> Sayı (1200.0, 15.0) dönüşümü"""
    if isinstance(x, str):
        clean_str = x.replace('TL', '').replace('₺', '').replace('%', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(clean_str)
        except:
            return 0.0
    return x

def convert_df_to_excel(df):
    """İndirme işlemi için Excel motoru"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export = df.copy()
        # Tarihleri düzgün formatta Excel'e yaz
        if 'Tarih' in df_export.columns:
            df_export['Tarih'] = df_export['Tarih'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else '')
        df_export.to_excel(writer, index=False, sheet_name='Analiz_Raporu')
    return output.getvalue()

# ---------------------------------------------------------
# 2. SIDEBAR - TAKVİM VE AYARLAR
# ---------------------------------------------------------
st.sidebar.title("🎛️ Yönetim Paneli")

# A) TARİH ARALIĞI SEÇİMİ (TAKVİM)
st.sidebar.subheader("1. Analiz Dönemi")
today = datetime.date.today()
first_day = today.replace(day=1)

# Varsayılan: Bu ayın başından bugüne
tarih_araligi = st.sidebar.date_input(
    "Tarih Aralığı Seçiniz:",
    value=(first_day, today),
    format="DD.MM.YYYY"
)

# Tarih aralığı kontrolü (Başlangıç ve Bitiş seçildi mi?)
if isinstance(tarih_araligi, tuple) and len(tarih_araligi) == 2:
    start_date = pd.to_datetime(tarih_araligi[0])
    end_date = pd.to_datetime(tarih_araligi[1])
    st.sidebar.success(f"📅 {tarih_araligi[0].strftime('%d.%m')} - {tarih_araligi[1].strftime('%d.%m.%Y')}")
else:
    st.sidebar.warning("Lütfen takvimden bitiş tarihini de seçiniz.")
    st.stop() # Tarih tam seçilmeden kodun geri kalanı çalışmaz

st.sidebar.divider()

# B) DOSYA YÜKLEME
st.sidebar.subheader("2. Veri Kaynağı")
uploaded_file = st.sidebar.file_uploader("Excel Dosyası Yükle", type=["xlsx", "xls", "csv"])

# C) SIFIRLAMA BUTONU
if st.sidebar.button("⚠️ Verileri Sıfırla"):
    st.cache_data.clear()
    st.session_state.manual_data = pd.DataFrame(
        columns=['Tarih', 'Hesap', 'Ülke', 'Satış', 'Order', 'Reklam Harcaması', 'Reklamlı Satış', 'TACOS']
    )
    st.rerun()

# ---------------------------------------------------------
# 3. VERİ İŞLEME VE EŞLEŞTİRME (MAPPING)
# ---------------------------------------------------------
df_excel = pd.DataFrame()

if uploaded_file:
    df_temp = load_data(uploaded_file)
    cols = df_temp.columns.tolist()
    
    st.sidebar.divider()
    st.sidebar.info("Sütun Eşleştirme")
    
    # Otomatik kelime yakalayıcı
    def get_idx(keywords, columns):
        for i, c in enumerate(columns):
            if any(k in c.lower() for k in keywords): return i
        return 0

    # Kullanıcıya Sütunları Seçtir
    # En önemlisi TARİH sütunu
    c_date = st.sidebar.selectbox("📅 TARİH Sütunu", cols, index=get_idx(['tarih', 'date', 'zaman', 'gün'], cols))
    c_hesap = st.sidebar.selectbox("Hesap/Mağaza", cols, index=get_idx(['hesap', 'account', 'firma'], cols))
    c_ulke = st.sidebar.selectbox("Ülke", cols, index=get_idx(['ülke', 'country', 'region'], cols))
    c_ciro = st.sidebar.selectbox("Satış (Ciro)", cols, index=get_idx(['ciro', 'sales', 'tutar'], cols))
    c_order = st.sidebar.selectbox("Order (Adet)", cols, index=get_idx(['order', 'adet', 'qty'], cols))
    c_spend = st.sidebar.selectbox("Reklam Harcama", cols, index=get_idx(['spend', 'harcama', 'cost'], cols))
    c_adsales = st.sidebar.selectbox("Reklamlı Satış", cols, index=get_idx(['ad sales', 'reklam ciro'], cols))
    c_tacos = st.sidebar.selectbox("TACOS (%)", cols, index=get_idx(['tacos', 'acos'], cols))
    
    # Standartlaştırma
    rename_map = {
        c_date: 'Tarih', c_hesap: 'Hesap', c_ulke: 'Ülke', c_ciro: 'Satış',
        c_order: 'Order', c_spend: 'Reklam Harcaması', c_adsales: 'Reklamlı Satış', c_tacos: 'TACOS'
    }
    
    df_excel = df_temp.rename(columns=rename_map)[list(rename_map.values())].copy()
    
    # FORMATLAMA
    # 1. Tarihleri datetime objesine çevir
    df_excel['Tarih'] = pd.to_datetime(df_excel['Tarih'], errors='coerce')
    
    # 2. Sayıları temizle
    for col in ['Satış', 'Order', 'Reklam Harcaması', 'Reklamlı Satış', 'TACOS']:
        df_excel[col] = pd.to_numeric(df_excel[col].apply(clean_currency), errors='coerce').fillna(0)

# --- BİRLEŞTİRME (Excel + Manuel) ---
# Manuel verideki tarihleri de datetime yapalım
if not st.session_state.manual_data.empty:
    st.session_state.manual_data['Tarih'] = pd.to_datetime(st.session_state.manual_data['Tarih'])

if not df_excel.empty:
    df_final = pd.concat([df_excel, st.session_state.manual_data], ignore_index=True)
else:
    df_final = st.session_state.manual_data.copy()

# --- FİLTRELEME (Seçilen Tarih Aralığına Göre) ---
if not df_final.empty:
    # Tarihi bozuk olanları sil
    df_final = df_final.dropna(subset=['Tarih'])
    
    # Maskeleme (Start <= Tarih <= End)
    mask = (df_final['Tarih'] >= start_date) & (df_final['Tarih'] <= end_date)
    df_filtered = df_final.loc[mask]
else:
    df_filtered = pd.DataFrame()

# ---------------------------------------------------------
# 4. SEKME YAPISI
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Analiz Paneli", "📝 Manuel Veri Girişi", "💾 Rapor İndir"])

# ==========================================
# SEKME 1: ANALİZ PANELİ (DASHBOARD)
# ==========================================
with tab1:
    st.markdown(f"### 📈 Performans: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
    
    if df_filtered.empty:
        st.warning("Seçilen tarih aralığında gösterilecek veri bulunamadı.")
        st.info("💡 Sol menüden tarih aralığını genişletin veya 'Manuel Veri Girişi' sekmesinden veri ekleyin.")
    else:
        # FİLTRELER
        c1, c2 = st.columns(2)
        hesaplar = ["Tümü"] + sorted(df_filtered['Hesap'].astype(str).unique().tolist())
        ulkeler = ["Tümü"] + sorted(df_filtered['Ülke'].astype(str).unique().tolist())
        
        sel_hesap = c1.selectbox("Mağaza Filtrele:", hesaplar)
        sel_ulke = c2.selectbox("Ülke Filtrele:", ulkeler)
        
        # Datayı Süz
        df_viz = df_filtered.copy()
        if sel_hesap != "Tümü": df_viz = df_viz[df_viz['Hesap'].astype(str) == sel_hesap]
        if sel_ulke != "Tümü": df_viz = df_viz[df_viz['Ülke'].astype(str) == sel_ulke]
        
        st.divider()

        # KPI KARTLARI
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Toplam Satış", f"{df_viz['Satış'].sum():,.0f} TL")
        k2.metric("Toplam Order", f"{df_viz['Order'].sum():,.0f}")
        k3.metric("Reklam Harcama", f"{df_viz['Reklam Harcaması'].sum():,.0f} TL")
        k4.metric("Reklamlı Satış", f"{df_viz['Reklamlı Satış'].sum():,.0f} TL")
        k5.metric("Ort. TACOS", f"%{df_viz['TACOS'].mean():.1f}")
        
        st.divider()
        
        # GRAFİK ALANI
        col_set, col_chart = st.columns([1, 3])
        with col_set:
            st.markdown("**Grafik Ayarları**")
            secilen_metrikler = st.multiselect(
                "Gösterilecek Veriler:",
                ['Satış', 'Order', 'Reklam Harcaması', 'Reklamlı Satış', 'TACOS'],
                default=['Satış', 'Reklam Harcaması']
            )
            
            grafik_tipi = st.radio(
                "Grafik Türü:",
                ["Zaman Trendi (Çizgi)", "Toplam Karşılaştırma (Bar)"]
            )
        
        with col_chart:
            if secilen_metrikler:
                # 1. ZAMAN TRENDİ GRAFİĞİ
                if grafik_tipi == "Zaman Trendi (Çizgi)":
                    # Gün bazında topla
                    df_trend = df_viz.groupby('Tarih')[secilen_metrikler].sum().reset_index()
                    # TACOS ortalamasını düzelt
                    if 'TACOS' in secilen_metrikler:
                        df_trend['TACOS'] = df_viz.groupby('Tarih')['TACOS'].mean().reset_index()['TACOS']
                    
                    fig = px.line(df_trend, x='Tarih', y=secilen_metrikler, markers=True, title="Zaman İçindeki Değişim")
                
                # 2. KARŞILAŞTIRMA GRAFİĞİ (Bar)
                else:
                    # Grup belirle (Tek hesap seçiliyse ülkeye göre, değilse hesaba göre)
                    grp = 'Ülke' if sel_hesap != "Tümü" else 'Hesap'
                    
                    df_bar = df_viz.groupby(grp)[secilen_metrikler].sum().reset_index()
                    if 'TACOS' in secilen_metrikler:
                        df_bar['TACOS'] = df_viz.groupby(grp)['TACOS'].mean().reset_index()['TACOS']
                    
                    # Veriyi Plotly formatına çevir
                    df_melt = df_bar.melt(id_vars=grp, var_name='Veri', value_name='Değer')
                    
                    fig = px.bar(df_melt, x=grp, y='Değer', color='Veri', barmode='group', text_auto='.2s', title=f"{grp} Bazlı Toplamlar")
                
                st.plotly_chart(fig, use_container_width=True)

# ==========================================
# SEKME 2: MANUEL VERİ GİRİŞİ (TAKVİMLİ)
# ==========================================
with tab2:
    st.subheader("📝 Manuel Veri Girişi")
    st.caption("Excel'de olmayan verileri girmek için formu kullanın. 'İşlem Tarihi' seçimi önemlidir.")
    
    with st.form("entry_form"):
        # TARİH SEÇİMİ
        inp_date = st.date_input("İşlem Tarihi", value=datetime.date.today())
        
        c1, c2 = st.columns(2)
        inp_hesap = c1.text_input("Hesap Adı", value="HomeByHome")
        inp_ulke = c2.text_input("Ülke", value="Germany")
        
        c3, c4, c5 = st.columns(3)
        inp_satis = c3.number_input("Satış (Ciro)", min_value=0.0)
        inp_order = c4.number_input("Order (Adet)", min_value=0)
        inp_spend = c5.number_input("Reklam Harcaması", min_value=0.0)
        
        c6, c7 = st.columns(2)
        inp_adsales = c6.number_input("Reklamlı Satış", min_value=0.0)
        inp_tacos = c7.number_input("TACOS (%)", min_value=0.0, step=0.1)
        
        if st.form_submit_button("✅ Veriyi Kaydet"):
            new_row = {
                'Tarih': pd.to_datetime(inp_date),
                'Hesap': inp_hesap, 'Ülke': inp_ulke, 'Satış': inp_satis,
                'Order': inp_order, 'Reklam Harcaması': inp_spend,
                'Reklamlı Satış': inp_adsales, 'TACOS': inp_tacos
            }
            # Session State'e ekle
            st.session_state.manual_data = pd.concat([st.session_state.manual_data, pd.DataFrame([new_row])], ignore_index=True)
            st.success("Veri başarıyla eklendi!")
            st.rerun()

    # Eklenen verileri göster
    if not st.session_state.manual_data.empty:
        st.divider()
        st.write("📋 Eklenen Manuel Kayıtlar:")
        
        # Gösterim için tarihi string yapalım
        show_df = st.session_state.manual_data.copy()
        show_df['Tarih'] = show_df['Tarih'].dt.strftime('%d-%m-%Y')
        st.dataframe(show_df, use_container_width=True)
        
        if st.button("🗑️ Son Kaydı Sil"):
            st.session_state.manual_data = st.session_state.manual_data[:-1]
            st.rerun()

# ==========================================
# SEKME 3: İNDİRME
# ==========================================
with tab3:
    st.subheader("💾 Raporu İndir")
    st.write(f"Şu anki tarih aralığı ({start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}) içindeki filtrelenmiş veriyi indirir.")
    
    if not df_filtered.empty:
        excel_byte = convert_df_to_excel(df_filtered)
        fname = f"Satis_Raporu_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
        
        st.download_button(
            label="📥 Excel Olarak İndir",
            data=excel_byte,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("İndirilecek veri bulunmuyor.")
