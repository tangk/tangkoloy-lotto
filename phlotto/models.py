from google.appengine.ext import db

class DrawDate(db.Model):
    year = db.StringProperty(required=True)
    month = db.StringProperty(required=True)
    day = db.StringProperty(required=True)

def DrawDate_key(results=None):
    return db.Key.from_path('DrawDate', drawdate_name)

class LottoResults(db.Model):
    result = db.StringProperty()
    jackpot = db.StringProperty()
    winners = db.StringProperty()

class DigitsResults_high(db.Model):
    result = db.StringProperty()

class DigitsResults_low(db.Model):
    eleven_am_result = db.StringProperty()
    four_pm_result = db.StringProperty()
    nine_pm_result = db.StringProperty()