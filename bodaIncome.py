import json
import datetime
from datetime import datetime as dt
from pathlib import Path
import re
import calendar

# File to store data
DATA_FILE = "boda_budget.json"

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
            # Ensure expense_categories exists
            if "expense_categories" not in data:
                data["expense_categories"] = ["Bike Hire", "Airtime", "Fuel", "Food", "Rent", "Debts", "Clothes"]
            return data
    return {
        "income": [],
        "expenses": [],
        "expense_categories": ["Bike Hire", "Airtime", "Fuel", "Food", "Rent", "Debts", "Clothes"]
    }

def save_data(data):
    """Save data to JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def parse_date(date_str):
    """Parse date input and return datetime.date object."""
    today = dt.today().date()
    try:
        # Full date YYYY-MM-DD
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            parsed = dt.strptime(date_str, '%Y-%m-%d').date()
        # MM-DD, use current year
        elif re.match(r'\d{2}-\d{2}', date_str):
            parsed = dt.strptime(f"{today.year}-{date_str}", '%Y-%m-%d').date()
        # DD, use current month and year
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

def validate_category(category, data):
    """Validate and return expense category."""
    categories = data["expense_categories"]
    category = category.lower().strip()
    # Try matching by number
    try:
        idx = int(category) - 1
        if 0 <= idx < len(categories):
            return categories[idx]
    except ValueError:
        # Try matching by first letter or full name
        for cat in categories:
            if cat.lower().startswith(category) or category == cat.lower():
                return cat
    raise ValueError(f"Invalid category. Use number (1-{len(categories)}) or first letter of: {', '.join(categories)}.")

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
    print(f"Added Income: {date} - {platform} - {amount:.2f} KES - {notes}")

def add_expense(date_str, category, amount, notes=""):
    """Add expense entry to data."""
    date = parse_date(date_str)
    data = load_data()
    category = validate_category(category, data)
    amount = validate_amount(amount)
    
    data["expenses"].append({
        "date": date.isoformat(),
        "category": category,
        "amount": amount,
        "notes": notes.strip()
    })
    save_data(data)
    print(f"Added Expense: {date} - {category} - {amount:.2f} KES - {notes}")

def manage_categories():
    """Manage expense categories (add, modify, delete)."""
    data = load_data()
    while True:
        print("\nManage Expense Categories")
        for i, cat in enumerate(data["expense_categories"], 1):
            print(f"{i}. {cat}")
        print("\n1. Add Category")
        print("2. Modify Category")
        print("3. Delete Category")
        print("4. Back")
        
        choice = input("Select option (1-4): ").strip()
        
        try:
            if choice == "1":
                new_cat = input("Enter new category name: ").strip().title()
                if new_cat in data["expense_categories"]:
                    print("Category already exists.")
                elif not new_cat:
                    print("Category name cannot be empty.")
                else:
                    data["expense_categories"].append(new_cat)
                    save_data(data)
                    print(f"Added category: {new_cat}")
            
            elif choice == "2":
                cat_num = input("Enter category number to modify: ").strip()
                idx = int(cat_num) - 1
                if 0 <= idx < len(data["expense_categories"]):
                    old_cat = data["expense_categories"][idx]
                    new_name = input("Enter new name: ").strip().title()
                    if new_name in data["expense_categories"]:
                        print("Category name already exists.")
                    elif not new_name:
                        print("Category name cannot be empty.")
                    else:
                        # Update category in expenses
                        for expense in data["expenses"]:
                            if expense["category"] == old_cat:
                                expense["category"] = new_name
                        data["expense_categories"][idx] = new_name
                        save_data(data)
                        print(f"Modified category: {old_cat} -> {new_name}")
                else:
                    print("Invalid category number.")
            
            elif choice == "3":
                cat_num = input("Enter category number to delete: ").strip()
                idx = int(cat_num) - 1
                if 0 <= idx < len(data["expense_categories"]):
                    cat = data["expense_categories"][idx]
                    # Check if category is used in expenses
                    if any(expense["category"] == cat for expense in data["expenses"]):
                        print(f"Cannot delete {cat}: Category is used in expenses.")
                    else:
                        data["expense_categories"].pop(idx)
                        save_data(data)
                        print(f"Deleted category: {cat}")
                else:
                    print("Invalid category number.")
            
            elif choice == "4":
                break
            
            else:
                print("Invalid choice. Please select 1-4.")
        
        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

def calculate_totals(date=None, week=None, month=None):
    """Calculate income, expense, and balance totals by date, week, or month."""
    data = load_data()
    income_totals = {
        "total": 0,
        "Uber": 0,
        "Bolt": 0,
        "Littlecab": 0,
        "Offline": 0
    }
    expense_totals = {cat: 0 for cat in data["expense_categories"]}
    expense_totals["total"] = 0
    daily_income = {}
    daily_expense = {}
    weekly_income = {}
    weekly_expense = {}

    # Process income
    for entry in data["income"]:
        entry_date = dt.fromisoformat(entry["date"]).date()
        platform = entry["platform"]
        amount = entry["amount"]
        
        # Filter by date, week, or month
        if date and entry_date != date:
            continue
        if month and (entry_date.year != month[0] or entry_date.month != month[1]):
            continue
        if week and (entry_date.isocalendar()[1] != week[1] or entry_date.year != week[0]):
            continue

        # Update income totals
        income_totals["total"] += amount
        income_totals[platform] += amount

        # Daily income
        date_str = entry_date.isoformat()
        if date_str not in daily_income:
            daily_income[date_str] = {"total": 0, "Uber": 0, "Bolt": 0, "Littlecab": 0, "Offline": 0}
        daily_income[date_str]["total"] += amount
        daily_income[date_str][platform] += amount

        # Weekly income
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
        
        # Filter by date, week, or month
        if date and entry_date != date:
            continue
        if month and (entry_date.year != month[0] or entry_date.month != month[1]):
            continue
        if week and (entry_date.isocalendar()[1] != week[1] or entry_date.year != week[0]):
            continue

        # Update expense totals
        expense_totals["total"] += amount
        expense_totals[category] += amount

        # Daily expense
        date_str = entry_date.isoformat()
        if date_str not in daily_expense:
            daily_expense[date_str] = {cat: 0 for cat in data["expense_categories"]}
            daily_expense[date_str]["total"] = 0
        daily_expense[date_str]["total"] += amount
        daily_expense[date_str][category] += amount

        # Weekly expense
        week_num = entry_date.isocalendar()
        week_key = f"{week_num[0]}-W{week_num[1]:02d}"
        if week_key not in weekly_expense:
            weekly_expense[week_key] = {cat: 0 for cat in data["expense_categories"]}
            weekly_expense[week_key]["total"] = 0
        weekly_expense[week_key]["total"] += amount
        weekly_expense[week_key][category] += amount

    balance = income_totals["total"] - expense_totals["total"]
    return income_totals, expense_totals, daily_income, daily_expense, weekly_income, weekly_expense, balance

def display_totals(income_totals, expense_totals, daily_income, daily_expense, weekly_income, weekly_expense, balance, period=""):
    """Display income, expense, and balance totals."""
    print(f"\nBalance: {balance:.2f} KES {period}")
    print(f"Income: {income_totals['total']:.2f} KES")
    print(f"Expenses: {expense_totals['total']:.2f} KES")

    print("\nIncome Breakdown:")
    for platform in ["Uber", "Bolt", "Littlecab", "Offline"]:
        if income_totals[platform] > 0:
            print(f"{platform}: {income_totals[platform]:.2f} KES")

    print("\nExpense Breakdown:")
    for category, amount in expense_totals.items():
        if category != "total" and amount > 0:
            print(f"{category}: {amount:.2f} KES")

    if daily_income or daily_expense:
        print("\nDaily Breakdown:")
        dates = sorted(set(daily_income.keys()) | set(daily_expense.keys()))
        for date in dates:
            income = daily_income.get(date, {"total": 0})
            expense = daily_expense.get(date, {"total": 0})
            daily_balance = income["total"] - expense["total"]
            print(f"{date}: Balance {daily_balance:.2f} KES (Income {income['total']:.2f}, Expense {expense['total']:.2f})")
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

    if weekly_income or weekly_expense:
        print("\nWeekly Breakdown (Monday-Sunday, ISO Week):")
        weeks = sorted(set(weekly_income.keys()) | set(weekly_expense.keys()))
        for week in weeks:
            income = weekly_income.get(week, {"total": 0})
            expense = weekly_expense.get(week, {"total": 0})
            weekly_balance = income["total"] - expense["total"]
            print(f"{week}: Balance {weekly_balance:.2f} KES (Income {income['total']:.2f}, Expense {expense['total']:.2f})")
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

def main():
    """Main command-line interface."""
    while True:
        print("\nBoda Boda Budget Tracker")
        print("1. Add Income")
        print("2. Add Expense")
        print("3. Manage Expense Categories")
        print("4. View Totals by Date")
        print("5. View Totals by Week")
        print("6. View Totals by Month")
        print("7. View All Time Totals")
        print("8. Exit")
        
        choice = input("Select option (1-8): ").strip()
        
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
                manage_categories()
            
            elif choice == "4":
                date_str = input("Date (YYYY-MM-DD, MM-DD, DD): ").strip()
                date = parse_date(date_str)
                totals = calculate_totals(date=date)
                display_totals(*totals, f"for {date}")
            
            elif choice == "5":
                year = int(input("Year (e.g., 2025): "))
                week_num = int(input("ISO Week number (1-53): "))
                totals = calculate_totals(week=(year, week_num))
                display_totals(*totals, f"for Week {week_num}, {year}")
            
            elif choice == "6":
                year = int(input("Year (e.g., 2025): "))
                month = int(input("Month (1-12): "))
                totals = calculate_totals(month=(year, month))
                month_name = calendar.month_name[month]
                display_totals(*totals, f"for {month_name} {year}")
            
            elif choice == "7":
                totals = calculate_totals()
                display_totals(*totals, "All Time")
            
            elif choice == "8":
                print("Exiting...")
                break
            
            else:
                print("Invalid choice. Please select 1-8.")
        
        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()