import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
from neo4j import GraphDatabase
import csv
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tkinter.ttk as ttk  # Import ttk for Treeview widget


# Neo4j database connection
class Neo4jDatabase:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_node(self, label, attributes):
        with self.driver.session() as session:
            session.write_transaction(self._create_node, label, attributes)

    def create_relationship(self, start_node, end_node, relation, attributes):
        with self.driver.session() as session:
            session.write_transaction(self._create_relationship, start_node, end_node, relation, attributes)

    def create_schema(self, label):
        with self.driver.session() as session:
            session.write_transaction(self._create_schema, label)

    def delete_node(self, label):
        with self.driver.session() as session:
            session.write_transaction(self._delete_node, label)

    def delete_relationship(self, label):
        with self.driver.session() as session:
            session.write_transaction(self._delete_relationship, label)

    @staticmethod
    def _create_node(tx, label, attributes):
        query = f"CREATE (n:{label} {{"
        query += ", ".join([f"{key}: ${key}" for key in attributes.keys()])
        query += "})"
        tx.run(query, **attributes)

    @staticmethod
    def _create_schema(tx, label):
        # query = f"CREATE CONSTRAINT {label}_ID IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
        # tx.run(query)
        query = f"CREATE CONSTRAINT {label}"
        query += "_"
        query += "ID"
        query += f" IF NOT EXISTS FOR (n:{label})"
        query += f" REQUIRE n.id IS UNIQUE"
        tx.run(query)

    @staticmethod
    def _create_relationship(tx, start_node, end_node, relation, attributes):
        query = (
            f"MATCH (a:{start_node}), (b:{end_node}) "
            f"WHERE a.id = $start_id AND b.id = $end_id "
            f"CREATE (a)-[r:{relation} {{"
        )
        query += ", ".join([f"{key}: ${key}" for key in attributes.keys()])
        query += "}]->(b)"
        parameters = {**attributes, 'start_id': attributes.get('start_id'), 'end_id': attributes.get('end_id')}
        tx.run(query, **parameters)

    @staticmethod
    def _delete_node(tx, label):
        query = f"MATCH (n:{label}) DETACH DELETE n"
        tx.run(query)

    @staticmethod
    def _delete_relationship(tx, label):
        query = f"MATCH ()-[r:{label}]->() DETACH DELETE r"
        tx.run(query)


# Load CSV data
def load_data(file_path):
    data = []
    with open(file_path, mode='r') as file:
        first_line = file.readline()
        delimiter = ';' if ';' in first_line else ','
        file.seek(0)
        csv_reader = csv.DictReader(file, delimiter=delimiter)
        for row in csv_reader:
            data.append(row)
    return data


# Login Page
class LoginPage:
    def __init__(self, root):
        self.root = root
        self.root.title("Neo4j Database Login")
        self.root.configure(bg='light grey')

        self.label = tk.Label(root, text="Login", bg='light grey', fg='black', font=('Helvetica', 16))
        self.label.pack(pady=20)

        self.username_label = tk.Label(root, text="Username", bg='light grey', fg='black')
        self.username_label.pack(pady=5)
        self.username_entry = tk.Entry(root, width=50)
        self.username_entry.pack(pady=5)
        self.username_entry.insert(0, "neo4j")

        self.password_label = tk.Label(root, text="Password", bg='light grey', fg='black')
        self.password_label.pack(pady=5)
        self.password_entry = tk.Entry(root, show='*', width=50)
        self.password_entry.pack(pady=5)

        self.role_label = tk.Label(root, text="Role", bg='light grey', fg='black')
        self.role_label.pack(pady=5)
        self.role_select = ttk.Combobox(root, values=["admin", "user"])
        self.role_select.pack(pady=5)

        self.login_button = tk.Button(root, text="Login", command=self.login, bg='light blue')
        self.login_button.pack(pady=20)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        role = self.role_select.get()

        if username and password and role:
            self.root.destroy()
            root = tk.Tk()
            if role == "admin":
                app = AdminGUI(root, username, password)
                app.initialization()
            else:
                app = UserGUI(root, username, password)
            root.mainloop()
        else:
            messagebox.showerror("Error", "All fields are required")


