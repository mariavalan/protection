import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

st.set_page_config(
    page_title="Protection Indicators – Evaluation Dashboard",
    layout="wide"
)

# -------------------------------------------------------------------
# DATA LOADING
# -------------------------------------------------------------------
@st.cache_data
def load_data(path: str = "protection_evaluation.xlsx") -> pd.DataFrame:
    """
    Load the Excel file exported from Kobo / XLSForm.
    Path must match the file name in your GitHub repository.
    """
    df = pd.read_excel(path)

    # Basic cleaning
    if "Age :" in df.columns:
        df["Age :"] = pd.to_numeric(df["Age :"], errors="coerce")

    return df


data = load_data()

# mapping of indicator columns by index in your file
INDICATOR_INDEXES = {
    "SDH1": 7,   # Safety during the service
    "SDH2": 9,   # Respectful treatment
    "MEA1": 11,  # Satisfaction
    "MEA2": 13,  # Exclusion from assistance
    "ACC1": 22,  # Knowledge of complaint channels
    "ACC2": 23,  # Response to complaints
    "PEM1": 25,  # Participation / opinions considered
    "PEM2": 27,  # Informed about services
}

INDICATOR_COLUMNS = {k: data.columns[i] for k, i in INDICATOR_INDEXES.items()}

LIKERT_OPTIONS = [
    "Oui, complètement",
    "Plutôt oui",
    "Pas vraiment",
    "Pas du tout",
    "Ne sait pas",
    "Pas de réponse",
]

# -------------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choisir la vue",
    ["1. Tableau de bord", "2. Formulaire d’entretien"]
)

st.sidebar.markdown("---")
st.sidebar.write(
    "Cet outil est destiné à l’analyse interne et à l’apprentissage. "
    "Il ne remplace pas les systèmes officiels de gestion de données."
)

# small helper
def short(text, n=90):
    return text if len(text) <= n else text[: n - 3] + "..."


# -------------------------------------------------------------------
# PAGE 1 – DASHBOARD
# -------------------------------------------------------------------
if page.startswith("1"):

    st.title("Tableau de bord – Évaluation des indicateurs de protection")

    # filters
    st.subheader("Filtres de base")

    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        camps = sorted(data["Camps :"].dropna().unique())
        camp_filter = st.multiselect("Camp", camps, default=camps)

    with col_f2:
        sexes = sorted(data["Sexe :"].dropna().unique())
        sex_filter = st.multiselect("Sexe", sexes, default=sexes)

    with col_f3:
        min_age = int(data["Age :"].min())
        max_age = int(data["Age :"].max())
        age_range = st.slider("Tranche d’âge", min_age, max_age, (min_age, max_age))

    # apply filters
    df = data.copy()
    df = df[df["Camps :"].isin(camp_filter)]
    df = df[df["Sexe :"].isin(sex_filter)]
    df = df[df["Age :"].between(age_range[0], age_range[1])]

    st.caption(f"Nombre d’entretiens dans le filtre actuel : {len(df)}")

    if len(df) == 0:
        st.warning("Aucun enregistrement pour ces filtres. Merci d’élargir la sélection.")
    else:
        # -------------------- key figures --------------------
        st.subheader("Chiffres clés")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total enquêtés", len(df))
        with col2:
            st.metric("Âge moyen", round(df["Age :"].mean(), 1))
        with col3:
            sex_counts = df["Sexe :"].value_counts()
            m = sex_counts.get("Masculin", 0)
            f = sex_counts.get("Féminin", 0)
            st.metric("Sex ratio (H/F)", f"{m}:{f}")
        with col4:
            pbs_yes = df["PBS :"].astype(str).str.contains("Oui", case=False, na=False).mean()
            st.metric("Proportion personnes en situation de handicap (approx.)", f"{round(pbs_yes*100,1)} %")

        # -------------------- demographics --------------------
        st.subheader("Profil démographique")

        c1, c2 = st.columns(2)

        with c1:
            st.write("Répartition par sexe")
            st.bar_chart(df["Sexe :"].value_counts())

        with c2:
            st.write("Histogramme des âges")
            age_chart = (
                alt.Chart(df.dropna(subset=["Age :"]))
                .mark_bar()
                .encode(
                    alt.X("Age :", bin=alt.Bin(maxbins=15), title="Âge"),
                    alt.Y("count()", title="Nombre de personnes"),
                )
                .properties(height=300)
            )
            st.altair_chart(age_chart, use_container_width=True)

        # camp distribution
        st.subheader("Répartition par camp")
        st.bar_chart(df["Camps :"].value_counts())

        # -------------------- indicator visuals --------------------
        st.subheader("Indicateurs de protection")

        indicator_key = st.selectbox(
            "Choisir un indicateur à afficher",
            options=list(INDICATOR_COLUMNS.keys()),
            format_func=lambda k: f"{k} – {short(INDICATOR_COLUMNS[k])}",
        )

        colname = INDICATOR_COLUMNS[indicator_key]

        st.markdown(f"**Question :** {colname}")
        counts = df[colname].value_counts().reindex(LIKERT_OPTIONS).fillna(0)

        indicator_chart = (
            alt.Chart(counts.reset_index())
            .mark_bar()
            .encode(
                x=alt.X("index:N", title="Réponse"),
                y=alt.Y(colname="value:Q", title="Nombre"),
            )
            .properties(height=300)
        )
        st.altair_chart(indicator_chart, use_container_width=True)

        # cross-tab sex vs chosen indicator
        st.subheader("Analyse croisée sexe × indicateur")

        cross = (
            df.groupby(["Sexe :", colname])["Nom"]
            .count()
            .reset_index()
            .rename(columns={"Nom": "count"})
        )

        cross_chart = (
            alt.Chart(cross)
            .mark_bar()
            .encode(
                x=alt.X(colname + ":N", title="Réponse"),
                y=alt.Y("count:Q", title="Nombre"),
                color="Sexe :N",
                column="Sexe :N",
            )
        )
        st.altair_chart(cross_chart, use_container_width=True)

        # raw table
        st.subheader("Tableau des données filtrées")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Télécharger les données filtrées (CSV)",
            data=csv,
            file_name="protection_evaluation_filtre.csv",
            mime="text/csv",
        )

