import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# Initialize session state
if 'categories' not in st.session_state:
    st.session_state.categories = ['Salary', 'Food', 'Rent', 'Utilities', 'Entertainment']

# Connect to SQLite database
conn = sqlite3.connect('expenses.db', check_same_thread=False)
c = conn.cursor()

# Create table if it doesn't exist
c.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        type TEXT,
        category TEXT,
        description TEXT,
        amount REAL
    )
''')
conn.commit()

# Function to add a transaction
def add_transaction(date, trans_type, category, description, amount):
    c.execute('INSERT INTO transactions (date, type, category, description, amount) VALUES (?, ?, ?, ?, ?)',
              (date, trans_type, category, description, amount))
    conn.commit()

# Function to fetch transactions
def get_transactions():
    c.execute('SELECT * FROM transactions')
    return c.fetchall()

# Function to delete a transaction
def delete_transaction(trans_id):
    c.execute('DELETE FROM transactions WHERE id = ?', (trans_id,))
    conn.commit()

# Sidebar for navigation
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Go to", ["Add Transaction", "View Transactions", "Analytics", "Settings"])

# Add Transaction Page
if menu == "Add Transaction":
    st.title("Add Income / Expense")

    with st.form(key='add_form'):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date", datetime.now())
            trans_type = st.selectbox("Type", ["Income", "Expense"])
            amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        with col2:
            category = st.selectbox("Category", st.session_state.categories + ["Add New Category"])
            if category == "Add New Category":
                new_category = st.text_input("New Category")
                if new_category:
                    st.session_state.categories.append(new_category)
                    category = new_category
            description = st.text_input("Description")

        submit = st.form_submit_button("Add")
        if submit:
            add_transaction(date.strftime("%Y-%m-%d"), trans_type, category, description, amount)
            st.success("Transaction added successfully!")

# View Transactions Page
elif menu == "View Transactions":
    st.title("Transaction History")

    transactions = get_transactions()
    df = pd.DataFrame(transactions, columns=['ID', 'Date', 'Type', 'Category', 'Description', 'Amount'])

    if not df.empty:
        # Filters
        with st.expander("Filters"):
            col1, col2, col3 = st.columns(3)
            with col1:
                start_date = st.date_input("Start Date", datetime.now())
            with col2:
                end_date = st.date_input("End Date", datetime.now())
            with col3:
                trans_type_filter = st.multiselect("Type", options=df['Type'].unique(), default=df['Type'].unique())

            category_filter = st.multiselect("Category", options=df['Category'].unique(), default=df['Category'].unique())

        # Apply filters
        df['Date'] = pd.to_datetime(df['Date'])
        mask = (df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))
        df = df[mask]
        df = df[df['Type'].isin(trans_type_filter)]
        df = df[df['Category'].isin(category_filter)]

        st.dataframe(df[['Date', 'Type', 'Category', 'Description', 'Amount']])

        # Delete transaction
        with st.expander("Delete Transaction"):
            trans_id = st.number_input("Enter Transaction ID to delete", min_value=1, step=1)
            if st.button("Delete"):
                delete_transaction(trans_id)
                st.success(f"Transaction ID {trans_id} deleted.")
    else:
        st.info("No transactions found.")

# Analytics Page
elif menu == "Analytics":
    st.title("Analytics")

    transactions = get_transactions()
    df = pd.DataFrame(transactions, columns=['ID', 'Date', 'Type', 'Category', 'Description', 'Amount'])

    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        df['Month'] = df['Date'].dt.to_period('M')

        # Summary
        total_income = df[df['Type'] == 'Income']['Amount'].sum()
        total_expense = df[df['Type'] == 'Expense']['Amount'].sum()
        balance = total_income - total_expense

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹ {total_income:,.2f}")
        col2.metric("Total Expense", f"₹ {total_expense:,.2f}")
        col3.metric("Balance", f"₹ {balance:,.2f}")

        # Pie Chart
        st.subheader("Expenses by Category")
        expense_df = df[df['Type'] == 'Expense']
        if not expense_df.empty:
            fig = px.pie(expense_df, names='Category', values='Amount', title='Expenses by Category')
            st.plotly_chart(fig)
        else:
            st.info("No expense data to display.")

        # Line Chart
        st.subheader("Monthly Income vs Expense")
        monthly_data = df.groupby(['Month', 'Type'])['Amount'].sum().unstack().fillna(0)
        monthly_data = monthly_data.reset_index()
        monthly_data['Month'] = monthly_data['Month'].astype(str)
        fig2 = px.line(monthly_data, x='Month', y=['Income', 'Expense'], markers=True)
        st.plotly_chart(fig2)
    else:
        st.info("No transactions to analyze.")

# Settings Page
elif menu == "Settings":
    st.title("Settings")

    # Export Data
    st.subheader("Export Transactions")
    transactions = get_transactions()
    df = pd.DataFrame(transactions, columns=['ID', 'Date', 'Type', 'Category', 'Description', 'Amount'])
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", data=csv, file_name='transactions.csv', mime='text/csv')

    # Import Data
    st.subheader("Import Transactions")
    uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
    if uploaded_file:
        import_df = pd.read_csv(uploaded_file)
        for _, row in import_df.iterrows():
            add_transaction(row['Date'], row['Type'], row['Category'], row['Description'], row['Amount'])
        st.success("Transactions imported successfully!")
