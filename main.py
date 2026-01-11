import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime

# ---------------------------------------------------------
# SAYFA AYARLARI
# ---------------------------------------------------------
st.set_page_config(page_title="E-Ticaret Veri Yönetim Paneli", layout="wide", page_icon="🧮")

# Veritabanı Dosya Adı
DB_FILE = 'eticaret_veritabani_v2.csv'

# ---------------------------------------------------------
# 1. TEMEL FONKSİYONLAR VE HESAPLAMA MOTORU
# ---------------------------------------------------------
def init_db():
    """Veritabanı dosyası yoksa gerekli sütunlarla oluşturur."""
    columns = [
        'Tarih', 'Ay', 'Firma', 'Ülke', 
        'Ciro', 'GecenYilCiro', 'Order', 
        'Reklam', 'ReklamliSatis', # Ham Veriler
        'TACOS', 'ACOS', 'AOV'     # Otomatik Hesaplanacaklar
    ]
    
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=columns)
        df.to_csv(DB_FILE, index=False)
        return df
    else:
        # Mevcut dosyayı oku, eksik sütun varsa tamamla (Eski versiyondan geçiş için)
        df = pd.read_csv(DB_FILE)
        for col in columns:
            if col not in df.columns:
                df[col] = 0
        return df

def calculate_metrics(df):
    """
    Verilen DataFrame üzerindeki ham verileri kullanarak 
    ACOS, TACOS ve AOV metriklerini otomatik hesaplar.
    """
    # 0'a bölünme hatalarını önlemek için işlemler
    
    # 1. TACOS = Reklam Harcaması / Toplam Ciro
    df['TACOS'] = df.apply(lambda x: (x['Reklam'] / x['Ciro']) if x['Ciro'] > 0 else 0, axis=1)
    
    # 2. ACOS = Reklam Harcaması / Reklamlı Satış
    df['ACOS'] = df.apply(lambda x: (x['Reklam'] / x['ReklamliSatis']) if x['ReklamliSatis'] > 0 else 0, axis=1)
    
    # 3. AOV (Sepet Ortalaması) = Toplam Ciro / Order Adeti
    df['AOV'] = df.apply(lambda x: (x['Ciro'] / x['Order']) if x['Order'] > 0 else 0, axis=1)
    
    return df

def save_to_db(new_data):
    """Yeni veriyi hesaplayıp kaydeder."""
    # Önce metrikleri hesapla
    new_data = calculate_metrics(new_data)
    
    current_db = init_db() # Dosyayı oku
    updated_db = pd.concat([current_db, new_data], ignore_index=True)
    updated_db.to_csv(DB_FILE, index=False)
    return updated_db

def reset_db():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    init_db()

