from flask import Flask, request, render_template, session, redirect, url_for
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from booking_db import load_bookings, save_bookings, add_booking, get_dynamic_available_times, SERVICES, SERVICE_DURATION
import unicodedata
from datetime import datetime


newnum = "+17752619881"

TWILIO_ACCOUNT_SID = "your_account_sid"
TWILIO_AUTH_TOKEN = "your_auth_token"


# Storing what step each user is on
user_states = {}


# Temporarily holds the date selected by each user
user_pending_date = {}   

# Dictionary for username and password
BUSINESS_PASSWORDS = {
    "whatsapp:+17752619881": ("barbearia", "senha123")
}

#Dictionary for retreiving owner of bot whatsapp number
BUSINESS_CONFIG = {
    "whatsapp:+17752619881": {
        "twilio_number": "whatsapp:+17752619881",  # number of bot
        "owner_number": "whatsapp:+5511980711972"   # number of owner
    },
    
}



user_pending_service = {}
user_pending_name = {}


#Function for notifying owner when an appointment is fixed
def notify_owner(business_id, nome, user_number, service, date_str, hora):
    cfg = BUSINESS_CONFIG.get(business_id)
    if not cfg:
        print(f"[notify_owner] Nenhuma configuração cadastrada para o business_id {business_id}")
        return
    twilio_number = cfg["twilio_number"]
    owner_number = cfg["owner_number"]

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    msg = (
        f"Novo agendamento!\n"
        f"Cliente: {nome}\n"
        f"Número WhatsApp: {user_number}\n"
        f"Serviço: {service}\n"
        f"Data: {date_str}\n"
        f"Hora: {hora}"
    )
    try:
        client.messages.create(
            body=msg,
            from_=twilio_number,
            to=owner_number
        )
        print(f"[notify_owner] Mensagem enviada para o dono do negócio {business_id}: {owner_number}")
    except Exception as e:
        print(f"[notify_owner] Erro ao enviar mensagem: {e}")



def normalize_text(text):
    # Remove acentos e deixa tudo minúsculo
    return ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn').lower()



#Usable for constructing front end 
def find_business_by_username(username: str):
    matches = [(bid, pwd) for bid, (usr, pwd) in BUSINESS_PASSWORDS.items() if usr == username]
    if not matches:
        return None  # username not found
    if len(matches) > 1:
        # optional: handle duplicate usernames across businesses
        # raise ValueError("Duplicate username")  # or return a special value
        return "DUPLICATE"
    bid, pwd = matches[0]
    return bid, pwd


app = Flask(__name__)

app.secret_key = 'your_app.secret_key'