# -------------------------------------------------------------------
# PAGE 2 – QUESTION FORM
# -------------------------------------------------------------------
else:
    st.title("Formulaire d’entretien – Indicateurs de protection")

    st.write(
        "Ce formulaire numérique reprend les principaux éléments de votre outil. "
        "Les réponses saisies ici sont stockées seulement pendant la session en cours."
    )

    if "new_responses" not in st.session_state:
        st.session_state["new_responses"] = []

    with st.form("protection_form"):
        st.subheader("Informations de base")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            nom = st.text_input("Nom (ou code)", "")
        with col_b:
            camp = st.selectbox("Camp", sorted(data["Camps :"].dropna().unique()))
        with col_c:
            sexe = st.selectbox("Sexe", ["Féminin", "Masculin", "Autre / Préfère ne pas dire"])

        col_d, col_e = st.columns(2)
        with col_d:
            age = st.number_input("Âge", min_value=15, max_value=120, value=25, step=1)
        with col_e:
            pbs = st.selectbox("Personne en situation de handicap (PBS)", ["Oui", "Non", "Ne sait pas"])

        st.markdown("---")
        st.subheader("Questions d’indicateurs clés")

        responses = {}
        for code, colname in INDICATOR_COLUMNS.items():
            responses[code] = st.radio(
                f"{code} – {colname}",
                LIKERT_OPTIONS,
                horizontal=True,
            )

        commentaires = st.text_area("Commentaires complémentaires / exemples (optionnel)")

        submitted = st.form_submit_button("Enregistrer l’entretien")

        if submitted:
            new_record = {
                "Nom": nom,
                "Camps :": camp,
                "Sexe :": sexe,
                "Age :": age,
                "PBS :": pbs,
                "submission_time": datetime.utcnow().isoformat(),
                "commentaires": commentaires,
            }
            new_record.update(responses)
            st.session_state["new_responses"].append(new_record)
            st.success("Entretien enregistré dans la session actuelle.")

    # show the new responses table
    st.subheader("Entretiens saisis dans cette session")

    if len(st.session_state["new_responses"]) == 0:
        st.info("Aucun entretien saisi pour le moment.")
    else:
        new_df = pd.DataFrame(st.session_state["new_responses"])
        st.dataframe(new_df, use_container_width=True)

        csv_new = new_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Télécharger les nouveaux entretiens (CSV)",
            data=csv_new,
            file_name="nouveaux_entretiens_protection.csv",
            mime="text/csv",
        )

        st.caption(
            "Attention : ces données ne sont pas fusionnées automatiquement avec le fichier Excel d’origine. "
            "Vous pouvez cependant les télécharger et les joindre manuellement dans Excel ou dans un autre outil."
        )
