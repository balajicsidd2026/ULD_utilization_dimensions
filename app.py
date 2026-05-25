# =====================================================
# AI Cargo ULD Allocation System
# Constraint-Based Best Fit Decreasing Algorithm
# =====================================================

import streamlit as st
import pandas as pd
import plotly.express as px


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="ULD Allocation System",
    layout="wide"
)


# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>

.main {
    background-color: #f5f7fb;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}

.big-title {
    font-size: 52px;
    font-weight: 800;
    color: #18214D;
    line-height: 1.3;
    padding-top: 10px;
    padding-bottom: 20px;
}

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 16px;
    border: 1px solid #edf0f7;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.chart-card {
    background: white;
    padding: 20px;
    border-radius: 16px;
    border: 1px solid #edf0f7;
    margin-top: 15px;
    margin-bottom: 15px;
}

/* Shadow wrapper for plotly charts */
[data-testid="stPlotlyChart"] {
    background: white;
    border-radius: 16px;
    border: 1px solid #edf0f7;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    padding: 8px;
    margin-bottom: 8px;
}

.small-label {
    color: gray;
    font-size: 14px;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# SHC INCOMPATIBILITY RULES
# =====================================================

INCOMPATIBLE_SHC = {
    "DGR": ["PER", "AVI", "HUM", "ELI"],
    "PER": ["DGR", "HUM", "RAD"],
    "HUM": ["PER", "DGR", "AVI"],
    "AVI": ["DGR", "RAD", "HUM"],
    "RAD": ["PER", "AVI", "HUM"],
    "WET": ["ELI"],
    "ELI": ["DGR", "WET"]
}


# =====================================================
# SHC ULD RULES
# =====================================================

SHC_ULD_RULES = {
    "PIL": ["RAP", "RKN", "ALF"],
    "COL": ["RAP", "RKN"],
    "RFL": ["RAP", "PMC"],
    "PER": ["RAP", "PMC"],
    "DGR": ["PMC"],
    "AVI": ["AKE"],
    "VAL": ["AKE"],
    "HEA": ["PMC", "PAG"],
    "BIG": ["PMC"],
    "MAG": ["PMC"],
    "EAT": ["PMC", "RAP"],
    "GEN": ["AKE", "PMC"],
    "SPX": ["RAP", "PMC", "AKE", "ALF", "RKN"]
}


# =====================================================
# SHC COMPATIBILITY
# =====================================================

def is_shc_compatible(existing_shcs, new_shc):

    for existing_shc in existing_shcs:

        if new_shc in INCOMPATIBLE_SHC.get(
            existing_shc,
            []
        ):
            return False

        if existing_shc in INCOMPATIBLE_SHC.get(
            new_shc,
            []
        ):
            return False

    return True


# =====================================================
# CHECK ULD TYPE
# =====================================================

def is_uld_allowed(shc, uld_type):

    allowed_uld_types = SHC_ULD_RULES.get(
        shc,
        []
    )

    return uld_type in allowed_uld_types


# =====================================================
# VALIDATE DATASET COLUMNS
# =====================================================

def validate_awb_file(df):

    required_columns = [
        "AWB",
        "SHC",
        "Weight_kg",
        "Length_cm",
        "Width_cm",
        "Height_cm"
    ]

    return all(
        col in df.columns
        for col in required_columns
    )


def validate_uld_file(df):

    required_columns = [
        "ULD_Number",
        "ULD_Type",
        "Max_Weight",
        "Max_Volume_m3"
    ]

    return all(
        col in df.columns
        for col in required_columns
    )


# =====================================================
# HEADER
# =====================================================

st.markdown("""
<h1 class="big-title">
AI Cargo ULD Allocation System
</h1>
""", unsafe_allow_html=True)


# =====================================================
# FILE UPLOAD
# =====================================================

col1, col2 = st.columns(2)

with col1:

    awb_file = st.file_uploader(
        "Upload AWB Dataset",
        type=["csv"]
    )

with col2:

    uld_file = st.file_uploader(
        "Upload ULD Dataset",
        type=["csv"]
    )


# =====================================================
# MAIN CONDITION
# =====================================================

if awb_file and uld_file:

    # =================================================
    # LOAD DATA
    # =================================================

    awb_df = pd.read_csv(awb_file)
    uld_df = pd.read_csv(uld_file)


    # =================================================
    # VALIDATE FILES
    # =================================================

    if not validate_awb_file(awb_df):

        st.error("Invalid AWB file format")
        st.stop()

    if not validate_uld_file(uld_df):

        st.error("Invalid ULD file format")
        st.stop()


    # =================================================
    # CALCULATE VOLUME
    # =================================================

    awb_df["Volume_m3"] = (

        awb_df["Length_cm"] *

        awb_df["Width_cm"] *

        awb_df["Height_cm"]

    ) / 1000000


    awb_df["Volume_m3"] = awb_df[
        "Volume_m3"
    ].clip(upper=13.5)


    # =================================================
    # SORTING
    # =================================================

    awb_df = awb_df.sort_values(

        by=["Weight_kg", "Volume_m3"],

        ascending=False

    ).reset_index(drop=True)


    # =================================================
    # ULD STATE
    # =================================================

    uld_state = {}

    for _, row in uld_df.iterrows():

        uld_number = row["ULD_Number"]

        uld_state[uld_number] = {

            "ULD_Type": row["ULD_Type"],

            "Remaining_Weight": row[
                "Max_Weight"
            ],

            "Remaining_Volume": row[
                "Max_Volume_m3"
            ],

            "Loaded_AWBs": [],

            "Loaded_SHC": []

        }


    # =================================================
    # BEST FIT DECREASING
    # =================================================

    allocation_results = []

    for _, cargo in awb_df.iterrows():

        awb = cargo["AWB"]

        shc = cargo["SHC"]

        cargo_weight = cargo["Weight_kg"]

        cargo_volume = cargo["Volume_m3"]

        best_uld = None

        minimum_remaining_volume = float("inf")


        # =============================================
        # CHECK ULDs
        # =============================================

        for uld_number, uld_info in uld_state.items():

            uld_type = uld_info["ULD_Type"]


            # =========================================
            # CHECK ULD TYPE
            # =========================================

            if not is_uld_allowed(
                shc,
                uld_type
            ):
                continue


            # =========================================
            # WEIGHT CHECK
            # =========================================

            if cargo_weight > uld_info[
                "Remaining_Weight"
            ]:
                continue


            # =========================================
            # VOLUME CHECK
            # =========================================

            if cargo_volume > uld_info[
                "Remaining_Volume"
            ]:
                continue


            # =========================================
            # SHC CHECK
            # =========================================

            if not is_shc_compatible(
                uld_info["Loaded_SHC"],
                shc
            ):
                continue


            # =========================================
            # BEST FIT LOGIC
            # =========================================

            remaining_volume_after_loading = (

                uld_info["Remaining_Volume"]

                - cargo_volume

            )

            if (

                remaining_volume_after_loading

                < minimum_remaining_volume

            ):

                minimum_remaining_volume = (
                    remaining_volume_after_loading
                )

                best_uld = uld_number


        # =============================================
        # FINAL ASSIGNMENT
        # =============================================

        assigned_uld = None

        if best_uld is not None:

            uld_state[best_uld][
                "Remaining_Weight"
            ] -= cargo_weight

            uld_state[best_uld][
                "Remaining_Volume"
            ] -= cargo_volume

            uld_state[best_uld][
                "Loaded_AWBs"
            ].append(awb)

            uld_state[best_uld][
                "Loaded_SHC"
            ].append(shc)

            assigned_uld = best_uld


        allocation_results.append({

            "AWB": awb,

            "SHC": shc,

            "Weight_kg": cargo_weight,

            "Volume_m3": round(
                cargo_volume,
                2
            ),

            "Assigned_ULD": assigned_uld

        })


    # =================================================
    # RESULT DATAFRAME
    # =================================================

    result_df = pd.DataFrame(
        allocation_results
    )


    # =================================================
    # REPORT
    # =================================================

    report_data = []

    for uld_number, uld_info in uld_state.items():

        total_awbs = len(
            uld_info["Loaded_AWBs"]
        )

        utilized_weight = result_df[
            result_df["Assigned_ULD"]
            == uld_number
        ]["Weight_kg"].sum()

        utilized_volume = result_df[
            result_df["Assigned_ULD"]
            == uld_number
        ]["Volume_m3"].sum()

        original_weight = (
            utilized_weight +
            uld_info["Remaining_Weight"]
        )

        original_volume = (
            utilized_volume +
            uld_info["Remaining_Volume"]
        )

        weight_utilization = (
            utilized_weight /
            original_weight
        ) * 100 if original_weight > 0 else 0

        volume_utilization = (
            utilized_volume /
            original_volume
        ) * 100 if original_volume > 0 else 0

        report_data.append({

            "ULD_Number": uld_number,

            "ULD_Type": uld_info[
                "ULD_Type"
            ],

            "Total_AWBs": total_awbs,

            "AWB_List": ", ".join(
                uld_info["Loaded_AWBs"]
            ),

            "Weight_Utilization_%": round(
                weight_utilization,
                2
            ),

            "Volume_Utilization_%": round(
                volume_utilization,
                2
            )

        })


    report_df = pd.DataFrame(report_data)


    # =================================================
    # PAGE NAVIGATION
    # =================================================

    page = st.radio(

        "Select Page",

        [
            "Prediction System",
            "Analytics Dashboard"
        ],

        horizontal=True

    )


    # =================================================
    # PREDICTION SYSTEM
    # =================================================

    if page == "Prediction System":

        st.subheader(
            "ULD Utilization Report"
        )
        sorted_report_df = report_df.sort_values(
            by="Total_AWBs",
            ascending=False
        ).reset_index(drop=True)

        st.dataframe(
            sorted_report_df,
            use_container_width=True
        )

        report_df.to_csv(
            "uld_utilization_report.csv",
            index=False
        )

        with open(
            "uld_utilization_report.csv",
            "rb"
        ) as f:

            st.download_button(
                label="Download ULD Report CSV",
                data=f,
                file_name="uld_utilization_report.csv"
            )


    # =================================================
    # ANALYTICS DASHBOARD
    # =================================================

    if page == "Analytics Dashboard":

        # =============================================
        # KPI VALUES
        # =============================================

        total_awbs_kpi = len(result_df)

        total_uld_kpi = len(report_df)

        avg_uld_utilization = round(
            report_df["Volume_Utilization_%"].mean(), 2
        )

        allocated_awbs = result_df["Assigned_ULD"].notna().sum()

        allocation_rate = round(
            (allocated_awbs / total_awbs_kpi) * 100, 1
        ) if total_awbs_kpi > 0 else 0

        avg_weight_util = round(
            report_df["Weight_Utilization_%"].mean(), 2
        )


        # =============================================
        # KPI CARDS
        # =============================================

        c1, c2, c3= st.columns(3)

        kpi_data = [
            (c1, "Total AWBs", str(total_awbs_kpi), "#3b82f6"),
            (c2, "Total ULDs", str(total_uld_kpi), "#8b5cf6"),
            (c3, "Avg Vol Utilization", f"{avg_uld_utilization}%", "#ef4444"),
        ]

        for col, label, value, color in kpi_data:
            with col:
                st.markdown(f"""
                <div style="
                  background:white;
                  padding:18px 16px;
                  border-radius:14px;
                  border:1px solid #edf0f7;
                  box-shadow:0 2px 8px rgba(0,0,0,0.05);
                  border-top: 4px solid {color};
                ">
                  <div style="color:#6b7280;font-size:13px;font-weight:500;margin-bottom:8px;">{label}</div>
                  <div style="color:#111827;font-size:26px;font-weight:700;">{value}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)


        # =============================================
        # CHARTS ROW  –  SHC Bar | ULD Donut+Table
        # =============================================

        col1, col2 = st.columns([1, 1])


        # =============================================
        # 1. SHC CODE WISE COUNT - Blue bar chart
        # =============================================

        with col1:

            shc_count = awb_df["SHC"].value_counts().reset_index()
            shc_count.columns = ["SHC", "Count"]
            shc_count = shc_count.sort_values("Count", ascending=False)

            fig1 = px.bar(
                shc_count,
                x="SHC",
                y="Count",
                title="1. SHC Code Wise Count",
                text="Count",
            )

            fig1.update_traces(
                marker_color="#2563eb",
                textposition="outside",
                textfont=dict(size=12, color="#1e293b"),
            )

            fig1.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(family="sans-serif", size=13, color="#374151"),
                title=dict(
                    text="1. SHC Code Wise Count",
                    font=dict(size=15, color="#111827", weight="bold"),
                    x=0,
                    xanchor="left",
                ),
                xaxis=dict(
                    title="SHC Code",
                    title_font=dict(size=13, color="#6b7280"),
                    tickfont=dict(size=12),
                    showgrid=False,
                    linecolor="#e5e7eb",
                ),
                yaxis=dict(
                    title="Count",
                    title_font=dict(size=13, color="#6b7280"),
                    showgrid=True,
                    gridcolor="#f3f4f6",
                    tickfont=dict(size=11),
                    zeroline=False,
                ),
                margin=dict(t=50, b=40, l=40, r=20),
                height=420,
            )

            st.plotly_chart(fig1, use_container_width=True)


        # =============================================
        # 2. ULD TYPE WISE COUNT - Donut + Table in one card
        # Strategy: render both into a Plotly figure with
        # the table as a Plotly Table trace on the right
        # =============================================

        with col2:

            uld_count = uld_df["ULD_Type"].value_counts().reset_index()
            uld_count.columns = ["ULD_Type", "Count"]
            total_ulds = uld_count["Count"].sum()
            uld_count["Pct"] = (uld_count["Count"] / total_ulds * 100).round(1)

            DONUT_COLORS = [
                "#2563eb", "#22c55e", "#a855f7",
                "#f97316", "#ef4444", "#eab308",
                "#06b6d4",
            ]

            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            # Build combined figure: donut left, table right
            fig2 = make_subplots(
                rows=1, cols=2,
                column_widths=[0.52, 0.48],
                specs=[[{"type": "domain"}, {"type": "table"}]],
            )

            # Donut trace — explicit domain so annotation can be centered precisely
            PIE_X0, PIE_X1 = 0.0, 0.50
            PIE_Y0, PIE_Y1 = 0.0, 1.0
            PIE_CX = (PIE_X0 + PIE_X1) / 2  # 0.25
            PIE_CY = (PIE_Y0 + PIE_Y1) / 2  # 0.50

            fig2.add_trace(
                go.Pie(
                    labels=uld_count["ULD_Type"].tolist(),
                    values=uld_count["Count"].tolist(),
                    hole=0.55,
                    marker=dict(
                        colors=DONUT_COLORS[:len(uld_count)],
                        line=dict(color="white", width=2),
                    ),
                    textinfo="none",
                    domain=dict(x=[PIE_X0, PIE_X1], y=[PIE_Y0, PIE_Y1]),
                ),
                row=1, col=1,
            )

            # Center annotation — exactly at pie center
            fig2.add_annotation(
                text=f"<b>Total<br>{total_ulds}<br>ULDs</b>",
                x=PIE_CX, y=PIE_CY,
                xref="paper", yref="paper",
                xanchor="center",
                yanchor="middle",
                font=dict(size=14, color="#111827"),
                showarrow=False,
                align="center",
            )

            # Color dots: go.Table doesn't render HTML so we use
            # per-cell font colors + unicode bullet prefix in the label
            uld_labels = uld_count["ULD_Type"].tolist()
            dot_labels = ["  ● " + lbl for lbl in uld_labels]
            dot_colors = [DONUT_COLORS[i % len(DONUT_COLORS)] for i in range(len(uld_count))]

            fig2.add_trace(
                go.Table(
                    columnwidth=[120, 70, 70],
                    header=dict(
                        values=["ULD Type", "Count", "%"],
                        fill_color="white",
                        align=["left", "right", "right"],
                        font=dict(size=12, color="#9ca3af", family="sans-serif"),
                        line_color="#e5e7eb",
                        height=34,
                    ),
                    cells=dict(
                        values=[
                            dot_labels,
                            uld_count["Count"].tolist(),
                            [f"{p}%" for p in uld_count["Pct"].tolist()],
                        ],
                        fill_color="white",
                        align=["left", "right", "right"],
                        font=dict(
                            size=13,
                            family="sans-serif",
                            color=[
                                dot_colors,
                                ["#111827"] * len(uld_count),
                                ["#6b7280"] * len(uld_count),
                            ],
                        ),
                        line_color="#f3f4f6",
                        height=38,
                    ),
                ),
                row=1, col=2,
            )

            fig2.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                title=dict(
                    text="2. ULD Type Wise Count",
                    font=dict(size=15, color="#111827", weight="bold"),
                    x=0,
                    xanchor="left",
                ),
                margin=dict(t=50, b=10, l=10, r=10),
                height=420,
                showlegend=False,
            )

            st.plotly_chart(fig2, use_container_width=True)


        # =================================================
        # 3. ULD → AWB HIERARCHY TREE VIEW
        # =================================================

        st.markdown("""
        <div style="background:white;border-radius:16px;border:1px solid #edf0f7;
        box-shadow:0 2px 8px rgba(0,0,0,0.05);padding:24px;margin-top:8px;margin-bottom:16px;">
          <div style="font-size:17px;font-weight:700;color:#111827;margin-bottom:16px;">
            3. ULD → AWB Hierarchy (Tree View)
          </div>
        """, unsafe_allow_html=True)

        # Sort ULDs by AWB count
        sorted_report_df = report_df.sort_values(by="Total_AWBs", ascending=False)

        selected_uld = st.selectbox(
            "Select ULD",
            sorted_report_df["ULD_Number"]
        )

        selected_data = sorted_report_df[
            sorted_report_df["ULD_Number"] == selected_uld
        ]

        awb_list = selected_data["AWB_List"].values[0]
        awb_items = [x.strip() for x in awb_list.split(",") if x.strip() != ""]
        total_awbs_sel = selected_data["Total_AWBs"].values[0]
        uld_type_sel = selected_data["ULD_Type"].values[0]
        volume_util_sel = selected_data["Volume_Utilization_%"].values[0]

        # Max weight and volume from uld_df
        uld_row = uld_df[uld_df["ULD_Number"] == selected_uld]
        max_weight = uld_row["Max_Weight"].values[0] if len(uld_row) > 0 else "N/A"
        max_volume = uld_row["Max_Volume_m3"].values[0] if len(uld_row) > 0 else "N/A"

        # =============================================
        # LEFT INFO PANEL + RIGHT TREE
        # =============================================

        left_col, right_col = st.columns([1, 4])

        with left_col:

            st.markdown(f"""
            <div style="
              background:#f8fafc;
              border:1px solid #e2e8f0;
              border-radius:14px;
              padding:20px 18px;
            ">
              <div style="font-size:14px;font-weight:700;color:#1e3a8a;
              margin-bottom:16px;letter-spacing:0.02em;">ULD Details</div>
              <table style="width:100%;border-collapse:collapse;">
                <tr>
                  <td style="font-size:12px;color:#6b7280;padding:5px 0;">ULD Type</td>
                  <td style="font-size:12px;color:#111827;font-weight:600;
                  text-align:right;padding:5px 0;">{uld_type_sel}</td>
                </tr>
                <tr>
                  <td style="font-size:12px;color:#6b7280;padding:5px 0;">Max Weight</td>
                  <td style="font-size:12px;color:#111827;font-weight:600;
                  text-align:right;padding:5px 0;">{max_weight:,} kg</td>
                </tr>
                <tr>
                  <td style="font-size:12px;color:#6b7280;padding:5px 0;">Max Volume</td>
                  <td style="font-size:12px;color:#111827;font-weight:600;
                  text-align:right;padding:5px 0;">{max_volume} m³</td>
                </tr>
                <tr>
                  <td style="font-size:12px;color:#6b7280;padding:5px 0;">Utilization (V)</td>
                  <td style="font-size:12px;color:#111827;font-weight:600;
                  text-align:right;padding:5px 0;">{volume_util_sel}%</td>
                </tr>
                <tr>
                  <td style="font-size:12px;color:#6b7280;padding:5px 0;">AWBs Loaded</td>
                  <td style="font-size:12px;color:#111827;font-weight:600;
                  text-align:right;padding:5px 0;">{total_awbs_sel}</td>
                </tr>
              </table>
            </div>
            """, unsafe_allow_html=True)

        with right_col:

            # Parent node
            st.markdown(f"""
            <div style="display:flex;flex-direction:column;align-items:center;margin-bottom:0;">
              <div style="
                background:#dbeafe;
                border:2px solid #3b82f6;
                border-radius:12px;
                padding:14px 36px;
                text-align:center;
                min-width:200px;
                box-shadow:0 2px 8px rgba(59,130,246,0.15);
              ">
                <div style="font-size:16px;font-weight:700;color:#1d4ed8;">
                  {selected_uld} ({uld_type_sel})
                </div>
                <div style="font-size:13px;color:#475569;margin-top:4px;">
                  AWBs: {total_awbs_sel}
                </div>
              </div>

              <!-- Vertical connector -->
              <div style="width:2px;height:32px;background:#cbd5e1;"></div>

              <!-- Horizontal bar spanning children -->
              <div style="position:relative;width:100%;display:flex;justify-content:center;">
                <div style="width:90%;height:2px;background:#cbd5e1;"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Child nodes
            cols_per_row = 4

            for start in range(0, len(awb_items), cols_per_row):

                row_awbs = awb_items[start:start + cols_per_row]
                cols = st.columns(cols_per_row)

                for idx, awb in enumerate(row_awbs):

                    awb_data = result_df[result_df["AWB"] == awb]

                    if len(awb_data) > 0:
                        weight = round(awb_data["Weight_kg"].values[0], 1)
                        volume = round(awb_data["Volume_m3"].values[0], 2)
                    else:
                        weight = 0
                        volume = 0

                    with cols[idx]:
                        st.markdown(f"""
                        <div style="
                          background:white;
                          border:1px solid #e2e8f0;
                          border-radius:12px;
                          padding:14px 12px;
                          text-align:center;
                          box-shadow:0 1px 4px rgba(0,0,0,0.06);
                          margin-top:8px;
                          margin-bottom:8px;
                        ">
                          <div style="
                            font-size:13px;
                            font-weight:700;
                            color:#1e293b;
                            margin-bottom:10px;
                            word-break:break-all;
                          ">{awb}</div>
                          <div style="font-size:12px;color:#64748b;line-height:1.8;">
                            Weight: <b style="color:#111827;">{weight} kg</b><br>
                            Volume: <b style="color:#111827;">{volume} m³</b>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

else:

    st.info(
        "Please upload both datasets"
    )
