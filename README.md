

#WhatsApp Reservation Management System (Prototype)

Backend-focused prototype of a reservation system that allows clients to book services via WhatsApp and business owners to manage appointments through an authenticated web dashboard.

The project emphasizes business logic, stateful conversations, and API integration rather than UI or infrastructure polish.

##Features

WhatsApp-based booking flow with state management
Service selection, date and time handling
Dynamic availability calculation
Persistent booking storage
Owner notification on booking confirmation
Authenticated admin dashboard with session-based access control

##Tech Stack

Python, Flask
Twilio WhatsApp API
Local database persistence (prototype)
Minimal HTML templates for admin dashboard

##Architecture

WhatsApp users interact with a Flask backend via Twilio webhooks.
The backend manages conversation state, booking logic, and persistence.
Business owners access bookings through a protected web dashboard.

##Project Status

Functional backend prototype with working WhatsApp integration and dashboard.
Runs locally and is exposed during development for webhook testing.
Not deployed to a permanent production server.

##Running Locally

Install dependencies and configure Twilio credentials.
Start the application with:
