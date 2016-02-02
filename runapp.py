from envwatcher.webapp import app
app.config['DEG_F'] = True
app.run(debug=True)