@app.route('/webhook', methods=['POST'])
def webhook():
    user_number = request.form.get('From')
    business_id = request.form.get('To')

    #Creating unique keys
    key = (business_id, user_number)

    bookings = load_bookings(business_id)

    #Retrieve message received
    incoming_msg = request.form.get('Body').strip().lower()
    resp = MessagingResponse()

    print(f"📥 Incoming message: {incoming_msg}")
    print(f"Business id = {business_id}")


    #=============================
    #BEGINNING OF USER FLOW:
    #
    #   Organized in a sequence 
    #   of 6 possible states
    #=============================
    if key not in user_states:
        user_states[key] = "INIT"

    state = user_states[key]

    #1st step  ->  first message and retreiving user's name input 
    if state == "INIT":
        if 'prenotare' in incoming_msg:
            resp.message("Ciao! Come ti chiami??")
            user_states[key] = "ASK_NAME"
            return str(resp)
        else:
            resp.message("Scrivi 'prenotare' per fissare il tuo appuntamento!")
            return str(resp)
        
    #2nd step -> services offering + retreiving user selection 
    if state == "ASK_NAME":
        nome = incoming_msg.strip().title()
        user_pending_name[key] = nome
        available_services = SERVICES.get(business_id, [])
        if available_services:
            services_str = ', '.join(available_services)
            resp.message(f"Perfetto, {nome}! Quale servizio desideri prenotare? Opzioni: {services_str}")
            user_states[key] = "ASK_SERVICE"
        else:
            resp.message("Nessuno Servizio Disponibile a questo posto")
            user_states[key] = "INIT"
        return str(resp)
    
    #3rd step -> receive desired service and get desired day
    if state == "ASK_SERVICE":
        chosen_service = incoming_msg.strip().title()
        available_services = SERVICES.get(business_id, [])
        if chosen_service in available_services:
            user_pending_service[key] = chosen_service
            nome = user_pending_name.get(key, user_number)
            resp.message(f"Certo {nome}, per quale giorno del mese sei interessato? Se si tratta del mese prossimo, digita 'Prossimo Mese'."
)
            user_states[key] = "ASK_DAY"
        else:
            services_str = ', '.join(available_services)
            resp.message(f"Servizio non valido. Per favore, scrivere una delle opzioni: {services_str}")
        return str(resp)

    #4rth step -> Retreive the desired day, handle next month cases    
    if state == "ASK_DAY":
        normalized_msg = normalize_text(incoming_msg)
        nome = user_pending_name.get(key, user_number)

        if 'prossimo mese' in normalized_msg:
        
            today = datetime.now()
            
            #Handling boundaries possible issues
            year = today.year + 1 if today.month == 12 else today.year
            next_month = 1 if today.month == 12 else today.month + 1

            #Saves date without day yet
            user_pending_date[key] = f"{year}-{next_month:02d}-"  
            resp.message(f"Ottimo! Per favore, inviami il giorno del mese desiderato per {next_month:02d}/{year}.")
            user_states[key] = "ASK_DAY_NEXT_MONTH"
            return str(resp)

        
        if incoming_msg.isdigit() and 1 <= int(incoming_msg) <= 31:
            today = datetime.now()

            date_str = f"{today.year}-{today.month:02d}-{int(incoming_msg):02d}"
            user_pending_date[key] = date_str

            service = user_pending_service.get(key)
            duration = SERVICE_DURATION.get((business_id, service))
            available_times = get_dynamic_available_times(business_id, bookings, date_str, duration)
            if available_times:
                times_str = ', '.join(available_times)
                resp.message(
                    f"Orari disponibili per {service} il giorno {incoming_msg}: {times_str}.\n"
                    f"Durata del servizio: {duration} minuti.\n"
                    "Per favore, rispondi con l'orario desiderato (es: 09:00)."

                )                
                user_states[key] = "ASK_TIME"
            else:
                resp.message(f"Mi dispiace {nome}, non ci sono orari disponibili per quel giorno. Per favore, scegli un altro giorno.")
        else:
            resp.message("Per favore, inviami un numero di giorno valido (1-31) oppure 'Prossimo Mese'.")
        return str(resp)
    
    #4.b Next month case
    if state == "ASK_DAY_NEXT_MONTH":
        nome = user_pending_name.get(key, user_number)
        normalized_msg = normalize_text(incoming_msg)

        if normalized_msg.isdigit() and 1 <= int(normalized_msg) <= 31:

        
            partial_date = user_pending_date[key]  # Ex: '2025-08-'
            date_str = partial_date + f"{int(normalized_msg):02d}"
            user_pending_date[key] = date_str

            service = user_pending_service.get(key)
            duration = SERVICE_DURATION.get((business_id, service))
            available_times = get_dynamic_available_times(business_id, bookings, date_str, duration)
            if available_times:
                times_str = ', '.join(available_times)
                resp.message(f"Orari disponibili per {service} il giorno {normalized_msg} del prossimo mese: {times_str}. Per favore, rispondi con l'orario desiderato (es: 09:00).")
                user_states[key] = "ASK_TIME"
            else:
                resp.message(f"Mi dispiace {nome}, non ci sono orari disponibili per quel giorno. Per favore, scegli un altro giorno del prossimo mese.")
        else:
            resp.message("Per favore, inviare un numero di giorno valido (1-31) per il prossimo mese.")
        return str(resp)

    #5th step: allocate user hour preference
    if state == "ASK_TIME":
        nome = user_pending_name.get(key, user_number)
        date_str = user_pending_date.get(key)
        if not date_str:
            # fallback, shouldn't happen, but reset state
            user_states[key] = "INIT"
            resp.message("Si è verificato un errore. Per favore, invia 'prenotare' per ricominciare.")
            return str(resp)
        
        service = user_pending_service.get(key)
        duration = SERVICE_DURATION.get((business_id, service))
        available_times = get_dynamic_available_times(business_id, bookings, date_str, duration)
        if incoming_msg in available_times:
            nome = user_pending_name.get(key, user_number)  # usa o nome salvo, ou o número se não houver
            add_booking(business_id, bookings, user_number, nome, date_str, incoming_msg, service)
            notify_owner(business_id,nome,user_number,service,date_str,incoming_msg)            
            resp.message(
                f"Prenotazione confermata per {nome} ({service}) il {date_str[-2:]}/{date_str[5:7]} alle {incoming_msg}."
            )
  
            user_states[key] = "INIT"
            user_pending_date.pop(key, None)
            user_pending_service.pop(key, None)
            user_pending_name.pop(key, None)
        else:
            #resp.message("Questo orario non è disponibile o non è valido. Per favore, scrivi uno degli orari disponibili, nel formato indicato.")
            if available_times:
                times_str = ', '.join(available_times)
                resp.message(f"Orari disponibili per il giorno scelto: {times_str}")
            else:
                resp.message("Non ci sono orari disponibili.")
        return str(resp)       



@app.route('/dashboard')
def dashboard():
    business_id = session.get('business_id')
    if not business_id:
        return redirect(url_for('login'))
    bookings = load_bookings(business_id)

    return render_template('dashboard.html', bookings=bookings, business_id=business_id)




@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        result = find_business_by_username(username)
        if result is None:
            error = "Credenziale non valida!"
        elif result == "DUPLICATE":
            error = "Contattare supporto, nome usuario dupplicato"
        else:
            business_id, stored_password = result
            if password == stored_password:
                session['business_id'] = business_id
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                error = "Credenziale non valida!"

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(port=5000, debug=True)
