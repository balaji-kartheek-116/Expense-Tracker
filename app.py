import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import calendar
import sqlite3
from pathlib import Path

# Initialize database
def init_db():
    conn = sqlite3.connect('expense_tracker.db')
    c = conn.cursor()
    
    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  type TEXT,
                  amount REAL,
                  category TEXT,
                  date DATE,
                  description TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS categories
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  type TEXT)''')
    
    # Insert default categories if they don't exist
    default_expense_categories = ['Food', 'Transport', 'Housing', 'Entertainment', 'Healthcare', 'Education', 'Shopping', 'Others']
    default_income_categories = ['Salary', 'Bonus', 'Freelance', 'Investment', 'Gift', 'Others']
    
    for cat in default_expense_categories:
        try:
            c.execute("INSERT INTO categories (name, type) VALUES (?, 'expense')", (cat,))
        except sqlite3.IntegrityError:
            pass
    
    for cat in default_income_categories:
        try:
            c.execute("INSERT INTO categories (name, type) VALUES (?, 'income')", (cat,))
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    conn.close()

init_db()

# Helper functions
def get_categories(transaction_type):
    conn = sqlite3.connect('expense_tracker.db')
    c = conn.cursor()
    c.execute("SELECT name FROM categories WHERE type = ? ORDER BY name", (transaction_type,))
    categories = [row[0] for row in c.fetchall()]
    conn.close()
    return categories

def add_category(name, transaction_type):
    conn = sqlite3.connect('expense_tracker.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (name, transaction_type))
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning("Category already exists!")
    finally:
        conn.close()

def add_transaction(transaction_type, amount, category, date, description):
    conn = sqlite3.connect('expense_tracker.db')
    c = conn.cursor()
    c.execute("INSERT INTO transactions (type, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
              (transaction_type, amount, category, date, description))
    conn.commit()
    conn.close()

def get_transactions(start_date=None, end_date=None, categories=None, transaction_type=None):
    conn = sqlite3.connect('expense_tracker.db')
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if categories:
        query += " AND category IN ({})".format(','.join(['?']*len(categories)))
        params.extend(categories)
    if transaction_type:
        query += " AND type = ?"
        params.append(transaction_type)
    
    query += " ORDER BY date DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_balance():
    conn = sqlite3.connect('expense_tracker.db')
    income = pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'income'", conn).iloc[0,0]
    expenses = pd.read_sql_query("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'expense'", conn).iloc[0,0]
    conn.close()
    return income - expenses

def get_monthly_summary():
    conn = sqlite3.connect('expense_tracker.db')
    query = """
    SELECT 
        strftime('%Y-%m', date) as month,
        SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
        SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense,
        SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END) as balance
    FROM transactions
    GROUP BY strftime('%Y-%m', date)
    ORDER BY month DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Streamlit App
st.set_page_config(page_title="Expense Tracker", layout="wide", page_icon="💰")

st.title("💰 Personal Expense Tracker")

# Sidebar for navigation
menu = st.sidebar.selectbox("Menu", ["Dashboard", "Add Transaction", "Transaction History", "Category Management", "Reports"])

if menu == "Dashboard":
    st.header("Financial Overview")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Balance", f"₹{get_balance():,.2f}")
    with col2:
        st.metric("Total Income", f"₹{get_transactions(transaction_type='income')['amount'].sum():,.2f}")
    with col3:
        st.metric("Total Expenses", f"₹{get_transactions(transaction_type='expense')['amount'].sum():,.2f}")
    
    # Monthly summary chart
    st.subheader("Monthly Summary")
    monthly_df = get_monthly_summary()
    if not monthly_df.empty:
        fig = px.bar(monthly_df, x='month', y=['income', 'expense'], 
                     barmode='group', title="Income vs Expenses by Month")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No transactions yet. Add some to see your financial trends!")
    
    # Recent transactions
    st.subheader("Recent Transactions")
    recent_transactions = get_transactions().head(10)
    st.dataframe(recent_transactions.drop(columns=['id']), hide_index=True, use_container_width=True)

elif menu == "Add Transaction":
    st.header("Add New Transaction")
    
    with st.form("transaction_form"):
        col1, col2 = st.columns(2)
        with col1:
            transaction_type = st.radio("Transaction Type", ["expense", "income"], horizontal=True)
        with col2:
            amount = st.number_input("Amount", min_value=0.01, step=0.01, format="%.2f")
        
        categories = get_categories(transaction_type)
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", categories)
        with col2:
            new_category = st.text_input("Or add new category")
            if new_category:
                add_category(new_category, transaction_type)
                st.success(f"Category '{new_category}' added!")
                st.experimental_rerun()
        
        date = st.date_input("Date", datetime.now())
        description = st.text_input("Description (optional)")
        
        submitted = st.form_submit_button("Add Transaction")
        if submitted:
            add_transaction(transaction_type, amount, category, date, description)
            st.success("Transaction added successfully!")

elif menu == "Transaction History":
    st.header("Transaction History")
    
    with st.expander("Filters"):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", datetime.now())
        
        transaction_type_filter = st.selectbox("Transaction Type", ["All", "income", "expense"])
        
        all_categories = get_categories('income') + get_categories('expense')
        selected_categories = st.multiselect("Categories", all_categories)
    
    filters = {}
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date
    if transaction_type_filter != "All":
        filters['transaction_type'] = transaction_type_filter
    if selected_categories:
        filters['categories'] = selected_categories
    
    transactions = get_transactions(**filters)
    
    if not transactions.empty:
        st.dataframe(transactions.drop(columns=['id']), hide_index=True, use_container_width=True)
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download as CSV",
                transactions.to_csv(index=False),
                "transactions.csv",
                "text/csv"
            )
        with col2:
            st.download_button(
                "Download as Excel",
                transactions.to_excel(excel_writer="transactions.xlsx", index=False),
                "transactions.xlsx",
                "application/vnd.ms-excel"
            )
    else:
        st.info("No transactions found with the selected filters.")

elif menu == "Category Management":
    st.header("Category Management")
    
    tab1, tab2 = st.tabs(["Expense Categories", "Income Categories"])
    
    with tab1:
        st.subheader("Expense Categories")
        expense_categories = get_categories('expense')
        st.dataframe(pd.DataFrame(expense_categories, columns=["Category"]), hide_index=True)
        
        with st.form("new_expense_category"):
            new_category = st.text_input("Add New Expense Category")
            submitted = st.form_submit_button("Add")
            if submitted and new_category:
                add_category(new_category, 'expense')
                st.success(f"Category '{new_category}' added!")
                st.experimental_rerun()
    
    with tab2:
        st.subheader("Income Categories")
        income_categories = get_categories('income')
        st.dataframe(pd.DataFrame(income_categories, columns=["Category"]), hide_index=True)
        
        with st.form("new_income_category"):
            new_category = st.text_input("Add New Income Category")
            submitted = st.form_submit_button("Add")
            if submitted and new_category:
                add_category(new_category, 'income')
                st.success(f"Category '{new_category}' added!")
                st.experimental_rerun()

elif menu == "Reports":
    st.header("Financial Reports")
    
    tab1, tab2, tab3 = st.tabs(["Spending by Category", "Monthly Trends", "Yearly Overview"])
    
    with tab1:
        st.subheader("Spending by Category")
        time_range = st.selectbox("Time Range", ["Last 30 Days", "Last 90 Days", "This Year", "All Time"])
        
        if time_range == "Last 30 Days":
            start_date = datetime.now() - timedelta(days=30)
        elif time_range == "Last 90 Days":
            start_date = datetime.now() - timedelta(days=90)
        elif time_range == "This Year":
            start_date = datetime(datetime.now().year, 1, 1)
        else:
            start_date = None
        
        expenses = get_transactions(start_date=start_date, transaction_type='expense')
        
        if not expenses.empty:
            fig = px.pie(expenses, names='category', values='amount', 
                         title=f"Expense Distribution {f'since {start_date.strftime("%Y-%m-%d")}' if start_date else ''}")
            st.plotly_chart(fig, use_container_width=True)
            
            # Top expenses
            st.subheader("Top Expenses")
            top_expenses = expenses.groupby('category')['amount'].sum().sort_values(ascending=False).reset_index()
            st.dataframe(top_expenses, hide_index=True, use_container_width=True)
        else:
            st.info("No expense data available for the selected time range.")
    
    with tab2:
        st.subheader("Monthly Trends")
        
        monthly_summary = get_monthly_summary()
        if not monthly_summary.empty:
            fig = px.line(monthly_summary, x='month', y=['income', 'expense', 'balance'], 
                          title="Monthly Financial Trends")
            st.plotly_chart(fig, use_container_width=True)
            
            # Monthly details
            st.dataframe(monthly_summary, hide_index=True, use_container_width=True)
        else:
            st.info("No data available for monthly trends.")
    
    with tab3:
        st.subheader("Yearly Overview")
        current_year = datetime.now().year
        year = st.selectbox("Select Year", range(current_year, current_year - 5, -1))
        
        yearly_data = get_transactions(
            start_date=f"{year}-01-01",
            end_date=f"{year}-12-31"
        )
        
        if not yearly_data.empty:
            # Yearly summary
            yearly_summary = yearly_data.groupby('type')['amount'].sum().reset_index()
            fig = px.bar(yearly_summary, x='type', y='amount', 
                         title=f"Year {year} Summary")
            st.plotly_chart(fig, use_container_width=True)
            
            # Monthly breakdown
            yearly_data['month'] = pd.to_datetime(yearly_data['date']).dt.month
            monthly_breakdown = yearly_data.groupby(['month', 'type'])['amount'].sum().unstack().fillna(0)
            monthly_breakdown.index = monthly_breakdown.index.map(lambda x: calendar.month_abbr[x])
            fig = px.bar(monthly_breakdown, x=monthly_breakdown.index, y=['income', 'expense'], 
                         barmode='group', title=f"Monthly Breakdown for {year}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No data available for year {year}.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Built with ❤️ using Streamlit")
