import tkinter as tk
from tkinter import messagebox, filedialog

def create_messagebox(parent, message_type, title, message, **options):
    """
    Creates a messagebox that stays on top of the parent window.
    
    Args:
        parent: The parent window (should be the video player window)
        message_type: Type of message ('info', 'warning', 'error', 'yesno')
        title: Title of the message box
        message: Message to display
        **options: Additional options to pass to the messagebox
    
    Returns:
        The result from the messagebox (True/False for yesno, None for others)
    """
    # Create a temporary Toplevel window to act as the parent for the messagebox
    temp_window = tk.Toplevel(parent)
    temp_window.withdraw()
    temp_window.transient(parent)
    temp_window.attributes('-topmost', True)
    
    try:
        if message_type == 'info':
            result = messagebox.showinfo(title, message, parent=temp_window, **options)
        elif message_type == 'warning':
            result = messagebox.showwarning(title, message, parent=temp_window, **options)
        elif message_type == 'error':
            result = messagebox.showerror(title, message, parent=temp_window, **options)
        elif message_type == 'yesno':
            result = messagebox.askyesno(title, message, parent=temp_window, **options)
        else:
            raise ValueError(f"Unsupported message type: {message_type}")
    finally:
        temp_window.destroy()
    
    return result
def askopenfilename(parent, **options):
    """Open a file dialog that is tied to the parent window."""
    temp_window = tk.Toplevel(parent)
    temp_window.withdraw()
    temp_window.transient(parent)
    temp_window.attributes('-topmost', True)
    
    try:
        file = filedialog.askopenfilename(parent=temp_window, **options)
    finally:
        temp_window.destroy()
    return file

def asksaveasfilename(parent, **options):
    """Save file dialog tied to parent."""
    temp_window = tk.Toplevel(parent)
    temp_window.withdraw()
    temp_window.transient(parent)
    temp_window.attributes('-topmost', True)
    
    try:
        file = filedialog.asksaveasfilename(parent=temp_window, **options)
    finally:
        temp_window.destroy()
    return file

def askdirectory(parent, **options):
    """Open directory dialog tied to parent."""
    temp_window = tk.Toplevel(parent)
    temp_window.withdraw()
    temp_window.transient(parent)
    temp_window.attributes('-topmost', True)
    
    try:
        directory = filedialog.askdirectory(parent=temp_window, **options)
    finally:
        temp_window.destroy()
    return directory

def showinfo(parent, title, message, **options):
    """Show an info message box."""
    return create_messagebox(parent, 'info', title, message, **options)

def showwarning(parent, title, message, **options):
    """Show a warning message box."""
    return create_messagebox(parent, 'warning', title, message, **options)

def showerror(parent, title, message, **options):
    """Show an error message box."""
    return create_messagebox(parent, 'error', title, message, **options)

def askyesno(parent, title, message, **options):
    """Show a yes/no question message box."""
    return create_messagebox(parent, 'yesno', title, message, **options) 