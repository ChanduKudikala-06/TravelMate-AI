import os 
import re
import certifi
import airportsdata
import pycountry
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"]=certifi.where()
os.environ["REQUEST_CA_BUNDLE"]=certifi.where()

API_KEY=os.getenv("AVIATIONSTACK_API_KEY")


#Default origin is Dhaka

DEFAULT_ORIGIN_IATA=os.getenv("DEFAULT_ORIGIN_IATA","DAC")

BASE_URL="https://api.aviationstack.com/v1/flights"

AIRPORTS=airportsdata.load("IATA")

COUNTRY_ALIASES={
    "usa":"US",
    "america":"US",
    "uk":"GB"
}

COUNTRY_MAIN_AIRPORT={
    "BD":"DAC",
    "IN":"DEL",
    "US":"JFK"
}