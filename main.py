import threading
import time
import tkinter

import customtkinter
import requests
from PIL import Image

import api
import data
import util

customtkinter.set_appearance_mode(
    "System"
)  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme(
    "blue"
)  # Themes: "blue" (standard), "green", "dark-blue"

wrapped_text = util.CustomTextWrapper(width=90)


class ToplevelWindow(customtkinter.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("HGTD Tools - Help")
        self.geometry("1000x300")

        self.textbox = customtkinter.CTkTextbox(master=self, width=400, wrap="word")
        self.textbox.pack(fill="both", expand=True, padx=20, pady=20)
        self.textbox.insert(
            "0.0",
            "Each Support Unit is oriented in such a way that when looking at its face, the module connectors are at the top (or on the right), and module capacitors are on the bottom (or on the left).\nUser actions (loading sites / assembly at CERN): First step at a loading site: fill the Detector Unit with modules, click on the canvas to select the correct position and use the button below. Once finished, move to the assembly step at CERN and enter the position manually when connecting a Detector Unit with the Detector (VxLxQx). Note: A back Detector Unit can only be on layer 1 or 2, a front Detector Unit can only be on layer 0 or 3.\nToo long dropdown selections are split into chunks, you can select which chunk shall be shown with the arrow buttons. This is to ensure compatibility with more operating systems.\n\nHint: manufacturers for modules should be interpreted as assembly sites. This field is taken live from all manufacturers available in the database and hence does not necessarily agree with the six defined assembly sites.\n\nHint 2: Blue option menus contain static choices (=hardcoded), while grey comboboxes are retrieved dynamically (=from the DB).\n\nHint 3: if you do not pre-select children by trivial attributes like manufacturer or type, the option to choose only not-yet-connected children will be slow, as is has to check from the full set of children. Pre-select with the other options to speed this process up.",
        )
        self.textbox.configure(state="disabled")


class AuthenticateWindow(customtkinter.CTkToplevel):
    def __init__(self, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("HGTD Tools - Authenticate new user")
        self.geometry("900x300")

        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure((0, 1), weight=1)

        self.callback = callback

        self.frame_entries = customtkinter.CTkFrame(self, corner_radius=0)
        self.frame_entries.grid(row=0, column=0, rowspan=3, columnspan=3, sticky="nsew")

        self.label_auth_info = customtkinter.CTkLabel(
            self.frame_entries,
            text="Type in your user data to authenticate as a new user of HGTD-Tools.",
        )
        self.label_auth_info.grid(row=0, column=0, padx=10, pady=10, columnspan=3)

        self.username_variable = customtkinter.StringVar(value="")
        self.username_entry = customtkinter.CTkEntry(
            self.frame_entries, textvariable=self.username_variable, state="normal"
        )
        self.username_entry.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.label_username = customtkinter.CTkLabel(
            self.frame_entries, text="Username"
        )
        self.label_username.grid(row=2, column=0, padx=10, pady=10)

        self.password_variable = customtkinter.StringVar(value="")
        self.password_entry = customtkinter.CTkEntry(
            self.frame_entries,
            textvariable=self.password_variable,
            state="normal",
            show="*",
        )
        self.password_entry.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.label_password = customtkinter.CTkLabel(
            self.frame_entries, text="Password"
        )
        self.label_password.grid(row=2, column=1, padx=10, pady=10)

        self.totp_variable = customtkinter.StringVar(value="")
        self.totp_entry = customtkinter.CTkEntry(
            self.frame_entries, textvariable=self.totp_variable, state="normal"
        )
        self.totp_entry.grid(row=1, column=2, padx=10, pady=10, sticky="nsew")
        self.label_totp = customtkinter.CTkLabel(
            self.frame_entries,
            text="2FA 6-digit code, if configured (leave empty if you are not using 2FA yet)",
        )
        self.label_totp.grid(row=2, column=2, padx=10, pady=10)

        self.button_auth = customtkinter.CTkButton(
            self.frame_entries, text="Authenticate me!", command=self.auth
        )
        self.button_auth.grid(row=3, column=1, padx=10, pady=10)

        self.auth_user, self.last_responseText = None, None

    def auth(self):
        try:
            # this authentication method survives for as long as the GUI is open
            self.auth_user, self.last_responseText = api.get_user(
                self.username_variable.get(),
                self.password_variable.get(),
                self.totp_variable.get(),
            )
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            self.last_responseText = str(e)
        except ValueError as e:
            self.last_responseText = str(e)

        self.callback(
            self.auth_user, self.last_responseText
        )  # send back to the other class.
        self.destroy()


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # configure window
        self.title("HGTD Tools")
        self.geometry(f"{1500}x{1000}")
        icon = tkinter.PhotoImage(file="windowIcon.png")
        self.wm_iconbitmap()
        self.iconphoto(True, icon)

        self.n_items_to_show_in_cbx = 16
        # configure grid layout
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure((0, 1), weight=1)

        # create sidebar frame with widgets
        self.frame_sidebar_left = customtkinter.CTkFrame(self, corner_radius=0)
        self.frame_sidebar_left.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.frame_sidebar_left.grid_columnconfigure((0, 1), weight=1)
        self.frame_sidebar_left.grid_rowconfigure(5, weight=1)

        # fill sidebar
        self.label_logo = customtkinter.CTkLabel(
            self.frame_sidebar_left,
            text="HGTD Tools",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        )
        self.label_logo.grid(row=0, column=0, padx=20, pady=(20, 5), columnspan=2)
        self.my_version = "1.9.0"
        self.version_full_text = (
            f"v{self.my_version} - January 2026\nAnnika Stein (JGU Mainz)"
        )
        self.label_credits = customtkinter.CTkLabel(
            self.frame_sidebar_left, text=self.version_full_text
        )
        self.label_credits.grid(row=1, column=0, padx=20, pady=5, columnspan=2)

        self.label_progress = customtkinter.CTkLabel(
            self.frame_sidebar_left, text="API Request Status"
        )
        self.label_progress.grid(row=2, column=0, padx=20, pady=5, columnspan=2)
        self.progressbar = customtkinter.CTkProgressBar(
            self.frame_sidebar_left,
            orientation="horizontal",
            progress_color=data.progress_color_OK,
        )
        self.progressbar.grid(row=3, column=0, padx=20, pady=5, columnspan=2)
        self.progressbar.set(1)

        # buttons to select use case of the tool
        self.frame_operation_mode = customtkinter.CTkFrame(self.frame_sidebar_left)
        self.frame_operation_mode.grid(
            row=4, column=0, padx=5, pady=(20, 5), sticky="nsew", columnspan=2
        )
        self.frame_operation_mode.grid_columnconfigure((0, 1), weight=1)
        self.operation_mode = "Module Assembly"  # default

        self.label_operation_mode = customtkinter.CTkLabel(
            self.frame_operation_mode,
            text="Operation Mode",
            font=customtkinter.CTkFont(size=16, weight="bold"),
        )
        self.label_operation_mode.grid(row=0, column=0, padx=20, pady=5, columnspan=2)

        self.button_operation_mode_MA = customtkinter.CTkButton(
            self.frame_operation_mode,
            text="Module Assembly",
            command=lambda: self.button_mode_event_click("Module Assembly"),
            fg_color=data.fg_color_standard_but_active,
            hover_color=data.hover_color_standard_but_active,
        )
        self.button_operation_mode_MA.grid(
            row=1, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        self.button_operation_mode_ML = customtkinter.CTkButton(
            self.frame_operation_mode,
            text="Module Loading",
            command=lambda: self.button_mode_event_click("Module Loading"),
            fg_color=data.fg_color_standard_but_inactive,
            hover_color=data.hover_color_standard_but_inactive,
        )
        self.button_operation_mode_ML.grid(
            row=2, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        self.button_operation_mode_DA_DU = customtkinter.CTkButton(
            self.frame_operation_mode,
            text="Detector Assembly (CERN): DU",
            command=lambda: self.button_mode_event_click(
                "Detector Assembly (CERN): DU"
            ),
            fg_color=data.fg_color_standard_but_inactive,
            hover_color=data.hover_color_standard_but_inactive,
        )
        self.button_operation_mode_DA_DU.grid(
            row=3, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        self.button_operation_mode_DA_PEB = customtkinter.CTkButton(
            self.frame_operation_mode,
            text="Detector Assembly (CERN): PEB",
            command=lambda: self.button_mode_event_click(
                "Detector Assembly (CERN): PEB"
            ),
            fg_color=data.fg_color_standard_but_inactive,
            hover_color=data.hover_color_standard_but_inactive,
        )
        self.button_operation_mode_DA_PEB.grid(
            row=4, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        self.button_operation_mode_DA_FT = customtkinter.CTkButton(
            self.frame_operation_mode,
            text="Detector Assembly (CERN): FT",
            command=lambda: self.button_mode_event_click(
                "Detector Assembly (CERN): FT"
            ),
            fg_color=data.fg_color_standard_but_inactive,
            hover_color=data.hover_color_standard_but_inactive,
        )
        self.button_operation_mode_DA_FT.grid(
            row=5, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        # buttons to go to external useful pages
        self.frame_useful_links = customtkinter.CTkFrame(self.frame_sidebar_left)
        self.frame_useful_links.grid(
            row=5, column=0, padx=5, pady=5, sticky="nsew", columnspan=2
        )
        self.frame_useful_links.grid_columnconfigure((0, 1), weight=1)

        self.label_useful_links = customtkinter.CTkLabel(
            self.frame_useful_links,
            text="Useful Links",
            font=customtkinter.CTkFont(size=16, weight="bold"),
        )
        self.label_useful_links.grid(row=0, column=0, padx=20, pady=5, columnspan=2)

        self.button_useful_links_Frontend = customtkinter.CTkButton(
            self.frame_useful_links,
            text="DB Frontend",
            command=lambda: util.open_webbrowser_with_url(
                api.frontendUrlPrefix, noExtraPrefix=True
            ),
            fg_color=data.fg_color_standard_but_inactive,
            hover_color=data.hover_color_standard_but_inactive,
        )
        self.button_useful_links_Frontend.grid(
            row=1, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        self.button_useful_links_Mockup = customtkinter.CTkButton(
            self.frame_useful_links,
            text="SN Decoder/Encoder",
            command=lambda: util.open_webbrowser_with_url(
                "https://annika-stein.web.cern.ch/module_mockup/serialnumber.html",
                noExtraPrefix=True,
            ),
            fg_color=data.fg_color_standard_but_inactive,
            hover_color=data.hover_color_standard_but_inactive,
        )
        self.button_useful_links_Mockup.grid(
            row=2, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        self.button_useful_links_Docs = customtkinter.CTkButton(
            self.frame_useful_links,
            text="ProdDB Documentation",
            command=lambda: util.open_webbrowser_with_url(
                "https://hgtd-database.docs.cern.ch/", noExtraPrefix=True
            ),
            fg_color=data.fg_color_standard_but_inactive,
            hover_color=data.hover_color_standard_but_inactive,
        )
        self.button_useful_links_Docs.grid(
            row=3, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        self.button_useful_links_MM = customtkinter.CTkButton(
            self.frame_useful_links,
            text="ProdDB Mattermost",
            command=lambda: util.open_webbrowser_with_url(
                "https://mattermost.web.cern.ch/atlas/channels/hgtd-production-database",
                noExtraPrefix=True,
            ),
            fg_color=data.fg_color_standard_but_inactive,
            hover_color=data.hover_color_standard_but_inactive,
        )
        self.button_useful_links_MM.grid(
            row=4, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        self.button_useful_links_meetings = customtkinter.CTkButton(
            self.frame_useful_links,
            text="ProdDB Meetings",
            command=lambda: util.open_webbrowser_with_url(
                "https://indico.cern.ch/category/9458/", noExtraPrefix=True
            ),
            fg_color=data.fg_color_standard_but_inactive,
            hover_color=data.hover_color_standard_but_inactive,
        )
        self.button_useful_links_meetings.grid(
            row=5, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        self.button_useful_links_GL_repo = customtkinter.CTkButton(
            self.frame_useful_links,
            text="hgtd-tools gitlab",
            command=lambda: util.open_webbrowser_with_url(
                "https://gitlab.cern.ch/anstein/hgtd-tools", noExtraPrefix=True
            ),
            fg_color=data.fg_color_standard_but_inactive,
            hover_color=data.hover_color_standard_but_inactive,
        )
        self.button_useful_links_GL_repo.grid(
            row=6, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        self.button_useful_links_tools_docs = customtkinter.CTkButton(
            self.frame_useful_links,
            text="hgtd-tools Documentation",
            command=lambda: util.open_webbrowser_with_url(
                "https://hgtd-tools.docs.cern.ch/", noExtraPrefix=True
            ),
            fg_color=data.fg_color_standard_but_inactive,
            hover_color=data.hover_color_standard_but_inactive,
        )
        self.button_useful_links_tools_docs.grid(
            row=7, column=0, padx=5, pady=(3, 0), sticky="nsew", columnspan=2
        )

        self.label_user = customtkinter.CTkLabel(
            self.frame_sidebar_left, text="User:", anchor="e"
        )
        self.label_user.grid(row=8, column=0, padx=5, pady=5)
        self.optionmenu_user = customtkinter.CTkOptionMenu(
            self.frame_sidebar_left,
            values=["None", "new..."],
            command=self.change_user_event,
            width=60,
        )
        self.optionmenu_user.grid(row=8, column=1, padx=5, pady=5)
        self.optionmenu_user.set("None")
        self.user_window = None

        self.label_appearance_mode = customtkinter.CTkLabel(
            self.frame_sidebar_left, text="Theme:", anchor="e"
        )
        self.label_appearance_mode.grid(row=9, column=0, padx=5, pady=5)
        self.optionmenu_appearance_mode = customtkinter.CTkOptionMenu(
            self.frame_sidebar_left,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event,
            width=60,
        )
        self.optionmenu_appearance_mode.grid(row=9, column=1, padx=5, pady=5)
        self.optionmenu_appearance_mode.set("System")

        self.label_scaling = customtkinter.CTkLabel(
            self.frame_sidebar_left, text="UI Scaling:", anchor="e"
        )
        self.label_scaling.grid(row=10, column=0, padx=5, pady=5)
        self.optionmenu_scaling = customtkinter.CTkOptionMenu(
            self.frame_sidebar_left,
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.change_scaling_event,
            width=60,
        )
        self.optionmenu_scaling.grid(row=10, column=1, padx=5, pady=5)
        self.optionmenu_scaling.set("100%")

        self.help_image = customtkinter.CTkImage(
            Image.open("circle-question.png"), size=(20, 20)
        )
        self.btnHelp = customtkinter.CTkButton(
            self.frame_sidebar_left,
            image=self.help_image,
            text="Help",
            compound="left",
            fg_color=data.fg_color_standard_but_active,
            hover_color=data.hover_color_standard_but_active,
            command=self.help,
            width=60,
        )
        self.btnHelp.grid(row=11, column=0, pady=10, padx=5, columnspan=2)
        self.help_window = None

        self.exit_image = customtkinter.CTkImage(
            Image.open("right-from-bracket-solid.png"), size=(20, 20)
        )
        self.btnLogout = customtkinter.CTkButton(
            self.frame_sidebar_left,
            image=self.exit_image,
            text="Close",
            compound="left",
            fg_color=data.fg_color_standard_but_red,
            hover_color=data.hover_color_standard_but_red,
            command=self.exit,
            width=60,
        )
        self.btnLogout.grid(row=12, column=0, pady=20, padx=5, columnspan=2)

        # work in main widget (column w.r.t. root >= 1)

        # create main frame with widgets
        self.frame_main = customtkinter.CTkFrame(self)
        self.frame_main.grid(
            row=0, column=1, rowspan=1, columnspan=2, padx=10, pady=10, sticky="nsew"
        )
        self.frame_main.grid_columnconfigure((0, 1), weight=1)
        self.frame_main.grid_rowconfigure(1, weight=1)

        # ********************************************
        #
        # === Parent/Child selection for ML/DU/PEB ===
        #
        # ********************************************

        # left sub widget: form
        self.frame_combobox = customtkinter.CTkFrame(self.frame_main, width=600)
        self.frame_combobox.grid(
            row=0, column=0, padx=5, pady=5, sticky="nsew", rowspan=2
        )
        self.frame_combobox.grid_columnconfigure((0, 1), weight=1)
        self.frame_combobox.grid_remove()  # The initial frame shown will now be Module Assembly

        # parent
        self.frame_parent = customtkinter.CTkFrame(self.frame_combobox)
        self.frame_parent.grid(
            row=0, column=0, padx=5, pady=5, sticky="nsew", columnspan=2
        )
        self.frame_parent.grid_columnconfigure((0, 1), weight=1)

        self.label_combobox_parent_T = customtkinter.CTkLabel(
            self.frame_parent, text="Parent Part Type: Detector Unit"
        )
        self.label_combobox_parent_T.grid(
            row=0, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew"
        )

        self.label_combobox_par_type = customtkinter.CTkLabel(
            self.frame_parent, text="DU type"
        )
        self.label_combobox_par_type.grid(
            row=1, column=0, padx=20, pady=(10, 10), sticky="nsew"
        )

        self.combobox_par_type_paginationFrame = customtkinter.CTkFrame(
            self.frame_parent
        )
        self.combobox_par_type_paginationFrame.grid(
            row=1, column=1, padx=20, pady=(10, 10), sticky="nsew"
        )
        self.label_combobox_par_type_paginationFrame = customtkinter.CTkLabel(
            self.combobox_par_type_paginationFrame, text="page 0/0"
        )
        self.label_combobox_par_type_paginationFrame.grid(
            row=0, column=0, padx=(10, 5), pady=5, sticky="nsew"
        )
        self.combobox_par_type_paginationButtonLeft = customtkinter.CTkButton(
            self.combobox_par_type_paginationFrame,
            text=">",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "DA-par-type", "L"
            ),
        )
        self.combobox_par_type_paginationButtonLeft.grid(
            row=0, column=1, padx=5, pady=5
        )
        self.combobox_par_type = customtkinter.CTkComboBox(
            self.combobox_par_type_paginationFrame,
            values=["All DU types"],
            command=self.combobox_par_type_event_select,
            state="readonly",
        )
        self.combobox_par_type.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_par_type.set("- Select -")
        self.combobox_par_type_paginationButtonRight = customtkinter.CTkButton(
            self.combobox_par_type_paginationFrame,
            text=">",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "DA-par-type", "R"
            ),
        )
        self.combobox_par_type_paginationButtonRight.grid(
            row=0, column=3, padx=5, pady=5
        )

        self.label_combobox_parent = customtkinter.CTkLabel(
            self.frame_parent, text="Parent Part SN"
        )
        self.label_combobox_parent.grid(
            row=2, column=0, padx=20, pady=(10, 10), sticky="nsew"
        )

        self.combobox_parent_paginationFrame = customtkinter.CTkFrame(self.frame_parent)
        self.combobox_parent_paginationFrame.grid(
            row=2, column=1, padx=20, pady=(10, 10), sticky="nsew"
        )
        self.label_combobox_parent_paginationFrame = customtkinter.CTkLabel(
            self.combobox_parent_paginationFrame, text="page 0/0"
        )
        self.label_combobox_parent_paginationFrame.grid(
            row=0, column=0, padx=(10, 5), pady=5, sticky="nsew"
        )
        self.combobox_parent_paginationButtonLeft = customtkinter.CTkButton(
            self.combobox_parent_paginationFrame,
            text="<",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "DA-par-SN", "L"
            ),
        )
        self.combobox_parent_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_parent = customtkinter.CTkComboBox(
            self.combobox_parent_paginationFrame,
            values=["Detector Unit", "Detector"],
            command=self.combobox_p_c_event_select,
            state="readonly",
            width=200,
        )
        self.combobox_parent.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_parent.set("- Select -")
        self.combobox_parent_paginationButtonRight = customtkinter.CTkButton(
            self.combobox_parent_paginationFrame,
            text=">",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "DA-par-SN", "R"
            ),
        )
        self.combobox_parent_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)

        self.button_inspect_parent = customtkinter.CTkButton(
            self.frame_parent,
            text="INSPECT PARENT",
            command=self.button_inspect_parent_event_click,
        )
        self.button_inspect_parent.grid(row=3, column=1, padx=20, pady=(10, 10))

        # child
        self.frame_child = customtkinter.CTkFrame(self.frame_combobox)
        self.frame_child.grid(
            row=1, column=0, padx=5, pady=5, sticky="nsew", columnspan=2
        )
        self.frame_child.grid_columnconfigure((0, 1), weight=1)

        self.label_combobox_child_T = customtkinter.CTkLabel(
            self.frame_child, text="Child Part Type: Module"
        )
        self.label_combobox_child_T.grid(
            row=0, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew"
        )

        self.optionmenu_child_conn = customtkinter.CTkOptionMenu(
            self.frame_child,
            values=["Not yet connected children", "All children"],
            command=self.change_child_conn_event,
            width=250,
        )
        self.optionmenu_child_conn.grid(row=1, column=0, padx=5, pady=10)
        self.optionmenu_child_conn.set("All children")
        self.combobox_child_manu = customtkinter.CTkComboBox(
            self.frame_child,
            values=["All manufacturers"],
            command=self.combobox_child_manu_event,
            width=250,
        )
        self.combobox_child_manu.grid(row=1, column=1, padx=5, pady=10)
        self.combobox_child_manu.set(
            "All manufacturers"
        )  # ToDo: change values depending on mode

        self.combobox_chi_type_paginationFrame = customtkinter.CTkFrame(
            self.frame_child
        )
        self.combobox_chi_type_paginationFrame.grid(
            row=1, column=1, padx=20, pady=(10, 10), sticky="nsew"
        )

        self.label_combobox_chi_type_paginationFrame = customtkinter.CTkLabel(
            self.combobox_chi_type_paginationFrame, text="page 0/0"
        )
        self.label_combobox_chi_type_paginationFrame.grid(
            row=0, column=0, padx=(10, 5), pady=5, sticky="nsew"
        )
        self.combobox_chi_type_paginationButtonLeft = customtkinter.CTkButton(
            self.combobox_chi_type_paginationFrame,
            text="<",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "DA-chi-type", "L"
            ),
        )
        self.combobox_chi_type_paginationButtonLeft.grid(
            row=0, column=1, padx=5, pady=5
        )
        self.combobox_chi_type = customtkinter.CTkComboBox(
            self.combobox_chi_type_paginationFrame,
            values=["All DU types"],
            command=self.combobox_chi_type_event_select,
            state="readonly",
        )
        self.combobox_chi_type.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_chi_type.set("- Select -")
        self.combobox_chi_type_paginationButtonRight = customtkinter.CTkButton(
            self.combobox_chi_type_paginationFrame,
            text=">",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "DA-chi-type", "R"
            ),
        )
        self.combobox_chi_type_paginationButtonRight.grid(
            row=0, column=3, padx=5, pady=5
        )
        self.combobox_chi_type_paginationFrame.grid_remove()

        self.label_combobox_child = customtkinter.CTkLabel(
            self.frame_child, text="Child Part SN"
        )
        self.label_combobox_child.grid(
            row=2, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew"
        )

        self.frame_child_SN_filter = customtkinter.CTkFrame(self.frame_child)
        self.frame_child_SN_filter.grid(
            row=3, column=0, padx=20, pady=(10, 10), sticky="nsew"
        )
        self.variable_child_SN_filter = customtkinter.StringVar(value="")
        self.entry_child_SN_filter = customtkinter.CTkEntry(
            self.frame_child_SN_filter, textvariable=self.variable_child_SN_filter
        )
        self.entry_child_SN_filter.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.filter_image = customtkinter.CTkImage(
            Image.open("searchIcon.png"), size=(20, 20)
        )
        self.btn_child_filter_SN = customtkinter.CTkButton(
            self.frame_child_SN_filter,
            image=self.filter_image,
            text="Filter SN",
            compound="left",
            command=lambda: self.button_onclick_event_filter_child_SN("generic child"),
            width=60,
        )
        self.btn_child_filter_SN.grid(row=0, column=1, padx=5, pady=5, columnspan=2)

        self.combobox_child_paginationFrame = customtkinter.CTkFrame(self.frame_child)
        self.combobox_child_paginationFrame.grid(
            row=3, column=1, padx=20, pady=(10, 10), sticky="nsew"
        )
        self.label_combobox_child_paginationFrame = customtkinter.CTkLabel(
            self.combobox_child_paginationFrame, text="page 0/0"
        )
        self.label_combobox_child_paginationFrame.grid(
            row=0, column=0, padx=(10, 5), pady=5, sticky="nsew"
        )
        self.combobox_child_paginationButtonLeft = customtkinter.CTkButton(
            self.combobox_child_paginationFrame,
            text="<",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "DA-chi-SN", "L"
            ),
        )
        self.combobox_child_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_child = customtkinter.CTkComboBox(
            self.combobox_child_paginationFrame,
            values=["Module", "Detector Unit"],
            command=self.combobox_p_c_event_select,
            state="readonly",
            width=200,
        )
        self.combobox_child.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_child.set("- Select -")
        self.combobox_child_paginationButtonRight = customtkinter.CTkButton(
            self.combobox_child_paginationFrame,
            text=">",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "DA-chi-SN", "R"
            ),
        )
        self.combobox_child_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)

        self.button_inspect_child = customtkinter.CTkButton(
            self.frame_child,
            text="INSPECT CHILD",
            command=self.button_inspect_child_event_click,
        )
        self.button_inspect_child.grid(row=4, column=1, padx=20, pady=(10, 10))

        # position / click
        self.frame_position = customtkinter.CTkFrame(self.frame_combobox)
        self.frame_position.grid(
            row=2, column=0, padx=5, pady=5, sticky="nsew", columnspan=2
        )
        self.frame_position.grid_columnconfigure((0, 1), weight=1)

        self.label_position = customtkinter.CTkLabel(
            self.frame_position, text="Position (derived from canvas interaction)"
        )
        self.label_position.grid(row=6, column=0, padx=20, pady=(20, 10), sticky="nsew")

        self.position_variable = customtkinter.StringVar(value="- automatic -")
        self.position_entry = customtkinter.CTkEntry(
            self.frame_position, textvariable=self.position_variable, state="disabled"
        )
        self.position_entry.grid(row=6, column=1, padx=20, pady=(20, 10), sticky="nsew")

        self.button_add = customtkinter.CTkButton(
            self.frame_position,
            text="ADD PARTS TREE",
            command=self.button_add_event_click,
        )
        self.button_add.grid(row=7, column=1, padx=20, pady=(20, 10))

        self.frame_clicked_position = customtkinter.CTkFrame(self.frame_position)
        self.frame_clicked_position.grid(
            row=9, column=0, padx=5, pady=5, sticky="nsew", columnspan=2
        )
        self.frame_clicked_position.grid_columnconfigure((0, 1), weight=1)

        self.button_inspect_clicked = customtkinter.CTkButton(
            self.frame_clicked_position,
            text="INSPECT CLICKED MODULE",
            command=self.button_inspect_clicked_event_click,
            state="disabled",
        )
        self.button_inspect_clicked.grid(row=0, column=1, padx=20, pady=(20, 10))

        self.button_delete_clicked = customtkinter.CTkButton(
            self.frame_clicked_position,
            text="UNLOAD CLICKED MODULE",
            command=self.button_delete_clicked_event_click,
            state="disabled",
            fg_color=data.fg_color_standard_but_red,
            hover_color=data.hover_color_standard_but_red,
        )
        self.button_delete_clicked.grid(row=0, column=0, padx=20, pady=(20, 10))

        # right sub widget: canvas containing DUs to click on
        self.label_canvas = customtkinter.CTkLabel(
            self.frame_main, text="Interactive canvas: accepting user click"
        )
        self.label_canvas.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.label_canvas.grid_remove()

        self.canvas = customtkinter.CTkCanvas(
            self.frame_main, width=500, height=700, background="white"
        )
        self.canvas.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.canvas.bind("<Button-1>", self.canvas_event_click)
        self.canvas.grid_remove()
        self.displayedDUtype = "None"

        # *********************************************
        #
        # === Module Assembly with MF, Hybrid HV/LV ===
        #
        # *********************************************

        self.frame_ma = customtkinter.CTkFrame(self.frame_main)
        self.frame_ma.grid(
            row=0, column=0, padx=5, pady=5, sticky="nsew", rowspan=2, columnspan=3
        )
        #
        # === 1st line ===
        #
        self.frame_module_parent = customtkinter.CTkFrame(self.frame_ma)
        self.frame_module_parent.grid(row=0, column=0, padx=5, pady=5, columnspan=2)

        self.frame_module_parent_selection = customtkinter.CTkFrame(
            self.frame_module_parent
        )
        self.frame_module_parent_selection.grid(
            row=0, column=0, padx=5, pady=5, columnspan=1
        )
        self.frame_module_parent_selection.grid_columnconfigure((0, 1), weight=1)

        self.label_module_parent = customtkinter.CTkLabel(
            self.frame_module_parent_selection, text="Parent Module"
        )
        self.label_module_parent.grid(row=0, column=0, padx=5, pady=5, columnspan=2)
        self.label_module_parent_manu = customtkinter.CTkLabel(
            self.frame_module_parent_selection, text="Manufacturer"
        )
        self.label_module_parent_manu.grid(
            row=1, column=0, padx=5, pady=5, columnspan=1
        )
        self.label_module_parent_loc = customtkinter.CTkLabel(
            self.frame_module_parent_selection, text="Location"
        )
        self.label_module_parent_loc.grid(row=1, column=1, padx=5, pady=5, columnspan=1)
        self.label_module_parent_SN = customtkinter.CTkLabel(
            self.frame_module_parent_selection, text="Parent SN"
        )
        self.label_module_parent_SN.grid(row=3, column=0, padx=5, pady=5, columnspan=1)

        self.combobox_MA_mod_par_manu = customtkinter.CTkComboBox(
            self.frame_module_parent_selection,
            values=["All manufacturers"],
            command=self.change_MA_parent_Mod_filter_event,
            width=250,
        )
        self.combobox_MA_mod_par_manu.grid(row=2, column=0, padx=10, pady=10)
        self.combobox_MA_mod_par_manu.set("All manufacturers")

        self.combobox_MA_mod_par_loc = customtkinter.CTkComboBox(
            self.frame_module_parent_selection,
            values=["All locations"],
            command=self.change_MA_parent_Mod_filter_event,
            width=250,
        )
        self.combobox_MA_mod_par_loc.grid(row=2, column=1, padx=10, pady=10)
        self.combobox_MA_mod_par_loc.set("All locations")

        self.combobox_MA_mod_par_paginationFrame = customtkinter.CTkFrame(
            self.frame_module_parent_selection
        )
        self.combobox_MA_mod_par_paginationFrame.grid(
            row=4, column=0, padx=20, pady=10, sticky="nsew"
        )
        self.label_combobox_MA_mod_par_paginationFrame = customtkinter.CTkLabel(
            self.combobox_MA_mod_par_paginationFrame, text="page 0/0"
        )
        self.label_combobox_MA_mod_par_paginationFrame.grid(
            row=0, column=0, padx=(10, 5), pady=5, sticky="nsew"
        )
        self.combobox_MA_mod_par_paginationButtonLeft = customtkinter.CTkButton(
            self.combobox_MA_mod_par_paginationFrame,
            text="<",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click("MA-MO", "L"),
        )
        self.combobox_MA_mod_par_paginationButtonLeft.grid(
            row=0, column=1, padx=5, pady=5
        )
        self.combobox_MA_mod_par = customtkinter.CTkComboBox(
            self.combobox_MA_mod_par_paginationFrame,
            values=["Nothing"],
            command=self.combobox_MA_mod_event_select,
            state="readonly",
            width=200,
        )
        self.combobox_MA_mod_par.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_MA_mod_par.set("- Select -")
        self.combobox_MA_mod_par_paginationButtonRight = customtkinter.CTkButton(
            self.combobox_MA_mod_par_paginationFrame,
            text=">",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click("MA-MO", "R"),
        )
        self.combobox_MA_mod_par_paginationButtonRight.grid(
            row=0, column=3, padx=5, pady=5
        )

        self.button_inspect_parent_module = customtkinter.CTkButton(
            self.frame_module_parent_selection,
            text="INSPECT MODULE",
            command=self.button_inspect_parent_module_event_click,
        )
        self.button_inspect_parent_module.grid(row=4, column=1, padx=20, pady=10)

        self.module_image = customtkinter.CTkImage(
            Image.open("Module.png"), size=(1920 / 5, (1920 / 5) * 1080 / 1920)
        )
        self.label_module_image_in = customtkinter.CTkLabel(
            self.frame_module_parent, text="", image=self.module_image
        )
        self.label_module_image_in.grid(
            row=0, column=1, padx=15, pady=15, sticky="nsew", rowspan=4
        )

        #
        # === 2nd line ===
        #
        self.frame_module_children = customtkinter.CTkFrame(self.frame_ma)
        self.frame_module_children.grid(
            row=1, column=0, padx=5, pady=5, sticky="nsew", columnspan=3
        )
        self.frame_module_children.grid_columnconfigure((0, 1, 2), weight=1)

        #
        # === Module Flex ===
        #
        self.frame_module_flex_child = customtkinter.CTkFrame(
            self.frame_module_children
        )
        self.frame_module_flex_child.grid(
            row=1, column=0, padx=5, pady=5, sticky="nsew"
        )
        self.frame_module_flex_child.grid_columnconfigure((0, 1), weight=1)

        self.label_module_flex_child = customtkinter.CTkLabel(
            self.frame_module_flex_child, text="Child Module Flex"
        )
        self.label_module_flex_child.grid(row=0, column=0, padx=5, pady=5, columnspan=2)
        self.label_module_flex_child_loc = customtkinter.CTkLabel(
            self.frame_module_flex_child, text="Location"
        )
        self.label_module_flex_child_loc.grid(
            row=1, column=0, padx=5, pady=5, columnspan=2
        )
        self.combobox_MA_MF_child_loc = customtkinter.CTkComboBox(
            self.frame_module_flex_child,
            values=["All locations"],
            command=self.change_MA_child_MF_filter_event,
            width=250,
        )
        self.combobox_MA_MF_child_loc.grid(
            row=2, column=0, padx=5, pady=5, columnspan=2
        )
        self.combobox_MA_MF_child_loc.set("All locations")
        self.label_module_flex_child_conn = customtkinter.CTkLabel(
            self.frame_module_flex_child, text="Connection status"
        )
        self.label_module_flex_child_conn.grid(
            row=3, column=0, padx=5, pady=5, columnspan=2
        )
        self.optionmenu_MA_child_MF_conn = customtkinter.CTkOptionMenu(
            self.frame_module_flex_child,
            values=["Not yet connected children", "All children"],
            command=self.change_MA_child_MF_filter_event,
            width=250,
        )
        self.optionmenu_MA_child_MF_conn.grid(
            row=4, column=0, padx=5, pady=5, columnspan=2
        )
        self.optionmenu_MA_child_MF_conn.set("All children")
        self.label_module_flex_child_SN = customtkinter.CTkLabel(
            self.frame_module_flex_child, text="Module Flex SN"
        )
        self.label_module_flex_child_SN.grid(
            row=5, column=0, padx=5, pady=5, columnspan=2
        )

        self.frame_child0_SN_filter = customtkinter.CTkFrame(
            self.frame_module_flex_child
        )
        self.frame_child0_SN_filter.grid(
            row=6, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew"
        )
        self.variable_child0_SN_filter = customtkinter.StringVar(value="")
        self.entry_child0_SN_filter = customtkinter.CTkEntry(
            self.frame_child0_SN_filter, textvariable=self.variable_child0_SN_filter
        )
        self.entry_child0_SN_filter.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.btn_child0_filter_SN = customtkinter.CTkButton(
            self.frame_child0_SN_filter,
            image=self.filter_image,
            text="Filter SN",
            compound="left",
            command=lambda: self.button_onclick_event_filter_child_SN("Module Flex"),
            width=60,
        )
        self.btn_child0_filter_SN.grid(row=0, column=1, padx=5, pady=5)

        self.combobox_MA_MF_chi_paginationFrame = customtkinter.CTkFrame(
            self.frame_module_flex_child
        )
        self.combobox_MA_MF_chi_paginationFrame.grid(
            row=7, column=0, padx=20, pady=10, sticky="nsew", columnspan=2
        )
        self.label_combobox_MA_MF_chi_paginationFrame = customtkinter.CTkLabel(
            self.combobox_MA_MF_chi_paginationFrame, text="page 0/0"
        )
        self.label_combobox_MA_MF_chi_paginationFrame.grid(
            row=0, column=0, padx=(10, 5), pady=5, sticky="nsew"
        )
        self.combobox_MA_MF_chi_paginationButtonLeft = customtkinter.CTkButton(
            self.combobox_MA_MF_chi_paginationFrame,
            text="<",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click("MA-MF", "L"),
        )
        self.combobox_MA_MF_chi_paginationButtonLeft.grid(
            row=0, column=1, padx=5, pady=5
        )
        self.combobox_MA_MF_chi = customtkinter.CTkComboBox(
            self.combobox_MA_MF_chi_paginationFrame,
            values=["Nothing"],
            command=self.combobox_MA_MF_event_select,
            state="readonly",
            width=200,
        )
        self.combobox_MA_MF_chi.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_MA_MF_chi.set("- Select -")
        self.combobox_MA_MF_chi_paginationButtonRight = customtkinter.CTkButton(
            self.combobox_MA_MF_chi_paginationFrame,
            text=">",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click("MA-MF", "R"),
        )
        self.combobox_MA_MF_chi_paginationButtonRight.grid(
            row=0, column=3, padx=5, pady=5
        )

        self.button_inspect_child_module_flex = customtkinter.CTkButton(
            self.frame_module_flex_child,
            text="INSPECT MODULE FLEX",
            command=self.button_inspect_child_module_flex_event_click,
        )
        self.button_inspect_child_module_flex.grid(
            row=8, column=0, padx=5, pady=5, columnspan=2
        )
        self.button_add_child_module_flex = customtkinter.CTkButton(
            self.frame_module_flex_child,
            text="CONNECT MODULE FLEX\nTO MODULE ABOVE",
            command=self.button_add_child_module_flex_event_click,
            fg_color=data.fg_color_standard_but_active,
            hover_color=data.hover_color_standard_but_active,
        )
        self.button_add_child_module_flex.grid(
            row=9, column=0, padx=5, pady=5, columnspan=2
        )
        self.button_delete_child_MF = customtkinter.CTkButton(
            self.frame_module_flex_child,
            text="DISCONNECT MODULE FLEX\nFROM ITS PARENT",
            command=self.button_delete_child_module_flex_event_click,
            state="disabled",
            fg_color=data.fg_color_standard_but_red,
            hover_color=data.hover_color_standard_but_red,
        )
        self.button_delete_child_MF.grid(row=10, column=0, padx=5, pady=5, columnspan=2)

        #
        # === Hybrid HV-side ===
        #
        self.frame_HY_HV_child = customtkinter.CTkFrame(self.frame_module_children)
        self.frame_HY_HV_child.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        self.frame_HY_HV_child.grid_columnconfigure((0, 1), weight=1)
        self.label_HY_HV_child = customtkinter.CTkLabel(
            self.frame_HY_HV_child, text="Child Hybrid HV-side"
        )
        self.label_HY_HV_child.grid(row=0, column=0, padx=5, pady=5, columnspan=2)
        self.label_HY_HV_child_loc = customtkinter.CTkLabel(
            self.frame_HY_HV_child, text="Location"
        )
        self.label_HY_HV_child_loc.grid(row=1, column=0, padx=5, pady=5, columnspan=2)
        self.combobox_MA_HY_HV_child_loc = customtkinter.CTkComboBox(
            self.frame_HY_HV_child,
            values=["All locations"],
            command=self.change_MA_child_HY_HV_filter_event,
            width=250,
        )
        self.combobox_MA_HY_HV_child_loc.grid(
            row=2, column=0, padx=5, pady=5, columnspan=2
        )
        self.combobox_MA_HY_HV_child_loc.set("All locations")
        self.label_HY_HV_child_conn = customtkinter.CTkLabel(
            self.frame_HY_HV_child, text="Connection status"
        )
        self.label_HY_HV_child_conn.grid(row=3, column=0, padx=5, pady=5, columnspan=2)
        self.optionmenu_MA_child_HY_HV_conn = customtkinter.CTkOptionMenu(
            self.frame_HY_HV_child,
            values=["Not yet connected children", "All children"],
            command=self.change_MA_child_HY_HV_filter_event,
            width=250,
        )
        self.optionmenu_MA_child_HY_HV_conn.grid(
            row=4, column=0, padx=5, pady=5, columnspan=2
        )
        self.optionmenu_MA_child_HY_HV_conn.set("All children")
        self.label_HY_HV_child_conn = customtkinter.CTkLabel(
            self.frame_HY_HV_child, text="Cluster based on VBD"
        )
        self.label_HY_HV_child_conn.grid(row=5, column=0, padx=5, pady=5, columnspan=2)
        self.combobox_MA_HY_HV_child_cluster = customtkinter.CTkComboBox(
            self.frame_HY_HV_child,
            values=["All clusters"],
            command=self.change_MA_child_HY_HV_filter_event,
            width=250,
        )
        self.combobox_MA_HY_HV_child_cluster.grid(
            row=6, column=0, padx=5, pady=5, columnspan=2
        )
        self.combobox_MA_HY_HV_child_cluster.set("All clusters")
        self.label_HY_HV_child_SN = customtkinter.CTkLabel(
            self.frame_HY_HV_child, text="HY HV-side SN"
        )
        self.label_HY_HV_child_SN.grid(row=7, column=0, padx=5, pady=5, columnspan=2)

        self.frame_child1_SN_filter = customtkinter.CTkFrame(self.frame_HY_HV_child)
        self.frame_child1_SN_filter.grid(
            row=8, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew"
        )
        self.variable_child1_SN_filter = customtkinter.StringVar(value="")
        self.entry_child1_SN_filter = customtkinter.CTkEntry(
            self.frame_child1_SN_filter, textvariable=self.variable_child1_SN_filter
        )
        self.entry_child1_SN_filter.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.btn_child1_filter_SN = customtkinter.CTkButton(
            self.frame_child1_SN_filter,
            image=self.filter_image,
            text="Filter SN",
            compound="left",
            command=lambda: self.button_onclick_event_filter_child_SN("HY_LV"),
            width=60,
        )
        self.btn_child1_filter_SN.grid(row=0, column=1, padx=5, pady=5, columnspan=2)

        self.combobox_HY_HV_paginationFrame = customtkinter.CTkFrame(
            self.frame_HY_HV_child
        )
        self.combobox_HY_HV_paginationFrame.grid(
            row=9, column=0, padx=20, pady=10, sticky="nsew", columnspan=2
        )
        self.label_combobox_HY_HV_paginationFrame = customtkinter.CTkLabel(
            self.combobox_HY_HV_paginationFrame, text="page 0/0"
        )
        self.label_combobox_HY_HV_paginationFrame.grid(
            row=0, column=0, padx=(10, 5), pady=5, sticky="nsew"
        )
        self.combobox_HY_HV_paginationButtonLeft = customtkinter.CTkButton(
            self.combobox_HY_HV_paginationFrame,
            text="<",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "MA-Hybrid-HV", "L"
            ),
        )
        self.combobox_HY_HV_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_MA_HY_HV_chi = customtkinter.CTkComboBox(
            self.combobox_HY_HV_paginationFrame,
            values=["Nothing"],
            command=self.combobox_MA_HY_HV_event_select,
            state="readonly",
            width=200,
        )
        self.combobox_MA_HY_HV_chi.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_MA_HY_HV_chi.set("- Select -")
        self.combobox_HY_HV_paginationButtonRight = customtkinter.CTkButton(
            self.combobox_HY_HV_paginationFrame,
            text=">",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "MA-Hybrid-HV", "R"
            ),
        )
        self.combobox_HY_HV_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)

        self.button_inspect_child_HY_HV = customtkinter.CTkButton(
            self.frame_HY_HV_child,
            text="INSPECT HY HV-side",
            command=self.button_inspect_child_HY_HV_event_click,
        )
        self.button_inspect_child_HY_HV.grid(
            row=10, column=0, padx=5, pady=5, columnspan=2
        )
        self.button_add_child_HY_HV = customtkinter.CTkButton(
            self.frame_HY_HV_child,
            text="CONNECT HY HV-side\nTO MODULE ABOVE",
            command=self.button_add_child_HY_HV_event_click,
            fg_color=data.fg_color_standard_but_active,
            hover_color=data.hover_color_standard_but_active,
        )
        self.button_add_child_HY_HV.grid(row=11, column=0, padx=5, pady=5, columnspan=2)
        self.button_delete_child_HY_HV = customtkinter.CTkButton(
            self.frame_HY_HV_child,
            text="DISCONNECT HY HV-side\nFROM ITS PARENT",
            command=self.button_delete_child_HY_HV_event_click,
            state="disabled",
            fg_color=data.fg_color_standard_but_red,
            hover_color=data.hover_color_standard_but_red,
        )
        self.button_delete_child_HY_HV.grid(
            row=12, column=0, padx=5, pady=5, columnspan=2
        )

        #
        # === Hybrid LV-side ===
        #
        self.frame_HY_LV_child = customtkinter.CTkFrame(self.frame_module_children)
        self.frame_HY_LV_child.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        self.frame_HY_LV_child.grid_columnconfigure((0, 1), weight=1)
        self.label_HY_LV_child = customtkinter.CTkLabel(
            self.frame_HY_LV_child, text="Child Hybrid LV-side"
        )
        self.label_HY_LV_child.grid(row=0, column=0, padx=5, pady=5, columnspan=2)
        self.label_HY_LV_child_loc = customtkinter.CTkLabel(
            self.frame_HY_LV_child, text="Location"
        )
        self.label_HY_LV_child_loc.grid(row=1, column=0, padx=5, pady=5, columnspan=2)
        self.combobox_MA_HY_LV_child_loc = customtkinter.CTkComboBox(
            self.frame_HY_LV_child,
            values=["All locations"],
            command=self.change_MA_child_HY_LV_filter_event,
            width=250,
        )
        self.combobox_MA_HY_LV_child_loc.grid(
            row=2, column=0, padx=5, pady=5, columnspan=2
        )
        self.combobox_MA_HY_LV_child_loc.set("All locations")
        self.label_HY_LV_child_conn = customtkinter.CTkLabel(
            self.frame_HY_LV_child, text="Connection status"
        )
        self.label_HY_LV_child_conn.grid(row=3, column=0, padx=5, pady=5, columnspan=2)
        self.optionmenu_MA_child_HY_LV_conn = customtkinter.CTkOptionMenu(
            self.frame_HY_LV_child,
            values=["Not yet connected children", "All children"],
            command=self.change_MA_child_HY_LV_filter_event,
            width=250,
        )
        self.optionmenu_MA_child_HY_LV_conn.grid(
            row=4, column=0, padx=5, pady=5, columnspan=2
        )
        self.optionmenu_MA_child_HY_LV_conn.set("All children")
        self.label_HY_LV_child_conn = customtkinter.CTkLabel(
            self.frame_HY_LV_child, text="Cluster based on VBD"
        )
        self.label_HY_LV_child_conn.grid(row=5, column=0, padx=5, pady=5, columnspan=2)
        self.combobox_MA_HY_LV_child_cluster = customtkinter.CTkComboBox(
            self.frame_HY_LV_child,
            values=["All clusters"],
            command=self.change_MA_child_HY_LV_filter_event,
            width=250,
        )
        self.combobox_MA_HY_LV_child_cluster.grid(
            row=6, column=0, padx=5, pady=5, columnspan=2
        )
        self.combobox_MA_HY_LV_child_cluster.set("All clusters")
        self.label_HY_LV_child_SN = customtkinter.CTkLabel(
            self.frame_HY_LV_child, text="HY LV-side SN"
        )
        self.label_HY_LV_child_SN.grid(row=7, column=0, padx=5, pady=5, columnspan=2)

        self.frame_child2_SN_filter = customtkinter.CTkFrame(self.frame_HY_LV_child)
        self.frame_child2_SN_filter.grid(
            row=8, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew"
        )
        self.variable_child2_SN_filter = customtkinter.StringVar(value="")
        self.entry_child2_SN_filter = customtkinter.CTkEntry(
            self.frame_child2_SN_filter, textvariable=self.variable_child2_SN_filter
        )
        self.entry_child2_SN_filter.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.btn_child2_filter_SN = customtkinter.CTkButton(
            self.frame_child2_SN_filter,
            image=self.filter_image,
            text="Filter SN",
            compound="left",
            command=lambda: self.button_onclick_event_filter_child_SN("HY_LV"),
            width=60,
        )
        self.btn_child2_filter_SN.grid(row=0, column=1, padx=5, pady=5, columnspan=2)

        self.combobox_HY_LV_paginationFrame = customtkinter.CTkFrame(
            self.frame_HY_LV_child
        )
        self.combobox_HY_LV_paginationFrame.grid(
            row=9, column=0, padx=20, pady=10, sticky="nsew", columnspan=2
        )
        self.label_combobox_HY_LV_paginationFrame = customtkinter.CTkLabel(
            self.combobox_HY_LV_paginationFrame, text="page 0/0"
        )
        self.label_combobox_HY_LV_paginationFrame.grid(
            row=0, column=0, padx=(10, 5), pady=5, sticky="nsew"
        )
        self.combobox_HY_LV_paginationButtonLeft = customtkinter.CTkButton(
            self.combobox_HY_LV_paginationFrame,
            text="<",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "MA-Hybrid-LV", "L"
            ),
        )
        self.combobox_HY_LV_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_MA_HY_LV_chi = customtkinter.CTkComboBox(
            self.combobox_HY_LV_paginationFrame,
            values=["Nothing"],
            command=self.combobox_MA_HY_LV_event_select,
            state="readonly",
            width=200,
        )
        self.combobox_MA_HY_LV_chi.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_MA_HY_LV_chi.set("- Select -")
        self.combobox_HY_LV_paginationButtonRight = customtkinter.CTkButton(
            self.combobox_HY_LV_paginationFrame,
            text=">",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click(
                "MA-Hybrid-LV", "R"
            ),
        )
        self.combobox_HY_LV_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)

        self.button_inspect_child_HY_LV = customtkinter.CTkButton(
            self.frame_HY_LV_child,
            text="INSPECT HY LV-side",
            command=self.button_inspect_child_HY_LV_event_click,
        )
        self.button_inspect_child_HY_LV.grid(
            row=10, column=0, padx=5, pady=5, columnspan=2
        )
        self.button_add_child_HY_LV = customtkinter.CTkButton(
            self.frame_HY_LV_child,
            text="CONNECT HY LV-side\nTO MODULE ABOVE",
            command=self.button_add_child_HY_LV_event_click,
            fg_color=data.fg_color_standard_but_active,
            hover_color=data.hover_color_standard_but_active,
        )
        self.button_add_child_HY_LV.grid(row=11, column=0, padx=5, pady=5, columnspan=2)
        self.button_delete_child_HY_LV = customtkinter.CTkButton(
            self.frame_HY_LV_child,
            text="DISCONNECT HY LV-side\nFROM ITS PARENT",
            command=self.button_delete_child_HY_LV_event_click,
            state="disabled",
            fg_color=data.fg_color_standard_but_red,
            hover_color=data.hover_color_standard_but_red,
        )
        self.button_delete_child_HY_LV.grid(
            row=12, column=0, padx=5, pady=5, columnspan=2
        )

        # ******************************************
        #
        # === Slot global/local for FT selection ===
        #
        # ******************************************

        self.frame_ft_rel = customtkinter.CTkFrame(self.frame_main, width=600)
        self.frame_ft_rel.grid(
            row=0, column=0, padx=5, pady=5, sticky="nsew", rowspan=2, columnspan=2
        )
        self.frame_ft_rel.grid_remove()

        #
        # === 1st line ===
        #
        self.frame_slot_sel = customtkinter.CTkFrame(self.frame_ft_rel)
        self.frame_slot_sel.grid(
            row=0, column=0, padx=5, pady=5, sticky="nsew", columnspan=3
        )
        self.frame_slot_sel.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.frame_slot_sel.grid_rowconfigure((0, 1, 2), weight=1)

        self.optionmenu_slot_vessel = customtkinter.CTkOptionMenu(
            self.frame_slot_sel,
            values=["Vessel: 1", "Vessel: 2", "Vessel: M", "Vessel: D"],
            command=self.change_child_conn_event,
            width=200,
        )
        self.optionmenu_slot_vessel.grid(row=0, column=0, padx=5, pady=10)
        self.optionmenu_slot_vessel.set("Vessel: 1")

        self.optionmenu_slot_layer = customtkinter.CTkOptionMenu(
            self.frame_slot_sel,
            values=["Layer: 0", "Layer: 1", "Layer: 2", "Layer: 3"],
            command=self.change_child_conn_event,
            width=200,
        )
        self.optionmenu_slot_layer.grid(row=1, column=0, padx=5, pady=10)
        self.optionmenu_slot_layer.set("Layer: 0")

        self.optionmenu_slot_quadrant = customtkinter.CTkOptionMenu(
            self.frame_slot_sel,
            values=["Quadrant: 0", "Quadrant: 1", "Quadrant: 2", "Quadrant: 3"],
            command=self.change_child_conn_event,
            width=200,
        )
        self.optionmenu_slot_quadrant.grid(row=2, column=0, padx=5, pady=10)
        self.optionmenu_slot_quadrant.set("Quadrant: 0")

        self.label_slot_global = customtkinter.CTkLabel(
            self.frame_slot_sel, text="Global (type in):"
        )
        self.label_slot_global.grid(row=0, column=1, padx=20, pady=10, sticky="nsew")

        self.button_find_slot = customtkinter.CTkButton(
            self.frame_slot_sel,
            text="FIND IN SLOT TABLE",
            command=self.button_find_slot_event_click,
        )
        self.button_find_slot.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")

        self.button_inspect_slot = customtkinter.CTkButton(
            self.frame_slot_sel,
            text="INSPECT SLOT",
            command=self.button_inspect_slot_event_click,
        )
        self.button_inspect_slot.grid(row=3, column=1, padx=20, pady=10)

        self.label_slot_local = customtkinter.CTkLabel(
            self.frame_slot_sel, text="Local (derived):"
        )
        self.label_slot_local.grid(row=2, column=1, padx=20, pady=10, sticky="nsew")

        self.label_slot_DU_type = customtkinter.CTkLabel(
            self.frame_slot_sel, text="DU type"
        )
        self.label_slot_DU_type.grid(row=1, column=2, padx=20, pady=10, sticky="nsew")

        self.slot_loc_DUtype_variable = customtkinter.StringVar(value="- automatic -")
        self.slot_loc_DUtype_entry = customtkinter.CTkEntry(
            self.frame_slot_sel,
            textvariable=self.slot_loc_DUtype_variable,
            state="disabled",
        )
        self.slot_loc_DUtype_entry.grid(
            row=2, column=2, padx=20, pady=10, sticky="nsew"
        )

        self.slot_glob_row_variable = customtkinter.StringVar(value="")
        self.slot_glob_row_entry = customtkinter.CTkEntry(
            self.frame_slot_sel, textvariable=self.slot_glob_row_variable
        )
        self.slot_glob_row_entry.grid(row=0, column=3, padx=20, pady=10, sticky="nsew")

        self.label_slot_row = customtkinter.CTkLabel(self.frame_slot_sel, text="Row")
        self.label_slot_row.grid(row=1, column=3, padx=20, pady=10, sticky="nsew")

        self.slot_loc_row_variable = customtkinter.StringVar(value="- automatic -")
        self.slot_loc_row_entry = customtkinter.CTkEntry(
            self.frame_slot_sel,
            textvariable=self.slot_loc_row_variable,
            state="disabled",
        )
        self.slot_loc_row_entry.grid(row=2, column=3, padx=20, pady=10, sticky="nsew")

        self.slot_glob_mod_variable = customtkinter.StringVar(value="")
        self.slot_glob_mod_entry = customtkinter.CTkEntry(
            self.frame_slot_sel, textvariable=self.slot_glob_mod_variable
        )
        self.slot_glob_mod_entry.grid(row=0, column=4, padx=20, pady=10, sticky="nsew")

        self.label_slot_mod = customtkinter.CTkLabel(self.frame_slot_sel, text="Mod")
        self.label_slot_mod.grid(row=1, column=4, padx=20, pady=10, sticky="nsew")

        self.slot_loc_mod_variable = customtkinter.StringVar(value="- automatic -")
        self.slot_loc_mod_entry = customtkinter.CTkEntry(
            self.frame_slot_sel,
            textvariable=self.slot_loc_mod_variable,
            state="disabled",
        )
        self.slot_loc_mod_entry.grid(row=2, column=4, padx=20, pady=10, sticky="nsew")

        #
        # === 2nd line ===
        #
        self.label_ft_gen = customtkinter.CTkLabel(
            self.frame_ft_rel,
            text="Suitable FT batch(es)/meta-generation for this VLQ:",
        )
        self.label_ft_gen.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # demo V1 (PEB 1F): 20WFTC11F/20WFTS11F/20WFTG11F (old order cat 01--36), 20WFTG12F (new order cat 37--57)
        # Pre-production: 20WFTCP1F/20WFTSP1F/20WFTGPF/20WFTMP1F (cat 01--62)
        # Main Production: 20WFTCM1F/20WFTSM1F/20WFTGM1F/20WFTMM1F (cat 01--62)
        self.label_ft_gen_output = customtkinter.CTkLabel(self.frame_ft_rel, text=" ")
        self.label_ft_gen_output.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")

        #
        # === 3rd line ===
        #
        self.label_ft_type = customtkinter.CTkLabel(
            self.frame_ft_rel,
            text="Derived FT type of this FT generation for this Slot:",
        )
        self.label_ft_type.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        self.label_ft_type_output = customtkinter.CTkLabel(self.frame_ft_rel, text=" ")
        self.label_ft_type_output.grid(row=2, column=1, padx=20, pady=10, sticky="nsew")

        #
        # === 4/5th line ===
        #
        self.label_combobox_ft = customtkinter.CTkLabel(
            self.frame_ft_rel, text="FTs matching selection criteria:"
        )
        self.label_combobox_ft.grid(row=4, column=0, padx=20, pady=10, sticky="nsew")

        self.frame_childFT_SN_filter = customtkinter.CTkFrame(self.frame_ft_rel)
        self.frame_childFT_SN_filter.grid(
            row=3, column=1, padx=20, pady=(10, 10), sticky="nsew"
        )
        self.variable_childFT_SN_filter = customtkinter.StringVar(value="")
        self.entry_childFT_SN_filter = customtkinter.CTkEntry(
            self.frame_childFT_SN_filter, textvariable=self.variable_childFT_SN_filter
        )
        self.entry_childFT_SN_filter.grid(
            row=0, column=0, padx=5, pady=5, sticky="nsew"
        )
        self.filter_image = customtkinter.CTkImage(
            Image.open("searchIcon.png"), size=(20, 20)
        )
        self.btn_childFT_filter_SN = customtkinter.CTkButton(
            self.frame_childFT_SN_filter,
            image=self.filter_image,
            text="Filter SN",
            compound="left",
            command=lambda: self.button_onclick_event_filter_child_SN("generic child"),
            width=60,
        )
        self.btn_childFT_filter_SN.grid(row=0, column=1, padx=5, pady=5)

        self.optionmenu_ft_conn = customtkinter.CTkOptionMenu(
            self.frame_ft_rel,
            values=["Not yet connected FTs", "All FTs"],
            command=self.change_ft_conn_event,
            width=250,
        )
        self.optionmenu_ft_conn.grid(row=4, column=0, padx=20, pady=10)
        self.optionmenu_ft_conn.set("All FTs")

        self.combobox_ft_paginationFrame = customtkinter.CTkFrame(self.frame_ft_rel)
        self.combobox_ft_paginationFrame.grid(
            row=4, column=1, padx=20, pady=10, sticky="ns"
        )
        self.label_combobox_ft_paginationFrame = customtkinter.CTkLabel(
            self.combobox_ft_paginationFrame, text="page 0/0"
        )
        self.label_combobox_ft_paginationFrame.grid(
            row=0, column=0, padx=(10, 5), pady=5, sticky="nsew"
        )
        self.combobox_ft_paginationButtonLeft = customtkinter.CTkButton(
            self.combobox_ft_paginationFrame,
            text="<",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click("FT", "L"),
        )
        self.combobox_ft_paginationButtonLeft.grid(row=0, column=1, padx=5, pady=5)
        self.combobox_ft = customtkinter.CTkComboBox(
            self.combobox_ft_paginationFrame,
            values=["Nothing"],
            command=self.combobox_ft_event_select,
            state="readonly",
            width=200,
        )
        self.combobox_ft.grid(row=0, column=2, padx=0, pady=5, sticky="nsew")
        self.combobox_ft.set("- Select -")
        self.combobox_ft_paginationButtonRight = customtkinter.CTkButton(
            self.combobox_ft_paginationFrame,
            text=">",
            width=30,
            command=lambda: self.button_combobox_paginationButton_click("FT", "R"),
        )
        self.combobox_ft_paginationButtonRight.grid(row=0, column=3, padx=5, pady=5)

        self.button_inspect_ft = customtkinter.CTkButton(
            self.frame_ft_rel,
            text="INSPECT FT",
            command=self.button_inspect_ft_event_click,
        )
        self.button_inspect_ft.grid(row=4, column=2, padx=20, pady=10)

        self.button_delete_connected_ft = customtkinter.CTkButton(
            self.frame_ft_rel,
            text="DISCONNECT SELECTED FT",
            command=self.button_delete_connected_ft_event_click,
            state="disabled",
            fg_color=data.fg_color_standard_but_red,
            hover_color=data.hover_color_standard_but_red,
        )
        self.button_delete_connected_ft.grid(row=5, column=1, padx=20, pady=(20, 10))

        self.button_add_ft = customtkinter.CTkButton(
            self.frame_ft_rel,
            text="ADD PARTS TREE",
            command=self.button_add_ft_event_click,
        )
        self.button_add_ft.grid(row=5, column=2, padx=20, pady=10)

        # footer: info for user (e.g. Warning, Error)
        self.label_info = customtkinter.CTkLabel(
            self.frame_main,
            text=" ",
            font=customtkinter.CTkFont(size=16, weight="bold"),
        )
        self.label_info.grid(row=2, column=0, padx=20, pady=20, columnspan=2)

        # *************************************************
        #
        # === Filling variables with defaults / startup ===
        #
        # *************************************************

        # First startup of program: default values
        self.api_status = 1
        self.last_responseText = ""
        self.slots = None
        self.partstree = None
        self.this_DU_relations_MODULE = []
        self.this_MODULE_relations_DU = []
        self.this_MODULE_relations_SLOT = []
        self.this_FT_relations_SLOT = []
        self.this_SLOT_relations_FT = []
        self.ft_filter = ""
        self.combined_slot = ""
        self.this_MOD_relations_MF = []
        self.this_MOD_relations_HY_HV = []
        self.this_MOD_relations_HY_LV = []
        self.this_MOD_relations_HY_unknownPosition = []
        self.this_MF_relations_MOD = []
        self.this_HY_HV_relations_MOD = []
        self.this_HY_LV_relations_MOD = []

        self.possible_parents = []
        self.possible_children = []
        self.possible_ft = []
        self.possible_MA_mod_par = []
        self.possible_MF = []
        self.possible_HY_HV = []
        self.possible_HY_LV = []

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
        self.child_conn = None
        self.child_manu = None
        self.child_SN_filter = ""
        self.child0_SN_filter = ""
        self.child1_SN_filter = ""
        self.child2_SN_filter = ""
        self.childFT_SN_filter = ""
        self.ft_conn = None

        # Module Assembly
        self.MA_mod_par_manu = None
        self.MA_mod_par_loc = None
        self.module_flex_child_loc = None
        self.HY_HV_child_loc = None
        self.HY_LV_child_loc = None

        self.MF_child_conn = None
        self.HY_HV_child_conn = None
        self.HY_LV_child_conn = None

        self.HY_HV_child_cluster = None
        self.HY_LV_child_cluster = None

        self.user = "None"
        self.users = ["None", "new..."]

        # these are not taken from the DB, but from conventions
        self.possible_par_types = ["All DU types"] + data.allDUkeysList
        self.possible_par_types_chunked = [
            self.possible_par_types[i : i + self.n_items_to_show_in_cbx]
            for i in range(0, len(self.possible_par_types), self.n_items_to_show_in_cbx)
        ]
        self.possible_chi_types = ["All DU types"] + data.allDUkeysList
        self.possible_chi_types_chunked = [
            self.possible_chi_types[i : i + self.n_items_to_show_in_cbx]
            for i in range(0, len(self.possible_chi_types), self.n_items_to_show_in_cbx)
        ]
        self.cbx_ptype_n_pages = len(self.possible_par_types_chunked)
        self.cbx_ctype_n_pages = len(self.possible_chi_types_chunked)
        self.cbx_ptype_n_pages = len(self.possible_par_types_chunked)
        self.cbx_ctype_n_pages = len(self.possible_chi_types_chunked)
        self.cbx_ptype_shown_page = 1
        self.cbx_ctype_shown_page = 1
        self.label_combobox_par_type_paginationFrame.configure(
            text=f"page {self.cbx_ptype_shown_page}/{self.cbx_ptype_n_pages}"
        )
        self.label_combobox_chi_type_paginationFrame.configure(
            text=f"page {self.cbx_ctype_shown_page}/{self.cbx_ctype_n_pages}"
        )
        self.combobox_par_type.configure(values=self.possible_par_types_chunked[0])
        self.combobox_chi_type.configure(values=self.possible_chi_types_chunked[0])

        print("=" * 80)
        print(f"Welcome to hgtd-tools!")
        print("-" * 80)
        try:
            upstream_version, upstream_version_last_responseText = api.get_version()
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            upstream_version_last_responseText = str(e)
        except ValueError as e:
            upstream_version_last_responseText = str(e)

        if upstream_version_last_responseText[:3] != "200":
            print(
                f"Version of hgtd-tools could not be compared to upstream, check your web connection!"
            )
        else:
            if self.my_version != upstream_version:
                print(f"You are not running the most recent version of hgtd-tools.")
                print(
                    f"Your release: {self.my_version} / latest published release: {upstream_version}."
                )
                print(
                    f"Consider updating to a new release, either via git workflow (pull) or by downloading a specific release archive from gitlab."
                )
                self.version_full_text = (
                    self.version_full_text + f"\noutdated release, please update"
                )
                self.label_credits.configure(text=self.version_full_text)
            else:
                print(
                    f"You are running version {self.my_version}, the most recent release of hgtd-tools. Enjoy!"
                )

        # Get first parents and children for default operating mode
        try:
            self.manufacturers, self.last_responseText = util.get_manufacturers()
            self.locations, self.last_responseText = util.get_locations()
            self.possible_MA_mod_par, self.last_responseText = util.get_relevant_parts(
                "Module"
            )
            self.possible_MF, self.last_responseText = util.get_relevant_parts(
                "Module Flex"
            )
            self.possible_HY_HV, self.last_responseText = util.get_relevant_parts(
                "Hybrid"
            )
            self.possible_HY_LV = self.possible_HY_HV
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            self.manufacturers = []
            self.locations = []
            self.possible_MA_mod_par = []
            self.possible_MF = []
            self.possible_HY_HV = []
            self.possible_HY_LV = []
            self.last_responseText = str(e)
        except ValueError as e:
            self.manufacturers = []
            self.locations = []
            self.possible_MA_mod_par = []
            self.possible_MF = []
            self.possible_HY_HV = []
            self.possible_HY_LV = []
            self.last_responseText = str(e)

        if self.last_responseText[:3] != "200":
            self.api_status = 0
            self.progressbar.configure(progress_color=data.progress_color_ERROR)
            info_text = wrapped_text.fill(
                f"Error: Parents / Children could not be loaded from ProdDB API.\n{self.last_responseText}"
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color=data.progress_color_OK)

            self.combobox_child_manu.configure(
                values=["All manufacturers"]
                + [m["manufacturer_name"] for m in self.manufacturers]
            )
            self.combobox_MA_mod_par_manu.configure(
                values=["All manufacturers"]
                + [m["manufacturer_name"] for m in self.manufacturers]
            )
            self.combobox_MA_mod_par_loc.configure(
                values=["All locations"] + [m["location_name"] for m in self.locations]
            )
            self.combobox_MA_MF_child_loc.configure(
                values=["All locations"] + [m["location_name"] for m in self.locations]
            )
            self.combobox_MA_HY_HV_child_loc.configure(
                values=["All locations"] + [m["location_name"] for m in self.locations]
            )
            self.combobox_MA_HY_LV_child_loc.configure(
                values=["All locations"] + [m["location_name"] for m in self.locations]
            )

            # Module
            self.possible_MA_mod_par_SNs_and_partIDs = (
                util.get_relevant_SNs_and_partIDs(self.possible_MA_mod_par)
            )
            self.possible_MA_mod_par_SNs = [
                entry[0] for entry in self.possible_MA_mod_par_SNs_and_partIDs
            ]
            self.possible_MA_mod_par_SNs_chunked = [
                self.possible_MA_mod_par_SNs[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_MA_mod_par_SNs), self.n_items_to_show_in_cbx
                )
            ]
            self.possible_MA_mod_par_partIDs = [
                entry[1] for entry in self.possible_MA_mod_par_SNs_and_partIDs
            ]
            self.cbx_MA_mod_par_n_pages = len(self.possible_MA_mod_par_SNs_chunked)
            self.cbx_MA_mod_par_shown_page = 1
            self.label_combobox_MA_mod_par_paginationFrame.configure(
                text=f"page {self.cbx_MA_mod_par_shown_page}/{self.cbx_MA_mod_par_n_pages}"
            )
            self.combobox_MA_mod_par.configure(
                values=self.possible_MA_mod_par_SNs_chunked[0]
            )

            # Module Flex
            self.possible_MF_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(
                self.possible_MF
            )
            self.possible_MF_SNs = [
                entry[0] for entry in self.possible_MF_SNs_and_partIDs
            ]
            self.possible_MF_SNs_chunked = [
                self.possible_MF_SNs[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_MF_SNs), self.n_items_to_show_in_cbx
                )
            ]
            self.possible_MF_partIDs = [
                entry[1] for entry in self.possible_MF_SNs_and_partIDs
            ]
            self.cbx_MF_n_pages = len(self.possible_MF_SNs_chunked)
            self.cbx_MF_shown_page = 1
            self.label_combobox_MA_MF_chi_paginationFrame.configure(
                text=f"page {self.cbx_MF_shown_page}/{self.cbx_MF_n_pages}"
            )
            self.combobox_MA_MF_chi.configure(values=self.possible_MF_SNs_chunked[0])

            # Hybrid HV-side
            self.possible_HY_HV_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(
                self.possible_HY_HV
            )
            self.possible_HY_HV_SNs = [
                entry[0] for entry in self.possible_HY_HV_SNs_and_partIDs
            ]
            self.possible_HY_HV_SNs_chunked = [
                self.possible_HY_HV_SNs[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_HY_HV_SNs), self.n_items_to_show_in_cbx
                )
            ]
            self.possible_HY_HV_partIDs = [
                entry[1] for entry in self.possible_HY_HV_SNs_and_partIDs
            ]
            self.cbx_HY_HV_n_pages = len(self.possible_HY_HV_SNs_chunked)
            self.cbx_HY_HV_shown_page = 1
            self.label_combobox_HY_HV_paginationFrame.configure(
                text=f"page {self.cbx_HY_HV_shown_page}/{self.cbx_HY_HV_n_pages}"
            )
            self.combobox_MA_HY_HV_chi.configure(
                values=self.possible_HY_HV_SNs_chunked[0]
            )

            # Hybrid LV-side
            self.possible_HY_LV_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(
                self.possible_HY_LV
            )
            self.possible_HY_LV_SNs = [
                entry[0] for entry in self.possible_HY_LV_SNs_and_partIDs
            ]
            self.possible_HY_LV_SNs_chunked = [
                self.possible_HY_LV_SNs[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_HY_LV_SNs), self.n_items_to_show_in_cbx
                )
            ]
            self.possible_HY_LV_partIDs = [
                entry[1] for entry in self.possible_HY_LV_SNs_and_partIDs
            ]
            self.cbx_HY_LV_n_pages = len(self.possible_HY_LV_SNs_chunked)
            self.cbx_HY_LV_shown_page = 1
            self.label_combobox_HY_LV_paginationFrame.configure(
                text=f"page {self.cbx_HY_LV_shown_page}/{self.cbx_HY_LV_n_pages}"
            )
            self.combobox_MA_HY_LV_chi.configure(
                values=self.possible_HY_LV_SNs_chunked[0]
            )

    def authenticate_return_function(self, result, response):
        if response[:2] != "20":
            self.api_status = 0
            self.progressbar.configure(progress_color=data.progress_color_ERROR)

            info_text = wrapped_text.fill(
                f"Error: New user could not be authenticated.\n{response}"
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)

            self.optionmenu_user.set("None")
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color=data.progress_color_OK)

            self.label_info.configure(text=" ")

            self.user = result
            self.last_responseText = response

            old_users = self.users[:-1]  # all old ones without 'new...'
            if result not in old_users:
                new_users = old_users + [result, "new..."]
                self.users = new_users
                self.optionmenu_user.configure(values=new_users)
            self.optionmenu_user.set(result)

    def authenticate_user(self):
        # open a tiny window with extra inputs, return new_authenticated_user
        if self.user_window is None or not self.user_window.winfo_exists():
            self.user_window = AuthenticateWindow(
                self.authenticate_return_function
            )  # create window if its None or destroyed
        else:
            self.user_window.focus()  # if window exists focus it

    def button_add_child_module_flex_event_click(self, debug=False):
        chi = self.combobox_MA_MF_chi.get()
        par = self.combobox_MA_mod_par.get()
        pos = ""  # A relation between MF and MO does not require a position.
        if chi == "- Select -" or par == "- Select -":
            info_text = (
                "Warning: Select a child & parent from the respective lists to proceed."
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
        else:
            if self.user == "None" or self.user == "new...":
                info_text = "Error: Please login with your CERN account, because this operation requires a user name."
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
            else:
                self.label_info.configure(text=" ")
                chi_partID = self.possible_MF_partIDs[self.possible_MF_SNs.index(chi)]
                par_partID = self.possible_MA_mod_par_partIDs[
                    self.possible_MA_mod_par_SNs.index(par)
                ]
                part_tree = {
                    "position": pos,
                    "is_record_deleted": "F",
                    "part": chi_partID,
                    "part_parent": par_partID,
                    "record_insertion_user": self.user,
                }
                occupied = False
                confirmed = "OVERWRITE"
                try:
                    parents_of_target_MF, self.last_responseText = util.get_parents(
                        chi_partID, ofKind="Module"
                    )
                    if len(parents_of_target_MF) == 0:
                        children_of_targetMod, self.last_responseText = (
                            util.get_children(par_partID, ofKind="Module Flex")
                        )
                        MF_already_occupying_target_position = ""
                        Mod_MF_relation_to_delete = ""
                        # all children found are also matching (we have no position to fill with a MO to MF relation)
                        for c in children_of_targetMod:
                            occupied = True
                            MF_already_occupying_target_position = c["part"][
                                "serial_number"
                            ]
                            Mod_MF_relation_to_delete = c["record_id"]
                        if occupied:
                            confirmed = ""
                            dialog = customtkinter.CTkInputDialog(
                                text=f"This Module is already connected to (at least one) MF {MF_already_occupying_target_position}.\n"
                                + "Confirm by typing a confirmation: OVERWRITE to overwrite it with your selected MF:",
                                title="Confirm dialog",
                            )
                            confirmed = dialog.get_input()
                            if debug:
                                print(
                                    "Typed in confirmation from confirm dialog:",
                                    confirmed,
                                )
                            if confirmed == "OVERWRITE":
                                # DELETION OF PREVIOUS STUFF

                                # delete Mod -> MF relation for the MF that already connects to that Mod
                                for c in children_of_targetMod:
                                    self.last_responseText = api.delete_information(
                                        f"/partstreedelete/{c['record_id']}/"
                                    )

                                # POSTING NEW STUFF

                                # connect new MF there by creating a new Mod -> MF relation
                                self.last_responseText = api.post_information(
                                    "/partstreelist", part_tree, dryrun=False
                                )
                        else:
                            self.last_responseText = api.post_information(
                                "/partstreelist", part_tree, dryrun=False
                            )

                    else:
                        info_text = wrapped_text.fill(
                            f"Error: You can not connect this MF to the selected module.\nFirst you need to delete its existing relation to a module!"
                        )
                        print(f">>> {info_text}")
                        self.label_info.configure(text=info_text)

                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.last_responseText = str(e)

                if self.last_responseText[:2] != "20":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Parent / Child relations could not be fetched, deleted or posted to ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)
                    info_text = wrapped_text.fill(
                        f"Info: Child Module Flex added successfully to ProdDB API."
                    )

                    if len(parents_of_target_MF) == 0 and (
                        (occupied == False)
                        or (occupied == True and confirmed == "OVERWRITE")
                    ):
                        self.loading_wheel = threading.Thread(
                            target=self.fetch_MA_p_c, args=("Module Flex", info_text)
                        )
                        self.loading_wheel.start()
                        self.update_progressbar(self.loading_wheel)

    def button_add_child_HY_HV_event_click(self, debug=False):
        chi = self.combobox_MA_HY_HV_chi.get()
        par = self.combobox_MA_mod_par.get()
        pos = "HV"
        if chi == "- Select -" or par == "- Select -":
            info_text = (
                "Warning: Select a child & parent from the respective lists to proceed."
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
        else:
            if self.user == "None" or self.user == "new...":
                info_text = "Error: Please login with your CERN account, because this operation requires a user name."
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
            else:
                self.label_info.configure(text=" ")
                chi_partID = self.possible_HY_HV_partIDs[
                    self.possible_HY_HV_SNs.index(chi)
                ]
                par_partID = self.possible_MA_mod_par_partIDs[
                    self.possible_MA_mod_par_SNs.index(par)
                ]
                part_tree = {
                    "position": pos,
                    "is_record_deleted": "F",
                    "part": chi_partID,
                    "part_parent": par_partID,
                    "record_insertion_user": self.user,
                }
                occupied = False
                confirmed = "OVERWRITE"
                posted_new_rel = False
                try:
                    parents_of_target_HY, self.last_responseText = util.get_parents(
                        chi_partID, ofKind="Module"
                    )
                    if len(parents_of_target_HY) == 0:
                        children_of_targetMod, self.last_responseText = (
                            util.get_children(par_partID, ofKind="Hybrid")
                        )
                        HYs_already_occupying_target_position = []
                        occupied_target_positions = []
                        Mod_HY_relations_to_delete = []
                        # test whether sensor VBD clusters match (or something else that makes two hybrids form a good pair),
                        # if yes or the user confirms to connect another hybrid regardless, proceed
                        mismatch = False
                        confirmed_mismatch = "OVERWRITE"
                        for c in children_of_targetMod:
                            # need to check whether a hybrid occupies the module HV-side OR no particular position
                            # old relations between MO & HY did NOT enforce position attribute, so we are left with
                            # empty or invalid position attributes
                            # the only thing we can be sure about is that a hybrid that is connected on LV-side is
                            # harmless for the following operation, such potential relation does not need to be deleted
                            # similar for the other side (swap HV & LV)
                            if str(c["position"]) != "LV":
                                occupied = True
                                occupied_target_positions.append(c["position"])
                                HYs_already_occupying_target_position.append(
                                    c["part"]["serial_number"]
                                )
                                Mod_HY_relations_to_delete.append(c["record_id"])
                            else:
                                # ToDo: implement the actual call to something like child sensor of other hybrid
                                # or some attribute / measurement of the hybrid itself
                                if (
                                    str(c["part"]["serial_number"])
                                    == "something_that_tells_us_the_VBD_mismatch"
                                ):
                                    mismatch = True
                        if mismatch:
                            confirmed_mismatch = ""
                            dialog_mismatch = customtkinter.CTkInputDialog(
                                text=f"This Module is already connected to a LV-side HY"
                                + f" which does not match the VBD pairing cluster of your currently selected HV-side HY.\n"
                                + "Confirm by typing a confirmation: OVERWRITE to connect your selected HY irrespective of this mismatch:",
                                title="Confirm dialog",
                            )
                            confirmed_mismatch = dialog_mismatch.get_input()
                        if confirmed_mismatch == "OVERWRITE":
                            if occupied:
                                confirmed = ""
                                dialog = customtkinter.CTkInputDialog(
                                    text=f"This Module is already connected to the non-LV-side HY(s) {','.join(HYs_already_occupying_target_position)}\n"
                                    + f"at position(s) {','.join(occupied_target_positions)}.\n"
                                    + "Confirm by typing a confirmation: OVERWRITE to overwrite ALL known non-LV-side hybrid children of the selected parent module with your selected HY:",
                                    title="Confirm dialog",
                                )
                                confirmed = dialog.get_input()
                                if debug:
                                    print(
                                        "Typed in confirmation from confirm dialog:",
                                        confirmed,
                                    )
                                if confirmed == "OVERWRITE":
                                    # DELETION OF PREVIOUS STUFF

                                    # delete Mod -> HY relations for the HYs that already connect to that Mod
                                    for del_this in Mod_HY_relations_to_delete:
                                        self.last_responseText = api.delete_information(
                                            f"/partstreedelete/{del_this}/"
                                        )

                                    # POSTING NEW STUFF

                                    # connect new HY there by creating a new Mod -> HY relation
                                    self.last_responseText = api.post_information(
                                        "/partstreelist", part_tree, dryrun=False
                                    )
                                    posted_new_rel = True
                            else:
                                self.last_responseText = api.post_information(
                                    "/partstreelist", part_tree, dryrun=False
                                )
                                posted_new_rel = True

                    else:
                        info_text = wrapped_text.fill(
                            f"Error: You can not connect this hybrid to the selected module.\nFirst you need to delete its existing relation to a module!"
                        )
                        print(f">>> {info_text}")
                        self.label_info.configure(text=info_text)

                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.last_responseText = str(e)

                if self.last_responseText[:2] != "20":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Parent / Child relations could not be fetched, deleted or posted to ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)
                    info_text = wrapped_text.fill(
                        f"Info: Child HV Hybrid added successfully to ProdDB API."
                    )

                    if posted_new_rel:
                        self.loading_wheel = threading.Thread(
                            target=self.fetch_MA_p_c, args=("HY_HV", info_text)
                        )
                        self.loading_wheel.start()
                        self.update_progressbar(self.loading_wheel)

    def button_add_child_HY_LV_event_click(self, debug=False):
        chi = self.combobox_MA_HY_LV_chi.get()
        par = self.combobox_MA_mod_par.get()
        pos = "LV"
        if chi == "- Select -" or par == "- Select -":
            info_text = (
                "Warning: Select a child & parent from the respective lists to proceed."
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
        else:
            if self.user == "None" or self.user == "new...":
                info_text = "Error: Please login with your CERN account, because this operation requires a user name."
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
            else:
                self.label_info.configure(text=" ")
                chi_partID = self.possible_HY_LV_partIDs[
                    self.possible_HY_LV_SNs.index(chi)
                ]
                par_partID = self.possible_MA_mod_par_partIDs[
                    self.possible_MA_mod_par_SNs.index(par)
                ]
                part_tree = {
                    "position": pos,
                    "is_record_deleted": "F",
                    "part": chi_partID,
                    "part_parent": par_partID,
                    "record_insertion_user": self.user,
                }
                occupied = False
                confirmed = "OVERWRITE"
                posted_new_rel = False
                try:
                    parents_of_target_HY, self.last_responseText = util.get_parents(
                        chi_partID, ofKind="Module"
                    )
                    if len(parents_of_target_HY) == 0:
                        children_of_targetMod, self.last_responseText = (
                            util.get_children(par_partID, ofKind="Hybrid")
                        )
                        HYs_already_occupying_target_position = []
                        occupied_target_positions = []
                        Mod_HY_relations_to_delete = []
                        # test whether sensor VBD clusters match (or something else that makes two hybrids form a good pair),
                        # if yes or the user confirms to connect another hybrid regardless, proceed
                        mismatch = False
                        confirmed_mismatch = "OVERWRITE"
                        for c in children_of_targetMod:
                            # need to check whether a hybrid occupies the module LV-side OR no particular position
                            # old relations between MO & HY did NOT enforce position attribute, so we are left with
                            # empty or invalid position attributes
                            # the only thing we can be sure about is that a hybrid that is connected on HV-side is
                            # harmless for the following operation, such potential relation does not need to be deleted
                            # similar for the other side (swap HV & LV)
                            if str(c["position"]) != "HV":
                                occupied = True
                                occupied_target_positions.append(c["position"])
                                HYs_already_occupying_target_position.append(
                                    c["part"]["serial_number"]
                                )
                                Mod_HY_relations_to_delete.append(c["record_id"])
                            else:
                                # ToDo: implement the actual call to something like child sensor of other hybrid
                                # or some attribute / measurement of the hybrid itself
                                if (
                                    str(c["part"]["serial_number"])
                                    == "something_that_tells_us_the_VBD_mismatch"
                                ):
                                    mismatch = True
                        if mismatch:
                            confirmed_mismatch = ""
                            dialog_mismatch = customtkinter.CTkInputDialog(
                                text=f"This Module is already connected to a HV-side HY"
                                + f" which does not match the VBD pairing cluster of your currently selected LV-side HY.\n"
                                + "Confirm by typing a confirmation: OVERWRITE to connect your selected HY irrespective of this mismatch:",
                                title="Confirm dialog",
                            )
                            confirmed_mismatch = dialog_mismatch.get_input()
                        if confirmed_mismatch == "OVERWRITE":
                            if occupied:
                                confirmed = ""
                                dialog = customtkinter.CTkInputDialog(
                                    text=f"This Module is already connected to the non-HV-side HY(s) {','.join(HYs_already_occupying_target_position)}\n"
                                    + f"at position(s) {','.join(occupied_target_positions)}.\n"
                                    + "Confirm by typing a confirmation: OVERWRITE to overwrite ALL known non-HV-side hybrid children of the selected parent module with your selected HY:",
                                    title="Confirm dialog",
                                )
                                confirmed = dialog.get_input()
                                if debug:
                                    print(
                                        "Typed in confirmation from confirm dialog:",
                                        confirmed,
                                    )
                                if confirmed == "OVERWRITE":
                                    # DELETION OF PREVIOUS STUFF

                                    # delete Mod -> HY relations for the HYs that already connect to that Mod
                                    for del_this in Mod_HY_relations_to_delete:
                                        self.last_responseText = api.delete_information(
                                            f"/partstreedelete/{del_this}/"
                                        )

                                    # POSTING NEW STUFF

                                    # connect new HY there by creating a new Mod -> HY relation
                                    self.last_responseText = api.post_information(
                                        "/partstreelist", part_tree, dryrun=False
                                    )
                                    posted_new_rel = True
                            else:
                                self.last_responseText = api.post_information(
                                    "/partstreelist", part_tree, dryrun=False
                                )
                                posted_new_rel = True

                    else:
                        info_text = wrapped_text.fill(
                            f"Error: You can not connect this hybrid to the selected module.\nFirst you need to delete its existing relation to a module!"
                        )
                        print(f">>> {info_text}")
                        self.label_info.configure(text=info_text)

                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.last_responseText = str(e)

                if self.last_responseText[:2] != "20":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Parent / Child relations could not be fetched, deleted or posted to ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)
                    info_text = wrapped_text.fill(
                        f"Info: Child LV Hybrid added successfully to ProdDB API."
                    )

                    if posted_new_rel:
                        self.loading_wheel = threading.Thread(
                            target=self.fetch_MA_p_c, args=("HY_LV", info_text)
                        )
                        self.loading_wheel.start()
                        self.update_progressbar(self.loading_wheel)

    def button_add_ft_event_click(self, debug=False):
        chi = self.combobox_ft.get()
        par = self.combined_slot
        if chi == "- Select -" or par == "":
            info_text = (
                "Warning: Select a FT & Slot from the respective lists to proceed."
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
        else:
            if self.user == "None" or self.user == "new...":
                info_text = "Error: Please login with your CERN account, because this operation requires a user name."
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
            else:
                self.label_info.configure(text=" ")
                chi_partID = self.possible_ft_partIDs[self.possible_ft_SNs.index(chi)]
                for s in self.slots:
                    if str(s["part_serial_number"]) == str(par):
                        par_partID = s["part_id"]
                        connects_to_PEB_type = s["PEB_type"]
                        connects_to_DU_type = s["SU_type"]
                        break
                part_tree = {
                    "position": "",
                    "is_record_deleted": "F",
                    "part": chi_partID,
                    "part_parent": par_partID,
                    "record_insertion_user": self.user,
                }
                allowed_slot = False
                occupied_slot = False
                confirmed = ""
                try:
                    # allowed: chosen FT matches the generation and category that the slot requires
                    gen = self.ft_filter.split("+")[0].split(
                        "/"
                    )  # multiple generations
                    cat = self.ft_filter[-2:]  # the last two chars make the category
                    if any(gen_ in chi for gen_ in gen) and int(chi[9:11]) == int(cat):
                        allowed_slot = True
                        children_of_targetSlot, self.last_responseText = (
                            util.get_children(par_partID, ofKind="Flex Tail")
                        )
                        FT_already_occupying_target_position = ""
                        Slot_FT_relation_to_delete = ""
                        matching_partIDs = []
                        matching_relations = []
                        for c in children_of_targetSlot:
                            occupied_slot = True
                            FT_already_occupying_target_position = c["part"][
                                "serial_number"
                            ]
                            Slot_FT_relation_to_delete = c["record_id"]
                            matching_relations.append(c)
                            matching_partIDs.append(c["part"]["part_id"])
                            break
                        if occupied_slot:
                            confirmed = ""
                            dialog = customtkinter.CTkInputDialog(
                                text=f"This Slot is already occupied by (at least one) FT {FT_already_occupying_target_position}.\n"
                                + "Confirm by typing a confirmation: OVERWRITE to overwrite it with your selected FT:",
                                title="Confirm dialog",
                            )
                            confirmed = dialog.get_input()
                            if debug:
                                print(
                                    "Typed in confirmation from confirm dialog:",
                                    confirmed,
                                )
                            if confirmed == "OVERWRITE":
                                # DELETION OF PREVIOUS STUFF

                                # delete Slot -> FT relation for the FT that already occupies that Slot
                                # the deletion of slot relations will be done as part of parent deletion
                                # but not only that, we need to delete the already occupying FTs' parents (all of them, Slot, DU, PEB, MO)
                                for occ_pid in matching_partIDs:
                                    self.last_responseText = util.delete_parents(
                                        occ_pid
                                    )

                        # POSTING NEW STUFF

                        # connect new FT there by creating a new Slot -> FT relation
                        self.last_responseText = api.post_information(
                            "/partstreelist", part_tree, dryrun=False
                        )

                        # mod to connect FT to
                        mod_for_FT, self.last_responseText = util.get_children(
                            par_partID, ofKind="Module"
                        )
                        if len(mod_for_FT) > 0:
                            for mFT in mod_for_FT:
                                parentMod_for_FT_partID = mFT["part"]["part_id"]
                                part_tree = {
                                    "position": "",
                                    "is_record_deleted": "F",
                                    "part": chi_partID,
                                    "part_parent": parentMod_for_FT_partID,
                                    "record_insertion_user": self.user,
                                }
                                self.last_responseText = api.post_information(
                                    "/partstreelist", part_tree, dryrun=False
                                )

                                # the DU this FT will connect to
                                mod_in_DU, self.last_responseText = util.get_parents(
                                    parentMod_for_FT_partID, ofKind="Detector Unit"
                                )
                                if len(mod_in_DU) > 0:
                                    for du_rel in mod_in_DU:
                                        if debug:
                                            print(du_rel)
                                        part_tree = {
                                            "position": du_rel["position"],
                                            "is_record_deleted": "F",
                                            "part": chi_partID,
                                            "part_parent": du_rel["part_parent"][
                                                "part_id"
                                            ],
                                            "record_insertion_user": self.user,
                                        }
                                        self.last_responseText = api.post_information(
                                            "/partstreelist", part_tree, dryrun=False
                                        )

                                    # the PEB this FT will connect to
                                    (
                                        all_PEB_childs_of_mainDet,
                                        self.last_responseText,
                                    ) = util.get_children(
                                        data.partID_parent_Detector, ofKind="PEB"
                                    )
                                    found_PEB_for_FT = False
                                    for peb_rel in all_PEB_childs_of_mainDet:
                                        if (
                                            str(peb_rel["position"])
                                            == f"V{par[1]}L{par[4]}Q{par[7]}"
                                        ):
                                            # it's for the correct quadrant
                                            if str(connects_to_PEB_type) == str(
                                                peb_rel["part"]["serial_number"][9:11]
                                            ):
                                                # it's also correct type of PEB sitting there
                                                # so we can connect the FT to this PEB
                                                found_PEB_for_FT = True
                                                part_tree = {
                                                    "position": du_rel["position"],
                                                    "is_record_deleted": "F",
                                                    "part": chi_partID,
                                                    "part_parent": peb_rel["part"][
                                                        "part_id"
                                                    ],
                                                    "record_insertion_user": self.user,
                                                }
                                                self.last_responseText = (
                                                    api.post_information(
                                                        "/partstreelist",
                                                        part_tree,
                                                        dryrun=False,
                                                    )
                                                )
                                                break
                                    if not found_PEB_for_FT:
                                        info_text = wrapped_text.fill(
                                            f"Error: You can not connect this FT to the selected slot.\nThere is no PEB on the cooling plate!"
                                        )
                                        print(f">>> {info_text}")
                                        self.label_info.configure(text=info_text)
                                else:
                                    info_text = wrapped_text.fill(
                                        f"Error: You can not connect this FT to the selected slot.\nThere is no detector unit on the cooling plate!"
                                    )
                                    print(f">>> {info_text}")
                                    self.label_info.configure(text=info_text)
                        else:
                            info_text = wrapped_text.fill(
                                f"Error: You can not connect this FT to the selected slot.\nThere is no module occupying this slot!"
                            )
                            print(f">>> {info_text}")
                            self.label_info.configure(text=info_text)
                    else:
                        info_text = wrapped_text.fill(
                            f"Error: You can not connect this FT to the selected slot.\nCheck the FT generation and FT category requirements!"
                        )
                        print(f">>> {info_text}")
                        self.label_info.configure(text=info_text)

                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.last_responseText = str(e)

                if self.last_responseText[:2] != "20":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Parent / Child relations could not be fetched, deleted or posted to ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)

                    self.combobox_ft.set("- Select -")
                    self.this_FT_relations_SLOT = []
                    self.loading_wheel = threading.Thread(target=self.fetch_ft)
                    self.loading_wheel.start()
                    self.update_progressbar(self.loading_wheel)

    def button_add_event_click(self, debug=False):
        chi = self.combobox_child.get()
        par = self.combobox_parent.get()
        pos = self.position_entry.get()
        if (
            chi == "- Select -"
            or par == "- Select -"
            or pos == "- automatic -"
            or pos == "VxLyQz"
        ):
            info_text = "Warning: Select a child & parent from the respective lists and a position to proceed."
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
        else:
            if self.user == "None" or self.user == "new...":
                info_text = "Error: Please login with your CERN account, because this operation requires a user name."
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
            else:
                self.label_info.configure(text=" ")
                chi_partID = self.possible_children_partIDs[
                    self.possible_children_SNs.index(chi)
                ]
                par_partID = self.possible_parents_partIDs[
                    self.possible_parents_SNs.index(par)
                ]
                part_tree = {
                    "position": pos,
                    "is_record_deleted": "F",
                    "part": chi_partID,
                    "part_parent": par_partID,
                    "record_insertion_user": self.user,
                }
                allowed_VLQ = False
                occupied_VLQ = False
                confirmed = pos
                try:
                    if self.operation_mode == "Module Loading":
                        self.last_responseText = api.post_information(
                            "/partstreelist", part_tree, dryrun=False
                        )

                        self.displayedDUtype = "None"
                        self.this_DU_relations_MODULE = []
                        self.this_MODULE_relations_DU = []
                        self.this_MODULE_relations_SLOT = []
                        self.possible_parents = []
                        self.possible_children = []
                        self.slots = None
                        self.partstree = None

                        self.loading_wheel = threading.Thread(
                            target=self.fetch_loaded_DU_and_display, args=(chi, par)
                        )
                        self.loading_wheel.start()
                        self.update_progressbar(self.loading_wheel)
                    elif self.operation_mode == "Detector Assembly (CERN): DU":
                        attribute_Vessel = pos.split("V").pop().split("L")[0]
                        if attribute_Vessel not in ["1", "2", "M", "D"]:
                            info_text = wrapped_text.fill(
                                f"Error: You can not load to this vessel.\nVessel attribute only accepts 1, 2, M, or D, but you selected {attribute_Vessel}!"
                            )
                            print(f">>> {info_text}")
                            self.label_info.configure(text=info_text)
                        else:
                            attribute_Layer = pos.split("L").pop().split("Q")[0]
                            if attribute_Layer not in ["0", "1", "2", "3"]:
                                info_text = wrapped_text.fill(
                                    f"Error: You can not load to this layer.\nLayer attribute only accepts 0, 1, 2, or 3, but you selected {attribute_Layer}!"
                                )
                                print(f">>> {info_text}")
                                self.label_info.configure(text=info_text)
                            else:
                                if attribute_Layer == "0" or attribute_Layer == "3":
                                    allowed_type = "F"
                                    not_allowed_type = "B"
                                else:  # elif attribute_Layer == '1' or attribute_Layer == '2':
                                    allowed_type = "B"
                                    not_allowed_type = "F"
                                if self.displayedDUtype[0] == not_allowed_type:
                                    info_text = wrapped_text.fill(
                                        f"Error: You can not load this DU to this layer.\nLayer {attribute_Layer} only accepts {allowed_type} DUs, but you selected a {self.displayedDUtype[0]} DU!"
                                    )
                                    print(f">>> {info_text}")
                                    self.label_info.configure(text=info_text)
                                else:
                                    attribute_Quadrant = pos.split("Q").pop()
                                    if attribute_Quadrant not in ["0", "1", "2", "3"]:
                                        info_text = wrapped_text.fill(
                                            f"Error: You can not load to this quadrant.\nQuadrant attribute only accepts 0, 1, 2, or 3, but you selected {attribute_Quadrant}!"
                                        )
                                        print(f">>> {info_text}")
                                        self.label_info.configure(text=info_text)
                                    else:
                                        allowed_VLQ = True
                                        # make sure to only check for DU children KoP, nothing else
                                        (
                                            children_of_targetDetector,
                                            self.last_responseText,
                                        ) = util.get_children(
                                            par_partID, ofKind="Detector Unit"
                                        )
                                        DU_already_occupying_target_position = ""
                                        Det_DU_relation_to_delete = ""
                                        matching_relations = []
                                        for c in children_of_targetDetector:
                                            # position of Det child is the same as the desired one, and DU type of desired DU is same as the one that already occupies the spot:
                                            if (
                                                str(c["position"]) == pos
                                                and self.displayedDUtype
                                                in c["part"]["serial_number"]
                                            ):
                                                occupied_VLQ = True
                                                DU_already_occupying_target_position = (
                                                    c["part"]["serial_number"]
                                                )
                                                Det_DU_relation_to_delete = c[
                                                    "record_id"
                                                ]
                                                matching_relations.append(c)
                                                break

                                        if occupied_VLQ:
                                            confirmed = ""
                                            dialog = customtkinter.CTkInputDialog(
                                                text=f"This Vessel Layer Quadrant is already occupied by (at least one) DU {DU_already_occupying_target_position}.\n"
                                                + "Confirm by typing the desired Vessel Layer Quadrant (VxLyQz) again to overwrite it with your selected DU:",
                                                title="Confirm dialog",
                                            )
                                            confirmed = dialog.get_input()
                                            if debug:
                                                print(
                                                    "Typed in slot from confirm dialog:",
                                                    confirmed,
                                                )
                                            if confirmed == pos:
                                                # DELETION OF PREVIOUS STUFF

                                                # delete Det -> DU relation for the DUs that already occupy that VLQ
                                                for c in matching_relations:
                                                    self.last_responseText = api.delete_information(
                                                        f"/partstreedelete/{c['record_id']}/"
                                                    )
                                                    # get children modules of the DU that previously occupied the VLQ
                                                    (
                                                        affected_previous_modules,
                                                        self.last_responseText,
                                                    ) = util.get_children(
                                                        c["part"]["part_id"],
                                                        ofKind="Module",
                                                    )
                                                    # the parent slots of modules of the DU that previously occupied the VLQ
                                                    for a in affected_previous_modules:
                                                        (
                                                            affected_parents_of_children,
                                                            self.last_responseText,
                                                        ) = util.get_parents(
                                                            a["part"]["part_id"],
                                                            ofKind="Slot",
                                                        )
                                                        for (
                                                            p
                                                        ) in (
                                                            affected_parents_of_children
                                                        ):
                                                            # delete those Slot -> Mod relations
                                                            if debug:
                                                                print(
                                                                    str(
                                                                        p[
                                                                            "part_parent"
                                                                        ][
                                                                            "kind_of_part"
                                                                        ][
                                                                            "kind_of_part_id"
                                                                        ]
                                                                    )
                                                                )
                                                                print(
                                                                    "Delete Slot -> Module relation",
                                                                    p,
                                                                )
                                                            self.last_responseText = api.delete_information(
                                                                f"/partstreedelete/{p['record_id']}/"
                                                            )

                                                # POSTING NEW STUFF

                                                # place new DU at this position by creating a new Det -> DU relation
                                                self.last_responseText = (
                                                    api.post_information(
                                                        "/partstreelist",
                                                        part_tree,
                                                        dryrun=False,
                                                    )
                                                )
                                                self.canvas.itemconfig(
                                                    self.duAlreadyPlacedText,
                                                    text=f"Now placed at:\n{pos}",
                                                )
                                        else:
                                            self.last_responseText = (
                                                api.post_information(
                                                    "/partstreelist",
                                                    part_tree,
                                                    dryrun=False,
                                                )
                                            )
                                            self.canvas.itemconfig(
                                                self.duAlreadyPlacedText,
                                                text=f"Now placed at:\n{pos}",
                                            )
                    elif self.operation_mode == "Detector Assembly (CERN): PEB":
                        attribute_Vessel = pos.split("V").pop().split("L")[0]
                        if attribute_Vessel not in ["1", "2", "M", "D"]:
                            info_text = wrapped_text.fill(
                                f"Error: You can not load to this vessel.\nVessel attribute only accepts 1, 2, M, or D, but you selected {attribute_Vessel}!"
                            )
                            print(f">>> {info_text}")
                            self.label_info.configure(text=info_text)
                        else:
                            if (
                                attribute_Vessel in ["D"]
                                and self.displayed_PEB_type != "1F"
                            ):
                                info_text = wrapped_text.fill(
                                    f"Error: You can not load to this vessel (demonstrator).\nDemonstratorV1 only accepts PEB type 1F, but you selected a PEB of type {self.displayed_PEB_type}!"
                                )
                                print(f">>> {info_text}")
                                self.label_info.configure(text=info_text)
                            else:
                                attribute_Layer = pos.split("L").pop().split("Q")[0]
                                if attribute_Layer not in ["0", "1", "2", "3"]:
                                    info_text = wrapped_text.fill(
                                        f"Error: You can not load to this layer.\nLayer attribute only accepts 0, 1, 2, or 3, but you selected {attribute_Layer}!"
                                    )
                                    print(f">>> {info_text}")
                                    self.label_info.configure(text=info_text)
                                else:
                                    if attribute_Layer == "0" or attribute_Layer == "3":
                                        allowed_types = data.F_PEBs
                                        not_allowed_type = "3B"
                                    else:  # elif attribute_Layer == '1' or attribute_Layer == '2':
                                        allowed_types = data.B_PEBs
                                        not_allowed_type = "3F"
                                    if self.displayed_PEB_type == not_allowed_type:
                                        info_text = wrapped_text.fill(
                                            f"Error: You can not load this PEB to this layer.\nLayer {attribute_Layer} only accepts {allowed_types} PEBs, but you selected a {self.displayed_PEB_type} PEB!"
                                        )
                                        print(f">>> {info_text}")
                                        self.label_info.configure(text=info_text)
                                    else:
                                        attribute_Quadrant = pos.split("Q").pop()
                                        if attribute_Quadrant not in [
                                            "0",
                                            "1",
                                            "2",
                                            "3",
                                        ]:
                                            info_text = wrapped_text.fill(
                                                f"Error: You can not load to this quadrant.\nQuadrant attribute only accepts 0, 1, 2, or 3, but you selected {attribute_Quadrant}!"
                                            )
                                            print(f">>> {info_text}")
                                            self.label_info.configure(text=info_text)
                                        else:
                                            allowed_VLQ = True
                                            # make sure to only check for PEB children KoP, nothing else
                                            (
                                                children_of_targetDetector,
                                                self.last_responseText,
                                            ) = util.get_children(
                                                par_partID, ofKind="PEB"
                                            )
                                            PEB_already_occupying_target_position = ""
                                            Det_PEB_relation_to_delete = ""
                                            matching_relations = []
                                            for c in children_of_targetDetector:
                                                # position of Det child is the same as the desired one, and PEB type of desired PEB is same as the one that already occupies the spot:
                                                if str(c["position"]) == pos:
                                                    # == OLD ==: previous schema did not include PEB Type in PEB SN
                                                    # == OLD ==:  => used to need to fetch the attributes of maybe occupying children PEBs, because PEB type was only part of attributes (not part of SN sadly)
                                                    # == OLD ==: child_attributes, self.last_responseText = api.fetch_information(f'/partattrlist/{c['part']['part_id']}/')
                                                    # == OLD ==: PEB_type_occupying = [c for c in child_attributes if c['attribute']['name'] == 'Type'][0]['value']
                                                    # NEW: PEB type is part of PEB SN!
                                                    if (
                                                        self.displayed_PEB_type
                                                        in c["part"]["serial_number"]
                                                    ):
                                                        occupied_VLQ = True
                                                        PEB_already_occupying_target_position = c[
                                                            "part"
                                                        ][
                                                            "serial_number"
                                                        ]
                                                        Det_PEB_relation_to_delete = c[
                                                            "record_id"
                                                        ]
                                                        matching_relations.append(c)
                                                        break
                                            if occupied_VLQ:
                                                confirmed = ""
                                                dialog = customtkinter.CTkInputDialog(
                                                    text=f"This Vessel Layer Quadrant is already occupied by (at least one) PEB {PEB_already_occupying_target_position}.\n"
                                                    + "Confirm by typing the desired Vessel Layer Quadrant (VxLyQz) again to overwrite it with your selected PEB:",
                                                    title="Confirm dialog",
                                                )
                                                confirmed = dialog.get_input()
                                                if debug:
                                                    print(
                                                        "Typed in slot from confirm dialog:",
                                                        confirmed,
                                                    )
                                                if confirmed == pos:
                                                    # DELETION OF PREVIOUS STUFF

                                                    # delete Det -> PEB relation for the PEB that already occupies that VLQ
                                                    for c in matching_relations:
                                                        self.last_responseText = api.delete_information(
                                                            f"/partstreedelete/{c['record_id']}/"
                                                        )

                                                    # POSTING NEW STUFF

                                                    # place new DU at this position by creating a new Det -> PEB relation
                                                    self.last_responseText = (
                                                        api.post_information(
                                                            "/partstreelist",
                                                            part_tree,
                                                            dryrun=False,
                                                        )
                                                    )
                                            else:
                                                self.last_responseText = (
                                                    api.post_information(
                                                        "/partstreelist",
                                                        part_tree,
                                                        dryrun=False,
                                                    )
                                                )

                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.last_responseText = str(e)

                if self.last_responseText[:2] != "20":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Parent / Child relations could not be fetched, deleted or posted to ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)

                    if (
                        self.operation_mode == "Detector Assembly (CERN): DU"
                        and allowed_VLQ
                        and ((occupied_VLQ and confirmed == pos) or not occupied_VLQ)
                    ):
                        # find all existing relations between this DU and its Modules, those are propagated to create new Slot -> Module relations
                        self.loading_wheel_A = threading.Thread(
                            target=self.fetch_and_write_module_slots,
                            args=(
                                attribute_Vessel,
                                attribute_Layer,
                                attribute_Quadrant,
                            ),
                        )
                        self.loading_wheel_A.start()
                        self.update_progressbar(self.loading_wheel_A)

    # Combobox page selection by pressing a button to go left or right (previous page / next page)
    def button_combobox_paginationButton_click(self, affects, page_dir):
        if affects == "MA-MO":
            (
                affected_cbx_shown_page,
                affected_label_cbx_page,
                affected_cbx_n_pages,
                affected_cbx_part,
                affected_cbx_possible_SNs_chunked,
            ) = (
                self.cbx_MA_mod_par_shown_page,
                self.label_combobox_MA_mod_par_paginationFrame,
                self.cbx_MA_mod_par_n_pages,
                self.combobox_MA_mod_par,
                self.possible_MA_mod_par_SNs_chunked,
            )
        elif affects == "MA-MF":
            (
                affected_cbx_shown_page,
                affected_label_cbx_page,
                affected_cbx_n_pages,
                affected_cbx_part,
                affected_cbx_possible_SNs_chunked,
            ) = (
                self.cbx_MF_shown_page,
                self.label_combobox_MA_MF_chi_paginationFrame,
                self.cbx_MF_n_pages,
                self.combobox_MA_MF_chi,
                self.possible_MF_SNs_chunked,
            )

        elif affects == "MA-Hybrid-HV":
            (
                affected_cbx_shown_page,
                affected_label_cbx_page,
                affected_cbx_n_pages,
                affected_cbx_part,
                affected_cbx_possible_SNs_chunked,
            ) = (
                self.cbx_HY_HV_shown_page,
                self.label_combobox_HY_HV_paginationFrame,
                self.cbx_HY_HV_n_pages,
                self.combobox_MA_HY_HV_chi,
                self.possible_HY_HV_SNs_chunked,
            )

        elif affects == "MA-Hybrid-LV":
            (
                affected_cbx_shown_page,
                affected_label_cbx_page,
                affected_cbx_n_pages,
                affected_cbx_part,
                affected_cbx_possible_SNs_chunked,
            ) = (
                self.cbx_HY_LV_shown_page,
                self.label_combobox_HY_LV_paginationFrame,
                self.cbx_HY_LV_n_pages,
                self.combobox_MA_HY_LV_chi,
                self.possible_HY_LV_SNs_chunked,
            )

        elif affects == "FT":
            (
                affected_cbx_shown_page,
                affected_label_cbx_page,
                affected_cbx_n_pages,
                affected_cbx_part,
                affected_cbx_possible_SNs_chunked,
            ) = (
                self.cbx_ft_shown_page,
                self.label_combobox_ft_paginationFrame,
                self.cbx_ft_n_pages,
                self.combobox_ft,
                self.possible_ft_SNs_chunked,
            )

        elif affects == "DA-chi-SN":
            (
                affected_cbx_shown_page,
                affected_label_cbx_page,
                affected_cbx_n_pages,
                affected_cbx_part,
                affected_cbx_possible_SNs_chunked,
            ) = (
                self.cbx_chi_shown_page,
                self.label_combobox_child_paginationFrame,
                self.cbx_chi_n_pages,
                self.combobox_child,
                self.possible_children_SNs_chunked,
            )

        elif affects == "DA-par-SN":
            (
                affected_cbx_shown_page,
                affected_label_cbx_page,
                affected_cbx_n_pages,
                affected_cbx_part,
                affected_cbx_possible_SNs_chunked,
            ) = (
                self.cbx_par_shown_page,
                self.label_combobox_parent_paginationFrame,
                self.cbx_par_n_pages,
                self.combobox_parent,
                self.possible_parents_SNs_chunked,
            )

        elif affects == "DA-chi-type":
            (
                affected_cbx_shown_page,
                affected_label_cbx_page,
                affected_cbx_n_pages,
                affected_cbx_part,
                affected_cbx_possible_SNs_chunked,
            ) = (
                self.cbx_ctype_shown_page,
                self.label_combobox_chi_type_paginationFrame,
                self.cbx_ctype_n_pages,
                self.combobox_chi_type,
                self.possible_chi_types_chunked,
            )

        elif affects == "DA-par-type":
            (
                affected_cbx_shown_page,
                affected_label_cbx_page,
                affected_cbx_n_pages,
                affected_cbx_part,
                affected_cbx_possible_SNs_chunked,
            ) = (
                self.cbx_ptype_shown_page,
                self.label_combobox_par_type_paginationFrame,
                self.cbx_ptype_n_pages,
                self.combobox_par_type,
                self.possible_par_types_chunked,
            )
        else:
            raise NotImplementedError("Pagination not refactored for this combobox!")

        if page_dir == "L":
            affected_cbx_shown_page = (
                max(affected_cbx_shown_page - 1, 1) if affected_cbx_n_pages > 0 else 0
            )
        elif page_dir == "R":
            affected_cbx_shown_page = (
                min(affected_cbx_shown_page + 1, affected_cbx_n_pages)
                if affected_cbx_n_pages > 0
                else 0
            )
        else:
            raise NotImplementedError(
                "Can only go left (L) or right (R) in pagination frame!"
            )

        # one variable must be written back on a case-by-case basis,
        # others are just updating on-the-fly by configure
        if affects == "MA-MO":
            self.cbx_MA_mod_par_shown_page = affected_cbx_shown_page
        elif affects == "MA-MF":
            self.cbx_MF_shown_page = affected_cbx_shown_page
        elif affects == "MA-Hybrid-HV":
            self.cbx_HY_HV_shown_page = affected_cbx_shown_page
        elif affects == "MA-Hybrid-LV":
            self.cbx_HY_LV_shown_page = affected_cbx_shown_page
        elif affects == "FT":
            self.cbx_ft_shown_page = affected_cbx_shown_page
        elif affects == "DA-chi-SN":
            self.cbx_chi_shown_page = affected_cbx_shown_page
        elif affects == "DA-par-SN":
            self.cbx_par_shown_page = affected_cbx_shown_page
        elif affects == "DA-chi-type":
            self.cbx_ctype_shown_page = affected_cbx_shown_page
        elif affects == "DA-par-type":
            self.cbx_ptype_shown_page = affected_cbx_shown_page
        affected_label_cbx_page.configure(
            text=f"page {affected_cbx_shown_page}/{affected_cbx_n_pages}"
        )
        if affected_cbx_n_pages > 0:
            affected_cbx_part.configure(
                values=affected_cbx_possible_SNs_chunked[affected_cbx_shown_page - 1]
            )
        else:
            affected_cbx_part.configure(values=[])
            affected_cbx_part.set("- Select -")

    def button_delete_connected_ft_event_click(self):
        if len(self.this_FT_relations_SLOT) > 0:
            if self.user == "None" or self.user == "new...":
                info_text = "Error: Please login with your CERN account, because this operation requires a user name."
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
            else:
                self.label_info.configure(text=" ")
                try:
                    for k in self.this_FT_relations_SLOT:
                        # this already deletes ALL relations of this FT to any parent, including: Slot, DU, PEB, MO
                        self.last_responseText = util.delete_parents(
                            k["part"]["part_id"]
                        )
                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.last_responseText = str(e)

                if self.last_responseText[:2] != "20":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Existing FT relation could not be deleted (disconnected from slot) with ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)
                    self.label_info.configure(text=" ")
                    self.this_FT_relations_SLOT = []
                    self.button_delete_connected_ft.configure(state="disabled")

    def button_delete_clicked_event_click(self):
        if len(self.clicked_module) > 0:
            if self.user == "None" or self.user == "new...":
                info_text = "Error: Please login with your CERN account, because this operation requires a user name."
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
            else:
                self.label_info.configure(text=" ")
                try:
                    self.last_responseText = util.delete_parents(
                        self.clicked_module["part"]["part_id"]
                    )
                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.last_responseText = str(e)

                if self.last_responseText[:2] != "20":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Existing module relation could not be deleted (unloaded) with ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)

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
                    self.button_inspect_clicked.configure(
                        text=f"INSPECT CLICKED MODULE"
                    )
                    self.button_inspect_clicked.configure(state="disabled")
                    self.button_delete_clicked.configure(text=f"UNLOAD CLICKED MODULE")
                    self.button_delete_clicked.configure(state="disabled")

                    parentSNIn = self.combobox_parent.get()
                    childSNIn = self.combobox_child.get()
                    self.loading_wheel = threading.Thread(
                        target=self.fetch_loaded_DU_and_display,
                        args=(childSNIn, parentSNIn),
                    )
                    self.loading_wheel.start()
                    self.update_progressbar(self.loading_wheel)

    def button_delete_child_module_flex_event_click(self):
        if len(self.this_MF_relations_MOD) > 0:
            if self.user == "None" or self.user == "new...":
                info_text = "Error: Please login with your CERN account, because this operation requires a user name."
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
            else:
                self.label_info.configure(text=" ")
                try:
                    for k in self.this_MF_relations_MOD:
                        self.last_responseText = util.delete_parents(
                            k["part"]["part_id"], ofKind="Module"
                        )
                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.last_responseText = str(e)

                if self.last_responseText[:2] != "20":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Existing MF relation could not be deleted (disconnected from module) with ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)
                    self.label_info.configure(text=" ")
                    self.this_MF_relations_MOD = []
                    self.button_delete_child_MF.configure(state="disabled")

    def button_delete_child_HY_HV_event_click(self):
        if len(self.this_HY_HV_relations_MOD) > 0:
            if self.user == "None" or self.user == "new...":
                info_text = "Error: Please login with your CERN account, because this operation requires a user name."
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
            else:
                self.label_info.configure(text=" ")
                try:
                    for k in self.this_HY_HV_relations_MOD:
                        self.last_responseText = util.delete_parents(
                            k["part"]["part_id"], ofKind="Module"
                        )
                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.last_responseText = str(e)

                if self.last_responseText[:2] != "20":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Existing HY HV-side relation could not be deleted (disconnected from module) with ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)
                    self.label_info.configure(text=" ")
                    self.this_HY_HV_relations_MOD = []
                    self.button_delete_child_HY_HV.configure(state="disabled")

    def button_delete_child_HY_LV_event_click(self):
        if len(self.this_HY_LV_relations_MOD) > 0:
            if self.user == "None" or self.user == "new...":
                info_text = "Error: Please login with your CERN account, because this operation requires a user name."
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
            else:
                self.label_info.configure(text=" ")
                try:
                    for k in self.this_HY_LV_relations_MOD:
                        self.last_responseText = util.delete_parents(
                            k["part"]["part_id"], ofKind="Module"
                        )
                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.last_responseText = str(e)

                if self.last_responseText[:2] != "20":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Existing HY LV-side relation could not be deleted (disconnected from module) with ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)
                    self.label_info.configure(text=" ")
                    self.this_HY_LV_relations_MOD = []
                    self.button_delete_child_HY_LV.configure(state="disabled")

    def button_onclick_event_filter_child_SN(self, childIdentifier="Module Flex"):
        if self.operation_mode == "Module Assembly":
            if childIdentifier == "Module Flex":
                self.combobox_MA_MF_chi.set("- Select -")
            elif childIdentifier == "HY_HV":
                self.combobox_MA_HY_HV_chi.set("- Select -")
            elif childIdentifier == "HY_LV":
                self.combobox_MA_HY_LV_chi.set("- Select -")
            self.loading_wheel = threading.Thread(
                target=self.fetch_MA_p_c, args=(childIdentifier,)
            )
        elif self.operation_mode == "Detector Assembly (CERN): FT":
            self.combobox_ft.set("- Select -")
            self.loading_wheel = threading.Thread(target=self.fetch_ft)
        else:
            self.combobox_child.set("- Select -")
            if self.operation_mode == "Module Loading":
                self.loading_wheel = threading.Thread(
                    target=self.fetch_p_c, args=("Detector Unit", "Module")
                )
            elif self.operation_mode == "Detector Assembly (CERN): DU":
                self.loading_wheel = threading.Thread(
                    target=self.fetch_p_c, args=("Detector", "Detector Unit")
                )
            elif self.operation_mode == "Detector Assembly (CERN): PEB":
                self.loading_wheel = threading.Thread(
                    target=self.fetch_p_c, args=("Detector", "PEB")
                )

        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def button_find_slot_event_click(self):
        self.label_info.configure(text=" ")
        v = self.optionmenu_slot_vessel.get()[-1]
        l = self.optionmenu_slot_layer.get()[-1]
        q = self.optionmenu_slot_quadrant.get()[-1]
        r = self.slot_glob_row_entry.get()
        m = self.slot_glob_mod_entry.get()
        self.ft_filter = ""

        self.combined_slot = f"V{v}:L{l}:Q{q}:R{r}:M{m}"
        self.this_SLOT_relations_FT = []
        self.this_FT_relations_SLOT = []
        self.possible_ft = []
        self.combobox_ft.configure(values=[])
        self.combobox_ft.set("- Select -")

        for s in self.slots:
            if s["part_serial_number"] == self.combined_slot:
                self.slot_loc_DUtype_variable.set(s["SU_type"])
                self.slot_loc_row_variable.set(s["SU_Row"])
                self.slot_loc_mod_variable.set(s["SU_Module"])
                if v == "D":
                    if s["PEB_type"] == "1F":
                        # demonstrator V1 (PEB 1F)
                        # demo V1 (PEB 1F): 20WFTC11F/20WFTS11F/20WFTG11F (old order cat 01--36),
                        # 20WFTG12F (new order cat 37--57)
                        self.label_ft_gen_output.configure(
                            text="20WFTC11F/20WFTS11F/20WFTG11F (old order cat 01--36), 20WFTG12F (new order cat 37--57)"
                        )
                        self.ft_filter = f"20WFTC11F/20WFTS11F/20WFTG11F/20WFTG12F+{s['FT_length_category']}"
                    elif s["PEB_type"] == "3F":
                        # demonstrator V2 (PEB 3F)
                        # Pre-production: 20WFTCP1F/20WFTSP1F/20WFTGPF/20WFTMP1F (cat 01--62)
                        self.label_ft_gen_output.configure(
                            text="20WFTCP1F/20WFTSP1F/20WFTGPF/20WFTMP1F (cat 01--62)"
                        )
                        self.ft_filter = f"20WFTCP1F/20WFTSP1F/20WFTGPF/20WFTMP1F+{s['FT_length_category']}"
                elif v == "M":
                    # Module 0
                    # Pre-production: 20WFTCP1F/20WFTSP1F/20WFTGPF/20WFTMP1F (cat 01--62)
                    self.label_ft_gen_output.configure(
                        text="20WFTCP1F/20WFTSP1F/20WFTGPF/20WFTMP1F (cat 01--62)"
                    )
                    self.ft_filter = f"20WFTCP1F/20WFTSP1F/20WFTGPF/20WFTMP1F+{s['FT_length_category']}"
                else:
                    # Full Detector
                    # Main Production: 20WFTCM1F/20WFTSM1F/20WFTGM1F/20WFTMM1F (cat 01--62)
                    self.label_ft_gen_output.configure(
                        text="20WFTCM1F/20WFTSM1F/20WFTGM1F/20WFTMM1F (cat 01--62)"
                    )
                    self.ft_filter = f"20WFTCM1F/20WFTSM1F/20WFTGM1F/20WFTMM1F+{s['FT_length_category']}"
                self.label_ft_type_output.configure(
                    text=f"{s['FT_length_category']} ({s['FT_Length_mm']} mm)"
                )

                # find all FTs that match this generation/category
                self.loading_wheel = threading.Thread(target=self.fetch_ft)
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)
                break
        else:
            info_text = wrapped_text.fill(
                f"Error: Your combination of Vessel, Layer, Quadrant, Global Row & Module does not exist in the slot table."
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)

    def button_inspect_child_event_click(self):
        childSNIn = self.combobox_child.get()
        if childSNIn != "- Select -":
            chi_partID = self.possible_children_partIDs[
                self.possible_children_SNs.index(childSNIn)
            ]
            util.open_webbrowser_with_url(f"/viewparts/{chi_partID}")

    def button_inspect_clicked_event_click(self):
        if len(self.clicked_module) > 0:
            util.open_webbrowser_with_url(
                f"/viewparts/{self.clicked_module['part']['part_id']}"
            )

    def button_inspect_parent_event_click(self):
        parentSNIn = self.combobox_parent.get()
        if parentSNIn != "- Select -":
            par_partID = self.possible_parents_partIDs[
                self.possible_parents_SNs.index(parentSNIn)
            ]
            util.open_webbrowser_with_url(f"/viewparts/{par_partID}")

    def button_inspect_slot_event_click(self):
        if len(self.combined_slot) > 0:
            self.label_info.configure(text=" ")
            for s in self.slots:
                if s["part_serial_number"] == self.combined_slot:
                    par_partID = s["part_id"]
                    break
            util.open_webbrowser_with_url(f"/viewparts/{par_partID}")
        else:
            info_text = wrapped_text.fill(
                f"Error: You first need to find the slot in the slot table to inspect its properties."
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)

    def button_inspect_ft_event_click(self):
        childSNIn = self.combobox_ft.get()
        if childSNIn != "- Select -":
            chi_partID = self.possible_ft_partIDs[self.possible_ft_SNs.index(childSNIn)]
            util.open_webbrowser_with_url(f"/viewparts/{chi_partID}")

    def button_inspect_parent_module_event_click(self):
        parentSNIn = self.combobox_MA_mod_par.get()
        if parentSNIn != "- Select -":
            par_partID = self.possible_MA_mod_par_partIDs[
                self.possible_MA_mod_par_SNs.index(parentSNIn)
            ]
            util.open_webbrowser_with_url(f"/viewparts/{par_partID}")

    def button_inspect_child_module_flex_event_click(self):
        childSNIn = self.combobox_MA_MF_chi.get()
        if childSNIn != "- Select -":
            chi_partID = self.possible_MF_partIDs[self.possible_MF_SNs.index(childSNIn)]
            util.open_webbrowser_with_url(f"/viewparts/{chi_partID}")

    def button_inspect_child_HY_HV_event_click(self):
        childSNIn = self.combobox_MA_HY_HV_chi.get()
        if childSNIn != "- Select -":
            chi_partID = self.possible_HY_HV_partIDs[
                self.possible_HY_HV_SNs.index(childSNIn)
            ]
            util.open_webbrowser_with_url(f"/viewparts/{chi_partID}")

    def button_inspect_child_HY_LV_event_click(self):
        childSNIn = self.combobox_MA_HY_LV_chi.get()
        if childSNIn != "- Select -":
            chi_partID = self.possible_HY_LV_partIDs[
                self.possible_HY_LV_SNs.index(childSNIn)
            ]
            util.open_webbrowser_with_url(f"/viewparts/{chi_partID}")

    # https://stackoverflow.com/a/23944658
    def button_mode_event_click(self, value):
        self.operation_mode = value
        self.displayedDUtype = "None"
        self.this_DU_relations_MODULE = []
        self.this_MODULE_relations_DU = []
        self.this_MODULE_relations_SLOT = []
        self.this_FT_relations_SLOT = []
        self.this_SLOT_relations_FT = []
        self.ft_filter = ""
        self.combined_slot = ""
        self.this_MOD_relations_MF = []
        self.this_MOD_relations_HY_HV = []
        self.this_MOD_relations_HY_LV = []
        self.this_MOD_relations_HY_unknownPosition = []
        self.this_MF_relations_MOD = []
        self.this_HY_HV_relations_MOD = []
        self.this_HY_LV_relations_MOD = []

        self.possible_parents = []
        self.possible_children = []
        self.possible_ft = []
        self.possible_MA_mod_par = []
        self.possible_MF = []
        self.possible_HY_HV = []
        self.possible_HY_LV = []

        self.slots = None
        self.partstree = None
        self.clicked_module = []
        self.button_inspect_clicked.configure(text=f"INSPECT CLICKED MODULE")
        self.button_inspect_clicked.configure(state="disabled")
        self.button_delete_clicked.configure(text=f"UNLOAD CLICKED MODULE")
        self.button_delete_clicked.configure(state="disabled")

        # Detector Assembly / Loading
        self.par_type = None
        self.combobox_par_type.set("- Select -")
        self.chi_type = None
        self.combobox_chi_type.set("- Select -")
        self.child_conn = None
        self.optionmenu_child_conn.set("All children")
        self.ft_conn = None
        self.optionmenu_ft_conn.set("All FTs")
        self.child_manu = None
        self.combobox_child_manu.set("All manufacturers")

        # Module Assembly
        self.MA_mod_par_manu = None
        self.combobox_MA_mod_par_manu.set("All manufacturers")
        self.MA_mod_par_loc = None
        self.combobox_MA_mod_par_loc.set("All locations")
        self.module_flex_child_loc = None
        self.combobox_MA_MF_child_loc.set("All locations")
        self.HY_HV_child_loc = None
        self.combobox_MA_HY_HV_child_loc.set("All locations")
        self.HY_LV_child_loc = None
        self.combobox_MA_HY_LV_child_loc.set("All locations")

        self.MF_child_conn = None
        self.optionmenu_MA_child_MF_conn.set("All children")
        self.HY_HV_child_conn = None
        self.optionmenu_MA_child_HY_HV_conn.set("All children")
        self.HY_LV_child_conn = None
        self.optionmenu_MA_child_HY_LV_conn.set("All children")

        self.HY_HV_child_cluster = None
        self.combobox_MA_HY_HV_child_cluster.set("All clusters")
        self.HY_LV_child_cluster = None
        self.combobox_MA_HY_LV_child_cluster.set("All clusters")

        self.button_delete_child_MF.configure(state="disabled")
        self.button_delete_child_HY_HV.configure(state="disabled")
        self.button_delete_child_HY_LV.configure(state="disabled")

        self.progressbar.set(0)
        self.label_info.configure(text=" ")
        self.canvas.delete("all")
        if self.operation_mode == "Module Assembly":
            self.button_operation_mode_MA.configure(
                fg_color=data.fg_color_standard_but_active,
                hover_color=data.hover_color_standard_but_active,
            )
            self.button_operation_mode_ML.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_DU.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_PEB.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_FT.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )

            self.frame_ma.grid()
            self.frame_combobox.grid_remove()
            self.label_canvas.grid_remove()
            self.canvas.grid_remove()
            self.label_info.grid()
            self.frame_ft_rel.grid_remove()

            self.combobox_MA_mod_par.set("- Select -")
            self.combobox_MA_MF_chi.set("- Select -")
            self.combobox_MA_HY_HV_chi.set("- Select -")
            self.combobox_MA_HY_LV_chi.set("- Select -")

            self.loading_wheel = threading.Thread(target=self.fetch_MA_p_c)
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

        elif self.operation_mode == "Module Loading":
            self.button_operation_mode_MA.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_ML.configure(
                fg_color=data.fg_color_standard_but_active,
                hover_color=data.hover_color_standard_but_active,
            )
            self.button_operation_mode_DA_DU.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_PEB.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_FT.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )

            self.frame_ma.grid_remove()
            self.frame_combobox.grid()
            self.label_canvas.grid()
            self.canvas.grid()
            self.label_info.grid()
            self.frame_ft_rel.grid_remove()

            self.label_combobox_par_type.grid()
            self.combobox_par_type_paginationFrame.grid()

            self.combobox_child_manu.grid()

            self.combobox_chi_type_paginationFrame.grid_remove()

            self.frame_clicked_position.grid()

            self.label_canvas.configure(text="Interactive canvas: accepting user click")
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.label_combobox_parent_T.configure(
                text="Parent Part Type: Detector Unit"
            )
            self.label_combobox_child_T.configure(text="Child Part Type: Module")
            self.label_position.configure(
                text="Position (derived from canvas interaction)"
            )
            self.position_variable.set("- automatic -")
            self.position_entry.configure(state="disabled")
            self.loading_wheel = threading.Thread(
                target=self.fetch_p_c, args=("Detector Unit", "Module")
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == "Detector Assembly (CERN): DU":
            self.button_operation_mode_MA.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_ML.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_DU.configure(
                fg_color=data.fg_color_standard_but_active,
                hover_color=data.hover_color_standard_but_active,
            )
            self.button_operation_mode_DA_PEB.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_FT.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )

            self.frame_ma.grid_remove()
            self.frame_combobox.grid()
            self.label_canvas.grid()
            self.canvas.grid()
            self.label_info.grid()
            self.frame_ft_rel.grid_remove()

            self.label_combobox_par_type.grid_remove()
            self.combobox_par_type_paginationFrame.grid_remove()

            self.combobox_child_manu.grid_remove()

            self.possible_chi_types = ["All DU types"] + data.allDUkeysList
            self.possible_chi_types_chunked = [
                self.possible_chi_types[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_chi_types), self.n_items_to_show_in_cbx
                )
            ]
            self.cbx_ctype_n_pages = len(self.possible_chi_types_chunked)
            self.cbx_ctype_shown_page = 1
            self.label_combobox_chi_type_paginationFrame.configure(
                text=f"page {self.cbx_ctype_shown_page}/{self.cbx_ctype_n_pages}"
            )
            self.combobox_chi_type.configure(values=self.possible_chi_types_chunked[0])

            self.combobox_chi_type_paginationFrame.grid()

            self.frame_clicked_position.grid()

            self.label_canvas.configure(text="Static canvas: served from database")
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.label_combobox_parent_T.configure(text="Parent Part Type: Detector")
            self.label_combobox_child_T.configure(text="Child Part Type: Detector Unit")
            self.label_position.configure(text="Position (type by hand)")
            self.position_variable.set("VxLyQz")
            self.position_entry.configure(state="normal")
            self.loading_wheel = threading.Thread(
                target=self.fetch_p_c, args=("Detector", "Detector Unit")
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == "Detector Assembly (CERN): PEB":
            self.button_operation_mode_MA.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_ML.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_DU.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_PEB.configure(
                fg_color=data.fg_color_standard_but_active,
                hover_color=data.hover_color_standard_but_active,
            )
            self.button_operation_mode_DA_FT.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )

            self.frame_ma.grid_remove()
            self.frame_combobox.grid()
            self.label_canvas.grid_remove()
            self.canvas.grid_remove()
            self.label_info.grid()
            self.frame_ft_rel.grid_remove()

            self.label_combobox_par_type.grid_remove()
            self.combobox_par_type_paginationFrame.grid_remove()

            self.combobox_child_manu.grid_remove()

            self.possible_chi_types = ["All PEB types"] + data.allPEBs
            self.possible_chi_types_chunked = [
                self.possible_chi_types[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_chi_types), self.n_items_to_show_in_cbx
                )
            ]
            self.cbx_ctype_n_pages = len(self.possible_chi_types_chunked)
            self.cbx_ctype_shown_page = 1
            self.label_combobox_chi_type_paginationFrame.configure(
                text=f"page {self.cbx_ctype_shown_page}/{self.cbx_ctype_n_pages}"
            )
            self.combobox_chi_type.configure(values=self.possible_chi_types_chunked[0])

            self.combobox_chi_type_paginationFrame.grid()

            self.frame_clicked_position.grid_remove()

            self.label_canvas.configure(text="Static canvas: served from database")
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.label_combobox_parent_T.configure(text="Parent Part Type: Detector")
            self.label_combobox_child_T.configure(text="Child Part Type: PEB")
            self.label_position.configure(text="Position (type by hand)")
            self.position_variable.set("VxLyQz")
            self.position_entry.configure(state="normal")
            self.loading_wheel = threading.Thread(
                target=self.fetch_p_c, args=("Detector", "PEB")
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == "Detector Assembly (CERN): FT":
            self.button_operation_mode_MA.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_ML.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_DU.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_PEB.configure(
                fg_color=data.fg_color_standard_but_inactive,
                hover_color=data.hover_color_standard_but_inactive,
            )
            self.button_operation_mode_DA_FT.configure(
                fg_color=data.fg_color_standard_but_active,
                hover_color=data.hover_color_standard_but_active,
            )

            self.frame_ma.grid_remove()
            self.frame_combobox.grid_remove()
            self.label_canvas.grid_remove()
            self.canvas.grid_remove()
            self.label_info.grid()
            self.frame_ft_rel.grid()

            self.optionmenu_slot_vessel.set("Vessel: 1")
            self.optionmenu_slot_layer.set("Layer: 0")
            self.optionmenu_slot_quadrant.set("Quadrant: 0")
            self.slot_loc_DUtype_variable.set("- automatic -")
            self.slot_loc_row_variable.set("- automatic -")
            self.slot_loc_mod_variable.set("- automatic -")
            self.slot_glob_row_variable.set("")
            self.slot_glob_mod_variable.set("")

            self.loading_wheel = threading.Thread(target=self.fetch_ft)
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def canvas_event_click(self, event, debug=False):
        self.clicked_module = []
        self.button_inspect_clicked.configure(text=f"INSPECT CLICKED MODULE")
        self.button_inspect_clicked.configure(state="disabled")
        self.button_delete_clicked.configure(text=f"UNLOAD CLICKED MODULE")
        self.button_delete_clicked.configure(state="disabled")
        info_text = " "
        if self.operation_mode == "Module Loading":
            if self.displayedDUtype != "None":
                arrayOfModulesInDU = data.allDUs[self.displayedDUtype]
                alreadyConnectedModules = (
                    self.this_DU_relations_MODULE
                )  # list of relations, as in partstree
                if debug:
                    print(alreadyConnectedModules)
                alreadyUsedSlots = [
                    entry["position"] for entry in alreadyConnectedModules
                ]

                alreadyConnectedDUsForModule = self.this_MODULE_relations_DU
                alreadyConnectedSLOTsForModule = self.this_MODULE_relations_SLOT

                mouseInSomeMod = False
                mouseX = self.canvas.canvasx(event.x)
                mouseY = self.canvas.canvasy(event.y)
                for slot in arrayOfModulesInDU:
                    if util.isInSlot(slot, mouseX, mouseY):
                        mouseInSomeMod = True
                        possible_slot = slot["slot"]
                        notAllowedSlot = False
                        if slot["slot"] in alreadyUsedSlots:
                            self.clicked_module = alreadyConnectedModules[
                                alreadyUsedSlots.index(slot["slot"])
                            ]
                            self.button_inspect_clicked.configure(
                                text=f"INSPECT CLICKED MODULE\n{self.clicked_module['part']['serial_number']}\n at {slot['slot']}"
                            )
                            self.button_inspect_clicked.configure(state="normal")
                            self.button_delete_clicked.configure(
                                text=f"UNLOAD CLICKED MODULE\n{self.clicked_module['part']['serial_number']}\n at {slot['slot']}"
                            )
                            self.button_delete_clicked.configure(state="normal")
                            notAllowedSlot = True
                            self.canvas_place_rounded_rectangle(
                                slot["x"],
                                slot["y"],
                                slot["w"],
                                slot["h"],
                                fill=data.fillColor_AlreadyLoadedSlot,
                            )
                        else:
                            self.canvas_place_rounded_rectangle(
                                slot["x"],
                                slot["y"],
                                slot["w"],
                                slot["h"],
                                fill=data.fillColor_ActiveSlot,
                            )
                    else:
                        if slot["slot"] in alreadyUsedSlots:
                            self.canvas_place_rounded_rectangle(
                                slot["x"],
                                slot["y"],
                                slot["w"],
                                slot["h"],
                                fill=data.fillColor_AlreadyLoadedSlot,
                            )
                        else:
                            self.canvas_place_rounded_rectangle(
                                slot["x"],
                                slot["y"],
                                slot["w"],
                                slot["h"],
                                fill=data.fillColor_Slot,
                            )
                if (
                    len(alreadyConnectedDUsForModule)
                    + len(alreadyConnectedSLOTsForModule)
                    > 0
                ):
                    self.position_variable.set("- automatic -")
                    info_text = "Warning: Your selected child is already connected to some parent.\nSelect a different one, or disconnect the parents of this module by inspecting the Module.\nThere you can delete existing relations with the red trash button."
                    print(f">>> {info_text}")
                    if debug:
                        print(
                            "Existing connections to the following DU(s):",
                            [
                                DU["part_parent"]["serial_number"]
                                for DU in alreadyConnectedDUsForModule
                            ],
                        )
                        print(
                            "Existing connections to the following Slot(s):",
                            [
                                SLOT["part_parent"]["serial_number"]
                                for SLOT in alreadyConnectedSLOTsForModule
                            ],
                        )
                    self.label_info.configure(text=info_text)
                if not mouseInSomeMod:
                    self.position_variable.set("- automatic -")
                    info_text = (
                        info_text + "\n\nWarning: Place mouse in some module slot."
                        if info_text != " "
                        else "Warning: Place mouse in some module slot."
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    if notAllowedSlot:
                        self.position_variable.set("- automatic -")
                        info_text = (
                            info_text
                            + "\n\nWarning: This slot is already in use.\nSelect a different one, or disconnect the already loaded module by inspecting the DU.\nThere you can delete existing relations with the red trash button."
                            if info_text != " "
                            else "Warning: This slot is already in use.\nSelect a different one, or disconnect the already loaded module by inspecting the DU.\nThere you can delete existing relations with the red trash button."
                        )
                        print(f">>> {info_text}")
                        self.label_info.configure(text=info_text)
                    else:
                        if info_text == " ":
                            self.position_variable.set(possible_slot)
                            self.label_info.configure(text=" ")
        elif self.operation_mode == "Detector Assembly (CERN): DU":
            if self.displayedDUtype != "None":
                arrayOfModulesInDU = data.allDUs[self.displayedDUtype]
                alreadyConnectedModules = (
                    self.this_DU_relations_MODULE
                )  # list of relations, as in partstree
                if debug:
                    print(alreadyConnectedModules)
                alreadyUsedSlots = [
                    entry["position"] for entry in alreadyConnectedModules
                ]
                mouseInSomeMod = False
                mouseX = self.canvas.canvasx(event.x)
                mouseY = self.canvas.canvasy(event.y)
                for slot in arrayOfModulesInDU:
                    if util.isInSlot(slot, mouseX, mouseY):
                        mouseInSomeMod = True
                        if slot["slot"] in alreadyUsedSlots:
                            self.clicked_module = alreadyConnectedModules[
                                alreadyUsedSlots.index(slot["slot"])
                            ]
                            self.button_inspect_clicked.configure(
                                text=f"INSPECT CLICKED MODULE\n{self.clicked_module['part']['serial_number']}\n at {slot['slot']}"
                            )
                            self.button_inspect_clicked.configure(state="normal")
                            self.button_delete_clicked.configure(
                                text=f"UNLOAD CLICKED MODULE\n{self.clicked_module['part']['serial_number']}\n at {slot['slot']}"
                            )
                            self.button_delete_clicked.configure(state="normal")

    # https://stackoverflow.com/a/44100075
    def canvas_place_rounded_rectangle(
        self, x1, y1, width, height, radius=25, **kwargs
    ):
        x2 = x1 + width
        y2 = y1 + height

        points = [
            x1 + radius,
            y1,
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]

        self.canvas.create_polygon(points, **kwargs, smooth=True)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)
        # self.frame_ft_rel.grid_remove()
        # print(self.operation_mode)
        if self.operation_mode == "Module Assembly":
            self.frame_ma.grid()
            self.frame_combobox.grid_remove()
            self.label_canvas.grid_remove()
            self.canvas.grid_remove()
            self.label_info.grid()
            self.frame_ft_rel.grid_remove()
        elif self.operation_mode == "Module Loading":
            self.frame_ma.grid_remove()
            self.frame_combobox.grid()
            self.label_canvas.grid()
            self.canvas.grid()
            self.label_info.grid()
            self.frame_ft_rel.grid_remove()
        elif self.operation_mode == "Detector Assembly (CERN): DU":
            self.frame_ma.grid_remove()
            self.frame_combobox.grid()
            self.label_canvas.grid()
            self.canvas.grid()
            self.label_info.grid()
            self.frame_ft_rel.grid_remove()
        elif self.operation_mode == "Detector Assembly (CERN): PEB":
            self.frame_ma.grid_remove()
            self.frame_combobox.grid()
            self.label_canvas.grid_remove()
            self.canvas.grid_remove()
            self.label_info.grid()
            self.frame_ft_rel.grid_remove()
        elif self.operation_mode == "Detector Assembly (CERN): FT":
            self.frame_ma.grid_remove()
            self.frame_combobox.grid_remove()
            self.label_canvas.grid_remove()
            self.canvas.grid_remove()
            self.label_info.grid()
            self.frame_ft_rel.grid()
        # self.button_mode_event_click(self.operation_mode)

    def change_ft_conn_event(self, ft_conn):
        self.ft_conn = self.optionmenu_ft_conn.get()
        self.combobox_ft.set("- Select -")

        self.loading_wheel = threading.Thread(target=self.fetch_ft)
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def change_MA_parent_Mod_filter_event(self, foo):
        self.MA_mod_par_loc = self.combobox_MA_mod_par_loc.get()
        self.MA_mod_par_manu = self.combobox_MA_mod_par_manu.get()
        self.combobox_MA_mod_par.set("- Select -")

        self.loading_wheel = threading.Thread(
            target=self.fetch_MA_p_c, args=("Module",)
        )
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def change_MA_child_MF_filter_event(self, foo):
        self.module_flex_child_loc = self.combobox_MA_MF_child_loc.get()
        self.MF_child_conn = self.optionmenu_MA_child_MF_conn.get()
        self.combobox_MA_MF_chi.set("- Select -")

        self.loading_wheel = threading.Thread(
            target=self.fetch_MA_p_c, args=("Module Flex",)
        )
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def change_MA_child_HY_HV_filter_event(self, foo):
        self.HY_HV_child_loc = self.combobox_MA_HY_HV_child_loc.get()
        self.HY_HV_child_conn = self.optionmenu_MA_child_HY_HV_conn.get()
        self.HY_HV_child_cluster = self.combobox_MA_HY_HV_child_cluster.get()
        # if cluster HV different from existing cluster LV
        # let user know when trying to add a relation between non-matching HYs
        self.combobox_MA_HY_HV_chi.set("- Select -")

        self.loading_wheel = threading.Thread(target=self.fetch_MA_p_c, args=("HY_HV",))
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def change_MA_child_HY_LV_filter_event(self, foo):
        self.HY_LV_child_loc = self.combobox_MA_HY_LV_child_loc.get()
        self.HY_LV_child_conn = self.optionmenu_MA_child_HY_LV_conn.get()
        self.HY_LV_child_cluster = self.combobox_MA_HY_LV_child_cluster.get()
        # if cluster LV different from existing cluster HV
        # let user know when trying to add a relation between non-matching HYs
        self.combobox_MA_HY_LV_chi.set("- Select -")

        self.loading_wheel = threading.Thread(target=self.fetch_MA_p_c, args=("HY_LV",))
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def change_child_conn_event(self, child_conn):
        self.child_conn = self.optionmenu_child_conn.get()
        self.combobox_child.set("- Select -")

        if self.operation_mode == "Module Loading":
            self.loading_wheel = threading.Thread(
                target=self.fetch_p_c, args=("Detector Unit", "Module")
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == "Detector Assembly (CERN): DU":
            self.loading_wheel = threading.Thread(
                target=self.fetch_p_c, args=("Detector", "Detector Unit")
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == "Detector Assembly (CERN): PEB":
            self.loading_wheel = threading.Thread(
                target=self.fetch_p_c, args=("Detector", "PEB")
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def change_user_event(self, selected_user: str):
        if selected_user == "None":
            self.user = None
        elif selected_user == "new...":
            # authenticate as user
            try:
                self.authenticate_user()
            except (
                requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException,
            ) as e:
                self.last_responseText = str(e)
            except ValueError as e:
                self.last_responseText = str(e)

            if self.last_responseText[:2] != "20":
                self.api_status = 0
                self.progressbar.configure(progress_color=data.progress_color_ERROR)
                info_text = wrapped_text.fill(
                    f"Error: New user could not be authenticated.\n{self.last_responseText}"
                )
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
            else:
                self.api_status = 1
                self.progressbar.configure(progress_color=data.progress_color_OK)
        else:
            self.user = selected_user

    def combobox_child_manu_event(self, child_manu):
        self.child_manu = self.combobox_child_manu.get()
        self.combobox_child.set("- Select -")

        self.loading_wheel = threading.Thread(
            target=self.fetch_p_c, args=("Detector Unit", "Module")
        )
        self.loading_wheel.start()
        self.update_progressbar(self.loading_wheel)

    def combobox_par_type_event_select(self, par_type):
        self.par_type = self.combobox_par_type.get()
        self.combobox_parent.set("- Select -")

        self.loading_wheel = threading.Thread(
            target=self.fetch_p_c, args=("Detector Unit", "Module")
        )
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

        if self.operation_mode == "Detector Assembly (CERN): DU":
            self.loading_wheel = threading.Thread(
                target=self.fetch_p_c, args=("Detector", "Detector Unit")
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == "Detector Assembly (CERN): PEB":
            self.loading_wheel = threading.Thread(
                target=self.fetch_p_c, args=("Detector", "PEB")
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def combobox_ft_event_select(self, unused_var_to_please_python):
        self.this_FT_relations_SLOT = []
        ftSNIn = self.combobox_ft.get()
        if ftSNIn != "- Select -":
            self.loading_wheel = threading.Thread(
                target=self.fetch_loaded_FT, args=(ftSNIn,)
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def combobox_MA_mod_event_select(self, unused_var_to_please_python):
        self.this_MOD_relations_MF = []
        self.this_MOD_relations_HY_HV = []
        self.this_MOD_relations_HY_LV = []
        self.this_MOD_relations_HY_unknownPosition = []
        SNIn = self.combobox_MA_mod_par.get()
        if SNIn != "- Select -":
            self.loading_wheel = threading.Thread(
                target=self.fetch_MA_mod, args=(SNIn,)
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def combobox_MA_MF_event_select(self, unused_var_to_please_python):
        self.this_MF_relations_MOD = []
        SNIn = self.combobox_MA_MF_chi.get()
        if SNIn != "- Select -":
            self.loading_wheel = threading.Thread(target=self.fetch_MA_MF, args=(SNIn,))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def combobox_MA_HY_HV_event_select(self, unused_var_to_please_python):
        self.this_HY_HV_relations_MOD = []
        SNIn = self.combobox_MA_HY_HV_chi.get()
        if SNIn != "- Select -":
            self.loading_wheel = threading.Thread(
                target=self.fetch_MA_HY_HV, args=(SNIn,)
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def combobox_MA_HY_LV_event_select(self, unused_var_to_please_python):
        self.this_HY_LV_relations_MOD = []
        SNIn = self.combobox_MA_HY_LV_chi.get()
        if SNIn != "- Select -":
            self.loading_wheel = threading.Thread(
                target=self.fetch_MA_HY_LV, args=(SNIn,)
            )
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)

    def combobox_p_c_event_select(self, unused_var_to_please_python):
        self.displayedDUtype = "None"
        self.displayed_PEB_type = "None"
        self.this_DU_relations_MODULE = []
        self.this_MODULE_relations_DU = []
        self.this_MODULE_relations_SLOT = []
        self.slots = None
        self.partstree = None
        self.clicked_module = []
        self.button_inspect_clicked.configure(text=f"INSPECT CLICKED MODULE")
        self.button_inspect_clicked.configure(state="disabled")
        self.button_delete_clicked.configure(text=f"UNLOAD CLICKED MODULE")
        self.button_delete_clicked.configure(state="disabled")

        parentSNIn = self.combobox_parent.get()
        childSNIn = self.combobox_child.get()
        if self.operation_mode == "Module Loading":
            parentNameIn = "Detector Unit"
            childNameIn = "Module"
            self.canvas.delete("all")
            if parentSNIn != "- Select -":
                self.loading_wheel = threading.Thread(
                    target=self.fetch_loaded_DU_and_display,
                    args=(childSNIn, parentSNIn),
                )
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == "Detector Assembly (CERN): DU":
            parentNameIn = "Detector"
            childNameIn = "Detector Unit"
            self.canvas.delete("all")
            if childSNIn != "- Select -":
                self.loading_wheel = threading.Thread(
                    target=self.fetch_loaded_DU_and_display,
                    args=(childSNIn, parentSNIn),
                )
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)
        elif self.operation_mode == "Detector Assembly (CERN): PEB":
            parentNameIn = "Detector"
            childNameIn = "PEB"
            self.canvas.delete("all")
            if childSNIn != "- Select -":
                self.loading_wheel = threading.Thread(
                    target=self.fetch_loaded_PEB, args=(childSNIn, parentSNIn)
                )
                self.loading_wheel.start()
                self.update_progressbar(self.loading_wheel)

    def delete_old_and_post_new_slots_for_loaded_modules(self, V, L, Q):
        if self.user == "None" or self.user == "new...":
            info_text = "Error: Please login with your CERN account, because this operation requires a user name."
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
        else:
            self.label_info.configure(text=" ")
            for entry in self.this_DU_relations_MODULE:
                try:
                    parents_of_child_module, self.responseText = util.get_parents(
                        entry["part"]["part_id"], ofKind="Slot"
                    )
                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.last_responseText = str(e)

                if self.last_responseText[:2] != "20":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Parents could not be loaded from ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)

                    for r in parents_of_child_module:
                        try:
                            self.last_responseText = api.delete_information(
                                f"/partstreedelete/{r['record_id']}/"
                            )
                        except (
                            requests.exceptions.HTTPError,
                            requests.exceptions.ConnectionError,
                            requests.exceptions.Timeout,
                            requests.exceptions.RequestException,
                        ) as e:
                            self.last_responseText = str(e)
                        except ValueError as e:
                            self.last_responseText = str(e)

                        if self.last_responseText[:2] != "20":
                            self.api_status = 0
                            self.progressbar.configure(
                                progress_color=data.progress_color_ERROR
                            )
                            info_text = wrapped_text.fill(
                                f"Error: Record could not be deleted from ProdDB API.\n{self.last_responseText}"
                            )
                            print(f">>> {info_text}")
                            self.label_info.configure(text=info_text)
                        else:
                            self.api_status = 1
                            self.progressbar.configure(
                                progress_color=data.progress_color_OK
                            )
                    if self.api_status == 1:
                        if debug:
                            print(entry)
                        attribute_SU_r = (
                            entry["position"].split("R").pop().split("M")[0]
                        )
                        attribute_SU_m = entry["position"].split("M").pop()
                        if debug:
                            print("self.displayedDUtype", self.displayedDUtype)
                            print("V", V)
                            print("L", L)
                            print("Q", Q)
                            print("attribute_SU_r", attribute_SU_r)
                            print("attribute_SU_m", attribute_SU_m)
                            print(self.slots[0])
                        for sl in self.slots:
                            if (
                                sl["Vessel"] == str(V)
                                and str(sl["Layer"]) == str(L)
                                and str(sl["Quadrant"]) == str(Q)
                                and str(sl["SU_type"]) == str(self.displayedDUtype)
                                and str(sl["SU_Row"]) == str(attribute_SU_r)
                                and str(sl["SU_Module"]) == str(attribute_SU_m)
                            ):
                                # found a slot :-)
                                if debug:
                                    print("found a slot")
                                    print("sl:", sl)
                                part_tree = {
                                    "position": "",
                                    "is_record_deleted": "F",
                                    "part": entry["part"]["part_id"],
                                    "part_parent": sl["part_id"],
                                    "record_insertion_user": self.user,
                                }
                                try:
                                    print(part_tree)
                                    self.last_responseText = api.post_information(
                                        "/partstreelist", part_tree, dryrun=False
                                    )
                                except (
                                    requests.exceptions.HTTPError,
                                    requests.exceptions.ConnectionError,
                                    requests.exceptions.Timeout,
                                    requests.exceptions.RequestException,
                                ) as e:
                                    self.last_responseText = str(e)
                                except ValueError as e:
                                    self.last_responseText = str(e)

                                if self.last_responseText[:2] != "20":
                                    self.api_status = 0
                                    self.progressbar.configure(
                                        progress_color=data.progress_color_ERROR
                                    )
                                    info_text = wrapped_text.fill(
                                        f"Error: Parent / Child relation could not be patched to ProdDB API.\n{self.last_responseText}"
                                    )
                                    print(f">>> {info_text}")
                                    self.label_info.configure(text=info_text)
                                else:
                                    self.api_status = 1
                                    self.progressbar.configure(
                                        progress_color=data.progress_color_OK
                                    )

    def exit(self):
        self.destroy()

    def fetch_and_write_module_slots(
        self, attribute_Vessel, attribute_Layer, attribute_Quadrant, debug=False
    ):
        if self.api_status == 1:
            if debug:
                if len(self.this_DU_relations_MODULE) == 0:
                    info_text = wrapped_text.fill(
                        f"Warning: There is no relation to a module for this DU."
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
            self.fetch_slots()
            self.delete_old_and_post_new_slots_for_loaded_modules(
                attribute_Vessel, attribute_Layer, attribute_Quadrant
            )

    def fetch_loaded_DU_and_display(self, childSNIn, parentSNIn, debug=False):
        if self.operation_mode == "Module Loading":
            DU_SN = parentSNIn
            parentDU_partID = self.possible_parents_partIDs[
                self.possible_parents_SNs.index(DU_SN)
            ]
            if childSNIn != "- Select -":
                childModule_partID = self.possible_children_partIDs[
                    self.possible_children_SNs.index(childSNIn)
                ]
                # fetch possibly existing parents of module to make sure we don't load it again somewhere else,
                # record multiple KoP as parents!
                try:
                    self.module_parents, self.last_responseText = util.get_parents(
                        childModule_partID
                    )
                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.module_parents = []
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.module_parents = []
                    self.last_responseText = str(e)

                if self.last_responseText[:3] != "200":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: Module relations could not be loaded from ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                    self.this_MODULE_relations_DU = []
                    self.this_MODULE_relations_SLOT = []
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)
                    for r in self.module_parents:
                        if debug:
                            print(r)
                        if str(
                            r["part_parent"]["kind_of_part"]["kind_of_part_id"]
                        ) == str(data.KoPID_from_partKoPName["Detector Unit"]):
                            self.this_MODULE_relations_DU.append(r)
                        if str(
                            r["part_parent"]["kind_of_part"]["kind_of_part_id"]
                        ) == str(data.KoPID_from_partKoPName["Slot"]):
                            self.this_MODULE_relations_SLOT.append(r)
        elif self.operation_mode == "Detector Assembly (CERN): DU":
            DU_SN = childSNIn
            parentDU_partID = self.possible_children_partIDs[
                self.possible_children_SNs.index(DU_SN)
            ]

        self.duAlreadyPlacedText = self.canvas.create_text(
            380, 525, text=f"", anchor="nw", fill=data.fillColor_SU_Text
        )
        self.clicked_module = []
        for key in data.allDUs.keys():
            if key in DU_SN:
                self.displayedDUtype = key
                self.label_info.configure(text=" ")
                self.canvas.create_rectangle(40, 40, 360, 540, fill=data.fillColor_SU)
                for mod in data.allDUs[self.displayedDUtype]:
                    self.canvas_place_rounded_rectangle(
                        mod["x"], mod["y"], mod["w"], mod["h"], fill=data.fillColor_Slot
                    )
                self.canvas.create_text(
                    140,
                    475,
                    text=self.displayedDUtype,
                    anchor="nw",
                    font=("Arial", 50),
                    fill=data.fillColor_SU_Text,
                )
                self.canvas.create_text(
                    145,
                    20,
                    text="Connector side",
                    anchor="nw",
                    fill=data.fillColor_SU_Text,
                )
                self.canvas.create_text(
                    145,
                    545,
                    text="Capacitor side",
                    anchor="nw",
                    fill=data.fillColor_SU_Text,
                )
                if "FI10" in DU_SN:
                    self.canvas.create_text(
                        360,
                        290,
                        text="Connector side",
                        anchor="nw",
                        fill=data.fillColor_SU_Text,
                        angle=90,
                    )
                    self.canvas.create_text(
                        20,
                        290,
                        text="Capacitor side",
                        anchor="nw",
                        fill=data.fillColor_SU_Text,
                        angle=90,
                    )
                # get the children of that DU, interested in Modules only here; get potential detector parent
                try:
                    self.partstree, self.last_responseText = util.get_children(
                        parentDU_partID, ofKind="Module"
                    )
                    detector, self.last_responseText = util.get_parents(
                        parentDU_partID, ofKind="Detector"
                    )
                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    self.partstree = []
                    detector = []
                    self.last_responseText = str(e)
                except ValueError as e:
                    self.partstree = []
                    detector = []
                    self.last_responseText = str(e)

                if self.last_responseText[:3] != "200":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: DU relations could not be loaded from ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                    self.this_DU_relations_MODULE = []
                    break
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)
                    self.this_DU_fully_loaded = False
                    for r in self.partstree:
                        if str(r["part_parent"]["part_id"]) == str(parentDU_partID):
                            if str(r["part"]["kind_of_part"]["kind_of_part_id"]) == str(
                                data.KoPID_from_partKoPName["Module"]
                            ):
                                self.this_DU_relations_MODULE.append(r)
                                # make the corresponding slot blue if already in use, white if not used
                                for mod in data.allDUs[self.displayedDUtype]:
                                    if str(mod["slot"]) == str(r["position"]):
                                        self.canvas_place_rounded_rectangle(
                                            mod["x"],
                                            mod["y"],
                                            mod["w"],
                                            mod["h"],
                                            fill=data.fillColor_AlreadyLoadedSlot,
                                        )
                                        self.clicked_module = r["part"]
                    if len(self.this_DU_relations_MODULE) == len(
                        data.allDUs[self.displayedDUtype]
                    ):
                        self.canvas.create_text(
                            380,
                            475,
                            text="Fully loaded DU",
                            anchor="nw",
                            fill=data.fillColor_SU_Text,
                        )
                    if detector != []:
                        # this DU was already placed somewhere in the detector!!
                        for r in detector:
                            self.duAlreadyPlacedText = self.canvas.create_text(
                                380,
                                525,
                                text=f"Already placed at:\n{r['position']}",
                                anchor="nw",
                                fill=data.fillColor_SU_Text,
                            )
                    break
        else:
            info_text = "Warning: Detector Unit type could not be retrieved from DU SN."
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)

    def fetch_loaded_FT(self, ftSNIn, debug=False):
        FT_partID = self.possible_ft_partIDs[self.possible_ft_SNs.index(ftSNIn)]
        if debug:
            print(ftSNIn)
            print(FT_partID)
            print(self.possible_ft)
        self.label_info.configure(text=" ")
        self.button_delete_connected_ft.configure(state="disabled")
        try:
            ft_par, self.last_responseText = util.get_parents(FT_partID, ofKind="Slot")
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            ft_par = []
            self.last_responseText = str(e)
        except ValueError as e:
            ft_par = []

            self.last_responseText = str(e)

        if self.last_responseText[:3] != "200":
            self.api_status = 0
            self.progressbar.configure(progress_color=data.progress_color_ERROR)
            info_text = wrapped_text.fill(
                f"Error: FT relations could not be loaded from ProdDB API.\n{self.last_responseText}"
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
            self.this_FT_relations_SLOT = []
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color=data.progress_color_OK)

            if ft_par != []:
                # this FT is already connected to some slot!!
                for r in ft_par:
                    if debug:
                        print(r)
                    info_text = f"Info: This FT is already connected to a slot: {r['part_parent']['serial_number']}."
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                    self.this_FT_relations_SLOT.append(r)
                    self.button_delete_connected_ft.configure(state="normal")

    def fetch_loaded_PEB(self, childSNIn, parentSNIn, debug=False):
        PEB_SN = childSNIn
        PEB_partID = self.possible_children_partIDs[
            self.possible_children_SNs.index(PEB_SN)
        ]
        if debug:
            print(childSNIn)
            print(PEB_partID)
            print(self.possible_children)
        # == OLD ==: PEB type used to be only an attribute
        # self.displayed_PEB_type = self.possible_children[self.possible_children_SNs.index(PEB_SN)]['Type']
        for key in data.allPEBs:
            if key in PEB_SN:
                self.displayed_PEB_type = key
                self.label_info.configure(text=" ")

                # find out if this PEB is already placed somewhere
                info_text = " "
                self.label_info.configure(text=info_text)
                try:
                    detector, self.last_responseText = util.get_parents(
                        PEB_partID, ofKind="Detector"
                    )
                except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    detector = []
                    self.last_responseText = str(e)
                except ValueError as e:
                    detector = []
                    self.last_responseText = str(e)

                if self.last_responseText[:3] != "200":
                    self.api_status = 0
                    self.progressbar.configure(progress_color=data.progress_color_ERROR)
                    info_text = wrapped_text.fill(
                        f"Error: PEB relations could not be loaded from ProdDB API.\n{self.last_responseText}"
                    )
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                    break
                else:
                    self.api_status = 1
                    self.progressbar.configure(progress_color=data.progress_color_OK)

                    if detector != []:
                        # this PEB was already placed somewhere in the detector!!
                        for r in detector:
                            info_text = f"Info: This PEB is already mounted to the parent detector, at {r['position']}."
                            print(f">>> {info_text}")
                            self.label_info.configure(text=info_text)
                    break
        else:
            info_text = "Warning: PEB type could not be retrieved from PEB SN."
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)

    def fetch_ft(self):
        try:
            self.fetch_slots()
            self.possible_ft, self.last_responseText = util.get_relevant_parts(
                "Flex Tail"
            )
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            self.possible_ft = []
            self.last_responseText = str(e)
        except ValueError as e:
            self.possible_ft = []
            self.last_responseText = str(e)

        if self.last_responseText[:3] != "200":
            self.api_status = 0
            self.progressbar.configure(progress_color=data.progress_color_ERROR)
            info_text = wrapped_text.fill(
                f"Error: Slots / FT could not be loaded from ProdDB API.\n{self.last_responseText}"
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color=data.progress_color_OK)

            if self.ft_filter != "":
                gen = self.ft_filter.split("+")[0].split("/")  # multiple generations
                cat = self.ft_filter[-2:]  # the last two chars make the category

                self.possible_ft = [
                    pft
                    for pft in self.possible_ft
                    if any(gen_ in pft["serial_number"] for gen_ in gen)
                    and int(pft["serial_number"][9:11]) == int(cat)
                ]

            # HY_LV child SN filter input
            self.childFT_SN_filter = self.entry_childFT_SN_filter.get()
            if self.childFT_SN_filter != "":
                self.possible_ft = [
                    pft
                    for pft in self.possible_ft
                    if self.childFT_SN_filter in str(pft["serial_number"])
                ]
            # do the most expensive part last (when easy filters on existing data have already been applied)
            # expensive meaning need to make calls to the API for each part in the list that survived the previous cuts
            if self.ft_conn != None and self.ft_conn != "All FTs":
                self.possible_ft = [
                    pp
                    for pp in self.possible_ft
                    if (len(util.get_parents(pp["part_id"], ofKind="Slot")[0])) == 0
                ]
            self.possible_ft_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(
                self.possible_ft
            )
            self.possible_ft_SNs = [
                entry[0] for entry in self.possible_ft_SNs_and_partIDs
            ]
            self.possible_ft_SNs_chunked = [
                self.possible_ft_SNs[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_ft_SNs), self.n_items_to_show_in_cbx
                )
            ]
            self.possible_ft_partIDs = [
                entry[1] for entry in self.possible_ft_SNs_and_partIDs
            ]
            self.cbx_ft_n_pages = len(self.possible_ft_SNs_chunked)
            self.cbx_ft_shown_page = min(1, self.cbx_ft_n_pages)
            self.label_combobox_ft_paginationFrame.configure(
                text=f"page {self.cbx_ft_shown_page}/{self.cbx_ft_n_pages}"
            )
            if len(self.possible_ft) > 0:
                self.combobox_ft.configure(values=self.possible_ft_SNs_chunked[0])
            else:
                self.combobox_ft.configure(values=[])
                self.combobox_ft.set("- Select -")

    def fetch_MA_p_c(self, update="all", withMessage=" "):
        # this happens when any filter is changed and at the beginning
        self.progressbar.set(0)
        self.label_info.configure(text=withMessage)
        try:
            if update == "all" or update == "Module":
                self.possible_MA_mod_par, self.last_responseText = (
                    util.get_relevant_parts("Module")
                )
                self.combobox_MA_mod_par.set("- Select -")
                self.this_MOD_relations_MF = []
                self.this_MOD_relations_HY_HV = []
                self.this_MOD_relations_HY_LV = []
                self.this_MOD_relations_HY_unknownPosition = []
            if update == "all" or update == "Module Flex":
                self.possible_MF, self.last_responseText = util.get_relevant_parts(
                    "Module Flex"
                )
                self.combobox_MA_MF_chi.set("- Select -")
                self.this_MF_relations_MOD = []
            if update == "all" or update == "HY_HV" or update == "HY_LV":
                self.possible_HY_HV, self.last_responseText = util.get_relevant_parts(
                    "Hybrid"
                )
                self.combobox_MA_HY_HV_chi.set("- Select -")
                self.this_HY_HV_relations_MOD = []
            if update == "all" or update == "HY_LV":
                self.possible_HY_LV = self.possible_HY_HV
                self.combobox_MA_HY_LV_chi.set("- Select -")
                self.this_HY_LV_relations_MOD = []
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            if update == "all" or update == "Module":
                self.possible_MA_mod_par = []
                self.combobox_MA_mod_par.set("- Select -")
                self.this_MOD_relations_MF = []
                self.this_MOD_relations_HY_HV = []
                self.this_MOD_relations_HY_LV = []
                self.this_MOD_relations_HY_unknownPosition = []
            if update == "all" or update == "Module Flex":
                self.possible_MF = []
                self.combobox_MA_MF_chi.set("- Select -")
                self.this_MF_relations_MOD = []
            if update == "all" or update == "HY_HV" or update == "HY_LV":
                self.possible_HY_HV = []
            if update == "all" or update == "HY_LV":
                self.possible_HY_LV = []
            self.last_responseText = str(e)
        except ValueError as e:
            if update == "all" or update == "Module":
                self.possible_MA_mod_par = []
                self.combobox_MA_mod_par.set("- Select -")
                self.this_MOD_relations_MF = []
                self.this_MOD_relations_HY_HV = []
                self.this_MOD_relations_HY_LV = []
                self.this_MOD_relations_HY_unknownPosition = []
            if update == "all" or update == "Module Flex":
                self.possible_MF = []
                self.combobox_MA_MF_chi.set("- Select -")
                self.this_MF_relations_MOD = []
            if update == "all" or update == "HY_HV" or update == "HY_LV":
                self.possible_HY_HV = []
                self.combobox_MA_HY_HV_chi.set("- Select -")
                self.this_HY_HV_relations_MOD = []
            if update == "all" or update == "HY_LV":
                self.possible_HY_LV = []
                self.combobox_MA_HY_LV_chi.set("- Select -")
                self.this_HY_LV_relations_MOD = []
            self.last_responseText = str(e)

        if self.last_responseText[:3] != "200":
            self.api_status = 0
            self.progressbar.configure(progress_color=data.progress_color_ERROR)
            info_text = wrapped_text.fill(
                f"Error: Parents / Children could not be loaded from ProdDB API.\n{self.last_responseText}"
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color=data.progress_color_OK)

            if update == "all" or update == "Module":
                if (
                    self.MA_mod_par_manu != None
                    and self.MA_mod_par_manu != "All manufacturers"
                ):
                    self.possible_MA_mod_par = [
                        pp
                        for pp in self.possible_MA_mod_par
                        if self.MA_mod_par_manu
                        == str(pp["manufacturer"]["manufacturer_name"])
                    ]

                if (
                    self.MA_mod_par_loc != None
                    and self.MA_mod_par_loc != "All locations"
                ):
                    self.possible_MA_mod_par = [
                        pp
                        for pp in self.possible_MA_mod_par
                        if self.MA_mod_par_loc == str(pp["location"]["location_name"])
                    ]

            if update == "all" or update == "Module Flex":
                if (
                    self.module_flex_child_loc != None
                    and self.module_flex_child_loc != "All locations"
                ):
                    self.possible_MF = [
                        pp
                        for pp in self.possible_MF
                        if self.module_flex_child_loc
                        == str(pp["location"]["location_name"])
                    ]

                # MF child SN filter input
                self.child0_SN_filter = self.entry_child0_SN_filter.get()
                if self.child0_SN_filter != "":
                    self.possible_MF = [
                        pc
                        for pc in self.possible_MF
                        if self.child0_SN_filter in str(pc["serial_number"])
                    ]

                if self.MF_child_conn != None and self.MF_child_conn != "All children":
                    self.possible_MF = [
                        pp
                        for pp in self.possible_MF
                        if (len(util.get_parents(pp["part_id"], ofKind="Module")[0]))
                        == 0
                    ]

            if update == "all" or update == "HY_HV":
                if (
                    self.HY_HV_child_loc != None
                    and self.HY_HV_child_loc != "All locations"
                ):
                    self.possible_HY_HV = [
                        pp
                        for pp in self.possible_HY_HV
                        if self.HY_HV_child_loc == str(pp["location"]["location_name"])
                    ]

                # HY_HV child SN filter input
                self.child1_SN_filter = self.entry_child1_SN_filter.get()
                if self.child1_SN_filter != "":
                    self.possible_HY_HV = [
                        pc
                        for pc in self.possible_HY_HV
                        if self.child1_SN_filter in str(pc["serial_number"])
                    ]

                if (
                    self.HY_HV_child_conn != None
                    and self.HY_HV_child_conn != "All children"
                ):
                    self.possible_HY_HV = [
                        pp
                        for pp in self.possible_HY_HV
                        if (len(util.get_parents(pp["part_id"], ofKind="Module")[0]))
                        == 0
                    ]

                if (
                    self.HY_HV_child_cluster != None
                    and self.HY_HV_child_cluster != "All clusters"
                ):
                    # ToDo: call the function that groups Hybrids by their child sensor VBD score into different clusters
                    self.possible_HY_HV = [pp for pp in self.possible_HY_HV if True]

            if update == "all" or update == "HY_LV":
                if (
                    self.HY_LV_child_loc != None
                    and self.HY_LV_child_loc != "All locations"
                ):
                    self.possible_HY_LV = [
                        pp
                        for pp in self.possible_HY_LV
                        if self.HY_LV_child_loc == str(pp["location"]["location_name"])
                    ]

                # HY_LV child SN filter input
                self.child2_SN_filter = self.entry_child2_SN_filter.get()
                if self.child2_SN_filter != "":
                    self.possible_HY_LV = [
                        pc
                        for pc in self.possible_HY_LV
                        if self.child2_SN_filter in str(pc["serial_number"])
                    ]

                if (
                    self.HY_LV_child_conn != None
                    and self.HY_LV_child_conn != "All children"
                ):
                    self.possible_HY_LV = [
                        pp
                        for pp in self.possible_HY_LV
                        if (len(util.get_parents(pp["part_id"], ofKind="Module")[0]))
                        == 0
                    ]

                if (
                    self.HY_LV_child_cluster != None
                    and self.HY_LV_child_cluster != "All clusters"
                ):
                    # ToDo: call the function that groups Hybrids by their child sensor VBD score into different clusters
                    self.possible_HY_LV = [pp for pp in self.possible_HY_LV if True]

            # begin updating the paginated SN comboboxes shown to user
            # Module
            self.possible_MA_mod_par_SNs_and_partIDs = (
                util.get_relevant_SNs_and_partIDs(self.possible_MA_mod_par)
            )
            self.possible_MA_mod_par_SNs = [
                entry[0] for entry in self.possible_MA_mod_par_SNs_and_partIDs
            ]
            self.possible_MA_mod_par_SNs_chunked = [
                self.possible_MA_mod_par_SNs[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_MA_mod_par_SNs), self.n_items_to_show_in_cbx
                )
            ]
            self.possible_MA_mod_par_partIDs = [
                entry[1] for entry in self.possible_MA_mod_par_SNs_and_partIDs
            ]
            self.cbx_MA_mod_par_n_pages = len(self.possible_MA_mod_par_SNs_chunked)
            self.cbx_MA_mod_par_shown_page = min(1, self.cbx_MA_mod_par_n_pages)
            self.label_combobox_MA_mod_par_paginationFrame.configure(
                text=f"page {self.cbx_MA_mod_par_shown_page}/{self.cbx_MA_mod_par_n_pages}"
            )
            if self.cbx_MA_mod_par_n_pages > 0:
                self.combobox_MA_mod_par.configure(
                    values=self.possible_MA_mod_par_SNs_chunked[0]
                )
            else:
                self.combobox_MA_mod_par.configure(values=[])
                self.combobox_MA_mod_par.set("- Select -")

            # Module Flex
            self.possible_MF_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(
                self.possible_MF
            )
            self.possible_MF_SNs = [
                entry[0] for entry in self.possible_MF_SNs_and_partIDs
            ]
            self.possible_MF_SNs_chunked = [
                self.possible_MF_SNs[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_MF_SNs), self.n_items_to_show_in_cbx
                )
            ]
            self.possible_MF_partIDs = [
                entry[1] for entry in self.possible_MF_SNs_and_partIDs
            ]
            self.cbx_MF_n_pages = len(self.possible_MF_SNs_chunked)
            self.cbx_MF_shown_page = min(1, self.cbx_MF_n_pages)
            self.label_combobox_MA_MF_chi_paginationFrame.configure(
                text=f"page {self.cbx_MF_shown_page}/{self.cbx_MF_n_pages}"
            )
            if self.cbx_MF_n_pages > 0:
                self.combobox_MA_MF_chi.configure(
                    values=self.possible_MF_SNs_chunked[0]
                )
            else:
                self.combobox_MA_MF_chi.configure(values=[])
                self.combobox_MA_MF_chi.set("- Select -")

            # Hybrid HV-side
            self.possible_HY_HV_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(
                self.possible_HY_HV
            )
            self.possible_HY_HV_SNs = [
                entry[0] for entry in self.possible_HY_HV_SNs_and_partIDs
            ]
            self.possible_HY_HV_SNs_chunked = [
                self.possible_HY_HV_SNs[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_HY_HV_SNs), self.n_items_to_show_in_cbx
                )
            ]
            self.possible_HY_HV_partIDs = [
                entry[1] for entry in self.possible_HY_HV_SNs_and_partIDs
            ]
            self.cbx_HY_HV_n_pages = len(self.possible_HY_HV_SNs_chunked)
            self.cbx_HY_HV_shown_page = min(1, self.cbx_HY_HV_n_pages)
            self.label_combobox_HY_HV_paginationFrame.configure(
                text=f"page {self.cbx_HY_HV_shown_page}/{self.cbx_HY_HV_n_pages}"
            )
            if self.cbx_HY_HV_n_pages > 0:
                self.combobox_MA_HY_HV_chi.configure(
                    values=self.possible_HY_HV_SNs_chunked[0]
                )
            else:
                self.combobox_MA_HY_HV_chi.configure(values=[])
                self.combobox_MA_HY_HV_chi.set("- Select -")

            # Hybrid LV-side
            self.possible_HY_LV_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(
                self.possible_HY_LV
            )
            self.possible_HY_LV_SNs = [
                entry[0] for entry in self.possible_HY_LV_SNs_and_partIDs
            ]
            self.possible_HY_LV_SNs_chunked = [
                self.possible_HY_LV_SNs[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_HY_LV_SNs), self.n_items_to_show_in_cbx
                )
            ]
            self.possible_HY_LV_partIDs = [
                entry[1] for entry in self.possible_HY_LV_SNs_and_partIDs
            ]
            self.cbx_HY_LV_n_pages = len(self.possible_HY_LV_SNs_chunked)
            self.cbx_HY_LV_shown_page = min(1, self.cbx_HY_LV_n_pages)
            self.label_combobox_HY_LV_paginationFrame.configure(
                text=f"page {self.cbx_HY_LV_shown_page}/{self.cbx_HY_LV_n_pages}"
            )
            if self.cbx_HY_LV_n_pages > 0:
                self.combobox_MA_HY_LV_chi.configure(
                    values=self.possible_HY_LV_SNs_chunked[0]
                )
            else:
                self.combobox_MA_HY_LV_chi.configure(values=[])
                self.combobox_MA_HY_LV_chi.set("- Select -")

    def fetch_MA_mod(self, SN, debug=False):
        # this happens when a parent SN is selected
        partID = self.possible_MA_mod_par_partIDs[
            self.possible_MA_mod_par_SNs.index(SN)
        ]
        if debug:
            print(SN)
            print(partID)
            print(self.possible_MA_mod_par)
        self.label_info.configure(text=" ")
        try:
            par, self.last_responseText = util.get_children(
                partID
            )  # fetches all of them, group into KoP afterwards
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            par = []
            self.last_responseText = str(e)
        except ValueError as e:
            par = []

            self.last_responseText = str(e)

        if self.last_responseText[:3] != "200":
            self.api_status = 0
            self.progressbar.configure(progress_color=data.progress_color_ERROR)
            info_text = wrapped_text.fill(
                f"Error: Module relations could not be loaded from ProdDB API.\n{self.last_responseText}"
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
            self.this_MOD_relations_MF = []
            self.this_MOD_relations_HY_HV = []
            self.this_MOD_relations_HY_LV = []
            self.this_MOD_relations_HY_unknownPosition = []
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color=data.progress_color_OK)

            if par != []:
                # this Module is already connected to some children!!
                info_text = f"Info: This Module is already connected to some children."
                print(f">>> {info_text}")
                self.label_info.configure(text=info_text)
                for r in par:
                    if debug:
                        print(r)
                    if str(data.KoPID_from_partKoPName["Module Flex"]) == str(
                        r["part"]["kind_of_part"]["kind_of_part_id"]
                    ):
                        self.this_MOD_relations_MF.append(r)
                        add_info_text = (
                            f"\n\nExisting MF relation: {r['part']['serial_number']}."
                        )
                        print(f"{add_info_text}")
                        info_text += add_info_text
                    elif (
                        str(data.KoPID_from_partKoPName["Hybrid"])
                        == str(r["part"]["kind_of_part"]["kind_of_part_id"])
                    ) and (str(r["position"]) == "HV"):
                        self.this_MOD_relations_HY_HV.append(r)
                        add_info_text = f"\n\nExisting HY HV-side relation: {r['part']['serial_number']}."
                        print(f"{add_info_text}")
                        info_text += add_info_text
                    elif (
                        str(data.KoPID_from_partKoPName["Hybrid"])
                        == str(r["part"]["kind_of_part"]["kind_of_part_id"])
                    ) and (str(r["position"]) == "LV"):
                        self.this_MOD_relations_HY_LV.append(r)
                        add_info_text = f"\n\nExisting HY LV-side relation: {r['part']['serial_number']}."
                        print(f"{add_info_text}")
                        info_text += add_info_text
                    elif (
                        str(data.KoPID_from_partKoPName["Hybrid"])
                        == str(r["part"]["kind_of_part"]["kind_of_part_id"])
                    ) and (str(r["position"]) == ""):
                        self.this_MOD_relations_HY_unknownPosition.append(r)
                        add_info_text = f"\n\nExisting HY relation, at unknown location within module: {r['part']['serial_number']}.\nPlease consider adding the child again with this tool to record a valid position."
                        print(f"{add_info_text}")
                        info_text += add_info_text
                    else:
                        add_info_text = f"\n\nExisting unexpected relation to child: {r['part']['serial_number']}.\nPlease inspect the part and investigate why this is neither a module flex nor hybrid!"
                        print(f"{add_info_text}")
                        info_text += add_info_text
                    self.label_info.configure(text=info_text)

    def fetch_MA_MF(self, SN, debug=False):
        # this happens when a child SN is selected
        partID = self.possible_MF_partIDs[self.possible_MF_SNs.index(SN)]
        if debug:
            print(SN)
            print(partID)
            print(self.possible_MF)
        self.label_info.configure(text=" ")
        self.button_delete_child_MF.configure(state="disabled")
        try:
            par, self.last_responseText = util.get_parents(partID, ofKind="Module")
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            par = []
            self.last_responseText = str(e)
        except ValueError as e:
            par = []

            self.last_responseText = str(e)

        if self.last_responseText[:3] != "200":
            self.api_status = 0
            self.progressbar.configure(progress_color=data.progress_color_ERROR)
            info_text = wrapped_text.fill(
                f"Error: MF relations could not be loaded from ProdDB API.\n{self.last_responseText}"
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
            self.this_MF_relations_MOD = []
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color=data.progress_color_OK)

            if par != []:
                # this MF is already connected to some module!!
                for r in par:
                    if debug:
                        print(r)
                    info_text = f"Info: This MF is already connected to a module: {r['part_parent']['serial_number']}."
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                    self.this_MF_relations_MOD.append(r)
                    self.button_delete_child_MF.configure(state="normal")

    def fetch_MA_HY_HV(self, SN, debug=False):
        # this happens when a child SN is selected
        partID = self.possible_HY_HV_partIDs[self.possible_HY_HV_SNs.index(SN)]
        if debug:
            print(SN)
            print(partID)
            print(self.possible_HY_HV)
        self.label_info.configure(text=" ")
        self.button_delete_child_HY_HV.configure(state="disabled")
        try:
            par, self.last_responseText = util.get_parents(partID, ofKind="Module")
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            par = []
            self.last_responseText = str(e)
        except ValueError as e:
            par = []

            self.last_responseText = str(e)

        if self.last_responseText[:3] != "200":
            self.api_status = 0
            self.progressbar.configure(progress_color=data.progress_color_ERROR)
            info_text = wrapped_text.fill(
                f"Error: HY HV-side relations could not be loaded from ProdDB API.\n{self.last_responseText}"
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
            self.this_HY_HV_relations_MOD = []
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color=data.progress_color_OK)

            if par != []:
                # this HY HV-side is already connected to some module!!
                for r in par:
                    if debug:
                        print(r)
                    info_text = f"Info: This HY HV-side is already connected to a module: {r['part_parent']['serial_number']}."
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                    self.this_HY_HV_relations_MOD.append(r)
                    self.button_delete_child_HY_HV.configure(state="normal")

    def fetch_MA_HY_LV(self, SN, debug=False):
        # this happens when a child SN is selected
        partID = self.possible_HY_LV_partIDs[self.possible_HY_LV_SNs.index(SN)]
        if debug:
            print(SN)
            print(partID)
            print(self.possible_HY_LV)
        self.label_info.configure(text=" ")
        self.button_delete_child_HY_LV.configure(state="disabled")
        try:
            par, self.last_responseText = util.get_parents(partID, ofKind="Module")
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            par = []
            self.last_responseText = str(e)
        except ValueError as e:
            par = []

            self.last_responseText = str(e)

        if self.last_responseText[:3] != "200":
            self.api_status = 0
            self.progressbar.configure(progress_color=data.progress_color_ERROR)
            info_text = wrapped_text.fill(
                f"Error: HY LV-side relations could not be loaded from ProdDB API.\n{self.last_responseText}"
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
            self.this_HY_LV_relations_MOD = []
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color=data.progress_color_OK)

            if par != []:
                # this HY LV-side is already connected to some module!!
                for r in par:
                    if debug:
                        print(r)
                    info_text = f"Info: This HY LV-side is already connected to a module: {r['part_parent']['serial_number']}."
                    print(f">>> {info_text}")
                    self.label_info.configure(text=info_text)
                    self.this_HY_LV_relations_MOD.append(r)
                    self.button_delete_child_HY_LV.configure(state="normal")

    def fetch_p_c(self, p, c):
        try:
            self.possible_parents, self.last_responseText = util.get_relevant_parts(p)
            self.possible_children, self.last_responseText = util.get_relevant_parts(c)
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            self.possible_parents = []
            self.possible_children = []
            self.last_responseText = str(e)
        except ValueError as e:
            self.possible_parents = []
            self.possible_children = []
            self.last_responseText = str(e)

        if self.last_responseText[:3] != "200":
            self.api_status = 0
            self.progressbar.configure(progress_color=data.progress_color_ERROR)
            info_text = wrapped_text.fill(
                f"Error: Parents / Children could not be loaded from ProdDB API.\n{self.last_responseText}"
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color=data.progress_color_OK)

            if p == "Detector Unit" and c == "Module":
                if self.par_type != None and self.par_type != "All DU types":
                    self.possible_parents = [
                        pp
                        for pp in self.possible_parents
                        if self.par_type in pp["serial_number"]
                    ]
                if self.child_manu != None and self.child_manu != "All manufacturers":
                    self.possible_children = [
                        pp
                        for pp in self.possible_children
                        if self.child_manu
                        == str(pp["manufacturer"]["manufacturer_name"])
                    ]

            elif p == "Detector" and c == "Detector Unit":
                if self.chi_type != None and self.chi_type != "All DU types":
                    self.possible_children = [
                        pc
                        for pc in self.possible_children
                        if self.chi_type in pc["serial_number"]
                    ]

            elif p == "Detector" and c == "PEB":
                if self.chi_type != None and self.chi_type != "All PEB types":
                    self.possible_children = [
                        pc
                        for pc in self.possible_children
                        if self.chi_type in pc["Type"]
                    ]

            # child SN filter input
            self.child_SN_filter = self.entry_child_SN_filter.get()
            if self.child_SN_filter != "":
                self.possible_children = [
                    pc
                    for pc in self.possible_children
                    if self.child_SN_filter in str(pc["serial_number"])
                ]

            # do the most expensive part last (when easy filters on existing data have already been applied)
            # expensive meaning need to make calls to the API for each part in the list that survived the previous cuts
            # multiple KoP possible
            if self.child_conn != None and self.child_conn != "All children":
                self.possible_children = [
                    pp
                    for pp in self.possible_children
                    if (len(util.get_parents(pp["part_id"])[0])) == 0
                ]

            self.possible_parents_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(
                self.possible_parents
            )
            self.possible_children_SNs_and_partIDs = util.get_relevant_SNs_and_partIDs(
                self.possible_children
            )
            self.possible_parents_SNs = [
                entry[0] for entry in self.possible_parents_SNs_and_partIDs
            ]
            self.possible_parents_SNs_chunked = [
                self.possible_parents_SNs[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_parents_SNs), self.n_items_to_show_in_cbx
                )
            ]
            self.possible_children_SNs = [
                entry[0] for entry in self.possible_children_SNs_and_partIDs
            ]
            self.possible_children_SNs_chunked = [
                self.possible_children_SNs[i : i + self.n_items_to_show_in_cbx]
                for i in range(
                    0, len(self.possible_children_SNs), self.n_items_to_show_in_cbx
                )
            ]
            self.possible_parents_partIDs = [
                entry[1] for entry in self.possible_parents_SNs_and_partIDs
            ]
            self.possible_children_partIDs = [
                entry[1] for entry in self.possible_children_SNs_and_partIDs
            ]
            self.cbx_par_n_pages = len(self.possible_parents_SNs_chunked)
            self.cbx_chi_n_pages = len(self.possible_children_SNs_chunked)
            self.cbx_par_shown_page = min(1, self.cbx_par_n_pages)
            self.cbx_chi_shown_page = min(1, self.cbx_chi_n_pages)
            self.label_combobox_parent_paginationFrame.configure(
                text=f"page {self.cbx_par_shown_page}/{self.cbx_par_n_pages}"
            )
            self.label_combobox_child_paginationFrame.configure(
                text=f"page {self.cbx_chi_shown_page}/{self.cbx_chi_n_pages}"
            )
            if self.cbx_par_n_pages > 0:
                self.combobox_parent.configure(
                    values=self.possible_parents_SNs_chunked[0]
                )
            else:
                self.combobox_parent.configure(values=[])
                self.combobox_parent.set("- Select -")
            if self.cbx_chi_n_pages > 0:
                self.combobox_child.configure(
                    values=self.possible_children_SNs_chunked[0]
                )
            else:
                self.combobox_child.configure(values=[])
                self.combobox_child.set("- Select -")

    def fetch_slots(self):
        try:
            self.slots, self.last_responseText = util.get_relevant_parts(
                "Slot", getFullAttributes=True, useLocal=True
            )
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        ) as e:
            self.slots = None
            self.last_responseText = str(e)
        except ValueError as e:
            self.slots = None
            self.last_responseText = str(e)

        if self.last_responseText[:3] != "200":
            self.api_status = 0
            self.progressbar.configure(progress_color=data.progress_color_ERROR)
            info_text = wrapped_text.fill(
                f"Error: Slots could not be loaded from ProdDB API.\n{self.last_responseText}"
            )
            print(f">>> {info_text}")
            self.label_info.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color=data.progress_color_OK)

    def help(self):
        if self.help_window is None or not self.help_window.winfo_exists():
            self.help_window = ToplevelWindow(
                self
            )  # create window if its None or destroyed
        else:
            self.help_window.focus()  # if window exists focus it

    def update_progressbar(self, thread):
        if thread.is_alive():
            # update progressbar
            self.progressbar.step()
            self.after(250, self.update_progressbar, thread)
            self.progressbar.configure(progress_color=data.progress_color_wait)
        else:
            self.progressbar.set(1)
            if self.api_status == 0:
                self.progressbar.configure(progress_color=data.progress_color_ERROR)
            else:
                self.progressbar.configure(progress_color=data.progress_color_OK)


if __name__ == "__main__":
    app = App()
    app.mainloop()
