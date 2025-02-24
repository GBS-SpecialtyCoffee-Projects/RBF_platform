from phonenumbers import COUNTRY_CODE_TO_REGION_CODE

# for country_code, region_codes in COUNTRY_CODE_TO_REGION_CODE.items():
#     print(country_code, region_codes)

# COUNTRY_CODES = [ item for item in COUNTRY_CODE_TO_REGION_CODE ]
COUNTRY_REGION_CODES = [ (code, f'{item} (+{code})') for code in COUNTRY_CODE_TO_REGION_CODE for item in COUNTRY_CODE_TO_REGION_CODE[code] ]

