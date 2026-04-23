import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# -----------------------------
# LOAD DATA
# -----------------------------
archetypes = pd.read_csv(r"datasets\state_archetypes.csv")
gii = pd.read_csv(r"datasets\state_gii_panel.csv")

df = gii.merge(
    archetypes[['State','Archetype','Cluster_assigned']],
    on='State',
    how='left'
)

numeric_cols = ['GII','Merch_Index','FDI_Index','Tourism_Index']
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

df['Year'] = df['Year'].astype(str)

fdi_fta = pd.read_csv(r"datasets\fdi_fta_merged.csv")
fdi_fta = fdi_fta.replace("NA", pd.NA)
fdi_fta.columns = fdi_fta.columns.str.strip()  
fdi_fta = fdi_fta.rename(columns={'State/UT': 'State'})

fdi_fta = fdi_fta.replace("NA", pd.NA)

fdi_cols = ['FDI_2019','FDI_2020','FDI_2021']
fta_cols = ['FTA_2019','FTA_2020','FTA_2021']

fdi_fta[fdi_cols + fta_cols] = fdi_fta[fdi_cols + fta_cols].apply(
    pd.to_numeric, errors='coerce'
)

commodities = pd.read_csv(r"datasets\commodities_merged.csv")

commodities.columns = commodities.columns.str.strip()


commodities['Top Commodity 1'] = commodities['Top Commodity 1'].str.strip()
commodities['Top Commodity 2'] = commodities['Top Commodity 2'].str.strip()

rows = []

for _, row in commodities.iterrows():
    state = row['State']

    # Top commodity 1
    if pd.notna(row['Top Commodity 1']):
        rows.append({
            'State': state,
            'Product': row['Top Commodity 1'],
            'Type': 'Top 1',
            'Value': row['Value 1']
        })

    # Top commodity 2
    if pd.notna(row['Top Commodity 2']):
        rows.append({
            'State': state,
            'Product': row['Top Commodity 2'],
            'Type': 'Top 2',
            'Value': row['Value 2']
        })

commodity_long = pd.DataFrame(rows)

commodity_long = commodity_long.drop_duplicates(subset=['State','Product'])

app = Dash(__name__)

app.layout = html.Div([

    html.H1("State Global Integration Dashboard", style={'textAlign':'center'}),

    html.Div([
        dcc.Dropdown(
            id='state_filter',
            options=[{'label':s,'value':s} for s in df['State'].unique()],
            multi=True,
            placeholder="Select States"
        ),
        dcc.Dropdown(
            id='archetype_filter',
            options=[{'label':a,'value':a} for a in df['Archetype'].dropna().unique()],
            multi=True,
            placeholder="Select Archetype"
        ),
        dcc.Dropdown(
            id='year_filter',
            options=[{'label':y,'value':y} for y in sorted(df['Year'].unique())],
            value='2021'
        )
    ], style={'display':'flex','gap':'10px'}),

    html.Br(),

    html.Div(id='kpi_cards', style={'display':'flex','gap':'10px'}),

    dcc.Graph(id='bar_chart'),
    dcc.Graph(id='scatter_chart'),
    dcc.Graph(id='stacked_chart'),
    dcc.Graph(id='line_chart'),

    html.H2("FDI & Tourism Trends"),
    dcc.Graph(id='fdi_trend'),
    dcc.Graph(id='fta_trend'),

    html.H2("Export Basket Structure: For Top 2 Commodities"),
    dcc.Graph(id='commodity_chart')
])

@app.callback(
    [
        Output('kpi_cards','children'),
        Output('bar_chart','figure'),
        Output('scatter_chart','figure'),
        Output('stacked_chart','figure'),
        Output('line_chart','figure'),
        Output('fdi_trend','figure'),
        Output('fta_trend','figure'),
        Output('commodity_chart','figure')
    ],
    [
        Input('state_filter','value'),
        Input('archetype_filter','value'),
        Input('year_filter','value')
    ]
)
def update_dashboard(states, archetypes_sel, year):

    dff = df.copy()

    if states:
        dff = dff[dff['State'].isin(states)]
    if archetypes_sel:
        dff = dff[dff['Archetype'].isin(archetypes_sel)]

    dff_year = dff[dff['Year'] == year]

    if dff_year.empty:
        avg_gii = 0
        top_state = "N/A"
        low_state = "N/A"
        common_arch = "N/A"
    else:
        avg_gii = round(dff_year['GII'].mean(),3)
        top_state = dff_year.loc[dff_year['GII'].idxmax(),'State']
        low_state = dff_year.loc[dff_year['GII'].idxmin(),'State']
        common_arch = dff_year['Archetype'].mode().iloc[0]

    kpis = [
        html.Div([html.H4("Avg GII"), html.H2(avg_gii)]),
        html.Div([html.H4("Top State"), html.H2(top_state)]),
        html.Div([html.H4("Lowest State"), html.H2(low_state)]),
        html.Div([html.H4("Dominant Archetype"), html.H2(common_arch)])
    ]

    fig_bar = px.bar(dff_year, x='State', y='GII', color='Archetype')

    fig_scatter = px.scatter(
        dff_year,
        x='FDI_Index',
        y='Merch_Index',
        size=dff_year['Tourism_Index'].fillna(0),
        color='Archetype',
        hover_name='State'
    )

    stacked_df = dff_year.melt(
        id_vars=['State'],
        value_vars=['FDI_Index','Merch_Index','Tourism_Index'],
        var_name='Component',
        value_name='Value'
    )

    fig_stack = px.bar(stacked_df, x='State', y='Value', color='Component')

    fig_line = px.line(df, x='Year', y='GII', color='State')


    fdi_long = fdi_fta.melt(
        id_vars='State',
        value_vars=['FDI_2019','FDI_2020','FDI_2021'],
        var_name='Year',
        value_name='FDI'
    )
    if states:
        fdi_long = fdi_long[fdi_long['State'].isin(states)]
        fta_long = fta_long[fta_long['State'].isin(states)]

    fdi_long['Year'] = fdi_long['Year'].str[-4:]
    fdi_long = fdi_long.dropna(subset=['FDI'])

    fig_fdi = px.line(
        fdi_long,
        x='Year',
        y='FDI',
        color='State',
        title="FDI Inflows by State (USD Million)"
    )


    fta_long = fdi_fta.melt(
        id_vars='State',
        value_vars=['FTA_2019','FTA_2020','FTA_2021'],
        var_name='Year',
        value_name='FTA'
    )
    if states:
        fdi_long = fdi_long[fdi_long['State'].isin(states)]
        fta_long = fta_long[fta_long['State'].isin(states)]
    fta_long['Year'] = fta_long['Year'].str[-4:]
    fta_long = fta_long.dropna(subset=['FTA'])

    fig_fta = px.line(
        fta_long,
        x='Year',
        y='FTA',
        color='State',
        title="Foreign Tourist Arrivals by State"
    )

    commodity_tree = (
        commodity_long.groupby(['Product','State'])
        .size()
        .reset_index(name='Count')
    )

    fig_commodity = px.treemap(
        commodity_tree,
        path=['Product','State'],
        values='Count'
    )
    product_clicked = "N/A"
    

    fig_commodity.update_layout(margin=dict(t=50, l=25, r=25, b=25))
    fig_fdi.update_layout(hovermode='x unified')
    fig_fta.update_layout(hovermode='x unified')

    return kpis, fig_bar, fig_scatter, fig_stack, fig_line, fig_fdi, fig_fta, fig_commodity

server = app.server
if __name__ == '__main__':
    app.run(debug=True)