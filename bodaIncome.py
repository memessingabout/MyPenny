import json
import datetime
from datetime import datetime as dt
from pathlib import Path
import re
import calendar

# File to store income data
DATA_FILE = "boda_income.json"

# Platform mappings
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
            return json.load(f)
    return {"income": []}

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
    print(f"Added: {date} - {platform} - {amount:.2f} KES - {notes}")

def calculate_totals(date=None, week=None, month=None):
    """Calculate totals by date, week, or month."""
    data = load_data()
    totals = {
        "total": 0,
        "Uber": 0,
        "Bolt": 0,
        "Littlecab": 0,
        "Offline": 0
    }
    daily_totals = {}
    weekly_totals = {}

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

        # Update totals
        totals["total"] += amount
        totals[platform] += amount

        # Daily totals
        date_str = entry_date.isoformat()
        if date_str not in daily_totals:
            daily_totals[date_str] = {"total": 0, "Uber": 0, "Bolt": 0, "Littlecab": 0, "Offline": 0}
        daily_totals[date_str]["total"] += amount
        daily_totals[date_str][platform] += amount

        # Weekly totals
        week_num = entry_date.isocalendar()
        week_key = f"{week_num[0]}-W{week_num[1]:02d}"
        if week_key not in weekly_totals:
            weekly_totals[week_key] = {"total": 0, "Uber": 0, "Bolt": 0, "Littlecab": 0, "Offline": 0}
        weekly_totals[week_key]["total"] += amount
        weekly_totals[week_key][platform] += amount

    return totals, daily_totals, weekly_totals

def display_totals(totals, daily_totals, weekly_totals, period=""):
    """Display income totals."""
    print(f"\nIncome: {totals['total']:.2f} KES {period}")
    print("\nPlatform Breakdown:")
    for platform in ["Uber", "Bolt", "Littlecab", "Offline"]:
        print(f"{platform}: {totals[platform]:.2f} KES")

    if daily_totals:
        print("\nDaily Totals:")
        for date in sorted(daily_totals.keys()):
            print(f"{date}: {daily_totals[date]['total']:.2f} KES")
            for platform in ["Uber", "Bolt", "Littlecab", "Offline"]:
                if daily_totals[date][platform] > 0:
                    print(f"  {platform}: {daily_totals[date][platform]:.2f} KES")

    if weekly_totals:
        print("\nWeekly Totals (Monday-Sunday, ISO Week):")
        for week in sorted(weekly_totals.keys()):
            print(f"{week}: {weekly_totals[week]['total']:.2f} KES")
            for platform in ["Uber", "Bolt", "Littlecab", "Offline"]:
                if weekly_totals[week][platform] > 0:
                    print(f"  {platform}: {weekly_totals[week][platform]:.2f} KES")

def main():
    """Main command-line interface."""
    while True:
        print("\nBoda Boda Income Tracker")
        print("1. Add Income")
        print("2. View Totals by Date")
        print("3. View Totals by Week")
        print("4. View Totals by Month")
        print("5. View All Time Totals")
        print("6. Exit")
        
        choice = input("Select option (1-6): ").strip()
        
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
                date_str = input("Date (YYYY-MM-DD, MM-DD, DD): ").strip()
                date = parse_date(date_str)
                totals, daily_totals, _ = calculate_totals(date=date)
                display_totals(totals, daily_totals, {}, f"for {date}")
            
            elif choice == "3":
                year = int(input("Year (e.g., 2025): "))
                week_num = int(input("ISO Week number (1-53): "))
                totals, daily_totals, weekly_totals = calculate_totals(week=(year, week_num))
                display_totals(totals, daily_totals, weekly_totals, f"for Week {week_num}, {year}")
            
            elif choice == "4":
                year = int(input("Year (e.g., 2025): "))
                month = int(input("Month (1-12): "))
                totals, daily_totals, weekly_totals = calculate_totals(month=(year, month))
                month_name = calendar.month_name[month]
                display_totals(totals, daily_totals, weekly_totals, f"for {month_name} {year}")
            
            elif choice == "5":
                totals, daily_totals, weekly_totals = calculate_totals()
                display_totals(totals, {}, weekly_totals, "All Time")
            
            elif choice == "6":
                print("Exiting...")
                break
            
            else:
                print("Invalid choice. Please select 1-6.")
        
        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()