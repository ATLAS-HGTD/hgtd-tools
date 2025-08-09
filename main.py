import customtkinter
from PIL import Image
import requests
import threading
import time
import tkinter

import api
import data
import util

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

wrapped_text = util.CustomTextWrapper(width=90)

class ToplevelWindow(customtkinter.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("HGTD Tools - Help")
        self.geometry("1000x300")

        self.textbox = customtkinter.CTkTextbox(master=self, width=400, wrap='word')
        self.textbox.pack(fill="both", expand=True, padx=20, pady=20)
        self.textbox.insert("0.0", "Each Support Unit is oriented in such a way that when looking at its face, the module connectors are at the top (or on the right), and module capacitors are on the bottom (or on the left).\nUser actions (loading sites / assembly at CERN): First step at a loading site: fill the Detector Unit with modules, click on the canvas to select the correct position and use the button below. Once finished, move to the assembly step at CERN and enter the position manually when connecting a Detector Unit with the Detector (VxLxQx). Note: A back Detector Unit can only be on layer 1 or 2, a front Detector Unit can only be on layer 0 or 3.\nToo long dropdown selections are split into chunks, you can select which chunk shall be shown with the arrow buttons. This is to ensure compatibility with more operating systems.\n\nHint: manufacturers for modules should be interpreted as assembly sites. This field is taken live from all manufacturers available in the database and hence does not necessarily agree with the six defined assembly sites.\n\nHint 2: Blue option menus contain static choices (=hardcoded), while grey comboboxes are retrieved dynamically (=from the DB).\n\nHint 3: if you do not pre-select children by trivial attributes like manufacturer or type, the option to choose only not-yet-connected children will be slow, as is has to check from the full set of children. Pre-select with the other options to speed this process up.")
        self.textbox.configure(state='disabled')


class AuthenticateWindow(customtkinter.CTkToplevel):
    def __init__(self, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("HGTD Tools - Authenticate new user")
        self.geometry("900x300")

        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure((0,1), weight=1)

        self.callback = callback

        self.entries_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.entries_frame.grid(row=0, column=0, rowspan=3, columnspan=3, sticky="nsew")

        self.auth_info_label = customtkinter.CTkLabel(self.entries_frame, text="Type in your user data to authenticate as a new user of HGTD-Tools.")
        self.auth_info_label.grid(row=0, column=0, padx=10, pady=10, columnspan=3)

        self.username_variable = customtkinter.StringVar(value="")
        self.username_entry = customtkinter.CTkEntry(self.entries_frame, textvariable=self.username_variable, state='normal')
        self.username_entry.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.username_label = customtkinter.CTkLabel(self.entries_frame, text="Username")
        self.username_label.grid(row=2, column=0, padx=10, pady=10)

        self.password_variable = customtkinter.StringVar(value="")
        self.password_entry = customtkinter.CTkEntry(self.entries_frame, textvariable=self.password_variable, state='normal', show="*")
        self.password_entry.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.password_label = customtkinter.CTkLabel(self.entries_frame, text="Password")
        self.password_label.grid(row=2, column=1, padx=10, pady=10)

        self.totp_variable = customtkinter.StringVar(value="")
        self.totp_entry = customtkinter.CTkEntry(self.entries_frame, textvariable=self.totp_variable, state='normal')
        self.totp_entry.grid(row=1, column=2, padx=10, pady=10, sticky="nsew")
        self.totp_label = customtkinter.CTkLabel(self.entries_frame, text="2FA 6-digit code, if configured (leave empty if you are not using 2FA yet)")
        self.totp_label.grid(row=2, column=2, padx=10, pady=10)

        self.auth_button = customtkinter.CTkButton(self.entries_frame, text="Authenticate me!", command=self.auth)
        self.auth_button.grid(row=3, column=1, padx=10, pady=10)

        self.auth_user, self.last_responseText = None, None

    def auth(self):
        try:
            self.auth_user, self.last_responseText = api.get_user(self.username_variable.get(), self.password_variable.get(), self.totp_variable.get())
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            self.last_responseText = str(e)
        except ValueError as e:
            self.last_responseText = str(e)

        self.callback(self.auth_user, self.last_responseText) # send back to the other class.
        self.destroy()


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # configure window
        #self.tk.call('tk', 'scaling', 1.6)
        self.title("HGTD Tools")
        #self.update_idletasks()

        #screen_width = self.winfo_screenwidth()
        #screen_height = self.winfo_screenheight()
        #print("screen width = ", screen_width)
        #print("screen height = ", screen_height)
        
        #ratio_width = screen_width/3840
        #ratio_height = screen_height/2160
        #print("ratio width = ", ratio_width)
        #print("ratio height = ", ratio_height)
        
        #width_I_want = 3456
        #height_I_want = 2234
        
        #width = int(width_I_want*ratio_width)
        #height = int(height_I_want*ratio_height)
        #print("width = ", width)
        #print("height = ", height)
        
        #x = int((screen_width - width) /2/ratio_width)
        #y = int((screen_height - height) /2/ratio_height)
        #print("x = ", x)
        #print("y = ", y)
        
        #self.geometry(f"{width}x{height}+{x}+{y}")
        #self.attributes("-zoomed", "True")
        #self.after(0, lambda:self.state('zoomed'))
        #width, height = self.winfo_screenwidth(), self.winfo_screenheight()
        #width, height = screen_width, screen_height
        #print(width)
        #print(height)
        #dpi = self.winfo_fpixels('1i')
        #print(dpi)
        #real_width = int(width * dpi / 96)
        #real_height = int(height * dpi / 96)
        
        #print('real width should be', real_width)
        #print('real height should be', real_height)
        #self.geometry(f"{width}x{height}")
        self.geometry(f"{1500}x{1000}")
        icon = tkinter.PhotoImage(file="windowIcon.png")
        self.wm_iconbitmap()
        self.iconphoto(True,icon)

        self.n_items_to_show_in_cbx = 16
        # configure grid layout
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure((0,1), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame_left = customtkinter.CTkFrame(self, corner_radius=0)
        self.sidebar_frame_left.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame_left.grid_columnconfigure((0,1), weight=1)
        self.sidebar_frame_left.grid_rowconfigure(5, weight=1)

        # fill sidebar
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="HGTD Tools", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10), columnspan=2)
        self.credits_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="v1.5.0dev - August 2025\nAnnika Stein (JGU Mainz)")
        self.credits_label.grid(row=1, column=0, padx=20, pady=10, columnspan=2)

        self.progress_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="API Request Status")
        self.progress_label.grid(row=2, column=0, padx=20, pady=10, columnspan=2)
        self.progressbar = customtkinter.CTkProgressBar(self.sidebar_frame_left, orientation="horizontal", progress_color="#007711")
        self.progressbar.grid(row=3, column=0, padx=20, pady=10, columnspan=2)
        self.progressbar.set(1)

        # buttons to select use case of the tool
        self.operation_mode_frame = customtkinter.CTkFrame(self.sidebar_frame_left)
        self.operation_mode_frame.grid(row=4, column=0, padx=5, pady=(20,5), sticky="nsew", columnspan=2)
        self.operation_mode_frame.grid_columnconfigure((0,1), weight=1)
        self.operation_mode = 'Module Assembly'

        self.operation_mode_label = customtkinter.CTkLabel(self.operation_mode_frame, text="Operation Mode", font=customtkinter.CTkFont(size=16, weight="bold"))
        self.operation_mode_label.grid(row=0, column=0, padx=20, pady=10, columnspan=2)

        self.operation_mode_MA_button = customtkinter.CTkButton(self.operation_mode_frame, text="Module Assembly",
            command=lambda: self.button_mode_event_click('Module Assembly'), fg_color="#339941", hover_color="#228831")
        self.operation_mode_MA_button.grid(row=1, column=0, padx=5, pady=5, sticky="nsew", columnspan=2)

        self.operation_mode_ML_button = customtkinter.CTkButton(self.operation_mode_frame, text="Module Loading",
            command=lambda: self.button_mode_event_click('Module Loading'), fg_color="#555555", hover_color="#444444")
        self.operation_mode_ML_button.grid(row=2, column=0, padx=5, pady=5, sticky="nsew", columnspan=2)

        self.operation_mode_DA_DU_button = customtkinter.CTkButton(self.operation_mode_frame, text="Detector Assembly (CERN): DU",
            command=lambda: self.button_mode_event_click('Detector Assembly (CERN): DU'), fg_color="#555555", hover_color="#444444")
        self.operation_mode_DA_DU_button.grid(row=3, column=0, padx=5, pady=5, sticky="nsew", columnspan=2)

        self.operation_mode_DA_PEB_button = customtkinter.CTkButton(self.operation_mode_frame, text="Detector Assembly (CERN): PEB",
            command=lambda: self.button_mode_event_click('Detector Assembly (CERN): PEB'), fg_color="#555555", hover_color="#444444")
        self.operation_mode_DA_PEB_button.grid(row=4, column=0, padx=5, pady=5, sticky="nsew", columnspan=2)

        self.operation_mode_DA_FT_button = customtkinter.CTkButton(self.operation_mode_frame, text="Detector Assembly (CERN): FT",
            command=lambda: self.button_mode_event_click('Detector Assembly (CERN): FT'), fg_color="#555555", hover_color="#444444")
        self.operation_mode_DA_FT_button.grid(row=5, column=0, padx=5, pady=5, sticky="nsew", columnspan=2)

        # buttons to go to external useful pages
        self.useful_links_frame = customtkinter.CTkFrame(self.sidebar_frame_left)
        self.useful_links_frame.grid(row=5, column=0, padx=5, pady=20, sticky="nsew", columnspan=2)
        self.useful_links_frame.grid_columnconfigure((0,1), weight=1)

        self.useful_links_label = customtkinter.CTkLabel(self.useful_links_frame, text="Useful Links", font=customtkinter.CTkFont(size=16, weight="bold"))
        self.useful_links_label.grid(row=0, column=0, padx=20, pady=10, columnspan=2)

        self.useful_links_Frontend_button = customtkinter.CTkButton(self.useful_links_frame, text="DB Frontend",
            command=lambda: util.open_webbrowser_with_url(api.frontendUrlPrefix, noExtraPrefix = True), fg_color="#555555", hover_color="#444444")
        self.useful_links_Frontend_button.grid(row=1, column=0, padx=5, pady=5, sticky="nsew", columnspan=2)

        self.useful_links_Mockup_button = customtkinter.CTkButton(self.useful_links_frame, text="SN Decoder/Encoder",
            command=lambda: util.open_webbrowser_with_url('https://annika-stein.web.cern.ch/module_mockup/serialnumber.html', noExtraPrefix = True), fg_color="#555555", hover_color="#444444")
        self.useful_links_Mockup_button.grid(row=2, column=0, padx=5, pady=5, sticky="nsew", columnspan=2)


        self.user_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="User:", anchor="e")
        self.user_label.grid(row=7, column=0, padx=5, pady=10)
        self.user_optionmenu = customtkinter.CTkOptionMenu(self.sidebar_frame_left, values=['None', 'new...'],
                                                                       command=self.change_user_event, width=60)
        self.user_optionmenu.grid(row=7, column=1, padx=5, pady=10)
        self.user_optionmenu.set("None")
        self.user_window = None


        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="Theme:", anchor="e")
        self.appearance_mode_label.grid(row=8, column=0, padx=5, pady=10)
        self.appearance_mode_optionmenu = customtkinter.CTkOptionMenu(self.sidebar_frame_left, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event, width=60)
        self.appearance_mode_optionmenu.grid(row=8, column=1, padx=5, pady=10)
        self.appearance_mode_optionmenu.set("System")

        self.help_image = customtkinter.CTkImage(Image.open("circle-question.png"), size=(20,20))
        self.btnHelp = customtkinter.CTkButton(self.sidebar_frame_left, image=self.help_image, text="Help", compound='left', fg_color="#339941", hover_color="#228831", command=self.help, width=60)
        self.btnHelp.grid(row=9, column=0, pady=10, padx=5, columnspan=2)
        self.help_window = None

        self.exit_image = customtkinter.CTkImage(Image.open("right-from-bracket-solid.png"), size=(20,20))
        self.btnLogout = customtkinter.CTkButton(self.sidebar_frame_left, image=self.exit_image, text="Close", compound='left', fg_color="#cf352e", hover_color="#B02B25", command=self.exit, width=60)
        self.btnLogout.grid(row=10, column=0, pady=20, padx=5, columnspan=2)

        # work in main widget (column w.r.t. root >= 1)

        # create main frame with widgets
        self.main_frame = customtkinter.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, rowspan=1, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure((0,1), weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # ********************************************
        #
        # === Parent/Child selection for ML/DU/PEB ===
        #
        # ********************************************

        # left sub widget: form
        self.combobox_frame = customtkinter.CTkFrame(self.main_frame, width = 600)
        self.combobox_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew", rowspan=2)
        self.combobox_frame.grid_columnconfigure((0,1), weight=1)
        self.combobox_frame.grid_remove() # The initial frame shown will now be Module Assembly

        # parent
        self.parent_frame = customtkinter.CTkFrame(self.combobox_frame)
        self.parent_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew", columnspan=2)
        self.parent_frame.grid_columnconfigure((0,1), weight=1)

        self.combobox_parent_T_label = customtkinter.CTkLabel(self.parent_frame, text="Parent Part Type: Detector Unit")
        self.combobox_parent_T_label.grid(row=0, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew")


        self.combobox_par_type_label = customtkinter.CTkLabel(self.parent_frame, text="DU type")
        self.combobox_par_type_label.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="nsew")

        self.combobox_par_type_paginationFrame = customtkinter.CTkFrame(self.parent_frame)
        self.combobox_par_type_paginationFrame.grid(row=1, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.combobox_par_type_paginationFrame_label = customtkinter.CTkLabel(self.combobox_par_type_paginationFrame, text="0/0")
        self.combobox_par_type_paginationFrame_label.grid(row=0, column=0, padx=(10,5), pady=5, sticky="nsew")
        self.combobox_par_type_paginationButtonLeft = customtkinter.CTkButton(self.combobox_par_type_paginationFrame,
                                                                           text="<", width=30,
                                                   command=self.button_combobox_par_type_paginationButtonLeft_click)
        self.combobox_par_type_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_par_type = customtkinter.CTkComboBox(self.combobox_par_type_paginationFrame,
                                                    values=["All DU types"],
                                                    command=self.combobox_par_type_event_select,
                                                    state="readonly")
        self.combobox_par_type.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_par_type.set("- Select -")
        self.combobox_par_type_paginationButtonRight = customtkinter.CTkButton(self.combobox_par_type_paginationFrame,
                                                                           text=">", width=30,
                                                   command=self.button_combobox_par_type_paginationButtonRight_click)
        self.combobox_par_type_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)


        self.combobox_parent_label = customtkinter.CTkLabel(self.parent_frame, text="Parent Part SN")
        self.combobox_parent_label.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="nsew")

        self.combobox_parent_paginationFrame = customtkinter.CTkFrame(self.parent_frame)
        self.combobox_parent_paginationFrame.grid(row=2, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.combobox_parent_paginationFrame_label = customtkinter.CTkLabel(self.combobox_parent_paginationFrame, text="0/0")
        self.combobox_parent_paginationFrame_label.grid(row=0, column=0, padx=(10,5), pady=5, sticky="nsew")
        self.combobox_parent_paginationButtonLeft = customtkinter.CTkButton(self.combobox_parent_paginationFrame,
                                                                           text="<", width=30,
                                                   command=self.button_combobox_parent_paginationButtonLeft_click)
        self.combobox_parent_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_parent = customtkinter.CTkComboBox(self.combobox_parent_paginationFrame,
                                                    values=["Detector Unit", "Detector"],
                                                    command=self.combobox_p_c_event_select,
                                                    state="readonly",width=200)
        self.combobox_parent.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_parent.set("- Select -")
        self.combobox_parent_paginationButtonRight = customtkinter.CTkButton(self.combobox_parent_paginationFrame,
                                                                           text=">", width=30,
                                                   command=self.button_combobox_parent_paginationButtonRight_click)
        self.combobox_parent_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)


        self.inspect_parent_button = customtkinter.CTkButton(self.parent_frame, text="INSPECT PARENT",
                                                   command=self.button_inspect_parent_event_click)
        self.inspect_parent_button.grid(row=3, column=1, padx=20, pady=(10, 10))

        # child
        self.child_frame = customtkinter.CTkFrame(self.combobox_frame)
        self.child_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew", columnspan=2)
        self.child_frame.grid_columnconfigure((0,1), weight=1)

        self.combobox_child_T_label = customtkinter.CTkLabel(self.child_frame, text="Child Part Type: Module")
        self.combobox_child_T_label.grid(row=0, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew")


        self.child_conn_optionmenu = customtkinter.CTkOptionMenu(self.child_frame, values=["Not yet connected children", "All children"],
                                                                       command=self.change_child_conn_event, width=250)
        self.child_conn_optionmenu.grid(row=1, column=0, padx=5, pady=10)
        self.child_conn_optionmenu.set("All children")
        self.combobox_child_manu = customtkinter.CTkComboBox(self.child_frame, values=["All manufacturers"],
                                                                       command=self.combobox_child_manu_event, width=250)
        self.combobox_child_manu.grid(row=1, column=1, padx=5, pady=10)
        self.combobox_child_manu.set("All manufacturers") # ToDo: change values depending on mode


        self.combobox_chi_type_paginationFrame = customtkinter.CTkFrame(self.child_frame)
        self.combobox_chi_type_paginationFrame.grid(row=1, column=1, padx=20, pady=(10, 10), sticky="nsew")

        self.combobox_chi_type_paginationFrame_label = customtkinter.CTkLabel(self.combobox_chi_type_paginationFrame, text="0/0")
        self.combobox_chi_type_paginationFrame_label.grid(row=0, column=0, padx=(10,5), pady=5, sticky="nsew")
        self.combobox_chi_type_paginationButtonLeft = customtkinter.CTkButton(self.combobox_chi_type_paginationFrame,
                                                                           text="<", width=30,
                                                   command=self.button_combobox_chi_type_paginationButtonLeft_click)
        self.combobox_chi_type_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_chi_type = customtkinter.CTkComboBox(self.combobox_chi_type_paginationFrame,
                                                    values=["All DU types"],
                                                    command=self.combobox_chi_type_event_select,
                                                    state="readonly")
        self.combobox_chi_type.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_chi_type.set("- Select -")
        self.combobox_chi_type_paginationButtonRight = customtkinter.CTkButton(self.combobox_chi_type_paginationFrame,
                                                                           text=">", width=30,
                                                   command=self.button_combobox_chi_type_paginationButtonRight_click)
        self.combobox_chi_type_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)
        self.combobox_chi_type_paginationFrame.grid_remove()



        self.combobox_child_label = customtkinter.CTkLabel(self.child_frame, text="Child Part SN")
        self.combobox_child_label.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="nsew")

        self.combobox_child_paginationFrame = customtkinter.CTkFrame(self.child_frame)
        self.combobox_child_paginationFrame.grid(row=2, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.combobox_child_paginationFrame_label = customtkinter.CTkLabel(self.combobox_child_paginationFrame, text="0/0")
        self.combobox_child_paginationFrame_label.grid(row=0, column=0, padx=(10,5), pady=5, sticky="nsew")
        self.combobox_child_paginationButtonLeft = customtkinter.CTkButton(self.combobox_child_paginationFrame,
                                                                           text="<", width=30,
                                                   command=self.button_combobox_child_paginationButtonLeft_click)
        self.combobox_child_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_child = customtkinter.CTkComboBox(self.combobox_child_paginationFrame,
                                                    values=["Module", "Detector Unit"],
                                                    command=self.combobox_p_c_event_select,
                                                    state="readonly",width=200)
        self.combobox_child.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_child.set("- Select -")
        self.combobox_child_paginationButtonRight = customtkinter.CTkButton(self.combobox_child_paginationFrame,
                                                                           text=">", width=30,
                                                   command=self.button_combobox_child_paginationButtonRight_click)
        self.combobox_child_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)

        self.inspect_child_button = customtkinter.CTkButton(self.child_frame, text="INSPECT CHILD",
            command=self.button_inspect_child_event_click)
        self.inspect_child_button.grid(row=3, column=1, padx=20, pady=(10, 10))

        # position / click
        self.position_frame = customtkinter.CTkFrame(self.combobox_frame)
        self.position_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew", columnspan=2)
        self.position_frame.grid_columnconfigure((0,1), weight=1)

        self.position_label = customtkinter.CTkLabel(self.position_frame, text="Position (derived from canvas interaction)")
        self.position_label.grid(row=6, column=0, padx=20, pady=(20, 10), sticky="nsew")

        self.position_variable = customtkinter.StringVar(value="- automatic -")
        self.position_entry = customtkinter.CTkEntry(self.position_frame, textvariable=self.position_variable, state='disabled')
        self.position_entry.grid(row=6, column=1, padx=20, pady=(20, 10), sticky="nsew")

        self.add_button = customtkinter.CTkButton(self.position_frame, text="ADD PARTS TREE",
            command=self.button_add_event_click)
        self.add_button.grid(row=7, column=1, padx=20, pady=(20, 10))

        self.clicked_position_frame = customtkinter.CTkFrame(self.position_frame)
        self.clicked_position_frame.grid(row=9, column=0, padx=5, pady=5, sticky="nsew", columnspan=2)
        self.clicked_position_frame.grid_columnconfigure((0,1), weight=1)

        self.inspect_clicked_button = customtkinter.CTkButton(self.clicked_position_frame, text="INSPECT CLICKED MODULE",
            command=self.button_inspect_clicked_event_click, state='disabled')
        self.inspect_clicked_button.grid(row=0, column=1, padx=20, pady=(20, 10))

        self.delete_clicked_button = customtkinter.CTkButton(self.clicked_position_frame, text="UNLOAD CLICKED MODULE",
            command=self.button_delete_clicked_event_click, state='disabled', fg_color="#cf352e", hover_color="#B02B25")
        self.delete_clicked_button.grid(row=0, column=0, padx=20, pady=(20, 10))


        # right sub widget: canvas containing DUs to click on
        self.canvas_label = customtkinter.CTkLabel(self.main_frame, text="Interactive canvas: accepting user click")
        self.canvas_label.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.canvas_label.grid_remove()

        self.canvas = customtkinter.CTkCanvas(self.main_frame, width = 500, height = 700, background='white')
        self.canvas.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.canvas.bind('<Button-1>', self.canvas_event_click)
        self.canvas.grid_remove()
        self.displayedDUtype = "None"

        # *********************************************
        #
        # === Module Assembly with MF, Hybrid HV/LV ===
        #
        # *********************************************

        self.ma_frame = customtkinter.CTkFrame(self.main_frame)
        self.ma_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew", rowspan=2, columnspan=4)
        #
        # === 1st line ===
        #
        self.module_parent_frame = customtkinter.CTkFrame(self.ma_frame)
        self.module_parent_frame.grid(row=0, column=0, padx=5, pady=5, columnspan=4)
        
        self.module_parent_label = customtkinter.CTkLabel(self.module_parent_frame, text="Parent Module")
        self.module_parent_label.grid(row=0, column=0, padx=5, pady=5, columnspan=3)
        self.module_parent_manu_label = customtkinter.CTkLabel(self.module_parent_frame, text="Manufacturer")
        self.module_parent_manu_label.grid(row=1, column=0, padx=5, pady=5, columnspan=1)
        self.module_parent_loc_label = customtkinter.CTkLabel(self.module_parent_frame, text="Location")
        self.module_parent_loc_label.grid(row=1, column=1, padx=5, pady=5, columnspan=1)
        self.module_parent_SN_label = customtkinter.CTkLabel(self.module_parent_frame, text="Parent SN")
        self.module_parent_SN_label.grid(row=3, column=0, padx=5, pady=5, columnspan=1)

        
        self.combobox_MA_mod_par_manu = customtkinter.CTkComboBox(self.module_parent_frame, values=["All manufacturers"],
                                                                  command=self.change_MA_parent_Mod_filter_event, width=250)
        self.combobox_MA_mod_par_manu.grid(row=2, column=0, padx=10, pady=10)
        self.combobox_MA_mod_par_manu.set("All manufacturers")

        
        self.combobox_MA_mod_par_loc = customtkinter.CTkComboBox(self.module_parent_frame, values=["All locations"],
                                                                  command=self.change_MA_parent_Mod_filter_event, width=250)
        self.combobox_MA_mod_par_loc.grid(row=2, column=1, padx=10, pady=10)
        self.combobox_MA_mod_par_loc.set("All locations")

        
        self.combobox_MA_mod_par_paginationFrame = customtkinter.CTkFrame(self.module_parent_frame)
        self.combobox_MA_mod_par_paginationFrame.grid(row=3, column=1, padx=20, pady=10, sticky="nsew")
        self.combobox_MA_mod_par_paginationFrame_label = customtkinter.CTkLabel(self.combobox_MA_mod_par_paginationFrame, text="0/0")
        self.combobox_MA_mod_par_paginationFrame_label.grid(row=0, column=0, padx=(10,5), pady=5, sticky="nsew")
        self.combobox_MA_mod_par_paginationButtonLeft = customtkinter.CTkButton(self.combobox_MA_mod_par_paginationFrame,
                                                                           text="<", width=30,
                                                   command=self.button_combobox_MA_mod_par_paginationButtonLeft_click)
        self.combobox_MA_mod_par_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_MA_mod_par = customtkinter.CTkComboBox(self.combobox_MA_mod_par_paginationFrame,
                                                    values=["Nothing"],
                                                    command=self.combobox_MA_mod_event_select,
                                                    state="readonly",width=200)
        self.combobox_MA_mod_par.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_MA_mod_par.set("- Select -")
        self.combobox_MA_mod_par_paginationButtonRight = customtkinter.CTkButton(self.combobox_MA_mod_par_paginationFrame,
                                                                           text=">", width=30,
                                                   command=self.button_combobox_MA_mod_par_paginationButtonRight_click)
        self.combobox_MA_mod_par_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)

        
        self.inspect_parent_module_button = customtkinter.CTkButton(self.module_parent_frame, text="INSPECT MODULE",
            command=self.button_inspect_parent_module_event_click)
        self.inspect_parent_module_button.grid(row=3, column=2, padx=20, pady=10)

        #self.update_idletasks()
        #width, height = self.winfo_screenwidth(), self.winfo_screenheight()
        #print(width)
        #print(height)
        #print(width/4)
        #print((width/4)*1080/1920)
        self.module_image = customtkinter.CTkImage(Image.open('Module.png'), size=(1920/5, (1920/5)*1080/1920))
        self.module_image_in_label = customtkinter.CTkLabel(self.module_parent_frame, text="", image=self.module_image)
        self.module_image_in_label.grid(row=0, column=3, padx=15, pady=15, sticky="nsew", rowspan=4)

        
        #
        # === 2nd line ===
        #
        self.module_children_frame = customtkinter.CTkFrame(self.ma_frame)
        self.module_children_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew", columnspan=4)
        self.module_children_frame.grid_columnconfigure((0,1,2,3), weight=1)

        #
        # === Module Flex ===
        #
        self.module_flex_child_frame = customtkinter.CTkFrame(self.module_children_frame)
        self.module_flex_child_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.module_flex_child_frame.grid_columnconfigure((0,1), weight=1)
        
        self.module_flex_child_label = customtkinter.CTkLabel(self.module_flex_child_frame, text="Child Module Flex")
        self.module_flex_child_label.grid(row=0, column=0, padx=5, pady=5, columnspan=2)
        self.module_flex_child_loc_label = customtkinter.CTkLabel(self.module_flex_child_frame, text="Location")
        self.module_flex_child_loc_label.grid(row=1, column=0, padx=5, pady=5, columnspan=2)
        self.combobox_module_flex_child_loc = customtkinter.CTkComboBox(self.module_flex_child_frame, values=["All locations"],
                                                                  command=self.change_MA_child_MF_filter_event, width=250)
        self.combobox_module_flex_child_loc.grid(row=2, column=0, padx=10, pady=10, columnspan=2)
        self.combobox_module_flex_child_loc.set("All locations")
        self.module_flex_child_conn_label = customtkinter.CTkLabel(self.module_flex_child_frame, text="Connection status")
        self.module_flex_child_conn_label.grid(row=3, column=0, padx=5, pady=5, columnspan=2)
        self.MA_child_module_flex_conn_optionmenu = customtkinter.CTkOptionMenu(self.module_flex_child_frame, values=["Not yet connected children", "All children"],
                                                                       command=self.change_MA_child_MF_filter_event, width=250)
        self.MA_child_module_flex_conn_optionmenu.grid(row=4, column=0, padx=10, pady=10, columnspan=2)
        self.MA_child_module_flex_conn_optionmenu.set("All children")
        self.module_flex_child_SN_label = customtkinter.CTkLabel(self.module_flex_child_frame, text="Module Flex SN")
        self.module_flex_child_SN_label.grid(row=5, column=0, padx=5, pady=5, columnspan=2)

        self.combobox_MA_MF_chi_paginationFrame = customtkinter.CTkFrame(self.module_flex_child_frame)
        self.combobox_MA_MF_chi_paginationFrame.grid(row=6, column=0, padx=20, pady=10, sticky="nsew", columnspan=2)
        self.combobox_MA_MF_chi_paginationFrame_label = customtkinter.CTkLabel(self.combobox_MA_MF_chi_paginationFrame, text="0/0")
        self.combobox_MA_MF_chi_paginationFrame_label.grid(row=0, column=0, padx=(10,5), pady=5, sticky="nsew")
        self.combobox_MA_MF_chi_paginationButtonLeft = customtkinter.CTkButton(self.combobox_MA_MF_chi_paginationFrame,
                                                                           text="<", width=30,
                                                   command=lambda: self.button_combobox_paginationButton_click())
        self.combobox_MA_MF_chi_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_MA_MF_chi = customtkinter.CTkComboBox(self.combobox_MA_MF_chi_paginationFrame,
                                                    values=["Nothing"],
                                                    command=self.combobox_MA_MF_event_select,
                                                    state="readonly",width=200)
        self.combobox_MA_MF_chi.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_MA_MF_chi.set("- Select -")
        self.combobox_MA_MF_chi_paginationButtonRight = customtkinter.CTkButton(self.combobox_MA_MF_chi_paginationFrame,
                                                                           text=">", width=30,
                                                   command=lambda: self.button_combobox_paginationButton_click())
        self.combobox_MA_MF_chi_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)
        
        self.inspect_child_module_flex_button = customtkinter.CTkButton(self.module_flex_child_frame, text="INSPECT MODULE FLEX",
            command=self.button_inspect_child_module_flex_event_click)
        self.inspect_child_module_flex_button.grid(row=7, column=0, padx=10, pady=10, columnspan=2)
        self.add_child_module_flex_button = customtkinter.CTkButton(self.module_flex_child_frame, text="CONNECT MODULE FLEX\nTO MODULE ABOVE",
            command=self.button_add_child_module_flex_event_click, fg_color="#339941", hover_color="#228831")
        self.add_child_module_flex_button.grid(row=8, column=0, padx=10, pady=10, columnspan=2)
        self.delete_child_module_flex_button = customtkinter.CTkButton(self.module_flex_child_frame, text="DISCONNECT MODULE FLEX\nFROM ITS PARENT",
            command=self.button_delete_child_module_flex_event_click, state='disabled', fg_color="#cf352e", hover_color="#B02B25")
        self.delete_child_module_flex_button.grid(row=9, column=0, padx=10, pady=10, columnspan=2)

        #
        # === Hybrid HV-side ===
        #
        self.HY_HV_child_frame = customtkinter.CTkFrame(self.module_children_frame)
        self.HY_HV_child_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        self.HY_HV_child_frame.grid_columnconfigure((0,1), weight=1)
        self.HY_HV_child_label = customtkinter.CTkLabel(self.HY_HV_child_frame, text="Child Hybrid HV-side")
        self.HY_HV_child_label.grid(row=0, column=0, padx=5, pady=5, columnspan=2)
        self.HY_HV_child_loc_label = customtkinter.CTkLabel(self.HY_HV_child_frame, text="Location")
        self.HY_HV_child_loc_label.grid(row=1, column=0, padx=5, pady=5, columnspan=2)
        self.combobox_HY_HV_child_loc = customtkinter.CTkComboBox(self.HY_HV_child_frame, values=["All locations"],
                                                                  command=self.change_MA_child_HY_HV_filter_event, width=250)
        self.combobox_HY_HV_child_loc.grid(row=2, column=0, padx=10, pady=10, columnspan=2)
        self.combobox_HY_HV_child_loc.set("All locations")
        self.HY_HV_child_conn_label = customtkinter.CTkLabel(self.HY_HV_child_frame, text="Connection status")
        self.HY_HV_child_conn_label.grid(row=3, column=0, padx=5, pady=5, columnspan=2)
        self.MA_child_HY_HV_conn_optionmenu = customtkinter.CTkOptionMenu(self.HY_HV_child_frame, values=["Not yet connected children", "All children"],
                                                                       command=self.change_MA_child_HY_HV_filter_event, width=250)
        self.MA_child_HY_HV_conn_optionmenu.grid(row=4, column=0, padx=10, pady=10, columnspan=2)
        self.MA_child_HY_HV_conn_optionmenu.set("All children")
        self.HY_HV_child_conn_label = customtkinter.CTkLabel(self.HY_HV_child_frame, text="Cluster based on VBD")
        self.HY_HV_child_conn_label.grid(row=5, column=0, padx=5, pady=5, columnspan=2)
        self.combobox_HY_HV_child_cluster = customtkinter.CTkComboBox(self.HY_HV_child_frame, values=["All clusters"],
                                                                  command=self.change_MA_child_HY_HV_filter_event, width=250)
        self.combobox_HY_HV_child_cluster.grid(row=6, column=0, padx=10, pady=10, columnspan=2)
        self.combobox_HY_HV_child_cluster.set("All clusters")
        self.HY_HV_child_SN_label = customtkinter.CTkLabel(self.HY_HV_child_frame, text="HY HV-side SN")
        self.HY_HV_child_SN_label.grid(row=7, column=0, padx=5, pady=5, columnspan=2)

        self.combobox_HY_HV_paginationFrame = customtkinter.CTkFrame(self.HY_HV_child_frame)
        self.combobox_HY_HV_paginationFrame.grid(row=8, column=0, padx=20, pady=10, sticky="nsew", columnspan=2)
        self.combobox_HY_HV_paginationFrame_label = customtkinter.CTkLabel(self.combobox_HY_HV_paginationFrame, text="0/0")
        self.combobox_HY_HV_paginationFrame_label.grid(row=0, column=0, padx=(10,5), pady=5, sticky="nsew")
        self.combobox_HY_HV_paginationButtonLeft = customtkinter.CTkButton(self.combobox_HY_HV_paginationFrame,
                                                                           text="<", width=30,
                                                   command=lambda: self.button_combobox_paginationButton_click())
        self.combobox_HY_HV_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_HY_HV = customtkinter.CTkComboBox(self.combobox_HY_HV_paginationFrame,
                                                    values=["Nothing"],
                                                    command=self.combobox_MA_HY_HV_event_select,
                                                    state="readonly",width=200)
        self.combobox_HY_HV.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_HY_HV.set("- Select -")
        self.combobox_HY_HV_paginationButtonRight = customtkinter.CTkButton(self.combobox_HY_HV_paginationFrame,
                                                                           text=">", width=30,
                                                   command=lambda: self.button_combobox_paginationButton_click())
        self.combobox_HY_HV_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)
        
        self.inspect_child_HY_HV_button = customtkinter.CTkButton(self.HY_HV_child_frame, text="INSPECT HY HV-side",
            command=self.button_inspect_child_HY_HV_event_click)
        self.inspect_child_HY_HV_button.grid(row=9, column=0, padx=10, pady=10, columnspan=2)
        self.add_child_HY_HV_button = customtkinter.CTkButton(self.HY_HV_child_frame, text="CONNECT HY HV-side\nTO MODULE ABOVE",
            command=self.button_add_child_HY_HV_event_click, fg_color="#339941", hover_color="#228831")
        self.add_child_HY_HV_button.grid(row=10, column=0, padx=10, pady=10, columnspan=2)
        self.delete_child_HY_HV_button = customtkinter.CTkButton(self.HY_HV_child_frame, text="DISCONNECT HY HV-side\nFROM ITS PARENT",
            command=self.button_delete_child_HY_HV_event_click, state='disabled', fg_color="#cf352e", hover_color="#B02B25")
        self.delete_child_HY_HV_button.grid(row=11, column=0, padx=10, pady=10, columnspan=2)

        #
        # === Hybrid LV-side ===
        #
        self.HY_LV_child_frame = customtkinter.CTkFrame(self.module_children_frame)
        self.HY_LV_child_frame.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        self.HY_LV_child_frame.grid_columnconfigure((0,1), weight=1)
        self.HY_LV_child_label = customtkinter.CTkLabel(self.HY_LV_child_frame, text="Child Hybrid LV-side")
        self.HY_LV_child_label.grid(row=0, column=0, padx=5, pady=5, columnspan=2)
        self.HY_LV_child_loc_label = customtkinter.CTkLabel(self.HY_LV_child_frame, text="Location")
        self.HY_LV_child_loc_label.grid(row=1, column=0, padx=5, pady=5, columnspan=2)
        self.combobox_HY_LV_child_loc = customtkinter.CTkComboBox(self.HY_LV_child_frame, values=["All locations"],
                                                                  command=self.change_MA_child_HY_LV_filter_event, width=250)
        self.combobox_HY_LV_child_loc.grid(row=2, column=0, padx=10, pady=10, columnspan=2)
        self.combobox_HY_LV_child_loc.set("All locations")
        self.HY_LV_child_conn_label = customtkinter.CTkLabel(self.HY_LV_child_frame, text="Connection status")
        self.HY_LV_child_conn_label.grid(row=3, column=0, padx=5, pady=5, columnspan=2)
        self.MA_child_HY_LV_conn_optionmenu = customtkinter.CTkOptionMenu(self.HY_LV_child_frame, values=["Not yet connected children", "All children"],
                                                                       command=self.change_MA_child_HY_LV_filter_event, width=250)
        self.MA_child_HY_LV_conn_optionmenu.grid(row=4, column=0, padx=10, pady=10, columnspan=2)
        self.MA_child_HY_LV_conn_optionmenu.set("All children")
        self.HY_LV_child_conn_label = customtkinter.CTkLabel(self.HY_LV_child_frame, text="Cluster based on VBD")
        self.HY_LV_child_conn_label.grid(row=5, column=0, padx=5, pady=5, columnspan=2)
        self.combobox_HY_LV_child_cluster = customtkinter.CTkComboBox(self.HY_LV_child_frame, values=["All clusters"],
                                                                  command=self.change_MA_child_HY_LV_filter_event, width=250)
        self.combobox_HY_LV_child_cluster.grid(row=6, column=0, padx=10, pady=10, columnspan=2)
        self.combobox_HY_LV_child_cluster.set("All clusters")
        self.HY_LV_child_SN_label = customtkinter.CTkLabel(self.HY_LV_child_frame, text="HY LV-side SN")
        self.HY_LV_child_SN_label.grid(row=7, column=0, padx=5, pady=5, columnspan=2)

        self.combobox_HY_LV_paginationFrame = customtkinter.CTkFrame(self.HY_LV_child_frame)
        self.combobox_HY_LV_paginationFrame.grid(row=8, column=0, padx=20, pady=10, sticky="nsew", columnspan=2)
        self.combobox_HY_LV_paginationFrame_label = customtkinter.CTkLabel(self.combobox_HY_LV_paginationFrame, text="0/0")
        self.combobox_HY_LV_paginationFrame_label.grid(row=0, column=0, padx=(10,5), pady=5, sticky="nsew")
        self.combobox_HY_LV_paginationButtonLeft = customtkinter.CTkButton(self.combobox_HY_LV_paginationFrame,
                                                                           text="<", width=30,
                                                   command=lambda: self.button_combobox_paginationButton_click())
        self.combobox_HY_LV_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_HY_LV = customtkinter.CTkComboBox(self.combobox_HY_LV_paginationFrame,
                                                    values=["Nothing"],
                                                    command=self.combobox_MA_HY_LV_event_select,
                                                    state="readonly",width=200)
        self.combobox_HY_LV.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_HY_LV.set("- Select -")
        self.combobox_HY_LV_paginationButtonRight = customtkinter.CTkButton(self.combobox_HY_LV_paginationFrame,
                                                                           text=">", width=30,
                                                   command=lambda: self.button_combobox_paginationButton_click())
        self.combobox_HY_LV_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)
        
        self.inspect_child_HY_LV_button = customtkinter.CTkButton(self.HY_LV_child_frame, text="INSPECT HY LV-side",
            command=self.button_inspect_child_HY_LV_event_click)
        self.inspect_child_HY_LV_button.grid(row=9, column=0, padx=10, pady=10, columnspan=2)
        self.add_child_HY_LV_button = customtkinter.CTkButton(self.HY_LV_child_frame, text="CONNECT HY LV-side\nTO MODULE ABOVE",
            command=self.button_add_child_HY_LV_event_click, fg_color="#339941", hover_color="#228831")
        self.add_child_HY_LV_button.grid(row=10, column=0, padx=10, pady=10, columnspan=2)
        self.delete_child_HY_LV_button = customtkinter.CTkButton(self.HY_LV_child_frame, text="DISCONNECT HY LV-side\nFROM ITS PARENT",
            command=self.button_delete_child_HY_LV_event_click, state='disabled', fg_color="#cf352e", hover_color="#B02B25")
        self.delete_child_HY_LV_button.grid(row=11, column=0, padx=10, pady=10, columnspan=2)

        # ******************************************
        #
        # === Slot global/local for FT selection ===
        #
        # ******************************************

        self.ft_rel_frame = customtkinter.CTkFrame(self.main_frame, width = 600)
        self.ft_rel_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew", rowspan=2, columnspan=2)
        self.ft_rel_frame.grid_remove()

        #
        # === 1st line ===
        #
        self.slot_sel_frame = customtkinter.CTkFrame(self.ft_rel_frame)
        self.slot_sel_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew", columnspan=3)
        self.slot_sel_frame.grid_columnconfigure((0,1,2,3,4), weight=1)
        self.slot_sel_frame.grid_rowconfigure((0,1,2), weight=1)

        self.slot_vessel_optionmenu = customtkinter.CTkOptionMenu(self.slot_sel_frame, values=["Vessel: 1", "Vessel: 2", "Vessel: M", "Vessel: D"],
                                                                       command=self.change_child_conn_event, width=200)
        self.slot_vessel_optionmenu.grid(row=0, column=0, padx=5, pady=10)
        self.slot_vessel_optionmenu.set("Vessel: 1")

        self.slot_layer_optionmenu = customtkinter.CTkOptionMenu(self.slot_sel_frame, values=["Layer: 0", "Layer: 1", "Layer: 2", "Layer: 3"],
                                                                       command=self.change_child_conn_event, width=200)
        self.slot_layer_optionmenu.grid(row=1, column=0, padx=5, pady=10)
        self.slot_layer_optionmenu.set("Layer: 0")

        self.slot_quadrant_optionmenu = customtkinter.CTkOptionMenu(self.slot_sel_frame, values=["Quadrant: 0", "Quadrant: 1", "Quadrant: 2", "Quadrant: 3"],
                                                                       command=self.change_child_conn_event, width=200)
        self.slot_quadrant_optionmenu.grid(row=2, column=0, padx=5, pady=10)
        self.slot_quadrant_optionmenu.set("Quadrant: 0")

        self.slot_global_label = customtkinter.CTkLabel(self.slot_sel_frame, text="Global (type in):")
        self.slot_global_label.grid(row=0, column=1, padx=20, pady=10, sticky="nsew")

        self.find_slot_button = customtkinter.CTkButton(self.slot_sel_frame, text="FIND IN SLOT TABLE",
            command=self.button_find_slot_event_click)
        self.find_slot_button.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")

        self.inspect_slot_button = customtkinter.CTkButton(self.slot_sel_frame, text="INSPECT SLOT",
            command=self.button_inspect_slot_event_click)
        self.inspect_slot_button.grid(row=3, column=1, padx=20, pady=10)
        
        self.slot_local_label = customtkinter.CTkLabel(self.slot_sel_frame, text="Local (derived):")
        self.slot_local_label.grid(row=2, column=1, padx=20, pady=10, sticky="nsew")
        
        self.slot_DU_type_label = customtkinter.CTkLabel(self.slot_sel_frame, text="DU type")
        self.slot_DU_type_label.grid(row=1, column=2, padx=20, pady=10, sticky="nsew")
        
        self.slot_loc_DUtype_variable = customtkinter.StringVar(value="- automatic -")
        self.slot_loc_DUtype_entry = customtkinter.CTkEntry(self.slot_sel_frame, textvariable=self.slot_loc_DUtype_variable, state='disabled')
        self.slot_loc_DUtype_entry.grid(row=2, column=2, padx=20, pady=10, sticky="nsew")

        
        self.slot_glob_row_variable = customtkinter.StringVar(value="")
        self.slot_glob_row_entry = customtkinter.CTkEntry(self.slot_sel_frame, textvariable=self.slot_glob_row_variable)
        self.slot_glob_row_entry.grid(row=0, column=3, padx=20, pady=10, sticky="nsew")
        
        self.slot_row_label = customtkinter.CTkLabel(self.slot_sel_frame, text="Row")
        self.slot_row_label.grid(row=1, column=3, padx=20, pady=10, sticky="nsew")
        
        self.slot_loc_row_variable = customtkinter.StringVar(value="- automatic -")
        self.slot_loc_row_entry = customtkinter.CTkEntry(self.slot_sel_frame, textvariable=self.slot_loc_row_variable, state='disabled')
        self.slot_loc_row_entry.grid(row=2, column=3, padx=20, pady=10, sticky="nsew")


        self.slot_glob_mod_variable = customtkinter.StringVar(value="")
        self.slot_glob_mod_entry = customtkinter.CTkEntry(self.slot_sel_frame, textvariable=self.slot_glob_mod_variable)
        self.slot_glob_mod_entry.grid(row=0, column=4, padx=20, pady=10, sticky="nsew")
        
        self.slot_mod_label = customtkinter.CTkLabel(self.slot_sel_frame, text="Mod")
        self.slot_mod_label.grid(row=1, column=4, padx=20, pady=10, sticky="nsew")
        
        self.slot_loc_mod_variable = customtkinter.StringVar(value="- automatic -")
        self.slot_loc_mod_entry = customtkinter.CTkEntry(self.slot_sel_frame, textvariable=self.slot_loc_mod_variable, state='disabled')
        self.slot_loc_mod_entry.grid(row=2, column=4, padx=20, pady=10, sticky="nsew")
        
        #
        # === 2nd line ===
        #
        self.ft_gen_label = customtkinter.CTkLabel(self.ft_rel_frame, text="Suitable FT batch(es)/meta-generation for this VLQ:")
        self.ft_gen_label.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # demo: 20WFTC11F/20WFTS11F/20WFTG11F (old order cat 01--36), 20WFTG12F (new order cat 37--57)
        # M0 & Full det: 20WFTCM1F/20WFTSM1F/20WFTGM1F (future cat 01--62)
        self.ft_gen_label_output = customtkinter.CTkLabel(self.ft_rel_frame, text=" ")
        self.ft_gen_label_output.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")

        #
        # === 3rd line ===
        #
        self.ft_type_label = customtkinter.CTkLabel(self.ft_rel_frame, text="Derived FT type of this FT generation for this Slot:")
        self.ft_type_label.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        
        self.ft_type_label_output = customtkinter.CTkLabel(self.ft_rel_frame, text=" ")
        self.ft_type_label_output.grid(row=2, column=1, padx=20, pady=10, sticky="nsew")

        #
        # === 4/5th line ===
        #
        self.combobox_ft_label = customtkinter.CTkLabel(self.ft_rel_frame, text="FTs matching selection criteria:")
        self.combobox_ft_label.grid(row=4, column=0, padx=20, pady=10, sticky="nsew")

        self.ft_conn_optionmenu = customtkinter.CTkOptionMenu(self.ft_rel_frame, values=["Not yet connected FTs", "All FTs"],
                                                                       command=self.change_ft_conn_event, width=250)
        self.ft_conn_optionmenu.grid(row=3, column=0, padx=20, pady=10)
        self.ft_conn_optionmenu.set("All FTs")
        

        self.combobox_ft_paginationFrame = customtkinter.CTkFrame(self.ft_rel_frame)
        self.combobox_ft_paginationFrame.grid(row=4, column=1, padx=20, pady=10, sticky="ns")
        self.combobox_ft_paginationFrame_label = customtkinter.CTkLabel(self.combobox_ft_paginationFrame, text="0/0")
        self.combobox_ft_paginationFrame_label.grid(row=0, column=0, padx=(10,5), pady=5, sticky="nsew")
        self.combobox_ft_paginationButtonLeft = customtkinter.CTkButton(self.combobox_ft_paginationFrame,
                                                                           text="<", width=30,
                                                   command=self.button_combobox_ft_paginationButtonLeft_click)
        self.combobox_ft_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_ft = customtkinter.CTkComboBox(self.combobox_ft_paginationFrame,
                                                    values=["Nothing"],
                                                    command=self.combobox_ft_event_select,
                                                    state="readonly",width=200)
        self.combobox_ft.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_ft.set("- Select -")
        self.combobox_ft_paginationButtonRight = customtkinter.CTkButton(self.combobox_ft_paginationFrame,
                                                                           text=">", width=30,
                                                   command=self.button_combobox_ft_paginationButtonRight_click)
        self.combobox_ft_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)


        self.inspect_ft_button = customtkinter.CTkButton(self.ft_rel_frame, text="INSPECT FT",
            command=self.button_inspect_ft_event_click)
        self.inspect_ft_button.grid(row=4, column=2, padx=20, pady=10)

        self.delete_connected_ft_button = customtkinter.CTkButton(self.ft_rel_frame, text="DISCONNECT SELECTED FT",
            command=self.button_delete_connected_ft_event_click, state='disabled', fg_color="#cf352e", hover_color="#B02B25")
        self.delete_connected_ft_button.grid(row=5, column=1, padx=20, pady=(20, 10))
        
        self.add_ft_button = customtkinter.CTkButton(self.ft_rel_frame, text="ADD PARTS TREE",
            command=self.button_add_ft_event_click)
        self.add_ft_button.grid(row=5, column=2, padx=20, pady=10)

        # footer: info for user (e.g. Warning, Error)
        self.info_label = customtkinter.CTkLabel(self.main_frame, text=" ", font=customtkinter.CTkFont(size=16, weight="bold"))
        self.info_label.grid(row=2, column=0, padx=20, pady=20, columnspan=2)

        # *************************************************
        #
        # === Filling variables with defaults / startup ===
        #
        # *************************************************

        # First startup of program: default values
        self.api_status = 1
        self.last_responseText = ''
        self.slots = None
        self.partstree = None
        self.this_DU_relations_MODULE = []
        self.this_MODULE_relations_DU = []
        self.this_MODULE_relations_SLOT = []
        self.this_FT_relations_SLOT = []
        self.this_SLOT_relations_FT = []
        self.ft_filter = ''
        self.combined_slot = ''
        self.cbx_par_n_pages = 0
        self.cbx_chi_n_pages = 0
        self.cbx_ft_n_pages = 0
        self.cbx_ptype_n_pages = 0
        self.cbx_ctype_n_pages = 0
        self.cbx_par_shown_page = 0
        self.cbx_chi_shown_page = 0
        self.cbx_ft_shown_page = 0
        self.cbx_ptype_shown_page = 0
        self.cbx_ctype_shown_page = 0
        self.clicked_module = []

        self.par_type = None
        self.chi_type = None
        self.chi_conn = None
        self.chi_manu = None
        self.ft_conn = None

        self.user = 'None'
        self.users = ['None', 'new...']

        # Get first parents and children (Module Loading), FTs
        try:
            # ToDo: use this as long as the token is valid self.access_token = util.get_access_token()
            self.possible_parents, self.last_responseText = util.get_relevant_parts('Detector Unit')
            self.possible_children, self.last_responseText = util.get_relevant_parts('Module')
            self.possible_ft, self.last_responseText = util.get_relevant_parts('FT')
            self.manufacturers, self.last_responseText = util.get_manufacturers()
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            self.possible_parents = []
            self.possible_children = []
            self.possible_ft = []
            self.manufacturers = []
            self.last_responseText = str(e)
        except ValueError as e:
            self.possible_parents = []
            self.possible_children = []
            self.possible_ft = []
            self.manufacturers = []
            self.last_responseText = str(e)

        if self.last_responseText[:3] != '200':
            self.api_status = 0
            self.progressbar.configure(progress_color="#ff0000")
            info_text = wrapped_text.fill(f'Error: Parents / Children could not be loaded from ProdDB API.\n{self.last_responseText}')
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color="#007711")
            self.possible_parents_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(self.possible_parents)
            self.possible_children_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(self.possible_children)
            self.possible_ft_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(self.possible_ft)
            self.possible_parents_SNs = [entry[0] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_parents_SNs_chunked = [self.possible_parents_SNs[i:i + self.n_items_to_show_in_cbx] for i in range(0, len(self.possible_parents_SNs), self.n_items_to_show_in_cbx)]
            self.possible_children_SNs = [entry[0] for entry in self.possible_children_SNs_and_partIDs]
            self.possible_children_SNs_chunked = [self.possible_children_SNs[i:i + self.n_items_to_show_in_cbx] for i in range(0, len(self.possible_children_SNs), self.n_items_to_show_in_cbx)]
            self.possible_ft_SNs = [entry[0] for entry in self.possible_ft_SNs_and_partIDs]
            self.possible_ft_SNs_chunked = [self.possible_ft_SNs[i:i + self.n_items_to_show_in_cbx] for i in range(0, len(self.possible_ft_SNs), self.n_items_to_show_in_cbx)]
            self.possible_par_types = ["All DU types"]+list(data.allDUs.keys())
            self.possible_par_types_chunked = [self.possible_par_types[i:i + self.n_items_to_show_in_cbx] for i in range(0, len(self.possible_par_types), self.n_items_to_show_in_cbx)]
            self.possible_chi_types = ["All DU types"]+list(data.allDUs.keys())
            self.possible_chi_types_chunked = [self.possible_chi_types[i:i + self.n_items_to_show_in_cbx] for i in range(0, len(self.possible_chi_types), self.n_items_to_show_in_cbx)]
            self.possible_parents_partIDs = [entry[1] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_children_partIDs = [entry[1] for entry in self.possible_children_SNs_and_partIDs]
            self.possible_ft_partIDs = [entry[1] for entry in self.possible_ft_SNs_and_partIDs]
            self.cbx_par_n_pages = len(self.possible_parents_SNs_chunked)
            self.cbx_chi_n_pages = len(self.possible_children_SNs_chunked)
            self.cbx_ft_n_pages = len(self.possible_ft_SNs_chunked)
            self.cbx_ptype_n_pages = len(self.possible_par_types_chunked)
            self.cbx_ctype_n_pages = len(self.possible_chi_types_chunked)
            self.cbx_par_shown_page = 1
            self.cbx_chi_shown_page = 1
            self.cbx_ft_shown_page = 1
            self.cbx_ptype_shown_page = 1
            self.cbx_ctype_shown_page = 1
            self.combobox_parent_paginationFrame_label.configure(text=f"page {self.cbx_par_shown_page}/{self.cbx_par_n_pages}")
            self.combobox_child_paginationFrame_label.configure(text=f"page {self.cbx_chi_shown_page}/{self.cbx_chi_n_pages}")
            self.combobox_ft_paginationFrame_label.configure(text=f"page {self.cbx_ft_shown_page}/{self.cbx_ft_n_pages}")
            self.combobox_par_type_paginationFrame_label.configure(text=f"page {self.cbx_ptype_shown_page}/{self.cbx_ptype_n_pages}")
            self.combobox_chi_type_paginationFrame_label.configure(text=f"page {self.cbx_ctype_shown_page}/{self.cbx_ctype_n_pages}")
            self.combobox_parent.configure(values=self.possible_parents_SNs_chunked[0])
            self.combobox_child.configure(values=self.possible_children_SNs_chunked[0])
            self.combobox_ft.configure(values=self.possible_ft_SNs_chunked[0])
            self.combobox_par_type.configure(values=self.possible_par_types_chunked[0])
            self.combobox_chi_type.configure(values=self.possible_chi_types_chunked[0])
            self.combobox_child_manu.configure(values=["All manufacturers"]+[m['manufacturer_name'] for m in self.manufacturers])

    def authenticate_return_function(self, result, response):
        if response[:2] != '20':
            self.api_status = 0
            self.progressbar.configure(progress_color="#ff0000")

            info_text = wrapped_text.fill(f'Error: New user could not be authenticated.\n{response}')
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)

            self.user_optionmenu.set('None')
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color="#007711")

            self.info_label.configure(text=' ')

            self.user = result
            self.last_responseText = response

            old_users = self.users[:-1] # all old ones without 'new...'
            if result not in old_users:
                new_users = old_users + [result, 'new...']
                self.users = new_users
                self.user_optionmenu.configure(values = new_users)
            self.user_optionmenu.set(result)

    def authenticate_user(self):
        # open a tiny window with extra inputs, return new_authenticated_user
        if self.user_window is None or not self.user_window.winfo_exists():
            self.user_window = AuthenticateWindow(self.authenticate_return_function)  # create window if its None or destroyed
        else:
            self.user_window.focus()  # if window exists focus it

    def button_add_child_module_flex_event_click(self):
        pass

    def button_add_child_HY_HV_event_click(self):
        pass

    def button_add_child_HY_LV_event_click(self):
        pass
        
    def button_add_ft_event_click(self, debug = False):
        chi = self.combobox_ft.get()
        par = self.combined_slot
        if chi == '- Select -' or par == '':
            info_text = 'Warning: Select a FT & Slot from the respective lists to proceed.'
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.info_label.configure(text=' ')
            chi_partID = self.possible_ft_partIDs[self.possible_ft_SNs.index(chi)]
            for s in self.slots:
                if s['part_serial_number'] == par:
                    par_partID = s['part_id']
                    break
            if self.user != 'None' and self.user != 'new...':
                part_tree = {
                    'position': '',
                    'is_record_deleted': 'F',
                    'part': chi_partID,
                    'part_parent': par_partID,
                    'record_insertion_user': self.user,
                }
            else:
                part_tree = {
                    'position': '',
                    'is_record_deleted': 'F',
                    'part': chi_partID,
                    'part_parent': par_partID,
                }
            allowed_slot = False
            occupied_slot = False
            confirmed = ''
            try:
                # allowed: chosen FT matches the generation and category that the slot requires
                gen = self.ft_filter.split('+')[0].split('/') # multiple generations
                cat = self.ft_filter[-2:] # the last two chars make the category
                if any(gen_ in chi for gen_ in gen) and int(chi[9:11]) == int(cat):
                    allowed_slot = True
                    children_of_targetSlot, self.last_responseText = util.get_children(par_partID, ofKind = 'FT')
                    FT_already_occupying_target_position = ''
                    Slot_FT_relation_to_delete = ''
                    matching_relation = []
                    for c in children_of_targetSlot:
                        occupied_slot = True
                        FT_already_occupying_target_position = c['part']['serial_number']
                        Slot_FT_relation_to_delete = c['record_id']
                        matching_relation = c
                        break
                    if occupied_slot:
                        confirmed = ''
                        dialog = customtkinter.CTkInputDialog(text=f"This Slot is already occupied by the FT {FT_already_occupying_target_position}.\n" +
                                "Confirm by typing a confirmation: OVERWRITE to overwrite it with your selected FT:", title="Confirm dialog")
                        confirmed = dialog.get_input()
                        if debug:
                            print("Typed in confirmation from confirm dialog:", confirmed)
                        if confirmed == 'OVERWRITE':
                            # DELETION OF PREVIOUS STUFF

                            # delete Slot -> FT relation for the FT that already occupies that Slot
                            self.last_responseText = api.delete_information(f'/partstreedelete/{Slot_FT_relation_to_delete}/')

                            # POSTING NEW STUFF

                            # connect new FT there by creating a new Slot -> FT relation
                            self.last_responseText = api.post_information('/partstreelist', part_tree)
                    else:
                        self.last_responseText = api.post_information('/partstreelist', part_tree)
                        
                else:
                    info_text = wrapped_text.fill(f'Error: You can not connect this FT to the selected slot.\nCheck the FT generation and FT category requirements!')
                    print(f'>>> {info_text}')
                    self.info_label.configure(text=info_text)

            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                self.last_responseText = str(e)
            except ValueError as e:
                self.last_responseText = str(e)

            if self.last_responseText[:2] != '20':
                self.api_status = 0
                self.progressbar.configure(progress_color="#ff0000")
                info_text = wrapped_text.fill(f'Error: Parent / Child relations could not be fetched, deleted or posted to ProdDB API.\n{self.last_responseText}')
                print(f'>>> {info_text}')
                self.info_label.configure(text=info_text)
            else:
                self.api_status = 1
                self.progressbar.configure(progress_color="#007711")

                self.combobox_ft.set("- Select -")
                self.this_FT_relations_SLOT = []
                self.loading_wheel = threading.Thread(target=self.fetch_ft)
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)

    def button_add_event_click(self, debug = False):
        chi = self.combobox_child.get()
        par = self.combobox_parent.get()
        pos = self.position_entry.get()
        if chi == '- Select -' or par == '- Select -' or pos == '- automatic -' or pos == 'VxLyQz':
            info_text = 'Warning: Select a child & parent from the respective lists and a position to proceed.'
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.info_label.configure(text=' ')
            chi_partID = self.possible_children_partIDs[self.possible_children_SNs.index(chi)]
            par_partID = self.possible_parents_partIDs[self.possible_parents_SNs.index(par)]
            if self.user != 'None' and self.user != 'new...':
                part_tree = {
                    'position': pos,
                    'is_record_deleted': 'F',
                    'part': chi_partID,
                    'part_parent': par_partID,
                    'record_insertion_user': self.user,
                }
            else:
                part_tree = {
                    'position': pos,
                    'is_record_deleted': 'F',
                    'part': chi_partID,
                    'part_parent': par_partID,
                }
            allowed_VLQ = False
            occupied_VLQ = False
            confirmed = pos
            try:
                if self.operation_mode == 'Module Loading':
                    self.last_responseText = api.post_information('/partstreelist', part_tree)

                    self.displayedDUtype = "None"
                    self.this_DU_relations_MODULE = []
                    self.this_MODULE_relations_DU = []
                    self.this_MODULE_relations_SLOT = []
                    self.possible_parents = []
                    self.possible_children = []
                    self.slots = None
                    self.partstree = None

                    self.loading_wheel = threading.Thread(target=self.fetch_loaded_DU_and_display, args=(chi, par))
                    self.loading_wheel.start()
                    self.update_progressbar(self.loading_wheel)
                elif self.operation_mode == 'Detector Assembly (CERN): DU':
                    attribute_Vessel = pos.split('V').pop().split('L')[0]
                    if attribute_Vessel not in ['1', '2', 'M', 'D']:
                        info_text = wrapped_text.fill(f'Error: You can not load to this vessel.\nVessel attribute only accepts 1, 2, M, or D, but you selected {attribute_Vessel}!')
                        print(f'>>> {info_text}')
                        self.info_label.configure(text=info_text)
                    else:
                        attribute_Layer = pos.split('L').pop().split('Q')[0]
                        if attribute_Layer not in ['0', '1', '2', '3']:
                            info_text = wrapped_text.fill(f'Error: You can not load to this layer.\nLayer attribute only accepts 0, 1, 2, or 3, but you selected {attribute_Layer}!')
                            print(f'>>> {info_text}')
                            self.info_label.configure(text=info_text)
                        else:
                            if attribute_Layer == '0' or attribute_Layer == '3':
                                allowed_type = 'F'
                                not_allowed_type = 'B'
                            else:#elif attribute_Layer == '1' or attribute_Layer == '2':
                                allowed_type = 'B'
                                not_allowed_type = 'F'
                            if self.displayedDUtype[0] == not_allowed_type:
                                info_text = wrapped_text.fill(f'Error: You can not load this DU to this layer.\nLayer {attribute_Layer} only accepts {allowed_type} DUs, but you selected a {self.displayedDUtype[0]} DU!')
                                print(f'>>> {info_text}')
                                self.info_label.configure(text=info_text)
                            else:
                                attribute_Quadrant = pos.split('Q').pop()
                                if attribute_Quadrant not in ['0', '1', '2', '3']:
                                    info_text = wrapped_text.fill(f'Error: You can not load to this quadrant.\nQuadrant attribute only accepts 0, 1, 2, or 3, but you selected {attribute_Quadrant}!')
                                    print(f'>>> {info_text}')
                                    self.info_label.configure(text=info_text)
                                else:
                                    allowed_VLQ = True
                                    children_of_targetDetector, self.last_responseText = util.get_children(par_partID)
                                    DU_already_occupying_target_position = ''
                                    Det_DU_relation_to_delete = ''
                                    matching_relation = []
                                    for c in children_of_targetDetector:
                                        # make sure to only check for DU children KoP, nothing else
                                        if str(c['part']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['PEB']):
                                            # position of Det child is the same as the desired one, and DU type of desired DU is same as the one that already occupies the spot:
                                            if str(c['position']) == pos and self.displayedDUtype in c['part']['serial_number']:
                                                occupied_VLQ = True
                                                DU_already_occupying_target_position = c['part']['serial_number']
                                                Det_DU_relation_to_delete = c['record_id']
                                                matching_relation = c
                                                break

                                    if occupied_VLQ:
                                        confirmed = ''
                                        dialog = customtkinter.CTkInputDialog(text=f"This Vessel Layer Quadrant is already occupied by the DU {DU_already_occupying_target_position}.\n" +
                                            "Confirm by typing the desired Vessel Layer Quadrant (VxLyQz) again to overwrite it with your selected DU:", title="Confirm dialog")
                                        confirmed = dialog.get_input()
                                        if debug:
                                            print("Typed in slot from confirm dialog:", confirmed)
                                        if confirmed == pos:
                                            # DELETION OF PREVIOUS STUFF

                                            # delete Det -> DU relation for the DU that already occupies that VLQ
                                            self.last_responseText = api.delete_information(f'/partstreedelete/{Det_DU_relation_to_delete}/')
                                            # get children modules of the DU that previously occupied the VLQ
                                            affected_previous_modules, self.last_responseText = util.get_children(matching_relation['part']['part_id'])
                                            # the parent slots of modules of the DU that previously occupied the VLQ
                                            for a in affected_previous_modules:
                                                affected_parents_of_children, self.last_responseText = util.get_parents(a['part']['part_id'])
                                                for p in affected_parents_of_children:
                                                    if debug:
                                                        print(str(p['part_parent']['kind_of_part']['kind_of_part_id']))
                                                    if str(p['part_parent']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['Slot']):
                                                        # delete those Slot -> Mod relations
                                                        if debug:
                                                            print('Delete Slot -> Module relation', p)
                                                        self.last_responseText = api.delete_information(f'/partstreedelete/{p['record_id']}/')

                                            # POSTING NEW STUFF

                                            # place new DU at this position by creating a new Det -> DU relation
                                            self.last_responseText = api.post_information('/partstreelist', part_tree)
                                            self.canvas.itemconfig(self.duAlreadyPlacedText, text=f'Now placed at:\n{pos}')
                                    else:
                                        self.last_responseText = api.post_information('/partstreelist', part_tree)
                                        self.canvas.itemconfig(self.duAlreadyPlacedText, text=f'Now placed at:\n{pos}')
                elif self.operation_mode == 'Detector Assembly (CERN): PEB':
                    attribute_Vessel = pos.split('V').pop().split('L')[0]
                    if attribute_Vessel not in ['1', '2', 'M', 'D']:
                        info_text = wrapped_text.fill(f'Error: You can not load to this vessel.\nVessel attribute only accepts 1, 2, M, or D, but you selected {attribute_Vessel}!')
                        print(f'>>> {info_text}')
                        self.info_label.configure(text=info_text)
                    else:
                        if attribute_Vessel in ['D'] and self.displayed_PEB_type != '1F':
                            info_text = wrapped_text.fill(f'Error: You can not load to this vessel (demonstrator).\nDemonstratorV1 only accepts PEB type 1F, but you selected a PEB of type {self.displayed_PEB_type}!')
                            print(f'>>> {info_text}')
                            self.info_label.configure(text=info_text)
                        else:
                            attribute_Layer = pos.split('L').pop().split('Q')[0]
                            if attribute_Layer not in ['0', '1', '2', '3']:
                                info_text = wrapped_text.fill(f'Error: You can not load to this layer.\nLayer attribute only accepts 0, 1, 2, or 3, but you selected {attribute_Layer}!')
                                print(f'>>> {info_text}')
                                self.info_label.configure(text=info_text)
                            else:
                                if attribute_Layer == '0' or attribute_Layer == '3':
                                    allowed_types = data.F_PEBs
                                    not_allowed_type = '3B'
                                else:#elif attribute_Layer == '1' or attribute_Layer == '2':
                                    allowed_types = data.B_PEBs
                                    not_allowed_type = '3F'
                                if self.displayed_PEB_type == not_allowed_type:
                                    info_text = wrapped_text.fill(f'Error: You can not load this PEB to this layer.\nLayer {attribute_Layer} only accepts {allowed_types} PEBs, but you selected a {self.displayed_PEB_type} PEB!')
                                    print(f'>>> {info_text}')
                                    self.info_label.configure(text=info_text)
                                else:
                                    attribute_Quadrant = pos.split('Q').pop()
                                    if attribute_Quadrant not in ['0', '1', '2', '3']:
                                        info_text = wrapped_text.fill(f'Error: You can not load to this quadrant.\nQuadrant attribute only accepts 0, 1, 2, or 3, but you selected {attribute_Quadrant}!')
                                        print(f'>>> {info_text}')
                                        self.info_label.configure(text=info_text)
                                    else:
                                        allowed_VLQ = True
                                        children_of_targetDetector, self.last_responseText = util.get_children(par_partID)
                                        PEB_already_occupying_target_position = ''
                                        Det_PEB_relation_to_delete = ''
                                        matching_relation = []
                                        for c in children_of_targetDetector:
                                            # make sure to only check for PEB children KoP, nothing else
                                            if str(c['part']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['PEB']):
                                                # position of Det child is the same as the desired one, and PEB type of desired PEB is same as the one that already occupies the spot:
                                                if str(c['position']) == pos:
                                                    # == OLD ==: previous schema did not include PEB Type in PEB SN
                                                    # == OLD ==:  => used to need to fetch the attributes of maybe occupying children PEBs, because PEB type was only part of attributes (not part of SN sadly)
                                                    # == OLD ==: child_attributes, self.last_responseText = api.fetch_information(f'/partattrlist/{c['part']['part_id']}/')
                                                    # == OLD ==: PEB_type_occupying = [c for c in child_attributes if c['attribute']['name'] == 'Type'][0]['value']
                                                    # NEW: PEB type is part of PEB SN!
                                                    if self.displayed_PEB_type in c['part']['serial_number']:
                                                        occupied_VLQ = True
                                                        PEB_already_occupying_target_position = c['part']['serial_number']
                                                        Det_PEB_relation_to_delete = c['record_id']
                                                        matching_relation = c
                                                        break
                                        if occupied_VLQ:
                                            confirmed = ''
                                            dialog = customtkinter.CTkInputDialog(text=f"This Vessel Layer Quadrant is already occupied by the PEB {PEB_already_occupying_target_position}.\n" +
                                                "Confirm by typing the desired Vessel Layer Quadrant (VxLyQz) again to overwrite it with your selected PEB:", title="Confirm dialog")
                                            confirmed = dialog.get_input()
                                            if debug:
                                                print("Typed in slot from confirm dialog:", confirmed)
                                            if confirmed == pos:
                                                # DELETION OF PREVIOUS STUFF
    
                                                # delete Det -> PEB relation for the PEB that already occupies that VLQ
                                                self.last_responseText = api.delete_information(f'/partstreedelete/{Det_PEB_relation_to_delete}/')
    
                                                # POSTING NEW STUFF
    
                                                # place new DU at this position by creating a new Det -> PEB relation
                                                self.last_responseText = api.post_information('/partstreelist', part_tree)
                                        else:
                                            self.last_responseText = api.post_information('/partstreelist', part_tree)

            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                self.last_responseText = str(e)
            except ValueError as e:
                self.last_responseText = str(e)

            if self.last_responseText[:2] != '20':
                self.api_status = 0
                self.progressbar.configure(progress_color="#ff0000")
                info_text = wrapped_text.fill(f'Error: Parent / Child relations could not be fetched, deleted or posted to ProdDB API.\n{self.last_responseText}')
                print(f'>>> {info_text}')
                self.info_label.configure(text=info_text)
            else:
                self.api_status = 1
                self.progressbar.configure(progress_color="#007711")

                if self.operation_mode == 'Detector Assembly (CERN): DU' and allowed_VLQ and ((occupied_VLQ and confirmed == pos) or not occupied_VLQ):
                    # find all existing relations between this DU and its Modules, those are propagated to create new Slot -> Module relations
                    self.loading_wheel_A = threading.Thread(target=self.fetch_and_write_module_slots, args=(attribute_Vessel, attribute_Layer, attribute_Quadrant))
                    self.loading_wheel_A.start()
                    self.update_progressbar(self.loading_wheel_A)

    # Combobox page selection by pressing a button to go left or right (previous page / next page)
    def button_combobox_paginationButton_click(affected_cbx_shown_page, affected_cbx_page_label,
                                               affected_cbx_n_pages, affected_cbx_part,
                                               affected_cbx_possible_SNs, page_dir):
        if page_dir == 'L':
            affected_cbx_shown_page = max(affected_cbx_shown_page - 1, 1)
        elif page_dir == 'R':
            affected_cbx_shown_page = min(affected_cbx_shown_page + 1, affected_cbx_n_pages)
        else:
            raise NotImplementedError("Can only go left (L) or right (R) in pagination frame!")
        affected_cbx_page_label.configure(text=f"page {affected_cbx_shown_page}/{affected_cbx_n_pages}")
        affected_cbx_part.configure(values=affected_cbx_possible_SNs[affected_cbx_shown_page - 1])
    
    # control for Det Assembly: Child SN combobox page selection
    def button_combobox_child_paginationButtonLeft_click(self):
        self.cbx_chi_shown_page = max(self.cbx_chi_shown_page - 1, 1)
        self.combobox_child_paginationFrame_label.configure(text=f"page {self.cbx_chi_shown_page}/{self.cbx_chi_n_pages}")
        self.combobox_child.configure(values=self.possible_children_SNs_chunked[self.cbx_chi_shown_page - 1])

    def button_combobox_child_paginationButtonRight_click(self):
        self.cbx_chi_shown_page = min(self.cbx_chi_shown_page + 1, self.cbx_chi_n_pages)
        self.combobox_child_paginationFrame_label.configure(text=f"page {self.cbx_chi_shown_page}/{self.cbx_chi_n_pages}")
        self.combobox_child.configure(values=self.possible_children_SNs_chunked[self.cbx_chi_shown_page - 1])

    # control for FT: FT Child SN combobox page selection
    def button_combobox_ft_paginationButtonLeft_click(self):
        self.cbx_ft_shown_page = max(self.cbx_ft_shown_page - 1, 1)
        self.combobox_ft_paginationFrame_label.configure(text=f"page {self.cbx_ft_shown_page}/{self.cbx_ft_n_pages}")
        self.combobox_ft.configure(values=self.possible_ft_SNs_chunked[self.cbx_ft_shown_page - 1])

    def button_combobox_ft_paginationButtonRight_click(self):
        self.cbx_ft_shown_page = min(self.cbx_ft_shown_page + 1, self.cbx_ft_n_pages)
        self.combobox_ft_paginationFrame_label.configure(text=f"page {self.cbx_ft_shown_page}/{self.cbx_ft_n_pages}")
        self.combobox_ft.configure(values=self.possible_ft_SNs_chunked[self.cbx_ft_shown_page - 1])

    # control for MA: Module Parent SN combobox page selection
    def button_combobox_MA_mod_par_paginationButtonLeft_click(self):
        self.cbx_MA_mod_par_shown_page = max(self.cbx_MA_mod_par_shown_page - 1, 1)
        self.combobox_MA_mod_par_paginationFrame_label.configure(text=f"page {self.cbx_MA_mod_par_shown_page}/{self.cbx_MA_mod_par_n_pages}")
        self.combobox_MA_mod_par.configure(values=self.possible_MA_mod_par_SNs_chunked[self.cbx_MA_mod_par_shown_page - 1])

    def button_combobox_MA_mod_par_paginationButtonRight_click(self):
        self.cbx_MA_mod_par_shown_page = min(self.cbx_MA_mod_par_shown_page + 1, self.cbx_MA_mod_par_n_pages)
        self.combobox_MA_mod_par_paginationFrame_label.configure(text=f"page {self.cbx_MA_mod_par_shown_page}/{self.cbx_MA_mod_par_n_pages}")
        self.combobox_MA_mod_par.configure(values=self.possible_MA_mod_par_SNs_chunked[self.cbx_MA_mod_par_shown_page - 1])

    '''
    # this whole stuff needs to be refactored to not get crazy with every single new affected kind of part
    # control for MA: Hybrid HV Child SN combobox page selection
    def button_combobox_MA_HY_HV_chi_paginationButtonLeft_click(self):
        self.cbx_MA_HY_HV_chi_shown_page = max(self.cbx_MA_HY_HV_chi_shown_page - 1, 1)
        self.combobox_MA_HY_HV_chi_paginationFrame_label.configure(text=f"page {self.cbx_MA_HY_HV_chi_shown_page}/{self.cbx_MA_HY_HV_chi_n_pages}")
        self.combobox_MA_HY_HV_chi.configure(values=self.possible_MA_HY_HV_chi_SNs_chunked[self.cbx_MA_HY_HV_chi_shown_page - 1])

    def button_combobox_MA_HY_HV_chi_paginationButtonRight_click(self):
        self.cbx_MA_HY_HV_chi_shown_page = min(self.cbx_MA_HY_HV_chi_shown_page + 1, self.cbx_MA_HY_HV_chi_n_pages)
        self.combobox_MA_HY_HV_chi_paginationFrame_label.configure(text=f"page {self.cbx_MA_HY_HV_chi_shown_page}/{self.cbx_MA_HY_HV_chi_n_pages}")
        self.combobox_MA_HY_HV_chi.configure(values=self.possible_MA_HY_HV_chi_SNs_chunked[self.cbx_MA_HY_HV_chi_shown_page - 1])

    # control for MA: Hybrid LV Child SN combobox page selection
    def button_combobox_MA_HY_LV_chi__paginationButtonLeft_click(self):
        self.cbx_MA_HY_LV_chi__shown_page = max(self.cbx_MA_HY_LV_chi__shown_page - 1, 1)
        self.combobox_MA_HY_LV_chi__paginationFrame_label.configure(text=f"page {self.cbx_MA_HY_LV_chi__shown_page}/{self.cbx_MA_HY_LV_chi__n_pages}")
        self.combobox_MA_HY_LV_chi_.configure(values=self.possible_MA_HY_LV_chi__SNs_chunked[self.cbx_MA_HY_LV_chi__shown_page - 1])

    def button_combobox_MA_HY_LV_chi__paginationButtonRight_click(self):
        self.cbx_MA_HY_LV_chi__shown_page = min(self.cbx_MA_HY_LV_chi__shown_page + 1, self.cbx_MA_HY_LV_chi__n_pages)
        self.combobox_MA_HY_LV_chi__paginationFrame_label.configure(text=f"page {self.cbx_MA_HY_LV_chi__shown_page}/{self.cbx_MA_HY_LV_chi__n_pages}")
        self.combobox_MA_HY_LV_chi_.configure(values=self.possible_MA_HY_LV_chi__SNs_chunked[self.cbx_MA_HY_LV_chi_shown_page - 1])
    '''

    # control for Det Assembly: Parent SN combobox page selection
    def button_combobox_parent_paginationButtonLeft_click(self):
        self.cbx_par_shown_page = max(self.cbx_par_shown_page - 1, 1)
        self.combobox_parent_paginationFrame_label.configure(text=f"page {self.cbx_par_shown_page}/{self.cbx_par_n_pages}")
        self.combobox_parent.configure(values=self.possible_parents_SNs_chunked[self.cbx_par_shown_page - 1])

    def button_combobox_parent_paginationButtonRight_click(self):
        self.cbx_par_shown_page = min(self.cbx_par_shown_page + 1, self.cbx_par_n_pages)
        self.combobox_parent_paginationFrame_label.configure(text=f"page {self.cbx_par_shown_page}/{self.cbx_par_n_pages}")
        self.combobox_parent.configure(values=self.possible_parents_SNs_chunked[self.cbx_par_shown_page - 1])

    # control for Det Assembly: Parent Type combobox page selection
    def button_combobox_par_type_paginationButtonLeft_click(self):
        self.cbx_ptype_shown_page = max(self.cbx_ptype_shown_page - 1, 1)
        self.combobox_par_type_paginationFrame_label.configure(text=f"page {self.cbx_ptype_shown_page}/{self.cbx_ptype_n_pages}")
        self.combobox_par_type.configure(values=self.possible_par_types_chunked[self.cbx_ptype_shown_page - 1])

    def button_combobox_par_type_paginationButtonRight_click(self):
        self.cbx_ptype_shown_page = min(self.cbx_ptype_shown_page + 1, self.cbx_ptype_n_pages)
        self.combobox_par_type_paginationFrame_label.configure(text=f"page {self.cbx_ptype_shown_page}/{self.cbx_ptype_n_pages}")
        self.combobox_par_type.configure(values=self.possible_par_types_chunked[self.cbx_ptype_shown_page - 1])

    # control for Det Assembly: Child SN combobox page selection
    def button_combobox_chi_type_paginationButtonLeft_click(self):
        self.cbx_ctype_shown_page = max(self.cbx_ctype_shown_page - 1, 1)
        self.combobox_chi_type_paginationFrame_label.configure(text=f"page {self.cbx_ctype_shown_page}/{self.cbx_ctype_n_pages}")
        self.combobox_chi_type.configure(values=self.possible_chi_types_chunked[self.cbx_ctype_shown_page - 1])

    def button_combobox_chi_type_paginationButtonRight_click(self):
        self.cbx_ctype_shown_page = min(self.cbx_ctype_shown_page + 1, self.cbx_ctype_n_pages)
        self.combobox_chi_type_paginationFrame_label.configure(text=f"page {self.cbx_ctype_shown_page}/{self.cbx_ctype_n_pages}")
        self.combobox_chi_type.configure(values=self.possible_chi_types_chunked[self.cbx_ctype_shown_page - 1])

    def button_delete_connected_ft_event_click(self):
        if len(self.this_FT_relations_SLOT) > 0:
            try:
                for k in self.this_FT_relations_SLOT:
                    self.last_responseText = util.delete_parents(k['part']['part_id'])
            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                self.last_responseText = str(e)
            except ValueError as e:
                self.last_responseText = str(e)

            if self.last_responseText[:2] != '20':
                self.api_status = 0
                self.progressbar.configure(progress_color="#ff0000")
                info_text = wrapped_text.fill(f'Error: Existing FT relation could not be deleted (disconnected from slot) with ProdDB API.\n{self.last_responseText}')
                print(f'>>> {info_text}')
                self.info_label.configure(text=info_text)
            else:
                self.api_status = 1
                self.progressbar.configure(progress_color="#007711")
                self.info_label.configure(text=' ')
                self.this_FT_relations_SLOT = []
                self.delete_connected_ft_button.configure(state='disabled')
        
    def button_delete_clicked_event_click(self):
        if len(self.clicked_module) > 0:
            try:
                self.last_responseText = util.delete_parents(self.clicked_module['part']['part_id'])
            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                self.last_responseText = str(e)
            except ValueError as e:
                self.last_responseText = str(e)

            if self.last_responseText[:2] != '20':
                self.api_status = 0
                self.progressbar.configure(progress_color="#ff0000")
                info_text = wrapped_text.fill(f'Error: Existing module relation could not be deleted (unloaded) with ProdDB API.\n{self.last_responseText}')
                print(f'>>> {info_text}')
                self.info_label.configure(text=info_text)
            else:
                self.api_status = 1
                self.progressbar.configure(progress_color="#007711")

                # reload DU etc.
                self.displayedDUtype = "None"
                self.this_DU_relations_MODULE = []
                self.this_MODULE_relations_DU = []
                self.this_MODULE_relations_SLOT = []
                self.possible_parents = []
                self.possible_children = []
                self.slots = None
                self.partstree = None
                self.clicked_module = []
                self.inspect_clicked_button.configure(text=f'INSPECT CLICKED MODULE')
                self.inspect_clicked_button.configure(state='disabled')
                self.delete_clicked_button.configure(text=f'UNLOAD CLICKED MODULE')
                self.delete_clicked_button.configure(state='disabled')

                parentSNIn = self.combobox_parent.get()
                childSNIn = self.combobox_child.get()
                self.loading_wheel = threading.Thread(target=self.fetch_loaded_DU_and_display, args=(childSNIn, parentSNIn))
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)

    def button_delete_child_module_flex_event_click(self):
        pass

    def button_delete_child_HY_HV_event_click(self):
        pass

    def button_delete_child_HY_LV_event_click(self):
        pass
        
    def button_find_slot_event_click(self):
        self.info_label.configure(text=' ')
        v = self.slot_vessel_optionmenu.get()[-1]
        l = self.slot_layer_optionmenu.get()[-1]
        q = self.slot_quadrant_optionmenu.get()[-1]
        r = self.slot_glob_row_entry.get()
        m = self.slot_glob_mod_entry.get()
        self.ft_filter = ''

        self.combined_slot = f'V{v}:L{l}:Q{q}:R{r}:M{m}'
        self.this_SLOT_relations_FT = []

        for s in self.slots:
            if s['part_serial_number'] == self.combined_slot:
                self.slot_loc_DUtype_variable.set(s['SU_type'])
                self.slot_loc_row_variable.set(s['SU_Row'])
                self.slot_loc_mod_variable.set(s['SU_Module'])
                if v == 'D':
                    self.ft_gen_label_output.configure(text='20WFTC11F/20WFTS11F/20WFTG11F (old order cat 01--36), 20WFTG12F (new order cat 37--57)')
                    self.ft_filter = f'20WFTC11F/20WFTS11F/20WFTG11F/20WFTG12F+{s['FT_length_category']}'
                else:
                    self.ft_gen_label_output.configure(text='20WFTCM1F/20WFTSM1F/20WFTGM1F (future cat 01--62)')
                    self.ft_filter = f'20WFTCM1F/20WFTSM1F/20WFTGM1F+{s['FT_length_category']}'
                self.ft_type_label_output.configure(text=f'{s['FT_length_category']} ({s['FT_Length_mm']} mm)')
                
                # find all FTs that match this generation/category
                self.loading_wheel = threading.Thread(target=self.fetch_ft)
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)
                break
        else:
            info_text = wrapped_text.fill(f'Error: Your combination of Vessel, Layer, Quadrant, Global Row & Module does not exist in the slot table.')
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
    
    def button_inspect_child_event_click(self):
        childSNIn = self.combobox_child.get()
        if childSNIn != '- Select -':
            chi_partID = self.possible_children_partIDs[self.possible_children_SNs.index(childSNIn)]
            util.open_webbrowser_with_url(f'/viewparts/{chi_partID}')

    def button_inspect_clicked_event_click(self):
        if len(self.clicked_module) > 0:
            util.open_webbrowser_with_url(f'/viewparts/{self.clicked_module['part']['part_id']}')

    def button_inspect_parent_event_click(self):
        parentSNIn = self.combobox_parent.get()
        if parentSNIn != '- Select -':
            par_partID = self.possible_parents_partIDs[self.possible_parents_SNs.index(parentSNIn)]
            util.open_webbrowser_with_url(f'/viewparts/{par_partID}')

    def button_inspect_slot_event_click(self):
        if len(self.combined_slot) > 0:
            self.info_label.configure(text=' ')
            for s in self.slots:
                if s['part_serial_number'] == self.combined_slot:
                    par_partID = s['part_id']
                    break
            util.open_webbrowser_with_url(f'/viewparts/{par_partID}')
        else:
            info_text = wrapped_text.fill(f'Error: You first need to find the slot in the slot table to inspect its properties.')
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
            
    def button_inspect_ft_event_click(self):
        childSNIn = self.combobox_ft.get()
        if childSNIn != '- Select -':
            chi_partID = self.possible_ft_partIDs[self.possible_ft_SNs.index(childSNIn)]
            util.open_webbrowser_with_url(f'/viewparts/{chi_partID}')

    def button_inspect_parent_module_event_click(self):
        pass
        '''
        parentSNIn = self.combobox_parent_module.get()
        if parentSNIn != '- Select -':
            par_partID = self.possible_parent_mod_partIDs[self.possible_parent_mod_SNs.index(parentSNIn)]
            util.open_webbrowser_with_url(f'/viewparts/{par_partID}')
        '''

    def button_inspect_child_module_flex_event_click(self):
        pass

    def button_inspect_child_HY_HV_event_click(self):
        pass

    def button_inspect_child_HY_LV_event_click(self):
        pass

    # https://stackoverflow.com/a/23944658
    def button_mode_event_click(self, value):
        self.operation_mode = value
        self.displayedDUtype = "None"
        self.this_DU_relations_MODULE = []
        self.this_MODULE_relations_DU = []
        self.this_MODULE_relations_SLOT = []
        self.this_FT_relations_SLOT = []
        self.this_SLOT_relations_FT = []
        self.ft_filter = ''
        self.possible_parents = []
        self.possible_children = []
        self.possible_ft = []
        self.slots = None
        self.partstree = None
        self.clicked_module = []
        self.inspect_clicked_button.configure(text=f'INSPECT CLICKED MODULE')
        self.inspect_clicked_button.configure(state='disabled')
        self.delete_clicked_button.configure(text=f'UNLOAD CLICKED MODULE')
        self.delete_clicked_button.configure(state='disabled')

        self.par_type = None
        self.combobox_par_type.set("- Select -")
        self.chi_type = None
        self.combobox_chi_type.set("- Select -")
        self.chi_conn = None
        self.child_conn_optionmenu.set("All children")
        self.ft_conn = None
        self.ft_conn_optionmenu.set("All FTs")
        self.chi_manu = None
        self.combobox_child_manu.set("All manufacturers")

        self.progressbar.set(0)
        self.info_label.configure(text=' ')
        self.canvas.delete("all")
        if self.operation_mode == "Module Assembly":
            self.operation_mode_MA_button.configure(fg_color="#339941", hover_color="#228831")
            self.operation_mode_ML_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_DU_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_PEB_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_FT_button.configure(fg_color="#555555", hover_color="#444444")
            
            self.ma_frame.grid()
            self.combobox_frame.grid_remove()
            self.canvas_label.grid_remove()
            self.canvas.grid_remove()
            self.info_label.grid()
            self.ft_rel_frame.grid_remove()
            
        elif self.operation_mode  == "Module Loading":
            self.operation_mode_MA_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_ML_button.configure(fg_color="#339941", hover_color="#228831")
            self.operation_mode_DA_DU_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_PEB_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_FT_button.configure(fg_color="#555555", hover_color="#444444")

            self.ma_frame.grid_remove()
            self.combobox_frame.grid()
            self.canvas_label.grid()
            self.canvas.grid()
            self.info_label.grid()
            self.ft_rel_frame.grid_remove()

            self.combobox_par_type_label.grid()
            self.combobox_par_type_paginationFrame.grid()

            self.combobox_child_manu.grid()

            self.combobox_chi_type_paginationFrame.grid_remove()

            self.clicked_position_frame.grid()

            self.canvas_label.configure(text='Interactive canvas: accepting user click')
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.combobox_parent_T_label.configure(text="Parent Part Type: Detector Unit")
            self.combobox_child_T_label.configure(text="Child Part Type: Module")
            self.position_label.configure(text="Position (derived from canvas interaction)")
            self.position_variable.set("- automatic -")
            self.position_entry.configure(state="disabled")
            self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector Unit','Module'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode  == "Detector Assembly (CERN): DU":
            self.operation_mode_MA_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_ML_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_DU_button.configure(fg_color="#339941", hover_color="#228831")
            self.operation_mode_DA_PEB_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_FT_button.configure(fg_color="#555555", hover_color="#444444")

            self.ma_frame.grid_remove()
            self.combobox_frame.grid()
            self.canvas_label.grid()
            self.canvas.grid()
            self.info_label.grid()
            self.ft_rel_frame.grid_remove()

            self.combobox_par_type_label.grid_remove()
            self.combobox_par_type_paginationFrame.grid_remove()

            self.combobox_child_manu.grid_remove()

            self.possible_chi_types = ["All DU types"]+list(data.allDUs.keys())
            self.possible_chi_types_chunked = [self.possible_chi_types[i:i + self.n_items_to_show_in_cbx] for i in range(0, len(self.possible_chi_types), self.n_items_to_show_in_cbx)]
            self.cbx_ctype_n_pages = len(self.possible_chi_types_chunked)
            self.cbx_ctype_shown_page = 1
            self.combobox_chi_type_paginationFrame_label.configure(text=f"page {self.cbx_ctype_shown_page}/{self.cbx_ctype_n_pages}")
            self.combobox_chi_type.configure(values=self.possible_chi_types_chunked[0])

            self.combobox_chi_type_paginationFrame.grid()

            self.clicked_position_frame.grid()

            self.canvas_label.configure(text='Static canvas: served from database')
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.combobox_parent_T_label.configure(text="Parent Part Type: Detector")
            self.combobox_child_T_label.configure(text="Child Part Type: Detector Unit")
            self.position_label.configure(text="Position (type by hand)")
            self.position_variable.set("VxLyQz")
            self.position_entry.configure(state="normal")
            self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector','Detector Unit'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode  == "Detector Assembly (CERN): PEB":
            self.operation_mode_MA_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_ML_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_DU_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_PEB_button.configure(fg_color="#339941", hover_color="#228831")
            self.operation_mode_DA_FT_button.configure(fg_color="#555555", hover_color="#444444")

            self.ma_frame.grid_remove()
            self.combobox_frame.grid()
            self.canvas_label.grid_remove()
            self.canvas.grid_remove()
            self.info_label.grid()
            self.ft_rel_frame.grid_remove()

            self.combobox_par_type_label.grid_remove()
            self.combobox_par_type_paginationFrame.grid_remove()

            self.combobox_child_manu.grid_remove()

            self.possible_chi_types = ["All PEB types"]+data.allPEBs
            self.possible_chi_types_chunked = [self.possible_chi_types[i:i + self.n_items_to_show_in_cbx] for i in range(0, len(self.possible_chi_types), self.n_items_to_show_in_cbx)]
            self.cbx_ctype_n_pages = len(self.possible_chi_types_chunked)
            self.cbx_ctype_shown_page = 1
            self.combobox_chi_type_paginationFrame_label.configure(text=f"page {self.cbx_ctype_shown_page}/{self.cbx_ctype_n_pages}")
            self.combobox_chi_type.configure(values=self.possible_chi_types_chunked[0])

            self.combobox_chi_type_paginationFrame.grid()

            self.clicked_position_frame.grid_remove()

            self.canvas_label.configure(text='Static canvas: served from database')
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.combobox_parent_T_label.configure(text="Parent Part Type: Detector")
            self.combobox_child_T_label.configure(text="Child Part Type: PEB")
            self.position_label.configure(text="Position (type by hand)")
            self.position_variable.set("VxLyQz")
            self.position_entry.configure(state="normal")
            self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector','PEB'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode  == "Detector Assembly (CERN): FT":
            self.operation_mode_MA_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_ML_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_DU_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_PEB_button.configure(fg_color="#555555", hover_color="#444444")
            self.operation_mode_DA_FT_button.configure(fg_color="#339941", hover_color="#228831")

            self.ma_frame.grid_remove()
            self.combobox_frame.grid_remove()
            self.canvas_label.grid_remove()
            self.canvas.grid_remove()
            self.info_label.grid()
            self.ft_rel_frame.grid()

            self.slot_vessel_optionmenu.set("Vessel: 1")
            self.slot_layer_optionmenu.set("Layer: 0")
            self.slot_quadrant_optionmenu.set("Quadrant: 0")
            self.slot_loc_DUtype_variable.set('- automatic -')
            self.slot_loc_row_variable.set('- automatic -')
            self.slot_loc_mod_variable.set('- automatic -')
            self.slot_glob_row_variable.set('')
            self.slot_glob_mod_variable.set('')
            
            self.loading_wheel = threading.Thread(target=self.fetch_ft)
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def canvas_event_click(self, event, debug = False):
        self.clicked_module = []
        self.inspect_clicked_button.configure(text=f'INSPECT CLICKED MODULE')
        self.inspect_clicked_button.configure(state='disabled')
        self.delete_clicked_button.configure(text=f'UNLOAD CLICKED MODULE')
        self.delete_clicked_button.configure(state='disabled')
        info_text = ' '
        if self.operation_mode == 'Module Loading':
            if self.displayedDUtype != 'None':
                arrayOfModulesInDU = data.allDUs[self.displayedDUtype]
                alreadyConnectedModules = self.this_DU_relations_MODULE # list of relations, as in partstree
                if debug:
                    print(alreadyConnectedModules)
                alreadyUsedSlots = [entry['position'] for entry in alreadyConnectedModules]

                alreadyConnectedDUsForModule = self.this_MODULE_relations_DU
                alreadyConnectedSLOTsForModule = self.this_MODULE_relations_SLOT

                mouseInSomeMod = False
                mouseX = self.canvas.canvasx(event.x)
                mouseY = self.canvas.canvasy(event.y)
                for slot in arrayOfModulesInDU:
                    if util.isInSlot(slot, mouseX, mouseY):
                        mouseInSomeMod = True
                        possible_slot = slot['slot']
                        notAllowedSlot = False
                        if slot['slot'] in alreadyUsedSlots:
                            self.clicked_module = alreadyConnectedModules[alreadyUsedSlots.index(slot['slot'])]
                            self.inspect_clicked_button.configure(text=f'INSPECT CLICKED MODULE\n{self.clicked_module['part']['serial_number']}\n at {slot['slot']}')
                            self.inspect_clicked_button.configure(state='normal')
                            self.delete_clicked_button.configure(text=f'UNLOAD CLICKED MODULE\n{self.clicked_module['part']['serial_number']}\n at {slot['slot']}')
                            self.delete_clicked_button.configure(state='normal')
                            notAllowedSlot = True
                            self.canvas_place_rounded_rectangle(slot['x'], slot['y'], slot['w'], slot['h'], fill = data.fillColor_AlreadyLoadedSlot)
                        else:
                            self.canvas_place_rounded_rectangle(slot['x'], slot['y'], slot['w'], slot['h'], fill = data.fillColor_ActiveSlot)
                    else:
                        if slot['slot'] in alreadyUsedSlots:
                            self.canvas_place_rounded_rectangle(slot['x'], slot['y'], slot['w'], slot['h'], fill = data.fillColor_AlreadyLoadedSlot)
                        else:
                            self.canvas_place_rounded_rectangle(slot['x'], slot['y'], slot['w'], slot['h'], fill = data.fillColor_Slot)
                if len(alreadyConnectedDUsForModule) + len(alreadyConnectedSLOTsForModule) > 0:
                    self.position_variable.set("- automatic -")
                    info_text = 'Warning: Your selected child is already connected to some parent.\nSelect a different one, or disconnect the parents of this module by inspecting the Module.\nThere you can delete existing relations with the red trash button.'
                    print(f'>>> {info_text}')
                    if debug:
                        print('Existing connections to the following DU(s):',[DU['part_parent']['serial_number'] for DU in alreadyConnectedDUsForModule])
                        print('Existing connections to the following Slot(s):',[SLOT['part_parent']['serial_number'] for SLOT in alreadyConnectedSLOTsForModule])
                    self.info_label.configure(text=info_text)
                if not mouseInSomeMod:
                    self.position_variable.set("- automatic -")
                    info_text = info_text + '\n\nWarning: Place mouse in some module slot.' if info_text != ' ' else 'Warning: Place mouse in some module slot.'
                    print(f'>>> {info_text}')
                    self.info_label.configure(text=info_text)
                else:
                    if notAllowedSlot:
                        self.position_variable.set("- automatic -")
                        info_text = info_text + '\n\nWarning: This slot is already in use.\nSelect a different one, or disconnect the already loaded module by inspecting the DU.\nThere you can delete existing relations with the red trash button.' if info_text != ' ' else 'Warning: This slot is already in use.\nSelect a different one, or disconnect the already loaded module by inspecting the DU.\nThere you can delete existing relations with the red trash button.'
                        print(f'>>> {info_text}')
                        self.info_label.configure(text=info_text)
                    else:
                        if info_text == ' ':
                            self.position_variable.set(possible_slot)
                            self.info_label.configure(text=' ')
        elif self.operation_mode == 'Detector Assembly (CERN): DU':
            if self.displayedDUtype != 'None':
                arrayOfModulesInDU = data.allDUs[self.displayedDUtype]
                alreadyConnectedModules = self.this_DU_relations_MODULE # list of relations, as in partstree
                if debug:
                    print(alreadyConnectedModules)
                alreadyUsedSlots = [entry['position'] for entry in alreadyConnectedModules]
                mouseInSomeMod = False
                mouseX = self.canvas.canvasx(event.x)
                mouseY = self.canvas.canvasy(event.y)
                for slot in arrayOfModulesInDU:
                    if util.isInSlot(slot, mouseX, mouseY):
                        mouseInSomeMod = True
                        if slot['slot'] in alreadyUsedSlots:
                            self.clicked_module = alreadyConnectedModules[alreadyUsedSlots.index(slot['slot'])]
                            self.inspect_clicked_button.configure(text=f'INSPECT CLICKED MODULE\n{self.clicked_module['part']['serial_number']}\n at {slot['slot']}')
                            self.inspect_clicked_button.configure(state='normal')
                            self.delete_clicked_button.configure(text=f'UNLOAD CLICKED MODULE\n{self.clicked_module['part']['serial_number']}\n at {slot['slot']}')
                            self.delete_clicked_button.configure(state='normal')

    # https://stackoverflow.com/a/44100075
    def canvas_place_rounded_rectangle(self, x1, y1, width, height, radius=25, **kwargs):
        x2 = x1 + width
        y2 = y1 + height

        points = [x1+radius, y1,
                  x1+radius, y1,
                  x2-radius, y1,
                  x2-radius, y1,
                  x2, y1,
                  x2, y1+radius,
                  x2, y1+radius,
                  x2, y2-radius,
                  x2, y2-radius,
                  x2, y2,
                  x2-radius, y2,
                  x2-radius, y2,
                  x1+radius, y2,
                  x1+radius, y2,
                  x1, y2,
                  x1, y2-radius,
                  x1, y2-radius,
                  x1, y1+radius,
                  x1, y1+radius,
                  x1, y1]

        self.canvas.create_polygon(points, **kwargs, smooth=True)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_ft_conn_event(self, ft_conn):
        self.ft_conn = self.ft_conn_optionmenu.get()
        self.combobox_ft.set("- Select -")

        self.loading_wheel = threading.Thread(target=self.fetch_ft)
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def change_MA_parent_Mod_filter_event(self, foo):
        self.TODO = self.TODO.get()
        self.TODO = self.TODO.get()
        self.combobox_MA_mod_par.set("- Select -")

        self.loading_wheel = threading.Thread(target=self.fetch_MA_p_c)
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def change_MA_child_MF_filter_event(self, foo):
        self.TODO = self.TODO.get()
        self.TODO = self.TODO.get()
        self.combobox_MA_.set("- Select -")

        self.loading_wheel = threading.Thread(target=self.fetch_MA_p_c)
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def change_MA_child_HY_HV_filter_event(self, foo):
        # if cluster HV different from existing cluster LV
        # change not only HV but also LV cbx
        pass

    def change_MA_child_HY_LV_filter_event(self, foo):
        # if cluster LV different from existing cluster HV
        # change not only LV but also HV cbx
        pass


    # refactor those ===
    def change_MA_child_Module_loc_event(self, foo):
        pass

    def change_MA_child_Module_manu_event(self, foo):
        pass

    def change_MA_child_MF_conn_event(self, foo):
        pass

    def change_MA_child_MF_loc_event(self, foo):
        pass

    def change_MA_child_HL_conn_event(self, foo):
        pass

    def change_MA_child_HL_loc_event(self, foo):
        pass

    def change_MA_child_HL_cluster_event(self, foo):
        pass

    def change_MA_child_HR_conn_event(self, foo):
        pass

    def change_MA_child_HR_loc_event(self, foo):
        pass

    def change_MA_child_HR_cluster_event(self, foo):
        pass
    # === refactor those
            
    def change_child_conn_event(self, child_conn):
        self.chi_conn = self.child_conn_optionmenu.get()
        self.combobox_child.set("- Select -")

        if self.operation_mode == 'Module Loading':
            self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector Unit','Module'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == 'Detector Assembly (CERN): DU':
            self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector','Detector Unit'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == 'Detector Assembly (CERN): PEB':
            self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector','PEB'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def change_user_event(self, selected_user: str):
        if selected_user == 'None':
            self.user = None
        elif selected_user == 'new...':
            # authenticate as user
            try:
                self.authenticate_user()
            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                self.last_responseText = str(e)
            except ValueError as e:
                self.last_responseText = str(e)

            if self.last_responseText[:2] != '20':
                self.api_status = 0
                self.progressbar.configure(progress_color="#ff0000")
                info_text = wrapped_text.fill(f'Error: New user could not be authenticated.\n{self.last_responseText}')
                print(f'>>> {info_text}')
                self.info_label.configure(text=info_text)
            else:
                self.api_status = 1
                self.progressbar.configure(progress_color="#007711")
        else:
            self.user = selected_user

    def combobox_child_manu_event(self, child_manu):
        self.chi_manu = self.combobox_child_manu.get()
        self.combobox_child.set("- Select -")

        self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector Unit','Module'))
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def combobox_par_type_event_select(self, par_type):
        self.par_type = self.combobox_par_type.get()
        self.combobox_parent.set("- Select -")

        self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector Unit','Module'))
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def combobox_chi_type_event_select(self, chi_type):
        # this is relevant for child = DU, and you want to specify
        # which DU type shall be shown
        # from the children, select those that have the type in their SN
        # == OLD ==: for PEBs, PEB type is an attribute and not part of SN
        # NEW: for PEBs, PEB type is now also part of the SN!
        self.chi_type = self.combobox_chi_type.get()
        self.combobox_child.set("- Select -")

        if self.operation_mode == 'Detector Assembly (CERN): DU':
            self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector','Detector Unit'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == 'Detector Assembly (CERN): PEB':
            self.loading_wheel = threading.Thread(target=self.fetch_p_c, args=('Detector','PEB'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def combobox_ft_event_select(self, unused_var_to_please_python):
        self.this_FT_relations_SLOT = []
        ftSNIn = self.combobox_ft.get()
        if ftSNIn != '- Select -':
            self.loading_wheel = threading.Thread(target=self.fetch_loaded_FT, args=(ftSNIn,))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def combobox_MA_mod_event_select(self, unused_var_to_please_python):
        pass

    def combobox_MA_MF_event_select(self, unused_var_to_please_python):
        pass

    def combobox_MA_HY_HV_event_select(self, unused_var_to_please_python):
        pass

    def combobox_MA_HY_LV_event_select(self, unused_var_to_please_python):
        pass

    def combobox_p_c_event_select(self, unused_var_to_please_python):
        self.displayedDUtype = "None"
        self.displayed_PEB_type = "None"
        self.this_DU_relations_MODULE = []
        self.this_MODULE_relations_DU = []
        self.this_MODULE_relations_SLOT = []
        self.slots = None
        self.partstree = None

        parentSNIn = self.combobox_parent.get()
        childSNIn = self.combobox_child.get()
        if self.operation_mode == 'Module Loading':
            parentNameIn = 'Detector Unit'
            childNameIn = 'Module'
            self.canvas.delete("all")
            if parentSNIn != '- Select -':
                self.loading_wheel = threading.Thread(target=self.fetch_loaded_DU_and_display, args=(childSNIn, parentSNIn))
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == 'Detector Assembly (CERN): DU':
            parentNameIn = 'Detector'
            childNameIn = 'Detector Unit'
            self.canvas.delete("all")
            if childSNIn != '- Select -':
                self.loading_wheel = threading.Thread(target=self.fetch_loaded_DU_and_display, args=(childSNIn, parentSNIn))
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == 'Detector Assembly (CERN): PEB':
            parentNameIn = 'Detector'
            childNameIn = 'PEB'
            self.canvas.delete("all")
            if childSNIn != '- Select -':
                self.loading_wheel = threading.Thread(target=self.fetch_loaded_PEB, args=(childSNIn, parentSNIn))
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)

    def delete_old_and_post_new_slots_for_loaded_modules(self, V, L, Q):
        for entry in self.this_DU_relations_MODULE:
            try:
                parents_of_child_module, self.responseText = util.get_parents(entry['part']['part_id'])
            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                self.last_responseText = str(e)
            except ValueError as e:
                self.last_responseText = str(e)

            if self.last_responseText[:2] != '20':
                self.api_status = 0
                self.progressbar.configure(progress_color="#ff0000")
                info_text = wrapped_text.fill(f'Error: Parents could not be loaded from ProdDB API.\n{self.last_responseText}')
                print(f'>>> {info_text}')
                self.info_label.configure(text=info_text)
            else:
                self.api_status = 1
                self.progressbar.configure(progress_color="#007711")

                for r in parents_of_child_module:
                    if str(r['part_parent']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['Slot']):
                        try:
                            self.last_responseText = api.delete_information(f'/partstreedelete/{r['record_id']}/')
                        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                            self.last_responseText = str(e)
                        except ValueError as e:
                            self.last_responseText = str(e)

                        if self.last_responseText[:2] != '20':
                            self.api_status = 0
                            self.progressbar.configure(progress_color="#ff0000")
                            info_text = wrapped_text.fill(f'Error: Record could not be deleted from ProdDB API.\n{self.last_responseText}')
                            print(f'>>> {info_text}')
                            self.info_label.configure(text=info_text)
                        else:
                            self.api_status = 1
                            self.progressbar.configure(progress_color="#007711")
                if self.api_status == 1:
                    attribute_SU_r = entry['position'].split('R').pop().split('M')[0]
                    attribute_SU_m = entry['position'].split('M').pop()
                    for sl in self.slots:
                        if (sl['Vessel'] == V \
                            and sl['Layer'] == L \
                            and sl['Quadrant'] == Q \
                            and sl['SU_type'] == self.displayedDUtype \
                            and sl['SU_Row'] == attribute_SU_r \
                            and sl['SU_Module'] == attribute_SU_m):
                            # found a slot :-)
                            if self.user != 'None' and self.user != 'new...':
                                part_tree = {
                                    'position': '',
                                    'is_record_deleted': 'F',
                                    'part': entry['part']['part_id'],
                                    'part_parent': sl['part_id'],
                                    'record_insertion_user': self.user,
                                }
                            else:
                                part_tree = {
                                    'position': '',
                                    'is_record_deleted': 'F',
                                    'part': entry['part']['part_id'],
                                    'part_parent': sl['part_id'],
                                }
                            try:
                                self.last_responseText = api.post_information('/partstreelist', part_tree)
                            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                                self.last_responseText = str(e)
                            except ValueError as e:
                                self.last_responseText = str(e)

                            if self.last_responseText[:2] != '20':
                                self.api_status = 0
                                self.progressbar.configure(progress_color="#ff0000")
                                info_text = wrapped_text.fill(f'Error: Parent / Child relation could not be patched to ProdDB API.\n{self.last_responseText}')
                                print(f'>>> {info_text}')
                                self.info_label.configure(text=info_text)
                            else:
                                self.api_status = 1
                                self.progressbar.configure(progress_color="#007711")

    def exit(self):
        self.destroy()

    def fetch_and_write_module_slots(self, attribute_Vessel, attribute_Layer, attribute_Quadrant, debug = False):
        if self.api_status == 1:
            if debug:
                if len(self.this_DU_relations_MODULE) == 0:
                    info_text = wrapped_text.fill(f'Warning: There is no relation to a module for this DU.')
                    print(f'>>> {info_text}')
                    self.info_label.configure(text=info_text)
            self.fetch_slots()
            self.delete_old_and_post_new_slots_for_loaded_modules(attribute_Vessel, attribute_Layer, attribute_Quadrant)

    def fetch_loaded_DU_and_display(self, childSNIn, parentSNIn, debug = False):
        if self.operation_mode == 'Module Loading':
            DU_SN = parentSNIn
            parentDU_partID = self.possible_parents_partIDs[self.possible_parents_SNs.index(DU_SN)]
            if childSNIn != '- Select -':
                childModule_partID = self.possible_children_partIDs[self.possible_children_SNs.index(childSNIn)]
                # fetch possibly existing parents of module to make sure we don't load it again somewhere else
                try:
                    self.module_parents, self.last_responseText = util.get_parents(childModule_partID)
                except(requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                    self.module_parents = []
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.module_parents = []
                    self.last_responseText = str(e)

                if self.last_responseText[:3] != '200':
                    self.api_status = 0
                    self.progressbar.configure(progress_color="#ff0000")
                    info_text = wrapped_text.fill(f'Error: Module relations could not be loaded from ProdDB API.\n{self.last_responseText}')
                    print(f'>>> {info_text}')
                    self.info_label.configure(text=info_text)
                    self.this_MODULE_relations_DU = []
                    self.this_MODULE_relations_SLOT = []
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color="#007711")
                    for r in self.module_parents:
                        if debug:
                            print(r)
                        if str(r['part_parent']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['Detector Unit']):
                            self.this_MODULE_relations_DU.append(r)
                        if str(r['part_parent']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['Slot']):
                            self.this_MODULE_relations_SLOT.append(r)
        elif self.operation_mode == 'Detector Assembly (CERN): DU':
            DU_SN = childSNIn
            parentDU_partID = self.possible_children_partIDs[self.possible_children_SNs.index(DU_SN)]

        self.duAlreadyPlacedText = self.canvas.create_text(380, 525, text=f'', anchor='nw', fill=data.fillColor_SU_Text)
        self.clicked_module = []
        for key in data.allDUs.keys():
            if key in DU_SN:
                self.displayedDUtype = key
                self.info_label.configure(text=' ')
                self.canvas.create_rectangle(40, 40, 360, 540, fill=data.fillColor_SU)
                for mod in data.allDUs[self.displayedDUtype]:
                    self.canvas_place_rounded_rectangle(mod['x'], mod['y'], mod['w'], mod['h'], fill = data.fillColor_Slot)
                self.canvas.create_text(140, 475, text=self.displayedDUtype, anchor='nw', font=('Arial',50), fill=data.fillColor_SU_Text)
                self.canvas.create_text(145, 20, text='Connector side', anchor='nw', fill=data.fillColor_SU_Text)
                self.canvas.create_text(145, 545, text='Capacitor side', anchor='nw', fill=data.fillColor_SU_Text)
                if 'FI10' in DU_SN:
                    self.canvas.create_text(360, 290, text='Connector side', anchor='nw', fill=data.fillColor_SU_Text, angle=90)
                    self.canvas.create_text(20, 290, text='Capacitor side', anchor='nw', fill=data.fillColor_SU_Text, angle=90)
                # get the children of that DU, interested in Modules only here
                try:
                    self.partstree, self.last_responseText = util.get_children(parentDU_partID)
                    detector, self.last_responseText = util.get_parents(parentDU_partID)
                except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                    self.partstree = []
                    detector = []
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.partstree = []
                    detector = []
                    self.last_responseText = str(e)

                if self.last_responseText[:3] != '200':
                    self.api_status = 0
                    self.progressbar.configure(progress_color="#ff0000")
                    info_text = wrapped_text.fill(f'Error: DU relations could not be loaded from ProdDB API.\n{self.last_responseText}')
                    print(f'>>> {info_text}')
                    self.info_label.configure(text=info_text)
                    self.this_DU_relations_MODULE = []
                    break
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color="#007711")
                    self.this_DU_fully_loaded = False
                    for r in self.partstree:
                        if str(r['part_parent']['part_id']) == str(parentDU_partID):
                            if str(r['part']['kind_of_part']['kind_of_part_id']) == str(data.KoPID_from_partKoPName['Module']):
                                self.this_DU_relations_MODULE.append(r)
                                # make the corresponding slot blue if already in use, white if not used
                                for mod in data.allDUs[self.displayedDUtype]:
                                    if mod['slot'] == str(r['position']):
                                        self.canvas_place_rounded_rectangle(mod['x'], mod['y'], mod['w'], mod['h'], fill=data.fillColor_AlreadyLoadedSlot)
                                        self.clicked_module = r['part']
                    if len(self.this_DU_relations_MODULE) == len(data.allDUs[self.displayedDUtype]):
                        self.canvas.create_text(380, 475, text='Fully loaded DU', anchor='nw', fill=data.fillColor_SU_Text)
                    if detector != []:
                        # this DU was already placed somewhere in the detector!!
                        for r in detector:
                            self.duAlreadyPlacedText = self.canvas.create_text(380, 525, text=f'Already placed at:\n{r['position']}', anchor='nw', fill=data.fillColor_SU_Text)
                    break
        else:
            info_text = 'Warning: Detector Unit type could not be retrieved from DU SN.'
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)

    def fetch_loaded_FT(self, ftSNIn, debug = False):
        FT_partID = self.possible_ft_partIDs[self.possible_ft_SNs.index(ftSNIn)]
        if debug:
            print(ftSNIn)
            print(FT_partID)
            print(self.possible_ft)
        self.info_label.configure(text=' ')
        self.delete_connected_ft_button.configure(state='disabled')
        try:
            ft_par, self.last_responseText = util.get_parents(FT_partID, ofKind = 'Slot')
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            ft_par = []
            self.last_responseText = str(e)
        except ValueError as e:
            ft_par = []
            
            self.last_responseText = str(e)

        if self.last_responseText[:3] != '200':
            self.api_status = 0
            self.progressbar.configure(progress_color="#ff0000")
            info_text = wrapped_text.fill(f'Error: FT relations could not be loaded from ProdDB API.\n{self.last_responseText}')
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
            self.this_FT_relations_SLOT = []
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color="#007711")

            if ft_par != []:
                # this FT is already connected to some slot!!
                for r in ft_par:
                    if debug:
                        print(r)
                    info_text = f'Info: This FT is already connected to a slot: {r['part_parent']['serial_number']}.'
                    print(f'>>> {info_text}')
                    self.info_label.configure(text=info_text)
                    self.this_FT_relations_SLOT.append(r)
                    self.delete_connected_ft_button.configure(state='enabled')                
        
    def fetch_loaded_PEB(self, childSNIn, parentSNIn, debug = False):
        PEB_SN = childSNIn
        PEB_partID = self.possible_children_partIDs[self.possible_children_SNs.index(PEB_SN)]
        if debug:
            print(childSNIn)
            print(PEB_partID)
            print(self.possible_children)
        # == OLD ==: PEB type used to be only an attribute
        #self.displayed_PEB_type = self.possible_children[self.possible_children_SNs.index(PEB_SN)]['Type']
        for key in data.allPEBs:
            if key in PEB_SN:
                self.displayed_PEB_type = key
                self.info_label.configure(text=' ')

                # find out if this PEB is already placed somewhere
                info_text = ' '
                self.info_label.configure(text=info_text)
                try:
                    detector, self.last_responseText = util.get_parents(PEB_partID)
                except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                    detector = []
                    self.last_responseText = str(e)
                except ValueError as e:
                    detector = []
                    self.last_responseText = str(e)
        
                if self.last_responseText[:3] != '200':
                    self.api_status = 0
                    self.progressbar.configure(progress_color="#ff0000")
                    info_text = wrapped_text.fill(f'Error: PEB relations could not be loaded from ProdDB API.\n{self.last_responseText}')
                    print(f'>>> {info_text}')
                    self.info_label.configure(text=info_text)
                    break
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color="#007711")
        
                    if detector != []:
                        # this PEB was already placed somewhere in the detector!!
                        for r in detector:
                            info_text = f'Info: This PEB is already mounted to the parent detector, at {r['position']}.'
                            print(f'>>> {info_text}')
                            self.info_label.configure(text=info_text)
                    break
        else:
            info_text = 'Warning: PEB type could not be retrieved from PEB SN.'
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)

    def fetch_ft(self):
        try:
            self.fetch_slots()
            self.possible_ft, self.last_responseText = util.get_relevant_parts('FT')
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            self.possible_ft = []
            self.last_responseText = str(e)
        except ValueError as e:
            self.possible_ft = []
            self.last_responseText = str(e)

        if self.last_responseText[:3] != '200':
            self.api_status = 0
            self.progressbar.configure(progress_color="#ff0000")
            info_text = wrapped_text.fill(f'Error: Slots / FT could not be loaded from ProdDB API.\n{self.last_responseText}')
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color="#007711")

            if self.ft_filter != '':
                gen = self.ft_filter.split('+')[0].split('/') # multiple generations
                cat = self.ft_filter[-2:] # the last two chars make the category

                self.possible_ft = [pft for pft in self.possible_ft if any(gen_ in pft['serial_number'] for gen_ in gen) and int(pft['serial_number'][9:11]) == int(cat)]

            # do the most expensive part last (when easy filters on existing data have already been applied)
            # expensive meaning need to make calls to the API for each part in the list that survived the previous cuts
            if self.ft_conn != None and self.ft_conn != 'All FTs':
                self.possible_ft = [pp for pp in self.possible_ft if (len(util.get_parents(pp['part_id'], ofKind = 'Slot')[0])) == 0]
            self.possible_ft_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(self.possible_ft)
            self.possible_ft_SNs = [entry[0] for entry in self.possible_ft_SNs_and_partIDs]
            self.possible_ft_SNs_chunked = [self.possible_ft_SNs[i:i + self.n_items_to_show_in_cbx] for i in range(0, len(self.possible_ft_SNs), self.n_items_to_show_in_cbx)]
            self.possible_ft_partIDs = [entry[1] for entry in self.possible_ft_SNs_and_partIDs]
            self.cbx_chi_n_pages = len(self.possible_ft_SNs_chunked)
            self.cbx_chi_shown_page = min(1, self.cbx_ft_n_pages)
            self.combobox_child_paginationFrame_label.configure(text=f"page {self.cbx_ft_shown_page}/{self.cbx_ft_n_pages}")
            if len(self.possible_ft) > 0:
                self.combobox_ft.configure(values=self.possible_ft_SNs_chunked[0])
            else:
                self.combobox_ft.configure(values=[])
                self.combobox_ft.set("- Select -")

    def fetch_MA_p_c(self):
        pass
        
    def fetch_p_c(self, p, c):
        try:
            self.possible_parents, self.last_responseText = util.get_relevant_parts(p)
            self.possible_children, self.last_responseText = util.get_relevant_parts(c)
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            self.possible_parents = []
            self.possible_children = []
            self.last_responseText = str(e)
        except ValueError as e:
            self.possible_parents = []
            self.possible_children = []
            self.last_responseText = str(e)

        if self.last_responseText[:3] != '200':
            self.api_status = 0
            self.progressbar.configure(progress_color="#ff0000")
            info_text = wrapped_text.fill(f'Error: Parents / Children could not be loaded from ProdDB API.\n{self.last_responseText}')
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color="#007711")

            if p == 'Detector Unit' and c == 'Module':
                if self.par_type != None and self.par_type != 'All DU types':
                    self.possible_parents = [pp for pp in self.possible_parents if self.par_type in pp['serial_number']]
                if self.chi_manu != None and self.chi_manu != 'All manufacturers':
                    self.possible_children = [pp for pp in self.possible_children if self.chi_manu == str(pp['manufacturer']['manufacturer_name'])]

            elif p == 'Detector' and c == 'Detector Unit':
                if self.chi_type != None and self.chi_type != 'All DU types':
                    self.possible_children = [pc for pc in self.possible_children if self.chi_type in pc['serial_number']]

            elif p == 'Detector' and c == 'PEB':
                if self.chi_type != None and self.chi_type != 'All PEB types':
                    self.possible_children = [pc for pc in self.possible_children if self.chi_type in pc['Type']]

            # do the most expensive part last (when easy filters on existing data have already been applied)
            # expensive meaning need to make calls to the API for each part in the list that survived the previous cuts
            if self.chi_conn != None and self.chi_conn != 'All children':
                self.possible_children = [pp for pp in self.possible_children if (len(util.get_parents(pp['part_id'])[0])) == 0]

            self.possible_parents_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(self.possible_parents)
            self.possible_children_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(self.possible_children)
            self.possible_parents_SNs = [entry[0] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_parents_SNs_chunked = [self.possible_parents_SNs[i:i + self.n_items_to_show_in_cbx] for i in range(0, len(self.possible_parents_SNs), self.n_items_to_show_in_cbx)]
            self.possible_children_SNs = [entry[0] for entry in self.possible_children_SNs_and_partIDs]
            self.possible_children_SNs_chunked = [self.possible_children_SNs[i:i + self.n_items_to_show_in_cbx] for i in range(0, len(self.possible_children_SNs), self.n_items_to_show_in_cbx)]
            self.possible_parents_partIDs = [entry[1] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_children_partIDs = [entry[1] for entry in self.possible_children_SNs_and_partIDs]
            self.cbx_par_n_pages = len(self.possible_parents_SNs_chunked)
            self.cbx_chi_n_pages = len(self.possible_children_SNs_chunked)
            self.cbx_par_shown_page = min(1, self.cbx_par_n_pages)
            self.cbx_chi_shown_page = min(1, self.cbx_chi_n_pages)
            self.combobox_parent_paginationFrame_label.configure(text=f"page {self.cbx_par_shown_page}/{self.cbx_par_n_pages}")
            self.combobox_child_paginationFrame_label.configure(text=f"page {self.cbx_chi_shown_page}/{self.cbx_chi_n_pages}")
            if self.cbx_par_n_pages > 0:
                self.combobox_parent.configure(values=self.possible_parents_SNs_chunked[0])
            else:
                self.combobox_parent.configure(values=[])
                self.combobox_parent.set("- Select -")
            if self.cbx_chi_n_pages > 0:
                self.combobox_child.configure(values=self.possible_children_SNs_chunked[0])
            else:
                self.combobox_child.configure(values=[])
                self.combobox_child.set("- Select -")

    def fetch_slots(self):
        try:
            self.slots, self.last_responseText = util.get_relevant_parts('Slot', getFullAttributes = True, useLocal = True)
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            self.slots = None
            self.last_responseText = str(e)
        except ValueError as e:
            self.slots = None
            self.last_responseText = str(e)

        if self.last_responseText[:3] != '200':
            self.api_status = 0
            self.progressbar.configure(progress_color="#ff0000")
            info_text = wrapped_text.fill(f'Error: Slots could not be loaded from ProdDB API.\n{self.last_responseText}')
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color="#007711")


    def help(self):
        if self.help_window is None or not self.help_window.winfo_exists():
            self.help_window = ToplevelWindow(self)  # create window if its None or destroyed
        else:
            self.help_window.focus()  # if window exists focus it

    def update_progressbar(self, thread):
        if thread.is_alive():
            # update progressbar
            self.progressbar.step()
            self.after(250, self.update_progressbar, thread)
            self.progressbar.configure(progress_color="#BBAA00")
        else:
            self.progressbar.set(1)
            if self.api_status == 0:
                self.progressbar.configure(progress_color="#ff0000")
            else:
                self.progressbar.configure(progress_color="#007711")

if __name__ == "__main__":
    app = App()
    app.mainloop()
