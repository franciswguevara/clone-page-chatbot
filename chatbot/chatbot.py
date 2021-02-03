from dotenv import load_dotenv
from flask import Flask, request
import functools
import json
import os
from chatbot.pymessenger_updated import Bot
import re
from time import sleep
import time
import pickle
from chatbot.scraper import timeout, get_request, scraper, links, push

load_dotenv()

app = Flask(__name__)
ACCESS_TOKEN = os.environ['PAGE_ACCESS_TOKEN']
VERIFY_TOKEN = os.environ['VERIFY_TOKEN']
bot = Bot(ACCESS_TOKEN)
df = {}
message = ''

#We will receive messages that Facebook sends our bot at this endpoint 
@app.route("/", methods=['GET', 'POST'])
def receive_message():
    #remember list of articles and what are article the user is reading
    global df
    global message

    if request.method == 'GET':
        """Before allowing people to message your bot, Facebook has implemented a verify token
        that confirms all requests that your bot receives came from Facebook.""" 
        token_sent = request.args.get("hub.verify_token")

        return verify_fb_token(token_sent)
    #if the request was not get, it must be POST and we can just proceed with sending a message back to user
    else:
        print(os.getcwd())
        if os.path.exists('df.pickle'):
            with open('df.pickle', 'rb') as x:
                df = pickle.load(x)
        with open('message.pickle', 'wb') as x:
            pickle.dump(message, x, protocol=pickle.HIGHEST_PROTOCOL)
            
        # get whatever message a user sent the bot
        output = request.get_json()
        print(output)
        # for event in output['entry']:
        #added to remove for loops
        message = output['entry'][0]['messaging'][0]
            # for message in messaging:
        #unindented twice
        #Facebook Messenger ID for user so we know where to send response back to
        recipient_id = str(message['sender']['id'])
        #If user sent a message
        if message.get('message'):
            if message['message'].get('text'):
                string = message['message'].get('text').lstrip().split(' ',1)
                
                #If the person wants to search something
                if string[0].lower() == 'search' and len(string) >= 2:
                    with open('message.pickle', 'rb') as x:
                        previous_message = pickle.load(x)
                    print('previous message: ', previous_message)
                    print('message: ', message)
                    if message == previous_message:
                        print('MESSAGE PROCESSED')
                        return 'message processed'
                    else: 
                        send_message(recipient_id,"Thank you for your search! Let me see what I can find. :)")
                        articles = push(links(string[1]))
                        if articles:
                            df.pop(recipient_id, None)
                            with open('df.pickle', 'wb') as x:
                                pickle.dump(df, x, protocol=pickle.HIGHEST_PROTOCOL)
                            articles.insert(0,1)
                            df[recipient_id] = articles
                            with open('df.pickle', 'wb') as z:
                                pickle.dump(df, z, protocol = pickle.HIGHEST_PROTOCOL)
                            for i in range(1,len(articles)):
                                
                                #Send a button allowing them to read more of the article
                                buttons = [
                                                {
                                                    "type":"postback",
                                                    "title":"Read",
                                                    "payload": i
                                                }
                                            ]
                                #Send the title and summary of the article
                                button_message(recipient_id,articles[i]['title'][0:500],buttons)
                        else:
                            send_message(recipient_id,'''I couldn't find anything on that, could you try making your search more specific? It would help if you asked a question! (Ex. "Who is the President of the Philippines?)''')
                #If the person mistakenly just said search
                    return "Messaged Processed"
                elif string[0].lower() == 'search' and len(string) == 1:
                    send_message(recipient_id, "Hi there! Make sure that you type 'search' before your question. Ex. search Who is the President of the Philippines?")
                    #TELL THEM THAT 
                #All other cases 
                else:
                    #indent this when top is uncommented
                    send_message(recipient_id,"Can you say that again? I didn't understand what you said. Make sure that you type 'search' before your question. Ex. search Who is the President of the Philippines?")
                return "Messaged Processed"
            #MIGHT BE IN THE WRONG PLACE!
            #if user sends us a GIF, photo,video, or any other non-text item
            if message['message'].get('attachments'):
                #FUTURE DEVELOPMENT THINGOS
                pass
                return "Messaged Processed"
        #If user clicked one of the postback buttons
        elif message.get('postback'):
            print('DF Keys Existing: ',df.keys())
            #print(df)
            if message['postback'].get('title'):
                #If user wants to read a specific article
                #update df with new choice
                if df.get(recipient_id):
                    #retrieve choice from postback
                    choice = int(message['postback']['payload'])
                    df[recipient_id][0] = choice
                    if message['postback']['title'] == 'Read':
                        print('DF Keys Read: ',df.keys())
                        #dictionary for buttons
                        buttons = [
                                        {
                                            "type":"postback",
                                            "title":"Read more",
                                            "payload":choice
                                        }
                                    ]
                        #send button message
                        if len(df[recipient_id][choice]['article']) == 1:
                            send_message(recipient_id,df[recipient_id][choice]['article'][0])
                            df[recipient_id][choice]['article'] = "End"
                            send_message(recipient_id,"End of Article")
                        elif df[recipient_id][choice]['article'] == "End":
                            send_message(recipient_id,"End of Article")
                        else:
                            button_message(recipient_id,df[recipient_id][choice]['article'][0],buttons)
                            df[recipient_id][choice]['article'] = df[recipient_id][choice]['article'][1:]
                            with open('df.pickle', 'wb') as x:
                                pickle.dump(df, x, protocol=pickle.HIGHEST_PROTOCOL)
                        return "Messaged Processed"
                    #If user wants to read more of the article
                    elif message['postback']['title'] == 'Read more':
                        buttons = [
                                        {
                                            "type":"postback",
                                            "title":"Read more",
                                            "payload":choice
                                        }
                                    ]
                        print('Read More Keys: ',df.keys())
                        if len(df[recipient_id][choice]['article']) == 1:
                            send_message(recipient_id, df[recipient_id][choice]['article'][0])
                            df[recipient_id][choice]['article'] = "End"
                            send_message(recipient_id, "End of Article")
                        elif df[recipient_id][choice]['article'] == "End":
                            send_message(recipient_id, "End of Article")
                        else:
                            button_message(recipient_id, df[recipient_id][choice]['article'][0], buttons)
                            df[recipient_id][choice]['article'] = df[recipient_id][choice]['article'][1:]
                            with open('df.pickle', 'wb') as x:
                                pickle.dump(df, x, protocol=pickle.HIGHEST_PROTOCOL)
                        return "Messaged Processed"
                #If user clicks the get started button
                elif message['postback']['title'] == 'Get Started':
                    send_message(recipient_id, "Hey, I'm Dean! I allow Filipinos to access Google Search at no cost. This app runs purely on Free Facebook Data.\n\nIf you want to get started, just ask me a question! Make sure you write 'search' before your query. I'm excited to learn with you!\n\nI hope that you continue to stay safe! :)")
                    send_message(recipient_id, "Thank you for your interest in me! Due to an influx in responses, I'll be taking a short break for now. See you again tomorrow!")
                else:
                    send_message(recipient_id, "Hi there! Could you please repeat your search? Make sure you write 'search' before your query. Ex. search Who is the President of the Philippines")
                return "Messaged Processed"
        else:
            #how does this get triggered
            pass
    return "Message Processed"

def verify_fb_token(token_sent):
    #take token sent by facebook and verify it matches the verify token you sent
    #if they match, allow the request, else return an error 
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'

#uses PyMessenger to send response to user
def send_message(recipient_id, response):
    #sends user the text message provided via input response parameter
    bot.send_text_message(recipient_id, response)
    return "success"    

#uses PyMessenger to send message with button to user
def button_message(recipient_id,response,buttons):
    #sends user the button message provided via input response parameter
    bot.send_button_message(recipient_id,response,buttons)
    return "success"

def timer(func):
    '''Print the Runtime of the decorated function'''
    @functools.wraps(func)
    def wrapper_timer(*args,**kwargs):
        start_time = time.perf_counter()
        value = func(*args,**kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        print(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        return value
    return wrapper_timer