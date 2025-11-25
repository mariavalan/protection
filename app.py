import os
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st


# --------------------------------------------------------
# BASIC CONFIG
# --------------------------------------------------------
st.set_page_config(
    page_title="Protection Indicators – Evaluation Dashboard",
    layout="wide",
)

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choose a page",
    ["1. Dashboard", "2. Interview form"],
)

st.sidebar.markdown("---")
st.sidebar.write(
    "This tool is for internal learning and analysis. "
    "It does not replace official information management systems."
)


# --------------------------------------------------------
# DATA LOADING
# --------------------------------------------------------
@st.cache_data
def load_data(path: str = "protection_evaluation.xlsx") -> pd.DataFrame:
    """
    Load the Excel file exported from Kobo.
    The file must be in the same folder as app.py.
    """
    if not os.path.exists(path):
        st.error(
            f"Data file '{path}' was not found. "
            "Please upload the Excel file to the same repository and use this exact name."
        )
        st.stop()

    df = pd.read_excel(path)

    # Clean age column if available
    if "Age :" in df.columns:
        df["Age :"] = pd.to_numeric(df["Age :"], errors="coerce")

    return df


data = load_data()


# --------------------------------------------------------
# INDICATOR COLUMN MAPPING
# (positions based on your file structure)
# --------------------------------------------------------
# If your column order changes later, adjust these indexes
INDICATOR_INDEXES = {
    "SDH1": 7,   # Safety during assistance
    "SDH2": 9,   # Respectful treatment
    "MEA1": 11,  # Satisfaction with assistance
    "MEA2": 13,  # Exclusion from assistance
    "ACC1": 22,  # Knowledge of complaint channels
    "ACC2": 23,  # Response to complaints
    "PEM1": 25,  # Participation and consultation
    "PEM2": 27,  # Information about services
}

# Build a dictionary {short_code: full_column_name}
INDICATOR_COLUMNS = {}
for code, idx in INDICATOR_INDEXES.items():
    if idx < len(data.columns):
        INDICATOR_COLUMNS[code] = data.columns[idx]

# Standard Likert options used in the form
LIKERT_OPTIONS = [
    "Oui, complètement",
    "Plutôt oui",
    "Pas vraiment",
    "Pas du tout",
    "Ne sait pas",
    "Pas de réponse",
]


def short(text: str, n: int = 90) -> str:
    """Shorten long question text for display."""
    return text if len(text) <= n else text[: n - 3] + "..."


# --------------------------------------------------------
# PAGE 1 – DASHBOARD
# --------------------------------------------------------
if page.startswith("1"):
    st.title("Protection indicators – evaluation dashboard")

    # Filters
    st.subheader("Filters")

    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        camps = sorted(data["Camps :"].dropna().unique())
        camp_filter = st.multiselect("Camp", camps, default=camps)

    with col_f2:
        sexes = sorted(data["Sexe :"].dropna().unique())
        sex_filter = st.multiselect("Sex", sexes, default=sexes)

    with col_f3:
        if "Age :" in data.columns:
            min_age = int(data["Age :"].min())
            max_age = int(data["Age :"].max())
            age_range = st.slider(
                "Age range", min_age, max_age, (min_age, max_age)
            )
        else:
            age_range = None

    # Apply filters
    df = data.copy()
    df = df[df["Camps :"].isin(camp_filter)]
    df = df[df["Sexe :"].isin(sex_filter)]
    if age_range is not None:
        df = df[df["Age :"].between(age_range[0], age_range[1])]

    st.caption(f"Number of interviews after filters: {len(df)}")

    if len(df) == 0:
        st.warning("No records match these filters. Please adjust the selection.")
        st.stop()

    # Key figures
    st.subheader("Key figures")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total respondents", len(df))

    with col2:
        if "Age :" in df.columns:
            st.metric("Average age", round(df["Age :"].mean(), 1))
        else:
            st.metric("Average age", "N/A")

    with col3:
        sex_counts = df["Sexe :"].value_counts()
        m = sex_counts.get("Masculin", 0)
        f = sex_counts.get("Féminin", 0)
        st.metric("Sex ratio (M:F)", f"{m}:{f}")

    with col4:
        if "PBS : " in df.columns:
            pbs_col = "PBS : "
        else:
            pbs_col = "PBS :"
        if pbs_col in df.columns:
            pbs_yes = df[pbs_col].astype(str).str.contains(
                "Oui", case=False, na=False
            ).mean()
            st.metric(
                "Persons with disability (approx.)",
                f"{round(pbs_yes * 100, 1)} %",
            )
        else:
            st.metric("Persons with disability", "N/A")

    # Demographic visuals
    st.subheader("Demographic profile")

    col_d1, col_d2 = st.columns(2)

    with col_d1:
        st.write("Sex distribution")
        st.bar_chart(df["Sexe :"].value_counts())

    with col_d2:
        if "Age :" in df.columns:
            st.write("Age distribution")
            age_chart = (
                alt.Chart(df.dropna(subset=["Age :"]))
                .mark_bar()
                .encode(
                    alt.X("Age :", bin=alt.Bin(maxbins=15), title="Age"),
                    alt.Y("count()", title="Number of persons"),
                )
                .properties(height=300)
            )
            st.altair_chart(age_chart, use_container_width=True)
        else:
            st.info("Age column not available in this dataset.")

    st.subheader("Distribution by camp")
    st.bar_chart(df["Camps :"].value_counts())

    # Indicator visuals
    st.subheader("Protection indicator view")

    if not INDICATOR_COLUMNS:
        st.warning("Indicator columns could not be mapped. Please review column indexes.")
    else:
        indicator_key = st.selectbox(
            "Select an indicator",
            options=list(INDICATOR_COLUMNS.keys()),
            format_func=lambda k: f"{k} – {short(INDICATOR_COLUMNS[k])}",
        )

        colname = INDICATOR_COLUMNS[indicator_key]

        st.markdown(f"**Question:** {colname}")

        counts = (
            df[colname]
            .value_counts()
            .reindex(LIKERT_OPTIONS)
            .fillna(0)
            .astype(int)
        )

        chart = (
            alt.Chart(counts.reset_index())
            .mark_bar()
            .encode(
                x=alt.X("index:N", title="Response"),
                y=alt.Y(colname="value:Q", title="Number of respondents"),
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)

        st.subheader("Sex disaggregation for this indicator")

        cross = (
            df.groupby(["Sexe :", colname])
            .size()
            .reset_index(name="count")
        )

        cross_chart = (
            alt.Chart(cross)
            .mark_bar()
            .encode(
                x=alt.X(colname + ":N", title="Response"),
                y=alt.Y("count:Q", title="Number"),
                color="Sexe :N",
                column="Sexe :N",
            )
        )
        st.altair_chart(cross_chart, use_container_width=True)

    # Data table and download
    st.subheader("Filtered data table")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered data (CSV)",
        data=csv,
        file_name="protection_evaluation_filtered.csv",
        mime="text/csv",
    )


