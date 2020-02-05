import os
import tkinter as tk                
from tkinter import font  as tkfont
from tkinter import messagebox 
from PIL import Image
from PIL import ImageTk
from backend import Database,BackEndApp
from urllib.parse import urlparse
from cmd import commands

backend=BackEndApp()
database = backend.database

user_name="admin"
password="admin"
dns_server_running=False

WIDTH, HEIGTH = 500, 500


def start_procces():
    backend.start()
    dns_server_running=True 
    commands.flush_dns()
    print(dns_server_running)

def stop_procces():
    backend.stop()
    dns_server_running=False
    commands.flush_dns()
    print(dns_server_running)


def exit_program():
    if messagebox.askyesno("Exit", "Do you want to quit the application?"):
        commands.change_dns_to_dhcp()
        exit(1)

def is_url_valid(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

class SampleApp(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title_font = tkfont.Font(family='Helvetica', size=18, weight="bold", slant="italic")
        
        self.title("CAMERA-WEB-BLOCKER")
        self.resizable(width=False, height=False)
        self.geometry('{}x{}'.format(WIDTH, HEIGTH))
        

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (StartPage, MainPage, BlacklistPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame

            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("StartPage")
        self.protocol("WM_DELETE_WINDOW", exit_program)

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
    

#-------------------------------------LOGIN PAGE-------------------------------------------#
class StartPage(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.user_name="admin"
        self.password="admin"
        print(os.path.join(os.getcwd(),"images","books.png"))
        img = Image.open(os.path.join(os.getcwd(),"images","books.png"))
        img = img.resize((WIDTH,HEIGTH), Image.ANTIALIAS)
        self.background_image= ImageTk.PhotoImage(img)
        self.background_label = tk.Label(self, image=self.background_image)
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.background_label.img = self.background_image

        self.name_text = tk.StringVar()
        self.password_text = tk.StringVar()

        self.enter_b_frame = tk.Frame(self, borderwidth=1,background="white")
        self.enter_b_frame.place(relx=0.5 ,rely=0.47,anchor='n')

        self.name_l_frame = tk.Frame(self, borderwidth=1,background="white")
        self.name_l_frame.place(relx=0.25 ,rely=0.3,anchor='n')
        self.name_l = tk.Label(self.name_l_frame, text='user name',font=("Helvetica", 16),fg="white",bg="black").pack()

        self.name_e_frame = tk.Frame(self, borderwidth=1,background="black")
        self.name_e_frame.place(relx=0.65 ,rely=0.3,anchor='n')
        self.name_e=tk.Entry(self.name_e_frame,textvariable=self.name_text,font=("Helvetica", 16))
        self.name_e.pack()
        

        self.password_l_frame = tk.Frame(self, borderwidth=1,background="white")
        self.password_l_frame.place(relx=0.249 ,rely=0.37,anchor='n')
        self.password_l = tk.Label(self.password_l_frame, text='password',font=("Helvetica", 16),padx=5,fg="white",bg="black").pack()

        self.password_e_frame = tk.Frame(self, borderwidth=1,background="black")
        self.password_e_frame.place(relx=0.65 ,rely=0.37,anchor='n')
        self.password_e=tk.Entry(self.password_e_frame,textvariable=self.password_text,font=("Helvetica", 16))
        self.password_e.pack()
       
        self.enter_b_frame = tk.Frame(self, borderwidth=1,background="white")
        self.enter_b_frame.place(relx=0.5 ,rely=0.47,anchor='n')
        self.enter_b=tk.Button(self.enter_b_frame, text='Enter',font=("calibri", 12),fg="white",bg="black", command=lambda:self.cheak_user_and_paswword(self.name_e,self.password_e)).pack()
    
    def cheak_user_and_paswword(self,en,ep):
        if self.name_text.get()==self.user_name and self.password_text.get()==self.password:
            self.controller.show_frame(MainPage.__name__)
        else:
            messagebox.showinfo("Wrong Password","you have enterd a wrong password or user name. Please try again")
            ep.delete(0,'end')
            en.delete(0,'end')


#-------------------MAIN PAGE-----------------------------------------------------------------#

class MainPage(tk.Frame):

    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent)
        self.controller = controller

        img = Image.open(os.path.join(os.getcwd(),"images","books.png"))
        img = img.resize((WIDTH,HEIGTH), Image.ANTIALIAS)
        self.background_image= ImageTk.PhotoImage(img)
        self.background_label = tk.Label(self, image=self.background_image)
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.background_label.img = self.background_image

        self.start_b_frame = tk.Frame(self, borderwidth=1,background="black")
        self.start_b_frame.place(relx=0.28, rely=0.3)
        self.start_b=tk.Button(self.start_b_frame, text='start',font=("calibri", 30),bg="green", command=lambda:start_procces()).pack()

        self.stop_b_frame = tk.Frame(self, borderwidth=1,background="black")
        self.stop_b_frame.place(relx=0.54, rely=0.3)
        self.stop_b=tk.Button(self.stop_b_frame, text='stop',font=("calibri", 30),bg="red", command=lambda:stop_procces()).pack()

        self.blacklist_b_frame = tk.Frame(self, borderwidth=1,background="black")
        self.blacklist_b_frame.place(relx=0.28, rely=0.5)
        self.blacklist_b=tk.Button(self.blacklist_b_frame, text='blacklist setings',font=("calibri", 16),padx=38,fg="white",bg="black", command=lambda:controller.show_frame(BlacklistPage.__name__)).pack()

        self.back_b_frame = tk.Frame(self, borderwidth=1)
        self.back_b_frame.place(relx=0.05, rely=0.87)
        self.back_b=tk.Button(self.back_b_frame, text='exit',font=("calibri", 16),fg="white",bg="black", command=lambda:exit_program()).pack()


#--------------------------BLACKLIST SETTING PAGE-------------------------------------------------#
class BlacklistPage(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        img = Image.open(os.path.join(os.getcwd(),"images","books.png"))
        img = img.resize((WIDTH,HEIGTH), Image.ANTIALIAS)
        self.background_image= ImageTk.PhotoImage(img)
        self.background_label = tk.Label(self, image=self.background_image)
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.background_label.img = self.background_image

        self.url_text = tk.StringVar()


        self.url_e_frame = tk.Frame(self, borderwidth=1,background="black")
        self.url_e_frame.place(relx=0.5 ,rely=0.05,anchor='n')
        self.url_e=tk.Entry(self.url_e_frame,textvariable=self.url_text,font=("Helvetica", 12),width=50)
        self.url_e.pack()

        self.add_b_frame = tk.Frame(self, borderwidth=1,background="white")
        self.add_b_frame.place(relx=0.185 ,rely=0.11,anchor='n')
        self.add_b=tk.Button(self.add_b_frame, text='Add',font=("calibri", 12),fg="white",bg="black",padx=50, command=lambda:self.add_command(self.url_e)).pack()

        self.remove_b_frame = tk.Frame(self, borderwidth=1,background="white")
        self.remove_b_frame.place(relx=0.495 ,rely=0.11,anchor='n')
        self.remove_b=tk.Button(self.remove_b_frame, text='Remove',font=("calibri", 12),fg="white",bg="black",padx=39, command=lambda:self.remove_command(self.url_e)).pack()

        self.remove_b_frame = tk.Frame(self, borderwidth=1,background="white")
        self.remove_b_frame.place(relx=0.808 ,rely=0.11,anchor='n')
        self.remove_b=tk.Button(self.remove_b_frame, text='Clear All',font=("calibri", 12),fg="white",bg="black",padx=38, command=lambda:self.remove_all_command()).pack()

        self.list_frame = tk.Frame(self, borderwidth=1,background="black")
        self.list_frame.place(relx=0.5 ,rely=0.2,anchor='n')
       
        self.lb = tk.Listbox(self.list_frame, width=72, height=20)
        self.scrollbar = tk.Scrollbar(self.list_frame, orient="vertical",command=self.lb.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.lb.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.lb.yview)
        self.view_command(self.lb)
        self.lb.pack()
        self.lb.bind('<<ListboxSelect>>',self.get_selcted_row)

        self.back_b_frame = tk.Frame(self, borderwidth=1)
        self.back_b_frame.place(relx=0.05, rely=0.87)
        self.back_b=tk.Button(self.back_b_frame, text='back',font=("calibri", 16),fg="white",bg="black", command=lambda:controller.show_frame(MainPage.__name__)).pack()       



    def add_command(self,e):
        url=self.url_text.get()
        e.delete(0,'end')
        if is_url_valid(url):
            database.insert(url)
            backend.update_blacklist()
        else:
            messagebox.showinfo("INVALID URL","You have entered invalid URL, please try again.")
        self.view_command(self.lb)

        

    def get_selcted_row(self,event):
        index = self.lb.curselection()[0]
        url = self.lb.get(index)
        self.url_e.delete(0,'end')
        self.url_e.insert('end',url)
        
    def remove_command(self,e):
        database.delete(self.url_text.get())
        backend.update_blacklist()
        e.delete(0,'end')
        self.view_command(self.lb)
        

    def remove_all_command(self):
        if messagebox.askyesno("erase", "Are you sure you want to delete all the URLs?"):
            database.clear_tables()
            backend.update_blacklist()
        self.view_command(self.lb)
        

    def view_command(self,l):
        l.delete(0,'end')
        for row in database.view():
            l.insert('end',row)



if __name__ == "__main__":
    app = SampleApp()
    app.mainloop()