def clean_currency(x):
    if isinstance(x, str):
        clean_str = x.replace('TL', '').replace('₺', '').replace('%', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(clean_str)
        except:
            return 0.0
    return x

# Oturum Kontrolü
if 'main_df' not in st.session_state:
    st.session_state.main_df = init_db()

# ---------------------------------------------------------
# 2. SIDEBAR MENÜ
# ---------------------------------------------------------
st.sidebar.title("🎛️ Kontrol Paneli")
menu = st.sidebar.radio(
    "Menü Seçimi:",
    ["📊 Analiz Paneli (Dashboard)", "📤 Excel'den Veri Yükle", "📝 Manuel Veri Girişi", "⚙️ Ayarlar"]
)

# ---------------------------------------------------------
# MODÜL 1: EXCEL'DEN VERİ YÜKLEME
# ---------------------------------------------------------
if menu == "📤 Excel'den Veri Yükle":
    st.title("📤 Excel Yükle & Otomatik Hesapla")
    st.info("Siz sadece ham verileri (Ciro, Order, Reklam vb.) eşleştirin. ACOS, TACOS ve AOV otomatik hesaplanacaktır.")

    uploaded_file = st.file_uploader("Excel Dosyası (.xlsx)", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            xls = pd.read_excel(uploaded_file, sheet_name=None)
            sheet_names = list(xls.keys())
            
            st.write("---")
            c1, c2 = st.columns(2)
            selected_sheet = c1.selectbox("Sekme Seçin", sheet_names)
            
            df_temp = xls[selected_sheet].copy().dropna(how='all')
            cols = df_temp.columns.tolist()
            
            # Sütun Eşleştirme
            st.subheader("🔗 Sütun Eşleştirme")
            
            def get_idx(keys, columns):
                for i, c in enumerate(columns):
                    if any(k in str(c).lower() for k in keys): return i
                return 0

            col1, col2, col3 = st.columns(3)
            with col1:
                map_firma = st.selectbox("Firma", cols, index=get_idx(['firma', 'hesap'], cols))
                map_ulke = st.selectbox("Ülke", cols, index=get_idx(['ülke', 'country'], cols))
                secilen_ay = st.text_input("Dönem/Ay İsmi", value=selected_sheet)
                
            with col2:
                map_ciro = st.selectbox("Ciro (Total Sales)", cols, index=get_idx(['ciro', 'sales', '2025'], cols))
                map_prev = st.selectbox("Geçen Yıl Ciro", cols, index=get_idx(['2024', 'geçen'], cols))
                map_order = st.selectbox("Order (Total Orders)", cols, index=get_idx(['order', 'adet'], cols))
                
            with col3:
                map_spend = st.selectbox("Reklam Harcaması (Spend)", cols, index=get_idx(['reklam', 'spend'], cols))
                map_adsales = st.selectbox("Reklamlı Satış (Ad Sales)", cols, index=get_idx(['ad sales', 'reklam ciro', 'reklamlı'], cols))
                
            st.warning("⚠️ Not: Excel'inizdeki TACOS/ACOS sütunlarını seçmenize gerek yok. Sistem Ciro, Order ve Reklam verisinden kendisi hesaplayacaktır.")

            if st.button("🚀 Hesapla ve Kaydet"):
                new_data = pd.DataFrame()
                new_data['Firma'] = df_temp[map_firma]
                new_data['Ülke'] = df_temp[map_ulke]
                
                # Temizlik
                new_data['Ciro'] = df_temp[map_ciro].apply(clean_currency)
                new_data['GecenYilCiro'] = df_temp[map_prev].apply(clean_currency)
                new_data['Order'] = df_temp[map_order].apply(clean_currency)
                new_data['Reklam'] = df_temp[map_spend].apply(clean_currency)
                new_data['ReklamliSatis'] = df_temp[map_adsales].apply(clean_currency)
                
                new_data['Ay'] = secilen_ay
                new_data['Tarih'] = datetime.date.today()
                
                # Veriyi Kaydet (Otomatik hesaplama save_to_db içinde yapılır)
                updated_df = save_to_db(new_data)
                st.session_state.main_df = updated_df
                
                st.success("✅ Veriler hesaplandı ve kaydedildi!")
                st.dataframe(updated_df.tail(len(new_data))) # Son eklenenleri göster

        except Exception as e:
            st.error(f"Hata: {e}")

# ---------------------------------------------------------
# MODÜL 2: MANUEL VERİ GİRİŞİ
# ---------------------------------------------------------
elif menu == "📝 Manuel Veri Girişi":
    st.title("📝 Manuel Giriş (Otomatik Hesaplama)")
    st.info("Sadece temel verileri girin. ACOS, TACOS ve AOV'yi biz hesaplayacağız.")

    with st.form("manuel_form"):
        c1, c2 = st.columns(2)
        inp_ay = c1.selectbox("Dönem", ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])
        inp_tarih = c2.date_input("Kayıt Tarihi", datetime.date.today())
        
        c3, c4 = st.columns(2)
        inp_firma = c3.text_input("Firma", "HomeByHome")
        inp_ulke = c4.text_input("Ülke", "DE")
        
        st.write("---")
        st.markdown("**Finansal Veriler**")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        inp_ciro = col_m1.number_input("Toplam Ciro (Sales)", min_value=0.0, step=100.0)
        inp_order = col_m2.number_input("Toplam Order (Adet)", min_value=0, step=1)
        inp_prev = col_m3.number_input("Geçen Yıl Ciro (Opsiyonel)", min_value=0.0, step=100.0)
        
        col_m4, col_m5 = st.columns(2)
        inp_reklam = col_m4.number_input("Reklam Harcaması (Spend)", min_value=0.0, step=50.0)
        inp_adsales = col_m5.number_input("Reklamlı Satış (Ad Sales)", min_value=0.0, step=50.0, help="ACOS hesaplaması için gereklidir.")
        
        submitted = st.form_submit_button("🧮 Hesapla ve Kaydet")
        
        if submitted:
            # Tek satırlık veri
            row = {
                'Tarih': inp_tarih,
                'Ay': inp_ay,
                'Firma': inp_firma,
                'Ülke': inp_ulke,
                'Ciro': inp_ciro,
                'GecenYilCiro': inp_prev,
                'Order': inp_order,
                'Reklam': inp_reklam,
                'ReklamliSatis': inp_adsales
            }
            new_df = pd.DataFrame([row])
            
            # Kaydet (Hesaplama otomatik yapılacak)
            updated_df = save_to_db(new_df)
            st.session_state.main_df = updated_df
            
            # Kullanıcıya ne hesaplandığını gösterelim
            last_entry = updated_df.iloc[-1]
            st.success("✅ Kayıt Başarılı!")
            st.info(f"🧮 **Otomatik Hesaplanan Değerler:**\n"
                    f"- **TACOS:** %{last_entry['TACOS']*100:.2f}\n"
                    f"- **ACOS:** %{last_entry['ACOS']*100:.2f}\n"
                    f"- **AOV:** {last_entry['AOV']:.2f} TL")

# ---------------------------------------------------------
# MODÜL 3: ANALİZ PANELİ
# ---------------------------------------------------------
elif menu == "📊 Analiz Paneli (Dashboard)":
    st.title("📊 Performans Dashboard")
    
    df = st.session_state.main_df
    
    if df.empty:
        st.warning("Veri yok.")
    else:
        # Filtreler
        st.sidebar.markdown("---")
        sel_ay = st.sidebar.selectbox("Dönem:", ["Tümü"] + list(df['Ay'].unique()))
        sel_firma = st.sidebar.selectbox("Firma:", ["Tümü"] + list(df['Firma'].unique()))
        
        df_viz = df.copy()
        if sel_ay != "Tümü": df_viz = df_viz[df_viz['Ay'] == sel_ay]
        if sel_firma != "Tümü": df_viz = df_viz[df_viz['Firma'] == sel_firma]
        
        # --- KPI KARTLARI ---
        # Ağırlıklı ortalamalar ve toplamlar
        toplam_ciro = df_viz['Ciro'].sum()
        toplam_order = df_viz['Order'].sum()
        toplam_reklam = df_viz['Reklam'].sum()
        toplam_adsales = df_viz['ReklamliSatis'].sum()
        
        # Oranları toplam üzerinden yeniden hesapla (Aritmetik ortalama yanıltıcı olabilir)
        genel_tacos = (toplam_reklam / toplam_ciro * 100) if toplam_ciro > 0 else 0
        genel_acos = (toplam_reklam / toplam_adsales * 100) if toplam_adsales > 0 else 0
        genel_aov = (toplam_ciro / toplam_order) if toplam_order > 0 else 0
        
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Toplam Ciro", f"{toplam_ciro:,.0f} TL")
        k2.metric("Toplam Order", f"{toplam_order:,.0f}")
        k3.metric("AOV (Sepet Ort.)", f"{genel_aov:,.1f} TL")
        k4.metric("Genel TACOS", f"%{genel_tacos:.1f}")
        k5.metric("Genel ACOS", f"%{genel_acos:.1f}")
        
        st.markdown("---")
        
        # --- GRAFİKLER ---
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("📈 Metrik Karşılaştırması")
            metrik_secimi = st.selectbox("Grafik Verisi:", ["Ciro", "Order", "Reklam", "AOV", "TACOS", "ACOS"])
            
            grp = 'Ülke' if sel_ay != "Tümü" else 'Ay'
            
            # Oransal veriler için ortalama, sayısallar için toplam
            if metrik_secimi in ['AOV', 'TACOS', 'ACOS']:
                chart_data = df_viz.groupby(grp)[metrik_secimi].mean().reset_index()
            else:
                chart_data = df_viz.groupby(grp)[metrik_secimi].sum().reset_index()
                
            fig = px.bar(chart_data, x=grp, y=metrik_secimi, text_auto='.2s', title=f"{grp} Bazlı {metrik_secimi}")
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("💡 Kârlılık Analizi")
            # Scatter Plot: Ciro vs TACOS (Düşük TACOS, Yüksek Ciro iyidir)
            if not df_viz.empty:
                fig2 = px.scatter(df_viz, x="Ciro", y="TACOS", size="Reklam", color="Firma", 
                                  hover_name="Ülke", title="Ciro vs TACOS (Baloncuk: Reklam)")
                st.plotly_chart(fig2, use_container_width=True)
        
        # --- DETAYLI TABLO ---
        with st.expander("📋 Detaylı Veri Tablosu"):
            # Gösterim için yüzdeleri formatla
            show_df = df_viz.copy()
            show_df['TACOS'] = show_df['TACOS'].apply(lambda x: f"%{x*100:.2f}")
            show_df['ACOS'] = show_df['ACOS'].apply(lambda x: f"%{x*100:.2f}")
            show_df['AOV'] = show_df['AOV'].apply(lambda x: f"{x:.2f} TL")
            st.dataframe(show_df, use_container_width=True)

# ---------------------------------------------------------
# MODÜL 4: AYARLAR
# ---------------------------------------------------------
elif menu == "⚙️ Ayarlar":
    st.title("⚙️ Ayarlar")
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"Veritabanı: `{DB_FILE}`")
        if os.path.exists(DB_FILE):
            df = pd.read_csv(DB_FILE)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Yedeği İndir", csv, "eticaret_data_yedek.csv", "text/csv")
            
    with c2:
        if st.button("🗑️ Veritabanını SIFIRLA"):
            reset_db()
            st.session_state.main_df = init_db()
            st.error("Veritabanı sıfırlandı!")
            st.rerun()
