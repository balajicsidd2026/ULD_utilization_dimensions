# app.py — Constraint-Based Best Fit Decreasing ULD Optimization Web Application

import streamlit as st
import pandas as pd
import json


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="ULD Optimization System",
    layout="wide"
)


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
# SHC ALLOWED ULD TYPES
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
# CHECK SHC COMPATIBILITY
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
# CHECK ALLOWED ULD TYPES
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
# TITLE
# =====================================================

st.title(
    "AI Cargo ULD Allocation System"
)

# =====================================================
# FILE UPLOAD
# =====================================================

awb_file = st.file_uploader(
    "Upload AWB Dataset",
    type=["csv"]
)

uld_file = st.file_uploader(
    "Upload ULD Dataset",
    type=["csv"]
)


# =====================================================
# RUN BUTTON
# =====================================================

if st.button("Run Optimization"):

    if awb_file and uld_file:

        # =============================================
        # LOAD DATASETS
        # =============================================

        awb_df = pd.read_csv(awb_file)
        uld_df = pd.read_csv(uld_file)


        # =============================================
        # VALIDATE FILES
        # =============================================

        if not validate_awb_file(awb_df):
            st.error(
                "Wrong AWB Dataset Uploaded"
            )
            st.stop()

        if not validate_uld_file(uld_df):
            st.error(
                "Wrong ULD Dataset Uploaded"
            )
            st.stop()


        # =============================================
        # CALCULATE VOLUME FROM DIMENSIONS
        # =============================================

        awb_df["Volume_m3"] = (
            awb_df["Length_cm"] *
            awb_df["Width_cm"] *
            awb_df["Height_cm"]
        ) / 1000000


        # =============================================
        # LIMIT EXTREME VOLUME VALUES
        # =============================================

        awb_df["Volume_m3"] = awb_df[
            "Volume_m3"
        ].clip(upper=13.5)


        # =============================================
        # BEST FIT DECREASING SORT
        # =============================================

        awb_df = awb_df.sort_values(
            by=["Weight_kg", "Volume_m3"],
            ascending=False
        ).reset_index(drop=True)


        # =============================================
        # INITIALIZE ULD STATE
        # =============================================

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


        # =============================================
        # FINAL RESULTS
        # =============================================

        allocation_results = []


        # =============================================
        # BEST FIT DECREASING ALLOCATION
        # =============================================

        for _, cargo in awb_df.iterrows():

            awb = cargo["AWB"]
            shc = cargo["SHC"]
            cargo_weight = cargo["Weight_kg"]
            cargo_volume = cargo["Volume_m3"]

            best_uld = None

            minimum_remaining_volume = float("inf")


            # =========================================
            # CHECK ALL ULDs
            # =========================================

            for uld_number, uld_info in uld_state.items():

                uld_type = uld_info["ULD_Type"]


                # =====================================
                # CHECK PREFERRED ULD
                # =====================================

                if not is_uld_allowed(
                    shc,
                    uld_type
                ):
                    continue


                # =====================================
                # CHECK WEIGHT CAPACITY
                # =====================================

                if cargo_weight > uld_info[
                    "Remaining_Weight"
                ]:
                    continue


                # =====================================
                # CHECK VOLUME CAPACITY
                # =====================================

                if cargo_volume > uld_info[
                    "Remaining_Volume"
                ]:
                    continue


                # =====================================
                # CHECK SHC COMPATIBILITY
                # =====================================

                if not is_shc_compatible(
                    uld_info["Loaded_SHC"],
                    shc
                ):
                    continue


                # =====================================
                # BEST FIT LOGIC
                # =====================================

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


            # =========================================
            # FINAL ASSIGNMENT
            # =========================================

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


            # =========================================
            # SAVE RESULTS
            # =========================================

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


        # =============================================
        # CREATE RESULT DATAFRAME
        # =============================================

        result_df = pd.DataFrame(
            allocation_results
        )


        # =============================================
        # CREATE ULD UTILIZATION REPORT
        # =============================================

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

                "Utilized_Weight": round(
                    utilized_weight,
                    2
                ),

                "Remaining_Weight": round(
                    uld_info[
                        "Remaining_Weight"
                    ],
                    2
                ),

                "Weight_Utilization_%": round(
                    weight_utilization,
                    2
                ),

                "Utilized_Volume": round(
                    utilized_volume,
                    2
                ),

                "Remaining_Volume": round(
                    uld_info[
                        "Remaining_Volume"
                    ],
                    2
                ),

                "Volume_Utilization_%": round(
                    volume_utilization,
                    2
                )
            })


        report_df = pd.DataFrame(report_data)

        report_df = report_df.sort_values(
            by="Volume_Utilization_%",
            ascending=False
        )


        # =============================================
        # DISPLAY RESULTS
        # =============================================

        st.success(
            "ULD Optimization Completed"
        )


        st.subheader(
            "ULD Utilization Report"
        )

        st.dataframe(report_df)


        # =============================================
        # EXPORT FILES
        # =============================================

        report_df.to_csv(
            "uld_utilization_report.csv",
            index=False
        )


        # =============================================
        # DOWNLOAD BUTTONS
        # =============================================

        with open(
            "uld_utilization_report.csv",
            "rb"
        ) as f:

            st.download_button(
                label="Download ULD Report CSV",
                data=f,
                file_name="uld_utilization_report.csv"
            )


    else:

        st.warning(
            "Please upload both datasets"
        )
