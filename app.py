import os
import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt

# Database setup
DB_FILE = "enhanced_expenses.db"
EXCEL_FILE = "transactions.xlsx"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            amount INTEGER,
            type TEXT,
            category TEXT,
            description TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def add_transaction(date, amount, transaction_type, category, description):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (date, amount, type, category, description)
        VALUES (?, ?, ?, ?, ?)
    """, (date, amount, transaction_type, category, description))
    conn.commit()
    conn.close()

def get_transactions():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    return df

def delete_transaction(transaction_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()

def get_categories():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

def add_category(category_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Category already exists
    conn.close()

# Function to save transactions to Excel
def save_to_excel():
    df = get_transactions()
    if not df.empty:
        if os.path.exists(EXCEL_FILE):
            # If file exists, append data
            df_existing = pd.read_excel(EXCEL_FILE)
            df_combined = pd.concat([df_existing, df], ignore_index=True)
            df_combined.to_excel(EXCEL_FILE, index=False)
        else:
            # If file doesn't exist, create it
            df.to_excel(EXCEL_FILE, index=False)
        st.success(f"Transactions saved to {EXCEL_FILE} successfully!")
    else:
        st.info("No transactions to save.")

# Initialize database and default categories
init_db()
default_categories = ["Rent", "Groceries", "Entertainment", "Utilities", "Food", "Mutual Funds", "Investments", "Others"]
for category in default_categories:
    add_category(category)

# Streamlit UI
st.set_page_config(page_title="Enhanced Expense Tracker", layout="wide")

# Sidebar navigation
menu = ["Dashboard", "Add Income", "Add Expense", "Transaction History", "Manage Categories"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Dashboard":
    st.title("📊 Enhanced Expense Tracker Dashboard")
    df = get_transactions()

    if not df.empty:
        # Income, Expenses, and Savings
        income = df[df["type"] == "Income"]["amount"].sum()
        expenses = df[df["type"] == "Expense"]["amount"].sum()
        savings = income - expenses

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹{income:,}")
        col2.metric("Total Expenses", f"₹{expenses:,}")
        col3.metric("Savings", f"₹{savings:,}")

        # Expense category breakdown
        st.subheader("Expense Breakdown by Category")
        expense_data = df[df["type"] == "Expense"].groupby("category")["amount"].sum()

        if not expense_data.empty:
            fig, ax = plt.subplots()
            ax.pie(expense_data, labels=expense_data.index, autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
            st.pyplot(fig)

        # Monthly trends
        st.subheader("Monthly Trends (Income vs Expenses)")
        df["date"] = pd.to_datetime(df["date"])
        monthly_data = df.groupby([df["date"].dt.to_period("M"), "type"])["amount"].sum().unstack()
        monthly_data = monthly_data.fillna(0)
        monthly_data.index = monthly_data.index.astype(str)

        st.line_chart(monthly_data)

        # Yearly comparison
        st.subheader("Yearly Comparison (Income vs Expenses)")
        yearly_data = df.groupby([df["date"].dt.year, "type"])["amount"].sum().unstack()
        yearly_data = yearly_data.fillna(0)

        st.bar_chart(yearly_data)
    else:
        st.info("No transactions found! Add transactions to see the dashboard.")
elif choice == "Add Income":
    st.title("💰 Add Income")
    categories = get_categories()

    with st.form("Income Form"):
        date = st.date_input("Date")
        amount = st.number_input("Amount", min_value=1, step=1, format="%d")
        category = st.selectbox("Category", categories)
        description = st.text_area("Description (Optional)")
        submitted = st.form_submit_button("Add Income")  # Removed the type argument

        if submitted:
            add_transaction(date, amount, "Income", category, description)
            st.success(f"Income of ₹{amount:,} added successfully!")

elif choice == "Add Expense":
    st.title("💸 Add Expense")
    categories = get_categories()

    with st.form("Expense Form"):
        date = st.date_input("Date")
        amount = st.number_input("Amount", min_value=1, step=1, format="%d")
        category = st.selectbox("Category", categories)
        description = st.text_area("Description (Optional)")
        submitted = st.form_submit_button("Add Expense")  # Removed the type argument

        if submitted:
            add_transaction(date, amount, "Expense", category, description)
            st.success(f"Expense of ₹{amount:,} added successfully!")

elif choice == "Transaction History":
    st.title("📜 Transaction History")
    df = get_transactions()

    if not df.empty:
        # Display transaction table
        st.write("### All Transactions")
        df["Action"] = ["Delete"] * len(df)  # Add an Action column with 'Delete' labels
        for idx, row in df.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
            col1.write(row["id"])
            col2.write(row["date"])
            col3.write(f"₹{row['amount']:,}")
            col4.write(row["type"])
            col5.write(row["category"])
            col6.write(row["description"] if row["description"] else "-")
            delete_button = col7.button("Delete", key=f"delete_{row['id']}")
            
            # Handle delete button
            if delete_button:
                delete_transaction(row["id"])
                st.success(f"Transaction with ID {row['id']} deleted successfully!")
                df = get_transactions()  # Refresh the page to show updated transactions
                
        save_trans = st.toggle("Save the Transactions")
        if save_trans:
            save_to_excel()
    else:
        st.info("No transactions found!")

elif choice == "Manage Categories":
    st.title("⚙️ Manage Categories")
    categories = get_categories()
    st.write("### Existing Categories")
    st.write(", ".join(categories))

    with st.form("Add Category Form"):
        new_category = st.text_input("New Category Name")
        submitted = st.form_submit_button("Add Category")
        if submitted and new_category.strip():
            add_category(new_category.strip())
            st.success(f"Category '{new_category}' added successfully!")

