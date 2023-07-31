from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.graph_objects as go
import MetaTrader5 as mt5
from mt5_funcs import get_symbol_names, TIMEFRAMES, TIMEFRAME_DICT
import numpy as np


# creates the Dash App
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

symbol_dropdown = html.Div([
    html.P('Symbol:'),
    dcc.Dropdown(
        id='symbol-dropdown',
        options=[{'label': symbol, 'value': symbol} for symbol in get_symbol_names()],
        value='EURUSD'
    )
])

timeframe_dropdown = html.Div([
    html.P('Timeframe:'),
    dcc.Dropdown(
        id='timeframe-dropdown',
        options=[{'label': timeframe, 'value': timeframe} for timeframe in TIMEFRAMES],
        value='D1'
    )
])

num_bars_input = html.Div([
    html.P('Number of Candles'),
    dbc.Input(id='num-bar-input', type='number', value='20')
])

# creates the layout of the App
app.layout = html.Div([
    html.H1('Real Time Charts'),

    dbc.Row([
        dbc.Col(symbol_dropdown),
        dbc.Col(timeframe_dropdown),
        dbc.Col(num_bars_input)
    ]),

    html.Hr(),

    dcc.Interval(id='update', interval=200),

    html.Div(id='page-content')

], style={'margin-left': '5%', 'margin-right': '5%', 'margin-top': '20px'})

@app.callback(
    Output('page-content', 'children'),
    Input('update', 'n_intervals'),
    State('symbol-dropdown', 'value'), State('timeframe-dropdown', 'value'), State('num-bar-input', 'value')
)
def update_ohlc_chart(interval, symbol, timeframe, num_bars):
    timeframe_str = timeframe
    timeframe = TIMEFRAME_DICT[timeframe]
    num_bars = int(num_bars)

    print(symbol, timeframe, num_bars)

    bars = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)
    data = pd.DataFrame(bars)
    data['time'] = pd.to_datetime(data['time'], unit='s')


    print (data)



    O =2
    demand_period=10
    supply_period=5
    # Calculate demand and supply based on rolling windows
    data['Demand'] = data['close'].rolling(window=demand_period).mean()
    data['Supply'] = data['close'].rolling(window=supply_period).mean()

    # Calculate EMA for demand and supply
    data['EMA_Demand'] = data['Demand'].ewm(span=demand_period, adjust=False).mean()
    data['EMA_Supply'] = data['Supply'].ewm(span=supply_period, adjust=False).mean()

    # Calculate EMA liquidity using the EMA of demand and supply
    data['EMA_Liquidity'] = data['EMA_Demand'] - data['EMA_Supply']

    # Mark buy liquidity when price is falling and EMA liquidity is rising and EMA liquidity is greater than 0
    data['Buy_Liquidity'] = np.where(
        (data['close'] < data['close'].shift(1)) &
        (data['EMA_Liquidity'] > data['EMA_Liquidity'].shift(1)) &
        (data['EMA_Liquidity'] > 0),
        'Buy',
        ''
    )

    # Mark sell liquidity when price is rising and EMA liquidity is falling and EMA liquidity is less than 0
    data['Sell_Liquidity'] = np.where(
        (data['close'] > data['close'].shift(1)) &
        (data['EMA_Liquidity'] < data['EMA_Liquidity'].shift(1)) &
        (data['EMA_Liquidity'] < 0),
        'Sell',
        ''
    )

    buy_signals = data[data['Buy_Liquidity'] == 'Buy']
    sell_signals = data[data['Sell_Liquidity'] == 'Sell']

    List = []
    indx = []
    x = 0
    Trend_Dir = ''
    Change_direction_points = []
    Change_direction_index = []
    LenList = ''

   # cc = pd.Series(data['EMA_Liquidity'])

    for index, ema_liquidity in data['EMA_Liquidity'].items():
        Trend = ema_liquidity - x
        if Trend > 0 :
            try:
                if len(List) != [] and List[0] < 0:
                    if len(List) > O:
                      LenList = 'T'
                      pass
                    else:
                      LenList = 'F'
                      pass
                    List.clear()
                    indx.clear()
                    List.append(Trend)
                    indx.append(index)
                else:
                    List.append(Trend)
                    indx.append(index)
                    pass
            except:
                List.append(Trend)
                indx.append(index)
                pass
            Acctual_Trend_Dir = 'UP'
           # print (len(List))
        #    print ('UP')
         #   print (List)
        elif Trend < 0:
            try:
                if len(List) != [] and List[0] > 0:
                    if len(List) > O:
                      LenList = 'T'
                      pass
                    else:
                      LenList = 'F'
                      pass
                    List.clear()
                    indx.clear()
                    List.append(Trend)
                    indx.append(index)
                else:
                    List.append(Trend)
                    indx.append(index)
                    pass
            except:
                List.append(Trend)
                indx.append(index)
                pass
           # print (len(List))
            Acctual_Trend_Dir = 'DOWN'
           # print ('DOWN')
            #print (List)
        else:
            Acctual_Trend_Dir=''

        if Trend_Dir != Acctual_Trend_Dir and LenList == 'T':
            Change_direction_points.append(ema_liquidity)
            Change_direction_index.append(index)
        else:
            pass

        Trend_Dir = Acctual_Trend_Dir
        x = ema_liquidity

    datax = {'index': Change_direction_index , 'ema_liquidity' :Change_direction_points}
    d= pd.DataFrame(datax)


  #  datax = {'index': Change_direction_index, 'ema_liquidity': Change_direction_points}
   # d = pd.DataFrame(datax)
    merged_data = pd.merge(data, d, left_index=True, right_on='index', how='inner')

    # Drop the duplicate 'index' column from the merged DataFrame
    merged_data.drop('index', axis=1, inplace=True)

    # Print the merged DataFrame
    print(merged_data)

   # x = merged_data['close']




    fig = go.Figure(data=go.Candlestick(x=data['time'],
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close']))



    fig.add_trace(go.Scatter(x=merged_data[merged_data['Buy_Liquidity'] == 'Buy']['time'],
                             y=merged_data[merged_data['Buy_Liquidity'] == 'Buy']['low'],
                             mode='markers',
                             marker=dict(color='green', size=10),
                             name='Buy Signal'))

    # Add the 'Sell' signals to the Candlestick chart
    fig.add_trace(go.Scatter(x=merged_data[merged_data['Sell_Liquidity'] == 'Sell']['time'],
                             y=merged_data[merged_data['Sell_Liquidity'] == 'Sell']['high'],
                             mode='markers',
                             marker=dict(color='red', size=10),
                             name='Sell Signal'))

    # Customize the layout of the Candlestick chart
    fig.update(layout_xaxis_rangeslider_visible=False)
    fig.update_layout(yaxis={'side': 'right'})
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True

    # Return the chart as part of the callback output
    return [
        html.H2(id='chart-details', children=f'{symbol} - {timeframe_str}'),
        dcc.Graph(figure=fig, config={'displayModeBar': False})
    ]






    fig.update(layout_xaxis_rangeslider_visible=False)
    fig.update_layout(yaxis={'side': 'right'})
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True



   # return [
    #    html.H2(id='chart-details', children=f'{symbol} - {timeframe_str}'),
     #   dcc.Graph(figure=fig, config={'displayModeBar': False})
      #  ]


if __name__ == '__main__':
    # starts the server
    app.run_server()