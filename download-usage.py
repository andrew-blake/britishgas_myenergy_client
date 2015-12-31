#!/usr/bin/env python

from config import USERNAME, PASSWORD, DEBUG, SSL_VERIFY, PROXIES

from britishgas_myenergy_client import MyEnergyClient

client = MyEnergyClient(username=USERNAME, password=PASSWORD, proxies=PROXIES, debug=DEBUG, ssl_verify=SSL_VERIFY)

client.get_usage_by_month_daily()
client.get_usage_by_year_monthly()
client.get_nectar_details()