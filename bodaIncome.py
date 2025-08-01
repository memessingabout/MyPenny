import json
import datetime
from datetime import datetime as dt
from pathlib import Path
import re
import calendar
import logging
import argparse
import sys

# Files for data, logging, and contacts
DATA_FILE = "boda_budget.json"
LOG_FILE = "boda_budget.log"
CONTACTS_FILE = "contacts.json"

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Platform mappings for income
PLATFORMS = {
    "1": "Uber",
    "u": "Uber",
    "2": "Bolt",
    "b": "Bolt",
    "3": "Littlecab",
    "l": "Littlecab",
    "4": "Offline",
    "o": "Offline"
}

# Payment modes
PAYMENT_MODES = ["Cash", "M-Pesa"]

def load_data():
    """Load existing data from JSON file or initialize empty structure."""
    file = Path(DATA_FILE)
    if file.exists():
        with open(file, 'r') as f:
            data = json.load(f)
            # Ensure required keys exist
            for key in ["expense_categories", "savings_categories", "savings_switch", "mpesa_details"]:
                if key not in data:
                    data[key] = {
                        "expense_categories": ["Bike Hire", "Airtime", "Fuel", "Food", "Rent", "Debts", "Clothes"],
                        "savings_categories": ["Emergency Savings"],
                        "savings_switch": False,
                        "mpesa_details": {"name": "", "phone": ""}
                    }[key]
            return data
    return {
        "income": [],
        "expenses": [],
        "savings": [],
        "expense_categories": ["Bike Hire", "Airtime", "Fuel", "Food", "Rent", "Debts", "Clothes"],
        "savings_categories": ["Emergency Savings"],
        "savings_switch": False,
        "mpesa_details": {"name": "", "phone": ""}
    }