# --------------------------------------------------------
# PAGE 2 – INTERVIEW FORM
# --------------------------------------------------------
else:
    st.title("Interview form – protection indicators")

    st.write(
        "This simple digital form mirrors the key protection questions. "
        "Data entered here are kept only during the current Streamlit session."
    )

    if "new_responses" not in st.session_state:
        st.session_state["new_responses"] = []

    with st.form("protection_form"):
        st.subheader("Basic information")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            nom = st.text_input("Name or code of respondent", "")
        with col_b:
            camps = sorted(data["Camps :"].dropna().unique())
            camp = st.selectbox("Camp", camps)
        with col_c:
            sexe = st.selectbox(
                "Sex",
                ["Féminin", "Masculin", "Other or prefer not to say"],
            )

        col_d, col_e = st.columns(2)
        with col_d:
            age = st.number_input(
                "Age", min_value=15, max_value=120, value=25, step=1
            )
        with col_e:
            pbs = st.selectbox(
                "Person with disability (self reported)",
                ["Oui", "Non", "Ne sait pas"],
            )

        st.markdown("---")
        st.subheader("Key indicator questions")

        responses = {}
        if not INDICATOR_COLUMNS:
            st.warning("Indicator columns are not mapped. Please adjust the index mapping in the code.")
        else:
            for code, colname in INDICATOR_COLUMNS.items():
                responses[code] = st.radio(
                    f"{code} – {colname}",
                    LIKERT_OPTIONS,
                    horizontal=True,
                )

        comments = st.text_area(
            "Additional comments or examples (optional)"
        )

        submitted = st.form_submit_button("Save interview")

        if submitted:
            new_record = {
                "Nom": nom,
                "Camps :": camp,
                "Sexe :": sexe,
                "Age :": age,
                "PBS :": pbs,
                "submission_time": datetime.utcnow().isoformat(),
                "comments": comments,
            }
            new_record.update(responses)
            st.session_state["new_responses"].append(new_record)
            st.success("Interview saved in the current session.")

    st.subheader("Interviews entered in this session")

    if len(st.session_state["new_responses"]) == 0:
        st.info("No interviews recorded yet.")
    else:
        new_df = pd.DataFrame(st.session_state["new_responses"])
        st.dataframe(new_df, use_container_width=True)

        csv_new = new_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download new interviews (CSV)",
            data=csv_new,
            file_name="new_protection_interviews.csv",
            mime="text/csv",
        )

        st.caption(
            "Note: these new interviews are not merged automatically with the original Excel file. "
            "You can download them and join them manually in Excel or another tool."
        )
