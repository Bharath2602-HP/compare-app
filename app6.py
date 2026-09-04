import pandas as pd
import streamlit as st

st.set_page_config(page_title="CAD vs BOM Comparator", page_icon="🔍", layout="wide")
st.title("🔍 CAD vs BOM Comparator (with Alternatives)")

# Sidebar upload
st.sidebar.header("Upload Files")
bom_file = st.sidebar.file_uploader("Upload BOM File (Excel/CSV)", type=["xlsx", "csv"])
cad_file = st.sidebar.file_uploader("Upload CAD File (Excel/CSV)", type=["xlsx", "csv"])

def load_file(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file, dtype=str)
    else:
        return pd.read_excel(uploaded_file, dtype=str,engine="openpyxl")

def clean_string(val):
    """Ensure consistent string formatting"""
    return str(val).strip().upper()

def filter_bom_columns(bom_df):
    """Keep only RefDesignator, Component, and Alternative columns"""
    alt_cols = [c for c in bom_df.columns if "Alternative" in c]
    return bom_df[["RefDesignator", "Component"] + alt_cols]

def filter_cad_columns(cad_df):
    """Keep only RefDesignator and Component"""
    return cad_df[["RefDesignator", "Component"]]

def expand_bom(bom_df):
    """Expand BOM into Component–RefDesignator pairs including alternatives"""
    alt_cols = [c for c in bom_df.columns if "Alternative" in c]
    expanded_rows = []
    for _, row in bom_df.iterrows():
        refs = [clean_string(r) for r in str(row["RefDesignator"]).split(",") if r.strip()]
        parts = [clean_string(row["Component"])]
        for col in alt_cols:
            alt_val = row[col]
            if pd.notna(alt_val) and str(alt_val).strip():
                parts.append(clean_string(alt_val))
        for ref in refs:
            for part in parts:
                expanded_rows.append({"RefDesignator": ref, "Component": part})
    return pd.DataFrame(expanded_rows)

if bom_file and cad_file:
    bom_df = load_file(bom_file)
    cad_df = load_file(cad_file)

    # 🔄 Rename BOM column if present
    if "Sort String2" in bom_df.columns:
        bom_df = bom_df.rename(columns={"Sort String2": "RefDesignator"})

    # Keep only needed columns
    bom_df = filter_bom_columns(bom_df)
    cad_df = filter_cad_columns(cad_df)

    # Clean CAD data
    cad_df["RefDesignator"] = cad_df["RefDesignator"].apply(clean_string)
    cad_df["Component"] = cad_df["Component"].apply(clean_string)

    # Clean BOM data
    bom_df["RefDesignator"] = bom_df["RefDesignator"].apply(clean_string)
    bom_df["Component"] = bom_df["Component"].apply(clean_string)
    for col in [c for c in bom_df.columns if "Alternative" in c]:
        bom_df[col] = bom_df[col].apply(lambda x: clean_string(x) if pd.notna(x) else x)

    st.subheader("📋 BOM Preview")
    st.dataframe(bom_df.head(), use_container_width=True)
    st.subheader("📋 CAD Preview")
    st.dataframe(cad_df.head(), use_container_width=True)

    if st.button("Run Comparison", type="primary"):
        bom_expanded = expand_bom(bom_df)

        # Compare CAD vs BOM
        merged = pd.merge(
            cad_df,
            bom_expanded,
            on=["RefDesignator", "Component"],
            how="left",
            indicator=True
        )
        merged["Result"] = merged["_merge"].map({
            "both": "✅ match",
            "left_only": "❌ mismatch (not in BOM/alternatives)"
        })

        # BOM entries missing in CAD
        bom_missing = pd.merge(
            bom_expanded,
            cad_df,
            on=["RefDesignator", "Component"],
            how="left",
            indicator=True
        )
        bom_missing = bom_missing[bom_missing["_merge"] == "left_only"].drop(columns=["_merge"])

        # Show results
        st.markdown("---")
        st.subheader("📊 CAD vs BOM Result Sheet")
        st.dataframe(merged.drop(columns=["_merge"]), use_container_width=True)

        st.subheader("⚠️ BOM/Alternatives Missing in CAD")
        if len(bom_missing) > 0:
            st.dataframe(bom_missing, use_container_width=True)
        else:
            st.success("✅ All BOM components and alternatives are present in CAD!")

        # Summary
        st.markdown("---")
        st.subheader("📊 Summary")
        total = len(cad_df)
        matches = (merged["Result"] == "✅ match").sum()
        mismatches = (merged["Result"] != "✅ match").sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total CAD Entries", total)
        col2.metric("Matches", matches)
        col3.metric("Mismatches", mismatches)