def save_data(data):
    """Save data to JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_contacts():
    """Load contacts from JSON file or initialize empty list."""
    file = Path(CONTACTS_FILE)
    if file.exists():
        with open(file, 'r') as f:
            return json.load(f)
    return []

def save_contacts(contacts):
    """Save contacts to JSON file."""
    with open(CONTACTS_FILE, 'w') as f:
        json.dump(contacts, f, indent=4)

def log_action(action):
    """Log an action to the log file."""
    logging.info(action)

def parse_date(date_str):
    """Parse date input and return datetime.date object."""
    today = dt.today().date()
    try:
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            parsed = dt.strptime(date_str, '%Y-%m-%d').date()
        elif re.match(r'\d{2}-\d{2}', date_str):
            parsed = dt.strptime(f"{today.year}-{date_str}", '%Y-%m-%d').date()
        else:
            parsed = dt.strptime(f"{today.year}-{today.month:02d}-{date_str}", '%Y-%m-%d').date()
        
        if parsed > today:
            raise ValueError("Cannot track future dates.")
        return parsed
    except ValueError as e:
        if "future dates" in str(e):
            raise
        raise ValueError("Invalid date format. Use YYYY-MM-DD, MM-DD, or DD.")

def validate_platform(platform):
    """Validate and return platform name."""
    platform = platform.lower().strip()
    if platform in PLATFORMS:
        return PLATFORMS[platform]
    raise ValueError("Invalid platform. Use 1/u (Uber), 2/b (Bolt), 3/l (Littlecab), 4/o (Offline).")

def validate_category(category, categories, category_type):
    """Validate and return category for expenses or savings."""
    category = category.lower().strip()
    try:
        idx = int(category) - 1
        if 0 <= idx < len(categories):
            return categories[idx]
    except ValueError:
        for cat in categories:
            if cat.lower().startswith(category) or category == cat.lower():
                return cat
    raise ValueError(f"Invalid {category_type} category. Use number (1-{len(categories)}) or first letter of: {', '.join(categories)}.")

def validate_amount(amount):
    """Validate and return amount as float."""
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
        return amount
    except ValueError:
        raise ValueError("Amount must be a positive number.")

def validate_payment_mode(mode):
    """Validate and return payment mode."""
    mode = mode.title().strip()
    if mode in PAYMENT_MODES:
        return mode
    raise ValueError("Invalid payment mode. Use 'Cash' or 'M-Pesa'.")

def normalize_phone(phone):
    """Normalize phone number to +254 format."""
    phone = phone.strip()
    if phone.startswith('0'):
        return f"+254{phone[1:]}"
    elif phone.startswith('+254'):
        return phone
    return phone

def parse_mpesa_message(message):
    """Parse M-Pesa message and return transaction details."""
    patterns = {
        "received": r"(\w+) Confirmed\.You have received Ksh([\d,.]+)\.00 from ([A-Z\s]+) (\d+) on (\d+/\d+/\d+) at (\d+:\d+\s[AP]M)\s+New M-PESA balance is Ksh([\d,.]+)\.",
        "sent": r"(\w+) Confirmed\. Ksh([\d,.]+)\.00 sent to ([A-Z\s]+) (\d+) on (\d+/\d+/\d+) at (\d+:\d+\s[AP]M)\. New M-PESA balance is Ksh([\d,.]+)\.",
        "paid": r"(\w+) Confirmed\. Ksh([\d,.]+)\.00 paid to ([A-Z\s\-\.]+)\. on (\d+/\d+/\d+) at (\d+:\d+\s[AP]M)\.New M-PESA balance is Ksh([\d,.]+)\.",
        "paybill": r"(\w+) Confirmed\. Ksh([\d,.]+)\.00 sent to ([A-Z\s]+) for account (\S+) on (\d+/\d+/\d+) at (\d+:\d+\s[AP]M) New M-PESA balance is Ksh([\d,.]+)\."
    }
    
    for trans_type, pattern in patterns.items():
        match = re.search(pattern, message)
        if match:
            trans_code = match.group(1)
            amount = float(match.group(2).replace(',', ''))
            name = match.group(3).strip()
            phone_or_account = match.group(4) if trans_type != "paid" else ""
            date_str = match.group(5)
            time_str = match.group(6)
            balance = float(match.group(7).replace(',', ''))
            
            # Parse date and time
            date = dt.strptime(date_str, '%d/%m/%y').date()
            time = dt.strptime(time_str, '%I:%M %p').time()
            
            # Normalize phone
            phone = normalize_phone(phone_or_account) if phone_or_account.startswith('0') or phone_or_account.startswith('+254') else ""
            
            return {
                "type": "income" if trans_type == "received" else "expense",
                "transaction_code": trans_code,
                "amount": amount,
                "name": name,
                "phone": phone,
                "date": date.isoformat(),
                "time": time.strftime('%H:%M:%S'),
                "balance": balance
            }
    return None

def smart_categorize(name):
    """Smart categorization based on account name."""
    name = name.lower()
    if any(keyword in name for keyword in ["petrol", "fuel", "station"]):
        return "Fuel"
    if "marapay" in name:
        return "Airtime"
    return None

def verify_mpesa_balance(transaction, data):
    """Verify M-Pesa balance within ±10 KES."""
    mpesa_balance = calculate_mpesa_balance(data)
    expected_balance = mpesa_balance
    if transaction["type"] == "income":
        expected_balance += transaction["amount"]
    else:
        expected_balance -= transaction["amount"]
    
    if abs(expected_balance - transaction["balance"]) > 10:
        return False
    return True

def calculate_mpesa_balance(data):
    """Calculate current M-Pesa balance from transactions."""
    balance = 0
    for entry in data["income"]:
        if entry["payment_mode"] == "M-Pesa":
            balance += entry["amount"]
    for entry in data["expenses"] + data["savings"]:
        if entry["payment_mode"] == "M-Pesa":
            balance -= entry["amount"]
    return balance

def add_income(date_str, platform, amount, notes="", payment_mode="Cash", transaction_code=""):
    """Add income entry to data."""
    date = parse_date(date_str)
    platform = validate_platform(platform)
    amount = validate_amount(amount)
    payment_mode = validate_payment_mode(payment_mode)
    
    data = load_data()
    entry = {
        "date": date.isoformat(),
        "platform": platform,
        "amount": amount,
        "notes": notes.strip(),
        "payment_mode": payment_mode,
        "transaction_code": transaction_code if payment_mode == "M-Pesa" else ""
    }
    data["income"].append(entry)
    save_data(data)
    action = f"Added Income: {date} - {platform} - {amount:.2f} KES - {notes} - {payment_mode} - {transaction_code}"
    log_action(action)
    return entry

def add_expense(date_str, category, amount, notes="", payment_mode="Cash", transaction_code=""):
    """Add expense entry to data."""
    date = parse_date(date_str)
    data = load_data()
    category = validate_category(category, data["expense_categories"], "expense")
    amount = validate_amount(amount)
    payment_mode = validate_payment_mode(payment_mode)
    
    entry = {
        "date": date.isoformat(),
        "category": category,
        "amount": amount,
        "notes": notes.strip(),
        "payment_mode": payment_mode,
        "transaction_code": transaction_code if payment_mode == "M-Pesa" else ""
    }
    data["expenses"].append(entry)
    save_data(data)
    action = f"Added Expense: {date} - {category} - {amount:.2f} KES - {notes} - {payment_mode} - {transaction_code}"
    log_action(action)
    return entry

def add_savings(date_str, category, amount, notes="", payment_mode="Cash", transaction_code=""):
    """Add savings entry to data."""
    date = parse_date(date_str)
    data = load_data()
    category = validate_category(category, data["savings_categories"], "savings")
    amount = validate_amount(amount)
    payment_mode = validate_payment_mode(payment_mode)
    
    entry = {
        "date": date.isoformat(),
        "category": category,
        "amount": amount,
        "notes": notes.strip(),
        "payment_mode": payment_mode,
        "transaction_code": transaction_code if payment_mode == "M-Pesa" else ""
    }
    data["savings"].append(entry)
    save_data(data)
    action = f"Added Savings: {date} - {category} - {amount:.2f} KES - {notes} - {payment_mode} - {transaction_code}"
    log_action(action)
    return entry

def add_contact(name, phone, date, time, category):
    """Add or update contact entry."""
    contacts = load_contacts()
    entry = {
        "name": name,
        "phone": phone,
        "date": date,
        "time": time,
        "category": category
    }
    contacts.append(entry)
    save_contacts(contacts)

def manage_categories(category_type):
    """Manage expense or savings categories (add, modify, delete)."""
    data = load_data()
    categories_key = f"{category_type}_categories"
    entries_key = category_type
    while True:
        print(f"\nManage {category_type.title()} Categories")
        for i, cat in enumerate(data[categories_key], 1):
            print(f"{i}. {cat}")
        print("\n1. Add Category")
        print("2. Modify Category")
        print("3. Delete Category")
        print("4. Back")
        
        choice = input("Select option (1-4): ").strip()
        
        try:
            if choice == "1":
                new_cat = input(f"Enter new {category_type} category name: ").strip().title()
                if new_cat in data[categories_key]:
                    print("Category already exists.")
                elif not new_cat:
                    print("Category name cannot be empty.")
                else:
                    data[categories_key].append(new_cat)
                    save_data(data)
                    action = f"Added {category_type.title()} Category: {new_cat}"
                    log_action(action)
                    print(action)
            
            elif choice == "2":
                cat_num = input(f"Enter {category_type} category number to modify: ").strip()
                idx = int(cat_num) - 1
                if 0 <= idx < len(data[categories_key]):
                    old_cat = data[categories_key][idx]
                    new_name = input("Enter new name: ").strip().title()
                    if new_name in data[categories_key]:
                        print("Category name already exists.")
                    elif not new_name:
                        print("Category name cannot be empty.")
                    else:
                        for entry in data[entries_key]:
                            if entry["category"] == old_cat:
                                entry["category"] = new_name
                        data[categories_key][idx] = new_name
                        save_data(data)
                        action = f"Modified {category_type.title()} Category: {old_cat} -> {new_name}"
                        log_action(action)
                        print(action)
                else:
                    print("Invalid category number.")
            
            elif choice == "3":
                cat_num = input(f"Enter {category_type} category number to delete: ").strip()
                idx = int(cat_num) - 1
                if 0 <= idx < len(data[categories_key]):
                    cat = data[categories_key][idx]
                    if any(entry["category"] == cat for entry in data[entries_key]):
                        print(f"Cannot delete {cat}: Category is used in {category_type} entries.")
                    else:
                        data[categories_key].pop(idx)
                        save_data(data)
                        action = f"Deleted {category_type.title()} Category: {cat}"
                        log_action(action)
                        print(action)
                else:
                    print("Invalid category number.")
            
            elif choice == "4":
                break
            
            else:
                print("Invalid choice. Please select 1-4.")
        
        except ValueError as e:
            print(f"Error: {e}")
            log_action(f"Error in Manage {category_type.title()} Categories: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            log_action(f"Unexpected Error in Manage {category_type.title()} Categories: {e}")

def toggle_savings_switch():
    """Toggle the savings switch."""
    data = load_data()
    data["savings_switch"] = not data["savings_switch"]
    save_data(data)
    status = "on" if data["savings_switch"] else "off"
    action = f"Toggled Savings Switch to {status}"
    log_action(action)
    print(action)

def set_mpesa_details():
    """Set user's M-Pesa name and phone number."""
    data = load_data()
    name = input("Enter your M-Pesa registered name (e.g., JOHN DOE): ").strip().title()
    phone = input("Enter your M-Pesa phone number (e.g., 0712345678): ").strip()
    phone = normalize_phone(phone)
    data["mpesa_details"] = {"name": name, "phone": phone}
    save_data(data)
    action = f"Set M-Pesa Details: Name={name}, Phone={phone}"
    log_action(action)
    print(action)

