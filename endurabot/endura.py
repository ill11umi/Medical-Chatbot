import nltk
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()


import numpy as np
import json
import random
import pickle
import datetime


from flask import Flask, render_template, request

from keras.models import load_model
model = load_model('endu_model.h5')

intents = json.loads(open('data.json').read())

words = pickle.load(open('texts.pkl','rb'))
classes = pickle.load(open('labels.pkl','rb'))

def clean_up_sentence(sentence):
    #tokenize the pattern 
    sentence_words = nltk.word_tokenize(sentence)
    #lemmatize each word 
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

# return bag of words array: 0 or 1 for each word in the bag that exists in the sentence
def bow(sentence, words, show_details=True):
    # tokenize the pattern
    sentence_words = clean_up_sentence(sentence)
    # bag of words - matrix of N words, vocabulary matrix
    bag = [0]*len(words)  
    for s in sentence_words:
        for i,w in enumerate(words):
            if w == s: 
                # assign 1 if current word is in the vocabulary position
                bag[i] = 1
                if show_details:
                    print ("found in bag: %s" % w)
    return np.array(bag)

def predict_class(sentence, model):
    #filter out predictions below a threshold 
    b = bow(sentence, words,show_details=False)
    res = model.predict(np.array([b]))[0]
    ERROR_THRESHOLD = 0.25
    results = [[i,r] for i,r in enumerate(res) if r>ERROR_THRESHOLD]
    #sort by strength of probability
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return return_list

def getResponse(ints, intents_json):
    tag = ints[0]['intent']
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if(i['tag']== tag):
            result = random.choice(i['responses'])
            break
    return result

# Doctor data
doctors = [
    {"name": "Dr. John Doe", "specialty": "General Physician", "available_dates": ["2023-06-01", "2023-06-02", "2023-06-03"]},
    {"name": "Dr. Jane Smith", "specialty": "Dermatologist", "available_dates": ["2023-06-01", "2023-06-02", "2023-06-04"]}
]

# Global variables to store user state
user_state = {}

def handle_appointment_intent():
    response = "Sure, let me check the available doctors for you. Please select a doctor from the list:\n"

    for i, doctor in enumerate(doctors):
        response += f"{i+1}. {doctor['name']}, {doctor['specialty']}\n"

    user_state['current_intent'] = 'select_doctor'
    return response

def handle_select_doctor_intent(user_input):
    try:
        doctor_index = int(user_input) - 1
        if doctor_index < 0 or doctor_index >= len(doctors):
            return "Invalid doctor selection. Please try again."
        
        selected_doctor = doctors[doctor_index]
        user_state['selected_doctor'] = selected_doctor

        available_dates = selected_doctor['available_dates']
        response = "Great! Please select a date for your appointment from the available dates:\n"
        for i, date in enumerate(available_dates):
            response += f"{i+1}. {date}\n"

        user_state['current_intent'] = 'select_appointment_date'
        return response

    except ValueError:
        return "Invalid input. Please enter a valid number."

def handle_select_appointment_date_intent(user_input):
    try:
        date_index = int(user_input) - 1
        selected_doctor = user_state.get('selected_doctor')

        if selected_doctor is None:
            return "No doctor selected. Please start over and select a doctor first."

        available_dates = selected_doctor['available_dates']

        if date_index < 0 or date_index >= len(available_dates):
            return "Invalid date selection. Please try again."

        selected_date = available_dates[date_index]
        appointment_date = datetime.datetime.strptime(selected_date, "%Y-%m-%d").strftime("%B %d, %Y")

        response = f"Your appointment with {selected_doctor['name']} on {appointment_date} has been booked. We look forward to seeing you!"
        return response

    except ValueError:
        return "Invalid input. Please enter a valid number."

def chatbot_response(msg):
    ints = predict_class(msg, model)
    intent = ints[0]['intent']
    
    if intent == 'appointment':
        response = handle_appointment_intent()
        if response:
            return response
    
    elif intent == 'select_doctor':
        response = handle_select_doctor_intent(msg)
        if response:
            return response
    
    elif intent == 'select_appointment_date':
        response = handle_select_appointment_date_intent(msg)
        if response:
            return response
    else:
        response = getResponse(ints, intents)
        return response
    
    return response

app = Flask(__name__)

app.static_folder = 'static'

@app.route("/")
def home():
    return render_template("index.html")
@app.route("/get")

def get_bot_response():
    userText = request.args.get('msg')
    return chatbot_response(userText)
if __name__ == "__main__":
    app.run()