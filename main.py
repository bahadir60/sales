import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
from datetime import datetime, date
import re

# --- 1. GÜVENLİK VE GİRİŞ SİSTEMİ ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔐 Erişim Paneli")
        user = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap"):
            # Şifrelerinizi buradan güncelleyebilirsiniz
            if user == "admin" and password == "amazon2025": 
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Hatalı giriş!")
        return False
    return True

# --- 2. VERİTABANI BAĞLANTISI (POSTGRESQL / SQLITE) ---
def get_engine():
    # Bulut (PostgreSQL) için st.secrets["DATABASE_URL"] kullanılır.
    # Yerelde test etmek için otomatik SQLite oluşturur.
    try:
        conn_str = st.secrets.get("DATABASE_URL", "sqlite:///amazon_reports.db")
        # Render/Heroku/Supabase uyumluluğu için prefix düzeltmesi
        if conn_str.startswith("postgres://"):
            conn_str = conn_str.replace("postgres://", "postgresql://", 1)
        return create_engine(conn_str)
    except Exception as e:
        st.error(f"DB Bağlantı Hatası: {e}")
        return None

def init_db():
    engine = get_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS reports (
                    id SERIAL PRIMARY KEY,
                    firma TEXT,
                    ulke TEXT,
                    baslangic_tarihi DATE,
                    bitis_tarihi DATE,
                    ciro FLOAT,
                    siparis_adeti INTEGER,
                    reklam_harcamasi FLOAT,
                    reklamli_satis FLOAT,
                    tacos FLOAT,
                    kaynak_dosya TEXT,
                    kayit_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))

# --- 3. AKILLI VERİ İŞLEME MANTĞI ---
def find_col(df, keywords, exclude=["Artış", "Oran", "Kümülatif", "2024", "Geçen"]):
    for col in df.columns:
        col_str = str(col).lower()
        if any(k.lower() in col_str for k in keywords):
            if not any(e.lower() in col_str for e in exclude):
                return col
    return None

def parse_dates_from_filename(filename):
    # Dosya adından (Örn: "1-14 Aralık") tarih çıkarmaya çalışır
    # Varsayılan olarak bugünü döner, geliştirilebilir.
    return date.today(), date.today()

# --- 4. ANA PROGRAM ---
st.set_page_config(page_title="Amazon Pro Dashboard", layout="wide", page_icon="📈")
init_db()

