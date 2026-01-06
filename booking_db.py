import json
from datetime import datetime, timedelta
import re


def safe_filename(business_id):
    #Returns a version of business_id safe for file names
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', business_id)




BUSINESS_HOURS = {
    "whatsapp:+17752619881": {
        "work_start": "09:00",
        "work_end": "18:00",
        "lunch_start": "12:00",
        "lunch_end": "14:00"
    }
}


SERVICES = {
    "whatsapp:+17752619881": ["Taglio", "Barba", "Taglio + Barba"]
}

SERVICE_DURATION = {
    ("whatsapp:+17752619881", "Taglio"): 30,
    ("whatsapp:+17752619881", "Barba"): 20,
    ("whatsapp:+17752619881", "Taglio + Barba"): 45
}


def load_bookings(business_id):
    filename = f"bookings_{safe_filename(business_id)}.json"
    try:
        with open(filename, 'r') as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except FileNotFoundError:
        return []
    

def save_bookings(business_id,bookings):
    filename = f"bookings_{safe_filename(business_id)}.json"

    with open(filename, 'w') as f:
        json.dump(bookings, f, indent=2)

def add_booking(business_id, bookings, user, nome, date, time, service):
    duration = SERVICE_DURATION[(business_id, service)]
    booking = {
        "user": user,      # <-- Client WhatsApp Number
        "nome": nome,      # <-- Client Name
        "date": date,
        "time": time,
        "service": service,
        "duration": duration,
        "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    bookings.append(booking)
    save_bookings(business_id, bookings)
    return booking


def get_booked_times_for_day(bookings, date):
    return [b['time'] for b in bookings if b['date'] == date]





def get_dynamic_available_times(business_id, bookings, date_str, duration, interval=15):
    bh = BUSINESS_HOURS[business_id]
    fmt = "%H:%M"
    work_start = datetime.strptime(bh["work_start"], fmt)
    work_end = datetime.strptime(bh["work_end"], fmt)
    lunch_start = datetime.strptime(bh["lunch_start"], fmt)
    lunch_end = datetime.strptime(bh["lunch_end"], fmt)

    # List of booked hours and their durations
    booked_slots = []
    for b in bookings:
        if b["date"] == date_str:
            b_start = datetime.strptime(b["time"], fmt)
            b_duration = b.get("duration", 30)  # default 30 min if not present
            booked_slots.append((b_start, b_duration))

    curr = work_start
    available = []
    step = timedelta(minutes=interval)
    while curr + timedelta(minutes=duration) <= work_end:
        # outside lunch time
        in_lunch = (curr >= lunch_start and curr < lunch_end) or (curr + timedelta(minutes=duration) > lunch_start and curr < lunch_end)
        if not in_lunch:
            collides = False
            curr_end = curr + timedelta(minutes=duration)
            for b_start, b_dur in booked_slots:
                b_end = b_start + timedelta(minutes=b_dur)
                if curr < b_end and curr_end > b_start:
                    collides = True
                    break
            if not collides:
                available.append(curr.strftime(fmt))
        curr += step
    return available

