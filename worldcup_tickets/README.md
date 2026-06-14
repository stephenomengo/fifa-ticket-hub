# World Cup Ticket Booking Website (Flask + SQLite)

A simple ticket booking website for World Cup matches, built with Python Flask, SQLite, and HTML/CSS.

## Features
- Modern, animated UI (hero banner, smooth transitions, hover effects)
- Country flags and stadium photos pulled from free CDNs (flagcdn.com, Unsplash)
- Browse upcoming World Cup matches
- User sign up / login / logout
- Interactive seat map (select seats, see live total price)
- Realistic payment page (live card preview, formatted card number/expiry, "processing" animation) — demo only, no real charges
- Animated booking confirmation / e-ticket page
- "My Tickets" page showing a user's paid bookings
- Toast-style flash notifications
- Admin panel:
  - Dashboard with stats (matches, bookings, seats sold, revenue)
  - Add / edit / delete matches
  - View all paid bookings

## Setup

1. Install Flask (if not already installed):
   ```
   pip install flask
   ```

2. Run the app:
   ```
   python app.py
   ```

3. Open your browser to: http://127.0.0.1:5000

The database (`worldcup.db`) is created automatically on first run, with sample matches pre-loaded.

## Login Details

- **Admin account:** username `admin`, password `admin123`
- **Regular users:** sign up via the "Sign Up" page

## Project Structure
```
worldcup_tickets/
├── app.py                  # Main Flask application (routes, DB logic)
├── worldcup.db              # SQLite database (created on first run)
├── static/
│   └── css/
│       └── style.css       # All styling
└── templates/
    ├── base.html            # Shared layout/navbar
    ├── index.html           # Match listing (home page)
    ├── match_detail.html     # Seat selection page
    ├── checkout.html         # Booking confirmation/ticket
    ├── my_tickets.html        # User's booked tickets
    ├── login.html
    ├── register.html
    ├── admin_dashboard.html
    ├── add_match.html
    ├── edit_match.html
    └── admin_bookings.html
```

## Notes for Extending
- This app requires an internet connection to load team flags, stadium photos, and fonts (served from flagcdn.com, Unsplash, and Google Fonts). Without internet, the site still works but images/fonts won't load.
- Passwords are stored in plain text for simplicity — for a real project, use `werkzeug.security` (`generate_password_hash` / `check_password_hash`).
- Seat layout is a fixed 6x10 grid (rows A-F, seats 1-10) — adjust in `match_detail.html` / `app.py` if you want different layouts per stadium.
- Add a "cancel booking" feature by adding a delete route for bookings and a button on `my_tickets.html`.
- To add flags/stadium images for new teams or stadiums, add entries to `COUNTRY_CODES` and `STADIUM_IMAGES` in `app.py`.