def process_mpesa_messages():
    """Process M-Pesa messages input by user."""
    data = load_data()
    if not data["mpesa_details"]["name"] or not data["mpesa_details"]["phone"]:
        print("Please set M-Pesa details first (option 7).")
        return
    
    print("Paste M-Pesa messages (one per line, press Enter twice to finish):")
    messages = []
    while True:
        line = input()
        if line == "":
            break
        messages.append(line)
    
    for message in messages:
        trans = parse_mpesa_message(message)
        if not trans:
            print(f"Skipping invalid message: {message[:50]}...")
            log_action(f"Skipped invalid M-Pesa message: {message[:50]}...")
            continue
        
        # Verify balance
        if not verify_mpesa_balance(trans, data):
            print(f"Balance mismatch for transaction {trans['transaction_code']}. Skipping.")
            log_action(f"Balance mismatch for {trans['transaction_code']}: Expected {calculate_mpesa_balance(data)} ±10, Got {trans['balance']}")
            continue
        
        # Add contact
        if trans["phone"]:
            add_contact(trans["name"], trans["phone"], trans["date"], trans["time"], None)
        
        if trans["type"] == "income":
            # Assume Offline platform for M-Pesa income
            entry = add_income(
                trans["date"],
                "Offline",
                trans["amount"],
                f"From {trans['name']}",
                "M-Pesa",
                trans["transaction_code"]
            )
            # Update contact with category
            if trans["phone"]:
                contacts = load_contacts()
                for contact in contacts[-1:]:
                    if contact["phone"] == trans["phone"] and contact["date"] == trans["date"]:
                        contact["category"] = "Income"
                        save_contacts(contacts)
                        break
        
        else:  # Expense or Savings
            category = smart_categorize(trans["name"])
            if category and category in data["expense_categories"]:
                entry = add_expense(
                    trans["date"],
                    category,
                    trans["amount"],
                    f"To {trans['name']}",
                    "M-Pesa",
                    trans["transaction_code"]
                )
                if trans["phone"]:
                    contacts = load_contacts()
                    for contact in contacts[-1:]:
                        if contact["phone"] == trans["phone"] and contact["date"] == trans["date"]:
                            contact["category"] = category
                            save_contacts(contacts)
                            break
            else:
                print(f"\nUncategorized transaction: {trans['transaction_code']} - {trans['amount']:.2f} KES to {trans['name']}")
                print("1. Expense")
                print("2. Savings")
                print("3. Skip")
                choice = input("Select type (1-3): ").strip()
                
                if choice == "1":
                    print("Expense Categories:")
                    for i, cat in enumerate(data["expense_categories"], 1):
                        print(f"{i}. {cat}")
                    cat_input = input(f"Category (1-{len(data['expense_categories'])}, or first letter): ").strip()
                    category = validate_category(cat_input, data["expense_categories"], "expense")
                    entry = add_expense(
                        trans["date"],
                        category,
                        trans["amount"],
                        f"To {trans['name']}",
                        "M-Pesa",
                        trans["transaction_code"]
                    )
                    if trans["phone"]:
                        contacts = load_contacts()
                        for contact in contacts[-1:]:
                            if contact["phone"] == trans["phone"] and contact["date"] == trans["date"]:
                                contact["category"] = category
                                save_contacts(contacts)
                                break
                
                elif choice == "2":
                    print("Savings Categories:")
                    for i, cat in enumerate(data["savings_categories"], 1):
                        print(f"{i}. {cat}")
                    cat_input = input(f"Category (1-{len(data['savings_categories'])}, or first letter): ").strip()
                    category = validate_category(cat_input, data["savings_categories"], "savings")
                    entry = add_savings(
                        trans["date"],
                        category,
                        trans["amount"],
                        f"To {trans['name']}",
                        "M-Pesa",
                        trans["transaction_code"]
                    )
                    if trans["phone"]:
                        contacts = load_contacts()
                        for contact in contacts[-1:]:
                            if contact["phone"] == trans["phone"] and contact["date"] == trans["date"]:
                                contact["category"] = category
                                save_contacts(contacts)
                                break
                
                else:
                    print("Transaction skipped.")
                    log_action(f"Skipped transaction {trans['transaction_code']}")

