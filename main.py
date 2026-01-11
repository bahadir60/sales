import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Veri Yönetim Paneli", layout="wide", page_icon="💾")

# Veritabanı Dosya Adı
DB_FILE = 'eticaret_veritabani.csv'

# ---------------------------------------------------------
# 1. VERİTABANI YÖNETİM FONKSİYONLARI
# ---------------------------------------------------------
def init_db():
    """Veritabanı dosyası yoksa oluşturur, varsa yükler."""
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=['Tarih', 'Ay', 'Firma', 'Ülke', 'Ciro', 'GecenYilCiro', 'Order', 'Reklam', 'TACOS'])
        df.to_csv(DB_FILE, index=False)
        return df
    else:
        return pd.read_csv(DB_FILE)

def save_to_db(new_data):
    """Yeni veriyi mevcut veritabanına ekler ve kaydeder."""
    current_db = pd.read_csv(DB_FILE)
    updated_db = pd.concat([current_db, new_data], ignore_index=True)
    updated_db.to_csv(DB_FILE, index=False)
    return updated_db

def reset_db():
    """Veritabanını sıfırlar."""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()

def clean_currency(x):
    """Metin formatındaki sayıları temizler."""
    if isinstance(x, str):
        clean_str = x.replace('TL', '').replace('₺', '').replace('%', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(clean_str)
        except:
            return 0.0
    return x

# Uygulama Başlangıcında DB Kontrolü
if 'main_df' not in st.session_state:
    st.session_state.main_df = init_db()

# ---------------------------------------------------------
# 2. SIDEBAR - MENÜ GEÇİŞLERİ
# ---------------------------------------------------------
st.sidebar.title("🎛️ Kontrol Paneli")

menu = st.sidebar.radio(
    "Menü Seçimi:",
    ["📊 Analiz Paneli (Dashboard)", "📤 Excel'den Veri Yükle", "📝 Manuel Veri Girişi", "⚙️ Ayarlar"]
)

# ---------------------------------------------------------
# MODÜL 1: EXCEL'DEN VERİ YÜKLEME (IMPORT)
# ---------------------------------------------------------
if menu == "📤 Excel'den Veri Yükle":
    st.title("📤 Excel Verilerini Veritabanına Aktar")
    st.info("Buradan yüklediğiniz Excel dosyasındaki verileri kalıcı hafızaya kaydedebilirsiniz.")

    uploaded_file = st.file_uploader("Excel Dosyası Seçin", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            xls = pd.read_excel(uploaded_file, sheet_name=None)
            sheet_names = list(xls.keys())
            
            st.write("---")
            c1, c2 = st.columns(2)
            selected_sheet = c1.selectbox("Hangi Sekme (Ay) Yüklenecek?", sheet_names)
            
            # Seçilen sekmeyi oku
            df_temp = xls[selected_sheet].copy()
            df_temp = df_temp.dropna(how='all')
            cols = df_temp.columns.tolist()
            
            # Sütun Eşleştirme
            st.subheader("🔗 Sütun Eşleştirme")
            st.caption("Excel'deki sütunları sistemdeki karşılıklarıyla eşleştirin.")
            
            def get_idx(keys, columns):
                for i, c in enumerate(columns):
                    if any(k in str(c).lower() for k in keys): return i
                return 0

            col1, col2, col3 = st.columns(3)
            with col1:
                map_firma = st.selectbox("Firma Sütunu", cols, index=get_idx(['firma', 'hesap'], cols))
                map_ulke = st.selectbox("Ülke Sütunu", cols, index=get_idx(['ülke', 'country'], cols))
                # Ay bilgisini kullanıcıdan manuel alabiliriz veya sheet isminden
                secilen_ay = st.text_input("Bu veriler hangi Ay/Dönem için?", value=selected_sheet)
                
            with col2:
                map_ciro = st.selectbox("Ciro (Bu Yıl)", cols, index=get_idx(['ciro', 'sales', '2025'], cols))
                map_prev_ciro = st.selectbox("Ciro (Geçen Yıl)", cols, index=get_idx(['2024', 'geçen'], cols))
                map_order = st.selectbox("Order (Adet)", cols, index=get_idx(['order', 'adet'], cols))
                
            with col3:
                map_spend = st.selectbox("Reklam Harcaması", cols, index=get_idx(['reklam', 'spend'], cols))
                map_tacos = st.selectbox("TACOS (%)", cols, index=get_idx(['tacos', 'acos'], cols))
            
            # ÖNİZLEME VE KAYIT
            st.write("---")
            if st.button("💾 Verileri Kaydet ve Veritabanına Ekle"):
                # Yeni dataframe oluştur (Standardize et)
                new_data = pd.DataFrame()
                new_data['Firma'] = df_temp[map_firma]
                new_data['Ülke'] = df_temp[map_ulke]
                new_data['Ciro'] = df_temp[map_ciro].apply(clean_currency)
                new_data['GecenYilCiro'] = df_temp[map_prev_ciro].apply(clean_currency)
                new_data['Order'] = df_temp[map_order].apply(clean_currency)
                new_data['Reklam'] = df_temp[map_spend].apply(clean_currency)
                new_data['TACOS'] = df_temp[map_tacos].apply(clean_currency)
                
                # Tarih ve Ay bilgisi ekle
                new_data['Ay'] = secilen_ay
                new_data['Tarih'] = datetime.date.today() # Yükleme tarihi
                
                # Boş satırları ve 0 ciroları temizle (İsteğe bağlı)
                new_data = new_data[new_data['Ciro'] > 0]
                
                # Veritabanına yaz
                updated_df = save_to_db(new_data)
                st.session_state.main_df = updated_df
                
                st.success(f"✅ {len(new_data)} satır veri başarıyla kaydedildi!")
                st.dataframe(new_data.head())

        except Exception as e:
            st.error(f"Hata oluştu: {e}")

# ---------------------------------------------------------
# MODÜL 2: MANUEL VERİ GİRİŞİ
# ---------------------------------------------------------
elif menu == "📝 Manuel Veri Girişi":
    st.title("📝 Manuel Veri Girişi")
    st.info("Excel dosyanız yoksa verileri buradan elle girip kaydedebilirsiniz.")

    with st.form("manuel_form"):
        c1, c2 = st.columns(2)
        inp_ay = c1.selectbox("Dönem/Ay", ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", 
                                           "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])
        inp_tarih = c2.date_input("İşlem Tarihi", datetime.date.today())
        
        c3, c4 = st.columns(2)
        inp_firma = c3.text_input("Firma Adı", "HomeByHome")
        inp_ulke = c4.text_input("Ülke", "DE")
        
        st.write("---")
        m1, m2, m3 = st.columns(3)
        inp_ciro = m1.number_input("Ciro (Bu Yıl)", min_value=0.0, step=100.0)
        inp_prev = m2.number_input("Ciro (Geçen Yıl)", min_value=0.0, step=100.0)
        inp_order = m3.number_input("Order (Adet)", min_value=0, step=1)
        
        m4, m5 = st.columns(2)
        inp_reklam = m4.number_input("Reklam Harcaması", min_value=0.0)
        inp_tacos = m5.number_input("TACOS (%)", min_value=0.0, step=0.1)
        
        submitted = st.form_submit_button("💾 Kaydet")
        
        if submitted:
            # Tek satırlık veri oluştur
            row = {
                'Tarih': inp_tarih,
                'Ay': inp_ay,
                'Firma': inp_firma,
                'Ülke': inp_ulke,
                'Ciro': inp_ciro,
                'GecenYilCiro': inp_prev,
                'Order': inp_order,
                'Reklam': inp_reklam,
                'TACOS': inp_tacos
            }
            new_df = pd.DataFrame([row])
            
            # Kaydet
            updated_df = save_to_db(new_df)
            st.session_state.main_df = updated_df
            st.success("✅ Veri başarıyla veritabanına eklendi.")

# ---------------------------------------------------------
# MODÜL 3: ANALİZ PANELİ (DASHBOARD)
# ---------------------------------------------------------
elif menu == "📊 Analiz Paneli (Dashboard)":
    st.title("📊 Yönetim Raporu")
    
    # Veritabanını Oku
    df = st.session_state.main_df
    
    if df.empty:
        st.warning("Veritabanında henüz veri yok. Lütfen 'Excel Yükle' veya 'Manuel Giriş' menüsünü kullanın.")
    else:
        # --- FİLTRELER ---
        st.sidebar.markdown("---")
        st.sidebar.header("Filtreler")
        
        # Ay Filtresi
        aylar = ["Tümü"] + list(df['Ay'].unique())
        sel_ay = st.sidebar.selectbox("Dönem Seçin:", aylar)
        
        # Firma Filtresi
        firmalar = ["Tümü"] + list(df['Firma'].unique())
        sel_firma = st.sidebar.selectbox("Firma Seçin:", firmalar)
        
        # Veriyi Süz
        df_viz = df.copy()
        if sel_ay != "Tümü":
            df_viz = df_viz[df_viz['Ay'] == sel_ay]
        if sel_firma != "Tümü":
            df_viz = df_viz[df_viz['Firma'] == sel_firma]
            
        # --- ÖZET METRİKLER ---
        toplam_ciro = df_viz['Ciro'].sum()
        toplam_gecen = df_viz['GecenYilCiro'].sum()
        toplam_order = df_viz['Order'].sum()
        toplam_reklam = df_viz['Reklam'].sum()
        ort_tacos = df_viz['TACOS'].mean()
        
        diff = toplam_ciro - toplam_gecen
        growth = (diff / toplam_gecen * 100) if toplam_gecen > 0 else 0
        
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Toplam Ciro", f"{toplam_ciro:,.0f} TL", f"%{growth:.1f}")
        k2.metric("Geçen Yıl Ciro", f"{toplam_gecen:,.0f} TL", f"{diff:,.0f} TL")
        k3.metric("Order", f"{toplam_order:,.0f}")
        k4.metric("Reklam Harcama", f"{toplam_reklam:,.0f} TL")
        k5.metric("Ort. TACOS", f"%{ort_tacos:.1f}")
        
        st.markdown("---")
        
        # --- GRAFİKLER ---
        c_grafik1, c_grafik2 = st.columns([2, 1])
        
        with c_grafik1:
            st.subheader("📈 Karşılaştırmalı Ciro Analizi")
            # Gruplama (Ay seçiliyse Ülkeye göre, değilse Aya göre)
            grp = 'Ülke' if sel_ay != "Tümü" else 'Ay'
            
            chart_data = df_viz.groupby(grp)[['Ciro', 'GecenYilCiro']].sum().reset_index()
            chart_melt = chart_data.melt(id_vars=grp, var_name='Dönem', value_name='Tutar')
            
            fig = px.bar(chart_melt, x=grp, y='Tutar', color='Dönem', barmode='group', 
                         title=f"{grp} Bazlı Dağılım", text_auto='.2s',
                         color_discrete_map={'Ciro': '#00CC96', 'GecenYilCiro': '#EF553B'})
            st.plotly_chart(fig, use_container_width=True)
            
        with c_grafik2:
            st.subheader("🌍 Ülke Dağılımı")
            if toplam_ciro > 0:
                fig2 = px.pie(df_viz, values='Ciro', names='Ülke', hole=0.4)
                st.plotly_chart(fig2, use_container_width=True)
                
        # --- DETAY TABLO ---
        with st.expander("📋 Kayıtlı Verileri Görüntüle", expanded=True):
            st.dataframe(df_viz, use_container_width=True)

# ---------------------------------------------------------
# MODÜL 4: AYARLAR (VERİTABANI YÖNETİMİ)
# ---------------------------------------------------------
elif menu == "⚙️ Ayarlar":
    st.title("⚙️ Sistem Ayarları")
    
    st.warning("Buradaki işlemler geri alınamaz.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"📂 Mevcut Veritabanı: `{DB_FILE}`")
        if os.path.exists(DB_FILE):
            df = pd.read_csv(DB_FILE)
            st.write(f"Toplam Kayıt Sayısı: **{len(df)}**")
            
            # İndirme Butonu
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Veritabanını İndir (Yedek)", csv, "yedek_veritabani.csv", "text/csv")
            
    with c2:
        if st.button("🗑️ Veritabanını SIFIRLA (Tüm Verileri Sil)"):
            reset_db()
            st.session_state.main_df = init_db()
            st.success("Veritabanı temizlendi ve sıfırlandı.")
            st.rerun()
