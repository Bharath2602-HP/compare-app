import streamlit as st
import pandas as pd

st.title("BOM + CAD Merger Tool")

# Upload files
bom_file = st.file_uploader("Upload BOM file (Excel/CSV)", type=["xlsx", "csv"])
cad_file = st.file_uploader("Upload CAD file (Excel/CSV)", type=["xlsx", "csv"])

if bom_file and cad_file:
    required_cols = ["Component", "Component Material Description", "Sort String All"]

    # Read BOM
    if bom_file.name.endswith(".xlsx"):
        bom_df = pd.read_excel(bom_file)
    else:
        bom_df = pd.read_csv(bom_file)

    # Validate BOM columns
    missing_cols = [col for col in required_cols if col not in bom_df.columns]
    if missing_cols:
        st.error(f"❌ BOM file is missing required columns: {', '.join(missing_cols)}")
    else:
        bom_df = bom_df[required_cols]

        # Read CAD
        if cad_file.name.endswith(".xlsx"):
            cad_df = pd.read_excel(cad_file)
        else:
            cad_df = pd.read_csv(cad_file)

        # Normalize CAD reference designators
        cad_df["Reference Designator"] = cad_df["Reference Designator"].astype(str).str.strip().str.upper()

        # Expand BOM reference designators
        bom_expanded = bom_df.assign(
            ReferenceDesignator=bom_df["Sort String All"].astype(str).str.split(",")
        ).explode("ReferenceDesignator")
        bom_expanded["ReferenceDesignator"] = bom_expanded["ReferenceDesignator"].astype(str).str.strip().str.upper()

        # Merge BOM + CAD
        merged = pd.merge(
            cad_df,
            bom_expanded,
            left_on="Reference Designator",
            right_on="ReferenceDesignator",
            how="inner"
        )

        # Final result
        result = merged[[
            "Reference Designator",
            "Component",
            "Component Material Description",
            "X",
            "Y",
            "Angle"
        ]]
        result.columns = ["Reference Designator", "component", "component Description", "X", "Y", "Angle"]

        # Check mismatches
        bom_refs = set(bom_expanded["ReferenceDesignator"])
        cad_refs = set(cad_df["Reference Designator"])
        missing_in_cad = bom_refs - cad_refs
        missing_in_bom = cad_refs - bom_refs

        if missing_in_cad or missing_in_bom:
            st.error("❌ Mismatch detected between BOM and CAD files!")
            if missing_in_cad:
                st.warning("In BOM but not in CAD: " + ", ".join(sorted([str(x) for x in missing_in_cad])))
            if missing_in_bom:
                st.warning("In CAD but not in BOM: " + ", ".join(sorted([str(x) for x in missing_in_bom])))
        else:
            st.success("✅ All reference designators matched successfully!")

        # Display merged result
        st.subheader("Merged Result (Final Format)")
        st.write(result)

        # Download option
        csv = result.to_csv(index=False).encode("utf-8")
        st.download_button("Download Merged CSV", csv, "merged_result.csv", "text/csv")