def calculate_totals(date=None, week=None, month=None):
    """Calculate income, expense, savings, and balance totals."""
    data = load_data()
    income_totals = {"total": 0, "Uber": 0, "Bolt": 0, "Littlecab": 0, "Offline": 0}
    expense_totals = {cat: 0 for cat in data["expense_categories"]}
    expense_totals["total"] = 0
    savings_totals = {cat: 0 for cat in data["savings_categories"]}
    savings_totals["total"] = 0
    cash_balance = 0
    mpesa_balance = 0
    daily_income = {}
    daily_expense = {}
    daily_savings = {}
    weekly_income = {}
    weekly_expense = {}
    weekly_savings = {}

    # Process income
    for entry in data["income"]:
        entry_date = dt.fromisoformat(entry["date"]).date()
        platform = entry["platform"]
        amount = entry["amount"]
        payment_mode = entry["payment_mode"]
        
        if date and entry_date != date:
            continue
        if month and (entry_date.year != month[0] or entry_date.month != month[1]):
            continue
        if week and (entry_date.isocalendar()[1] != week[1] or entry_date.year != week[0]):
            continue

        income_totals["total"] += amount
        income_totals[platform] += amount
        if payment_mode == "Cash":
            cash_balance += amount
        else:
            mpesa_balance += amount

        date_str = entry_date.isoformat()
        if date_str not in daily_income:
            daily_income[date_str] = {"total": 0, "Uber": 0, "Bolt": 0, "Littlecab": 0, "Offline": 0}
        daily_income[date_str]["total"] += amount
        daily_income[date_str][platform] += amount

        week_num = entry_date.isocalendar()
        week_key = f"{week_num[0]}-W{week_num[1]:02d}"
        if week_key not in weekly_income:
            weekly_income[week_key] = {"total": 0, "Uber": 0, "Bolt": 0, "Littlecab": 0, "Offline": 0}
        weekly_income[week_key]["total"] += amount
        weekly_income[week_key][platform] += amount

    # Process expenses
    for entry in data["expenses"]:
        entry_date = dt.fromisoformat(entry["date"]).date()
        category = entry["category"]
        amount = entry["amount"]
        payment_mode = entry["payment_mode"]
        
        if date and entry_date != date:
            continue
        if month and (entry_date.year != month[0] or entry_date.month != month[1]):
            continue
        if week and (entry_date.isocalendar()[1] != week[1] or entry_date.year != week[0]):
            continue

        expense_totals["total"] += amount
        expense_totals[category] += amount
        if payment_mode == "Cash":
            cash_balance -= amount
        else:
            mpesa_balance -= amount

        date_str = entry_date.isoformat()
        if date_str not in daily_expense:
            daily_expense[date_str] = {cat: 0 for cat in data["expense_categories"]}
            daily_expense[date_str]["total"] = 0
        daily_expense[date_str]["total"] += amount
        daily_expense[date_str][category] += amount

        week_num = entry_date.isocalendar()
        week_key = f"{week_num[0]}-W{week_num[1]:02d}"
        if week_key not in weekly_expense:
            weekly_expense[week_key] = {cat: 0 for cat in data["expense_categories"]}
            weekly_expense[week_key]["total"] = 0
        weekly_expense[week_key]["total"] += amount
        weekly_expense[week_key][category] += amount

    # Process savings
    for entry in data["savings"]:
        entry_date = dt.fromisoformat(entry["date"]).date()
        category = entry["category"]
        amount = entry["amount"]
        payment_mode = entry["payment_mode"]
        
        if date and entry_date != date:
            continue
        if month and (entry_date.year != month[0] or entry_date.month != month[1]):
            continue
        if week and (entry_date.isocalendar()[1] != week[1] or entry_date.year != week[0]):
            continue

        savings_totals["total"] += amount
        savings_totals[category] += amount
        if payment_mode == "Cash":
            cash_balance -= amount
        else:
            mpesa_balance -= amount

        date_str = entry_date.isoformat()
        if date_str not in daily_savings:
            daily_savings[date_str] = {cat: 0 for cat in data["savings_categories"]}
            daily_savings[date_str]["total"] = 0
        daily_savings[date_str]["total"] += amount
        daily_savings[date_str][category] += amount

        week_num = entry_date.isocalendar()
        week_key = f"{week_num[0]}-W{week_num[1]:02d}"
        if week_key not in weekly_savings:
            weekly_savings[week_key] = {cat: 0 for cat in data["savings_categories"]}
            weekly_savings[week_key]["total"] = 0
        weekly_savings[week_key]["total"] += amount
        weekly_savings[week_key][category] += amount

    # Calculate balance and total savings
    if data["savings_switch"]:
        balance = income_totals["total"] - expense_totals["total"]
        unallocated_savings = max(0, balance)
        total_savings = savings_totals["total"] + unallocated_savings
    else:
        balance = income_totals["total"] - expense_totals["total"] - savings_totals["total"]
        total_savings = savings_totals["total"]

    return (income_totals, expense_totals, savings_totals, daily_income, daily_expense,
            daily_savings, weekly_income, weekly_expense, weekly_savings, balance, total_savings,
            cash_balance, mpesa_balance)

