import requests
import pygal
import csv
from flask import Flask, render_template, request
from datetime import datetime

app = Flask(__name__)
app.static_folder = 'static'

# fx that reads all stock symbols from stocks.csv
def get_stock_symbols():
    """Reads stock symbols from stocks.csv and returns them as a list."""
    stock_symbols = []
    try:
        with open('stocks.csv', 'r') as file:
            reader = csv.reader(file)
            next(reader)  # skip header
            stock_symbols = [row[0] for row in reader]
    except FileNotFoundError:
        print("Error: stocks.csv not found.")
    return stock_symbols

# fx that accesses the API — time series is tricky here
def get_stock_data(ticker, time_series):
    api_key = "JGSKV0LY50824HYL"
    url = "https://www.alphavantage.co/query"

    # select correct API function and key name for data based on time_series input
    if time_series == "1":
        function = "TIME_SERIES_INTRADAY"
        time_key = "Time Series (60min)"
        params = {
            "function": function,
            "symbol": ticker,
            "interval": "60min",
            "apikey": api_key
        }
    elif time_series == "2":
        function = "TIME_SERIES_DAILY"
        time_key = "Time Series (Daily)"
        params = {
            "function": function,
            "symbol": ticker,
            "apikey": api_key
        }
    elif time_series == "3":
        function = "TIME_SERIES_WEEKLY"
        time_key = "Weekly Time Series"
        params = {
            "function": function,
            "symbol": ticker,
            "apikey": api_key
        }
    else:  # time_series = "4"
        function = "TIME_SERIES_MONTHLY"
        time_key = "Monthly Time Series"
        params = {
            "function": function,
            "symbol": ticker,
            "apikey": api_key
        }

    # this is the part that actually gets the data
    response = requests.get(url, params=params)
    data = response.json()

    return data, time_key

# fx to handle the data by the date and time series
def filter_data_by_date(data, time_key, time_series, start_date, end_date):
    filtered_data = {}

    for date in data.get(time_key, {}):
        if time_series == "1":
            date_only = date.split()[0]  # for intraday
            if start_date <= date_only <= end_date:
                filtered_data[date] = data[time_key][date]
        else:
            if start_date <= date <= end_date:
                filtered_data[date] = data[time_key][date]

    return filtered_data

# fx that generates the chart from the filtered data
def create_chart(ticker, chart_type, filtered_data, time_series, start_date, end_date):
    if not filtered_data:
        return None

    # chart title
    chart_title = f"{ticker} Stock Prices ({start_date} to {end_date})"

    # extract dates and OHLC prices
    dates = sorted(filtered_data.keys())
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []

    for date in dates:
        daily_data = filtered_data[date]

        open_key = next((k for k in daily_data if "open" in k.lower()), "1. open")
        high_key = next((k for k in daily_data if "high" in k.lower()), "2. high")
        low_key  = next((k for k in daily_data if "low" in k.lower()),  "3. low")
        close_key = next((k for k in daily_data if "close" in k.lower()), "4. close")

        open_prices.append(float(daily_data[open_key]))
        high_prices.append(float(daily_data[high_key]))
        low_prices.append(float(daily_data[low_key]))
        close_prices.append(float(daily_data[close_key]))

    # Bar or Line with tooltip config
    if chart_type == "1":
        chart = pygal.Bar(
            x_label_rotation=45,
            show_legend=True,
            tooltip_border_radius=10,
            tooltip_font_size=14,
            tooltip_fancy_mode=True
        )
    else:
        chart = pygal.Line(
            x_label_rotation=45,
            show_legend=True,
            tooltip_border_radius=10,
            tooltip_font_size=14,
            tooltip_fancy_mode=True
        )

    chart.title = chart_title
    chart.y_title = "Price (USD)"
    chart.x_labels = [str(date) for date in dates]

    # add data with hover labels
    chart.add('Open', [{'value': val, 'label': f"Open: ${val:.2f}"} for val in open_prices])
    chart.add('High', [{'value': val, 'label': f"High: ${val:.2f}"} for val in high_prices])
    chart.add('Low',  [{'value': val, 'label': f"Low: ${val:.2f}"} for val in low_prices])
    chart.add('Close', [{'value': val, 'label': f"Close: ${val:.2f}"} for val in close_prices])

    return chart.render().decode('utf-8')

# main route — handles both GET and POST
@app.route("/", methods=["GET", "POST"])
def index():
    stock_symbols = get_stock_symbols()
    chart_file = None
    chart_attempted = False

    if request.method == "POST":
        ticker = request.form['stock_symbol']
        chart_type = request.form['chart_type']
        time_series = request.form['time_series']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        chart_attempted = True

        # input validation
        if ticker not in stock_symbols:
            print("Invalid stock symbol selected.")
            return render_template("index.html", stock_symbols=stock_symbols, chart_file=None, chart_attempted=chart_attempted)

        if chart_type not in ["1", "2"] or time_series not in ["1", "2", "3", "4"]:
            print("Invalid chart or time series input.")
            return render_template("index.html", stock_symbols=stock_symbols, chart_file=None, chart_attempted=chart_attempted)

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                print("End date must be after start date.")
                return render_template("index.html", stock_symbols=stock_symbols, chart_file=None, chart_attempted=chart_attempted)
        except ValueError:
            print("Date format error.")
            return render_template("index.html", stock_symbols=stock_symbols, chart_file=None, chart_attempted=chart_attempted)

        # main logic
        data, time_key = get_stock_data(ticker, time_series)
        filtered_data = filter_data_by_date(data, time_key, time_series, start_date, end_date)
        chart_file = create_chart(ticker, chart_type, filtered_data, time_series, start_date, end_date)

    return render_template("index.html", stock_symbols=stock_symbols, chart_file=chart_file, chart_attempted=chart_attempted)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)