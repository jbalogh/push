import requests


AUTH_KEY = ''
C2DM_URL = 'https://android.apis.google.com/c2dm/send'


def c2dm(droid_id, collapse_key, data):
    params = {'registration_id': droid_id,
              'collapse_key': collapse_key}
    for key, value in data.items():
        params['data.' + key] = value
    headers = {'Authorization': 'GoogleLogin auth=' + AUTH_KEY}
    r = requests.post(C2DM_URL, data=params, headers=headers)
    return r
