import json
import datetime
from datetime import datetime as dt
from pathlib import Path
import re
import calendar
import logging

# Files for data and logging
DATA_FILE = "boda_budget.json"
LOG_FILE = "boda_budget.log"

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

def load_data():
    """Load existing data from JSON file or initialize empty structure."""
    file = Path(DATA_FILE)
    if file.exists():
        with open(file, 'r') as f:
            data = json.load(f)
            # Ensure required keys exist
            if "expense_categories" not in data:
                data["expense_categories"] = ["Bike Hire", "Airtime", "Fuel", "Food", "Rent", "Debts", "Clothes"]
            if "savings_categories" not in data:
                data["savings_categories"] = ["Emergency Savings"]
            if "savings_switch" not in data:
                data["savings_switch"] = False
            return data
    return {
        "income": [],
        "expenses": [],
        "savings": [],
        "expense_categories": ["Bike Hire", "Airtime", "Fuel", "Food", "Rent", "Debts", "Clothes"],
        "savings_categories": ["Emergency Savings"],
        "savings_switch": False
    }

def save_data(data):
    """Save data to JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

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

def add_income(date_str, platform, amount, notes=""):
    """Add income entry to data."""
    date = parse_date(date_str)
    platform = validate_platform(platform)
    amount = validate_amount(amount)
    
    data = load_data()
    data["income"].append({
        "date": date.isoformat(),
        "platform": platform,
        "amount": amount,
        "notes": notes.strip()
    })
    save_data(data)
    action = f"Added Income: {date} - {platform} - {amount:.2f} KES - {notes}"
    log_action(action)
    print(action)

def add_expense(date_str, category, amount, notes=""):
    """Add expense entry to data."""
    date = parse_date(date_str)
    data = load_data()
    category = validate_category(category, data["expense_categories"], "expense")
    amount = validate_amount(amount)
    
    data["expenses"].append({
        "date": date.isoformat(),
        "category": category,
        "amount": amount,
        "notes": notes.strip()
    })
    save_data(data)
    action = f"Added Expense: {date} - {category} - {amount:.2f} KES - {notes}"
    log_action(action)
    print(action)

def add_savings(date_str, category, amount, notes=""):
    """Add savings entry to data."""
    date = parse_date(date_str)
    data = load_data()
    category = validate_category(category, data["savings_categories"], "savings")
    amount = validate_amount(amount)
    
    data["savings"].append({
        "date": date.isoformat(),
        "category": category,
        "amount": amount,
        "notes": notes.strip()
    })
    save_data(data)
    action = f"Added Savings: {date} - {category} - {amount:.2f} KES - {notes}"
    log_action(action)
    print(action)

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

def calculate_totals(date=None, week=None, month=None):
    """Calculate income, expense, savings, and balance totals."""
    data = load_data()
    income_totals = {"total": 0, "Uber": 0, "Bolt": 0, "Littlecab": 0, "Offline": 0}
    expense_totals = {cat: 0 for cat in data["expense_categories"]}
    expense_totals["total"] = 0
    savings_totals = {cat: 0 for cat in data["savings_categories"]}
    savings_totals["total"] = 0
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
        
        if date and entry_date != date:
            continue
        if month and (entry_date.year != month[0] or entry_date.month != month[1]):
            continue
        if week and (entry_date.isocalendar()[1] != week[1] or entry_date.year != week[0]):
            continue

        income_totals["total"] += amount
        income_totals[platform] += amount

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
        
        if date and entry_date != date:
            continue
        if month and (entry_date.year != month[0] or entry_date.month != month[1]):
            continue
        if week and (entry_date.isocalendar()[1] != week[1] or entry_date.year != week[0]):
            continue

        expense_totals["total"] += amount
        expense_totals[category] += amount

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
        
        if date and entry_date != date:
            continue
        if month and (entry_date.year != month[0] or entry_date.month != month[1]):
            continue
        if week and (entry_date.isocalendar()[1] != week[1] or entry_date.year != week[0]):
            continue

        savings_totals["total"] += amount
        savings_totals[category] += amount

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
            daily_savings, weekly_income, weekly_expense, weekly_savings, balance, total_savings)

def display_totals(income_totals, expense_totals, savings_totals, daily_income, daily_expense,
                  daily_savings, weekly_income, weekly_expense, weekly_savings, balance, total_savings, period=""):
    """Display income, expense, savings, and balance totals."""
    data = load_data()
    print(f"\nBalance: {balance:.2f} KES {period}")
    print(f"Income: {income_totals['total']:.2f} KES")
    print(f"Expenses: {expense_totals['total']:.2f} KES")
    print(f"Savings: {total_savings:.2f} KES" + (" (including unallocated income)" if data["savings_switch"] else ""))
    
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

def main():
    """Main command-line interface."""
    while True:
        data = load_data()
        print("\nBoda Boda Budget Tracker")
        print(f"Savings Switch: {'On' if data['savings_switch'] else 'Off'} (Unallocated income as savings)")
        print("1. Add Income")
        print("2. Add Expense")
        print("3. Add Savings")
        print("4. Manage Expense Categories")
        print("5. Manage Savings Categories")
        print("6. Toggle Savings Switch")
        print("7. View Totals by Date")
        print("8. View Totals by Week")
        print("9. View Totals by Month")
        print("10. View All Time Totals")
        print("11. Exit")
        
        choice = input("Select option (1-11): ").strip()
        
        try:
            if choice == "1":
                date_str = input("Date (YYYY-MM-DD, MM-DD, DD, or Enter for today): ").strip()
                if not date_str:
                    date_str = dt.today().date().isoformat()
                platform = input("Platform (1/u: Uber, 2/b: Bolt, 3/l: Littlecab, 4/o: Offline): ").strip()
                amount = input("Amount (KES): ").strip()
                notes = input("Notes (optional): ").strip()
                add_income(date_str, platform, amount, notes)
            
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
                add_expense(date_str, category, amount, notes)
            
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
                add_savings(date_str, category, amount, notes)
            
            elif choice == "4":
                manage_categories("expenses")
            
            elif choice == "5":
                manage_categories("savings")
            
            elif choice == "6":
                toggle_savings_switch()
            
            elif choice == "7":
                date_str = input("Date (YYYY-MM-DD, MM-DD, DD): ").strip()
                date = parse_date(date_str)
                totals = calculate_totals(date=date)
                display_totals(*totals, f"for {date}")
            
            elif choice == "8":
                year = int(input("Year (e.g., 2025): "))
                week_num = int(input("ISO Week number (1-53): "))
                totals = calculate_totals(week=(year, week_num))
                display_totals(*totals, f"for Week {week_num}, {year}")
            
            elif choice == "9":
                year = int(input("Year (e.g., 2025): "))
                month = int(input("Month (1-12): "))
                totals = calculate_totals(month=(year, month))
                month_name = calendar.month_name[month]
                display_totals(*totals, f"for {month_name} {year}")
            
            elif choice == "10":
                totals = calculate_totals()
                display_totals(*totals, "All Time")
            
            elif choice == "11":
                print("Exiting...")
                log_action("Application exited")
                break
            
            else:
                print("Invalid choice. Please select 1-11.")
        
        except ValueError as e:
            print(f"Error: {e}")
            log_action(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            log_action(f"Unexpected Error: {e}")

if __name__ == "__main__":
    log_action("Application started")
    main()