from flask import Flask, render_template

app = Flask(__name__.split('.')[0])

@app.route("/")
@app.route("/index")
def index():
    return render_template('index.html', series=series)


@app.route("/plots/<plotname>")
def index(plotname):
    return render_template('generating.html', series_name=series_name, plots=plots)
    return render_template('plots.html', series_name=series_name, plots=plots)

if __name__ == "__main__":
    app.run()