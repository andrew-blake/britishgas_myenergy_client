#!/usr/bin/env python
from datetime import date, timedelta

from config import USERNAME, PASSWORD, DEBUG, SSL_VERIFY, PROXIES

from britishgas_myenergy_client import MyEnergyClient

client = MyEnergyClient(username=USERNAME, password=PASSWORD, proxies=PROXIES, debug=DEBUG, ssl_verify=SSL_VERIFY)

today = date.today()
yesterday = today - timedelta(days=1)

client.get_usage_by_day_hourly(yesterday)
client.get_usage_by_month_daily(yesterday)
client.get_usage_by_year_monthly(yesterday)
client.get_nectar_details()