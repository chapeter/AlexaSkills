#!/usr/bin/env python
from flask import Flask, request, make_response
from flask.ext import restful
import requests
import apikey
from alexapy.request import *
from alexapy.response import *
import random
import re
import stockportfolio

# GLOBAL VARIABLE ASSIGNMENT
VERSION = '1.0'
SECRET_KEY = '1234'

# INITIALIZE FLASK APPLICATION
app = Flask(__name__)
api = restful.Api(app)
MASHAPE_API_KEY = apikey.MASHAPE_API_KEY


class DailyQuote(restful.Resource):
    """
    A Webservice for Amazon Alexa/Echo.  Provides three basic functions
    - A random quote - Alexa ask daily quote
    TODO: stubbed in for the following capabilities
    - Political quotes - Alexa ask daily quote for a political quote
    - A funny quote - Alexa ask daily quote for a political quote
    """
    def quotes_intent_mapping(self):
        return {
            'PoliticalQuote': self.politics,
            'FunnyQuote': self.funny,
        }

    def post(self):
        """
        Main request handler, executed by flask when a new request is made
        :return: flask response
        """
        obj = Request.from_json(request.json)
        print obj.request.type
        response = self.quote_response(obj)
        return response

    @api.representation('application/json')
    def quote_response(self, request_object):
        """
        Response handler, routes the request to the appropriate method depending on type
        :param request_object: flask request
        :return: flask response
        """
        # Get the quote which will be the content sent back
        if request_object.request.type == 'LaunchRequest':
            quote = self.randomquote()
        elif request_object.request.type == 'IntentRequest':
            print request_object.request.intent['name']
            quote = self.quotes_intent_mapping()[request_object.request.intent['name']]()
        elif request_object.request.type == 'SessionEndedRequest':
            quote = "Goodbye"
        else:
            quote = "I'm having trouble accessing the quotes database"
        # Formatting things - should be standard across most reponses
        mysession = ""
        mycard = Card("Quote of the Day", quote)
        myspeech = OutputSpeech(quote)
        response = Response(outputspeech=myspeech, card=mycard)
        mybody = ResponseBody(session=mysession, response=response, endsession=False)
        resp = make_response(mybody.to_json(), 200)
        resp.headers.extend({})
        return resp

    @staticmethod
    def politics():
        """
        Method for generating a political quote
        TODO: find a good API

        :return: string quote
        """
        quote = "This is a political quote"
        print "GOT QUOTE {}".format(quote)
        return quote

    @staticmethod
    def randomquote():
        """
        Method for generating a random quote using the mashape API,
        requires MASHAPE_API_KEY to be defined globally

        :return: string quote
        """

        headers = {
            "X-Mashape-Key": MASHAPE_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        response = requests.post("https://andruxnet-random-famous-quotes.p.mashape.com/cat=famous", headers=headers)
        data = json.loads(response.text)
        quote = data['quote']
        return quote

    @staticmethod
    def funny():
        """
        Method for generating a funny quote
        TODO: find a good API

        :return: string quote
        """

        quote = "This is a funny quote"
        print "GOT QUOTE {}".format(quote)
        return quote


class MagicEightBall(restful.Resource):
    """
    A Simple webservice for Amazon Alexa/Echo

    User: Alexa ask magic eight ball if I will win the lottery?
    Alexa: Don't count on it
    """

    def post(self):
        """
        Main request handler, executed by flask when a new request is made
        :return: flask response
        """
        obj = Request.from_json(request.json)
        print obj.request.type
        response = self.eightball_response(obj)
        return response

    @api.representation('application/json')
    def eightball_response(self, request_object):
        """
        Response handler, routes the request to the appropriate method depending on type

        :return: flask response
        """
        mysession = SessionAttribute()
        answer = self.eightball_answers()
        mycard = Card("Magic Eight Ball", answer)
        myspeech = OutputSpeech(answer)
        response = Response(outputspeech=myspeech, card=mycard)
        mybody = ResponseBody(session=mysession, response=response, endsession=False)
        resp = make_response(mybody.to_json(), 200)
        resp.headers.extend({})
        return resp

    @staticmethod
    def eightball_answers():
        """
        Method for generating a random magic eightball response.
        Obtained from : https://en.wikipedia.org/wiki/Magic_8-Ball#Possible_answers

        :return: string quote
        """
        answers = ['It is certain',
                   'It is decidedly so',
                   'Without a doubt',
                   'Yes definitely',
                   'You may rely on it',
                   'As I see it, yes',
                   'Most likely',
                   'Outlook good',
                   'Yes',
                   'Signs point to yes',
                   'Reply hazy try again',
                   'Ask again later',
                   'Better not tell you now',
                   'Cannot predict now',
                   'Concentrate and ask again',
                   "Don't count on it",
                   'My reply is no',
                   'My sources say no',
                   'Outlook not so good',
                   'Very doubtful'
                   ]

        return answers[random.randint(0, len(answers)-1)]


class StockQuote(restful.Resource):
    '''
    A Webservice for Amazon Alexa.  Provides:
    - A stock price given a ticker symbol (hard coded)
    TODO:
    - Speak ticker symbol to Alexa
    '''

    def post(self):
        obj = Request.from_json(request.json)
        response = self.stock_response(obj)
        return response

    def intent_mapping(self):
        return {
            'lookupbysymbol': self.lookup_by_symbol('csco'),
        }

    @api.representation('application/json')
    def stock_response(self, request_object):
        print request_object.request.type
        speak = "Welcome to Stock Quote"
        mysession = dict()
        if request_object.request.type == 'LaunchRequest':
            speak = speak + ".  This is a " + request_object.request.type + ". Please say a stock to lookup"
            mysession['intentSequence']= 'lookupbysymbol'
            endsession = False

        elif request_object.request.type == 'IntentRequest':
            ticker = request_object.request.intent['slots']['symbol']['value']
            ticker = (re.sub('\W+', '', ticker))
            data = self.lookup_by_symbol(ticker)
            if data['list']['meta']['count'] == 0:
                print("not a symbol")
                speak = "I'm sorry but %s is not a valid symbol" % ticker
            else:
                issure_name = data['list']['resources'][0]['resource']['fields']['issuer_name']
                price = '%.2f' % float(data['list']['resources'][0]['resource']['fields']['price'])
                speak = "The current price of %s is %s dollars" % (issure_name,price)
                endsession = True
        response = self.alexaspeak(speak, mysession, endsession)
        return response


    @staticmethod
    def alexaspeak(speak, mysession, endsession):
        mycard = Card("Stock Price", speak)
        myspeech = OutputSpeech(speak)
        response = Response(outputspeech=myspeech, card=mycard)
        mybody = ResponseBody(session=mysession, response=response, endsession=endsession)
        #print("**********************************************")
        resp = make_response(mybody.to_json(), 200)
        print(json.dumps(json.loads(mybody.to_json()), indent=4))
        resp.headers.extend({})
        return resp

    @staticmethod
    def lookup_by_symbol(symbol):
        response = requests.get("http://finance.yahoo.com/webservice/v1/symbols/%s/quote?format=json&view=detail" % symbol)
        data = json.loads(response.text)
        #print(data)
        return data


class StockReport(restful.Resource):
    '''
    A Webservice for Amazon Alexa.  Provides:
    - A stock price given a ticker symbol (hard coded)
    TODO:
    - Speak ticker symbol to Alexa
    '''

    def post(self):
        obj = Request.from_json(request.json)
        print obj.request.type
        response = self.stock_response(obj)
        return response

    @api.representation('application/json')
    def stock_response(self, request_object):
        speak = ""
        stocks = stockportfolio.stocks

        for stock in stocks:
            data = StockQuote.lookup_by_symbol(stock)
            issure_name = data['list']['resources'][0]['resource']['fields']['issuer_name']
            price = '%.2f' % float(data['list']['resources'][0]['resource']['fields']['price'])
            change = '%.2f' % float(data['list']['resources'][0]['resource']['fields']['change'])
            if float(change) >= 0:
                direction = 'up'
            else:
                direction = 'down'
            #Cisco is Up 15 points; brining it to price
            speakbuild = "%s is %s %s points; bringing it to a price of %s dollars.  " % (issure_name,direction,change,price)
            speak = speak + speakbuild
        mysession = ""
        mycard = Card("Stock Price", speak)
        myspeech = OutputSpeech(speak)
        response = Response(outputspeech=myspeech, card=mycard)
        mybody = ResponseBody(session=mysession, response=response, endsession=False)
        resp = make_response(mybody.to_json(), 200)
        #print(resp)
        resp.headers.extend({})
        #print(resp.headers.extend({}))
        return resp







"""
Resource mapping for api endpoints
"""

api.add_resource(DailyQuote, '/api/quote')
api.add_resource(MagicEightBall, '/api/eightball')
api.add_resource(StockQuote, '/api/stock')
api.add_resource(StockReport, '/api/report')

if __name__ == '__main__':
    app.secret_key = SECRET_KEY
    app.run(host='0.0.0.0', debug=True)
