from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
import random
import time
from datetime import datetime
import math
import threading
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')  # Change this in production

# Admin credentials
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = hashlib.sha256(os.environ.get('ADMIN_PASSWORD', 'admin123').encode()).hexdigest()

# Admin authentication decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Admin login route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin/login.html', error="Invalid credentials")
    
    return render_template('admin/login.html')

# Admin logout route
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# Admin dashboard route
@app.route('/admin')
@admin_required
def admin_dashboard():
    game_data = load_game_data()
    return render_template('admin/dashboard.html', game_data=game_data)

# Admin action routes
@app.route('/admin/add_coins', methods=['POST'])
@admin_required
def admin_add_coins():
    game_data = load_game_data()
    amount = int(request.form.get('amount', 0))
    if amount > 0:
        game_data['coins'] += amount
        save_game_data(game_data)
        return redirect(url_for('admin_dashboard', success=f'Added {amount} coins'))
    return redirect(url_for('admin_dashboard', error='Invalid amount'))

@app.route('/admin/reset_stats', methods=['POST'])
@admin_required
def admin_reset_stats():
    game_data = load_game_data()
    game_data['total_rolls'] = 0
    game_data['total_numbers'] = 0
    game_data['best_number'] = 0
    save_game_data(game_data)
    return redirect(url_for('admin_dashboard', success='Stats reset successfully'))

@app.route('/admin/reset_inventory', methods=['POST'])
@admin_required
def admin_reset_inventory():
    game_data = load_game_data()
    game_data['inventory'] = {}
    save_game_data(game_data)
    return redirect(url_for('admin_dashboard', success='Inventory reset successfully'))

@app.route('/admin/reset_prestige', methods=['POST'])
@admin_required
def admin_reset_prestige():
    game_data = load_game_data()
    game_data['prestige_level'] = 0
    game_data['prestige_multiplier'] = 1.0
    save_game_data(game_data)
    return redirect(url_for('admin_dashboard', success='Prestige reset successfully'))

@app.route('/admin/reset_all', methods=['POST'])
@admin_required
def admin_reset_all():
    game_data = {
        'coins': 0,
        'total_rolls': 0,
        'total_numbers': 0,
        'best_number': 0,
        'inventory': {},
        'active_auras': [],
        'game_passes': [],
        'prestige_level': 0,
        'prestige_multiplier': 1.0,
        'number_limit': 1000000,
        'achievements': [],
        'daily_rewards': [],
        'last_daily_reward': None
    }
    save_game_data(game_data)
    return redirect(url_for('admin_dashboard', success='Game data reset successfully'))

@app.route('/admin/give_item', methods=['POST'])
@admin_required
def admin_give_item():
    game_data = load_game_data()
    item_name = request.form.get('item_name')
    rarity = request.form.get('rarity')
    amount = int(request.form.get('amount', 1))
    
    if not item_name or not rarity or amount <= 0:
        return redirect(url_for('admin_dashboard', error='Invalid item data'))
    
    if rarity not in game_data['inventory']:
        game_data['inventory'][rarity] = {}
    
    if item_name not in game_data['inventory'][rarity]:
        game_data['inventory'][rarity][item_name] = 0
    
    game_data['inventory'][rarity][item_name] += amount
    save_game_data(game_data)
    return redirect(url_for('admin_dashboard', success=f'Added {amount} {item_name} ({rarity})'))

@app.route('/admin/give_aura', methods=['POST'])
@admin_required
def admin_give_aura():
    game_data = load_game_data()
    aura_name = request.form.get('aura_name')
    
    if not aura_name:
        return redirect(url_for('admin_dashboard', error='Invalid aura name'))
    
    if aura_name not in game_data['active_auras']:
        game_data['active_auras'].append(aura_name)
        save_game_data(game_data)
        return redirect(url_for('admin_dashboard', success=f'Added {aura_name}'))
    
    return redirect(url_for('admin_dashboard', error='Aura already owned'))

@app.route('/admin/give_pass', methods=['POST'])
@admin_required
def admin_give_pass():
    game_data = load_game_data()
    pass_name = request.form.get('pass_name')
    
    if not pass_name:
        return redirect(url_for('admin_dashboard', error='Invalid game pass name'))
    
    if pass_name not in game_data['game_passes']:
        game_data['game_passes'].append(pass_name)
        save_game_data(game_data)
        return redirect(url_for('admin_dashboard', success=f'Added {pass_name}'))
    
    return redirect(url_for('admin_dashboard', error='Game pass already owned'))

@app.route('/admin/set_prestige_level', methods=['POST'])
@admin_required
def admin_set_prestige_level():
    game_data = load_game_data()
    level = int(request.form.get('level', 0))
    
    if level < 0:
        return redirect(url_for('admin_dashboard', error='Invalid prestige level'))
    
    game_data['prestige_level'] = level
    game_data['prestige_multiplier'] = 1.0 + (level * 0.1)
    save_game_data(game_data)
    return redirect(url_for('admin_dashboard', success=f'Set prestige level to {level}'))

@app.route('/admin/set_number_limit', methods=['POST'])
@admin_required
def admin_set_number_limit():
    game_data = load_game_data()
    limit = int(request.form.get('limit', 1000000))
    
    if limit <= 0:
        return redirect(url_for('admin_dashboard', error='Invalid number limit'))
    
    game_data['number_limit'] = limit
    save_game_data(game_data)
    return redirect(url_for('admin_dashboard', success=f'Set number limit to {limit}'))

# Game data file path
GAME_DATA_FILE = 'game_data.json'

# Shop items (real money purchases)
shop_items = {
    'starter_pack': {'name': 'Starter Pack', 'coins': 1000, 'real_price': '4.99'},
    'medium_pack': {'name': 'Medium Pack', 'coins': 5000, 'real_price': '9.99'},
    'mega_pack': {'name': 'Mega Pack', 'coins': 12000, 'real_price': '19.99'},
    'ultra_pack': {'name': 'Ultra Pack', 'coins': 25000, 'real_price': '49.99'},
    'ultimate_pack': {'name': 'Ultimate Pack', 'coins': 2000000, 'real_price': '99.99'},
}

