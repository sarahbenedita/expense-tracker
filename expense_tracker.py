# AI-powered CLI Expense Tracker
# Built with Python, SQLite, Claude AI, Rich, and FPDF

import sqlite3
import os
import calendar
import anthropic
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from fpdf import FPDF

# Rich console for pretty terminal output
console = Console()

# DATABASE SETUP

def connect():
    conn = sqlite3.connect("expenses.db") # Opens or creates the expenses.db file
    conn.row_factory = sqlite3.Row # Lets us access coumns by name
    return conn

def create_table():
    # Creates the expenses table if it doesn't already exist
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS expenses (
                   id       INTEGER PRIMARY KEY AUTOINCREMENT,
                   date     TEXT,
                   category     TEXT,
                   description      TEXT,
                   amount       REAL
                   )
                """)
    conn.commit()
    conn.close()
    
# AI SETUP

def get_ai_client():
    # Reads the API key from a local file called api_key.txt
    # If the file doesn't exist, asks the user to enter their key and saves it
    key_file = "api_key.txt"
    if os.path.exists(key_file):
        with open(key_file, "r") as f:
            api_key = f.read().strip()
    else:
        console.print("\n[yellow]No API key found. Get a free key at console.anthropic.com[/yellow]")
        api_key = input("Paste your Anthropic API key here: ").strip()
        with open(key_file, "w") as f:
            f.write(api_key)
        console.print("[green]API key saved![/green]")
    return anthropic.Anthropic(api_key=api_key)

# ADD EXPENSE

def ai_categorize(description, client):
    # Uses Claude AI to guess the category based on the description
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        messages=[{
            "role": "user",
            "content": (
                f"Categorize this expense into ONE of these categories: "
                f"Food, Transport, Bills, Shopping, Health, Entertainment, Other.\n"
                f"Expense: {description}\n"
                f"Reply with only the category name, nothing else."
            )
        }]
    )
    return response.content[0].text.strip()

def add_expense():
    console.print("\n[bold cyan]--- Add New Expense ---[/bold cyan]")

    # Get the date (defaults to current date if the user just clicks Enter
    today = datetime.today().strftime("%Y-%m-%d")
    date_input = input(f"Date (press Enter for today {today}):").strip()
    date = date_input if date_input else today
    description = input("description: ").strip()

    # Asf if user wants AI to auto-categorize
    use_ai = input("Auto-categorize with AI? (y/n): ").strip().lower()
    if use_ai == "y":
        client = get_ai_client()
        category = ai_categorize(description, client)
        console.print(f"[green]AI suggests: {category}[/green]")
        confirm = input(f"Use '{category}'? (y/n): ").strip().lower()
        if confirm != "y":
            category = input("Enter category manually (Food/Transport/Bills/Shopping/Health/Entertainment/Other): ").strip()
        else:
            category = input("Category (Food/Transport/Bills/Shopping/Health/Entertainment/Other): ").strip()

        # Keep asking user until a valid number is entered
        while True:
            amount_input = input("Amount (e.g. 12.50): ").strip()
            try:
                amount = float(amount_input)
                break
            except ValueError:
                console.print("[red]That doesn't look like a numer. Please try again.[/red]")
        
        # Save to database
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
            (date, category, description, amount)
        )
        conn.commit()
        conn.close()
        
        console.print(f"[green]Saved: {description} - ${amount:.2f} ({category})[/green]")

# VIEW EXPENSES

def view_expenses():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]No expenses found.[/yellow]")
        return
    
    # Build a Rich table for clean terminal output
    table = Table(title="All Expenses", box=box.ROUNDED, show_lines=True)
    table.add_column("ID", style="dim", width=5)
    table.add_column("Date", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Description")
    table.add_column("Amount", style="green", justify="right")

    for row in rows:
        table.add_row(
            str(row["id"]),
            row["date"],
            row["category"],
            row["description"],
            f"${row['amount']:.2f}"
        )

    console.print(table)

# TOTAL SPENT

def total_spent():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM expenses")
    result = cursor.fetchone()[0] # fetchone() gets a single now and [0] gets the first value
    conn.close()

    total = result if result else 0 # If no expenses yet, default value to 0
    console.print(f"\n[bold green]Total spent: ${total:.2f}[/bold green]")

# FILTER BY CATEGORY

def filter_by_category():
    category = input("\nEnter category to filter(Food/Transport/Bills/Shopping/Health/Entertainment/Other): ").strip()

    conn = connect()
    cursor = conn.cursor()

    # The ? safely inserts category variable into the SQL query
    cursor.execute("SELECT * FROM expenses WHERE category = ? ORDER BY date DESC", (category,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        console.print(f"[yellow]No expenses found in category: {category}[/yellow]")
        return
    
    table = Table(title=f"Expenses - {category}", box=box.ROUNDED, show_lines=True)
    table.add_column("Date", style="cyan")
    table.add_column("Description")
    table.add_column("Amount", style="green", justify="right")

    total = 0
    for row in rows:
        table.add_row(row["date"], row["description"], f"${row['amount']:.2f}")
        total += row["amount"]

        console.print(table)
        console.print(f"[bold green]Total for {category}: ${total:.2f}[/bold green]")

# DASHBOARD

def show_dashboard():
    conn = connect()
    cursor = conn.cursor()

    # Get total spent
    cursor.execute("SELECT SUM(amount) FROM expenses")
    total = cursor.fetchone()[0] or 0

    # Get spending by category
    cursor.execute("SELECT category, SUM(amount) as total FROM expenses GROUP BY category ORDER BY total DESC")
    by_category = cursor.fetchall()

    # Get the 5 most recent expenses
    cursor.execute("SELECT * FROM expenses ORDER BY date DESC LIMIT 5")
    recent = cursor.fetchall()

    conn.close()

    console.print(Panel(f"[bold green]Total spent: ${total:.2f}[/bold green]", title="Epense Dashboard"))

    # Category breakdown table
    if by_category:
        cat_table = Table(title="Spending by Category", box=box.SIMPLE)
        cat_table.add_column("Category", style="magenta")
        cat_table.add_column("Total", style="green", justify="right")
        cat_table.add_column("% of Spending", justify="right")

        for row in by_category:
            pct = (row["total"] / total * 100) if total > 0 else 0
            cat_table.add_row(row["category"], f"${row['total']:.2f}", f"{pct:.1f}%")

            console.print(cat_table)

    # Recent expenses table
    if recent:
        recent_table = Table(title="5 Most Recent Expenses", box=box.SIMPLE)
        recent_table.add_column("Date", style="cyan")
        recent_table.add_column("Category", style="magenta")
        recent_table.add_column("Description")
        recent_table.add_column("Amount", style="green", justify="right")

        for row in recent:
            recent_table.add_row(row["date"], row["category"], row["description"], f"${row['amount']:.2f}")

            console.print(recent_table)

# AI FEATURES


                                