def display_totals(income_totals, expense_totals, savings_totals, daily_income, daily_expense,
                  daily_savings, weekly_income, weekly_expense, weekly_savings, balance, total_savings,
                  cash_balance, mpesa_balance, period=""):
    """Display income, expense, savings, and balance totals."""
    data = load_data()
    print(f"\nBalance: {balance:.2f} KES {period}")
    print(f"Income: {income_totals['total']:.2f} KES")
    print(f"Expenses: {expense_totals['total']:.2f} KES")
    print(f"Savings: {total_savings:.2f} KES" + (" (including unallocated income)" if data["savings_switch"] else ""))
    print(f"Cash Balance: {cash_balance:.2f} KES")
    print(f"M-Pesa Balance: {mpesa_balance:.2f} KES")
    
    print("\nIncome Breakdown:")
    for platform in ["Uber", "Bolt", "Littlecab", "Offline"]:
        if income_totals[platform] > 0:
            print(f"{platform}: {income_totals[platform]:.2f} KES")

    print("\nExpense Breakdown:")
    for category, amount in expense_totals.items():
        if category != "total" and amount > 0:
            print(f"{category}: {amount:.2f} KES")

    print("\nSavings Breakdown:")
    for category, amount in savings_totals.items():
        if category != "total" and amount > 0:
            print(f"{category}: {amount:.2f} KES")
    if data["savings_switch"] and total_savings > savings_totals["total"]:
        print(f"Unallocated Income as Savings: {(total_savings - savings_totals['total']):.2f} KES")

    if daily_income or daily_expense or daily_savings:
        print("\nDaily Breakdown:")
        dates = sorted(set(daily_income.keys()) | set(daily_expense.keys()) | set(daily_savings.keys()))
        for date in dates:
            income = daily_income.get(date, {"total": 0})
            expense = daily_expense.get(date, {"total": 0})
            savings = daily_savings.get(date, {"total": 0})
            daily_balance = income["total"] - expense["total"] - (savings["total"] if not data["savings_switch"] else 0)
            print(f"{date}: Balance {daily_balance:.2f} KES (Income {income['total']:.2f}, Expense {expense['total']:.2f}, Savings {savings['total']:.2f})")
            if income["total"] > 0:
                print("  Income:")
                for platform in ["Uber", "Bolt", "Littlecab", "Offline"]:
                    if income.get(platform, 0) > 0:
                        print(f"    {platform}: {income[platform]:.2f} KES")
            if expense["total"] > 0:
                print("  Expenses:")
                for category, amount in expense.items():
                    if category != "total" and amount > 0:
                        print(f"    {category}: {amount:.2f} KES")
            if savings["total"] > 0:
                print("  Savings:")
                for category, amount in savings.items():
                    if category != "total" and amount > 0:
                        print(f"    {category}: {amount:.2f} KES")

    if weekly_income or weekly_expense or weekly_savings:
        print("\nWeekly Breakdown (Monday-Sunday, ISO Week):")
        weeks = sorted(set(weekly_income.keys()) | set(weekly_expense.keys()) | set(weekly_savings.keys()))
        for week in weeks:
            income = weekly_income.get(week, {"total": 0})
            expense = weekly_expense.get(week, {"total": 0})
            savings = weekly_savings.get(week, {"total": 0})
            weekly_balance = income["total"] - expense["total"] - (savings["total"] if not data["savings_switch"] else 0)
            print(f"{week}: Balance {weekly_balance:.2f} KES (Income {income['total']:.2f}, Expense {expense['total']:.2f}, Savings {savings['total']:.2f})")
            if income["total"] > 0:
                print("  Income:")
                for platform in ["Uber", "Bolt", "Littlecab", "Offline"]:
                    if income.get(platform, 0) > 0:
                        print(f"    {platform}: {income[platform]:.2f} KES")
            if expense["total"] > 0:
                print("  Expenses:")
                for category, amount in expense.items():
                    if category != "total" and amount > 0:
                        print(f"    {category}: {amount:.2f} KES")
            if savings["total"] > 0:
                print("  Savings:")
                for category, amount in savings.items():
                    if category != "total" and amount > 0:
                        print(f"    {category}: {amount:.2f} KES")