# Game items (purchased with coins)
game_items = {
    'boot': {
        'name': 'Boot',
        'description': 'A mysterious boot with no apparent use... yet.',
        'base_price': 1000000,
        'initial_supply': 1000000,
        'icon': '👢'
    },
    'emerald': {
        'name': 'Emerald',
        'description': 'A precious gem used in special events.',
        'base_price': 4500000,
        'initial_supply': 1000000,
        'icon': '💎'
    },
    'lucky_charm': {
        'name': 'Lucky Charm',
        'description': 'Increases your chances of getting better numbers.',
        'base_price': 5000000,
        'initial_supply': 1000000,
        'icon': '🍀'
    }
}

# Auras (purchased with coins)
auras = {
    'lucky_aura': {
        'name': 'Lucky Aura',
        'coins': 100000,
        'duration': '30 min',
        'effect': '+10% Better Numbers',
        'multiplier': 1.1
    },
    'golden_aura': {
        'name': 'Golden Aura',
        'coins': 250000,
        'duration': '30 min',
        'effect': '+25% Better Numbers',
        'multiplier': 1.25
    },
    'rainbow_aura': {
        'name': 'Rainbow Aura',
        'coins': 500000,
        'duration': '1 hour',
        'effect': '+50% Better Numbers',
        'multiplier': 1.5
    },
    'divine_aura': {
        'name': 'Divine Aura',
        'coins': 1000000,
        'duration': '1 hour',
        'effect': '+100% Better Numbers',
        'multiplier': 2.0
    },
    'celestial_aura': {
        'name': 'Celestial Aura',
        'coins': 2000000,
        'duration': '2 hours',
        'effect': '+200% Better Numbers',
        'multiplier': 3.0
    }
}

# Define achievements
achievements = {
    'rolls_100': {
        'name': 'Rolling Beginner',
        'description': 'Roll 100 times',
        'reward': 1000000,
        'icon': '🎲'
    },
    'rolls_1000': {
        'name': 'Rolling Enthusiast',
        'description': 'Roll 1,000 times',
        'reward': 5000000,
        'icon': '🎲'
    },
    'rolls_10000': {
        'name': 'Rolling Master',
        'description': 'Roll 10,000 times',
        'reward': 20000000,
        'icon': '🎲'
    },
    'best_1000': {
        'name': 'Lucky One',
        'description': 'Get a roll of 1/1,000 or better',
        'reward': 5000000,
        'icon': '🍀'
    },
    'best_10000': {
        'name': 'Super Lucky',
        'description': 'Get a roll of 1/10,000 or better',
        'reward': 15000000,
        'icon': '🍀'
    },
    'best_100000': {
        'name': 'Extremely Lucky',
        'description': 'Get a roll of 1/100,000 or better',
        'reward': 50000000,
        'icon': '🍀'
    },
    'best_1000000': {
        'name': 'Legendary Luck',
        'description': 'Get a roll of 1/1,000,000 or better',
        'reward': 200000000,
        'icon': '🍀'
    },
    'coins_10000': {
        'name': 'Small Fortune',
        'description': 'Accumulate 10,000 coins',
        'reward': 5000000,
        'icon': '💰'
    },
    'coins_100000': {
        'name': 'Medium Fortune',
        'description': 'Accumulate 100,000 coins',
        'reward': 20000000,
        'icon': '💰'
    },
    'coins_1000000': {
        'name': 'Large Fortune',
        'description': 'Accumulate 1,000,000 coins',
        'reward': 100000000,
        'icon': '💰'
    },
    'all_auras': {
        'name': 'Aura Collector',
        'description': 'Own all auras at least once',
        'reward': 50000000,
        'icon': '✨'
    },
    'all_passes': {
        'name': 'Premium Player',
        'description': 'Own all game passes',
        'reward': 100000000,
        'icon': '👑'
    }
}

# Define daily rewards
daily_rewards = [
    {'day': 1, 'coins': 100000, 'name': 'Day 1', 'icon': '🎁'},
    {'day': 2, 'coins': 200000, 'name': 'Day 2', 'icon': '🎁'},
    {'day': 3, 'coins': 300000, 'name': 'Day 3', 'icon': '🎁'},
    {'day': 4, 'coins': 400000, 'name': 'Day 4', 'icon': '🎁'},
    {'day': 5, 'coins': 500000, 'name': 'Day 5', 'icon': '🎁'},
    {'day': 6, 'coins': 600000, 'name': 'Day 6', 'icon': '🎁'},
    {'day': 7, 'coins': 1000000, 'name': 'Day 7', 'icon': '🌟'}
]

# Define prestige upgrades
prestige_upgrades = {
    'coin_multiplier': {
        'name': 'Coin Multiplier',
        'description': 'Increase coin earnings by 10%',
        'cost': 50000000,  # Increased from 5,000,000
        'effect': 0.1,
        'max_level': 10
    },
    'luck_boost': {
        'name': 'Luck Boost',
        'description': 'Increase your luck by 5%',
        'cost': 100000000,  # Increased from 10,000,000
        'effect': 0.05,
        'max_level': 5
    },
    'limit_increase': {
        'name': 'Limit Increase',
        'description': 'Increase your number limit by 50M',
        'cost': 200000000,  # Increased from 20,000,000
        'effect': 50000000,
        'max_level': 10
    }
}

# Add this after the other global variables
bots = []
bot_names = [
    "LuckyBot", "NumberNinja", "RollMaster", "CoinCollector", "GambleGuru",
    "LuckyLarry", "RollingRandy", "NumberNerd", "CoinKing", "GambleGirl",
    "LuckyLucy", "RollingRob", "NumberNick", "CoinCarla", "GambleGary"
]

# Bot class to simulate players
class Bot:
    def __init__(self, name):
        self.name = name
        self.coins = random.randint(10000, 100000)
        self.best_number = 0
        self.total_rolls = 0
        self.last_active = time.time()
        self.active = True
    
    def generate_number(self):
        # Simulate number generation
        base_number = int(random.uniform(1, 1000000 ** 0.7) ** (1/0.7))
        self.best_number = max(self.best_number, base_number)
        self.total_rolls += 1
        self.coins += 200  # Fixed coin earnings (increased from 20)
        self.last_active = time.time()
        return base_number
    
    def gamble(self):
        # Simulate gambling
        if self.coins < 1000:
            return
        
        bet_amount = random.randint(1000, min(10000, self.coins))
        min_val = random.randint(1, 100000)
        max_val = min_val + random.randint(100, 10000)
        
        # Generate a number
        base_number = int(random.uniform(1, 1000000 ** 0.7) ** (1/0.7))
        
        # Check if bot won
        won = min_val <= base_number <= max_val
        
        # Calculate payout
        range_size = max_val - min_val
        total_range = 1000000
        probability = range_size / total_range
        payout_multiplier = min(1 / probability, 100)
        
        # Update coins
        if won:
            winnings = int(bet_amount * payout_multiplier)
            self.coins += winnings - bet_amount
        else:
            self.coins -= bet_amount
        
        self.last_active = time.time()
    
    def buy_item(self):
        # Simulate buying items
        if self.coins < 10000:
            return
        
        # Randomly select an item
        item_id = random.choice(list(game_items.keys()))
        item = game_items[item_id]
        
        # Check if bot can afford it
        if self.coins >= item['base_price']:
            self.coins -= item['base_price']
            self.last_active = time.time()

