# Lucky Number Generator

A web-based game where players generate numbers, collect items, and compete for achievements.

## Features

- Generate random numbers with various multipliers
- Collect items of different rarities
- Unlock achievements and daily rewards
- Prestige system for progression
- Admin panel for game management

## Local Development

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the development server:
   ```bash
   python app.py
   ```
5. Visit `http://localhost:5000` in your browser

## Deployment to Render

1. Create a Render account at https://render.com
2. Create a new Web Service
3. Connect your GitHub repository
4. Configure the service:
   - Name: lucky-number-generator
   - Environment: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Add environment variables:
   - `SECRET_KEY`: A secure random string
   - `ADMIN_USERNAME`: Your admin username
   - `ADMIN_PASSWORD`: Your admin password
6. Deploy!

## Admin Access

To access the admin panel:
1. Visit `/admin/login`
2. Use your admin credentials
3. Access the dashboard at `/admin`

## Security Notes

- Change the default admin credentials in production
- Use a secure secret key in production
- Enable HTTPS in production
- Regularly backup game data

## Contributing

Feel free to submit issues and enhancement requests! 
