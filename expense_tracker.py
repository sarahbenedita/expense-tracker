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

def get_all_expenses_as_text():
    # Converts all database rows into plain text to send to Claude
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses ORDER BY date")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No expenses recorded yet."
    
    lines = ["date, category, description, amount"]
    for row in rows:
        lines.append(f"{row['date']}, {row['category']}, {row['description']}, ${row['amount']:.2f}")
    return "\n".join(lines)

def natural_language_query():
    # Lets the user ask questions in plain English
    console.print("\n[bold yan]--- Ask About Your Expenses ---[/bold cyan]")
    console.print("[dim]Example: How much did I spend on food? What was my biggest expense?[/dim]")

    question = input("Your question: ").strip()
    if not question:
        return
    
    expenses_text = get_all_expenses_as_text()
    client = get_ai_client()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                f"Here is my expense data:\n{expenses_text}\n\n"
                f"Answer this question clearly and concisely: {question}"
            )
        }]
    )

    console.print(f"\n[green]{response.content[0].text}[/green]")

def ai_spending_insights():
    # Asks Claude to analyze all expenses and give personalized tips
    console.print("\n[bold cyan]--- AI Spending Insights ---[/bold cyan]")

    expenses_text = get_all_expenses_as_text()
    client = get_ai_client()

    console.print("[dim]Analyzing your spending...[/dim]")

    response = client.messages.create(
        model="claude-haiku-4-5-2025-1001",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": (
                f"Here is my expense data:\n{expenses_text}\n\n"
                f"Give me 3 short, friendly, specific insights about my spending habits. "
                f"Point out patterns, biggest categories, and one tip to save money. "
                f"Keep it simple and encouraging."
            )
        }]
    )

    console.print(Panel(response.content[0].text, title="Your AI Insights", border_style="cyan"))

# MONTHLY REPORT & PDF EXPORT

def generate_monthly_report():
    console.print("\n[bold cyan]--- Monthly Report ---[/bold cyan]")

    # Ask which month/year to report on
    year = input("Year (e.g. 2026): ").strip()
    month = input("Month number (e.g. 7 for July): ").strip()

    try:
        year = int(year)
        month = int(month)
    except ValueError:
        console.print("[red]Invalid year or month.[/red]")
        return
    
    month_name = calendar.month_name[month]

    # Fetch all expenses for that month using SQL LIKE pattern matching
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM expenses WHERE date LIKE ? ORDER BY date",
        (f"{year}-{month:02d}-%",)
    )
    rows = cursor.fetchall()

    # Get category totals for this month
    cursor.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE date LIKE ? GROUP BY category ORDER BY total DESC",
        (f"{year}-{month:02}-%",)
    )
    by_category = cursor.fetchall()
    conn.close()

    if not rows:
        console.print(f"[yellow]No expenses found for {month_name} {year}.[/yellow]")
        return
    
    total = sum(row["amount"] for row in rows)

    # Print report to terminal
    console.print(f"\n[bold]Monthly Report - {month_name} {year}[/bold]")

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_coumn("Date", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Description")
    table.add_column("Amount", style="green", justify="right")

    for row in rows:
        table.add_row(row["data"], row["category"], row["description"], f"${row['amount']:.2f}")

    console.print(table)
    console.print(f"[bold green]Total for {month_name} {year}: ${total:.2f}[/bold green]")

    # Ask if user would like a PDF
    save_pdf = input("\nExport as PDF? (y/n): ").strip().lower()
    if save_pdf == "y":
        export_pdf(rows, by_category, total, month_name, year)

def export_pdf(rows, by_category, total, month_name, year):
    # Creates a PDF file of the monthly report using the fpdf2 library
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)

    # Title
    pdf.cell(0, 10, f"Expense Report - {month_name} {year}", ln=True, align="C")
    pdf.ln(5)

    # Summary Section
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Total Spent: ${total:.2f}", ln=True)
    pdf.ln(3)

    # Category breakdown
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Spending by Category:", ln=True)
    pdf.set_font("Helvetica", size=10)
    for row in by_category:
        pdf.cell(0, 7, f" {row['category']}: ${row['total']:.2f}", ln=True)
    pdf.ln(5)

    # Expense table header
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(35, 8, "Date", border=1)
    pdf.cell(40, 8, "Category", border=1)
    pdf.cell(75, 8, "Description", border=1)
    pdf.cell(35, 8, "Amount", border=1, align="R")
    pdf.ln()

    # Expense rows
    pdf.set_font("Helvetica", size=10)
    for row in rows:
        pdf.cell(35, 7, row["date"], border=1)
        pdf.cell(40, 7, row["category"], border=1)
        pdf.cell(75, 7, row["description"][:40], border=1) # Truncate long descriptions
        pdf.cell(35, 7, f"${row['amount']:.2f}", border=1, align="R")
        pdf.ln()

    # Save the PDF file
    filename = f"report_{month_name}_{year}.pdf"
    pdf.output(filename)
    console.print(f"[green]PDF saved as: {filename}[/green]")

# MAIN MENU

def main():
    create_table() # Set up the database on first run

    while True:
        console.print("\n[bold cyan]--- Expense Tracker ---[/bold cyan]")
        console.print("1. Add expense")
        console.print("2. View all expenses")
        console.print("3. Filter by category")
        console.print("4. Total spent")
        console.print("5. Dashboard")
        console.print("6. Ask AI a question")
        console.print("7. AI spending insights")
        console.print("8. Monthly report + PDF export")
        console.print("9. Exit")

        choice = input("\nEnter your choice (1-9): ").strip()

        if choice == "1":
            add_expense()
        elif choice == "2":
            view_expenses()
        elif choice == "3":
            filter_by_category()
        elif choice == "4":
            total_spent()
        elif choice == "5":
            show_dashboard()
        elif choice == "6":
            natural_language_query()
        elif choice == "7":
            ai_spending_insights()
        elif choice == "8":
            generate_monthly_report()
        elif choice == "9":
            console.print("[cyan]Goodbye![/cyan]")
            break
        else:
            console.print("[red]Invalid choice. Please enter a number between 1-9.[/red]")

# Run the program
main()