# Bot activity thread
def bot_activity_thread():
    global bots
    
    # Create initial bots
    for name in bot_names:
        bots.append(Bot(name))
    
    while True:
        # Update bot activities
        for bot in bots:
            if not bot.active:
                continue
                
            # Randomly choose an activity
            activity = random.choice(['generate', 'gamble', 'buy_item'])
            
            if activity == 'generate':
                bot.generate_number()
            elif activity == 'gamble':
                bot.gamble()
            elif activity == 'buy_item':
                bot.buy_item()
            
            # Add longer delays between actions to simulate human behavior
            # Random delay between 30-120 seconds (30 seconds to 2 minutes)
            time.sleep(random.uniform(30, 120))
        
        # Sleep before next round of bot activities
        time.sleep(60)  # Wait a minute before the next round

# Initialize bot thread when the app is created
bot_thread = threading.Thread(target=bot_activity_thread)
bot_thread.daemon = True
bot_thread.start()

def load_game_data():
    try:
        with open('game_data.json', 'r') as f:
            data = json.load(f)
            
            # Ensure inventory has the correct structure
            if 'inventory' not in data:
                data['inventory'] = {}
                
            # Ensure each rarity category exists in inventory
            for rarity in item_rarities.keys():
                if rarity not in data['inventory']:
                    data['inventory'][rarity] = []
                    
            return data
    except FileNotFoundError:
        # Initialize with default values if file doesn't exist
        return {
            'coins': 1000,
            'stats': {
                'total_rolls': 0,
                'best_number': 0,
                'total_numbers': 0
            },
            'inventory': {rarity: [] for rarity in item_rarities.keys()},
            'active_auras': [],
            'game_passes': {
                'triple_generate': False,
                'double_luck': False,
                'auto_generate': False
            },
            'auto_generate_active': False,
            'number_limit': 1000000,
            'prestige': {
                'level': 0,
                'multiplier': 1.0,
                'points': 0,
                'upgrades': {
                    'coin_multiplier': 0,
                    'luck_boost': 0,
                    'limit_increase': 0
                }
            },
            'daily_rewards': {
                'last_claim': None,
                'streak': 0
            },
            'achievements': {
                'unlocked': []
            },
            'market': {}
        }