if check_password():
    st.sidebar.title("📊 Navigasyon")
    menu = st.sidebar.radio("Menü", ["Dashboard", "Veri Yükleme (Excel/CSV)", "Manuel Giriş", "Veri Yönetimi"])
    engine = get_engine()

    # --- MODÜL: DASHBOARD ---
    if menu == "Dashboard":
        st.header("📈 Performans Analiz Paneli")
        df = pd.read_sql("SELECT * FROM reports", engine)
        
        if not df.empty:
            df['baslangic_tarihi'] = pd.to_datetime(df['baslangic_tarihi']).dt.date
            
            # Tarih Filtresi
            st.sidebar.subheader("📅 Tarih Filtresi")
            min_d, max_d = df['baslangic_tarihi'].min(), df['baslangic_tarihi'].max()
            selected_dates = st.sidebar.date_input("Dönem Seçin", [min_d, max_d])
            
            if len(selected_dates) == 2:
                f_df = df[(df['baslangic_tarihi'] >= selected_dates[0]) & (df['baslangic_tarihi'] <= selected_dates[1])]
                
                # KPI Kartları
                k1, k2, k3, k4 = st.columns(4)
                total_rev = f_df['ciro'].sum()
                total_spend = f_df['reklam_harcamasi'].sum()
                k1.metric("Toplam Ciro", f"€{total_rev:,.2f}")
                k2.metric("Reklam Harcaması", f"€{total_spend:,.2f}")
                k3.metric("Sipariş Adeti", f"{int(f_df['siparis_adeti'].sum()):,}")
                k4.metric("Ort. TACOS", f"%{(total_spend/total_rev*100 if total_rev > 0 else 0):.2f}")

                # Grafikler
                st.divider()
                col_a, col_b = st.columns(2)
                with col_a:
                    fig1 = px.bar(f_df, x="ulke", y="ciro", color="firma", barmode="group", title="Ülke ve Firma Bazlı Ciro")
                    st.plotly_chart(fig1, use_container_width=True)
                with col_b:
                    fig2 = px.line(f_df.sort_values("baslangic_tarihi"), x="baslangic_tarihi", y="ciro", color="ulke", title="Ciro Trendi")
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Henüz veri yok. Lütfen yükleme yapın.")

    # --- MODÜL: VERİ YÜKLEME ---
    elif menu == "Veri Yükleme (Excel/CSV)":
        st.header("📤 Dosya Aktarımı")
        uploaded_files = st.file_uploader("Dosyaları Seçin", type=["xlsx", "csv"], accept_multiple_files=True)
        
        if st.button("Veritabanına Kaydet") and uploaded_files:
            for file in uploaded_files:
                try:
                    df_temp = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
                    
                    # Sütun Eşleştirme
                    c_rev = find_col(df_temp, ["Ciro"])
                    c_spend = find_col(df_temp, ["Spend", "Harcama"])
                    c_order = find_col(df_temp, ["Order", "Adeti", "Units"])
                    c_sales = find_col(df_temp, ["Ad Sales", "Reklamlı Satış"])
                    c_firma = find_col(df_temp, ["Firma"]) or "HomeByHome"
                    c_ulke = find_col(df_temp, ["Ülke", "Country"])
                    
                    start, end = parse_dates_from_filename(file.name)
                    
                    rows = []
                    for _, row in df_temp.iterrows():
                        ciro_val = pd.to_numeric(row[c_rev], errors='coerce') if c_rev else 0
                        if pd.isna(ciro_val) or ciro_val <= 0: continue
                        
                        rows.append({
                            "firma": str(row[c_firma]) if c_rev in df_temp.columns else "Genel",
                            "ulke": str(row[c_ulke]) if c_ulke else "Bilinmiyor",
                            "baslangic_tarihi": start,
                            "bitis_tarihi": end,
                            "ciro": ciro_val,
                            "siparis_adeti": int(pd.to_numeric(row[c_order], errors='coerce')) if c_order else 0,
                            "reklam_harcamasi": pd.to_numeric(row[c_spend], errors='coerce') if c_spend else 0,
                            "reklamli_satis": pd.to_numeric(row[c_sales], errors='coerce') if c_sales else 0,
                            "tacos": (pd.to_numeric(row[c_spend], errors='coerce') / ciro_val) if c_spend and ciro_val > 0 else 0,
                            "kaynak_dosya": file.name
                        })
                    
                    pd.DataFrame(rows).to_sql('reports', engine, if_exists='append', index=False)
                    st.success(f"✅ {file.name} işlendi.")
                except Exception as e:
                    st.error(f"❌ {file.name} hatası: {e}")

    # --- MODÜL: MANUEL GİRİŞ ---
    elif menu == "Manuel Giriş":
        st.header("✍️ Manuel Veri Ekleme")
        with st.form("manual_form"):
            c1, c2, c3 = st.columns(3)
            f_name = c1.selectbox("Firma", ["HomeByHome", "CarpetSale24", "Teppium"])
            u_name = c1.text_input("Ülke (DE, FR vb.)")
            s_date = c2.date_input("Başlangıç")
            e_date = c2.date_input("Bitiş")
            m_ciro = c3.number_input("Ciro (€)", min_value=0.0)
            m_spend = c3.number_input("Reklam (€)", min_value=0.0)
            m_order = c3.number_input("Sipariş", min_value=0)
            
            if st.form_submit_button("Kaydet"):
                new_data = pd.DataFrame([{
                    "firma": f_name, "ulke": u_name, "baslangic_tarihi": s_date, "bitis_tarihi": e_date,
                    "ciro": m_ciro, "siparis_adeti": m_order, "reklam_harcamasi": m_spend,
                    "reklamli_satis": 0, "tacos": (m_spend/m_ciro if m_ciro > 0 else 0), "kaynak_dosya": "Manuel"
                }])
                new_data.to_sql('reports', engine, if_exists='append', index=False)
                st.success("Veri eklendi!")

    # --- MODÜL: YÖNETİM ---
    elif menu == "Veri Yönetimi":
        st.header("⚙️ Veritabanı Kontrolü")
        df_all = pd.read_sql("SELECT * FROM reports", engine)
        st.dataframe(df_all, use_container_width=True)
        if st.button("🔴 Veritabanını Tamamen Boşalt"):
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM reports"))
            st.warning("Tüm veriler silindi.")
            st.rerun()
