import streamlit as st
import requests
import pandas as pd
import time
import plotly.express as px

# Base de données en mémoire pour les sources d'énergie et la production totale
db_energy = []

# Facteurs d'émission en g par kWh
emission_factors = {
    'bioenergies': 300,
    'hydraulique': 24,
    'diesel': 777,
    'charbon': 986,
    'turbines_a_combustion': 352,
    'photovoltaique': 45,
    'eolien': 11,
    'stockage': 10,
}

color_palette = {
    'turbines_a_combustion': '#954421',
    'bioenergies': '#563C0D',
    'diesel': '#7C3A2D',
    'charbon': '#251605',
    'hydraulique': '#007BFF',
    'photovoltaique': '#F4E409',
    'eolien': '#839918',
    'stockage': '#28a745'
}

# Define the layout of the page as wide
st.set_page_config(layout="wide")


def fetch_data():
    url = 'https://opendata-reunion.edf.fr/api/records/1.0/search/?dataset=prod-electricite-temps-reel&q=&rows=400&sort=date&facet=date'
    response = requests.get(url)
    return response.json()['records']


def process_data(records):
    global db_energy
    new_data_energy = []
    latest_date_in_db = db_energy[-1]['Date'] if db_energy else None

    for record in records:
        fields = record['fields']
        date = fields['date']
        if date == latest_date_in_db:
            break
        new_record_energy = {'Date': date, 'Total': fields['total']}
        for key in emission_factors.keys():
            new_record_energy[key] = max(0, fields[key])

        new_data_energy.append(new_record_energy)

    # Reverse to maintain chronological order
    db_energy.extend(new_data_energy[::-1])
    return pd.DataFrame(db_energy)


def calculate_emissions(data_energy):
    data_emissions = data_energy.copy()
    for key, factor in emission_factors.items():
        data_emissions[key] *= factor  # Use lowercase key
    return data_emissions


def render_metrics_tab(data_energy, current_power_MW, current_emissions_kg):
    # Define columns to display metrics
    col1, col2 = st.columns(2)

    # Metrics displayed as cards
    with col1:
        col1.metric("Puissance Actuelle", f"{current_power_MW:.2f} MW")
    with col2:
        col2.metric("Émissions Actuelles", f"{current_emissions_kg:.2f} kg CO2 / kWh")

    # Creating a DataFrame for the current mix of energy sources
    latest_data = data_energy.iloc[-1]
    current_mix_data = pd.DataFrame({
        'Source': list(emission_factors.keys()),
        'Value': [latest_data[source] for source in emission_factors.keys()]
    })

    # Plotting a pie chart for the current mix
    fig_current_mix = px.pie(current_mix_data, values='Value', names='Source',
                             title='Répartition Actuelle des Sources d\'Énergie',
                             color='Source',
                             color_discrete_map=color_palette)

    # Customize the layout
    fig_current_mix.update_layout(showlegend=True)

    # Displaying the pie chart
    st.plotly_chart(fig_current_mix, use_container_width=True)



def render_energy_sources_tab(data_energy):
    ordered_sources_sum_last_100 = data_energy.drop(columns=['Total', 'Date']).tail(100).sum().sort_values(ascending=False)
    ordered_columns = ['Date'] + [source for source in color_palette.keys() if source in ordered_sources_sum_last_100.index]

    fig_energy = px.area(data_energy[ordered_columns], x='Date', y=ordered_columns[1:],
                         title='Sources d\'Énergie au Fil du Temps',
                         labels={'value': 'Source d\'Énergie'},
                         height=600)

    for trace, source in zip(fig_energy.data, ordered_columns[1:]):
        trace.update(fillcolor=color_palette[source],
                     hovertemplate="<b>Power:</b> %{y} MW<br><b>Time:</b> %{x}<extra></extra>",
                     line=dict(width=0))

    fig_energy.update_layout(
        xaxis_showgrid=True,
        yaxis_showgrid=True,
        xaxis_gridcolor='rgba(128,128,128,0.5)',
        yaxis_gridcolor='rgba(128,128,128,0.5)'
    )

    st.plotly_chart(fig_energy, use_container_width=True)


def render_emissions_tab(data_emissions):
    ordered_columns = ['Date'] + [source for source in color_palette.keys() if source in data_emissions.columns]

    fig_emissions = px.area(data_emissions[ordered_columns], x='Date', y=ordered_columns[1:],
                            title='Émissions au Fil du Temps (g par kWh)',
                            labels={'value': 'Source d\'Émission'},
                            height=600,
                            color_discrete_map=color_palette)

    for trace, source in zip(fig_emissions.data, ordered_columns[1:]):
        trace.update(fillcolor=color_palette[source],
                     hovertemplate="<b>Emission:</b> %{y} g/kWh<br><b>Time:</b> %{x}<extra></extra>",
                     line=dict(width=0))

    fig_emissions.update_layout(
        xaxis_showgrid=True,
        yaxis_showgrid=True,
        xaxis_gridcolor='rgba(128,128,128,0.5)',
        yaxis_gridcolor='rgba(128,128,128,0.5)'
    )

    st.plotly_chart(fig_emissions, use_container_width=True)




def render_total_production_tab(data_energy):
    fig_total_production = px.line(data_energy, x='Date', y='Total',
                                   title='Production Totale au Fil du Temps (MW)',
                                   labels={'Total': 'Production Totale'},
                                   height=600)
    fig_total_production.update_traces(hovertemplate="<b>Production:</b> %{y} MW<br><b>Time:</b> %{x}<extra></extra>")
    fig_total_production.update_layout(
        xaxis_showgrid=True,
        yaxis_showgrid=True,
        xaxis_gridcolor='rgba(128,128,128,0.5)',
        yaxis_gridcolor='rgba(128,128,128,0.5)'
    )

    st.plotly_chart(fig_total_production, use_container_width=True)