def save_game_data(game_data):
    try:
        if 'active_auras' not in game_data:
            game_data['active_auras'] = []
        if 'stats' not in game_data:
            game_data['stats'] = {
                'total_rolls': 0,
                'best_number': 0,
                'total_numbers': 0
            }
        if 'game_passes' not in game_data:
            game_data['game_passes'] = {
                'triple_generate': False,
                'double_luck': False,
                'auto_generate': False
            }
        if 'auto_generate_active' not in game_data:
            game_data['auto_generate_active'] = False
        
        with open(GAME_DATA_FILE, 'w') as f:
            json.dump(game_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving game data: {e}")
        return False

def calculate_aura_multiplier(active_auras):
    multiplier = 1.0
    for aura in active_auras:
        if aura['id'] in auras:
            multiplier *= auras[aura['id']]['multiplier']
    return multiplier

def check_achievements(game_data):
    """Check and update achievements based on current game state"""
    new_achievements = []
    
    # Check roll count achievements
    if game_data['stats']['total_rolls'] >= 100 and 'rolls_100' not in game_data['achievements']['unlocked']:
        new_achievements.append('rolls_100')
    if game_data['stats']['total_rolls'] >= 1000 and 'rolls_1000' not in game_data['achievements']['unlocked']:
        new_achievements.append('rolls_1000')
    if game_data['stats']['total_rolls'] >= 10000 and 'rolls_10000' not in game_data['achievements']['unlocked']:
        new_achievements.append('rolls_10000')
    
    # Check best number achievements
    if game_data['stats']['best_number'] >= 1000 and 'best_1000' not in game_data['achievements']['unlocked']:
        new_achievements.append('best_1000')
    if game_data['stats']['best_number'] >= 10000 and 'best_10000' not in game_data['achievements']['unlocked']:
        new_achievements.append('best_10000')
    if game_data['stats']['best_number'] >= 100000 and 'best_100000' not in game_data['achievements']['unlocked']:
        new_achievements.append('best_100000')
    if game_data['stats']['best_number'] >= 1000000 and 'best_1000000' not in game_data['achievements']['unlocked']:
        new_achievements.append('best_1000000')
    
    # Check coin achievements
    if game_data['coins'] >= 10000 and 'coins_10000' not in game_data['achievements']['unlocked']:
        new_achievements.append('coins_10000')
    if game_data['coins'] >= 100000 and 'coins_100000' not in game_data['achievements']['unlocked']:
        new_achievements.append('coins_100000')
    if game_data['coins'] >= 1000000 and 'coins_1000000' not in game_data['achievements']['unlocked']:
        new_achievements.append('coins_1000000')
    
    # Check aura collection achievement
    aura_ids = [aura['id'] for aura in game_data['active_auras']]
    all_aura_ids = set(auras.keys())
    if all(aura_id in aura_ids for aura_id in all_aura_ids) and 'all_auras' not in game_data['achievements']['unlocked']:
        new_achievements.append('all_auras')
    
    # Check game pass achievement
    if all(game_data['game_passes'].values()) and 'all_passes' not in game_data['achievements']['unlocked']:
        new_achievements.append('all_passes')
    
    # Add new achievements and award coins
    for achievement_id in new_achievements:
        if achievement_id not in game_data['achievements']['unlocked']:
            game_data['achievements']['unlocked'].append(achievement_id)
            game_data['coins'] += achievements[achievement_id]['reward']
    
    return new_achievements

@app.route('/')
def index():
    game_data = load_game_data()
    return render_template('index.html', 
                         game_data=game_data, 
                         shop_items=shop_items,
                         auras=auras,
                         achievements=achievements,
                         daily_rewards=daily_rewards,
                         game_items=game_items)

@app.route('/buy_pack', methods=['POST'])
def buy_pack():
    pack_id = request.form.get('item_id')
    if pack_id not in shop_items:
        return jsonify({'success': False, 'message': 'Invalid pack!'})
    
    game_data = load_game_data()
    pack = shop_items[pack_id]
    
    game_data['coins'] += pack['coins']
    
    if not save_game_data(game_data):
        return jsonify({'success': False, 'message': 'Error saving game data!'})
    
    return jsonify({
        'success': True,
        'message': f'Successfully purchased {pack["name"]}! Added {pack["coins"]} coins!',
        'new_balance': game_data['coins']
    })

@app.route('/buy_aura', methods=['POST'])
def buy_aura():
    aura_id = request.form.get('aura_id')
    if aura_id not in auras:
        return jsonify({'success': False, 'message': f'Invalid aura: {aura_id}'})
    
    game_data = load_game_data()
    aura = auras[aura_id]
    
    try:
        if game_data['coins'] < aura['coins']:
            return jsonify({'success': False, 'message': 'Not enough coins!'})
        
        game_data['coins'] -= aura['coins']
        
        if 'active_auras' not in game_data:
            game_data['active_auras'] = []
            
        game_data['active_auras'].append({
            'id': aura_id,
            'name': aura['name'],
            'effect': aura['effect'],
            'duration': aura['duration'],
            'activated_at': time.time()
        })
        
        if not save_game_data(game_data):
            return jsonify({'success': False, 'message': 'Error saving game data!'})
        
        return jsonify({
            'success': True,
            'message': f'Successfully activated {aura["name"]}!',
            'new_balance': game_data['coins']
        })
    except Exception as e:
        print(f"Error processing aura purchase: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})

@app.route('/buy_game_pass', methods=['POST'])
def buy_game_pass():
    pass_id = request.form.get('pass_id')
    game_data = load_game_data()
    
    # Game pass prices in real money
    pass_prices = {
        'triple_generate': {'price': '14.99', 'name': 'Triple Generate Pass'},
        'double_luck': {'price': '19.99', 'name': 'Double Luck Pass'},
        'auto_generate': {'price': '24.99', 'name': 'Auto Generate Pass'}
    }
    
    if pass_id not in pass_prices:
        return jsonify({'success': False, 'message': 'Invalid game pass!'})
    
    if game_data['game_passes'][pass_id]:
        return jsonify({'success': False, 'message': 'You already own this game pass!'})
    
    # In a real implementation, you would process payment here
    # For this demo, we'll just simulate a successful purchase
    
    game_data['game_passes'][pass_id] = True
    
    if not save_game_data(game_data):
        return jsonify({'success': False, 'message': 'Error saving game data!'})
    
    return jsonify({
        'success': True,
        'message': f'Successfully purchased the {pass_prices[pass_id]["name"]}!',
        'new_balance': game_data['coins']
    })

@app.route('/toggle_auto_generate', methods=['POST'])
def toggle_auto_generate():
    game_data = load_game_data()
    
    if not game_data['game_passes']['auto_generate']:
        return jsonify({'success': False, 'message': 'You need to purchase the Auto Generate Pass first!'})
    
    game_data['auto_generate_active'] = not game_data['auto_generate_active']
    
    if not save_game_data(game_data):
        return jsonify({'success': False, 'message': 'Error saving game data!'})
    
    status = "activated" if game_data['auto_generate_active'] else "deactivated"
    return jsonify({
        'success': True,
        'message': f'Auto Generate {status}!',
        'is_active': game_data['auto_generate_active']
    })

@app.route('/increase_limit', methods=['POST'])
def increase_limit():
    game_data = load_game_data()
    
    # Increase the cost to increase the limit
    increase_cost = 50000000  # Changed from 5,000,000
    
    if game_data['coins'] < increase_cost:
        return jsonify({'success': False, 'message': f'Not enough coins! You need {increase_cost:,} coins to increase the limit.'})
    
    # Deduct coins
    game_data['coins'] -= increase_cost
    
    # Increase the limit by 100 million
    game_data['number_limit'] += 100000000
    
    if not save_game_data(game_data):
        return jsonify({'success': False, 'message': 'Error saving game data!'})
    
    return jsonify({
        'success': True,
        'message': f'Successfully increased the number limit to {game_data["number_limit"]:,}!',
        'new_limit': game_data['number_limit'],
        'new_balance': game_data['coins']
    })

@app.route('/prestige', methods=['POST'])
def prestige():
    game_data = load_game_data()
    
    # Calculate prestige points based on best number and total rolls
    best_number = game_data['stats']['best_number']
    total_rolls = game_data['stats']['total_rolls']
    
    # Formula: sqrt(best_number) * log10(total_rolls + 1)
    prestige_points = int((best_number ** 0.5) * (math.log10(total_rolls + 1)))
    
    # Calculate new multiplier
    new_multiplier = 1.0 + (prestige_points * 0.1)
    
    # Update prestige data
    game_data['prestige']['level'] += 1
    game_data['prestige']['multiplier'] = new_multiplier
    game_data['prestige']['total_resets'] += 1
    
    # Reset game data but keep prestige and owned passes
    owned_passes = game_data.get('game_passes', {}).values()
    prestige_data = game_data['prestige']
    
    # Create new game data
    game_data = {
        'coins': 1000,  # Starting bonus
        'stats': {
            'total_rolls': 0,
            'total_numbers': 0,
            'best_number': 0
        },
        'active_auras': [],
        'game_passes': {
            'triple_generate': False,
            'double_luck': False,
            'auto_generate': False
        },
        'number_limit': 985000000,
        'daily_rewards': {
            'last_claim': None,
            'streak': 0
        },
        'prestige': prestige_data
    }
    
    # Save game data
    save_game_data(game_data)
    
    return jsonify({
        'success': True,
        'message': f'Prestiged! You gained a {new_multiplier:.1f}x multiplier!',
        'prestige_points': prestige_points,
        'new_multiplier': new_multiplier,
        'prestige_level': game_data['prestige']['level']
    })

@app.route('/buy_prestige_upgrade', methods=['POST'])
def buy_prestige_upgrade():
    upgrade_id = request.form.get('upgrade_id')
    game_data = load_game_data()
    
    if upgrade_id not in prestige_upgrades:
        return jsonify({'success': False, 'message': 'Invalid upgrade!'})
    
    upgrade = prestige_upgrades[upgrade_id]
    current_level = game_data['prestige'].get(upgrade_id, 0)
    
    if current_level >= upgrade['max_level']:
        return jsonify({'success': False, 'message': 'This upgrade is already at max level!'})
    
    cost = upgrade['cost'] * (current_level + 1)  # Cost increases with level
    
    if game_data['coins'] < cost:
        return jsonify({'success': False, 'message': f'Not enough coins! You need {cost:,} coins.'})
    
    # Deduct coins
    game_data['coins'] -= cost
    
    # Apply upgrade effect
    if upgrade_id == 'coin_multiplier':
        game_data['prestige']['multiplier'] += upgrade['effect']
    elif upgrade_id == 'luck_boost':
        # This will be applied in the generate_number function
        pass
    elif upgrade_id == 'limit_increase':
        game_data['number_limit'] += upgrade['effect']
    
    # Update upgrade level
    game_data['prestige'][upgrade_id] = current_level + 1
    
    # Save game data
    save_game_data(game_data)
    
    return jsonify({
        'success': True,
        'message': f'Purchased {upgrade["name"]} level {current_level + 1}!',
        'new_balance': game_data['coins'],
        'new_level': current_level + 1,
        'new_multiplier': game_data['prestige']['multiplier'],
        'new_limit': game_data['number_limit']
    })

@app.route('/get_prestige_info', methods=['GET'])
def get_prestige_info():
    game_data = load_game_data()
    
    # Calculate prestige points based on best number and total rolls
    best_number = game_data['stats']['best_number']
    total_rolls = game_data['stats']['total_rolls']
    
    # Formula: sqrt(best_number) * log10(total_rolls + 1)
    prestige_points = int((best_number ** 0.5) * (math.log10(total_rolls + 1)))
    
    # Calculate next multiplier
    next_multiplier = 1.0 + ((game_data['prestige']['level'] + 1) * 0.1)
    
    # Get upgrade levels
    upgrade_levels = {}
    for upgrade_id in prestige_upgrades:
        upgrade_levels[upgrade_id] = game_data['prestige'].get(upgrade_id, 0)
    
    return jsonify({
        'success': True,
        'prestige_level': game_data['prestige']['level'],
        'current_multiplier': game_data['prestige']['multiplier'],
        'next_multiplier': next_multiplier,
        'prestige_points': prestige_points,
        'upgrade_levels': upgrade_levels
    })

@app.route('/generate_number', methods=['POST'])
def generate_number():
    game_data = load_game_data()
    
    # Calculate total multiplier from active auras
    multiplier = calculate_aura_multiplier(game_data['active_auras'])
    
    # Apply double luck if owned
    if game_data['game_passes']['double_luck']:
        multiplier *= 2
    
    # Apply prestige multiplier
    multiplier *= game_data['prestige']['multiplier']
    
    # Apply luck boost from prestige
    luck_boost_level = game_data['prestige'].get('luck_boost', 0)
    if luck_boost_level > 0:
        luck_boost = prestige_upgrades['luck_boost']['effect'] * luck_boost_level
        multiplier *= (1 + luck_boost)
    
    # Generate a random number between 1 and the current limit
    # Make it harder by using a higher minimum number and a more challenging distribution
    # Use a power distribution to make higher numbers rarer
    base_number = int(random.uniform(1, game_data['number_limit'] ** 0.7) ** (1/0.7))
    boosted_number = int(base_number * multiplier)
    
    # Update stats
    game_data['stats']['total_rolls'] += 1
    game_data['stats']['total_numbers'] += base_number
    game_data['stats']['best_number'] = max(game_data['stats']['best_number'], base_number)
    
    # Fixed coin earnings to 200 coins per roll (increased from 20)
    coins_earned = 200
    game_data['coins'] += coins_earned
    
    # Check for target number achievements
    target_rewards = []
    if base_number >= game_data['target_numbers']['easy']:
        target_rewards.append({
            'target': 'easy',
            'reward': game_data['target_numbers']['rewards']['easy']
        })
        game_data['coins'] += game_data['target_numbers']['rewards']['easy']
        coins_earned += game_data['target_numbers']['rewards']['easy']
    
    if base_number >= game_data['target_numbers']['medium']:
        target_rewards.append({
            'target': 'medium',
            'reward': game_data['target_numbers']['rewards']['medium']
        })
        game_data['coins'] += game_data['target_numbers']['rewards']['medium']
        coins_earned += game_data['target_numbers']['rewards']['medium']
    
    if base_number >= game_data['target_numbers']['hard']:
        target_rewards.append({
            'target': 'hard',
            'reward': game_data['target_numbers']['rewards']['hard']
        })
        game_data['coins'] += game_data['target_numbers']['rewards']['hard']
        coins_earned += game_data['target_numbers']['rewards']['hard']
    
    # Check for new achievements
    new_achievements = check_achievements(game_data)
    
    # Save game data
    save_game_data(game_data)
    
    # Check if triple generate is active
    if game_data['game_passes']['triple_generate']:
        # Generate two more numbers
        results = []
        for _ in range(2):
            # Use the same power distribution for additional rolls
            base_number = int(random.uniform(1, game_data['number_limit'] ** 0.7) ** (1/0.7))
            boosted_number = int(base_number * multiplier)
            
            # Update stats
            game_data['stats']['total_rolls'] += 1
            game_data['stats']['total_numbers'] += base_number
            game_data['stats']['best_number'] = max(game_data['stats']['best_number'], base_number)
            
            # Add coins for each roll
            coins_earned += 200
            game_data['coins'] += 200
            
            # Check for target number achievements
            if base_number >= game_data['target_numbers']['easy']:
                target_rewards.append({
                    'target': 'easy',
                    'reward': game_data['target_numbers']['rewards']['easy']
                })
                game_data['coins'] += game_data['target_numbers']['rewards']['easy']
                coins_earned += game_data['target_numbers']['rewards']['easy']
            
            if base_number >= game_data['target_numbers']['medium']:
                target_rewards.append({
                    'target': 'medium',
                    'reward': game_data['target_numbers']['rewards']['medium']
                })
                game_data['coins'] += game_data['target_numbers']['rewards']['medium']
                coins_earned += game_data['target_numbers']['rewards']['medium']
            
            if base_number >= game_data['target_numbers']['hard']:
                target_rewards.append({
                    'target': 'hard',
                    'reward': game_data['target_numbers']['rewards']['hard']
                })
                game_data['coins'] += game_data['target_numbers']['rewards']['hard']
                coins_earned += game_data['target_numbers']['rewards']['hard']
            
            results.append({
                'base_probability': 1 / base_number,
                'boosted_probability': 1 / boosted_number,
                'target_rewards': target_rewards
            })
        
        # Save game data again after all rolls
        save_game_data(game_data)
        
        return jsonify({
            'success': True,
            'base_probability': 1 / base_number,
            'boosted_probability': 1 / boosted_number,
            'multiplier': multiplier,
            'stats': game_data['stats'],
            'coins_earned': coins_earned,
            'new_balance': game_data['coins'],
            'new_achievements': new_achievements,
            'triple_generate': True,
            'additional_results': results,
            'target_rewards': target_rewards
        })
    
    return jsonify({
        'success': True,
        'base_probability': 1 / base_number,
        'boosted_probability': 1 / boosted_number,
        'multiplier': multiplier,
        'stats': game_data['stats'],
        'coins_earned': coins_earned,
        'new_balance': game_data['coins'],
        'new_achievements': new_achievements,
        'triple_generate': False,
        'target_rewards': target_rewards
    })

@app.route('/reroll', methods=['POST'])
def reroll():
    game_data = load_game_data()
    
    # Check if player has enough coins
    if game_data['coins'] < 5000:  # Increased from 500 to 5000
    
        return jsonify({
            'success': False,
            'message': 'Not enough coins! You need 5000 coins to reroll.'
        })
    
    # Deduct coins
    game_data['coins'] -= 5000  # Increased from 500 to 5000
    
    # Calculate total multiplier from active auras
    multiplier = calculate_aura_multiplier(game_data['active_auras'])
    
    # Apply double luck if owned
    if game_data['game_passes']['double_luck']:
        multiplier *= 2
    
    # Apply prestige multiplier
    multiplier *= game_data['prestige']['multiplier']
    
    # Apply luck boost from prestige
    luck_boost_level = game_data['prestige'].get('luck_boost', 0)
    if luck_boost_level > 0:
        luck_boost = prestige_upgrades['luck_boost']['effect'] * luck_boost_level
        multiplier *= (1 + luck_boost)
    
    # Generate a new number using the same challenging distribution
    base_number = int(random.uniform(1, game_data['number_limit'] ** 0.7) ** (1/0.7))
    boosted_number = int(base_number * multiplier)
    
    # Calculate improvement
    improvement = 0
    if base_number > game_data['stats']['best_number']:
        improvement = base_number - game_data['stats']['best_number']
        game_data['stats']['best_number'] = base_number
    
    # Update stats
    game_data['stats']['total_rolls'] += 1
    game_data['stats']['total_numbers'] += base_number
    
    # Save game data
    save_game_data(game_data)
    
    return jsonify({
        'success': True,
        'base_probability': 1 / base_number,
        'boosted_probability': 1 / boosted_number,
        'multiplier': multiplier,
        'stats': game_data['stats'],
        'improvement': improvement,
        'new_balance': game_data['coins']
    })

@app.route('/check_achievements', methods=['POST'])
def check_achievements_route():
    game_data = load_game_data()
    new_achievements = check_achievements(game_data)
    
    if new_achievements:
        save_game_data(game_data)
        achievement_details = [{
            'id': achievement_id,
            'name': achievements[achievement_id]['name'],
            'description': achievements[achievement_id]['description'],
            'reward': achievements[achievement_id]['reward'],
            'icon': achievements[achievement_id]['icon']
        } for achievement_id in new_achievements]
        
        return jsonify({
            'success': True,
            'new_achievements': achievement_details,
            'new_balance': game_data['coins']
        })
    
    return jsonify({'success': False, 'message': 'No new achievements unlocked.'})

@app.route('/get_achievements', methods=['GET'])
def get_achievements():
    game_data = load_game_data()
    
    all_achievements = []
    for achievement_id, achievement in achievements.items():
        unlocked = achievement_id in game_data['achievements']['unlocked']
        all_achievements.append({
            'id': achievement_id,
            'name': achievement['name'],
            'description': achievement['description'],
            'reward': achievement['reward'],
            'icon': achievement['icon'],
            'unlocked': unlocked
        })
    
    return jsonify({
        'success': True,
        'achievements': all_achievements
    })

@app.route('/get_daily_reward_status')
def get_daily_reward_status():
    game_data = load_game_data()
    last_claim = game_data['daily_rewards']['last_claim']
    streak = game_data['daily_rewards']['streak']
    
    # Check if can claim today
    can_claim = True
    if last_claim:
        last_claim_date = datetime.strptime(last_claim, '%Y-%m-%d').date()
        today = datetime.now().date()
        
        if last_claim_date == today:
            can_claim = False
        elif (today - last_claim_date).days > 1:
            streak = 0
    
    return jsonify({
        'success': True,
        'can_claim': can_claim,
        'streak': streak
    })

@app.route('/claim_daily_reward', methods=['POST'])
def claim_daily_reward():
    game_data = load_game_data()
    last_claim = game_data['daily_rewards']['last_claim']
    streak = game_data['daily_rewards']['streak']
    today = datetime.now().date()
    
    # Check if already claimed today
    if last_claim:
        last_claim_date = datetime.strptime(last_claim, '%Y-%m-%d').date()
        if last_claim_date == today:
            return jsonify({
                'success': False,
                'message': 'You have already claimed your daily reward today!'
            })
        
        # Check if streak should reset
        if (today - last_claim_date).days > 1:
            streak = 0
    
    # Increment streak and get reward
    streak = (streak + 1) % 7
    reward = daily_rewards[streak]
    
    # Add coins
    game_data['coins'] += reward['coins']
    game_data['daily_rewards']['last_claim'] = today.strftime('%Y-%m-%d')
    game_data['daily_rewards']['streak'] = streak
    
    # Check for new achievements
    new_achievements = check_achievements(game_data)
    
    # Save game data
    save_game_data(game_data)
    
    return jsonify({
        'success': True,
        'message': f'Claimed {reward["coins"]} coins for {reward["name"]}!',
        'new_balance': game_data['coins'],
        'streak': streak,
        'new_achievements': new_achievements
    })

@app.route('/buy_coins', methods=['POST'])
def buy_coins():
    game_data = load_game_data()
    amount = request.form.get('amount', type=int)
    
    if amount not in [100000, 250000]:
        return jsonify({'success': False, 'message': 'Invalid coin amount!'})
    
    # In a real application, you would integrate with a payment processor here
    # For now, we'll just add the coins directly
    game_data['coins'] += amount
    
    if not save_game_data(game_data):
        return jsonify({'success': False, 'message': 'Error saving game data!'})
    
    return jsonify({
        'success': True,
        'message': f'Successfully purchased {amount:,} coins!',
        'new_balance': game_data['coins']
    })

@app.route('/items')
def items():
    game_data = load_game_data()
    return render_template('items.html', game_data=game_data)

@app.route('/get_market_info')
def get_market_info():
    game_data = load_game_data()
    market_info = {}
    for item_id, item in game_items.items():
        market_data = game_data['market'][item_id]
        market_info[item_id] = {
            'name': item['name'],
            'description': item['description'],
            'icon': item['icon'],
            'price': market_data['price'],
            'supply': market_data['supply'],
            'owned': game_data['inventory'].get(item_id, 0)
        }
    return jsonify({'success': True, 'market_info': market_info})

@app.route('/buy_item', methods=['POST'])
def buy_item():
    game_data = load_game_data()
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))
    
    if item_id not in game_items:
        return jsonify({'success': False, 'message': 'Invalid item'})
    
    market_data = game_data['market'][item_id]
    total_cost = market_data['price'] * quantity
    
    if game_data['coins'] < total_cost:
        return jsonify({'success': False, 'message': 'Not enough coins'})
    
    if market_data['supply'] < quantity:
        return jsonify({'success': False, 'message': 'Not enough supply'})
    
    # Update coins and inventory
    game_data['coins'] -= total_cost
    game_data['inventory'][item_id] = game_data['inventory'].get(item_id, 0) + quantity
    market_data['supply'] -= quantity
    
    # Update price based on supply and demand
    supply_ratio = market_data['supply'] / game_items[item_id]['initial_supply']
    price_multiplier = 1 / (supply_ratio ** 0.5)  # Price increases as supply decreases
    market_data['price'] = int(game_items[item_id]['base_price'] * price_multiplier)
    
    save_game_data(game_data)
    
    # Get updated market info
    market_info = {}
    for item_id, item in game_items.items():
        market_data = game_data['market'][item_id]
        market_info[item_id] = {
            'name': item['name'],
            'description': item['description'],
            'icon': item['icon'],
            'price': market_data['price'],
            'supply': market_data['supply'],
            'owned': game_data['inventory'].get(item_id, 0)
        }
    
    return jsonify({
        'success': True,
        'message': f'Successfully purchased {quantity} {game_items[item_id]["name"]}(s)',
        'new_balance': game_data['coins'],
        'new_market': market_info
    })

