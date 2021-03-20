#
#
import settings # Import related setting constants from settings.py 
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.graph_objs as go
import settings
import itertools
import math
import base64
from flask import Flask
import os
from sqlalchemy import create_engine
import datetime
 
import re
import nltk
nltk.download('punkt')
nltk.download('stopwords')
from nltk.probability import FreqDist
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from textblob import TextBlob

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

today = datetime.datetime.now().strftime("%B %d, %Y")

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = 'Monitor de Twitter en Tiempo real'

app.layout = html.Div(children=[
    html.H2('Análisis de Sentimiento de Twitter en Tiempo real para Seguimiento Temático', style={
        'textAlign': 'center'
    }),
    html.H4('(Última actualización: {})'.format(today), style={
        'textAlign': 'right'
    }),
    
    html.Div(id='live-update-graph'),
    html.Div(id='live-update-graph-bottom'),
    
    # ABOUT ROW
    html.Div(
        className='row',
        children=[
            html.Div(
                className='three columns',
                children=[
                    html.P(
                    'Datos extraídos de:'
                    ),
                    html.A(
                        'API de Twitter ',
                        href='https://developer.twitter.com'
                    )                    
                ]
            ),
            html.Div(
                className='three columns',
                children=[
                    html.P(
                    'Código disponible en:'
                    ),
                    html.A(
                        'GitHub',
                        href='https://github.com/felipeescallon/Analisis-Sentimiento-Twitter-Tiempo-real-Seguimiento-vacunas-Hispanoamerica'
                    )                    
                ]
            ),
            html.Div(
                className='three columns',
                children=[
                    html.P(
                    'Hecho con:'
                    ),
                    html.A(
                        'Dash (by Plot.ly)',
                        href='https://plot.ly/dash/'
                    )                    
                ]
            ),
            html.Div(
                className='three columns',
                children=[
                    html.P(
                    'Autor:'
                    ),
                    html.A(
                        'Andres Felipe Escallon Portilla (basado y adaptado de la app original de Chulong Li)',
                        href='https://www.linkedin.com/in/andres-felipe-escallon-portilla/?locale=en_US'
                    )                    
                ]
            )                                                          
        ], style={'marginLeft': 70, 'fontSize': 16}
    ),

    dcc.Interval(
        id='interval-component-slow',
        interval=1*10000, # in milliseconds (it keeps constantly updating itself)
        n_intervals=0
    )
    ], style={'padding': '20px'})



# Multiple components can update everytime interval gets fired.
@app.callback(Output('live-update-graph', 'children'),
              [Input('interval-component-slow', 'n_intervals')])