# Admin Interface
class AdminGUI:
    def __init__(self, root, username, password):
        self.root = root
        self.root.title("Neo4j Database Admin Manager")
        self.root.configure(bg='light grey')

        self.uri = "bolt://localhost:7687"
        self.user = username
        self.password = password
        self.node_list = []
        self.rel_list = []
        self.initialization()

        # Left column - Database creation
        self.left_frame = tk.Frame(root, bg='light grey')
        self.left_frame.grid(row=0, column=0, padx=20, pady=20, sticky='n')

        self.label1 = tk.Label(self.left_frame, text="Node Creation:", bg='light grey', fg='blue')
        self.label1.pack(pady=10)
        self.node_label_entry = tk.Entry(self.left_frame, width=50)
        self.node_label_entry.pack(pady=5)
        self.node_label_entry.insert(0, "Enter Node Label")

        self.load_file_button = tk.Button(self.left_frame, text="Load & Create Node", command=self.load_file,
                                          bg='light blue')
        self.load_file_button.pack(pady=5)

        self.label2 = tk.Label(self.left_frame, text="Relationship Creation:", bg='light grey', fg='green')
        self.label2.pack(pady=12)
        self.start_node_entry = tk.Entry(self.left_frame, width=50)
        self.start_node_entry.pack(pady=5)
        self.start_node_entry.insert(0, "Enter Start Node Label")

        self.relation_label_entry = tk.Entry(self.left_frame, width=50)
        self.relation_label_entry.pack(pady=5)
        self.relation_label_entry.insert(0, "Enter Relation Label")

        self.end_node_entry = tk.Entry(self.left_frame, width=50)
        self.end_node_entry.pack(pady=5)
        self.end_node_entry.insert(0, "Enter End Node Label")

        self.load_relation_button = tk.Button(self.left_frame, text="Load & Create Relation",
                                              command=self.load_relation, bg='light blue')
        self.load_relation_button.pack(pady=5)

        self.drop_database_button = tk.Button(self.left_frame, text="Drop Database", command=self.drop_database,
                                              bg='red')
        self.drop_database_button.pack(side='bottom', padx=100, pady=100)

        # Middle column - Query execution
        self.middle_frame = tk.Frame(root, bg='light grey')
        self.middle_frame.grid(row=0, column=1, padx=10, pady=10, sticky='n')

        self.query_label = tk.Label(self.middle_frame, text="Enter Query:", bg='light grey', fg='black')
        self.query_label.pack(pady=5)

        self.query_entry = tk.Entry(self.middle_frame, width=50)
        self.query_entry.pack(pady=5)

        self.query_button = tk.Button(self.middle_frame, text="Execute Query", command=self.execute_query,
                                      bg='light blue')
        self.query_button.pack(pady=5)

        self.result_label = tk.Label(self.middle_frame, text="Result:", bg='light grey', fg='black')
        self.result_label.pack(pady=5)

        self.result_text = scrolledtext.ScrolledText(self.middle_frame, width=70, height=20)
        self.result_text.pack(pady=5)

        self.print_button = tk.Button(self.middle_frame, text="Print Result", command=self.print_result,
                                      bg='light blue')
        self.print_button.pack(pady=5)

        # Right column - Messages
        self.right_frame = tk.Frame(root, bg='light grey')
        self.right_frame.grid(row=0, column=2, padx=10, pady=10, sticky='n')

        self.message_label = tk.Label(self.right_frame, text="Messages:", bg='light grey', fg='black')
        self.message_label.pack(pady=5)

        self.message_text = scrolledtext.ScrolledText(self.right_frame, width=30, height=20)
        self.message_text.pack(pady=5)

        # Close button
        self.close_button = tk.Button(root, text="Close", command=root.quit, bg='light blue')
        self.close_button.grid(row=1, column=2, padx=10, pady=10, sticky='se')

        # Deletions of nodes and relations
        self.label3 = tk.Label(self.right_frame, text="DELETIONS:", bg='light grey', fg='blue')
        self.label3.pack(pady=10)
        self.delete_node_label_entry = tk.Entry(self.right_frame, width=50)
        self.delete_node_label_entry.pack(pady=5)
        self.delete_node_label_entry.insert(0, "Enter Node Label to Delete")

        self.delete_node_button = tk.Button(self.right_frame, text="Delete Node", command=self.delete_node,
                                            bg='light blue')
        self.delete_node_button.pack(pady=5)

        self.delete_relationship_label_entry = tk.Entry(self.right_frame, width=50)
        self.delete_relationship_label_entry.pack(pady=5)
        self.delete_relationship_label_entry.insert(0, "Enter Relationship Label to Delete")

        self.delete_relationship_button = tk.Button(self.right_frame, text="Delete Relationship",
                                                    command=self.delete_relationship, bg='light blue')
        self.delete_relationship_button.pack(pady=5)

    def initialization(self):
        db = Neo4jDatabase(self.uri, self.user, self.password)
        with db.driver.session() as session:
            # Execute the first query to get distinct node labels
            query1 = "MATCH (n) RETURN DISTINCT labels(n) AS labels"
            node1 = session.run(query1)
            self.node_list = [label for record in node1 for label in record["labels"]]

            # Execute the second query to get distinct relationship types
            query2 = "MATCH (n)-[r]->(m) RETURN DISTINCT type(r) AS rel"
            rel1 = session.run(query2)
            self.rel_list = [record["rel"] for record in rel1]

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return

        data = load_data(file_path)
        label = self.node_label_entry.get()

        if not label:
            messagebox.showerror("Error", "Node label cannot be empty.")
            return

        if label in self.node_list:
            messagebox.showerror("Error", f"{label} Node already exists! Please change label name and retry.")
        else:
            db = Neo4jDatabase(self.uri, self.user, self.password)
            try:
                for row in data:
                    db.create_node(label, row)
                # we add constraints: ID_Uniqueness on the ID of each node
                db.create_schema(label)
                db.close()
                messagebox.showinfo("Success", f"{label} Nodes created successfully from {file_path}!")
                self.message_text.insert(tk.END, f"{label} Nodes created successfully\n")
                self.message_text.insert(tk.END, f"Constraint on {label} ID created successfully\n")
            except Exception as e:
                self.message_text.insert(tk.END, f"Error: {str(e)}\n")
            db.close()
            self.node_list.append(label)

    def load_relation(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return

        data = load_data(file_path)
        start_label = self.start_node_entry.get()
        relation_label = self.relation_label_entry.get()
        end_label = self.end_node_entry.get()

        if not (start_label and relation_label and end_label):
            messagebox.showerror("Error", "Start node, relationship, and end node labels cannot be empty.")
            return

        if start_label not in self.node_list:
            messagebox.showerror("Error", f"{start_label} node does not exist in the database, check for spelling errors")
            return
        elif end_label not in self.node_list:
            messagebox.showerror("Error", f"{end_label} node does not exist in the database, check for spelling errors")
            return
        else:
            db = Neo4jDatabase(self.uri, self.user, self.password)
            try:
                for row in data:
                    db.create_relationship(start_label, end_label, relation_label, row)
                db.close()
                messagebox.showinfo("Success", f"{relation_label} relationships created successfully from {file_path}!")
                self.message_text.insert(tk.END, f"{relation_label} Relationships created successfully\n")
            except Exception as e:
                self.message_text.insert(tk.END, f"Error: {str(e)}\n")
            db.close()
            self.rel_list.append(relation_label)

    def delete_node(self):
        label = self.delete_node_label_entry.get()
        if not label:
            messagebox.showerror("Error", "Node label cannot be empty.")
            return
        if label not in self.node_list:
            messagebox.showerror("Error", f"{label} Node does not exist! Check for spelling error and retry.")
            return

        db = Neo4jDatabase(self.uri, self.user, self.password)
        try:
            db.delete_node(label)
            db.close()
            messagebox.showinfo("Success", f"Nodes with label {label} and their relationships deleted successfully!")
            self.message_text.insert(tk.END, f"Nodes with label {label} and their relationships deleted successfully\n")
            self.node_list.remove(label)
        except Exception as e:
            self.message_text.insert(tk.END, f"Error: {str(e)}\n")
        db.close()

    def delete_relationship(self):
        label = self.delete_relationship_label_entry.get()
        if not label:
            messagebox.showerror("Error", "Relationship label cannot be empty.")
            return
        if label not in self.rel_list:
            messagebox.showerror("Error", f"{label} Node does not exist! Check for spelling error and retry.")
            return

        db = Neo4jDatabase(self.uri, self.user, self.password)
        try:
            db.delete_relationship(label)
            db.close()
            messagebox.showinfo("Success", f"Relationships with label {label} deleted successfully!")
            self.message_text.insert(tk.END, f"Relationships with label {label} deleted successfully\n")
            self.rel_list.remove(label)
        except Exception as e:
            self.message_text.insert(tk.END, f"Error: {str(e)}\n")
        db.close()

    def execute_query(self):
        query = self.query_entry.get()

        if not query:
            messagebox.showerror("Error", "Query cannot be empty.")
            return

        # Initialize the Neo4j database connection
        db = Neo4jDatabase(self.uri, self.user, self.password)

        try:
            with db.driver.session() as session:
                result = session.run(query)

                # Clear previous result from the result_text field
                self.result_text.delete(1.0, tk.END)

                # Fetching column names from the query result
                columns = result.keys()

                # Initialize column widths based on column names initially
                column_widths = [len(col) for col in columns]

                # Collecting all rows to determine the maximum width for each column
                rows = []
                for record in result:
                    row = [str(record.get(col)) for col in columns]
                    rows.append(row)
                    # Update column_widths to be the max of current width or new data's length
                    column_widths = [max(width, len(str_data)) for width, str_data in zip(column_widths, row)]

                # Prepare the format string for each row
                format_string = "  ".join([f"{{:<{width}}}" for width in column_widths])

                # Displaying the column names as the header in the result_text field
                header = format_string.format(*columns)
                self.result_text.insert(tk.END, header + "\n")
                self.result_text.insert(tk.END, "-" * len(header) + "\n")  # To separate the header from the data

                # Insert each row into the result_text field
                for row in rows:
                    formatted_row = format_string.format(*row)
                    self.result_text.insert(tk.END, formatted_row + "\n")

        except Exception as e:
            self.message_text.insert(tk.END, f"Error executing query: {str(e)}\n")
        finally:
            db.close()

    def print_result(self):
        result = self.result_text.get(1.0, tk.END)
        if not result.strip():
            messagebox.showerror("Error", "Result is empty.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if file_path:
            c = canvas.Canvas(file_path, pagesize=letter)
            width, height = letter
            c.drawString(100, height - 100, "Query Result:")
            lines = result.split('\n')
            y = height - 120
            for line in lines:
                c.drawString(100, y, line)
                y -= 15
            c.save()
            messagebox.showinfo("Success", f"Result saved to {file_path}")

    def drop_database(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to drop the entire database?"):
            db = Neo4jDatabase(self.uri, self.user, self.password)
            try:
                with db.driver.session() as session:
                    session.run("MATCH (n) DETACH DELETE n")
                db.close()
                messagebox.showinfo("Success", "Database dropped successfully!")
                self.message_text.insert(tk.END, "Database dropped successfully\n")
            except Exception as e:
                self.message_text.insert(tk.END, f"Error: {str(e)}\n")
            db.close()


# User Interface
class UserGUI:
    def __init__(self, root, username, password):
        self.root = root
        self.root.title("Neo4j Database User Manager")
        self.root.configure(bg='light grey')

        self.uri = "bolt://localhost:7687"
        self.user = username
        self.password = password

        # Middle column - Query execution
        self.middle_frame = tk.Frame(root, bg='light grey')
        self.middle_frame.grid(row=0, column=1, padx=10, pady=10, sticky='n')

        self.query_label = tk.Label(self.middle_frame, text="Enter Query:", bg='light grey', fg='black')
        self.query_label.pack(pady=5)

        self.query_entry = tk.Entry(self.middle_frame, width=50)
        self.query_entry.pack(pady=5)

        self.query_button = tk.Button(self.middle_frame, text="Execute Query", command=self.execute_query,
                                      bg='light blue')
        self.query_button.pack(pady=5)

        self.result_label = tk.Label(self.middle_frame, text="Result:", bg='light grey', fg='black')
        self.result_label.pack(pady=5)

        self.result_text = scrolledtext.ScrolledText(self.middle_frame, width=70, height=20)
        self.result_text.pack(pady=5)

        self.print_button = tk.Button(self.middle_frame, text="Print Result", command=self.print_result,
                                      bg='light blue')
        self.print_button.pack(pady=5)

        # Right column - Messages
        self.right_frame = tk.Frame(root, bg='light grey')
        self.right_frame.grid(row=0, column=2, padx=10, pady=10, sticky='n')

        self.message_label = tk.Label(self.right_frame, text="Messages:", bg='light grey', fg='black')
        self.message_label.pack(pady=5)

        self.message_text = scrolledtext.ScrolledText(self.right_frame, width=30, height=20)
        self.message_text.pack(pady=5)

        # Close button
        self.close_button = tk.Button(root, text="Close", command=root.quit, bg='light blue')
        self.close_button.grid(row=1, column=2, padx=10, pady=10, sticky='se')

    def execute_query(self):
        query = self.query_entry.get()
        if not query:
            messagebox.showerror("Error", "Query cannot be empty.")
            return

        db = Neo4jDatabase(self.uri, self.user, self.password)
        try:
            with db.driver.session() as session:
                result = session.run(query)
                self.result_text.delete(1.0, tk.END)
                for record in result:
                    self.result_text.insert(tk.END, str(record) + '\n')
            db.close()
        except Exception as e:
            self.message_text.insert(tk.END, f"Error: {str(e)}\n")
        db.close()

    def print_result(self):
        result = self.result_text.get(1.0, tk.END)
        if not result.strip():
            messagebox.showerror("Error", "Result is empty.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if file_path:
            c = canvas.Canvas(file_path, pagesize=letter)
            width, height = letter
            c.drawString(100, height - 100, "Query Result:")
            lines = result.split('\n')
            y = height - 120
            for line in lines:
                c.drawString(100, y, line)
                y -= 15
            c.save()
            messagebox.showinfo("Success", f"Result saved to {file_path}")


if __name__ == "__main__":
    root = tk.Tk()
    login_app = LoginPage(root)
    root.mainloop()