def parse_arguments():
    """Parse command-line arguments for one-line logging."""
    parser = argparse.ArgumentParser(description="Boda Boda Budget Tracker")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Income parser
    income_parser = subparsers.add_parser("income", help="Log income")
    income_parser.add_argument("--date", required=True, help="Date (YYYY-MM-DD, MM-DD, DD)")
    income_parser.add_argument("--platform", required=True, help="Platform (1/u: Uber, 2/b: Bolt, 3/l: Littlecab, 4/o: Offline)")
    income_parser.add_argument("--amount", type=float, required=True, help="Amount in KES")
    income_parser.add_argument("--notes", default="", help="Optional notes")
    income_parser.add_argument("--mode", default="Cash", help="Payment mode (Cash, M-Pesa)")
    income_parser.add_argument("--transcode", default="", help="M-Pesa transaction code")

    # Expense parser
    expense_parser = subparsers.add_parser("expense", help="Log expense")
    expense_parser.add_argument("--date", required=True, help="Date (YYYY-MM-DD, MM-DD, DD)")
    expense_parser.add_argument("--category", required=True, help="Expense category (number or first letter)")
    expense_parser.add_argument("--amount", type=float, required=True, help="Amount in KES")
    expense_parser.add_argument("--notes", default="", help="Optional notes")
    expense_parser.add_argument("--mode", default="Cash", help="Payment mode (Cash, M-Pesa)")
    expense_parser.add_argument("--transcode", default="", help="M-Pesa transaction code")

    # Savings parser
    savings_parser = subparsers.add_parser("savings", help="Log savings")
    savings_parser.add_argument("--date", required=True, help="Date (YYYY-MM-DD, MM-DD, DD)")
    savings_parser.add_argument("--category", required=True, help="Savings category (number or first letter)")
    savings_parser.add_argument("--amount", type=float, required=True, help="Amount in KES")
    savings_parser.add_argument("--notes", default="", help="Optional notes")
    savings_parser.add_argument("--mode", default="Cash", help="Payment mode (Cash, M-Pesa)")
    savings_parser.add_argument("--transcode", default="", help="M-Pesa transaction code")

    args = parser.parse_args()
    return args

