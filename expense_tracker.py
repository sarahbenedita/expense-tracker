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