def update_graph_live(n):
    # Loading data from RDS PostgreSQL
    #engine = create_engine('postgresql://postgres:password@host:5432/database')#conexion a la base de datos
    #engine = create_engine('postgresql://postgres:postgres@***AWS-RDS***:5432/twitterdb')#conexion a la base de datos
    
    #DATABASE connection (twitterdb2 is a table inside uao_team18):
    host = 'xxxx'                                                                 #AWS RDS instance
    port = 5432                                                                   #default port
    user = 'xxxx'                                                                 #database user
    password = 'xxxx'                                                             #database password
    database = 'xxxx'                                                             #database name
    engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{database}')  #database connection (only once)


    
    query = "SELECT id_str, text, created_at, polarity, user_location, user_followers_count FROM {}".format(settings.TABLE_NAME)
    df = pd.read_sql(query,engine)
    print("1 df:\n", df.head())
    # Convert UTC into GMT-5 (GMT-5=UTC-5) for Colombian time
    df['created_at'] = pd.to_datetime(df['created_at']).apply(lambda x: x - datetime.timedelta(hours=5)) # UTC-5 = GMT-5 (Local time in Bogotá-Colombia)

    # Clean and transform data to enable time series
    result = df.groupby([pd.Grouper(key='created_at', freq='10s'), 'polarity']).count().unstack(fill_value=0).stack().reset_index()
    result = result.rename(columns={"id_str": "Num of '{}' mentions".format(settings.TRACK_WORDS[0]), "created_at":"Time"}) 
    print("2 result:\n",result.head())
    time_series = result["Time"][result['polarity']==0].reset_index(drop=True)
    print("3 time_series df:\n",time_series.head())

    min10 = datetime.datetime.now() - datetime.timedelta(hours=5, minutes=10) # UTC-5 = GMT-5 (Local time in Bogotá-Colombia)
    min20 = datetime.datetime.now() - datetime.timedelta(hours=5, minutes=20) # UTC-5 = GMT-5 (Local time in Bogotá-Colombia)

    neu_num = result[result['Time']>min10]["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==0].sum()
    print("4 neu_num:\n",neu_num)
    neg_num = result[result['Time']>min10]["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==-1].sum()
    print("5 neg_num:\n",neg_num)
    pos_num = result[result['Time']>min10]["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==1].sum()
    print("6 pos_num:\n",pos_num)
    
    # Loading back-up summary data
    # This table must be created before in PgAdmin (it is not the same as twitter2, it is in fact an aux table to show results transformed from the twitter2 table):
    #REMEMBER fill zeros in the columns of backup2 after creation, as a query in PgAdmin, like this:
    #INSERT INTO backup2 VALUES (0,0,0);
    #ASI LUEGO LA SQL DE REINICIO PERIODICO "UPDATE backup2 SET daily_tweets_num = 0, impressions = 0;" O LA SQL QUE LLENA VALORES,FUNCIONARÁ!
    #accesing the backup2 table via the database on AWS RDS (uao_team18):
      
    #DATABASE connection (the backup2 table is inside uao_team18):#now the backup table is named " backup2"
    #host = 'xxxxxx'                         #AWS RDS instance
    #port = 5432                                                                     #default port
    #user = 'xxxxxx'                                                                 #database user
    #password = 'xxxxxx'                                                             #database password
    #database = 'xxxxxx'                                                             #database name
    #engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{database}')  #database connection (only once)
    
    query = "SELECT daily_user_num, daily_tweets_num, impressions FROM backup2;" #now the backup table is named " backup2"
    back_up = pd.read_sql(query, engine)
    print("4 back_up:\n", back_up.head())
    daily_tweets_num = back_up['daily_tweets_num'].iloc[0] + result[-6:-3]["Num of '{}' mentions".format(settings.TRACK_WORDS[0])].sum()
    print("5 daily_tweets_num:\n", daily_tweets_num)
    daily_impressions = back_up['impressions'].iloc[0] + df[df['created_at'] > (datetime.datetime.now() - datetime.timedelta(hours=5, seconds=10))]['user_followers_count'].sum() # UTC-5 = GMT-5 (Local time in Bogotá-Colombia)
    print("6 daily_impressions:\n",daily_impressions)
    
    engine.connect()
    mydb = engine.raw_connection()
    mycursor = mydb.cursor()

    PDT_now = datetime.datetime.now() - datetime.timedelta(hours=5) # PDT_now is UTC-5 = GMT-5 (Local time in Bogotá-Colombia)
    if PDT_now.strftime("%H%M")=='0000': #erasing the previous dey data at this breaking point to start over with the following day
        mycursor.execute("UPDATE backup2 SET daily_tweets_num = 0, impressions = 0;")
    else:
        mycursor.execute("UPDATE backup2 SET daily_tweets_num = {}, impressions = {};".format(daily_tweets_num, daily_impressions))
    mydb.commit()
    mycursor.close()
    mydb.close()

    # Percentage Number of Tweets changed in Last 10 mins
    count_now = df[df['created_at'] > min10]['id_str'].count()
    count_before = df[ (min20 < df['created_at']) & (df['created_at'] < min10)]['id_str'].count()

    if count_before == 0:
        count_before = 24000 #just an average number to start and avoid dividing by zero!

    percent = (count_now-count_before)/count_before*100

    # Create the graph 
    print("Percent: ", percent)
    children = [
                html.Div([
                    html.Div([
                        dcc.Graph(
                            id='crossfilter-indicator-scatter',
                            figure={
                                'data': [
                                    go.Scatter(
                                        x=time_series,
                                        y=result["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==0].reset_index(drop=True),
                                        name="Neutrales",
                                        opacity=0.8,
                                        mode='lines',
                                        line=dict(width=0.5, color='rgb(131, 90, 241)'),
                                        stackgroup='one' 
                                    ),
                                    go.Scatter(
                                        x=time_series,
                                        y=result["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==-1].reset_index(drop=True).apply(lambda x: -x),
                                        name="Negativos",
                                        opacity=0.8,
                                        mode='lines',
                                        line=dict(width=0.5, color='rgb(255, 50, 50)'),
                                        stackgroup='two' 
                                    ),
                                    go.Scatter(
                                        x=time_series,
                                        y=result["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==1].reset_index(drop=True),
                                        name="Positivos",
                                        opacity=0.8,
                                        mode='lines',
                                        line=dict(width=0.5, color='rgb(184, 247, 212)'),
                                        stackgroup='three' 
                                    )
                                ]
                            }
                        )
                    ], style={'width': '73%', 'display': 'inline-block', 'padding': '0 0 0 20'}),
                    
                    html.Div([
                        dcc.Graph(
                            id='pie-chart',
                            figure={
                                'data': [
                                    go.Pie(
                                        labels=['Positivos', 'Negativos', 'Neutrales'], 
                                        values=[pos_num, neg_num, neu_num],
                                        name="Ver Metricas",
                                        marker_colors=['rgba(184, 247, 212, 0.6)','rgba(255, 50, 50, 0.6)','rgba(131, 90, 241, 0.6)'],
                                        textinfo='value',
                                        hole=.65)
                                ],
                                'layout':{
                                    'showlegend':False,
                                    'title':'Tweets en los últimos 10 min',
                                    'annotations':[
                                        dict(
                                            text='{0:.1f}K'.format((pos_num+neg_num+neu_num)/1000),
                                            font=dict(
                                                size=40
                                            ),
                                            showarrow=False
                                        )
                                    ]
                                }

                            }
                        )
                    ], style={'width': '27%', 'display': 'inline-block'})
                ]),
                
                html.Div(
                    className='row',
                    children=[
                        html.Div(
                            children=[
                                html.P("'%' de cambio de Tweets (últimos 10 min)",
                                    style={
                                        'fontSize': 17
                                    }
                                ),
                                html.P('{0:.2f}%'.format(percent) if percent <= 0 else '+{0:.2f}%'.format(percent),
                                    style={
                                        'fontSize': 40
                                    }
                                )
                            ], 
                            style={
                                'width': '20%', 
                                'display': 'inline-block'
                            }

                        ),
                        html.Div(
                            children=[
                                html.P('Impresiones Potenciales Hoy',
                                    style={
                                        'fontSize': 17
                                    }
                                ),
                                html.P('{0:.1f}K'.format(daily_impressions/1000) \
                                        if daily_impressions < 1000000 else \
                                            ('{0:.1f}M'.format(daily_impressions/1000000) if daily_impressions < 1000000000 \
                                            else '{0:.1f}B'.format(daily_impressions/1000000000)),
                                    style={
                                        'fontSize': 40
                                    }
                                )
                            ], 
                            style={
                                'width': '20%', 
                                'display': 'inline-block'
                            }
                        ),
                        html.Div(
                            children=[
                                html.P('Tweets Publicados Hoy',
                                    style={
                                        'fontSize': 17
                                    }
                                ),
                                html.P('{0:.1f}K'.format(daily_tweets_num/1000),
                                    style={
                                        'fontSize': 40
                                    }
                                )
                            ], 
                            style={
                                'width': '20%', 
                                'display': 'inline-block'
                            }
                        ),

                        html.Div(
                            children=[
                                html.P("Actualmente haciendo seguimiento a \"vacunas\" en Twitter  (UTC-5: Hora de Colombia).",
                                    style={
                                        'fontSize': 22
                                    }
                                ),
                            ], 
                            style={
                                'width': '40%', 
                                'display': 'inline-block'
                            }
                        ),

                    ],
                    style={'marginLeft': 70}
                )
            ]
    return children

@app.callback(Output('live-update-graph-bottom', 'children'),
              [Input('interval-component-slow', 'n_intervals')])
def update_graph_bottom_live(n):

    # Loading data from RDS PostgreSQL
    #engine = create_engine('postgresql://postgres:password@host:5432/database')#conexion a la base de datos
    #engine = create_engine('postgresql://postgres:postgres@***AWS-RDS***:5432/twitterdb')#conexion a la base de datos
    
    #DATABASE connection (twitterdb2 is a table inside uao_team18):
    host = 'xxxx'                                                                 #AWS RDS instance
    port = 5432                                                                   #default port
    user = 'xxxx'                                                                 #database user
    password = 'xxxx'                                                             #database password
    database = 'xxxx'                                                             #database name
    engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{database}')  #database connection (only once)

        
    query = "SELECT id_str, text, created_at, polarity, user_location FROM {}".format(settings.TABLE_NAME)
    df = pd.read_sql(query, engine)

    # Convert UTC into GMT-5 (GMT-5=UTC-5), Bogotá-Colombia time
    df['created_at'] = pd.to_datetime(df['created_at']).apply(lambda x: x - datetime.timedelta(hours=5))

    # Clean and transform data to enable word frequency
    content = ' '.join(df["text"])
    content = re.sub(r"http\S+", "", content)
    content = content.replace('RT ', ' ').replace('&amp;', 'and')
    content = re.sub('[^A-Za-z0-9]+', ' ', content)
    content = content.lower()
 
    #SE PODRIA TRABAJAR CON EL MAPA DE COLOMBIA POR EJEMPLO (o hacer un filtro adicional para desplegar el mapa del país deseado)
    #¡Trabajaré con el mapa de países HISPANOHABLANTES

    # Filter constants for states in Hispanoamérica
    #STATES = ['Alabama', 'AL', 'Alaska', 'AK', 'American Samoa', 'AS', 'Arizona', 'AZ', 'Arkansas', 'AR', 'California', 'CA', 'Colorado', 'CO', 'Connecticut', 'CT', 'Delaware', 'DE', 'District of Columbia', 'DC', 'Federated States of Micronesia', 'FM', 'Florida', 'FL', 'Georgia', 'GA', 'Guam', 'GU', 'Hawaii', 'HI', 'Idaho', 'ID', 'Illinois', 'IL', 'Indiana', 'IN', 'Iowa', 'IA', 'Kansas', 'KS', 'Kentucky', 'KY', 'Louisiana', 'LA', 'Maine', 'ME', 'Marshall Islands', 'MH', 'Maryland', 'MD', 'Massachusetts', 'MA', 'Michigan', 'MI', 'Minnesota', 'MN', 'Mississippi', 'MS', 'Missouri', 'MO', 'Montana', 'MT', 'Nebraska', 'NE', 'Nevada', 'NV', 'New Hampshire', 'NH', 'New Jersey', 'NJ', 'New Mexico', 'NM', 'New York', 'NY', 'North Carolina', 'NC', 'North Dakota', 'ND', 'Northern Mariana Islands', 'MP', 'Ohio', 'OH', 'Oklahoma', 'OK', 'Oregon', 'OR', 'Palau', 'PW', 'Pennsylvania', 'PA', 'Puerto Rico', 'PR', 'Rhode Island', 'RI', 'South Carolina', 'SC', 'South Dakota', 'SD', 'Tennessee', 'TN', 'Texas', 'TX', 'Utah', 'UT', 'Vermont', 'VT', 'Virgin Islands', 'VI', 'Virginia', 'VA', 'Washington', 'WA', 'West Virginia', 'WV', 'Wisconsin', 'WI', 'Wyoming', 'WY']
    '''PAÍSES HISPANOHABLANTES POR ZONAS GEOGRÁFICAS:
    http://www.editorialox.com/21paises.htm#:~:text=Pa%C3%ADses%20hispanohablantes%20donde%20el%20espa%C3%B1ol,Venezuela%2C%20Espa%C3%B1a%20y%20Guinea%20Ecuatorial.

    América del Norte: México
    América Central: Costa Rica, El Salvador, Guatemala, Honduras, Nicaragua, Panamá
    El Caribe: Cuba, Puerto Rico, República Dominicana
    América del Sur: Argentina, Bolivia, Chile, Colombia, Ecuador, Paraguay, Perú, Uruguay, Venezuela
    Europa: España
    África: Guinea Ecuatorial
    '''
    STATES=['Mexico','MEX','Costa Rica','COS','El Salvador','ELS','Guatemala','GUA','Honduras','HON','Nicaragua','NIC','Panama','PAN','Cuba','CUB','Puerto Rico','PUE','Republica Dominicana','REP','Argentina','ARG','Bolivia','BOL','Chile','CHI','Colombia','COL','Ecuador','ECU','Paraguay','PAR','Peru','PER','Uruguay','URU','Venezuela','VEN','Spain','SPA','Guinea Ecuatorial','GUI']
    
    # turning the above list into a dictionary
    STATE_DICT = dict(itertools.zip_longest(*[iter(STATES)] * 2, fillvalue=""))
    print('STATE_DICT:', STATE_DICT)
    INV_STATE_DICT = dict((v,k) for k,v in STATE_DICT.items())
    print('INV_STATE_DICT:', INV_STATE_DICT)

    # Clean and transform data to enable geo-distribution
    is_in_HIS=[] #HIS=HISPANOAMERICA
    geo = df[['user_location']]
    df = df.fillna(" ")
    print("geo = df[['user_location']]:",geo)
    for x in df['user_location']:
        check = False
        for s in STATES:
            if s in x:
                is_in_HIS.append(STATE_DICT[s] if s in STATE_DICT else s)
                check = True
                break
        if not check:
            is_in_HIS.append(None)


    print('is_in_HIS:',is_in_HIS)
    geo_dist = pd.DataFrame(is_in_HIS, columns=['State']).dropna().reset_index()
    geo_dist = geo_dist.groupby('State').count().rename(columns={"index": "Number"}) \
        .sort_values(by=['Number'], ascending=False).reset_index()
    geo_dist["Log Num"] = geo_dist["Number"].apply(lambda x: math.log(x, 2))


    geo_dist['Full State Name'] = geo_dist['State'].apply(lambda x: INV_STATE_DICT[x])
    geo_dist['text'] = geo_dist['Full State Name'] + '<br>' + 'Num: ' + geo_dist['Number'].astype(str)
    print('geo_dist:',geo_dist)

    tokenized_word = word_tokenize(content)
    stop_words=set(stopwords.words("spanish"))# se puede cambiar de idioma dependiendo del país escogido (en este caso Español: spanish)
    filtered_sent=[]
    for w in tokenized_word:
        if (w not in stop_words) and (len(w) >= 3):
            filtered_sent.append(w)
    fdist = FreqDist(filtered_sent)
    fd = pd.DataFrame(fdist.most_common(16), columns = ["Word","Frequency"]).drop([0]).reindex()
    fd['Polarity'] = fd['Word'].apply(lambda x: TextBlob(x).sentiment.polarity)
    fd['Marker_Color'] = fd['Polarity'].apply(lambda x: 'rgba(255, 50, 50, 0.6)' if x < -0.1 else \
        ('rgba(184, 247, 212, 0.6)' if x > 0.1 else 'rgba(131, 90, 241, 0.6)'))
    fd['Line_Color'] = fd['Polarity'].apply(lambda x: 'rgba(255, 50, 50, 1)' if x < -0.1 else \
        ('rgba(184, 247, 212, 1)' if x > 0.1 else 'rgba(131, 90, 241, 1)'))



    # Create the graph 
    children = [
                html.Div([
                    dcc.Graph(
                        id='x-time-series',
                        figure = {
                            'data':[
                                go.Bar(                          
                                    x=fd["Frequency"].loc[::-1],
                                    y=fd["Word"].loc[::-1], 
                                    name="Neutrales", 
                                    orientation='h',
                                    marker_color=fd['Marker_Color'].loc[::-1].to_list(),
                                    marker=dict(
                                        line=dict(
                                            color=fd['Line_Color'].loc[::-1].to_list(),
                                            width=1),
                                        ),
                                )
                            ],
                            'layout':{
                                'hovermode':"closest"
                            }
                        }        
                    )
                ], style={'width': '49%', 'display': 'inline-block', 'padding': '0 0 0 20'}),
                html.Div([
                    dcc.Graph(
                        id='y-time-series',
                        figure = {
                            'data':[
                                go.Choropleth(
                                    #locations=geo_dist['State'], # Spatial coordinates
                                    locations=geo_dist['Full State Name'], # Spatial coordinates (FUNCIONÓ!!!)
                                    #locations=['Mexico','Costa Rica','El Salvador','Guatemala','Honduras','Nicaragua','Panama','Cuba','Puerto Rico','Republica Dominicana','Argentina','Bolivia','Chile','Colombia','Ecuador','Paraguay','Peru','Uruguay','Venezuela','Spain','Guinea Ecuatorial'], # Spatial coordinates
                                    z = geo_dist['Log Num'].astype(float), # Data to be color-coded
                                    #locationmode = 'USA-states', # set of locations match entries in `locations`
                                    #locationmode = 'Colombia', # set of locations match entries in `locations` (NO FUNCIONÓ!!!)
                                    #The 'locationmode' property is an enumeration that may be specified as:
                                    #- One of the following enumeration values:
                                    #['ISO-3', 'USA-states', 'country names', 'geojson-id']
                                    locationmode = 'country names', # set of locations match entries in `locations`
                                    #locationmode = 'ISO-3', # set of locations match entries in `locations`
                                    #locationmode = 'geojson-id', # set of locations match entries in `locations`
                                    #colorscale = "Blues", LEAVE THIS COMMENTED!!!
                                    text=geo_dist['text'], # hover text
                                    geo = 'geo',
                                    colorbar_title = "Num in Log2",
                                    marker_line_color='white',
                                    colorscale = ["#fdf7ff", "#835af1"],
                                    #autocolorscale=False,
                                    #reversescale=True,
                                ) 
                            ],
                            'layout': {
                                'title': "Segmentación Geográgica para Hispanoamérica",
                                #'geo':{'scope':'usa'}
                                'geo':{'scope':'hispanoamerica'}
                            }
                        }
                    )
                ], style={'display': 'inline-block', 'width': '49%'})
            ]
        
    return children


if __name__ == '__main__':
    #app.run_server(debug=True)
    app.run_server(host="0.0.0.0", port="8052", debug=False) #debug=True (for localshost); #)#debug=False (for AWS EC2)