def main():
    """Main command-line interface."""
    args = parse_arguments()
    
    # Handle command-line arguments
    if args.command:
        try:
            if args.command == "income":
                add_income(args.date, args.platform, args.amount, args.notes, args.mode, args.transcode)
            elif args.command == "expense":
                add_expense(args.date, args.category, args.amount, args.notes, args.mode, args.transcode)
            elif args.command == "savings":
                add_savings(args.date, args.category, args.amount, args.notes, args.mode, args.transcode)
            sys.exit(0)
        except ValueError as e:
            print(f"Error: {e}")
            log_action(f"Error in command-line {args.command}: {e}")
            sys.exit(1)
    
    # Interactive menu
    while True:
        data = load_data()
        print("\nBoda Boda Budget Tracker (v0.1)")
        print(f"Savings Switch: {'On' if data['savings_switch'] else 'Off'} (Unallocated income as savings)")
        print(f"M-Pesa Details: Name={data['mpesa_details']['name']}, Phone={data['mpesa_details']['phone']}")
        print("1. Add Income")
        print("2. Add Expense")
        print("3. Add Savings")
        print("4. Process M-Pesa Messages")
        print("5. Manage Expense Categories")
        print("6. Manage Savings Categories")
        print("7. Set M-Pesa Details")
        print("8. Toggle Savings Switch")
        print("9. View Totals by Date")
        print("10. View Totals by Week")
        print("11. View Totals by Month")
        print("12. View All Time Totals")
        print("13. Exit")
        
        choice = input("Select option (1-13): ").strip()
        
        try:
            if choice == "1":
                date_str = input("Date (YYYY-MM-DD, MM-DD, DD, or Enter for today): ").strip()
                if not date_str:
                    date_str = dt.today().date().isoformat()
                platform = input("Platform (1/u: Uber, 2/b: Bolt, 3/l: Littlecab, 4/o: Offline): ").strip()
                amount = input("Amount (KES): ").strip()
                notes = input("Notes (optional): ").strip()
                mode = input("Payment Mode (Cash, M-Pesa): ").strip()
                trans_code = input("M-Pesa Transaction Code (if applicable): ").strip() if mode.lower() == "m-pesa" else ""
                add_income(date_str, platform, amount, notes, mode, trans_code)
            
            elif choice == "2":
                date_str = input("Date (YYYY-MM-DD, MM-DD, DD, or Enter for today): ").strip()
                if not date_str:
                    date_str = dt.today().date().isoformat()
                data = load_data()
                print("Expense Categories:")
                for i, cat in enumerate(data["expense_categories"], 1):
                    print(f"{i}. {cat}")
                category = input(f"Category (1-{len(data['expense_categories'])}, or first letter): ").strip()
                amount = input("Amount (KES): ").strip()
                notes = input("Notes (optional): ").strip()
                mode = input("Payment Mode (Cash, M-Pesa): ").strip()
                trans_code = input("M-Pesa Transaction Code (if applicable): ").strip() if mode.lower() == "m-pesa" else ""
                add_expense(date_str, category, amount, notes, mode, trans_code)
            
            elif choice == "3":
                date_str = input("Date (YYYY-MM-DD, MM-DD, DD, or Enter for today): ").strip()
                if not date_str:
                    date_str = dt.today().date().isoformat()
                data = load_data()
                print("Savings Categories:")
                for i, cat in enumerate(data["savings_categories"], 1):
                    print(f"{i}. {cat}")
                category = input(f"Category (1-{len(data['savings_categories'])}, or first letter): ").strip()
                amount = input("Amount (KES): ").strip()
                notes = input("Notes (optional): ").strip()
                mode = input("Payment Mode (Cash, M-Pesa): ").strip()
                trans_code = input("M-Pesa Transaction Code (if applicable): ").strip() if mode.lower() == "m-pesa" else ""
                add_savings(date_str, category, amount, notes, mode, trans_code)
            
            elif choice == "4":
                process_mpesa_messages()
            
            elif choice == "5":
                manage_categories("expenses")
            
            elif choice == "6":
                manage_categories("savings")
            
            elif choice == "7":
                set_mpesa_details()
            
            elif choice == "8":
                toggle_savings_switch()
            
            elif choice == "9":
                date_str = input("Date (YYYY-MM-DD, MM-DD, DD): ").strip()
                date = parse_date(date_str)
                totals = calculate_totals(date=date)
                display_totals(*totals, f"for {date}")
            
            elif choice == "10":
                year = int(input("Year (e.g., 2025): "))
                week_num = int(input("ISO Week number (1-53): "))
                totals = calculate_totals(week=(year, week_num))
                display_totals(*totals, f"for Week {week_num}, {year}")
            
            elif choice == "11":
                year = int(input("Year (e.g., 2025): "))
                month = int(input("Month (1-12): "))
                totals = calculate_totals(month=(year, month))
                month_name = calendar.month_name[month]
                display_totals(*totals, f"for {month_name} {year}")
            
            elif choice == "12":
                totals = calculate_totals()
                display_totals(*totals, "All Time")
            
            elif choice == "13":
                print("Exiting...")
                log_action("Application exited")
                break
            
            else:
                print("Invalid choice. Please select 1-13.")
        
        except ValueError as e:
            print(f"Error: {e}")
            log_action(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            log_action(f"Unexpected Error: {e}")

if __name__ == "__main__":
    log_action("Application started")
    main()