@app.route('/gamble', methods=['POST'])
def gamble():
    game_data = load_game_data()
    bet_amount = int(request.form.get('bet_amount', 0))
    target_range = request.form.get('target_range', '')
    
    # Validate bet amount
    if bet_amount <= 0 or bet_amount > game_data['coins']:
        return jsonify({'success': False, 'message': 'Invalid bet amount'})
    
    # Parse target range (e.g., "1-100", "1000-2000")
    try:
        min_val, max_val = map(int, target_range.split('-'))
        if min_val >= max_val:
            return jsonify({'success': False, 'message': 'Invalid range'})
    except:
        return jsonify({'success': False, 'message': 'Invalid range format'})
    
    # Generate a number
    base_number = int(random.uniform(1, game_data['number_limit'] ** 0.7) ** (1/0.7))
    
    # Check if player won
    won = min_val <= base_number <= max_val
    
    # Calculate payout (higher risk = higher reward)
    range_size = max_val - min_val
    total_range = game_data['number_limit']
    probability = range_size / total_range
    payout_multiplier = 1 / probability  # Inverse of probability
    
    # Cap the multiplier to prevent excessive rewards
    payout_multiplier = min(payout_multiplier, 100)
    
    # Update coins
    if won:
        winnings = int(bet_amount * payout_multiplier)
        game_data['coins'] += winnings - bet_amount
        message = f'You won {winnings - bet_amount} coins!'
    else:
        game_data['coins'] -= bet_amount
        message = f'You lost {bet_amount} coins!'
    
    # Save game data
    save_game_data(game_data)
    
    return jsonify({
        'success': True,
        'message': message,
        'number': base_number,
        'new_balance': game_data['coins']
    })

