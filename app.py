import streamlit as st
import yfinance as yf
import pandas as pd

# Configurazione Pagina
st.set_page_config(page_title="Value Scanner", layout="wide")

st.title("🚀 Stock Intrinsic Value Scanner")
st.sidebar.header("Impostazioni")

# --- FUNZIONE DI RECUPERO DATI ---
def get_val(df, keys):
    if df is None or df.empty:
        return 0
    for k in keys:
        if k in df.index:
            val = df.loc[k]
            return val.iloc[0] if hasattr(val, 'iloc') else val
    return 0

# --- LOGICA DI CALCOLO ---
def analyze_ticker(symbol):
    try:
        stock = yf.Ticker(symbol.strip().upper().replace('.', '-'))
        info = stock.info
        
        if not info or 'currentPrice' not in info:
            return None

        price = info.get('currentPrice', 0)
        roe = info.get('returnOnEquity', 0) or 0
        eps = info.get('trailingEps', 0) or 0
        shares = info.get('sharesOutstanding', 1)

        # Bilancio
        cf = stock.cashflow
        fina = stock.financials
        ni = get_val(fina, ['Net Income', 'Net Income Common Stockholders'])
        dep = get_val(cf, ['Depreciation And Amortization', 'Depreciation'])
        capex = abs(get_val(cf, ['Capital Expenditure', 'CapEx']))
        
        owner_earnings = ni + dep - capex
        oe_per_share = owner_earnings / shares if shares > 0 else 0

        # Valutazioni
        g = 8.5
        v_graham = eps * (8.5 + 2 * g) if eps > 0 else 0
        fcf = info.get('freeCashflow', owner_earnings) or 0
        v_dcf = (fcf * 15) / shares if shares > 0 else 0
        v_buffett = oe_per_share / 0.05 if oe_per_share > 0 else 0
        
        valori = [v for v in [v_graham, v_dcf, v_buffett] if v > 0]
        if not valori: return None
        
        v_medio = sum(valori) / len(valori)
        sconto = ((v_medio - price) / v_medio) * 100

        return {
            "Ticker": symbol,
            "Prezzo ($)": price,
            "Fair Value ($)": round(v_medio, 2),
            "Sconto %": round(sconto, 1),
            "ROE %": round(roe * 100, 1),
            "Owner Earnings": f"{owner_earnings/1e6:.1f}M"
        }
    except:
        return None

# --- INTERFACCIA UTENTE ---
uploaded_file = st.sidebar.file_uploader("Carica il tuo CSV (colonna 'Ticker')", type="csv")

if uploaded_file:
    df_input = pd.read_csv(uploaded_file)
    ticker_col = 'Ticker' if 'Ticker' in df_input.columns else df_input.columns[0]
    tickers = df_input[ticker_col].dropna().unique().tolist()
    
    if st.button("Avvia Analisi"):
        risultati = []
        progress_bar = st.progress(0)
        
        for i, t in enumerate(tickers):
            res = analyze_ticker(t)
            if res:
                risultati.append(res)
            progress_bar.progress((i + 1) / len(tickers))
        
        if risultati:
            df_res = pd.DataFrame(risultati).sort_values(by="Sconto %", ascending=False)
            
            # Evidenzia opportunità (Sconto > 25%)
            st.subheader("✅ Risultati Scanner")
            st.dataframe(df_res.style.highlight_max(subset=['Sconto %'], color='#2ecc71'))
            
            st.download_button("Scarica CSV", df_res.to_csv(index=False), "analisi.csv", "text/csv")
        else:
            st.warning("Nessun dato trovato o criteri non soddisfatti.")
else:
    st.info("Carica un file CSV nella barra laterale per iniziare. Il file deve avere una colonna chiamata 'Ticker'.")
