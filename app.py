import streamlit as st
import yfinance as yf
import pandas as pd

# Configurazione Pagina
st.set_page_config(page_title="Value Scanner MoS", layout="wide")

st.title("🛡️ Stock Value Scanner con Margine di Sicurezza")
st.markdown("""
Questa app calcola il **Fair Value** medio (Graham, DCF, Buffett) e applica un 
**Margine di Sicurezza del 25%** per trovare il prezzo d'ingresso ideale.
""")

# --- FUNZIONE DI RECUPERO DATI ---
def get_val(df, keys):
    if df is None or df.empty:
        return 0
    for k in keys:
        if k in df.index:
            val = df.loc[k]
            return val.iloc[0] if hasattr(val, 'iloc') else val
    return 0

# --- LOGICA DI ANALISI ---
def analyze_ticker(symbol):
    try:
        # Pulizia ticker e download (timeout per evitare blocchi su Streamlit)
        symbol = str(symbol).strip().upper().replace('.', '-')
        stock = yf.Ticker(symbol)
        info = stock.info
        
        if not info or 'currentPrice' not in info:
            return None

        # Dati base
        price = info.get('currentPrice', 0)
        eps = info.get('trailingEps', 0) or 0
        shares = info.get('sharesOutstanding', 1)
        roe = info.get('returnOnEquity', 0) or 0

        # Bilancio per Owner Earnings
        cf = stock.cashflow
        fina = stock.financials
        ni = get_val(fina, ['Net Income', 'Net Income Common Stockholders'])
        dep = get_val(cf, ['Depreciation And Amortization', 'Depreciation'])
        capex = abs(get_val(cf, ['Capital Expenditure', 'CapEx']))
        
        owner_earnings = ni + dep - capex
        oe_per_share = owner_earnings / shares if shares > 0 else 0

        # 1. Metodo Graham (Modificato)
        g = 8.5
        v_graham = eps * (8.5 + 2 * g) if eps > 0 else 0
        
        # 2. Metodo DCF Semplificato (15x FCF)
        fcf = info.get('freeCashflow', owner_earnings) or 0
        v_dcf = (fcf * 15) / shares if shares > 0 else 0
        
        # 3. Metodo Buffett (Owner Earnings Discount)
        v_buffett = oe_per_share / 0.05 if oe_per_share > 0 else 0
        
        # Calcolo Fair Value Medio
        valori = [v for v in [v_graham, v_dcf, v_buffett] if v > 0]
        if not valori: return None
        
        fair_value = sum(valori) / len(valori)
        
        # --- APPLICAZIONE MARGINE DI SICUREZZA (25%) ---
        target_mos = fair_value * 0.75
        sconto_rispetto_fv = ((fair_value - price) / fair_value) * 100

        return {
            "Ticker": symbol,
            "Prezzo Attuale": f"${price:.2f}",
            "Fair Value (Medio)": f"${fair_value:.2f}",
            "Target MoS (-25%)": f"${target_mos:.2f}",
            "Sconto Totale %": round(sconto_rispetto_fv, 1),
            "ROE %": round(roe * 100, 1),
            "Status": "SOTTOVALUTATO" if price <= target_mos else "SOPRAVVALUTATO"
        }
    except:
        return None

# --- SIDEBAR E CARICAMENTO ---
st.sidebar.header("Caricamento Dati")
uploaded_file = st.sidebar.file_uploader("Carica CSV con colonna 'Ticker'", type="csv")

if uploaded_file:
    df_input = pd.read_csv(uploaded_file)
    ticker_col = 'Ticker' if 'Ticker' in df_input.columns else df_input.columns[0]
    tickers = df_input[ticker_col].dropna().unique().tolist()
    
    if st.sidebar.button("🔍 Avvia Analisi"):
        risultati = []
        progress_text = "Analisi in corso. Per favore attendi..."
        my_bar = st.progress(0, text=progress_text)
        
        for i, t in enumerate(tickers):
            res = analyze_ticker(t)
            if res:
                risultati.append(res)
            my_bar.progress((i + 1) / len(tickers), text=f"Analizzando {t}...")
        
        my_bar.empty()

        if risultati:
            df_res = pd.DataFrame(risultati)
            
            # Filtriamo solo quelli con prezzo inferiore o vicino al Target MoS
            st.subheader("📊 Analisi dei Titoli")
            
            def color_status(val):
                color = '#2ecc71' if val == "SOTTOVALUTATO" else '#e74c3c'
                return f'background-color: {color}; color: white; font-weight: bold'

            st.dataframe(df_res.style.applymap(color_status, subset=['Status']))
            
            # Download dei risultati
            csv = df_res.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Scarica Report Completo", csv, "analisi_valore.csv", "text/csv")
        else:
            st.error("Impossibile recuperare dati per i ticker forniti.")
else:
    st.info("💡 Carica un file CSV con una lista di ticker per iniziare l'analisi.")