@app.route('/gamble')
def gamble_page():
    game_data = load_game_data()
    return render_template('gamble.html', game_data=game_data)

@app.route('/leaderboard')
def leaderboard():
    # Combine real player data with bot data
    game_data = load_game_data()
    
    # Create player entry
    player_entry = {
        'name': 'You',
        'coins': game_data['coins'],
        'best_number': game_data['stats']['best_number'],
        'total_rolls': game_data['stats']['total_rolls']
    }
    
    # Create leaderboard entries
    leaderboard_entries = []
    
    # Add player
    leaderboard_entries.append(player_entry)
    
    # Add bots
    for bot in bots:
        if bot.active:
            leaderboard_entries.append({
                'name': bot.name,
                'coins': bot.coins,
                'best_number': bot.best_number,
                'total_rolls': bot.total_rolls
            })
    
    # Sort by coins (descending)
    leaderboard_entries.sort(key=lambda x: x['coins'], reverse=True)
    
    return render_template('leaderboard.html', 
                         leaderboard=leaderboard_entries,
                         game_data=game_data)

# Item rarity definitions
item_rarities = {
    'common': {'chance': 50, 'color': '#969696', 'multiplier': 1},
    'rare': {'chance': 25, 'color': '#0096FF', 'multiplier': 2},
    'mythical': {'chance': 15, 'color': '#9400D3', 'multiplier': 3},
    'legendary': {'chance': 5, 'color': '#FFD700', 'multiplier': 4},
    'sub-reborn': {'chance': 4, 'color': '#FF4500', 'multiplier': 5},
    'grandmaster': {'chance': 1, 'color': '#00FF00', 'multiplier': 10}
}

