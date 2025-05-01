import customtkinter
import threading
import time
import tkinter
import requests
import textwrap
# If we need to tackle a longer list of options, there is a custom dropdown frame to handle them
#from ctk_scrollDropdown import CTkScrollableDropdownFrame
# Similar for overflowing text labels etc.
#from ctk_scrollFrame import CTkXYFrame
import api
import data
import util

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

def load_relevant_parts(partKoP_shortname, onlyNonDeleted = True):
    KoP_ID = data.KoPID_from_partKoPName[partKoP_shortname]
    try:
        these_parts, responseText = api.fetch_information(f'/partslistbykop/{KoP_ID}/')
        these_parts = [tP for tP in these_parts if tP['is_record_deleted'] == 'F']
        return these_parts, responseText
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        raise e
    except ValueError as e:
        raise e

def grab_relevant_SNs_and_partIDs(partsList):
    these_SNs_and_partIDs = util.getSortedListOfListsByNthColumn([[pL['serial_number'],pL['part_id']] for pL in partsList], 0)
    return these_SNs_and_partIDs

def isInSlot(rect, x, y):
    isInSlot = False
    left = rect['x']
    right = rect['x']+rect['w']
    top = rect['y']
    bottom = rect['y']+rect['h']
    if (right >= x
        and left <= x
        and bottom >= y
        and top <= y):
        isInSlot = True
    return isInSlot

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # configure window
        self.title("HGTD Tools")
        self.geometry(f"{1500}x{1000}")
        icon = tkinter.PhotoImage(file="windowIcon.png")
        self.iconphoto(True,icon)

        # configure grid layout
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure((0,1), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame_left = customtkinter.CTkFrame(self, corner_radius=0)
        self.sidebar_frame_left.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame_left.grid_columnconfigure(0, weight=1)
        self.sidebar_frame_left.grid_rowconfigure(4, weight=1)#, minsize=140)
        
        # fill sidebar
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="HGTD Tools", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.credits_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="v0.0.1 - May 2025\n Annika Stein (JGU Mainz)")
        self.credits_label.grid(row=1, column=0, padx=20, pady=10)

        self.progress_label = customtkinter.CTkLabel(self.sidebar_frame_left, text="API Request Status")
        self.progress_label.grid(row=2, column=0, padx=20, pady=10)
        self.progressbar = customtkinter.CTkProgressBar(self.sidebar_frame_left, orientation="horizontal", progress_color="#007711")
        self.progressbar.grid(row=3, column=0, padx=20, pady=10)
        self.progressbar.set(1)

        
        # work in main widget (column w.r.t. root >= 1)
        self.explain_frame = customtkinter.CTkFrame(self)#CTkXYFrame(self)
        self.explain_frame.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew", columnspan=2)
        
        self.textbox = customtkinter.CTkTextbox(master=self.explain_frame, width=400, wrap='word')
        self.textbox.pack(fill="both", expand=True, padx=20, pady=20)
        #self.textbox.grid(row=0, column=0, sticky="nsew")
        self.textbox.insert("0.0", "Each Support Unit is oriented in such a way that when looking at its face, the module connectors are at the top (or on the right), and module capacitors are on the bottom (or on the left).\n\nUser actions (loading sites / assembly at CERN): First step at a loading site: fill the Detector Unit with modules, click on the canvas to select the correct position and use the button below. Once finished, move to the assembly step at CERN and enter the position manually when connecting a Detector Unit with the Detector (VxLxQx). Note: A back Detector Unit can only be on layer 1 or 2, a front Detector Unit can only be on layer 0 or 3.")
        self.textbox.configure(state='disabled')
        # create main frame with widgets
        self.main_frame = customtkinter.CTkFrame(self)
        self.main_frame.grid(row=1, column=1, rowspan=1, columnspan=2, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure((0,1), weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # button to select use case of the tool
        self.segmented_button = customtkinter.CTkSegmentedButton(self.main_frame, values=["Module Loading", "Detector Assembly (CERN)"],
                                                     command=self.segmented_button_callback)
        self.segmented_button.set("Module Loading")
        self.segmented_button.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="nsew")

        # left sub widget: form
        self.combobox_frame = customtkinter.CTkFrame(self.main_frame, width = 600)
        self.combobox_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.combobox_frame.grid_columnconfigure((0,1), weight=1)

        self.combobox_parent_T_label = customtkinter.CTkLabel(self.combobox_frame, text="Parent Part Type: Detector Unit")
        self.combobox_parent_T_label.grid(row=0, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew") 

        self.combobox_parent_label = customtkinter.CTkLabel(self.combobox_frame, text="Parent Part SN")
        self.combobox_parent_label.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="nsew") 
        
        self.combobox_parent = customtkinter.CTkComboBox(self.combobox_frame,
                                                    values=["Detector Unit", "Detector"],
                                                    command=self.show_clickable
                                                        )
        self.combobox_parent.grid(row=1, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.combobox_parent.set("- Select -")

        self.combobox_child_T_label = customtkinter.CTkLabel(self.combobox_frame, text="Child Part Type: Module")
        self.combobox_child_T_label.grid(row=2, column=0, padx=20, pady=(10, 10), columnspan=2, sticky="nsew") 
                
        self.combobox_child_label = customtkinter.CTkLabel(self.combobox_frame, text="Child Part SN")
        self.combobox_child_label.grid(row=3, column=0, padx=20, pady=(10, 10), sticky="nsew") 
        
        self.combobox_child = customtkinter.CTkComboBox(self.combobox_frame,
                                                    values=["Module", "Detector Unit"])
        self.combobox_child.grid(row=3, column=1, padx=20, pady=(10, 10), sticky="nsew")
        self.combobox_child.set("- Select -")

        self.position_label = customtkinter.CTkLabel(self.combobox_frame, text="Position (derived from canvas interaction)")
        self.position_label.grid(row=4, column=0, padx=20, pady=(10, 10), sticky="nsew")
        
        self.position_variable = customtkinter.StringVar(value="- automatic -")
        self.position_entry = customtkinter.CTkEntry(self.combobox_frame, textvariable=self.position_variable, state='disabled')
        self.position_entry.grid(row=4, column=1, padx=20, pady=(10, 10), sticky="nsew")

        self.add_button = customtkinter.CTkButton(self.combobox_frame, text="ADD PARTS TREE",
                                                   command=self.add_button_event)
        self.add_button.grid(row=5, column=1, padx=20, pady=(10, 10))

        # If we need to tackle a longer list of options, there is a custom dropdown frame to handle them
        #self.longcombobox = customtkinter.CTkComboBox(self.combobox_frame)
        #self.longcombobox.grid(row=6, column=1, padx=20, pady=10, sticky="nsew")
        #CTkScrollableDropdownFrame(self.longcombobox, values=['abc' for i in range(1000)], justify="left", button_color="transparent", x=100)

        
        # right sub widget: canvas containing DUs to click on
        self.canvas = customtkinter.CTkCanvas(self.main_frame, width = 500, height = 700, background='white')
        self.canvas.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        self.canvas.bind('<Button-1>', self.click_canvas_event)
        self.displayedDUtype = "None"

        
        self.info_label = customtkinter.CTkLabel(self.main_frame, text=" ", font=customtkinter.CTkFont(size=16, weight="bold"))
        self.info_label.grid(row=2, column=0, padx=20, pady=20, columnspan=2)

        self.api_status = 1
        self.last_responseText = ''
        # First startup of program defaults to Module Loading
        try:
            self.possible_parents, self.last_responseText = load_relevant_parts('Detector Unit')
            self.possible_children, self.last_responseText = load_relevant_parts('Module')
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
            info_text = textwrap.fill(f'Error: Parents / Children could not be loaded from ProdDB API.\n {self.last_responseText}',80)
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color="#007711")
            self.possible_parents_SNs_and_partIDs = grab_relevant_SNs_and_partIDs(self.possible_parents)
            self.possible_children_SNs_and_partIDs = grab_relevant_SNs_and_partIDs(self.possible_children)
            self.possible_parents_SNs = [entry[0] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_children_SNs = [entry[0] for entry in self.possible_children_SNs_and_partIDs]
            self.possible_parents_partIDs = [entry[1] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_children_partIDs = [entry[1] for entry in self.possible_children_SNs_and_partIDs]
            self.combobox_parent.configure(values=self.possible_parents_SNs)
            self.combobox_child.configure(values=self.possible_children_SNs)
        
    def load_p_c(self, p, c):
        try:
            self.possible_parents, self.last_responseText = load_relevant_parts(p)
            self.possible_children, self.last_responseText = load_relevant_parts(c)
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
            info_text = textwrap.fill(f'Error: Parents / Children could not be loaded from ProdDB API.\n {self.last_responseText}',80)
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.api_status = 1
            self.progressbar.configure(progress_color="#007711")
            self.possible_parents_SNs_and_partIDs = grab_relevant_SNs_and_partIDs(self.possible_parents)
            self.possible_children_SNs_and_partIDs = grab_relevant_SNs_and_partIDs(self.possible_children)
            self.possible_parents_SNs = [entry[0] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_children_SNs = [entry[0] for entry in self.possible_children_SNs_and_partIDs]
            self.possible_parents_partIDs = [entry[1] for entry in self.possible_parents_SNs_and_partIDs]
            self.possible_children_partIDs = [entry[1] for entry in self.possible_children_SNs_and_partIDs]
            self.combobox_parent.configure(values=self.possible_parents_SNs)
            self.combobox_child.configure(values=self.possible_children_SNs)

    def update_progressbar(self, thread):
        if thread.is_alive():
            # update progressbar
            self.progressbar.step()
            self.after(250, self.update_progressbar, thread)
        else:
            self.progressbar.set(1)
        
    # https://stackoverflow.com/a/23944658
    def segmented_button_callback(self, value):
        self.progressbar.set(0)
        
        self.info_label.configure(text=' ')
        self.canvas.delete("all")
        if value == "Module Loading":
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.combobox_parent_T_label.configure(text="Parent Part Type: Detector Unit")
            self.combobox_child_T_label.configure(text="Child Part Type: Module")
            self.position_label.configure(text="Position (derived from canvas interaction)")
            self.position_variable.set("- automatic -")
            self.position_entry.configure(state="disabled")
            self.loading_wheel = threading.Thread(target=self.load_p_c, args=('Detector Unit','Module'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
            
        else:
            self.combobox_parent.set("- Select -")
            self.combobox_child.set("- Select -")
            self.combobox_parent_T_label.configure(text="Parent Part Type: Detector")
            self.combobox_child_T_label.configure(text="Child Part Type: Detector Unit")
            self.position_label.configure(text="Position (type by hand)")
            self.position_variable.set("VxLyQz")
            self.position_entry.configure(state="normal")
            self.loading_wheel = threading.Thread(target=self.load_p_c, args=('Detector','Detector Unit'))
            self.loading_wheel.start()
            self.update_progressbar(self.loading_wheel)
    
    def roundedRect(self, x1, y1, width, height, radius=25, **kwargs):
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
    
    def show_clickable(self, something):
        parentSNIn = self.combobox_parent.get()
        childSNIn = self.combobox_child.get()

        if self.segmented_button.get() == 'Module Loading':
            parentNameIn = 'Detector Unit'
            childNameIn = 'Module'
            self.canvas.delete("all")
            for key in data.allDUs.keys():
                if key in parentSNIn:
                    self.displayedDUtype = key
                    self.info_label.configure(text=' ')
                    self.canvas.create_rectangle(40, 40, 360, 540, fill=data.fillColor_SU)
                    for mod in data.allDUs[self.displayedDUtype]:
                        self.roundedRect(mod['x'], mod['y'], mod['w'], mod['h'])
                    self.canvas.create_text(140, 475, text=self.displayedDUtype, anchor='nw', font=('Arial',50), fill=data.fillColor_SU_Text)
                    self.canvas.create_text(145, 20, text='Connector side', anchor='nw', fill=data.fillColor_SU_Text)
                    self.canvas.create_text(145, 545, text='Capacitor side', anchor='nw', fill=data.fillColor_SU_Text)
                    if 'FI10' in parentSNIn:
                        self.canvas.create_text(360, 290, text='Connector side', anchor='nw', fill=data.fillColor_SU_Text, angle=90)
                        self.canvas.create_text(20, 290, text='Capacitor side', anchor='nw', fill=data.fillColor_SU_Text, angle=90)
                    break
            else:
                info_text = 'Warning: Detector Unit type could not be retrieved from Parent SN.'
                print(f'>>> {info_text}')
                self.info_label.configure(text=info_text)

    def click_canvas_event(self, event):
        if self.segmented_button.get() == 'Module Loading':
            if self.displayedDUtype != 'None':
                arrayOfModulesInDU = data.allDUs[self.displayedDUtype]
                mouseInSomeMod = False
                mouseX = self.canvas.canvasx(event.x)
                mouseY = self.canvas.canvasy(event.y)
                #mouseX, mouseX = getCursorPosition(...)
                for slot in arrayOfModulesInDU:
                    if isInSlot(slot, mouseX, mouseY) == True:
                        mouseInSomeMod = True
                        self.position_variable.set(slot['slot'])
                        self.roundedRect(slot['x'], slot['y'], slot['w'], slot['h'], fill = data.fillColor_ActiveSlot)
                    else:
                        self.roundedRect(slot['x'], slot['y'], slot['w'], slot['h'], fill = data.fillColor_Slot)
                if not mouseInSomeMod:
                    self.position_variable.set("- automatic -")
                    info_text = 'Warning: Place mouse in some module slot.'
                    print(f'>>> {info_text}')
                    self.info_label.configure(text=info_text)
                else:
                    self.info_label.configure(text=' ')
        else:
            pass
            # ToDo: read DU connections from DB and display each connected module as a green slot

    def add_button_event(self):
        chi = self.combobox_child.get()
        par = self.combobox_parent.get()
        pos = self.position_entry.get()
        if chi == '- Select -' or par == '- Select -' or pos == '- automatic -' or pos == 'VxLyQz':
            # perhaps add a popup window in the future
            info_text = 'Warning: Select a child & parent from the respective lists and a position to proceed.'
            print(f'>>> {info_text}')
            self.info_label.configure(text=info_text)
        else:
            self.info_label.configure(text=' ')
            part_tree = {
                'position': pos,
                'is_record_deleted': 'F',
                'part': self.possible_children_partIDs[self.possible_children_SNs.index(chi)],
                'part_parent': self.possible_parents_partIDs[self.possible_parents_SNs.index(par)],
            }
            try:
                self.last_responseText = api.post_information('/partstreelist', part_tree)
            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                self.last_responseText = str(e)
            except ValueError as e:
                self.last_responseText = str(e)
    
            if self.last_responseText[:3] != '200':
                self.api_status = 0
                self.progressbar.configure(progress_color="#ff0000")
                info_text = textwrap.fill(f'Error: Parent / Child relation could not be patched to ProdDB API.\n {self.last_responseText}', 80)
                print(f'>>> {info_text}')
                self.info_label.configure(text=info_text)
            else:
                self.api_status = 1
                self.progressbar.configure(progress_color="#007711")
        
if __name__ == "__main__":
    app = App()
    app.mainloop()