def render_storage_hydro_tab(data_energy):
    fig_storage_hydro = px.area(data_energy, x='Date', y='stockage',
                                title='Stockage au Fil du Temps',
                                labels={'value': 'Stockage'},
                                height=600,
                                color_discrete_sequence=[color_palette['stockage']])
    fig_storage_hydro.update_layout(
        xaxis_showgrid=True,
        yaxis_showgrid=True,
        xaxis_gridcolor='rgba(128,128,128,0.5)',
        yaxis_gridcolor='rgba(128,128,128,0.5)'
    )

    st.plotly_chart(fig_storage_hydro, use_container_width=True)


def render_single_source_tab(data_energy):
    st.header("Visualisation d'une Source d'Énergie")
    st.subheader(
        "Choisissez une source d'énergie pour visualiser sa contribution au fil du temps.")

    selected_source = st.selectbox(
        "Sélectionnez une source d'énergie:", list(emission_factors.keys()))

    selected_source_data = data_energy[['Date', selected_source]]

    fig_single_source = px.area(selected_source_data, x='Date', y=selected_source,
                                title=f'{selected_source.capitalize()} au Fil du Temps',
                                labels={'value': 'Source d\'Énergie'},
                                height=600,
                                color_discrete_sequence=[color_palette[selected_source]])
    fig_single_source.update_layout(
        xaxis_showgrid=True,
        yaxis_showgrid=True,
        xaxis_gridcolor='rgba(128,128,128,0.5)',
        yaxis_gridcolor='rgba(128,128,128,0.5)'
    )

    st.plotly_chart(fig_single_source, use_container_width=True)


def render_about_tab():
    st.header("À Propos de ce Tableau de Bord")
    st.write("""
        Ce tableau de bord offre une visualisation en temps réel des sources d'énergie, des émissions et de la production totale d'électricité. Voici une brève explication de chaque onglet :
    """)

    st.subheader("Onglet Mesures")
    st.write("""
        L'onglet Mesures affiche la puissance actuelle et les émissions actuelles en kilogrammes de CO2 par kilowatt-heure. De plus, une répartition en camembert des sources d'énergie actuelles est présentée.
    """)

    st.subheader("Onglet Sources d'Énergie")
    st.write("""
        Cet onglet illustre la répartition des différentes sources d'énergie au fil du temps. Chaque couleur représente une source d'énergie spécifique, et l'aire sous la courbe montre la contribution de cette source.
    """)

    st.subheader("Onglet Émissions")
    st.write("""
        L'onglet Émissions montre les émissions de gaz à effet de serre provenant de chaque source d'énergie au fil du temps. Les émissions sont calculées en grammes de CO2 par kilowatt-heure.
    """)

    st.subheader("Onglet Production Totale")
    st.write("""
        Cet onglet montre la production totale d'électricité au fil du temps en kilowatt-heures. Il offre une vue d'ensemble de la production d'énergie.
    """)

    st.subheader("Onglet Stockage")
    st.write("""
        L'onglet Stockage présente la capacité de stockage d'énergie au fil du temps. Il montre comment l'énergie est stockée et utilisée selon les besoins.
    """)

    st.subheader("Onglet Visualisation d'une Source")
    st.write("""
        Dans cet onglet, vous pouvez choisir une source d'énergie spécifique et visualiser sa contribution au fil du temps. Cela permet une analyse plus détaillée d'une source d'énergie particulière.
    """)

    st.subheader("Données et Mise à Jour")
    st.write("""
        Les données sont récupérées en temps réel et le tableau de bord est mis à jour toutes les 5 minutes. Pour toute question ou commentaire, n'hésitez pas à nous contacter.
    """)



def main():
    st.title('Sources d\'Énergie, Émissions et Production Totale au Fil du Temps')

    # Récupérer et traiter les données pour les sources d'énergie et la production totale
    records = fetch_data()
    data_energy = process_data(records)

    # Calculer les émissions en fonction des sources d'énergie
    data_emissions = calculate_emissions(data_energy)

    # Obtenir les dernières valeurs pour les métriques
    latest_data = data_energy.iloc[-1]
    current_power_MW = latest_data['Total']
    current_emissions_kg = sum(
        latest_data[key] * factor / 1000 for key, factor in emission_factors.items())  # Convertir de g à kg

    # Onglets
    metrics_tab, energy_sources_tab, emissions_tab, total_production_tab, storage_hydro_tab, single_source_tab, about_tab = st.tabs(
        ["Mesures", "Sources d'Énergie", "Émissions", "Production Totale", "Stockage", "Visualisation d'une Source", "À Propos"])

    with metrics_tab:
        render_metrics_tab(data_energy, current_power_MW, current_emissions_kg)

    with energy_sources_tab:
        render_energy_sources_tab(data_energy)

    with emissions_tab:
        render_emissions_tab(data_emissions)

    with total_production_tab:
        render_total_production_tab(data_energy)

    with storage_hydro_tab:
        render_storage_hydro_tab(data_energy)

    with single_source_tab:
        render_single_source_tab(data_energy)

    with about_tab:
        render_about_tab()

    # Actualiser les données toutes les 5 minutes
    time.sleep(300)
    st.experimental_rerun()


if __name__ == '__main__':
    main()