# Item definitions for each rarity
items_by_rarity = {
    'common': [
        {'name': 'Wooden Sword', 'value': 10000, 'icon': '🗡️'},
        {'name': 'Leather Armor', 'value': 15000, 'icon': '🥋'},
        {'name': 'Basic Shield', 'value': 12000, 'icon': '🛡️'},
        {'name': 'Training Boots', 'value': 8000, 'icon': '👢'},
        {'name': 'Simple Potion', 'value': 5000, 'icon': '🧪'}
    ],
    'rare': [
        {'name': 'Iron Sword', 'value': 30000, 'icon': '⚔️'},
        {'name': 'Chain Mail', 'value': 40000, 'icon': '🔗'},
        {'name': 'Steel Shield', 'value': 35000, 'icon': '🛡️'},
        {'name': 'Swift Boots', 'value': 25000, 'icon': '👢'},
        {'name': 'Health Potion', 'value': 20000, 'icon': '🧪'}
    ],
    'mythical': [
        {'name': 'Dragon Sword', 'value': 100000, 'icon': '🐉'},
        {'name': 'Dragon Scale Armor', 'value': 120000, 'icon': '🐲'},
        {'name': 'Dragon Shield', 'value': 110000, 'icon': '🛡️'},
        {'name': 'Dragon Boots', 'value': 90000, 'icon': '👢'},
        {'name': 'Dragon Blood', 'value': 80000, 'icon': '🧪'}
    ],
    'legendary': [
        {'name': 'Excalibur', 'value': 300000, 'icon': '⚔️'},
        {'name': 'God Armor', 'value': 350000, 'icon': '👑'},
        {'name': 'Aegis Shield', 'value': 320000, 'icon': '🛡️'},
        {'name': 'Hermes Boots', 'value': 280000, 'icon': '👢'},
        {'name': 'Ambrosia', 'value': 250000, 'icon': '🧪'}
    ],
    'sub-reborn': [
        {'name': 'Void Blade', 'value': 800000, 'icon': '🌌'},
        {'name': 'Void Armor', 'value': 900000, 'icon': '🌠'},
        {'name': 'Void Shield', 'value': 850000, 'icon': '🛡️'},
        {'name': 'Void Boots', 'value': 750000, 'icon': '👢'},
        {'name': 'Void Essence', 'value': 700000, 'icon': '🧪'}
    ],
    'grandmaster': [
        {'name': 'Infinity Blade', 'value': 2000000, 'icon': '∞'},
        {'name': 'Infinity Armor', 'value': 2500000, 'icon': '🌟'},
        {'name': 'Infinity Shield', 'value': 2200000, 'icon': '🛡️'},
        {'name': 'Infinity Boots', 'value': 1800000, 'icon': '👢'},
        {'name': 'Infinity Potion', 'value': 1500000, 'icon': '🧪'}
    ]
}

