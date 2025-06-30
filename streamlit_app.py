import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import folium
from shapely.geometry import shape
from streamlit_folium import st_folium
import json

st.set_page_config(page_title="Indonesia Education & GDP Dashboard", layout="wide")

# --------------------------
# Sidebar navigation
# --------------------------
page = st.sidebar.selectbox("Navigasi", ["📊 Dashboard", "👤 Tentang Saya"])

if page == "📊 Dashboard":
    # --------------------------
    # 1. Function: Load & Merge Data
    # --------------------------
    @st.cache_data
    def load_data():
        df = pd.read_csv("data/data.csv")
        df.columns = df.columns.str.strip().str.lower()
        df["provinsi"] = df["provinsi"].str.strip().str.lower()

        with open("data/indonesia.geojson", "r", encoding="utf-8") as f:
            gj = json.load(f)

        records = []
        for feat in gj["features"]:
            props = {k.strip().lower(): v for k, v in feat["properties"].items()}
            props["geometry"] = shape(feat["geometry"])
            records.append(props)

        gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
        gdf = gdf.rename(columns={"state": "provinsi"})
        gdf["provinsi"] = gdf["provinsi"].str.strip().str.lower()

        merged = gdf.merge(df, on="provinsi", how="left")
        return merged

    gdf = load_data()

    # --------------------------
    # 2. Header Layout
    # --------------------------
    st.title("📊 Geo-Education & GDP Dashboard Indonesia")
    st.markdown(
        """
    Dashboard ini menyajikan:
    1. **Sebaran GDP** antar provinsi  
    2. **Ketimpangan jenjang pendidikan** berdasarkan Indeks Entropi  
    3. **Korelasi** antara Pendidikan dan GDP
    """
    )

    # --------------------------
    # 3. Peta Interaktif GDP
    # --------------------------
    st.header("🗺️ 1. Peta Interaktif Sebaran GDP")

    gdf_gdp = gdf.dropna(subset=["regional gdp (idr bil)"])

    m_gdp = folium.Map(location=[-2.5, 118], zoom_start=5, tiles="cartodbpositron")

    folium.Choropleth(
        geo_data=gdf_gdp.to_json(),
        data=gdf_gdp,
        columns=["provinsi", "regional gdp (idr bil)"],
        key_on="feature.properties.provinsi",
        fill_color="YlGnBu",
        fill_opacity=0.7,
        line_opacity=0.3,
        legend_name="Regional GDP (Miliar IDR)"
    ).add_to(m_gdp)

    folium.GeoJson(
        gdf_gdp,
        tooltip=folium.GeoJsonTooltip(
            fields=["provinsi", "regional gdp (idr bil)"],
            aliases=["Provinsi:", "GDP (Miliar IDR):"],
            localize=True
        ),
        name="GDP"
    ).add_to(m_gdp)

    st_folium(m_gdp, width=900, height=600)

    # --------------------------
    # 4. Ketimpangan Pendidikan – Entropi
    # --------------------------
    st.header("📚 2. Ketimpangan Pendidikan Antar Provinsi")

    edu_cols = [
        "belum tamat sd", "tamat sd", "smp", "sma",
        "d1 dan d2", "d3", "s1", "s2", "s3"
    ]

    proportion = gdf[edu_cols].div(gdf[edu_cols].sum(axis=1), axis=0)
    proportion = proportion.replace(0, np.nan)
    gdf["edu_entropy"] = -np.nansum(proportion * np.log2(proportion), axis=1)

    st.markdown("Indeks Entropi mengukur pemerataan lulusan pendidikan. Nilai tinggi ⇒ distribusi merata.")

    st.subheader("Peta Interaktif Ketimpangan Pendidikan (Entropi)")
    ent_min, ent_max = 2.1, 2.5
    thresholds = [2.1, 2.2, 2.3, 2.4, 2.5]
    gdf_entropy = gdf.dropna(subset=["edu_entropy"])
    gdf_entropy = gdf_entropy[gdf_entropy["edu_entropy"].between(ent_min, ent_max)]

    m_ent = folium.Map(location=[-2.5, 118], zoom_start=5, tiles="cartodbpositron")

    folium.Choropleth(
        geo_data=gdf_entropy.to_json(),
        data=gdf_entropy,
        columns=["provinsi", "edu_entropy"],
        key_on="feature.properties.provinsi",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.3,
        threshold_scale=thresholds,
        bins=5,
        legend_name="Nilai Entropi (2.1 – 2.5)"
    ).add_to(m_ent)

    folium.GeoJson(
        gdf_entropy,
        tooltip=folium.GeoJsonTooltip(
            fields=["provinsi", "edu_entropy"],
            aliases=["Provinsi:", "Entropi:"],
            localize=True
        ),
        name="Entropi"
    ).add_to(m_ent)

    st_folium(m_ent, width=900, height=600)

    st.subheader("🔝 Provinsi Berdasarkan Pemerataan Pendidikan (Entropi)")
    top_5 = gdf[["provinsi", "edu_entropy"]].sort_values(by="edu_entropy", ascending=False).head(5)
    bottom_5 = gdf[["provinsi", "edu_entropy"]].sort_values(by="edu_entropy", ascending=True).head(5)
    avg_entropy = gdf["edu_entropy"].mean()
    st.metric(label="📊 Rata-Rata Nasional Entropi Pendidikan", value=f"{avg_entropy:.3f}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🟢 Top 5 Pemerataan Pendidikan Tertinggi")
        for _, row in top_5.reset_index(drop=True).iterrows():
            st.markdown(
                f"""<div style='background-color:#e0f7e9; padding:10px; border-radius:10px; margin-bottom:10px'>
                <h5>✅ {row['provinsi'].title()}</h5>
                <p>Entropi: <b>{row['edu_entropy']:.3f}</b></p>
                </div>""",
                unsafe_allow_html=True
            )
        csv_top = top_5.reset_index(drop=True).to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Top 5 (CSV)", csv_top, "top5_entropi.csv", "text/csv")

    with col2:
        st.markdown("#### 🔴 Bottom 5 Pemerataan Pendidikan Terendah")
        for _, row in bottom_5.reset_index(drop=True).iterrows():
            st.markdown(
                f"""<div style='background-color:#ffe0e0; padding:10px; border-radius:10px; margin-bottom:10px'>
                <h5>⚠️ {row['provinsi'].title()}</h5>
                <p>Entropi: <b>{row['edu_entropy']:.3f}</b></p>
                </div>""",
                unsafe_allow_html=True
            )
        csv_bot = bottom_5.reset_index(drop=True).to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Bottom 5 (CSV)", csv_bot, "bottom5_entropi.csv", "text/csv")

    # --------------------------
    # 5. Korelasi Pendidikan vs GDP
    # --------------------------
    st.header("📈 3. Korelasi Pendidikan dan GDP")

    jenjang = st.selectbox("Pilih jenjang pendidikan:", edu_cols)
    gdf["share"] = gdf[jenjang] / gdf[edu_cols].sum(axis=1)

    st.markdown(f"Plot di bawah menunjukkan hubungan antara persentase lulusan **{jenjang.upper()}** dan GDP provinsi:")
    st.scatter_chart(data=gdf, x="share", y="regional gdp (idr bil)", use_container_width=True)

    corr_val = gdf["share"].corr(gdf["regional gdp (idr bil)"])
    st.metric(label=f"Korelasi Pearson (GDP vs {jenjang.upper()})", value=f"{corr_val:.2f}")

elif page == "👤 Tentang Saya":
    st.title("👤 Tentang Saya")
    st.markdown("""
    Halo! Saya Mahardi Setyoso Pratomo, seorang Data Analyst & Geospatial Enthusiast.

    - 🌐 **LinkedIn**: [linkedin.com/feed](https://www.linkedin.com/feed/)
    - 💻 **GitHub**: [github.com/mahardisetyoso](https://github.com/mahardisetyoso?tab=repositories)
    - 📁 **Portofolio Web**: [mahardisetyoso.github.io/data-portofolio-hardy](https://mahardisetyoso.github.io/data-portofolio-hardy/)

    Saya tertarik dengan proyek-proyek data spasial, mobilitas, dan pembangunan wilayah berbasis data.
    """)
