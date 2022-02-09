import quantstats as qs

stock = qs.utils.download_returns('FB')

qs.reports.plots(stock, mode='basic')

qs.reports.html(stock, "AAPL", output='./file-name.html')