def get_random_item():
    # Roll for rarity
    roll = random.randint(1, 100)
    current_chance = 0
    selected_rarity = None
    
    for rarity, data in item_rarities.items():
        current_chance += data['chance']
        if roll <= current_chance:
            selected_rarity = rarity
            break
    
    # Get random item from selected rarity
    items = items_by_rarity[selected_rarity]
    item = random.choice(items)
    
    # Add rarity and color information to the item
    item['rarity'] = selected_rarity
    item['color'] = item_rarities[selected_rarity]['color']
    
    return item

@app.route('/generate', methods=['POST'])
def generate():
    game_data = load_game_data()
    
    # Check if player has enough coins
    if game_data['coins'] < 100:  # Increased from 10 to 100
        return jsonify({'success': False, 'error': 'Not enough coins! You need 100 coins to generate an item.'})
    
    # Deduct coins
    game_data['coins'] -= 100  # Increased from 10 to 100
    
    # Get a random item
    item = get_random_item()
    
    # Add item to inventory
    if item['rarity'] not in game_data['inventory']:
        game_data['inventory'][item['rarity']] = []
    game_data['inventory'][item['rarity']].append(item)
    
    # Update stats
    game_data['stats']['total_rolls'] += 1
    
    # Save game data
    save_game_data(game_data)
    
    return jsonify({
        'success': True,
        'item': item,
        'new_balance': game_data['coins'],
        'stats': game_data['stats']
    })

@app.route('/trade')
def trade_page():
    game_data = load_game_data()
    return render_template('trade.html', game_data=game_data)

@app.route('/get_inventory', methods=['GET'])
def get_inventory():
    game_data = load_game_data()
    return jsonify({
        'success': True,
        'inventory': game_data['inventory']
    })

@app.route('/trade_item', methods=['POST'])
def trade_item():
    game_data = load_game_data()
    
    item_name = request.form.get('item_name')
    rarity = request.form.get('rarity')
    amount = int(request.form.get('amount', 0))
    
    if not item_name or not rarity or amount <= 0:
        return jsonify({'success': False, 'error': 'Invalid trade parameters'})
    
    # Check if the item exists in the inventory
    if rarity not in game_data['inventory']:
        return jsonify({'success': False, 'error': 'Item not found in inventory'})
    
    # Count how many of this item the player has
    item_count = 0
    for item in game_data['inventory'][rarity]:
        if item['name'] == item_name:
            item_count += 1
    
    if item_count < amount:
        return jsonify({'success': False, 'error': f'You only have {item_count} of this item, not {amount}'})
    
    # Remove the items from inventory
    items_to_remove = amount
    new_inventory = []
    
    for item in game_data['inventory'][rarity]:
        if items_to_remove > 0 and item['name'] == item_name:
            items_to_remove -= 1
        else:
            new_inventory.append(item)
    
    game_data['inventory'][rarity] = new_inventory
    
    # Calculate trade value (50% of item value)
    item_value = 0
    for item in items_by_rarity[rarity]:
        if item['name'] == item_name:
            item_value = item['value']
            break
    
    trade_value = item_value * amount * 0.5
    
    # Add coins to player's balance
    game_data['coins'] += trade_value
    
    # Save game data
    save_game_data(game_data)
    
    return jsonify({
        'success': True,
        'message': f'Successfully traded {amount} {item_name} for {trade_value} coins',
        'new_balance': game_data['coins']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 
