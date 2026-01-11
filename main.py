import streamlit as st
import pandas as pd
import plotly.express as px
import io

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="Aylık E-Ticaret Raporu", layout="wide", page_icon="📅")

# ---------------------------------------------------------
# 1. FONKSİYONLAR
# ---------------------------------------------------------
@st.cache_data
def load_excel_file(uploaded_file):
    """Excel dosyasındaki TÜM sayfaları (sheet) okur."""
    try:
        # sheet_name=None parametresi tüm sekmeleri sözlük (dict) olarak okur
        xls = pd.read_excel(uploaded_file, sheet_name=None)
        return xls
    except Exception as e:
        st.error(f"Dosya okunamadı: {e}")
        return None

def clean_currency(x):
    """Metin formatındaki parayı (1.200 TL) sayıya (1200.0) çevirir."""
    if isinstance(x, str):
        # TL, %, harf ve boşlukları temizle. Virgülü noktaya çevir.
        clean_str = x.replace('TL', '').replace('₺', '').replace('%', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(clean_str)
        except:
            return 0.0
    return x

def get_idx(keywords, columns):
    """Sütun ismini tahmin etmeye yarayan yardımcı fonksiyon"""
    for i, c in enumerate(columns):
        if any(k in str(c).lower() for k in keywords):
            return i
    return 0

# ---------------------------------------------------------
# 2. SIDEBAR - DOSYA VE AY SEÇİMİ
# ---------------------------------------------------------
st.sidebar.title("🗂️ Rapor Yönetimi")

uploaded_file = st.sidebar.file_uploader("Excel Raporunu Yükle", type=["xlsx", "xls"])

if st.sidebar.button("⚠️ Paneli Temizle"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------
# 3. ANA MANTIK VE GÖRÜNÜM
# ---------------------------------------------------------

if uploaded_file:
    # Tüm sekmeleri oku
    all_sheets = load_excel_file(uploaded_file)
    
    if all_sheets:
        st.sidebar.divider()
        st.sidebar.subheader("1. Ay Seçimi")
        
        # Excel'deki sekme isimlerini listele (Örn: OCAK, ŞUBAT, MART...)
        sheet_names = list(all_sheets.keys())
        selected_sheet = st.sidebar.selectbox("Analiz Edilecek Ayı Seçin:", sheet_names)
        
        # Seçilen ayın verisini al
        df = all_sheets[selected_sheet].copy()
        
        # --- VERİ TEMİZLİĞİ ---
        # İlk satırlar bazen boş olabilir veya başlıklar kaymış olabilir.
        # Genelde başlıklar "Firma" kelimesinin olduğu satırdadır.
        # Bu basit bir kontrolle başlık satırını bulmaya çalışalım:
        
        # Eğer ilk sütunda 'Firma' yazmıyorsa, yazan satırı bulana kadar atla (Opsiyonel gelişmiş özellik)
        # Şimdilik standart okuma varsayıyoruz.
        
        # Boşlukları temizle
        df.columns = df.columns.str.strip()
        df = df.dropna(how='all') # Tamamen boş satırları sil
        
        cols = df.columns.tolist()
        
        # -----------------------------------------------------
        # SÜTUN EŞLEŞTİRME (MAPPING) - AY BAZLI
        # -----------------------------------------------------
        st.sidebar.divider()
        st.sidebar.subheader("2. Sütun Eşleştirme")
        st.sidebar.info(f"'{selected_sheet}' sayfası için sütunları doğrulayın:")
        
        # 1. KATEGORİLER
        idx_hesap = get_idx(['firma', 'hesap', 'account', 'marka'], cols)
        idx_ulke = get_idx(['ülke', 'country', 'region'], cols)
        
        c_hesap = st.sidebar.selectbox("Firma/Hesap", cols, index=idx_hesap)
        c_ulke = st.sidebar.selectbox("Ülke", cols, index=idx_ulke)
        
        # 2. METRİKLER (BU YIL)
        st.sidebar.markdown("**Bu Yılın Verileri**")
        idx_ciro = get_idx(['ciro', 'sales', 'tutar', '2025', 'revenue'], cols) # '2025' öncelikli
        idx_order = get_idx(['order', 'adet', 'qty', '2025'], cols)
        idx_spend = get_idx(['reklam harcama', 'spend', 'cost'], cols)
        idx_tacos = get_idx(['tacos', 'acos'], cols)
        
        c_ciro = st.sidebar.selectbox("Ciro (Bu Yıl)", cols, index=idx_ciro)
        c_order = st.sidebar.selectbox("Order (Bu Yıl)", cols, index=idx_order)
        c_spend = st.sidebar.selectbox("Reklam Harcaması", cols, index=idx_spend)
        c_tacos = st.sidebar.selectbox("TACOS (%)", cols, index=idx_tacos)

        # 3. METRİKLER (GEÇEN YIL - KARŞILAŞTIRMA İÇİN)
        st.sidebar.markdown("**Geçen Yıl (2024) Verileri**")
        # Geçen yılı bulmak için '2024' veya 'geçen' kelimesini arıyoruz
        # Ancak yukarıdaki 'ciro' seçiminden farklı olmalı.
        possible_prev_ciro = [i for i, c in enumerate(cols) if ('2024' in str(c) or 'geçen' in str(c).lower()) and 'ciro' in str(c).lower()]
        idx_prev_ciro = possible_prev_ciro[0] if possible_prev_ciro else 0
        
        c_prev_ciro = st.sidebar.selectbox("Ciro (Geçen Yıl/2024)", cols, index=idx_prev_ciro)

        # -----------------------------------------------------
        # VERİ İŞLEME
        # -----------------------------------------------------
        # Seçilen sütunları temizle ve sayıya çevir
        numeric_cols = [c_ciro, c_order, c_spend, c_tacos, c_prev_ciro]
        
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col].apply(clean_currency), errors='coerce').fillna(0)
            
        # -----------------------------------------------------
        # DASHBOARD EKRANI
        # -----------------------------------------------------
        st.title(f"📊 {selected_sheet} Ayı Performans Analizi")
        
        # FİLTRELER
        col_f1, col_f2 = st.columns(2)
        
        # Filtre listelerini oluştur (string'e çevirerek hata önle)
        hesaplar = ["Tümü"] + sorted(df[c_hesap].dropna().astype(str).unique().tolist())
        ulkeler = ["Tümü"] + sorted(df[c_ulke].dropna().astype(str).unique().tolist())
        
        sel_hesap = col_f1.selectbox("Firma Filtrele:", hesaplar)
        sel_ulke = col_f2.selectbox("Ülke Filtrele:", ulkeler)
        
        # Veriyi Süz
        df_viz = df.copy()
        if sel_hesap != "Tümü": 
            df_viz = df_viz[df_viz[c_hesap].astype(str) == sel_hesap]
        if sel_ulke != "Tümü": 
            df_viz = df_viz[df_viz[c_ulke].astype(str) == sel_ulke]
            
        st.markdown("---")
        
        # KPI KARTLARI
        # Toplamları hesapla
        toplam_ciro = df_viz[c_ciro].sum()
        toplam_gecen_ciro = df_viz[c_prev_ciro].sum()
        toplam_order = df_viz[c_order].sum()
        toplam_spend = df_viz[c_spend].sum()
        ort_tacos = df_viz[c_tacos].mean()
        
        # Büyüme Oranı Hesapla
        buyume_orani = ((toplam_ciro - toplam_gecen_ciro) / toplam_gecen_ciro * 100) if toplam_gecen_ciro > 0 else 0
        fark_tl = toplam_ciro - toplam_gecen_ciro

        k1, k2, k3, k4, k5 = st.columns(5)
        
        k1.metric("Ciro (Bu Yıl)", f"{toplam_ciro:,.0f} TL", f"%{buyume_orani:.1f}")
        k2.metric("Ciro (Geçen Yıl)", f"{toplam_gecen_ciro:,.0f} TL", f"{fark_tl:,.0f} TL Fark", delta_color="normal")
        k3.metric("Toplam Order", f"{toplam_order:,.0f}")
        k4.metric("Reklam Harcaması", f"{toplam_spend:,.0f} TL")
        k5.metric("Ort. TACOS", f"%{ort_tacos:.1f}")
        
        st.markdown("---")
        
        # GRAFİKLER
        col_g_sol, col_g_sag = st.columns([2, 1])
        
        with col_g_sol:
            st.subheader("📈 Karşılaştırmalı Performans")
            
            # Gruplama Sütunu Belirle (Tek firma seçildiyse ülkeye göre, değilse firmaya göre)
            grp_col = c_ulke if sel_hesap != "Tümü" else c_hesap
            grp_name = "Ülke" if sel_hesap != "Tümü" else "Firma"
            
            # Veriyi Hazırla
            chart_data = df_viz.groupby(grp_col)[[c_ciro, c_prev_ciro]].sum().reset_index()
            
            # İsimleri grafikte güzel görünsün diye değiştir
            chart_data = chart_data.rename(columns={c_ciro: 'Bu Yıl', c_prev_ciro: 'Geçen Yıl'})
            
            # Melt (Uzun format)
            chart_melt = chart_data.melt(id_vars=grp_col, var_name='Dönem', value_name='Tutar')
            
            fig = px.bar(
                chart_melt, 
                x=grp_col, 
                y='Tutar', 
                color='Dönem', 
                barmode='group',
                text_auto='.2s',
                title=f"{grp_name} Bazlı Ciro Karşılaştırması (Bu Yıl vs Geçen Yıl)",
                color_discrete_map={'Bu Yıl': '#00CC96', 'Geçen Yıl': '#EF553B'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col_g_sag:
            st.subheader("📊 Gider Analizi")
            # Reklam harcaması vs Ciro scatter plot veya Pie chart
            if toplam_ciro > 0:
                # Pasta grafik için veri
                pie_df = df_viz.groupby(grp_col)[c_ciro].sum().reset_index()
                fig2 = px.pie(pie_df, values=c_ciro, names=grp_col, hole=0.4, title=f"{grp_name} Payları")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Grafik için veri yetersiz.")

        # DETAY TABLO
        st.markdown("---")
        with st.expander("📋 Detaylı Veri Tablosunu Göster", expanded=True):
            # Tabloda gösterilecek sütunları düzenle
            show_cols = [c_hesap, c_ulke, c_ciro, c_prev_ciro, c_order, c_spend, c_tacos]
            
            # Sütun isimlerini daha okunur yapalım
            display_df = df_viz[show_cols].rename(columns={
                c_hesap: 'Firma',
                c_ulke: 'Ülke',
                c_ciro: '2025 Ciro',
                c_prev_ciro: '2024 Ciro',
                c_order: 'Order',
                c_spend: 'Reklam',
                c_tacos: 'TACOS'
            })
            
            st.dataframe(display_df, use_container_width=True)
            
else:
    # Dosya yüklenmediyse karşılama ekranı
    st.info("👆 Lütfen sol menüden aylık sekmeler içeren Excel dosyanızı yükleyin.")
    
    st.markdown("""
    ### Bu Panel Nasıl Çalışır?
    1. **Excel Yükle:** İçinde 'OCAK', 'ŞUBAT' gibi sekmeler olan dosyanızı yükleyin.
    2. **Ay Seçin:** Sol menüden analiz etmek istediğiniz sekmeyi seçin.
    3. **Sütunları Onaylayın:** Her ayın sütun isimleri farklı olabilir, sol menüden doğru sütunların seçili olduğundan emin olun.
    4. **Analiz Edin:** 2024 vs 2025 karşılaştırması ve ülke bazlı kırılımlar otomatik oluşacaktır.
    """)
